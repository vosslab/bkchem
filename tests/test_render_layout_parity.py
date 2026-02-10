# SPDX-License-Identifier: LGPL-3.0-or-later

"""Render layout parity guards for Haworth and backend sink capture."""

# Standard Library
import io
import math

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
import oasa
from oasa import haworth
from oasa import haworth_renderer
from oasa import haworth_spec
from oasa import render_geometry
from oasa import render_ops
from oasa import render_out
from oasa import sugar_code


#============================================
def _build_ring(size, oxygen_index=None):
	mol = oasa.molecule()
	atoms = []
	for idx in range(size):
		symbol = "C"
		if oxygen_index is not None and idx == oxygen_index:
			symbol = "O"
		atom = oasa.atom(symbol=symbol)
		atom.x = float(idx) * 20.0
		atom.y = 0.0
		mol.add_vertex(atom)
		atoms.append(atom)
	for idx in range(size):
		start_atom = atoms[idx]
		end_atom = atoms[(idx + 1) % size]
		bond = oasa.bond(order=1, type="n")
		bond.vertices = (start_atom, end_atom)
		mol.add_edge(start_atom, end_atom, bond)
	return mol


#============================================
def _capture_render_out_payloads(monkeypatch, mol):
	captured = {}

	def _capture_svg(_parent, ops):
		captured["svg"] = render_ops.ops_to_json_dict(ops, round_digits=3)

	def _capture_cairo(ops, _output_target, _fmt, _width, _height, _options):
		captured["cairo"] = render_ops.ops_to_json_dict(ops, round_digits=3)

	monkeypatch.setattr(render_out.render_ops, "ops_to_svg", _capture_svg)
	monkeypatch.setattr(render_out, "_render_cairo", _capture_cairo)
	render_out.render_to_svg(mol, io.StringIO(), show_carbon_symbol=True)
	render_out.render_to_png(mol, io.BytesIO(), scaling=1.0, show_carbon_symbol=True)
	assert "svg" in captured
	assert "cairo" in captured
	return captured["svg"], captured["cairo"]


#============================================
def _count_by_kind(payload):
	counts = {
		"line": 0,
		"text": 0,
		"path": 0,
		"polygon": 0,
	}
	for entry in payload:
		kind = entry.get("kind")
		if kind in counts:
			counts[kind] += 1
	return counts


#============================================
def _build_spec(code, ring_type, anomeric):
	parsed = sugar_code.parse(code)
	return haworth_spec.generate(parsed, ring_type=ring_type, anomeric=anomeric)


#============================================
def _render_haworth_ops(code, ring_type, anomeric, **kwargs):
	spec = _build_spec(code, ring_type, anomeric)
	ops = haworth_renderer.render(spec, **kwargs)
	return spec, ops


#============================================
def _by_id(ops, op_id):
	for op in ops:
		if getattr(op, "op_id", None) == op_id:
			return op
	raise AssertionError(f"Missing op_id {op_id}")


#============================================
def _text_by_id(ops, op_id):
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.TextOp)
	return op


#============================================
def _line_by_id(ops, op_id):
	op = _by_id(ops, op_id)
	assert isinstance(op, render_ops.LineOp)
	return op


#============================================
def _point_on_box_edge(point, box, tol=1e-6):
	x_value, y_value = point
	x1, y1, x2, y2 = box
	on_x = abs(x_value - x1) <= tol or abs(x_value - x2) <= tol
	on_y = abs(y_value - y1) <= tol or abs(y_value - y2) <= tol
	in_x = (x1 - tol) <= x_value <= (x2 + tol)
	in_y = (y1 - tol) <= y_value <= (y2 + tol)
	return (on_x and in_y) or (on_y and in_x)


#============================================
def _connector_bbox_for_label(label):
	first_bbox = render_geometry.label_attach_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom="first",
	).box
	last_bbox = render_geometry.label_attach_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
		attach_atom="last",
	).box
	if first_bbox != last_bbox:
		return first_bbox
	return render_geometry.label_target_from_text_origin(
		text_x=label.x,
		text_y=label.y,
		text=label.text,
		anchor=label.anchor,
		font_size=label.font_size,
	).box


#============================================
def _hydroxyl_oxygen_center(label):
	center = haworth_renderer._hydroxyl_oxygen_center(
		text=label.text,
		anchor=label.anchor,
		text_x=label.x,
		text_y=label.y,
		font_size=label.font_size,
	)
	if center is None:
		raise AssertionError("Expected hydroxyl label with oxygen center")
	return center


#============================================
def _distance(p1, p2):
	return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


#============================================
@pytest.mark.parametrize("mode", ("pyranose", "furanose"))
def test_haworth_pipeline_payload_parity(mode, monkeypatch):
	mol = _build_ring(6 if mode == "pyranose" else 5, oxygen_index=0)
	haworth.build_haworth(mol, mode=mode)
	svg_payload, cairo_payload = _capture_render_out_payloads(monkeypatch, mol)
	assert svg_payload == cairo_payload
	assert _count_by_kind(svg_payload) == _count_by_kind(cairo_payload)


#============================================
@pytest.mark.parametrize(
	"code,ring_type,anomeric,expected_ids",
	(
		(
			"ARLRDM",
			"pyranose",
			"alpha",
			("C2_down_connector", "C2_down_label", "C3_up_connector", "C3_up_label"),
		),
		(
			"MKLRDM",
			"furanose",
			"beta",
			("C2_up_connector", "C2_up_label", "C5_up_connector", "C5_up_label"),
		),
		(
			"ALLDM",
			"furanose",
			"alpha",
			("C2_up_connector", "C2_up_label", "C3_up_connector", "C3_up_label"),
		),
	),
)
def test_haworth_parity_preserves_key_connector_and_label_ids(
		code, ring_type, anomeric, expected_ids):
	_, ops = _render_haworth_ops(code, ring_type, anomeric, show_hydrogens=False)
	op_ids = {op.op_id for op in ops if getattr(op, "op_id", None)}
	for op_id in expected_ids:
		assert op_id in op_ids


#============================================
@pytest.mark.parametrize(
	"code,ring_type,anomeric",
	(
		("ARLRDM", "pyranose", "alpha"),
		("MKLRDM", "furanose", "beta"),
		("ALLDM", "furanose", "alpha"),
	),
)
def test_haworth_side_slot_hydroxyl_connectors_remain_vertical(code, ring_type, anomeric):
	spec, ops = _render_haworth_ops(code, ring_type, anomeric, show_hydrogens=False)
	slot_map = haworth_renderer.carbon_slot_map(spec)
	if ring_type == "pyranose":
		side_slots = ("BR", "BL", "TL")
	else:
		side_slots = ("BR", "BL")
	for carbon_key, slot in slot_map.items():
		if slot not in side_slots:
			continue
		carbon = int(carbon_key[1:])
		for direction in ("up", "down"):
			label_id = f"C{carbon}_{direction}_label"
			connector_id = f"C{carbon}_{direction}_connector"
			try:
				label = _text_by_id(ops, label_id)
				connector = _line_by_id(ops, connector_id)
			except AssertionError:
				continue
			if label.text not in ("OH", "HO"):
				continue
			assert connector.p1[0] == pytest.approx(connector.p2[0], abs=1e-5)


#============================================
@pytest.mark.parametrize(
	"code,ring_type,anomeric",
	(
		("ARLRDM", "pyranose", "alpha"),
		("MKLRDM", "furanose", "beta"),
		("ALLDM", "furanose", "alpha"),
	),
)
def test_haworth_connector_endpoints_land_on_label_boundaries(code, ring_type, anomeric):
	_, ops = _render_haworth_ops(code, ring_type, anomeric, show_hydrogens=False)
	for line in ops:
		if not isinstance(line, render_ops.LineOp):
			continue
		op_id = line.op_id or ""
		if not op_id.endswith("_connector"):
			continue
		if "_chain" in op_id:
			continue
		label = _text_by_id(ops, op_id.replace("_connector", "_label"))
		if label.text in ("OH", "HO"):
			oxygen_center = _hydroxyl_oxygen_center(label)
			min_radius = haworth_renderer._hydroxyl_oxygen_radius(label.font_size) + (line.width * 0.5)
			assert _distance(line.p2, oxygen_center) >= (min_radius - 1e-3)
			continue
		label_box = _connector_bbox_for_label(label)
		assert _point_on_box_edge(line.p2, label_box, tol=1e-5)
