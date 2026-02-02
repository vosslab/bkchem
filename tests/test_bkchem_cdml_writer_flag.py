# SPDX-License-Identifier: LGPL-3.0-or-later

"""BKChem molecule serialization using the OASA CDML writer."""

# Standard Library
import os
import subprocess
import sys
import xml.dom.minidom


def _repo_root():
	output = subprocess.check_output(
		["git", "rev-parse", "--show-toplevel"],
		text=True,
	).strip()
	if not output:
		raise RuntimeError("git rev-parse --show-toplevel returned empty output")
	return output


ROOT_DIR = _repo_root()
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

BKCHEM_DIR = os.path.join(ROOT_DIR, "packages", "bkchem")
if BKCHEM_DIR not in sys.path:
	sys.path.insert(0, BKCHEM_DIR)
BKCHEM_MODULE_DIR = os.path.join(BKCHEM_DIR, "bkchem")
if BKCHEM_MODULE_DIR not in sys.path:
	sys.path.append(BKCHEM_MODULE_DIR)

OASA_DIR = os.path.join(ROOT_DIR, "packages", "oasa")
if OASA_DIR not in sys.path:
	sys.path.insert(0, OASA_DIR)
if "oasa" in sys.modules:
	del sys.modules["oasa"]

# local repo modules
import bkchem.atom
import bkchem.bond
import bkchem.classes
import bkchem.molecule
import singleton_store


class _DummyPaper(object):
	def __init__(self, standard):
		self.standard = standard

	def screen_to_real_ratio(self):
		return 1.0

	def screen_to_real_coords(self, coords):
		return coords


class _DummyIdManager(object):
	def __init__(self):
		self._counts = {}

	def generate_and_register_id(self, obj, prefix=None):
		key = prefix or "obj"
		self._counts[key] = self._counts.get(key, 0) + 1
		return "%s%d" % (key, self._counts[key])

	def is_registered_object(self, obj):
		return False

	def unregister_object(self, obj):
		return None

	def register_id(self, obj, obj_id):
		return None


#============================================
def test_bkchem_oasa_cdml_writer():
	original_manager = singleton_store.Store.id_manager
	singleton_store.Store.id_manager = _DummyIdManager()
	try:
		standard = bkchem.classes.standard()
		singleton_store.Screen.dpi = 72
		paper = _DummyPaper(standard)
		mol = bkchem.molecule.molecule(paper=paper)
		a1 = bkchem.atom.atom(standard=standard, xy=(0, 0), molecule=mol)
		a2 = bkchem.atom.atom(standard=standard, xy=(20, 0), molecule=mol)
		mol.add_vertex(a1)
		mol.add_vertex(a2)
		bond = bkchem.bond.bond(standard=standard, atoms=(a1, a2), molecule=mol, type="n", order=1)
		bond.line_width = 1.0
		bond.wedge_width = 6.0
		mol.add_edge(a1, a2, bond)

		doc = xml.dom.minidom.Document()
		element = mol.get_package(doc)
		assert element.tagName == "molecule"
		assert element.getElementsByTagName("atom")
		assert element.getElementsByTagName("bond")
	finally:
		singleton_store.Store.id_manager = original_manager
