# SPDX-License-Identifier: LGPL-3.0-or-later

"""Load the CDML fixture corpus in OASA."""

# Standard Library
import os
import sys

# Third Party
from defusedxml import minidom


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "oasa"))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

# local repo modules
import oasa


FIXTURES_DIR = os.path.join(
	os.path.dirname(__file__),
	"fixtures",
	"cdml",
)


#============================================
def test_cdml_fixtures_load_in_oasa():
	fixtures = [
		"benzene.cdml",
		"stereochem.cdml",
		"haworth.cdml",
		"cholesterol.cdml",
	]
	for name in fixtures:
		path = os.path.join(FIXTURES_DIR, name)
		with open(path, "r", encoding="utf-8") as handle:
			text = handle.read()
		mol = oasa.cdml.text_to_mol(text)
		assert mol is not None


#============================================
def test_cdml_embedded_svg_contains_cdml():
	path = os.path.join(FIXTURES_DIR, "embedded_cdml.svg")
	with open(path, "r", encoding="utf-8") as handle:
		text = handle.read()
	doc = minidom.parseString(text)
	cdml_nodes = doc.getElementsByTagNameNS("http://www.freesoftware.fsf.org/bkchem/cdml", "cdml")
	assert cdml_nodes
