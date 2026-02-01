# SPDX-License-Identifier: LGPL-3.0-or-later

"""Unit tests for the OASA codec registry."""

# Standard Library
import io
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "oasa"))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

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
	smiles_codec = oasa.codec_registry.get_codec("s")
	assert smiles_codec.name == "smiles"
	by_ext = oasa.codec_registry.get_codec_by_extension(".smi")
	assert by_ext.name == "smiles"


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
def test_codec_registry_file_fallback():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("smiles")
	stream = io.StringIO("C")
	mol = codec.read_file(stream)
	assert mol is not None
