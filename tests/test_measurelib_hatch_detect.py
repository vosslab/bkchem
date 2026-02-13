"""Tests for measurelib.hatch_detect module."""

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

from measurelib.hatch_detect import (
	default_overlap_origin,
	detect_hashed_carrier_map,
	is_hashed_carrier_candidate,
	is_hatch_stroke_candidate,
	overlap_origin,
	quadrant_label,
	ring_region_label,
)


# -- helpers --

def _make_haworth_detected(cx=50.0, cy=50.0, radius=20.0):
	"""Return a haworth_base_ring dict with detected=True."""
	return {
		"detected": True,
		"line_indexes": [0, 1, 2, 3, 4, 5],
		"centroid": [cx, cy],
		"radius": radius,
	}


def _make_haworth_not_detected():
	"""Return a haworth_base_ring dict with detected=False."""
	return {
		"detected": False,
		"line_indexes": [],
		"centroid": None,
		"radius": 0.0,
	}


#============================================
def test_is_hatch_stroke_candidate_valid():
	"""Butt linecap with correct width and length returns True."""
	line = {
		"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 3.0,
		"width": 0.8, "linecap": "butt",
	}
	assert is_hatch_stroke_candidate(line) is True


#============================================
def test_is_hatch_stroke_candidate_round_linecap():
	"""Round linecap disqualifies stroke candidate."""
	line = {
		"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 3.0,
		"width": 0.8, "linecap": "round",
	}
	assert is_hatch_stroke_candidate(line) is False


#============================================
def test_is_hatch_stroke_candidate_too_long():
	"""Stroke longer than HATCH_STROKE_MAX_LENGTH returns False."""
	line = {
		"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 20.0,
		"width": 0.8, "linecap": "butt",
	}
	assert is_hatch_stroke_candidate(line) is False


#============================================
def test_is_hatch_stroke_candidate_too_wide():
	"""Stroke wider than HATCH_STROKE_MAX_WIDTH returns False."""
	line = {
		"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 3.0,
		"width": 5.0, "linecap": "butt",
	}
	assert is_hatch_stroke_candidate(line) is False


#============================================
def test_is_hashed_carrier_candidate_valid():
	"""Thin, long line qualifies as carrier."""
	line = {
		"x1": 0.0, "y1": 50.0, "x2": 30.0, "y2": 50.0,
		"width": 0.3, "linecap": "butt",
	}
	assert is_hashed_carrier_candidate(line) is True


#============================================
def test_is_hashed_carrier_candidate_too_short():
	"""Line shorter than HASHED_CARRIER_MIN_LENGTH returns False."""
	line = {
		"x1": 0.0, "y1": 50.0, "x2": 2.0, "y2": 50.0,
		"width": 0.3, "linecap": "butt",
	}
	assert is_hashed_carrier_candidate(line) is False


#============================================
def test_is_hashed_carrier_candidate_too_wide():
	"""Line wider than HASHED_CARRIER_MAX_WIDTH returns False."""
	line = {
		"x1": 0.0, "y1": 50.0, "x2": 30.0, "y2": 50.0,
		"width": 5.0, "linecap": "butt",
	}
	assert is_hashed_carrier_candidate(line) is False


#============================================
def test_detect_hashed_carrier_map_with_strokes():
	"""Carrier with perpendicular crossing strokes is detected."""
	# carrier: horizontal, thin, long
	carrier = {
		"x1": 0.0, "y1": 50.0, "x2": 30.0, "y2": 50.0,
		"width": 0.3, "linecap": "butt",
	}
	# strokes: vertical, short, crossing the carrier
	strokes = [
		{
			"x1": 5.0 * i, "y1": 48.0,
			"x2": 5.0 * i, "y2": 52.0,
			"width": 0.8, "linecap": "butt",
		}
		for i in range(1, 6)
	]
	lines = [carrier] + strokes
	checked = list(range(len(lines)))
	carrier_map = detect_hashed_carrier_map(lines, checked)
	assert 0 in carrier_map
	assert len(carrier_map[0]) >= 4


#============================================
def test_detect_hashed_carrier_map_no_strokes():
	"""Lines with no hatch strokes produce an empty carrier map."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 30.0, "y2": 0.0, "width": 0.3, "linecap": "butt"},
		{"x1": 40.0, "y1": 0.0, "x2": 70.0, "y2": 0.0, "width": 0.3, "linecap": "butt"},
	]
	checked = list(range(len(lines)))
	carrier_map = detect_hashed_carrier_map(lines, checked)
	assert carrier_map == {}


#============================================
def test_default_overlap_origin_basic():
	"""Origin is center of bounding box of all line endpoints."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 100.0, "y2": 0.0},
		{"x1": 0.0, "y1": 50.0, "x2": 100.0, "y2": 50.0},
	]
	origin = default_overlap_origin(lines)
	assert origin[0] == pytest.approx(50.0)
	assert origin[1] == pytest.approx(25.0)


#============================================
def test_default_overlap_origin_empty():
	"""Empty line list returns (0, 0)."""
	assert default_overlap_origin([]) == (0.0, 0.0)


#============================================
def test_overlap_origin_with_haworth_centroid():
	"""When haworth is detected, overlap_origin uses its centroid."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 100.0, "y2": 100.0},
	]
	haworth = _make_haworth_detected(cx=30.0, cy=40.0)
	origin = overlap_origin(lines, haworth)
	assert origin == (30.0, 40.0)


#============================================
def test_overlap_origin_without_haworth():
	"""When haworth is not detected, falls back to default_overlap_origin."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 100.0, "y2": 50.0},
	]
	haworth = _make_haworth_not_detected()
	origin = overlap_origin(lines, haworth)
	assert origin[0] == pytest.approx(50.0)
	assert origin[1] == pytest.approx(25.0)


#============================================
@pytest.mark.parametrize("point,expected", [
	((10.0, -10.0), "upper-right"),
	((-10.0, -10.0), "upper-left"),
	((-10.0, 10.0), "lower-left"),
	((10.0, 10.0), "lower-right"),
])
def test_quadrant_label_directions(point, expected):
	"""Points in each quadrant are labeled correctly (SVG y-down)."""
	assert quadrant_label(point, origin=(0.0, 0.0)) == expected


#============================================
def test_quadrant_label_axis():
	"""Point near origin on an axis returns 'axis'."""
	assert quadrant_label((0.0, 10.0), origin=(0.0, 0.0)) == "axis"
	assert quadrant_label((10.0, 0.0), origin=(0.0, 0.0)) == "axis"


#============================================
def test_ring_region_label_inside():
	"""Point inside ring radius * 1.15 returns 'inside_base_ring'."""
	haworth = _make_haworth_detected(cx=50.0, cy=50.0, radius=20.0)
	# point at center
	assert ring_region_label((50.0, 50.0), haworth) == "inside_base_ring"
	# point at radius (still within 1.15 * radius)
	assert ring_region_label((70.0, 50.0), haworth) == "inside_base_ring"


#============================================
def test_ring_region_label_outside():
	"""Point well outside the ring returns 'outside_base_ring'."""
	haworth = _make_haworth_detected(cx=50.0, cy=50.0, radius=20.0)
	assert ring_region_label((200.0, 200.0), haworth) == "outside_base_ring"


#============================================
def test_ring_region_label_not_detected():
	"""When ring is not detected, returns 'unknown'."""
	haworth = _make_haworth_not_detected()
	assert ring_region_label((50.0, 50.0), haworth) == "unknown"
