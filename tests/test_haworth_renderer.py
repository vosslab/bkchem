"""Unit tests for Haworth schematic render_ops output."""

# Standard Library
import math
from xml.dom import minidom as xml_minidom

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

import oasa.dom_extensions as dom_extensions
import oasa.haworth as haworth
import oasa.haworth_renderer as haworth_renderer
import oasa.haworth_spec as haworth_spec
import oasa.render_geometry as render_geometry
import oasa.render_ops as render_ops
import oasa.sugar_code as sugar_code


#============================================
def _build_spec(code: str, ring_type: str, anomeric: str) -> haworth_spec.HaworthSpec:
	parsed = sugar_code.parse(code)
	return haworth_spec.generate(parsed, ring_type=ring_type, anomeric=anomeric)


#============================================
def _render(code: str, ring_type: str, anomeric: str, bond_length: float = 30.0, **kwargs) -> tuple:
	spec = _build_spec(code, ring_type, anomeric)
	ops = haworth_renderer.render(spec, bond_length=bond_length, **kwargs)
	return spec, ops


#============================================
def _texts(ops):
	return [op for op in ops if isinstance(op, render_ops.TextOp)]


#============================================
def _polygons(ops):
	return [op for op in ops if isinstance(op, render_ops.PolygonOp)]


#============================================
def _lines(ops):
	return [op for op in ops if isinstance(op, render_ops.LineOp)]


#============================================
def _by_id(ops, op_id: str):
	for op in ops:
		if getattr(op, "op_id", None) == op_id:
			return op
	raise AssertionError("Missing op_id %s" % op_id)


#============================================
def _text_by_id(ops, op_id: str) -> render_ops.TextOp:
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.TextOp)
	return op


#============================================
def _line_by_id(ops, op_id: str) -> render_ops.LineOp:
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.LineOp)
	return op


#============================================
def _polygon_by_id(ops, op_id: str) -> render_ops.PolygonOp:
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.PolygonOp)
	return op


#============================================
def _ring_vertex(spec: haworth_spec.HaworthSpec, carbon: int, bond_length: float = 30.0) -> tuple[float, float]:
	slot_map = haworth_renderer.carbon_slot_map(spec)
	slot = slot_map[f"C{carbon}"]
	if spec.ring_type == "pyranose":
		coords = haworth._ring_template(6, bond_length=bond_length)
		index = haworth_renderer.PYRANOSE_SLOT_INDEX[slot]
	else:
		coords = haworth._ring_template(5, bond_length=bond_length)
		index = haworth_renderer.FURANOSE_SLOT_INDEX[slot]
	return coords[index]


#============================================
def _ring_center(spec: haworth_spec.HaworthSpec, bond_length: float = 30.0) -> tuple[float, float]:
	if spec.ring_type == "pyranose":
		coords = haworth._ring_template(6, bond_length=bond_length)
	else:
		coords = haworth._ring_template(5, bond_length=bond_length)
	center_x = sum(point[0] for point in coords) / len(coords)
	center_y = sum(point[1] for point in coords) / len(coords)
	return (center_x, center_y)


#============================================
def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
	return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


#============================================
def _line_length(line: render_ops.LineOp) -> float:
	return _distance(line.p1, line.p2)


#============================================
def _bbox(ops: list) -> tuple[float, float, float, float]:
	minx = float("inf")
	miny = float("inf")
	maxx = float("-inf")
	maxy = float("-inf")

	def take(x: float, y: float) -> None:
		nonlocal minx
		nonlocal miny
		nonlocal maxx
		nonlocal maxy
		minx = min(minx, x)
		miny = min(miny, y)
		maxx = max(maxx, x)
		maxy = max(maxy, y)

	for op in ops:
		if isinstance(op, render_ops.LineOp):
			take(op.p1[0], op.p1[1])
			take(op.p2[0], op.p2[1])
			continue
		if isinstance(op, render_ops.PolygonOp):
			for x, y in op.points:
				take(x, y)
			continue
		if isinstance(op, render_ops.TextOp):
			visible = haworth_renderer._visible_text_length(op.text)
			width = visible * op.font_size * 0.6
			height = op.font_size
			x = op.x
			if op.anchor == "middle":
				x -= width / 2.0
			elif op.anchor == "end":
				x -= width
			take(x, op.y - height)
			take(x + width, op.y)
	if minx == float("inf"):
		raise AssertionError("No drawable ops for bbox")
	return (minx, miny, maxx, maxy)


#============================================
def _edge_thicknesses(poly: render_ops.PolygonOp) -> tuple[float, float]:
	p0, p1, p2, p3 = poly.points
	return (_distance(p0, p1), _distance(p2, p3))


#============================================
def _label_bbox(label: render_ops.TextOp) -> tuple[float, float, float, float]:
	return haworth_renderer._text_bbox(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
	)


#============================================
def _point_in_box(point: tuple[float, float], box: tuple[float, float, float, float]) -> bool:
	return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


#============================================
def _point_on_box_edge(
		point: tuple[float, float],
		box: tuple[float, float, float, float],
		tol: float = 1e-6) -> bool:
	x_value, y_value = point
	x1, y1, x2, y2 = box
	on_x = abs(x_value - x1) <= tol or abs(x_value - x2) <= tol
	on_y = abs(y_value - y1) <= tol or abs(y_value - y2) <= tol
	in_x = (x1 - tol) <= x_value <= (x2 + tol)
	in_y = (y1 - tol) <= y_value <= (y2 + tol)
	return (on_x and in_y) or (on_y and in_x)


#============================================
def _connector_bbox_for_label(label: render_ops.TextOp) -> tuple[float, float, float, float]:
	first_bbox = render_geometry.label_attach_bbox_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom="first",
	)
	last_bbox = render_geometry.label_attach_bbox_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom="last",
	)
	if first_bbox != last_bbox:
		return first_bbox
	return _label_bbox(label)


#============================================
def _rect_corners(box: tuple[float, float, float, float]) -> list[tuple[float, float]]:
	return [
		(box[0], box[1]),
		(box[2], box[1]),
		(box[2], box[3]),
		(box[0], box[3]),
	]


#============================================
def _point_in_polygon(point: tuple[float, float], polygon: tuple[tuple[float, float], ...]) -> bool:
	x_value, y_value = point
	inside = False
	count = len(polygon)
	for index in range(count):
		x1, y1 = polygon[index]
		x2, y2 = polygon[(index + 1) % count]
		intersects = ((y1 > y_value) != (y2 > y_value))
		if not intersects:
			continue
		denominator = y2 - y1
		if abs(denominator) < 1e-9:
			continue
		x_intersect = x1 + ((y_value - y1) * (x2 - x1) / denominator)
		if x_intersect >= x_value:
			inside = not inside
	return inside


#============================================
def _segments_intersect(
		a1: tuple[float, float],
		a2: tuple[float, float],
		b1: tuple[float, float],
		b2: tuple[float, float]) -> bool:
	def _cross(p1, p2, p3):
		return ((p2[0] - p1[0]) * (p3[1] - p1[1])) - ((p2[1] - p1[1]) * (p3[0] - p1[0]))

	def _on_segment(p1, p2, p3):
		return (
			min(p1[0], p2[0]) - 1e-9 <= p3[0] <= max(p1[0], p2[0]) + 1e-9
			and min(p1[1], p2[1]) - 1e-9 <= p3[1] <= max(p1[1], p2[1]) + 1e-9
		)

	d1 = _cross(a1, a2, b1)
	d2 = _cross(a1, a2, b2)
	d3 = _cross(b1, b2, a1)
	d4 = _cross(b1, b2, a2)
	if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
		return True
	if abs(d1) < 1e-9 and _on_segment(a1, a2, b1):
		return True
	if abs(d2) < 1e-9 and _on_segment(a1, a2, b2):
		return True
	if abs(d3) < 1e-9 and _on_segment(b1, b2, a1):
		return True
	if abs(d4) < 1e-9 and _on_segment(b1, b2, a2):
		return True
	return False


#============================================
def _box_overlaps_polygon(
		box: tuple[float, float, float, float],
		polygon: tuple[tuple[float, float], ...]) -> bool:
	for point in polygon:
		if _point_in_box(point, box):
			return True
	for corner in _rect_corners(box):
		if _point_in_polygon(corner, polygon):
			return True
	rect_points = _rect_corners(box)
	rect_edges = [
		(rect_points[0], rect_points[1]),
		(rect_points[1], rect_points[2]),
		(rect_points[2], rect_points[3]),
		(rect_points[3], rect_points[0]),
	]
	for index in range(len(polygon)):
		edge_start = polygon[index]
		edge_end = polygon[(index + 1) % len(polygon)]
		for rect_start, rect_end in rect_edges:
			if _segments_intersect(edge_start, edge_end, rect_start, rect_end):
				return True
	return False


#============================================
def test_render_returns_ops():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert isinstance(ops, list)
	assert ops


#============================================
def test_render_contains_text_ops():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	text_values = [op.text for op in _texts(ops)]
	assert "O" in text_values
	assert "OH" in text_values
	assert "H" in text_values


#============================================
def test_render_contains_polygon_ops():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	polys = _polygons(ops)
	assert len(polys) >= 7


#============================================
def test_render_bbox_reasonable():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	minx, miny, maxx, maxy = _bbox(ops)
	assert maxx > minx
	assert maxy > miny
	assert (maxx - minx) > 20.0
	assert (maxy - miny) > 20.0


#============================================
def test_render_furanose():
	_, ops = _render("ARRDM", "furanose", "beta")
	ring_polys = [op for op in _polygons(ops) if (op.op_id or "").startswith("ring_edge_")]
	# 5 edges: 3 non-oxygen + 2 oxygen-adjacent (each split into 2 halves) = 7
	assert len(ring_polys) == 7


#============================================
def test_furanose_template_calibrated_to_neurotiker_means():
	assert haworth.FURANOSE_TEMPLATE[0] == pytest.approx((-0.97, -0.26))
	assert haworth.FURANOSE_TEMPLATE[1] == pytest.approx((-0.49, 0.58))
	assert haworth.FURANOSE_TEMPLATE[2] == pytest.approx((0.49, 0.58))
	assert haworth.FURANOSE_TEMPLATE[3] == pytest.approx((0.97, -0.26))
	assert haworth.FURANOSE_TEMPLATE[4] == pytest.approx((0.00, -0.65))


#============================================
def test_render_with_carbon_numbers():
	_, ops = _render("ARLRDM", "pyranose", "alpha", show_carbon_numbers=True)
	number_labels = [op for op in _texts(ops) if (op.op_id or "").endswith("_number")]
	assert len(number_labels) == 5


#============================================
def test_render_carbon_numbers_closer_to_ring_vertices():
	spec, ops = _render("ARLRDM", "pyranose", "alpha", show_carbon_numbers=True)
	center = _ring_center(spec, bond_length=30.0)
	for carbon in (1, 2, 3, 4, 5):
		vertex = _ring_vertex(spec, carbon, bond_length=30.0)
		label = _text_by_id(ops, f"C{carbon}_number")
		label_point = (label.x, label.y)
		assert _distance(label_point, vertex) < _distance(label_point, center)


#============================================
def test_render_aldohexose_furanose():
	_, ops = _render("ARLRDM", "furanose", "alpha")
	assert _text_by_id(ops, "C4_up_chain1_oh_label").text == "HO"
	assert _text_by_id(ops, "C4_up_chain2_label").text == "HOH<sub>2</sub>C"


#============================================
def test_render_ribose_pyranose():
	_, ops = _render("ARRDM", "pyranose", "alpha")
	chain_ops = [op for op in ops if "chain" in (op.op_id or "")]
	assert not chain_ops


#============================================
def test_render_erythrose_furanose():
	_, ops = _render("ARDM", "furanose", "beta")
	chain_ops = [op for op in ops if "chain" in (op.op_id or "")]
	assert not chain_ops


#============================================
def test_render_front_edge_stable():
	_, ops = _render("ARLRDM", "pyranose", "alpha", bond_length=40.0)
	front = _polygon_by_id(ops, f"ring_edge_{haworth_renderer.PYRANOSE_FRONT_EDGE_INDEX}")
	back = _polygon_by_id(ops, "ring_edge_0")
	front_start, front_end = _edge_thicknesses(front)
	back_start, back_end = _edge_thicknesses(back)
	assert front_start > back_start
	assert front_end > back_end


#============================================
def test_render_furanose_labels():
	_, ops = _render("ARRDM", "furanose", "alpha")
	c1_up = _text_by_id(ops, "C1_up_label")
	c2_up = _text_by_id(ops, "C2_up_label")
	assert c1_up.anchor == "start"
	assert c2_up.anchor == "start"


#============================================
def test_render_pyranose_side_connectors_vertical():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for op_id in ("C1_up_connector", "C1_down_connector", "C4_up_connector", "C4_down_connector"):
		line = _line_by_id(ops, op_id)
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		label_box = _label_bbox(label)
		assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_furanose_side_connectors_vertical():
	_, ops = _render("MKLRDM", "furanose", "beta")
	for op_id in ("C2_up_connector", "C2_down_connector", "C5_up_connector", "C5_down_connector"):
		line = _line_by_id(ops, op_id)
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		label_box = _label_bbox(label)
		assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_connector_terminates_at_bbox_edge():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for op in _lines(ops):
		op_id = op.op_id or ""
		if not op_id.endswith("_connector"):
			continue
		if "_chain" in op_id:
			continue
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		label_box = _connector_bbox_for_label(label)
		assert _point_on_box_edge(op.p2, label_box, tol=1e-5)


#============================================
def test_connector_does_not_enter_bbox():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for op in _lines(ops):
		op_id = op.op_id or ""
		if not op_id.endswith("_connector"):
			continue
		if "_chain" in op_id:
			continue
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		label_box = _connector_bbox_for_label(label)
		assert _point_on_box_edge(op.p2, label_box, tol=1e-5)
		midpoint = ((op.p1[0] + op.p2[0]) / 2.0, (op.p1[1] + op.p2[1]) / 2.0)
		assert not _point_in_box(midpoint, label_box)


#============================================
def test_no_connector_passes_through_label():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for op in _lines(ops):
		op_id = op.op_id or ""
		if not op_id.endswith("_connector"):
			continue
		if "_chain" in op_id:
			continue
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		label_box = _connector_bbox_for_label(label)
		midpoint = ((op.p1[0] + op.p2[0]) / 2.0, (op.p1[1] + op.p2[1]) / 2.0)
		assert not _point_in_box(midpoint, label_box)


#============================================
def test_render_internal_left_hydroxyl_uses_oh_order():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert _text_by_id(ops, "C3_up_label").text == "OH"


#============================================
def test_render_left_anchor_down_hydroxyl_uses_ho_order():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert _text_by_id(ops, "C4_down_label").text == "HO"


#============================================
def test_render_right_anchor_hydroxyl_keeps_oh_order():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert _text_by_id(ops, "C1_down_label").text == "OH"
	assert _text_by_id(ops, "C2_down_label").text == "OH"


#============================================
def test_render_right_anchor_hydroxyl_connector_hits_o_center():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	label = _text_by_id(ops, "C2_down_label")
	line = _line_by_id(ops, "C2_down_connector")
	assert label.text == "OH"
	assert label.anchor == "start"
	label_box = _connector_bbox_for_label(label)
	assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_left_anchor_hydroxyl_connector_hits_o_center():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	label = _text_by_id(ops, "C4_down_label")
	line = _line_by_id(ops, "C4_down_connector")
	assert label.text == "HO"
	assert label.anchor == "end"
	label_box = _connector_bbox_for_label(label)
	assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_hydroxyl_connectors_do_not_overlap_oxygen_glyph():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	for label in _texts(ops):
		op_id = label.op_id or ""
		if not op_id.endswith("_label"):
			continue
		if label.text not in ("OH", "HO"):
			continue
		line = _line_by_id(ops, op_id.replace("_label", "_connector"))
		label_box = _connector_bbox_for_label(label)
		assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_hydroxyl_two_pass_increases_spacing_for_aldm_furanose_alpha():
	_, ops = _render("ALDM", "furanose", "alpha", show_hydrogens=False)
	c1_down = _text_by_id(ops, "C1_down_label")
	c2_up = _text_by_id(ops, "C2_up_label")
	assert c1_down.text == "OH"
	assert c2_up.text in ("OH", "HO")
	gap = c1_down.font_size * haworth_renderer.HYDROXYL_LAYOUT_MIN_GAP_FACTOR
	intersection = haworth_renderer._intersection_area(_label_bbox(c1_down), _label_bbox(c2_up), gap=gap)
	assert intersection == pytest.approx(0.0, abs=1e-6)
	default_length = 30.0 * 0.45
	c1_down_line = _line_by_id(ops, "C1_down_connector")
	c2_up_line = _line_by_id(ops, "C2_up_connector")
	c1_length = _line_length(c1_down_line)
	c2_length = _line_length(c2_up_line)
	assert (abs(c1_length - default_length) > 1e-6) or (abs(c2_length - default_length) > 1e-6)


#============================================
def test_render_arabinose_furanose_labels_do_not_overlap_ring_bonds():
	_, ops = _render("ALRDM", "furanose", "alpha", show_hydrogens=False)
	ring_polys = [op for op in _polygons(ops) if (op.op_id or "").startswith("ring_edge_")]
	for label in _texts(ops):
		op_id = label.op_id or ""
		if not op_id.endswith("_label"):
			continue
		if op_id == "oxygen_label":
			continue
		label_box = _label_bbox(label)
		for polygon in ring_polys:
				assert not _box_overlaps_polygon(label_box, polygon.points), (
					f"{op_id} overlaps {polygon.op_id}"
				)


#============================================
def test_render_lyxose_pyranose_internal_labels_do_not_overlap_ring_bonds():
	_, ops = _render("ALLDM", "pyranose", "alpha", show_hydrogens=False)
	ring_polys = [op for op in _polygons(ops) if (op.op_id or "").startswith("ring_edge_")]
	for op_id in ("C2_up_label", "C3_up_label"):
		label_box = _label_bbox(_text_by_id(ops, op_id))
		for polygon in ring_polys:
			assert not _box_overlaps_polygon(label_box, polygon.points), (
				f"{op_id} overlaps {polygon.op_id}"
			)


#============================================
def test_render_lyxose_pyranose_internal_connectors_stop_at_label_edges():
	_, ops = _render("ALLDM", "pyranose", "alpha", show_hydrogens=False)
	for op_id in ("C2_up_connector", "C3_up_connector"):
		line = _line_by_id(ops, op_id)
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		label_box = _connector_bbox_for_label(label)
		assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_mannose_pyranose_internal_pair_renders_oh_ho():
	_, ops = _render("ALLRDM", "pyranose", "alpha", show_hydrogens=False)
	assert _text_by_id(ops, "C2_up_label").text == "HO"
	assert _text_by_id(ops, "C3_up_label").text == "OH"


#============================================
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_render_arabinose_pyranose_internal_right_is_ho(anomeric):
	_, ops = _render("ALRDM", "pyranose", anomeric, show_hydrogens=False)
	assert _text_by_id(ops, "C2_up_label").text == "HO"


#============================================
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_render_xylose_pyranose_internal_left_is_oh(anomeric):
	_, ops = _render("ARLDM", "pyranose", anomeric, show_hydrogens=False)
	assert _text_by_id(ops, "C3_up_label").text == "OH"


#============================================
def test_render_lyxose_furanose_internal_pair_has_no_ohho_overlap():
	_, ops = _render("ALLDM", "furanose", "alpha", show_hydrogens=False)
	left = _text_by_id(ops, "C3_up_label")
	right = _text_by_id(ops, "C2_up_label")
	overlap = haworth_renderer._intersection_area(_label_bbox(left), _label_bbox(right), gap=0.0)
	assert overlap <= haworth_renderer.INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD


#============================================
def test_render_lyxose_furanose_internal_pair_uses_spacing_rule():
	_, ops = _render("ALLDM", "furanose", "alpha", show_hydrogens=False)
	left = _text_by_id(ops, "C3_up_label")
	right = _text_by_id(ops, "C2_up_label")
	assert left.text == "OH"
	assert right.text == "HO"
	left_box = _label_bbox(left)
	right_box = _label_bbox(right)
	h_gap = right_box[0] - left_box[2]
	min_gap = 12.0 * haworth_renderer.INTERNAL_PAIR_MIN_H_GAP_FACTOR
	scaled_size = 12.0 * haworth_renderer.INTERNAL_PAIR_LABEL_SCALE
	is_scaled = (
		left.font_size == pytest.approx(scaled_size)
		and right.font_size == pytest.approx(scaled_size)
	)
	assert is_scaled or (h_gap >= min_gap)


#============================================
def test_internal_pair_adjustment_flips_then_scales_once():
	jobs = [
		{
			"carbon": 3,
			"ring_type": "furanose",
			"slot": "BL",
			"direction": "up",
			"vertex": (-2.0, 0.0),
			"dx": 0.0,
			"dy": -1.0,
			"length": 10.0,
			"label": "OH",
			"connector_width": 1.0,
			"font_size": 12.0,
			"font_name": "sans-serif",
			"anchor": "start",
			"text_scale": 1.0,
			"line_color": "#000",
			"label_color": "#000",
		},
		{
			"carbon": 2,
			"ring_type": "furanose",
			"slot": "BR",
			"direction": "up",
			"vertex": (2.0, 0.0),
			"dx": 0.0,
			"dy": -1.0,
			"length": 10.0,
			"label": "OH",
			"connector_width": 1.0,
			"font_size": 12.0,
			"font_name": "sans-serif",
			"anchor": "end",
			"text_scale": 1.0,
			"line_color": "#000",
			"label_color": "#000",
		},
	]
	haworth_renderer._resolve_internal_hydroxyl_pair_overlap(jobs)
	assert jobs[0]["anchor"] == "start"
	assert jobs[1]["anchor"] == "end"
	assert jobs[0]["text_scale"] == pytest.approx(haworth_renderer.INTERNAL_PAIR_LABEL_SCALE)
	assert jobs[1]["text_scale"] == pytest.approx(haworth_renderer.INTERNAL_PAIR_LABEL_SCALE)


#============================================
def test_validate_simple_job_rejects_invalid_anchor():
	job = {
		"carbon": 3,
		"ring_type": "furanose",
		"slot": "BL",
		"direction": "up",
		"vertex": (-2.0, 0.0),
		"dx": 0.0,
		"dy": -1.0,
		"length": 10.0,
		"label": "OH",
		"connector_width": 1.0,
		"font_size": 12.0,
		"font_name": "sans-serif",
		"anchor": "leftward",
		"text_scale": 1.0,
		"line_color": "#000",
		"label_color": "#000",
	}
	with pytest.raises(ValueError, match="invalid anchor"):
		haworth_renderer._validate_simple_job(job)


#============================================
def test_validate_simple_job_rejects_invalid_slot_for_ring_type():
	job = {
		"carbon": 3,
		"ring_type": "furanose",
		"slot": "TL",
		"direction": "up",
		"vertex": (-2.0, 0.0),
		"dx": 0.0,
		"dy": -1.0,
		"length": 10.0,
		"label": "OH",
		"connector_width": 1.0,
		"font_size": 12.0,
		"font_name": "sans-serif",
		"anchor": "start",
		"text_scale": 1.0,
		"line_color": "#000",
		"label_color": "#000",
	}
	with pytest.raises(ValueError, match="not valid for ring_type"):
		haworth_renderer._validate_simple_job(job)


#============================================
def test_render_mannose_furanose_internal_pair_uses_oh_ho_scaled():
	_, ops = _render("ALLRDM", "furanose", "alpha", show_hydrogens=False)
	left = _text_by_id(ops, "C3_up_label")
	right = _text_by_id(ops, "C2_up_label")
	assert left.text == "OH"
	assert right.text == "HO"
	scaled_size = 12.0 * haworth_renderer.INTERNAL_PAIR_LABEL_SCALE
	assert left.font_size == pytest.approx(scaled_size)
	assert right.font_size == pytest.approx(scaled_size)


#============================================
def test_furanose_internal_dual_hydroxyl_never_uses_ho_oh_order():
	codes = (
		"ARDM", "ALDM", "ARRDM", "ALRDM", "ARLDM", "ALLDM",
		"ARRRDM", "ALRRDM", "ARLRDM", "ALLRDM", "ARRLDM", "ALRLDM", "ARLLDM", "ALLLDM",
		"MKRDM", "MKLDM", "MKLRDM", "MKLLDM", "MKRRDM", "MKRLDM",
	)
	checked_pairs = 0
	for code in codes:
		for anomeric in ("alpha", "beta"):
			spec, ops = _render(code, "furanose", anomeric, show_hydrogens=False)
			slot_map = haworth_renderer.carbon_slot_map(spec)
			slot_to_carbon = {slot: int(carbon_key[1:]) for carbon_key, slot in slot_map.items()}
			left_carbon = slot_to_carbon.get("BL")
			right_carbon = slot_to_carbon.get("BR")
			if left_carbon is None or right_carbon is None:
				continue
			left_label = next(
				(op for op in ops if getattr(op, "op_id", None) == f"C{left_carbon}_up_label"),
				None,
			)
			right_label = next(
				(op for op in ops if getattr(op, "op_id", None) == f"C{right_carbon}_up_label"),
				None,
			)
			if not left_label or not right_label:
				continue
			if left_label.text in ("OH", "HO") and right_label.text in ("OH", "HO"):
				checked_pairs += 1
				assert (left_label.text, right_label.text) == ("OH", "HO"), (
					f"{code} {anomeric}: internal pair rendered {left_label.text} {right_label.text}"
				)
	assert checked_pairs > 0


#============================================
def test_render_ch2oh_connector_hits_leading_carbon_center():
	_, ops = _render("ARRRDM", "pyranose", "alpha", show_hydrogens=False)
	label = _text_by_id(ops, "C5_up_label")
	line = _line_by_id(ops, "C5_up_connector")
	assert label.text == "CH<sub>2</sub>OH"
	label_box = _connector_bbox_for_label(label)
	assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_cooh_connector_hits_leading_carbon_center():
	_, ops = _render("ARLLDc", "pyranose", "alpha", show_hydrogens=False)
	label = _text_by_id(ops, "C5_up_label")
	line = _line_by_id(ops, "C5_up_connector")
	assert label.text == "COOH"
	label_box = _connector_bbox_for_label(label)
	assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_arabinose_furanose_ch2oh_connector_hits_leading_carbon_center():
	_, ops = _render("ALRDM", "furanose", "alpha", show_hydrogens=False)
	label = _text_by_id(ops, "C4_up_label")
	line = _line_by_id(ops, "C4_up_connector")
	assert label.text == "CH<sub>2</sub>OH"
	label_box = _connector_bbox_for_label(label)
	assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
@pytest.mark.parametrize("code", ("MKRDM", "MKLDM"))
def test_render_ketopentose_furanose_down_ch2oh_connector_hits_leading_carbon_center(code):
	_, ops = _render(code, "furanose", "beta", show_hydrogens=False)
	label = _text_by_id(ops, "C2_down_label")
	line = _line_by_id(ops, "C2_down_connector")
	assert label.text == "CH<sub>2</sub>OH"
	label_box = _connector_bbox_for_label(label)
	assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_furanose_top_up_connectors_above_oxygen_label():
	_, ops = _render("MKLRDM", "furanose", "beta", show_hydrogens=False)
	oxygen = _text_by_id(ops, "oxygen_label")
	oxygen_top = oxygen.y - oxygen.font_size
	for op_id in ("C2_up_connector", "C5_up_connector"):
		line = _line_by_id(ops, op_id)
		assert line.p2[1] < (oxygen_top - 0.05)


#============================================
def test_render_arabinose_furanose_beta_top_labels_are_not_flat_aligned():
	_, ops = _render("ALRDM", "furanose", "beta", show_hydrogens=False)
	right_oh = _text_by_id(ops, "C1_up_label")
	left_chain = _text_by_id(ops, "C4_up_label")
	assert right_oh.text == "OH"
	assert left_chain.text == "CH<sub>2</sub>OH"
	assert right_oh.y > left_chain.y
	assert (right_oh.y - left_chain.y) >= (right_oh.font_size * 0.09)


#============================================
def test_resolve_hydroxyl_layout_jobs_uses_candidate_slots():
	jobs = [
		{
			"carbon": 1,
			"direction": "down",
			"vertex": (0.0, 0.0),
			"dx": 0.0,
			"dy": 1.0,
			"length": 10.0,
			"label": "OH",
			"connector_width": 1.0,
			"font_size": 12.0,
			"font_name": "sans-serif",
			"anchor": "start",
			"line_color": "#000",
			"label_color": "#000",
		},
		{
			"carbon": 2,
			"direction": "down",
			"vertex": (0.0, 2.0),
			"dx": 0.0,
			"dy": 1.0,
			"length": 10.0,
			"label": "OH",
			"connector_width": 1.0,
			"font_size": 12.0,
			"font_name": "sans-serif",
			"anchor": "start",
			"line_color": "#000",
			"label_color": "#000",
		},
	]
	resolved = haworth_renderer._resolve_hydroxyl_layout_jobs(jobs)
	assert len(resolved) == 2
	assert resolved[0]["length"] == pytest.approx(10.0)
	assert resolved[1]["length"] > 10.0


#============================================
def test_render_bbox_sub_tags():
	assert haworth_renderer._visible_text_length("CH<sub>2</sub>OH") == 5


#============================================
def test_render_subscript_svg_uses_lowered_tspan_dy():
	_, ops = _render("ALRDM", "furanose", "alpha", show_hydrogens=False)
	try:
		impl = xml_minidom.getDOMImplementation()
		doc = impl.createDocument(None, None, None)
	except Exception:
		doc = xml_minidom.Document()
	svg = dom_extensions.elementUnder(
		doc,
		"svg",
		attributes=(
			("xmlns", "http://www.w3.org/2000/svg"),
			("version", "1.1"),
			("width", "220"),
			("height", "220"),
			("viewBox", "0 0 220 220"),
		),
	)
	render_ops.ops_to_svg(svg, ops)
	svg_text = doc.toxml("utf-8")
	if isinstance(svg_text, bytes):
		svg_text = svg_text.decode("utf-8")
	assert 'dy="4.80"' in svg_text
	assert 'dy="-4.80"' in svg_text
	assert 'baseline-shift=' not in svg_text


#============================================
def test_render_fructose_anomeric_no_overlap():
	_, ops = _render("MKLRDM", "furanose", "beta")
	up = _text_by_id(ops, "C2_up_label")
	down = _text_by_id(ops, "C2_down_label")
	assert _distance((up.x, up.y), (down.x, down.y)) > 8.0


#============================================
def test_render_alpha_glucose_c1_oh_below():
	spec, ops = _render("ARLRDM", "pyranose", "alpha")
	vertex = _ring_vertex(spec, 1)
	oh_label = _text_by_id(ops, "C1_down_label")
	assert oh_label.text == "OH"
	assert oh_label.y > vertex[1]


#============================================
def test_render_alpha_glucose_c3_oh_above():
	spec, ops = _render("ARLRDM", "pyranose", "alpha")
	vertex = _ring_vertex(spec, 3)
	oh_label = _text_by_id(ops, "C3_up_label")
	assert oh_label.text == "OH"
	assert oh_label.y < vertex[1]


#============================================
def test_render_beta_glucose_c1_oh_above():
	spec, ops = _render("ARLRDM", "pyranose", "beta")
	vertex = _ring_vertex(spec, 1)
	oh_label = _text_by_id(ops, "C1_up_label")
	assert oh_label.text == "OH"
	assert oh_label.y < vertex[1]


#============================================
def test_render_all_substituents_correct_side():
	spec, ops = _render("ARLRDM", "pyranose", "alpha")
	for carbon in (1, 2, 3, 4, 5):
		vertex = _ring_vertex(spec, carbon)
		up = _text_by_id(ops, f"C{carbon}_up_label")
		down = _text_by_id(ops, f"C{carbon}_down_label")
		assert up.y < vertex[1]
		assert down.y > vertex[1]


#============================================
def test_render_fructose_c2_labels_both_offset():
	spec, ops = _render("MKLRDM", "furanose", "beta", bond_length=30.0)
	vertex = _ring_vertex(spec, 2)
	up = _text_by_id(ops, "C2_up_label")
	down = _text_by_id(ops, "C2_down_label")
	assert _distance(vertex, (up.x, up.y)) > (30.0 * 0.4)
	assert _distance(vertex, (down.x, down.y)) > (30.0 * 0.4)
	assert up.y < vertex[1] < down.y


#============================================
def test_render_l_series_reverses_directions():
	spec, ops = _render("ARLRLM", "pyranose", "alpha")
	vertex = _ring_vertex(spec, 1)
	oh_label = _text_by_id(ops, "C1_up_label")
	assert oh_label.text == "OH"
	assert oh_label.y < vertex[1]


#============================================
def test_visible_text_length_no_tags():
	assert haworth_renderer._visible_text_length("OH") == 2


#============================================
def test_visible_text_length_empty():
	assert haworth_renderer._visible_text_length("") == 0


#============================================
def test_visible_text_length_nested_tags():
	assert haworth_renderer._visible_text_length("<b>O<sub>2</sub></b>") == 2


#============================================
def test_sub_length_multiplier_dual_wide():
	_, ops = _render("MKLRDM", "furanose", "beta", bond_length=40.0)
	line = _line_by_id(ops, "C2_up_connector")
	label = _text_by_id(ops, "C2_up_label")
	label_box = _connector_bbox_for_label(label)
	assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_sub_length_default_single_wide():
	_, ops = _render("ARLRDM", "pyranose", "alpha", bond_length=40.0)
	line = _line_by_id(ops, "C1_down_connector")
	label = _text_by_id(ops, "C1_down_label")
	label_box = _connector_bbox_for_label(label)
	assert _point_on_box_edge(line.p2, label_box, tol=1e-5)


#============================================
def test_render_o_mask_uses_bg_color():
	_, ops = _render("ARLRDM", "pyranose", "alpha", bg_color="#f0f0f0")
	mask = _polygon_by_id(ops, "oxygen_mask")
	assert mask.fill == "#f0f0f0"


#============================================
def test_render_o_mask_default_white():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	mask = _polygon_by_id(ops, "oxygen_mask")
	assert mask.fill == "#fff"


#============================================
def test_render_o_mask_is_polygon_not_rect():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	mask = _polygon_by_id(ops, "oxygen_mask")
	assert isinstance(mask, render_ops.PolygonOp)


#============================================
def test_render_exocyclic_2_chain_direction():
	_, ops = _render("ARLRDM", "furanose", "alpha", bond_length=30.0)
	trunk = _line_by_id(ops, "C4_up_chain1_connector")
	ho_branch = _line_by_id(ops, "C4_up_chain1_oh_connector")
	ch2_branch = _line_by_id(ops, "C4_up_chain2_connector")
	assert ho_branch.p1 == pytest.approx(trunk.p2)
	assert ch2_branch.p1 == pytest.approx(trunk.p2)
	assert ho_branch.p2[0] < ho_branch.p1[0]
	assert ch2_branch.p2[0] < ch2_branch.p1[0]
	assert ho_branch.p2[1] < ho_branch.p1[1]
	assert ch2_branch.p2[1] > ch2_branch.p1[1]


#============================================
def test_render_exocyclic_2_chain_labels():
	_, ops = _render("ARLRDM", "furanose", "alpha")
	ho = _text_by_id(ops, "C4_up_chain1_oh_label")
	ch2 = _text_by_id(ops, "C4_up_chain2_label")
	assert ho.text == "HO"
	assert ch2.text == "HOH<sub>2</sub>C"
	assert _distance((ch2.x, ch2.y), (ho.x, ho.y)) > 5.0


#============================================
def test_render_gulose_furanose_chain_labels_flip_leftward_alpha_beta():
	for anomeric in ("alpha", "beta"):
		_, ops = _render("ARRLDM", "furanose", anomeric, show_hydrogens=False)
		assert _text_by_id(ops, "C4_down_chain1_oh_label").text == "HO"
		assert _text_by_id(ops, "C4_down_chain2_label").text == "HOH<sub>2</sub>C"


#============================================
@pytest.mark.parametrize(
	"code,direction",
	[
		("ALLLDM", "down"),
		("ARLLDM", "down"),
		("ALRLDM", "down"),
		("ALLRDM", "up"),
		("ARLRDM", "up"),
	],
)
def test_render_furanose_two_carbon_tail_uses_branched_labels(code, direction):
	_, ops = _render(code, "furanose", "alpha", show_hydrogens=False)
	assert _text_by_id(ops, f"C4_{direction}_chain1_oh_label").text == "HO"
	assert _text_by_id(ops, f"C4_{direction}_chain2_label").text == "HOH<sub>2</sub>C"
	chain_texts = [op.text for op in _texts(ops) if "chain" in (op.op_id or "")]
	assert "HOHC" not in chain_texts


#============================================
def test_render_exocyclic_0_no_chain():
	_, ops = _render("ARRDM", "pyranose", "alpha")
	chain_ops = [op for op in ops if "chain" in (op.op_id or "")]
	assert not chain_ops


#============================================
def test_render_exocyclic_3_collinear():
	_, ops = _render("ARLRRDM", "furanose", "alpha")
	line1 = _line_by_id(ops, "C4_up_chain1_connector")
	line2 = _line_by_id(ops, "C4_up_chain2_connector")
	line3 = _line_by_id(ops, "C4_up_chain3_connector")
	d1 = haworth_renderer._normalize_vector(line1.p2[0] - line1.p1[0], line1.p2[1] - line1.p1[1])
	d2 = haworth_renderer._normalize_vector(line2.p2[0] - line2.p1[0], line2.p2[1] - line2.p1[1])
	d3 = haworth_renderer._normalize_vector(line3.p2[0] - line3.p1[0], line3.p2[1] - line3.p1[1])
	assert d1[0] == pytest.approx(d2[0], rel=1e-3)
	assert d1[1] == pytest.approx(d2[1], rel=1e-3)
	assert d1[0] == pytest.approx(d3[0], rel=1e-3)
	assert d1[1] == pytest.approx(d3[1], rel=1e-3)


#============================================
def test_show_hydrogens_default_true():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	h_labels = [op for op in _texts(ops) if op.text == "H"]
	assert len(h_labels) > 0


#============================================
def test_show_hydrogens_false_no_h_labels():
	_, ops = _render("ARLRDM", "pyranose", "alpha", show_hydrogens=False)
	h_labels = [op for op in _texts(ops) if op.text == "H"]
	assert len(h_labels) == 0


#============================================
def test_show_hydrogens_false_no_h_connectors():
	spec, ops = _render("ARLRDM", "pyranose", "alpha", show_hydrogens=False)
	# C1_up is "H" for alpha glucose - its connector should be absent
	h_connector_ids = [
		op.op_id for op in _lines(ops)
		if op.op_id and op.op_id.endswith("_connector")
	]
	# For alpha-D-glucopyranose: C1_up=H, C2_up=H, C3_down=H, C4_up=H, C5_down=H
	for carbon, direction in ((1, "up"), (2, "up"), (3, "down"), (4, "up"), (5, "down")):
		assert f"C{carbon}_{direction}_connector" not in h_connector_ids


#============================================
def test_show_hydrogens_false_preserves_non_h():
	_, ops = _render("ARLRDM", "pyranose", "alpha", show_hydrogens=False)
	text_values = [op.text for op in _texts(ops)]
	assert "OH" in text_values
	assert "HO" in text_values
	assert "CH<sub>2</sub>OH" in text_values
	assert "O" in text_values
