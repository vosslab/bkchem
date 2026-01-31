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
PRINTER_BOND_TYPES = [
	('n', None, '#000000'),
	('b', None, '#239e2d'),
	('w', None, '#d94a2d'),
	('h', None, '#2d5fd9'),
	('l', None, '#8a2dd9'),
	('r', None, '#d92d8a'),
	('q', None, '#d9a12d'),
	('s', 'sine', '#2dd9c1'),
	('s', 'half-circle', '#2d8ad9'),
	('s', 'box', '#2dd94a'),
	('s', 'triangle', '#d92d2d'),
]


#============================================
@pytest.fixture
def output_dir(request, tmp_path):
	if request.config.getoption("save"):
		return os.getcwd()
	return tmp_path


#============================================
def output_path(output_dir, filename):
	return os.path.join(str(output_dir), filename)


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
def build_printer_self_test():
	"""Build a molecule with all bond styles and colors for smoke testing."""
	mol = oasa.molecule()
	spacing_x = 60
	spacing_y = 45
	segment = 40
	cols = 3
	for idx, (bond_type, wavy_style, color) in enumerate(PRINTER_BOND_TYPES):
		row = idx // cols
		col = idx % cols
		x = col * spacing_x
		y = row * spacing_y
		a1 = oasa.atom(symbol='C')
		a2 = oasa.atom(symbol='C')
		a1.x = x
		a1.y = y
		a2.x = x + segment
		a2.y = y
		mol.add_vertex(a1)
		mol.add_vertex(a2)
		bond = oasa.bond(order=1, type=bond_type)
		if wavy_style:
			bond.wavy_style = wavy_style
			bond.properties_['wavy_style'] = wavy_style
		if color:
			bond.line_color = color
			bond.properties_['line_color'] = color
		bond.vertices = (a1, a2)
		mol.add_edge(a1, a2, bond)
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
def test_oasa_bond_styles_svg(output_dir):
	mol = build_molecule()
	svg_path = output_path(output_dir, "oasa_bond_styles_smoke.svg")

	render_svg(mol, svg_path)
	assert os.path.isfile(svg_path)
	assert os.path.getsize(svg_path) > 0

	with open(svg_path, 'r', encoding='utf-8') as handle:
		svg_text = handle.read()
	assert "<polygon" in svg_text
	assert 'stroke-linecap="butt"' in svg_text
	assert 'stroke-width="2.4"' in svg_text


#============================================
def test_oasa_bond_styles_png(output_dir):
	if not oasa.CAIRO_AVAILABLE:
		pytest.skip("Cairo backend not available.")
	mol = build_molecule()
	png_path = output_path(output_dir, "oasa_bond_styles_smoke.png")
	render_png(mol, png_path)
	assert os.path.isfile(png_path)
	assert os.path.getsize(png_path) > 0


#============================================
def test_oasa_bond_styles_printer_svg(output_dir):
	mol = build_printer_self_test()
	svg_path = output_path(output_dir, "oasa_bond_styles_printer_self_test.svg")
	render_svg(mol, svg_path)
	assert os.path.isfile(svg_path)
	assert os.path.getsize(svg_path) > 0
	with open(svg_path, 'r', encoding='utf-8') as handle:
		svg_text = handle.read()
	assert "<polyline" in svg_text
	assert "#239e2d" in svg_text


#============================================
def test_oasa_bond_styles_printer_png(output_dir):
	if not oasa.CAIRO_AVAILABLE:
		pytest.skip("Cairo backend not available.")
	mol = build_printer_self_test()
	png_path = output_path(output_dir, "oasa_bond_styles_printer_self_test.png")
	render_png(mol, png_path)
	assert os.path.isfile(png_path)
	assert os.path.getsize(png_path) > 0
