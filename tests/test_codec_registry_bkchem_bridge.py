# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for codec registry usage in bkchem oasa_bridge."""

# Local repo modules
import conftest


conftest.add_bkchem_to_sys_path()
conftest.add_oasa_to_sys_path()

# local repo modules
import oasa
import oasa_bridge


class DummyCodec:
	def __init__(self):
		self.read_text_calls = []
		self.write_text_calls = []
		self.read_file_calls = []
		self.write_file_calls = []
		self.read_text_result = None
		self.read_file_result = None
		self.write_text_result = ""

	def read_text(self, text, **kwargs):
		self.read_text_calls.append((text, kwargs))
		return self.read_text_result

	def write_text(self, mol, **kwargs):
		self.write_text_calls.append((mol, kwargs))
		return self.write_text_result

	def read_file(self, file_obj, **kwargs):
		self.read_file_calls.append((file_obj, kwargs))
		return self.read_file_result

	def write_file(self, mol, file_obj, **kwargs):
		self.write_file_calls.append((mol, file_obj, kwargs))


class DummyMol:
	def __init__(self):
		self.cleaned = False

	def remove_unimportant_hydrogens(self):
		self.cleaned = True

	def is_connected(self):
		return True


class DummyDisconnectedMol:
	def __init__(self, parts):
		self._parts = parts

	def is_connected(self):
		return False

	def get_disconnected_subgraphs(self):
		return list(self._parts)


class DummyPaper:
	def __init__(self, molecules):
		self.molecules = list(molecules)


#============================================
def _make_oasa_mol():
	mol = oasa.molecule()
	a1 = oasa.atom(symbol="C")
	a2 = oasa.atom(symbol="O")
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	bond = oasa.bond(order=1, type="n")
	mol.add_edge(a1, a2, bond)
	return mol


#============================================
def test_oasa_bridge_read_smiles_uses_registry(monkeypatch):
	codec = DummyCodec()
	dummy_mol = DummyMol()
	codec.read_text_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)

	coords_calls = []
	monkeypatch.setattr(oasa.coords_generator, "calculate_coords",
						lambda mol, bond_length=1.0, force=1: coords_calls.append((mol, bond_length, force)))
	monkeypatch.setattr(oasa_bridge, "oasa_mol_to_bkchem_mol",
						lambda mol, paper: ("bkchem", mol, paper))

	result = oasa_bridge.read_smiles("C", paper="paper")
	assert result == ("bkchem", dummy_mol, "paper")
	assert codec.read_text_calls[0][0] == "C"
	assert coords_calls


#============================================
def test_oasa_bridge_mol_to_smiles_uses_registry(monkeypatch):
	codec = DummyCodec()
	codec.write_text_result = "CC"
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)

	dummy_mol = DummyMol()
	monkeypatch.setattr(oasa_bridge, "bkchem_mol_to_oasa_mol",
						lambda mol: dummy_mol)

	result = oasa_bridge.mol_to_smiles("bkchem_mol")
	assert result == "CC"
	assert dummy_mol.cleaned
	assert codec.write_text_calls


#============================================
def test_oasa_bridge_read_inchi_uses_registry(monkeypatch):
	codec = DummyCodec()
	dummy_mol = DummyMol()
	codec.read_text_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(oasa_bridge, "oasa_mol_to_bkchem_mol",
						lambda mol, paper: ("bkchem", mol, paper))

	result = oasa_bridge.read_inchi("InChI=1S/CH4/h1H4", paper="paper")
	assert result == ("bkchem", dummy_mol, "paper")
	assert codec.read_text_calls
	text, kwargs = codec.read_text_calls[0]
	assert text.startswith("InChI=")
	assert kwargs.get("calc_coords") == 1
	assert kwargs.get("include_hydrogens") is False


#============================================
def test_oasa_bridge_read_molfile_uses_registry(monkeypatch):
	codec = DummyCodec()
	dummy_mol = DummyMol()
	codec.read_file_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(oasa_bridge, "oasa_mol_to_bkchem_mol",
						lambda mol, paper: ("bkchem", mol, paper))

	result = oasa_bridge.read_molfile("file", paper="paper")
	assert result == [("bkchem", dummy_mol, "paper")]
	assert codec.read_file_calls


#============================================
def test_oasa_bridge_read_molfile_disconnected(monkeypatch):
	codec = DummyCodec()
	part_a = DummyMol()
	part_b = DummyMol()
	dummy_mol = DummyDisconnectedMol([part_a, part_b])
	codec.read_file_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(oasa_bridge, "oasa_mol_to_bkchem_mol",
						lambda mol, paper: ("bkchem", mol, paper))

	result = oasa_bridge.read_molfile("file", paper="paper")
	assert result == [("bkchem", part_a, "paper"), ("bkchem", part_b, "paper")]


#============================================
def test_oasa_bridge_write_molfile_uses_registry(monkeypatch):
	codec = DummyCodec()
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)

	dummy_mol = DummyMol()
	monkeypatch.setattr(oasa_bridge, "bkchem_mol_to_oasa_mol",
						lambda mol: dummy_mol)

	oasa_bridge.write_molfile("bkchem_mol", "file")
	assert codec.write_file_calls
	assert codec.write_file_calls[0][0] is dummy_mol


#============================================
def test_oasa_bridge_read_cml_uses_registry(monkeypatch):
	codec = DummyCodec()
	part_a = DummyMol()
	part_b = DummyMol()
	codec.read_file_result = DummyDisconnectedMol([part_a, part_b])
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(
		oasa_bridge,
		"oasa_mol_to_bkchem_mol",
		lambda mol, paper: ("bkchem", mol, paper),
	)

	result = oasa_bridge.read_cml("file", paper="paper", version=2)
	assert result == [("bkchem", part_a, "paper"), ("bkchem", part_b, "paper")]
	assert codec.read_file_calls


#============================================
def test_oasa_bridge_write_cml_from_paper_uses_registry(monkeypatch):
	codec = DummyCodec()
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)

	first = _make_oasa_mol()
	second = _make_oasa_mol()
	monkeypatch.setattr(
		oasa_bridge,
		"bkchem_mol_to_oasa_mol",
		lambda mol: first if mol == "one" else second,
	)
	paper = DummyPaper(["one", "two"])
	oasa_bridge.write_cml_from_paper(paper, "file", version=1)
	assert codec.write_file_calls


#============================================
def test_oasa_bridge_read_cdxml_uses_registry(monkeypatch):
	codec = DummyCodec()
	dummy_mol = DummyMol()
	codec.read_file_result = dummy_mol
	monkeypatch.setattr(oasa.codec_registry, "get_codec", lambda name: codec)
	monkeypatch.setattr(
		oasa_bridge,
		"oasa_mol_to_bkchem_mol",
		lambda mol, paper: ("bkchem", mol, paper),
	)

	result = oasa_bridge.read_cdxml("file", paper="paper")
	assert result == [("bkchem", dummy_mol, "paper")]
	assert codec.read_file_calls
