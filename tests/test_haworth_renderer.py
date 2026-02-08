"""Unit tests for Haworth schematic render_ops output."""

# Standard Library
import math

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

import oasa.haworth as haworth
import oasa.haworth_renderer as haworth_renderer
import oasa.haworth_spec as haworth_spec
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
	assert len(ring_polys) == 5


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
	text_values = [op.text for op in _texts(ops)]
	assert "CHOH" in text_values
	assert "CH<sub>2</sub>OH" in text_values


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
		assert line.p2[0] == pytest.approx(line.p1[0], abs=1e-6)


#============================================
def test_render_furanose_side_connectors_vertical():
	_, ops = _render("MKLRDM", "furanose", "beta")
	for op_id in ("C2_up_connector", "C2_down_connector", "C5_up_connector", "C5_down_connector"):
		line = _line_by_id(ops, op_id)
		assert line.p2[0] == pytest.approx(line.p1[0], abs=1e-6)


#============================================
def test_render_left_anchor_hydroxyl_uses_ho_order():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert _text_by_id(ops, "C3_up_label").text == "HO"
	assert _text_by_id(ops, "C4_down_label").text == "HO"


#============================================
def test_render_right_anchor_hydroxyl_keeps_oh_order():
	_, ops = _render("ARLRDM", "pyranose", "alpha")
	assert _text_by_id(ops, "C1_down_label").text == "OH"
	assert _text_by_id(ops, "C2_down_label").text == "OH"


#============================================
def test_render_bbox_sub_tags():
	assert haworth_renderer._visible_text_length("CH<sub>2</sub>OH") == 5


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
	assert oh_label.text == "HO"
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
	assert _line_length(line) == pytest.approx(40.0 * 0.4 * 1.5, rel=0.05)


#============================================
def test_sub_length_default_single_wide():
	_, ops = _render("ARLRDM", "pyranose", "alpha", bond_length=40.0)
	line = _line_by_id(ops, "C1_down_connector")
	assert _line_length(line) == pytest.approx(40.0 * 0.4, rel=0.05)


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
	spec, ops = _render("ARLRDM", "furanose", "alpha", bond_length=30.0)
	_ = spec
	line1 = _line_by_id(ops, "C4_up_chain1_connector")
	line2 = _line_by_id(ops, "C4_up_chain2_connector")
	v1 = (line1.p2[0] - line1.p1[0], line1.p2[1] - line1.p1[1])
	v2 = (line2.p2[0] - line2.p1[0], line2.p2[1] - line2.p1[1])
	n1 = haworth_renderer._normalize_vector(v1[0], v1[1])
	n2 = haworth_renderer._normalize_vector(v2[0], v2[1])
	assert n1[0] == pytest.approx(n2[0], rel=1e-3)
	assert n1[1] == pytest.approx(n2[1], rel=1e-3)


#============================================
def test_render_exocyclic_2_chain_labels():
	_, ops = _render("ARLRDM", "furanose", "alpha")
	l1 = _text_by_id(ops, "C4_up_chain1_label")
	l2 = _text_by_id(ops, "C4_up_chain2_label")
	assert l1.text == "CHOH"
	assert l2.text == "CH<sub>2</sub>OH"
	assert _distance((l2.x, l2.y), (l1.x, l1.y)) > 5.0


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
