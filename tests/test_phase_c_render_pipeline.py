# SPDX-License-Identifier: LGPL-3.0-or-later

"""Phase C coverage for render-ops and renderer parity."""

# Standard Library
import io

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
import oasa
from oasa import render_geometry
from oasa import render_ops
from oasa import render_out


#============================================
def _mol_from_smiles(smiles_text):
	mol = oasa.smiles.text_to_mol(smiles_text)
	assert mol is not None, f"Could not parse SMILES: {smiles_text}"
	oasa.coords_generator.calculate_coords(mol, bond_length=1.0, force=1)
	return mol


#============================================
def _single_bond(v1, v2, bond_type="n"):
	bond = oasa.bond(order=1, type=bond_type)
	bond.vertices = (v1, v2)
	return bond


#============================================
def test_molecule_to_ops_fixture_smiles_non_empty():
	fixtures = (
		"C1=CC=CC=C1",  # benzene
		"CC(O)C(=O)O",  # lactic acid
		"NCC(=O)O",  # glycine
		"C1CCCCC1",  # cyclohexane
		"Cn1cnc2n(C)c(=O)n(C)c(=O)c12",  # caffeine
	)
	for smiles_text in fixtures:
		mol = _mol_from_smiles(smiles_text)
		ops = render_geometry.molecule_to_ops(mol)
		assert ops, smiles_text
		assert any(isinstance(op, render_ops.LineOp) for op in ops), smiles_text


#============================================
def test_molecule_to_ops_includes_charge_and_stereo_geometry():
	mol = oasa.molecule()
	a1 = oasa.atom(symbol="N")
	a1.x = 0.0
	a1.y = 0.0
	a1.charge = 1
	a2 = oasa.atom(symbol="C")
	a2.x = 1.0
	a2.y = 0.0
	a3 = oasa.atom(symbol="C")
	a3.x = 0.3
	a3.y = 1.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	mol.add_vertex(a3)
	mol.add_edge(a1, a2, _single_bond(a1, a2, bond_type="w"))
	mol.add_edge(a1, a3, _single_bond(a1, a3, bond_type="h"))
	ops = render_geometry.molecule_to_ops(mol, style={"show_carbon_symbol": True})
	assert any(isinstance(op, render_ops.PolygonOp) for op in ops)
	assert any(isinstance(op, render_ops.TextOp) and "+" in op.text for op in ops)


#============================================
def test_svg_and_cairo_paths_receive_same_ops(monkeypatch):
	mol = _mol_from_smiles("CCO")
	captured = {}

	def _capture_svg(_parent, ops):
		captured["svg"] = render_ops.ops_to_json_dict(ops, round_digits=3)

	def _capture_cairo(ops, _output_target, _fmt, _width, _height, _options):
		captured["cairo"] = render_ops.ops_to_json_dict(ops, round_digits=3)

	monkeypatch.setattr(render_out.render_ops, "ops_to_svg", _capture_svg)
	monkeypatch.setattr(render_out, "_render_cairo", _capture_cairo)
	render_out.render_to_svg(mol, io.StringIO())
	render_out.render_to_png(mol, io.BytesIO(), scaling=1.0)
	assert "svg" in captured
	assert "cairo" in captured
	assert captured["svg"] == captured["cairo"]
