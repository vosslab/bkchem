"""Tests for bond vertex canonicalization."""

# Standard Library
import os
import sys


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "oasa"))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

# local repo modules
import oasa
from oasa import bond_semantics


#============================================
def _make_atoms(y_front=10.0, y_back=0.0):
	"""Create two atoms with deterministic coordinates."""
	a1 = oasa.atom(symbol="C")
	a2 = oasa.atom(symbol="C")
	a1.x = 0.0
	a1.y = y_front
	a2.x = 0.0
	a2.y = y_back
	return a1, a2


#============================================
def test_canonicalize_wedge_vertices_by_geometry():
	a1, a2 = _make_atoms()
	b = oasa.bond(order=1, type="w")
	b.set_vertices((a1, a2))
	bond_semantics.canonicalize_bond_vertices(b)
	assert b.vertices[1] is a1


#============================================
def test_canonicalize_hashed_vertices_by_geometry():
	a1, a2 = _make_atoms()
	b = oasa.bond(order=1, type="h")
	b.set_vertices((a1, a2))
	bond_semantics.canonicalize_bond_vertices(b)
	assert b.vertices[1] is a1


#============================================
def test_canonicalize_respects_front_vertices():
	a1, a2 = _make_atoms(y_front=5.0, y_back=10.0)
	b = oasa.bond(order=1, type="w")
	b.set_vertices((a1, a2))
	layout_ctx = {
		"front_vertices": {a1},
	}
	bond_semantics.canonicalize_bond_vertices(b, layout_ctx=layout_ctx)
	assert b.vertices[1] is a1


#============================================
def test_canonicalize_skips_non_wedge_types():
	a1, a2 = _make_atoms()
	b = oasa.bond(order=1, type="n")
	b.set_vertices((a1, a2))
	bond_semantics.canonicalize_bond_vertices(b)
	assert b.vertices[0] is a1
	assert b.vertices[1] is a2


#============================================
def test_parse_cdml_bond_type_normalizes_legacy():
	bond_type, order, legacy = bond_semantics.parse_cdml_bond_type("l1")
	assert bond_type == "h"
	assert order == 1
	assert legacy == "l"
