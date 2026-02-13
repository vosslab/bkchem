"""Phase 4 Haworth fixture checklist and geometry-contract gates."""

# Standard Library
import math
import re
import statistics

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
import oasa
from oasa import haworth_renderer
from oasa import render_geometry
from oasa import render_ops
from oasa import render_out


LATTICE_ANGLES = tuple(float(angle) for angle in range(0, 360, 30))
LATTICE_TOLERANCE_DEG = 1e-6


CHECKLIST_CASES = (
	("ARDM", "furanose", "alpha", "D-Erythrose"),
	("ARRDM", "furanose", "beta", "D-Ribose"),
	("ARRDM", "pyranose", "alpha", "D-Ribose"),
	("ALLDM", "furanose", "beta", "D-Lyxose"),
	("ALLDM", "pyranose", "alpha", "D-Lyxose"),
	("ARRRDM", "furanose", "alpha", "D-Allose"),
	("ARRRDM", "pyranose", "alpha", "D-Allose"),
	("ARRLDM", "furanose", "alpha", "D-Gulose"),
	("MKRDM", "furanose", "alpha", "D-Ribulose"),
	("ARRLLd", "pyranose", "alpha", "L-Rhamnose"),
	("ARLLDc", "pyranose", "alpha", "D-Galacturonic Acid"),
)


#============================================
def _render_ops(code: str, ring_type: str, anomeric: str) -> list:
	return haworth_renderer.render_from_code(
		code=code,
		ring_type=ring_type,
		anomeric=anomeric,
		show_hydrogens=False,
	)


#============================================
def _line_by_id(ops: list, op_id: str) -> render_ops.LineOp:
	for op in ops:
		if isinstance(op, render_ops.LineOp) and op.op_id == op_id:
			return op
	raise AssertionError(f"Missing line op_id={op_id!r}")


#============================================
def _text_by_id(ops: list, op_id: str) -> render_ops.TextOp:
	for op in ops:
		if isinstance(op, render_ops.TextOp) and op.op_id == op_id:
			return op
	raise AssertionError(f"Missing text op_id={op_id!r}")


#============================================
def _line_length(line: render_ops.LineOp) -> float:
	return math.hypot(line.p2[0] - line.p1[0], line.p2[1] - line.p1[1])


#============================================
def _angle_degrees(line: render_ops.LineOp) -> float:
	return math.degrees(math.atan2(line.p2[1] - line.p1[1], line.p2[0] - line.p1[0])) % 360.0


#============================================
def _nearest_lattice_error(angle_degrees: float) -> float:
	return min(
		abs(((angle_degrees - lattice_angle + 180.0) % 360.0) - 180.0)
		for lattice_angle in LATTICE_ANGLES
	)


#============================================
def _assert_lattice_angle(line: render_ops.LineOp, tol_deg: float = LATTICE_TOLERANCE_DEG) -> None:
	angle = _angle_degrees(line)
	error = _nearest_lattice_error(angle)
	assert error <= tol_deg, (
		f"{line.op_id} angle={angle:.3f}deg not within lattice tolerance "
		f"{tol_deg:.3f}deg (error={error:.3f}deg)"
	)


#============================================
def _assert_straight_bond(ops: list, connector_id: str, min_length: float = 1e-6) -> render_ops.LineOp:
	line = _line_by_id(ops, connector_id)
	assert _line_length(line) > min_length, f"{connector_id} must not be zero-length"
	for op in ops:
		if not isinstance(op, render_ops.LineOp):
			continue
		other_id = op.op_id or ""
		assert not other_id.startswith(connector_id + "_hatch"), (
			f"{connector_id} must be straight (no hatch segments)"
		)
	return line


#============================================
def _assert_connector_length_tracks_ring_band(
		ops: list,
		connector_id: str,
		min_ratio: float = 0.64,
		max_ratio: float = 1.85) -> render_ops.LineOp:
	"""Assert one connector length remains in a broad ring-relative band."""
	line = _line_by_id(ops, connector_id)
	baseline_lengths = []
	ring_connector_pattern = re.compile(r"^C\d+_(up|down)_connector$")
	for op in ops:
		if not isinstance(op, render_ops.LineOp):
			continue
		op_id = op.op_id or ""
		if op_id == connector_id:
			continue
		if not ring_connector_pattern.match(op_id):
			continue
		baseline_lengths.append(_line_length(op))
	assert baseline_lengths, f"{connector_id} requires peer ring connectors for baseline band"
	baseline = statistics.median(baseline_lengths)
	ratio = _line_length(line) / baseline
	assert min_ratio <= ratio <= max_ratio, (
		f"{connector_id} length ratio {ratio:.3f} outside ring-relative band "
		f"[{min_ratio:.3f}, {max_ratio:.3f}]"
	)
	return line


#============================================
def _assert_connector_contract(
		ops: list,
		label_id: str,
		connector_id: str,
		attach_atom: str | None = None,
		attach_element: str | None = None,
		attach_site: str | None = None) -> None:
	label = _text_by_id(ops, label_id)
	line = _line_by_id(ops, connector_id)
	contract = render_geometry.label_attach_contract_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		line_width=line.width,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		chain_attach_site="core_center",
		font_name=label.font_name,
	)
	assert render_geometry._point_in_attach_target_closed(
		line.p2,
		contract.endpoint_target,
		epsilon=1e-6,
	), f"{connector_id} endpoint must land in runtime endpoint target"
	assert render_geometry.validate_attachment_paint(
		line_start=line.p1,
		line_end=line.p2,
		line_width=line.width,
		forbidden_regions=[contract.full_target],
		allowed_regions=[contract.allowed_target],
		epsilon=0.5,
	), f"{connector_id} paint must remain legal under runtime contract"


#============================================
@pytest.mark.parametrize(("code", "ring_type", "anomeric", "name"), CHECKLIST_CASES)
def test_phase4_checklist_cases_pass_strict_validation(code, ring_type, anomeric, name):
	ops = _render_ops(code, ring_type, anomeric)
	haworth_renderer.strict_validate_ops(
		ops=ops,
		context=f"phase4_checklist_{name}_{code}_{ring_type}_{anomeric}",
		epsilon=0.5,
	)


#============================================
def test_phase4_ardm_furanose_alpha_all_three_oh_groups():
	ops = _render_ops("ARDM", "furanose", "alpha")
	for prefix in ("C1_down", "C2_down", "C3_down"):
		label = _text_by_id(ops, f"{prefix}_label")
		assert re.sub(r"<[^>]+>", "", label.text) in ("OH", "HO")
		_assert_connector_contract(ops, f"{prefix}_label", f"{prefix}_connector")
		_assert_straight_bond(ops, f"{prefix}_connector")


#============================================
def test_phase4_arrdm_furanose_beta_upward_ch2oh_group():
	ops = _render_ops("ARRDM", "furanose", "beta")
	label = _text_by_id(ops, "C4_up_label")
	assert re.sub(r"<[^>]+>", "", label.text) == "CH2OH"
	_assert_connector_contract(
		ops,
		"C4_up_label",
		"C4_up_connector",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)
	_assert_straight_bond(ops, "C4_up_connector")


#============================================
def test_phase4_arrdm_pyranose_alpha_all_downward_oh_groups():
	ops = _render_ops("ARRDM", "pyranose", "alpha")
	for prefix in ("C1_down", "C2_down", "C3_down", "C4_down"):
		label = _text_by_id(ops, f"{prefix}_label")
		assert re.sub(r"<[^>]+>", "", label.text) in ("OH", "HO")
		_assert_connector_contract(ops, f"{prefix}_label", f"{prefix}_connector")
		_assert_straight_bond(ops, f"{prefix}_connector")


#============================================
def test_phase4_alldm_furanose_beta_internal_oh_groups():
	ops = _render_ops("ALLDM", "furanose", "beta")
	for prefix in ("C2_up", "C3_up"):
		label = _text_by_id(ops, f"{prefix}_label")
		assert re.sub(r"<[^>]+>", "", label.text) in ("OH", "HO")
		_assert_connector_contract(ops, f"{prefix}_label", f"{prefix}_connector")
		_assert_straight_bond(ops, f"{prefix}_connector")


#============================================
def test_phase4_alldm_pyranose_alpha_internal_oh_groups():
	ops = _render_ops("ALLDM", "pyranose", "alpha")
	for prefix in ("C2_up", "C3_up"):
		label = _text_by_id(ops, f"{prefix}_label")
		assert re.sub(r"<[^>]+>", "", label.text) in ("OH", "HO")
		_assert_connector_contract(ops, f"{prefix}_label", f"{prefix}_connector")
		_assert_straight_bond(ops, f"{prefix}_connector")


#============================================
def test_phase4_arrrdm_furanose_alpha_two_carbon_up_left_oh_and_ch2oh():
	ops = _render_ops("ARRRDM", "furanose", "alpha")
	_assert_connector_contract(ops, "C4_up_chain1_oh_label", "C4_up_chain1_oh_connector")
	_assert_connector_contract(
		ops,
		"C4_up_chain2_label",
		"C4_up_chain2_connector",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)
	_assert_lattice_angle(_line_by_id(ops, "C4_up_chain1_oh_connector"))
	_assert_lattice_angle(_line_by_id(ops, "C4_up_chain2_connector"))
	_assert_straight_bond(ops, "C4_up_chain1_connector")


#============================================
def test_phase4_arrrdm_pyranose_alpha_upward_ch2oh_group():
	ops = _render_ops("ARRRDM", "pyranose", "alpha")
	label = _text_by_id(ops, "C5_up_label")
	assert re.sub(r"<[^>]+>", "", label.text) == "CH2OH"
	_assert_connector_contract(
		ops,
		"C5_up_label",
		"C5_up_connector",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)
	_assert_straight_bond(ops, "C5_up_connector")


#============================================
def test_phase4_arrldm_furanose_alpha_two_carbon_down_left_oh_and_ch2oh():
	ops = _render_ops("ARRLDM", "furanose", "alpha")
	_assert_connector_contract(ops, "C4_down_chain1_oh_label", "C4_down_chain1_oh_connector")
	_assert_connector_contract(
		ops,
		"C4_down_chain2_label",
		"C4_down_chain2_connector",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)
	_assert_lattice_angle(_line_by_id(ops, "C4_down_chain1_oh_connector"))
	_assert_lattice_angle(_line_by_id(ops, "C4_down_chain2_connector"))
	_assert_straight_bond(ops, "C4_down_chain1_connector")


#============================================
def test_phase4_mkrdm_furanose_alpha_right_side_ch2oh_and_oh_bonds_straight():
	ops = _render_ops("MKRDM", "furanose", "alpha")
	_assert_connector_contract(
		ops,
		"C2_up_label",
		"C2_up_connector",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)
	_assert_connector_contract(ops, "C2_down_label", "C2_down_connector")
	_assert_straight_bond(ops, "C2_up_connector")
	_assert_straight_bond(ops, "C2_down_connector")


#============================================
def test_phase4_arrlld_pyranose_alpha_internal_ch3_straight_length_and_c_alignment():
	ops = _render_ops("ARRLLd", "pyranose", "alpha")
	label = _text_by_id(ops, "C5_down_label")
	assert re.sub(r"<[^>]+>", "", label.text) == "CH3"
	line = _assert_straight_bond(ops, "C5_down_connector")
	_assert_connector_length_tracks_ring_band(ops, "C5_down_connector")
	assert _line_length(line) >= 6.0
	_assert_connector_contract(
		ops,
		"C5_down_label",
		"C5_down_connector",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)


#============================================
def test_phase4_arlldc_pyranose_alpha_upleft_cooh_straight_length_and_c_alignment():
	ops = _render_ops("ARLLDc", "pyranose", "alpha")
	label = _text_by_id(ops, "C5_up_label")
	assert re.sub(r"<[^>]+>", "", label.text) == "COOH"
	line = _assert_straight_bond(ops, "C5_up_connector")
	_assert_connector_length_tracks_ring_band(ops, "C5_up_connector")
	assert _line_length(line) >= 6.0
	_assert_connector_contract(
		ops,
		"C5_up_label",
		"C5_up_connector",
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
	)


#============================================
@pytest.mark.parametrize(("code", "ring_type", "anomeric", "_name"), CHECKLIST_CASES)
def test_phase4_global_ring_connected_bonds_are_straight(code, ring_type, anomeric, _name):
	ops = _render_ops(code, ring_type, anomeric)
	pattern = re.compile(r"^C\d+_(up|down)(_chain1)?_connector$")
	checked = 0
	for op in ops:
		if not isinstance(op, render_ops.LineOp):
			continue
		op_id = op.op_id or ""
		if not pattern.match(op_id):
			continue
		_assert_straight_bond(ops, op_id)
		checked += 1
	assert checked > 0


#============================================
@pytest.mark.parametrize(("code", "ring_type", "anomeric", "_name"), CHECKLIST_CASES)
def test_phase4_global_off_ring_bonds_follow_lattice(code, ring_type, anomeric, _name):
	ops = _render_ops(code, ring_type, anomeric)
	checked = 0
	for op in ops:
		if not isinstance(op, render_ops.LineOp):
			continue
		op_id = op.op_id or ""
		if "_chain" not in op_id:
			continue
		if not op_id.endswith("_connector"):
			continue
		if op_id.endswith("_chain1_connector"):
			continue
		_assert_lattice_angle(op)
		checked += 1
	if code in ("ARRRDM", "ARRLDM") and ring_type == "furanose":
		assert checked >= 2


#============================================
def _build_regular_hexagon_molecule() -> oasa.molecule:
	"""Build one non-Haworth six-member ring on canonical 60-degree lattice."""
	molecule = oasa.molecule()
	radius = 24.0
	vertices = []
	for angle in (0.0, 60.0, 120.0, 180.0, 240.0, 300.0):
		radians = math.radians(angle)
		vertex = oasa.atom(symbol="C")
		vertex.x = radius * math.cos(radians)
		vertex.y = radius * math.sin(radians)
		molecule.add_vertex(vertex)
		vertices.append(vertex)
	for index in range(len(vertices)):
		start = vertices[index]
		end = vertices[(index + 1) % len(vertices)]
		bond = oasa.bond(order=1, type="n")
		bond.vertices = (start, end)
		molecule.add_edge(start, end, bond)
	return molecule


#============================================
def test_phase4_non_haworth_ring_bonds_follow_lattice():
	"""Non-Haworth ring bonds follow canonical 60-degree lattice angles."""
	molecule = _build_regular_hexagon_molecule()
	ops, _width, _height = render_out._render_ops_for_mol(
		molecule,
		margin=4.0,
		scaling=1.0,
		options={"show_carbon_symbol": False},
	)
	checked = 0
	for op in ops:
		if not isinstance(op, render_ops.LineOp):
			continue
		_assert_lattice_angle(op, tol_deg=1.0)
		checked += 1
	assert checked >= 6
