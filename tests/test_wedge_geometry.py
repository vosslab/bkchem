"""Tests for rounded wedge geometry helpers."""

# Standard Library
import math
import os
import sys

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "oasa"))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

# local repo modules
from oasa import wedge_geometry


#============================================
def test_horizontal_wedge_corners():
	geom = wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (10.0, 0.0), 4.0, 0.0)
	assert geom["narrow_left"] == (0.0, 0.0)
	assert geom["narrow_right"] == (0.0, 0.0)
	assert geom["wide_left"] == (10.0, 2.0)
	assert geom["wide_right"] == (10.0, -2.0)
	assert geom["corner_radius"] == pytest.approx(1.0)
	assert geom["length"] == 10.0


#============================================
def test_vertical_wedge_corners():
	geom = wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (0.0, 10.0), 4.0, 0.0)
	assert geom["wide_left"] == (-2.0, 10.0)
	assert geom["wide_right"] == (2.0, 10.0)
	assert geom["angle"] == pytest.approx(math.pi / 2.0)


#============================================
def test_wedge_area_invariance():
	length = 10.0
	narrow_width = 0.0
	wide_width = 4.0
	expected = wedge_geometry._compute_wedge_area(length, narrow_width, wide_width)
	for angle in (0, 45, 90, 135, 180, 225, 270, 315):
		rad = math.radians(angle)
		base = (length * math.cos(rad), length * math.sin(rad))
		geom = wedge_geometry.rounded_wedge_geometry((0.0, 0.0), base, wide_width, narrow_width)
		assert geom["area"] == pytest.approx(expected, rel=1e-6)


#============================================
def test_wedge_path_commands():
	geom = wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (10.0, 0.0), 4.0, 0.0)
	commands = geom["path_commands"]
	assert commands[0][0] == "M"
	assert commands[1][0] == "L"
	assert commands[2][0] == "ARC"
	assert commands[-1][0] == "Z"
	assert sum(1 for cmd, _payload in commands if cmd == "ARC") == 2


#============================================
def test_wedge_path_without_rounding():
	geom = wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (10.0, 0.0), 4.0, 0.0, corner_radius=0.0)
	commands = geom["path_commands"]
	assert sum(1 for cmd, _payload in commands if cmd == "ARC") == 0


#============================================
def test_wedge_input_validation():
	with pytest.raises(ValueError):
		wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (0.0, 0.0), 4.0, 0.0)
	with pytest.raises(ValueError):
		wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (1.0, 0.0), 0.0, 0.0)
	with pytest.raises(ValueError):
		wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (1.0, 0.0), 4.0, -1.0)
