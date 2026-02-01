"""Smoke tests for biomolecule templates."""

# Standard Library
import os
import sys


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BKCHEM_DIR = os.path.join(ROOT_DIR, "packages", "bkchem")
BKCHEM_PKG_DIR = os.path.join(BKCHEM_DIR, "bkchem")


#============================================
def _ensure_sys_path():
	if BKCHEM_DIR not in sys.path:
		sys.path.insert(0, BKCHEM_DIR)
	if BKCHEM_PKG_DIR not in sys.path:
		sys.path.append(BKCHEM_PKG_DIR)


#============================================
def test_biomolecule_template_files_have_anchors():
	_ensure_sys_path()

	import safe_xml
	import template_catalog

	entries = template_catalog.scan_template_dirs(
		template_catalog.discover_biomolecule_template_dirs()
	)
	assert entries

	for entry in entries:
		doc = safe_xml.parse_dom_from_file(entry.path)
		molecules = doc.getElementsByTagName('molecule')
		assert molecules
		for mol in molecules:
			atoms = {atom.getAttribute('id') for atom in mol.getElementsByTagName('atom')}
			assert atoms
			bonds = mol.getElementsByTagName('bond')
			assert bonds
			templates = mol.getElementsByTagName('template')
			assert templates
			template = templates[0]
			t_atom = template.getAttribute('atom')
			bond_first = template.getAttribute('bond_first')
			bond_second = template.getAttribute('bond_second')
			assert t_atom in atoms
			assert bond_first in atoms
			assert bond_second in atoms
