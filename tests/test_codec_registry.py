# SPDX-License-Identifier: LGPL-3.0-or-later

"""Unit tests for the OASA codec registry."""

# Standard Library
import io
# Third Party
import pytest
# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
import oasa


#============================================
def _make_simple_mol():
	mol = oasa.molecule()
	a1 = oasa.atom(symbol="C")
	a1.x = 0.0
	a1.y = 0.0
	a2 = oasa.atom(symbol="O")
	a2.x = 1.0
	a2.y = 0.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	bond = oasa.bond(order=1, type="n")
	bond.vertices = (a1, a2)
	mol.add_edge(a1, a2, bond)
	return mol


#============================================
def test_codec_registry_defaults():
	oasa.codec_registry.reset_registry()
	codecs = oasa.codec_registry.list_codecs()
	assert "smiles" in codecs
	assert "inchi" in codecs
	assert "molfile" in codecs
	assert "cdml" in codecs
	assert "cml" in codecs
	assert "cml2" in codecs
	assert "cdxml" in codecs
	smiles_codec = oasa.codec_registry.get_codec("s")
	assert smiles_codec.name == "smiles"
	by_ext = oasa.codec_registry.get_codec_by_extension(".smi")
	assert by_ext.name == "smiles"
	by_ext = oasa.codec_registry.get_codec_by_extension(".cml")
	assert by_ext.name == "cml"
	by_ext = oasa.codec_registry.get_codec_by_extension(".cdxml")
	assert by_ext.name == "cdxml"


#============================================
def test_codec_registry_smiles_roundtrip():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("smiles")
	mol = _make_simple_mol()
	text = codec.write_text(mol)
	assert isinstance(text, str)
	assert text
	loaded = codec.read_text(text)
	assert loaded is not None


#============================================
def test_codec_registry_cdml_roundtrip():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cdml")
	mol = _make_simple_mol()
	text = codec.write_text(mol)
	assert "<cdml" in text
	loaded = codec.read_text(text)
	assert loaded is not None


#============================================
def test_codec_registry_cml_import_only():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cml")
	assert codec.writes_text is False
	assert codec.writes_files is False
	with pytest.raises(ValueError):
		codec.write_text(_make_simple_mol())
	text = (
		"<cml><molecule><atomArray>"
		"<atom id='a1' elementType='C' x2='0.0' y2='0.0'/>"
		"<atom id='a2' elementType='O' x2='1.0' y2='0.0'/>"
		"</atomArray><bondArray>"
		"<bond atomRefs2='a1 a2' order='1'/>"
		"</bondArray></molecule></cml>"
	)
	loaded = codec.read_text(text)
	assert loaded is not None
	assert len(loaded.vertices) == 2


#============================================
def test_codec_registry_cml2_import_only():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cml2")
	assert codec.writes_text is False
	assert codec.writes_files is False
	with pytest.raises(ValueError):
		codec.write_text(_make_simple_mol())
	text = (
		"<cml><molecule><atomArray>"
		"<atom id='a1' elementType='C' x2='0.0' y2='0.0'/>"
		"<atom id='a2' elementType='N' x2='1.0' y2='0.0'/>"
		"</atomArray><bondArray>"
		"<bond atomRefs2='a1 a2' order='1'/>"
		"</bondArray></molecule></cml>"
	)
	loaded = codec.read_text(text)
	assert loaded is not None
	assert len(loaded.vertices) == 2


#============================================
def test_codec_registry_cdxml_roundtrip():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("cdxml")
	mol = _make_simple_mol()
	text = codec.write_text(mol)
	assert "<CDXML" in text
	loaded = codec.read_text(text)
	assert loaded is not None
	assert len(loaded.vertices) == 2


#============================================
def test_codec_registry_file_fallback():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("smiles")
	stream = io.StringIO("C")
	mol = codec.read_file(stream)
	assert mol is not None


#============================================
def test_registry_snapshot_contains_capabilities():
	oasa.codec_registry.reset_registry()
	snapshot = oasa.codec_registry.get_registry_snapshot()
	assert "smiles" in snapshot
	assert "cml" in snapshot
	assert "cml2" in snapshot
	assert snapshot["smiles"]["writes_files"] is True
	assert snapshot["cml"]["writes_files"] is False
	assert snapshot["cml"]["writes_text"] is False
	assert snapshot["cml2"]["writes_files"] is False
	assert snapshot["cml2"]["writes_text"] is False
