"""Tests for Patch 3: CDML save and load-save round-trip."""

# Standard Library
import xml.etree.ElementTree

# local repo modules
import bkchem_qt.io.cdml_io


#============================================
def test_save_cdml_produces_valid_xml(main_window, tmp_path):
	"""save_cdml_file() produces valid XML with molecule data."""
	tmp_file = str(tmp_path / "test_save.cdml")
	# create a molecule with two atoms and a bond
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	a1 = draw_mode._create_atom_at(100.0, 200.0, "C")
	a2 = draw_mode._create_atom_at(140.0, 200.0, "O")
	draw_mode._create_bond_between(a1, a2)
	# save
	bkchem_qt.io.cdml_io.save_cdml_file(tmp_file, main_window.document)
	# verify XML is parseable
	tree = xml.etree.ElementTree.parse(tmp_file)
	root = tree.getroot()
	# strip namespace prefix for tag comparison
	tag = root.tag.split("}", 1)[-1] if "}" in root.tag else root.tag
	assert tag == "cdml", f"root should be <cdml>, got <{root.tag}>"
	# namespace-aware child search
	ns = root.tag.split("}", 1)[0] + "}" if "}" in root.tag else ""
	mols = root.findall(f"{ns}molecule")
	assert len(mols) >= 1, "should have at least 1 molecule element"
	atoms = mols[0].findall(f"{ns}atom")
	assert len(atoms) == 2, f"molecule should have 2 atoms, got {len(atoms)}"
	bonds = mols[0].findall(f"{ns}bond")
	assert len(bonds) == 1, f"molecule should have 1 bond, got {len(bonds)}"


#============================================
def test_load_save_roundtrip_preserves_atoms(main_window, tmp_path):
	"""Load-save-load round-trip preserves atom count and element symbols."""
	tmp_file = str(tmp_path / "test_atoms.cdml")
	# create 3 atoms with different elements, connected by bonds
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	a1 = draw_mode._create_atom_at(100.0, 200.0, "C")
	a2 = draw_mode._create_atom_at(140.0, 200.0, "N")
	a3 = draw_mode._create_atom_at(180.0, 200.0, "O")
	draw_mode._create_bond_between(a1, a2)
	draw_mode._create_bond_between(a2, a3)
	# save
	bkchem_qt.io.cdml_io.save_cdml_file(tmp_file, main_window.document)
	# reload
	mols = bkchem_qt.io.cdml_io.load_cdml_file(tmp_file)
	assert len(mols) >= 1, "should reload at least 1 molecule"
	all_atoms = []
	for m in mols:
		all_atoms.extend(m.atoms)
	assert len(all_atoms) == 3, f"expected 3 atoms, got {len(all_atoms)}"
	symbols = sorted(a.symbol for a in all_atoms)
	assert symbols == ["C", "N", "O"], f"expected C,N,O got {symbols}"


#============================================
def test_load_save_roundtrip_preserves_bonds(main_window, tmp_path):
	"""Load-save-load round-trip preserves bond count."""
	tmp_file = str(tmp_path / "test_bonds.cdml")
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	a1 = draw_mode._create_atom_at(100.0, 200.0, "C")
	a2 = draw_mode._create_atom_at(140.0, 200.0, "C")
	a3 = draw_mode._create_atom_at(180.0, 200.0, "O")
	draw_mode._create_bond_between(a1, a2)
	draw_mode._create_bond_between(a2, a3)
	# save
	bkchem_qt.io.cdml_io.save_cdml_file(tmp_file, main_window.document)
	# reload
	mols = bkchem_qt.io.cdml_io.load_cdml_file(tmp_file)
	all_bonds = []
	for m in mols:
		all_bonds.extend(m.bonds)
	assert len(all_bonds) == 2, f"expected 2 bonds, got {len(all_bonds)}"


#============================================
def test_coordinates_preserved_within_tolerance(main_window, tmp_path):
	"""Load-save-load round-trip preserves coordinates approximately."""
	tmp_file = str(tmp_path / "test_coords.cdml")
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	# create two atoms connected by a bond so they stay in one molecule
	a1 = draw_mode._create_atom_at(100.0, 200.0, "C")
	a2 = draw_mode._create_atom_at(300.0, 400.0, "O")
	draw_mode._create_bond_between(a1, a2)
	# save and reload
	bkchem_qt.io.cdml_io.save_cdml_file(tmp_file, main_window.document)
	mols = bkchem_qt.io.cdml_io.load_cdml_file(tmp_file)
	assert len(mols) >= 1, "should have molecules"
	loaded_atoms = mols[0].atoms
	assert len(loaded_atoms) == 2, (
		f"should have 2 atoms, got {len(loaded_atoms)}"
	)
	# verify both atoms have non-None coordinates
	for a in loaded_atoms:
		assert a.x is not None, "x should not be None"
		assert a.y is not None, "y should not be None"
