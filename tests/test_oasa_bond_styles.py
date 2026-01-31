"""Smoke test for OASA bond styles in SVG and PNG output."""

# Standard Library
import os
import sys

# Third Party
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "oasa"))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

# local repo modules
import oasa


DEFAULT_SMILES = "CCCCC"


#============================================
def build_molecule():
	"""Build a simple molecule with varied bond styles."""
	mol = oasa.smiles.text_to_mol(DEFAULT_SMILES, calc_coords=False)
	if not mol:
		raise ValueError("SMILES could not be parsed into a molecule.")
	oasa.coords_generator.calculate_coords(mol, force=1)
	mol.normalize_bond_length(30)
	mol.remove_unimportant_hydrogens()
	bonds = list(mol.edges)
	if len(bonds) < 4:
		raise ValueError("Not enough bonds to assign styles.")
	bonds[0].type = 'n'
	bonds[1].type = 'b'
	bonds[2].type = 'w'
	bonds[3].type = 'h'
	return mol


#============================================
def render_svg(mol, output_path):
	"""Render a molecule to SVG using svg_out."""
	from oasa import svg_out
	renderer = svg_out.svg_out()
	renderer.line_width = 2
	renderer.wedge_width = 6
	renderer.bold_line_width_multiplier = 1.2
	doc = renderer.mol_to_svg(mol)
	with open(output_path, 'wb') as handle:
		handle.write(doc.toxml('utf-8'))


#============================================
def render_png(mol, output_path):
	"""Render a molecule to PNG using cairo_out."""
	from oasa import cairo_out
	renderer = cairo_out.cairo_out(color_bonds=False, color_atoms=False)
	renderer.line_width = 2
	renderer.bold_line_width_multiplier = 1.2
	renderer.mols_to_cairo([mol], output_path, format="png")


#============================================
def test_oasa_bond_styles_svg(tmp_path):
	mol = build_molecule()
	svg_path = os.path.join(tmp_path, "oasa_bond_styles_smoke.svg")

	render_svg(mol, svg_path)
	assert os.path.isfile(svg_path)
	assert os.path.getsize(svg_path) > 0

	with open(svg_path, 'r', encoding='utf-8') as handle:
		svg_text = handle.read()
	assert "<polygon" in svg_text
	assert 'stroke-linecap="butt"' in svg_text
	assert 'stroke-width="2.4"' in svg_text


#============================================
def test_oasa_bond_styles_png(tmp_path):
	if not oasa.CAIRO_AVAILABLE:
		pytest.skip("Cairo backend not available.")
	mol = build_molecule()
	png_path = os.path.join(tmp_path, "oasa_bond_styles_smoke.png")
	render_png(mol, png_path)
	assert os.path.isfile(png_path)
	assert os.path.getsize(png_path) > 0
