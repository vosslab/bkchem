# Standard Library
import os
import sys
import xml.dom.minidom


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
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
import bkchem.classes
import bkchem.group
import bkchem.molecule
import bkchem.queryatom
import bkchem.textatom
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
def test_bkchem_cdml_vertex_tags():
	original_manager = singleton_store.Store.id_manager
	singleton_store.Store.id_manager = _DummyIdManager()
	try:
		standard = bkchem.classes.standard()
		singleton_store.Screen.dpi = 72
		paper = _DummyPaper(standard)
		mol = bkchem.molecule.molecule(paper=paper)

		atom = bkchem.atom.atom(standard=standard, xy=(0, 0), molecule=mol)
		mol.insert_atom(atom)

		group = bkchem.group.group(standard=standard, xy=(20, 0), molecule=mol)
		group.group_type = "builtin"
		group.symbol = "Me"
		mol.insert_atom(group)

		text = bkchem.textatom.textatom(standard=standard, xy=(40, 0), molecule=mol)
		text.symbol = "Label"
		mol.insert_atom(text)

		query = bkchem.queryatom.queryatom(standard=standard, xy=(60, 0), molecule=mol)
		query.set_name("R")
		mol.insert_atom(query)

		doc = xml.dom.minidom.Document()
		element = mol.get_package(doc)
		assert element.getElementsByTagName("atom")
		assert element.getElementsByTagName("group")
		assert element.getElementsByTagName("text")
		assert element.getElementsByTagName("query")
	finally:
		singleton_store.Store.id_manager = original_manager
