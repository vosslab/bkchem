"""Smoke tests for Haworth renderer ops and SVG serialization."""

# Standard Library
import math
import pathlib
import sys
from xml.dom import minidom as xml_minidom

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()
sys.path.insert(0, conftest.tests_path("fixtures"))

import oasa.dom_extensions as dom_extensions
import oasa.haworth_renderer as haworth_renderer
import oasa.haworth_spec as haworth_spec
import oasa.render_geometry as render_geometry
import oasa.render_ops as render_ops
import oasa.sugar_code as sugar_code
import oasa.svg_out as svg_out
from neurotiker_archive_mapping import all_mappable_entries


#============================================
def _build_ops(code: str, ring_type: str, anomeric: str, **render_kwargs) -> list:
	parsed = sugar_code.parse(code)
	spec = haworth_spec.generate(parsed, ring_type=ring_type, anomeric=anomeric)
	return haworth_renderer.render(spec, **render_kwargs)


#============================================
def _ops_to_svg_text(ops: list, width: int = 220, height: int = 220) -> str:
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
			("width", str(width)),
			("height", str(height)),
			("viewBox", f"0 0 {width} {height}"),
		),
	)
	render_ops.ops_to_svg(svg, ops)
	return svg_out.pretty_print_svg(doc.toxml("utf-8"))


#============================================
def _assert_ops_well_formed(ops: list, context: str) -> None:
	"""Validate basic render-op invariants for stability."""
	op_ids = [op.op_id for op in ops if getattr(op, "op_id", None)]
	assert len(op_ids) == len(set(op_ids)), f"Duplicate op_id values in {context}"
	for op in ops:
		if isinstance(op, render_ops.TextOp):
			assert op.text, f"Empty text op in {context}"
			assert op.font_size > 0.0, f"Non-positive text size in {context}"
			points = [(op.x, op.y)]
		elif isinstance(op, render_ops.LineOp):
			dx = op.p2[0] - op.p1[0]
			dy = op.p2[1] - op.p1[1]
			assert math.hypot(dx, dy) > 0.0, f"Zero-length line in {context}: {op.op_id}"
			points = [op.p1, op.p2]
		elif isinstance(op, render_ops.PolygonOp):
			assert len(op.points) >= 3, f"Degenerate polygon in {context}: {op.op_id}"
			points = list(op.points)
		else:
			points = []
		for x, y in points:
			assert math.isfinite(x) and math.isfinite(y), f"Non-finite point in {context}: {op.op_id}"


#============================================
def _label_target(op: render_ops.TextOp) -> render_geometry.AttachTarget:
	return render_geometry.label_target_from_text_origin(
		text_x=op.x,
		text_y=op.y,
		text=op.text,
		anchor=op.anchor,
		font_size=op.font_size,
		font_name=op.font_name,
	)


#============================================
def _segment_intersects_box_closed(
		p1: tuple[float, float],
		p2: tuple[float, float],
		box: tuple[float, float, float, float],
		tol: float = 1e-9) -> bool:
	x1, y1, x2, y2 = box
	dx = p2[0] - p1[0]
	dy = p2[1] - p1[1]
	p_values = (-dx, dx, -dy, dy)
	q_values = (
		p1[0] - x1,
		x2 - p1[0],
		p1[1] - y1,
		y2 - p1[1],
	)
	u1 = 0.0
	u2 = 1.0
	for p_value, q_value in zip(p_values, q_values):
		if abs(p_value) <= tol:
			if q_value < 0.0:
				return False
			continue
		t_value = q_value / p_value
		if p_value < 0.0:
			u1 = max(u1, t_value)
		else:
			u2 = min(u2, t_value)
		if u1 > u2:
			return False
	return True


#============================================
def _segment_intersects_box_interior(
		p1: tuple[float, float],
		p2: tuple[float, float],
		box: tuple[float, float, float, float],
		epsilon: float = 1e-3) -> bool:
	x1, y1, x2, y2 = box
	inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
	if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
		return False
	return _segment_intersects_box_closed(p1, p2, inner_box)


#============================================
def _point_to_segment_distance(
		point: tuple[float, float],
		seg_start: tuple[float, float],
		seg_end: tuple[float, float]) -> float:
	px, py = point
	ax, ay = seg_start
	bx, by = seg_end
	abx = bx - ax
	aby = by - ay
	ab2 = (abx * abx) + (aby * aby)
	if ab2 <= 1e-12:
		return math.hypot(px - ax, py - ay)
	t_value = ((px - ax) * abx + (py - ay) * aby) / ab2
	t_value = max(0.0, min(1.0, t_value))
	closest_x = ax + (abx * t_value)
	closest_y = ay + (aby * t_value)
	return math.hypot(px - closest_x, py - closest_y)


#============================================
def _segments_intersect(
		a1: tuple[float, float],
		a2: tuple[float, float],
		b1: tuple[float, float],
		b2: tuple[float, float],
		tol: float = 1e-12) -> bool:
	def _cross(p0, p1, p2):
		return ((p1[0] - p0[0]) * (p2[1] - p0[1])) - ((p1[1] - p0[1]) * (p2[0] - p0[0]))

	def _on_segment(p0, p1, p2):
		return (
			min(p0[0], p1[0]) - tol <= p2[0] <= max(p0[0], p1[0]) + tol
			and min(p0[1], p1[1]) - tol <= p2[1] <= max(p0[1], p1[1]) + tol
		)

	d1 = _cross(a1, a2, b1)
	d2 = _cross(a1, a2, b2)
	d3 = _cross(b1, b2, a1)
	d4 = _cross(b1, b2, a2)
	if ((d1 > tol and d2 < -tol) or (d1 < -tol and d2 > tol)) and (
			(d3 > tol and d4 < -tol) or (d3 < -tol and d4 > tol)):
		return True
	if abs(d1) <= tol and _on_segment(a1, a2, b1):
		return True
	if abs(d2) <= tol and _on_segment(a1, a2, b2):
		return True
	if abs(d3) <= tol and _on_segment(b1, b2, a1):
		return True
	if abs(d4) <= tol and _on_segment(b1, b2, a2):
		return True
	return False


#============================================
def _segment_segment_distance(
		a1: tuple[float, float],
		a2: tuple[float, float],
		b1: tuple[float, float],
		b2: tuple[float, float]) -> float:
	if _segments_intersect(a1, a2, b1, b2):
		return 0.0
	return min(
		_point_to_segment_distance(a1, b1, b2),
		_point_to_segment_distance(a2, b1, b2),
		_point_to_segment_distance(b1, a1, a2),
		_point_to_segment_distance(b2, a1, a2),
	)


#============================================
def _segment_distance_to_box_interior(
		p1: tuple[float, float],
		p2: tuple[float, float],
		box: tuple[float, float, float, float],
		epsilon: float = 1e-3) -> float:
	x1, y1, x2, y2 = box
	inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
	if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
		return float("inf")
	if _segment_intersects_box_closed(p1, p2, inner_box):
		return 0.0
	corners = [
		(inner_box[0], inner_box[1]),
		(inner_box[2], inner_box[1]),
		(inner_box[2], inner_box[3]),
		(inner_box[0], inner_box[3]),
	]
	edges = [
		(corners[0], corners[1]),
		(corners[1], corners[2]),
		(corners[2], corners[3]),
		(corners[3], corners[0]),
	]
	return min(_segment_segment_distance(p1, p2, edge_start, edge_end) for edge_start, edge_end in edges)


#============================================
def _point_in_box(point: tuple[float, float], box: tuple[float, float, float, float]) -> bool:
	return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


#============================================
def _label_inner_box(
		label_box: tuple[float, float, float, float],
		epsilon: float = 1e-3) -> tuple[float, float, float, float] | None:
	x1, y1, x2, y2 = label_box
	inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
	if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
		return None
	return inner_box


#============================================
def _is_hydroxyl_label(text: str) -> bool:
	return text in ("OH", "HO")


#============================================
def _hydroxyl_half_token_targets(
		text: str,
		label_target: render_geometry.AttachTarget) -> tuple[
			render_geometry.AttachTarget,
			render_geometry.AttachTarget]:
	"""Return deterministic first/last token targets for OH/HO when spans collapse."""
	x1, y1, x2, y2 = label_target.box
	split_x = (x1 + x2) * 0.5
	first_target = render_geometry.make_box_target((x1, y1, split_x, y2))
	last_target = render_geometry.make_box_target((split_x, y1, x2, y2))
	if text == "OH":
		return first_target, last_target
	return first_target, last_target


#============================================
def _own_hydroxyl_connector_overlaps_non_oxygen_area(
		line: render_ops.LineOp,
		label: render_ops.TextOp,
		label_target: render_geometry.AttachTarget) -> bool:
	inner_box = _label_inner_box(label_target.box)
	if inner_box is None:
		return False
	oxygen_center = haworth_renderer._hydroxyl_oxygen_center(
		text=label.text,
		anchor=label.anchor,
		text_x=label.x,
		text_y=label.y,
		font_size=label.font_size,
	)
	if oxygen_center is None:
		# If oxygen center cannot be computed, fall back to strict no-overlap.
		return _segment_distance_to_box_interior(line.p1, line.p2, label_target.box) < max(0.0, line.width * 0.5)
	oxygen_mode = "first" if label.text == "OH" else "last"
	non_oxygen_mode = "last" if label.text == "OH" else "first"
	oxygen_target = render_geometry.label_attach_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom=oxygen_mode,
		font_name=label.font_name,
	)
	non_oxygen_target = render_geometry.label_attach_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom=non_oxygen_mode,
		font_name=label.font_name,
	)
	if oxygen_target.box == non_oxygen_target.box:
		first_target, last_target = _hydroxyl_half_token_targets(label.text, label_target)
		oxygen_target = first_target if oxygen_mode == "first" else last_target
		non_oxygen_target = last_target if oxygen_mode == "first" else first_target
	line_radius = max(0.0, float(getattr(line, "width", 0.0) or 0.0) * 0.5)
	if line_radius <= 0.0:
		return _segment_intersects_box_interior(line.p1, line.p2, non_oxygen_target.box)
	min_distance = _segment_distance_to_box_interior(line.p1, line.p2, non_oxygen_target.box)
	return min_distance < line_radius


#============================================
def _line_overlaps_label_interior(
		line: render_ops.LineOp,
		label_box: tuple[float, float, float, float]) -> bool:
	line_radius = max(0.0, float(getattr(line, "width", 0.0) or 0.0) * 0.5)
	if line_radius <= 0.0:
		return _segment_intersects_box_interior(line.p1, line.p2, label_box)
	min_distance = _segment_distance_to_box_interior(line.p1, line.p2, label_box)
	return min_distance < line_radius


#============================================
def _connector_target_for_label(
		label: render_ops.TextOp,
		connector: render_ops.LineOp | None = None) -> render_geometry.AttachTarget | None:
	"""Resolve own-connector target with runtime connector attach-site policy."""
	return haworth_renderer._attach_target_for_connector(label, connector)


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
def _assert_no_oxygen_mask_ops(ops: list, context: str) -> None:
	for op in ops:
		assert (getattr(op, "op_id", None) or "") != "oxygen_mask", (
			f"Unexpected oxygen_mask op in {context}"
		)


#============================================
def _assert_oxygen_adjacent_ring_edges_clear_oxygen_label(
		ops: list,
		ring_type: str,
		context: str) -> None:
	oxygen_label = None
	for op in ops:
		if isinstance(op, render_ops.TextOp) and (op.op_id or "") == "oxygen_label":
			oxygen_label = op
			break
	assert oxygen_label is not None, f"Missing oxygen_label in {context}"
	oxygen_inner = _label_inner_box(_label_target(oxygen_label).box, epsilon=0.2)
	if oxygen_inner is None:
		return
	ring_cfg = haworth_renderer.RING_RENDER_CONFIG[ring_type]
	ring_size = ring_cfg["ring_size"]
	oxygen_index = ring_cfg["oxygen_index"]
	adjacent_edge_indices = {oxygen_index, (oxygen_index - 1) % ring_size}
	adjacent_polygons = []
	for edge_index in adjacent_edge_indices:
		base_id = f"ring_edge_{edge_index}"
		for op in ops:
			if not isinstance(op, render_ops.PolygonOp):
				continue
			op_id = op.op_id or ""
			if op_id == base_id or op_id.startswith(base_id + "_"):
				adjacent_polygons.append(op)
	assert adjacent_polygons, f"No oxygen-adjacent ring polygons in {context}"
	for polygon in adjacent_polygons:
		assert not _box_overlaps_polygon(oxygen_inner, polygon.points), (
			f"Oxygen-adjacent ring polygon overlaps oxygen label interior in {context}: {polygon.op_id}"
		)


#============================================
def _assert_no_bond_label_overlap(ops: list, context: str) -> None:
	labels = [op for op in ops if isinstance(op, render_ops.TextOp)]
	lines = [op for op in ops if isinstance(op, render_ops.LineOp)]
	for label in labels:
		label_target = _label_target(label)
		label_box = label_target.box
		label_id = getattr(label, "op_id", None)
		own_connector_id = None
		if label_id and label_id.endswith("_label"):
			own_connector_id = label_id.replace("_label", "_connector")
		for line in lines:
			line_id = line.op_id or "<no-line-id>"
			label_name = label_id or "<no-label-id>"
			is_own_connector = bool(own_connector_id and line.op_id == own_connector_id)
			is_own_hatch = bool(
				own_connector_id
				and line.op_id
				and line.op_id.startswith(f"{own_connector_id}_hatch")
			)
			if is_own_connector or is_own_hatch:
				if _is_hydroxyl_label(label.text):
					if _line_overlaps_label_interior(line, label_box):
						non_oxygen_overlap = _own_hydroxyl_connector_overlaps_non_oxygen_area(
							line,
							label,
							label_target,
						)
						if non_oxygen_overlap:
							raise AssertionError(
								(
									f"Bond/label overlap in {context}: line={line_id} "
									f"label={label_name} own_hydroxyl_non_oxygen={int(non_oxygen_overlap)}"
								)
							)
					continue
				own_attach_target = _connector_target_for_label(label, line)
				if own_attach_target is None:
					own_attach_target = label_target
				ok = render_geometry.validate_attachment_paint(
					line_start=line.p1,
					line_end=line.p2,
					line_width=float(getattr(line, "width", 0.0) or 0.0),
					forbidden_regions=[label_target],
					allowed_regions=[own_attach_target],
					epsilon=0.5,
				)
				if not ok:
					raise AssertionError(
						f"Bond/label overlap in {context}: line={line_id} label={label_name}"
					)
				continue
			overlaps = _line_overlaps_label_interior(line, label_box)
			if overlaps:
				raise AssertionError(
					f"Bond/label overlap in {context}: line={line_id} label={label_name}"
				)


#============================================
def test_haworth_renderer_smoke_matrix(tmp_path):
	cases = [
		("ARLRDM", "pyranose"),
		("ARLRDM", "furanose"),
		("ARRDM", "pyranose"),
		("ARRDM", "furanose"),
		("ARDM", "furanose"),
		("MKLRDM", "pyranose"),
		("MKLRDM", "furanose"),
		("AdRDM", "furanose"),
	]
	for code, ring_type in cases:
		for anomeric in ("alpha", "beta"):
			for show_hydrogens in (True, False):
				ops = _build_ops(
					code,
					ring_type,
					anomeric,
					show_hydrogens=show_hydrogens,
				)
				context = f"{code}_{ring_type}_{anomeric}_showH{int(show_hydrogens)}"
				_assert_ops_well_formed(ops, context)
				_assert_no_bond_label_overlap(ops, context)
				_assert_no_oxygen_mask_ops(ops, context)
				_assert_oxygen_adjacent_ring_edges_clear_oxygen_label(ops, ring_type, context)
				assert any(isinstance(op, render_ops.PolygonOp) for op in ops)
				assert any(isinstance(op, render_ops.TextOp) for op in ops)
				svg_text = _ops_to_svg_text(ops)
				output_path = tmp_path / f"{context}.svg"
				with open(output_path, "w", encoding="utf-8") as handle:
					handle.write(svg_text)
				assert output_path.is_file()
				assert output_path.stat().st_size > 0
				with open(output_path, "r", encoding="utf-8") as handle:
					file_text = handle.read()
				assert "<svg" in file_text

	ops = _build_ops("ARLRDM", "pyranose", "alpha", bg_color="#f0f0f0")
	_assert_ops_well_formed(ops, "ARLRDM_pyranose_alpha_bg")
	_assert_no_oxygen_mask_ops(ops, "ARLRDM_pyranose_alpha_bg")
	_assert_oxygen_adjacent_ring_edges_clear_oxygen_label(
		ops,
		"pyranose",
		"ARLRDM_pyranose_alpha_bg",
	)
	assert any(isinstance(op, render_ops.PolygonOp) for op in ops)
	assert any(isinstance(op, render_ops.TextOp) for op in ops)
	svg_text = _ops_to_svg_text(ops)
	output_path = tmp_path / "ARLRDM_pyranose_alpha_bg.svg"
	with open(output_path, "w", encoding="utf-8") as handle:
		handle.write(svg_text)
	assert output_path.is_file()
	assert output_path.stat().st_size > 0
	with open(output_path, "r", encoding="utf-8") as handle:
		file_text = handle.read()
	assert "<svg" in file_text


#============================================
# Full archive matrix: all 78 mappable sugars from NEUROtiker archive
#============================================

_ARCHIVE_CASES = [
	(code, ring_type, anomeric, filename)
	for code, ring_type, anomeric, filename, _name in all_mappable_entries()
]

_ARCHIVE_IDS = [
	f"{code}_{ring_type}_{anomeric}"
	for code, ring_type, anomeric, _filename, _name in all_mappable_entries()
]


@pytest.mark.parametrize(
	"code,ring_type,anomeric,archive_filename",
	_ARCHIVE_CASES,
	ids=_ARCHIVE_IDS,
)
def test_archive_full_matrix(tmp_path, code, ring_type, anomeric, archive_filename):
	"""Render every mappable sugar from the NEUROtiker archive and verify output."""
	for show_hydrogens in (True, False):
		ops = _build_ops(code, ring_type, anomeric, show_hydrogens=show_hydrogens)
		context = f"{code}_{ring_type}_{anomeric}_showH{int(show_hydrogens)}"
		_assert_ops_well_formed(ops, context)
		_assert_no_bond_label_overlap(ops, context)
		_assert_no_oxygen_mask_ops(ops, context)
		_assert_oxygen_adjacent_ring_edges_clear_oxygen_label(ops, ring_type, context)
		assert any(isinstance(op, render_ops.PolygonOp) for op in ops), (
			f"No PolygonOps for {context}"
		)
		assert any(isinstance(op, render_ops.TextOp) for op in ops), (
			f"No TextOps for {context}"
		)
		svg_text = _ops_to_svg_text(ops)
		output_path = tmp_path / f"{context}.svg"
		with open(output_path, "w", encoding="utf-8") as handle:
			handle.write(svg_text)
		assert output_path.is_file()
		assert output_path.stat().st_size > 0
		with open(output_path, "r", encoding="utf-8") as handle:
			file_text = handle.read()
		assert "<svg" in file_text


#============================================
@pytest.mark.parametrize("code", ["ARLLDM", "ALRLDM", "ALLLDM"])
def test_furanose_left_two_carbon_tail_parity_smoke(code):
	"""Phase B.1 parity smoke: left-tail class keeps hashed HO branch semantics."""
	ops = _build_ops(code, "furanose", "alpha", show_hydrogens=False)
	context = f"{code}_furanose_alpha_left_tail_parity"
	_assert_ops_well_formed(ops, context)
	_assert_no_bond_label_overlap(ops, context)
	ho_label = next(
		op for op in ops
		if isinstance(op, render_ops.TextOp) and op.op_id == "C4_down_chain1_oh_label"
	)
	ch2_label = next(
		op for op in ops
		if isinstance(op, render_ops.TextOp) and op.op_id == "C4_down_chain2_label"
	)
	ho_branch = next(
		op for op in ops
		if isinstance(op, render_ops.LineOp) and op.op_id == "C4_down_chain1_oh_connector"
	)
	ch2_branch = next(
		op for op in ops
		if isinstance(op, render_ops.LineOp) and op.op_id == "C4_down_chain2_connector"
	)
	assert ho_label.text == "HO"
	assert ch2_label.text == "HOH<sub>2</sub>C"
	assert any(
		isinstance(op, render_ops.LineOp) and (op.op_id or "").startswith("C4_down_chain1_oh_connector_hatch")
		for op in ops
	)
	assert ho_branch.p2[0] < ho_branch.p1[0]
	assert ch2_branch.p2[0] < ch2_branch.p1[0]
	assert ho_branch.p2[1] < ho_branch.p1[1]
	assert ch2_branch.p2[1] > ch2_branch.p1[1]


#============================================
def test_archive_matrix_ch3_labels_are_subscripted():
	"""Ensure no generated Haworth label emits plain CH3 text."""
	for code, ring_type, anomeric, _filename, _name in all_mappable_entries():
		ops = _build_ops(code, ring_type, anomeric, show_hydrogens=False)
		plain_ch3 = [
			op.op_id for op in ops
			if isinstance(op, render_ops.TextOp) and op.text == "CH3"
		]
		assert not plain_ch3, (
			f"Plain CH3 label(s) found in {code}_{ring_type}_{anomeric}: {plain_ch3}"
		)


#============================================
def test_archive_matrix_chain2_connectors_end_on_selected_carbon_token():
	"""Ensure CH2OH/HOH2C chain2 connectors terminate on attach_element C target."""
	for code, ring_type, anomeric, _filename, _name in all_mappable_entries():
		ops = _build_ops(code, ring_type, anomeric, show_hydrogens=False)
		line_by_id = {
			op.op_id: op
			for op in ops
			if isinstance(op, render_ops.LineOp) and op.op_id
		}
		for label in [op for op in ops if isinstance(op, render_ops.TextOp)]:
			label_id = label.op_id or ""
			if not label_id.endswith("_chain2_label"):
				continue
			connector_id = label_id.replace("_label", "_connector")
			connector = line_by_id.get(connector_id)
			assert connector is not None, (
				f"Missing connector {connector_id} for {code}_{ring_type}_{anomeric}"
			)
			attach_target = render_geometry.label_attach_target_from_text_origin(
				text_x=label.x,
				text_y=label.y,
				text=label.text,
				anchor=label.anchor,
				font_size=label.font_size,
				attach_atom="first",
				attach_element="C",
				attach_site="core_center",
				font_name=label.font_name,
			)
			assert _point_in_box(connector.p2, attach_target.box), (
				f"{code}_{ring_type}_{anomeric} {connector_id} endpoint {connector.p2} "
				f"outside C-target {attach_target.box}"
			)


#============================================
_HYDROXYL_OVERLAP_CASES = [
	("ARLRDM", "pyranose", "alpha"),
	("ARDM", "furanose", "alpha"),
]


@pytest.mark.parametrize(
	"code,ring_type,anomeric",
	_HYDROXYL_OVERLAP_CASES,
	ids=[f"{code}_{ring_type}_{anomeric}" for code, ring_type, anomeric in _HYDROXYL_OVERLAP_CASES],
)
def test_archive_hydroxyl_own_connector_overlap_is_detected(code, ring_type, anomeric):
	"""Ensure the gate catches own-connector hydroxyl overlaps in archive-style output."""
	ops = _build_ops(code, ring_type, anomeric, show_hydrogens=False)
	hydroxyl_label = None
	hydroxyl_line = None
	for label in [op for op in ops if isinstance(op, render_ops.TextOp)]:
		label_id = label.op_id or ""
		if not label_id.endswith("_label"):
			continue
		if not _is_hydroxyl_label(label.text):
			continue
		connector_id = label_id.replace("_label", "_connector")
		for line in [candidate for candidate in ops if isinstance(candidate, render_ops.LineOp)]:
			if line.op_id == connector_id:
				hydroxyl_label = label
				hydroxyl_line = line
				break
		if hydroxyl_line is not None:
			break
	assert hydroxyl_label is not None
	assert hydroxyl_line is not None
	# Force an overlap by driving the owning connector endpoint into label interior.
	non_oxygen_mode = "last" if hydroxyl_label.text == "OH" else "first"
	non_oxygen_target = render_geometry.label_attach_target_from_text_origin(
		text_x=hydroxyl_label.x,
		text_y=hydroxyl_label.y,
		text=hydroxyl_label.text,
		anchor=hydroxyl_label.anchor,
		font_size=hydroxyl_label.font_size,
		attach_atom=non_oxygen_mode,
		font_name=hydroxyl_label.font_name,
	)
	oxygen_mode = "first" if hydroxyl_label.text == "OH" else "last"
	oxygen_target = render_geometry.label_attach_target_from_text_origin(
		text_x=hydroxyl_label.x,
		text_y=hydroxyl_label.y,
		text=hydroxyl_label.text,
		anchor=hydroxyl_label.anchor,
		font_size=hydroxyl_label.font_size,
		attach_atom=oxygen_mode,
		font_name=hydroxyl_label.font_name,
	)
	if non_oxygen_target.box == oxygen_target.box:
		first_target, last_target = _hydroxyl_half_token_targets(
			hydroxyl_label.text,
			_label_target(hydroxyl_label),
		)
		non_oxygen_target = last_target if hydroxyl_label.text == "OH" else first_target
	overlap_point = (
		(non_oxygen_target.box[0] + non_oxygen_target.box[2]) * 0.5,
		(non_oxygen_target.box[1] + non_oxygen_target.box[3]) * 0.5,
	)
	replacement = render_ops.LineOp(
		p1=hydroxyl_line.p1,
		p2=overlap_point,
		width=hydroxyl_line.width,
		cap=hydroxyl_line.cap,
		join=hydroxyl_line.join,
		color=hydroxyl_line.color,
		z=hydroxyl_line.z,
		op_id=hydroxyl_line.op_id,
	)
	mutated_ops = [replacement if op is hydroxyl_line else op for op in ops]
	case_id = f"{code}_{ring_type}_{anomeric}_forced_overlap"
	with pytest.raises(
			AssertionError,
			match=rf"Bond/label overlap in {case_id}: line={hydroxyl_line.op_id} label={hydroxyl_label.op_id}"):
		_assert_no_bond_label_overlap(mutated_ops, case_id)


#============================================
@pytest.mark.xfail(reason="allowed_target composite includes full box; overlap not detected (pre-existing)")
def test_archive_matrix_strict_validator_rejects_induced_hydroxyl_overlap():
	"""Ensure archive_matrix strict gate hard-fails on visible own-label overlap."""
	import tools.archive_matrix_summary as archive_matrix_summary

	ops = _build_ops("ARLRDM", "pyranose", "alpha", show_hydrogens=False)
	hydroxyl_label = None
	hydroxyl_line = None
	for label in [op for op in ops if isinstance(op, render_ops.TextOp)]:
		label_id = label.op_id or ""
		if not label_id.endswith("_label"):
			continue
		if not _is_hydroxyl_label(label.text):
			continue
		connector_id = label_id.replace("_label", "_connector")
		for line in [candidate for candidate in ops if isinstance(candidate, render_ops.LineOp)]:
			if line.op_id == connector_id:
				hydroxyl_label = label
				hydroxyl_line = line
				break
		if hydroxyl_line is not None:
			break
	assert hydroxyl_label is not None
	assert hydroxyl_line is not None
	non_oxygen_mode = "last" if hydroxyl_label.text == "OH" else "first"
	non_oxygen_target = render_geometry.label_attach_target_from_text_origin(
		text_x=hydroxyl_label.x,
		text_y=hydroxyl_label.y,
		text=hydroxyl_label.text,
		anchor=hydroxyl_label.anchor,
		font_size=hydroxyl_label.font_size,
		attach_atom=non_oxygen_mode,
		font_name=hydroxyl_label.font_name,
	)
	oxygen_mode = "first" if hydroxyl_label.text == "OH" else "last"
	oxygen_target = render_geometry.label_attach_target_from_text_origin(
		text_x=hydroxyl_label.x,
		text_y=hydroxyl_label.y,
		text=hydroxyl_label.text,
		anchor=hydroxyl_label.anchor,
		font_size=hydroxyl_label.font_size,
		attach_atom=oxygen_mode,
		font_name=hydroxyl_label.font_name,
	)
	if non_oxygen_target.box == oxygen_target.box:
		first_target, last_target = _hydroxyl_half_token_targets(
			hydroxyl_label.text,
			_label_target(hydroxyl_label),
		)
		non_oxygen_target = last_target if hydroxyl_label.text == "OH" else first_target
	overlap_point = (
		(non_oxygen_target.box[0] + non_oxygen_target.box[2]) * 0.5,
		(non_oxygen_target.box[1] + non_oxygen_target.box[3]) * 0.5,
	)
	replacement = render_ops.LineOp(
		p1=hydroxyl_line.p1,
		p2=overlap_point,
		width=hydroxyl_line.width,
		cap=hydroxyl_line.cap,
		join=hydroxyl_line.join,
		color=hydroxyl_line.color,
		z=hydroxyl_line.z,
		op_id=hydroxyl_line.op_id,
	)
	mutated_ops = [replacement if op is hydroxyl_line else op for op in ops]
	repo_root = pathlib.Path(conftest.repo_root())
	case_id = "ARLRDM_pyranose_alpha_forced_overlap"
	with pytest.raises(
			RuntimeError,
			match=rf"Strict overlap failure in {case_id}: bond/label line={hydroxyl_line.op_id} label={hydroxyl_label.op_id}"):
		archive_matrix_summary._validate_ops_strict(repo_root, render_ops, mutated_ops, case_id)
