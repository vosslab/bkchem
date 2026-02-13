"""Tests for measurelib.lcf_optical module."""

# Standard Library
import os
import sys

# Third Party
import pytest

# Local
import conftest
_tools_dir = os.path.join(conftest.repo_root(), "tools")
if _tools_dir not in sys.path:
	sys.path.insert(0, _tools_dir)

from measurelib.lcf_optical import optical_center_via_isolation_render


#============================================
def test_optical_center_none_center():
	"""When center is None, the function returns (None, center_char) immediately."""
	label = {"text": "OH", "text_display": "OH", "text_raw": "OH",
		"x": 50.0, "y": 30.0, "anchor": "start", "font_size": 12.0,
		"font_name": "sans-serif"}
	center, char = optical_center_via_isolation_render(
		label=label, center=None, center_char="O",
		svg_path="/nonexistent.svg", gate_debug={})
	assert center is None
	assert char == "O"


#============================================
def test_optical_center_none_char():
	"""When center_char is None/empty, returns the input center unchanged."""
	label = {"text": "OH"}
	input_center = (50.0, 30.0)
	center, char = optical_center_via_isolation_render(
		label=label, center=input_center, center_char=None,
		svg_path="/nonexistent.svg", gate_debug={})
	assert center == input_center
	assert char is None


#============================================
def test_optical_center_empty_char():
	"""When center_char is empty string, returns the input center unchanged."""
	label = {"text": "OH"}
	input_center = (50.0, 30.0)
	center, char = optical_center_via_isolation_render(
		label=label, center=input_center, center_char="",
		svg_path="/nonexistent.svg", gate_debug={})
	assert center == input_center
	assert char == ""


#============================================
def test_optical_center_both_none():
	"""When both center and center_char are None, returns (None, None)."""
	label = {"text": "OH"}
	center, char = optical_center_via_isolation_render(
		label=label, center=None, center_char=None,
		svg_path="/nonexistent.svg", gate_debug={})
	assert center is None
	assert char is None


#============================================
def test_optical_center_return_types():
	"""Return value is always a 2-tuple."""
	label = {"text": "OH"}
	result = optical_center_via_isolation_render(
		label=label, center=None, center_char=None,
		svg_path="/nonexistent.svg", gate_debug={})
	assert isinstance(result, tuple)
	assert len(result) == 2


#============================================
def test_optical_center_gate_debug_unmodified_on_early_return():
	"""gate_debug dict is not modified when center is None (early return)."""
	label = {"text": "OH"}
	gate_debug = {}
	optical_center_via_isolation_render(
		label=label, center=None, center_char="O",
		svg_path="/nonexistent.svg", gate_debug=gate_debug)
	assert gate_debug == {}


#============================================
def test_optical_center_nonexistent_svg_raises():
	"""When SVG file does not exist and center+char are given, parsing will fail."""
	label = {"text": "OH"}
	with pytest.raises(Exception):
		optical_center_via_isolation_render(
			label=label, center=(50.0, 30.0), center_char="O",
			svg_path="/nonexistent_path_12345.svg", gate_debug={})
