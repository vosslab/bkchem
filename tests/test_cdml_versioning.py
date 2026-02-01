"""Smoke test for CDML version transforms."""

# Standard Library
import os
import sys
from defusedxml import minidom


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "bkchem"))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)
BKCHEM_MODULE_DIR = os.path.join(ROOT_DIR, "bkchem")
if BKCHEM_MODULE_DIR not in sys.path:
	sys.path.append(BKCHEM_MODULE_DIR)

# local repo modules
import CDML_versions
import config


#============================================
def build_cdml(version):
	doc = minidom.parseString(f'<cdml version="{version}"></cdml>')
	return doc.documentElement


#============================================
def test_cdml_transform_legacy_to_current():
	dom = build_cdml("0.16")
	assert CDML_versions.transform_dom_to_version(dom, config.current_CDML_version) == 1


#============================================
def test_cdml_transform_old_to_current():
	dom = build_cdml("0.15")
	assert CDML_versions.transform_dom_to_version(dom, config.current_CDML_version) == 1


#============================================
def test_cdml_transform_legacy_fixture():
	fixture_path = os.path.join(
		os.path.dirname(__file__),
		"fixtures",
		"cdml",
		"legacy_v0.11.cdml",
	)
	with open(fixture_path, "r", encoding="utf-8") as handle:
		text = handle.read()
	doc = minidom.parseString(text)
	dom = doc.documentElement
	assert CDML_versions.transform_dom_to_version(dom, config.current_CDML_version) == 1
