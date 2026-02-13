"""Unit tests for render_geometry gap, alignment, and perpendicular helpers."""

# Standard Library
import math

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
from oasa import render_geometry


#============================================
# _perpendicular_distance_to_line tests
#============================================

#============================================
def test_perpendicular_distance_point_on_line():
	# point on the line should have distance 0
	dist = render_geometry._perpendicular_distance_to_line(
		(5.0, 5.0), (0.0, 0.0), (10.0, 10.0),
	)
	assert dist == pytest.approx(0.0, abs=1e-10)


#============================================
def test_perpendicular_distance_horizontal_line():
	# point (3, 5) above horizontal line y=0
	dist = render_geometry._perpendicular_distance_to_line(
		(3.0, 5.0), (0.0, 0.0), (10.0, 0.0),
	)
	assert dist == pytest.approx(5.0, abs=1e-10)


#============================================
def test_perpendicular_distance_vertical_line():
	# point (7, 3) to the right of vertical line x=0
	dist = render_geometry._perpendicular_distance_to_line(
		(7.0, 3.0), (0.0, 0.0), (0.0, 10.0),
	)
	assert dist == pytest.approx(7.0, abs=1e-10)


#============================================
def test_perpendicular_distance_diagonal():
	# point (1, 0) to line from (0,0) to (0,1) -- distance is 1
	dist = render_geometry._perpendicular_distance_to_line(
		(1.0, 0.0), (0.0, 0.0), (0.0, 1.0),
	)
	assert dist == pytest.approx(1.0, abs=1e-10)


#============================================
def test_perpendicular_distance_degenerate_line():
	# degenerate line (start == end) falls back to euclidean distance
	dist = render_geometry._perpendicular_distance_to_line(
		(3.0, 4.0), (0.0, 0.0), (0.0, 0.0),
	)
	assert dist == pytest.approx(5.0, abs=1e-10)


#============================================
def test_perpendicular_distance_negative_coords():
	# point (-3, 0) to horizontal line y=4 from (-10,4) to (10,4)
	dist = render_geometry._perpendicular_distance_to_line(
		(-3.0, 0.0), (-10.0, 4.0), (10.0, 4.0),
	)
	assert dist == pytest.approx(4.0, abs=1e-10)


#============================================
def test_perpendicular_distance_45_degree_line():
	# point (0, 1) to 45-degree line from (0,0) to (1,1)
	# perpendicular distance = |0*1 - 1*1 + 0| / sqrt(2) ... using formula
	# cross product: |dy*(px-sx) - dx*(py-sy)| / length
	# = |1*(0-0) - 1*(1-0)| / sqrt(2) = 1/sqrt(2)
	dist = render_geometry._perpendicular_distance_to_line(
		(0.0, 1.0), (0.0, 0.0), (1.0, 1.0),
	)
	assert dist == pytest.approx(1.0 / math.sqrt(2.0), abs=1e-10)


#============================================
# _retreat_to_target_gap tests
#============================================

#============================================
def test_retreat_zero_gap_returns_endpoint():
	# target_gap=0 should return the endpoint unchanged
	result = render_geometry._retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), 0.0, [],
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_retreat_negative_gap_returns_endpoint():
	# negative target_gap should return the endpoint unchanged
	result = render_geometry._retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), -1.0, [],
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_retreat_gap_already_satisfied():
	# endpoint is 5 units from the box boundary, target_gap=2
	# box from (12, -5) to (20, 5), endpoint at (10, 0) -> distance to box = 2
	box = render_geometry.make_box_target((12.0, -5.0, 20.0, 5.0))
	result = render_geometry._retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), 2.0, [box],
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_retreat_gap_needs_retreat():
	# box from (11, -5) to (20, 5), endpoint at (10, 0) -> distance to box = 1
	# target_gap=3, so need to retreat by 2 units
	box = render_geometry.make_box_target((11.0, -5.0, 20.0, 5.0))
	result = render_geometry._retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), 3.0, [box],
	)
	# endpoint should move 2 units toward start, from (10,0) to (8,0)
	assert result[0] == pytest.approx(8.0, abs=1e-10)
	assert result[1] == pytest.approx(0.0, abs=1e-10)


#============================================
def test_retreat_gap_vertical_direction():
	# vertical bond: start=(5,0), endpoint=(5,10), box at (3,12) to (7,20)
	# distance from (5,10) to box boundary = 2 (y direction)
	# target_gap=4, need to retreat 2 units
	box = render_geometry.make_box_target((3.0, 12.0, 7.0, 20.0))
	result = render_geometry._retreat_to_target_gap(
		(5.0, 0.0), (5.0, 10.0), 4.0, [box],
	)
	assert result[0] == pytest.approx(5.0, abs=1e-10)
	assert result[1] == pytest.approx(8.0, abs=1e-10)


#============================================
def test_retreat_gap_no_forbidden_regions():
	# no forbidden regions: current_gap=0, so retreat by full target_gap
	result = render_geometry._retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), 2.0, [],
	)
	assert result[0] == pytest.approx(8.0, abs=1e-10)
	assert result[1] == pytest.approx(0.0, abs=1e-10)


#============================================
def test_retreat_gap_excessive_retreat_clamps_to_start():
	# target gap exceeds bond length -- should clamp to line_start
	box = render_geometry.make_box_target((3.0, -1.0, 5.0, 1.0))
	result = render_geometry._retreat_to_target_gap(
		(0.0, 0.0), (2.0, 0.0), 100.0, [box],
	)
	assert result == pytest.approx((0.0, 0.0), abs=1e-10)


#============================================
def test_retreat_gap_degenerate_zero_length():
	# start == endpoint: should return endpoint unchanged
	result = render_geometry._retreat_to_target_gap(
		(5.0, 5.0), (5.0, 5.0), 1.0, [],
	)
	assert result == pytest.approx((5.0, 5.0), abs=1e-10)


#============================================
# _correct_endpoint_for_alignment tests
#============================================

#============================================
def test_correct_alignment_already_aligned():
	# bond from (0,0) to (10,0), alignment center at (10,0) -- on the line
	box = render_geometry.make_box_target((8.0, -2.0, 12.0, 2.0))
	result = render_geometry._correct_endpoint_for_alignment(
		(0.0, 0.0), (10.0, 0.0), (10.0, 0.0), box, 0.5,
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_correct_alignment_within_tolerance():
	# bond from (0,0) to (10,0), alignment center at (10, 0.1) -- within tolerance
	box = render_geometry.make_box_target((8.0, -2.0, 12.0, 2.0))
	result = render_geometry._correct_endpoint_for_alignment(
		(0.0, 0.0), (10.0, 0.0), (10.0, 0.1), box, 0.5,
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_correct_alignment_off_axis_corrects():
	# bond from (0,0) to (10,0), alignment center at (10, 5) -- off axis
	# correction should redirect toward alignment center and hit box boundary
	box = render_geometry.make_box_target((8.0, -2.0, 12.0, 8.0))
	result = render_geometry._correct_endpoint_for_alignment(
		(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), box, 0.5,
	)
	# the corrected endpoint should be on the box boundary
	# and the line from (0,0) through result should pass closer to (10,5)
	assert result != pytest.approx((10.0, 0.0), abs=1e-2)
	# verify the correction moved the endpoint
	perp = render_geometry._perpendicular_distance_to_line(
		(10.0, 5.0), (0.0, 0.0), result,
	)
	# the corrected line should pass much closer to alignment center
	assert perp < 1.0


#============================================
def test_correct_alignment_circle_target():
	# bond from (0,0) to (10,0), alignment center at (10, 3)
	# circle target centered at (10,3) radius 2
	circle = render_geometry.make_circle_target((10.0, 3.0), 2.0)
	result = render_geometry._correct_endpoint_for_alignment(
		(0.0, 0.0), (10.0, 0.0), (10.0, 3.0), circle, 0.5,
	)
	# should correct to point toward the circle center
	assert result != pytest.approx((10.0, 0.0), abs=1e-2)
	# result should be on or near the circle boundary
	dx = result[0] - 10.0
	dy = result[1] - 3.0
	dist_from_center = math.hypot(dx, dy)
	assert dist_from_center == pytest.approx(2.0, abs=0.5)


#============================================
def test_correct_alignment_coincident_start_center():
	# bond_start == alignment_center: should return endpoint unchanged
	box = render_geometry.make_box_target((8.0, -2.0, 12.0, 2.0))
	result = render_geometry._correct_endpoint_for_alignment(
		(10.0, 0.0), (10.0, 0.0), (10.0, 0.0), box, 0.5,
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)
