"""Tests for measurelib.violations module."""

# Standard Library
import math
import os
import sys

# Local
import conftest
_tools_dir = os.path.join(conftest.repo_root(), "tools")
if _tools_dir not in sys.path:
	sys.path.insert(0, _tools_dir)

from measurelib.violations import (
	count_bond_bond_overlaps,
	count_bond_glyph_overlaps,
	count_glyph_glyph_overlaps,
	count_hatched_thin_conflicts,
	count_lattice_angle_violations,
)


# -- helpers --

def _haworth_not_detected():
	"""Return a haworth_base_ring dict with detected=False."""
	return {
		"detected": False,
		"line_indexes": [],
		"centroid": None,
		"radius": 0.0,
	}


def _make_label(text, x, y, font_size=12.0, box=None):
	"""Return a label dict with box and svg_estimated_box."""
	if box is None:
		hw = font_size * 0.5 * max(1, len(text))
		hh = font_size * 0.5
		box = (x - hw, y - hh, x + hw, y + hh)
	return {
		"text": text, "x": x, "y": y, "font_size": font_size,
		"svg_estimated_box": box, "box": box,
	}


#============================================
def test_count_lattice_angle_violations_zero_degrees():
	"""A horizontal line (0 degrees) is on the lattice -> no violation."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 20.0, "y2": 0.0, "width": 1.0},
	]
	haworth = _haworth_not_detected()
	count, violations = count_lattice_angle_violations(lines, [0], haworth)
	assert count == 0
	assert violations == []


#============================================
def test_count_lattice_angle_violations_off_angle():
	"""A line at 17 degrees is off-lattice -> violation."""
	angle_rad = math.radians(17.0)
	length = 20.0
	lines = [
		{
			"x1": 0.0, "y1": 0.0,
			"x2": length * math.cos(angle_rad),
			"y2": length * math.sin(angle_rad),
			"width": 1.0,
		},
	]
	haworth = _haworth_not_detected()
	count, violations = count_lattice_angle_violations(lines, [0], haworth)
	assert count == 1
	assert violations[0]["line_index"] == 0
	assert violations[0]["nearest_error_degrees"] > 0.0


#============================================
def test_count_lattice_angle_violations_short_line_skipped():
	"""A line shorter than MIN_BOND_LENGTH_FOR_ANGLE_CHECK is skipped."""
	angle_rad = math.radians(17.0)
	length = 1.0  # shorter than MIN_BOND_LENGTH_FOR_ANGLE_CHECK (4.0)
	lines = [
		{
			"x1": 0.0, "y1": 0.0,
			"x2": length * math.cos(angle_rad),
			"y2": length * math.sin(angle_rad),
			"width": 1.0,
		},
	]
	haworth = _haworth_not_detected()
	count, violations = count_lattice_angle_violations(lines, [0], haworth)
	assert count == 0


#============================================
def test_count_glyph_glyph_overlaps_overlapping():
	"""Two overlapping label boxes produce one overlap."""
	labels = [
		_make_label("OH", 50.0, 30.0, box=(45.0, 20.0, 60.0, 35.0)),
		_make_label("NH", 52.0, 30.0, box=(47.0, 20.0, 62.0, 35.0)),
	]
	count, overlaps = count_glyph_glyph_overlaps(labels, [0, 1])
	assert count == 1
	assert overlaps[0]["label_index_a"] == 0
	assert overlaps[0]["label_index_b"] == 1


#============================================
def test_count_glyph_glyph_overlaps_disjoint():
	"""Two disjoint label boxes produce no overlaps."""
	labels = [
		_make_label("OH", 10.0, 10.0, box=(5.0, 5.0, 15.0, 15.0)),
		_make_label("NH", 100.0, 100.0, box=(95.0, 95.0, 105.0, 105.0)),
	]
	count, overlaps = count_glyph_glyph_overlaps(labels, [0, 1])
	assert count == 0
	assert overlaps == []


#============================================
def test_count_bond_bond_overlaps_crossing():
	"""Two crossing lines are detected as an overlap."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 20.0, "y2": 20.0, "width": 1.0},
		{"x1": 0.0, "y1": 20.0, "x2": 20.0, "y2": 0.0, "width": 1.0},
	]
	haworth = _haworth_not_detected()
	count, overlaps = count_bond_bond_overlaps(lines, [0, 1], haworth)
	assert count == 1
	assert overlaps[0]["line_index_a"] == 0
	assert overlaps[0]["line_index_b"] == 1


#============================================
def test_count_bond_bond_overlaps_parallel_no_intersection():
	"""Two parallel non-intersecting lines produce no overlaps."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 20.0, "y2": 0.0, "width": 1.0},
		{"x1": 0.0, "y1": 10.0, "x2": 20.0, "y2": 10.0, "width": 1.0},
	]
	haworth = _haworth_not_detected()
	count, overlaps = count_bond_bond_overlaps(lines, [0, 1], haworth)
	assert count == 0


#============================================
def test_count_bond_bond_overlaps_shared_endpoint_v_junction():
	"""Two lines sharing an endpoint at a V-junction are not counted."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0, "width": 1.0},
		{"x1": 10.0, "y1": 10.0, "x2": 20.0, "y2": 0.0, "width": 1.0},
	]
	haworth = _haworth_not_detected()
	count, overlaps = count_bond_bond_overlaps(lines, [0, 1], haworth)
	assert count == 0


#============================================
def test_count_hatched_thin_conflicts_with_carrier():
	"""Carrier crossing a normal bond produces a conflict."""
	# carrier: horizontal, thin, long
	carrier = {
		"x1": 0.0, "y1": 50.0, "x2": 30.0, "y2": 50.0,
		"width": 0.3, "linecap": "butt",
	}
	# hatch strokes: vertical, short, crossing carrier
	strokes = [
		{
			"x1": 5.0 * i, "y1": 48.0,
			"x2": 5.0 * i, "y2": 52.0,
			"width": 0.8, "linecap": "butt",
		}
		for i in range(1, 6)
	]
	# normal bond: diagonal crossing through carrier
	normal_bond = {
		"x1": 10.0, "y1": 30.0, "x2": 20.0, "y2": 70.0,
		"width": 1.5, "linecap": "round",
	}
	lines = [carrier] + strokes + [normal_bond]
	checked = list(range(len(lines)))
	haworth = _haworth_not_detected()
	count, conflicts, carrier_map = count_hatched_thin_conflicts(lines, checked, haworth)
	assert count >= 1
	assert 0 in carrier_map


#============================================
def test_count_hatched_thin_conflicts_no_carrier():
	"""No carrier line produces zero conflicts and empty map."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 20.0, "y2": 0.0, "width": 1.5, "linecap": "round"},
		{"x1": 0.0, "y1": 10.0, "x2": 20.0, "y2": 10.0, "width": 1.5, "linecap": "round"},
	]
	checked = list(range(len(lines)))
	haworth = _haworth_not_detected()
	count, conflicts, carrier_map = count_hatched_thin_conflicts(lines, checked, haworth)
	assert count == 0
	assert conflicts == []
	assert carrier_map == {}


#============================================
def test_count_bond_glyph_overlaps_line_through_label():
	"""Line going through a label box produces an overlap."""
	lines = [
		{"x1": 40.0, "y1": 27.5, "x2": 70.0, "y2": 27.5, "width": 1.0},
	]
	labels = [
		_make_label("OH", 50.0, 30.0, box=(45.0, 20.0, 60.0, 35.0)),
	]
	haworth = _haworth_not_detected()
	count, overlaps = count_bond_glyph_overlaps(
		lines, labels,
		checked_line_indexes=[0],
		checked_label_indexes=[0],
		aligned_connector_pairs=set(),
		haworth_base_ring=haworth,
		gap_tolerance=0.65,
	)
	assert count >= 1
	assert overlaps[0]["label_text"] == "OH"


#============================================
def test_count_bond_glyph_overlaps_line_away_from_label():
	"""Line far from a label box produces no overlap."""
	lines = [
		{"x1": 200.0, "y1": 200.0, "x2": 250.0, "y2": 200.0, "width": 1.0},
	]
	labels = [
		_make_label("OH", 50.0, 30.0, box=(45.0, 20.0, 60.0, 35.0)),
	]
	haworth = _haworth_not_detected()
	count, overlaps = count_bond_glyph_overlaps(
		lines, labels,
		checked_line_indexes=[0],
		checked_label_indexes=[0],
		aligned_connector_pairs=set(),
		haworth_base_ring=haworth,
		gap_tolerance=0.65,
	)
	assert count == 0
	assert overlaps == []


#============================================
def test_count_bond_glyph_overlaps_wedge_bond():
	"""Wedge bond overlapping a label box produces an overlap."""
	labels = [
		_make_label("OH", 50.0, 30.0, box=(45.0, 20.0, 60.0, 35.0)),
	]
	wedge_bonds = [
		{
			"spine_start": (40.0, 27.5),
			"spine_end": (55.0, 27.5),
		},
	]
	haworth = _haworth_not_detected()
	count, overlaps = count_bond_glyph_overlaps(
		lines=[],
		labels=labels,
		checked_line_indexes=[],
		checked_label_indexes=[0],
		aligned_connector_pairs=set(),
		haworth_base_ring=haworth,
		gap_tolerance=0.65,
		wedge_bonds=wedge_bonds,
	)
	assert count >= 1
	assert overlaps[0]["overlap_classification"] == "wedge_bond_overlap"
