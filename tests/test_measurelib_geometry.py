"""Tests for measurelib.geometry module."""

# Standard Library
import math
import os
import sys

# Third Party
import pytest

# Local
import conftest
_tools_dir = os.path.join(conftest.repo_root(), "tools")
if _tools_dir not in sys.path:
	sys.path.insert(0, _tools_dir)

from measurelib.geometry import (
	angle_difference_degrees,
	boxes_overlap_interior,
	convex_hull,
	distance_sq_segment_to_segment,
	line_angle_degrees,
	line_collinear_overlap_length,
	line_intersection_point,
	line_intersects_box_interior,
	line_overlap_midpoint,
	lines_nearly_parallel,
	lines_share_endpoint,
	nearest_canonical_lattice_angle,
	nearest_lattice_angle_error,
	on_segment,
	orientation,
	parallel_error_degrees,
	point_to_infinite_line_distance,
	point_to_segment_distance_sq,
	points_close,
	segment_distance_to_box_sq,
	segments_intersect,
)


# ============================================
# line_angle_degrees
# ============================================

#============================================
def test_line_angle_degrees_horizontal():
	line = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	assert line_angle_degrees(line) == pytest.approx(0.0)


#============================================
def test_line_angle_degrees_vertical():
	line = {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 10.0}
	assert line_angle_degrees(line) == pytest.approx(90.0)


#============================================
def test_line_angle_degrees_diagonal_45():
	line = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0}
	assert line_angle_degrees(line) == pytest.approx(45.0)


#============================================
def test_line_angle_degrees_left_180():
	line = {"x1": 10.0, "y1": 0.0, "x2": 0.0, "y2": 0.0}
	assert line_angle_degrees(line) == pytest.approx(180.0)


#============================================
def test_line_angle_degrees_down_270():
	line = {"x1": 0.0, "y1": 10.0, "x2": 0.0, "y2": 0.0}
	assert line_angle_degrees(line) == pytest.approx(270.0)


# ============================================
# nearest_lattice_angle_error
# ============================================

#============================================
def test_nearest_lattice_angle_error_exact():
	# 0, 30, 60, ... are canonical lattice angles
	assert nearest_lattice_angle_error(0.0) == pytest.approx(0.0)
	assert nearest_lattice_angle_error(90.0) == pytest.approx(0.0)
	assert nearest_lattice_angle_error(150.0) == pytest.approx(0.0)


#============================================
def test_nearest_lattice_angle_error_between():
	# 15 is midway between 0 and 30 -> error = 15
	assert nearest_lattice_angle_error(15.0) == pytest.approx(15.0)


#============================================
def test_nearest_lattice_angle_error_close():
	# 31 degrees -> nearest is 30, error = 1
	assert nearest_lattice_angle_error(31.0) == pytest.approx(1.0)


# ============================================
# nearest_canonical_lattice_angle
# ============================================

#============================================
def test_nearest_canonical_lattice_angle_exact():
	assert nearest_canonical_lattice_angle(60.0) == pytest.approx(60.0)


#============================================
def test_nearest_canonical_lattice_angle_between():
	# 44 degrees -> nearest canonical is 30 or 60; 44 is closer to 30 (error=14) than 60 (error=16)
	assert nearest_canonical_lattice_angle(44.0) == pytest.approx(30.0)


#============================================
def test_nearest_canonical_lattice_angle_wrap():
	# 359 degrees -> nearest is 0
	assert nearest_canonical_lattice_angle(359.0) == pytest.approx(0.0)


# ============================================
# boxes_overlap_interior
# ============================================

#============================================
def test_boxes_overlap_interior_overlapping():
	box_a = (0.0, 0.0, 10.0, 10.0)
	box_b = (5.0, 5.0, 15.0, 15.0)
	assert boxes_overlap_interior(box_a, box_b) is True


#============================================
def test_boxes_overlap_interior_touching():
	# boxes share an edge -> overlap_x or overlap_y is 0
	box_a = (0.0, 0.0, 10.0, 10.0)
	box_b = (10.0, 0.0, 20.0, 10.0)
	assert boxes_overlap_interior(box_a, box_b) is False


#============================================
def test_boxes_overlap_interior_disjoint():
	box_a = (0.0, 0.0, 5.0, 5.0)
	box_b = (10.0, 10.0, 20.0, 20.0)
	assert boxes_overlap_interior(box_a, box_b) is False


#============================================
def test_boxes_overlap_interior_contained():
	box_a = (0.0, 0.0, 20.0, 20.0)
	box_b = (5.0, 5.0, 10.0, 10.0)
	assert boxes_overlap_interior(box_a, box_b) is True


# ============================================
# points_close
# ============================================

#============================================
def test_points_close_within_tol():
	assert points_close((0.0, 0.0), (0.5, 0.5), tol=1.0) is True


#============================================
def test_points_close_outside_tol():
	assert points_close((0.0, 0.0), (5.0, 5.0), tol=1.0) is False


#============================================
def test_points_close_exact():
	assert points_close((3.0, 4.0), (3.0, 4.0), tol=0.0) is True


# ============================================
# point_to_segment_distance_sq
# ============================================

#============================================
def test_point_to_segment_distance_sq_on_segment():
	# point is on the segment itself
	assert point_to_segment_distance_sq((5.0, 0.0), (0.0, 0.0), (10.0, 0.0)) == pytest.approx(0.0)


#============================================
def test_point_to_segment_distance_sq_off_end():
	# point past end of segment
	dist_sq = point_to_segment_distance_sq((15.0, 0.0), (0.0, 0.0), (10.0, 0.0))
	assert dist_sq == pytest.approx(25.0)


#============================================
def test_point_to_segment_distance_sq_perpendicular():
	# point 3 units above midpoint of horizontal segment
	dist_sq = point_to_segment_distance_sq((5.0, 3.0), (0.0, 0.0), (10.0, 0.0))
	assert dist_sq == pytest.approx(9.0)


#============================================
def test_point_to_segment_distance_sq_degenerate():
	# zero-length segment
	dist_sq = point_to_segment_distance_sq((3.0, 4.0), (0.0, 0.0), (0.0, 0.0))
	assert dist_sq == pytest.approx(25.0)


# ============================================
# orientation
# ============================================

#============================================
def test_orientation_ccw():
	# counter-clockwise: returns 2
	assert orientation((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)) == 2


#============================================
def test_orientation_cw():
	# clockwise: returns 1
	assert orientation((0.0, 0.0), (0.0, 1.0), (1.0, 0.0)) == 1


#============================================
def test_orientation_collinear():
	assert orientation((0.0, 0.0), (1.0, 1.0), (2.0, 2.0)) == 0


# ============================================
# on_segment
# ============================================

#============================================
def test_on_segment_on():
	assert on_segment((0.0, 0.0), (10.0, 0.0), (5.0, 0.0)) is True


#============================================
def test_on_segment_off():
	assert on_segment((0.0, 0.0), (10.0, 0.0), (15.0, 0.0)) is False


#============================================
def test_on_segment_endpoint():
	assert on_segment((0.0, 0.0), (10.0, 0.0), (0.0, 0.0)) is True


# ============================================
# segments_intersect
# ============================================

#============================================
def test_segments_intersect_crossing():
	assert segments_intersect((0.0, 0.0), (10.0, 10.0), (10.0, 0.0), (0.0, 10.0)) is True


#============================================
def test_segments_intersect_parallel():
	assert segments_intersect((0.0, 0.0), (10.0, 0.0), (0.0, 1.0), (10.0, 1.0)) is False


#============================================
def test_segments_intersect_collinear_overlapping():
	assert segments_intersect((0.0, 0.0), (10.0, 0.0), (5.0, 0.0), (15.0, 0.0)) is True


#============================================
def test_segments_intersect_non_intersecting():
	assert segments_intersect((0.0, 0.0), (1.0, 0.0), (2.0, 2.0), (3.0, 2.0)) is False


# ============================================
# distance_sq_segment_to_segment
# ============================================

#============================================
def test_distance_sq_segment_to_segment_intersecting():
	result = distance_sq_segment_to_segment(
		(0.0, 0.0), (10.0, 10.0), (10.0, 0.0), (0.0, 10.0)
	)
	assert result == pytest.approx(0.0)


#============================================
def test_distance_sq_segment_to_segment_non_intersecting():
	# two parallel horizontal segments, 5 apart vertically
	result = distance_sq_segment_to_segment(
		(0.0, 0.0), (10.0, 0.0), (0.0, 5.0), (10.0, 5.0)
	)
	assert result == pytest.approx(25.0)


#============================================
def test_distance_sq_segment_to_segment_gap():
	# end-to-end gap
	result = distance_sq_segment_to_segment(
		(0.0, 0.0), (3.0, 0.0), (6.0, 0.0), (9.0, 0.0)
	)
	assert result == pytest.approx(9.0)


# ============================================
# segment_distance_to_box_sq
# ============================================

#============================================
def test_segment_distance_to_box_sq_through():
	# segment passes through box
	result = segment_distance_to_box_sq((0.0, 5.0), (20.0, 5.0), (5.0, 0.0, 15.0, 10.0))
	assert result == pytest.approx(0.0)


#============================================
def test_segment_distance_to_box_sq_outside():
	# segment is above the box
	result = segment_distance_to_box_sq((0.0, 15.0), (10.0, 15.0), (0.0, 0.0, 10.0, 10.0))
	assert result == pytest.approx(25.0)


#============================================
def test_segment_distance_to_box_sq_endpoint_inside():
	# one endpoint is inside the box
	result = segment_distance_to_box_sq((5.0, 5.0), (20.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert result == pytest.approx(0.0)


# ============================================
# line_intersects_box_interior
# ============================================

#============================================
def test_line_intersects_box_interior_crosses():
	line = {"x1": 0.0, "y1": 5.0, "x2": 20.0, "y2": 5.0, "width": 1.0}
	box = (3.0, 0.0, 17.0, 10.0)
	assert line_intersects_box_interior(line, box) is True


#============================================
def test_line_intersects_box_interior_misses():
	line = {"x1": 0.0, "y1": 50.0, "x2": 20.0, "y2": 50.0, "width": 1.0}
	box = (0.0, 0.0, 10.0, 10.0)
	assert line_intersects_box_interior(line, box) is False


#============================================
def test_line_intersects_box_interior_tiny_box():
	# box too small after epsilon shrink -> always False
	line = {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 0.0, "width": 1.0}
	box = (0.0, 0.0, 0.5, 0.5)
	assert line_intersects_box_interior(line, box) is False


# ============================================
# lines_share_endpoint
# ============================================

#============================================
def test_lines_share_endpoint_shared():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 10.0, "y1": 0.0, "x2": 20.0, "y2": 0.0}
	assert lines_share_endpoint(line_a, line_b) is True


#============================================
def test_lines_share_endpoint_not_shared():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 5.0, "y2": 0.0}
	line_b = {"x1": 10.0, "y1": 10.0, "x2": 20.0, "y2": 10.0}
	assert lines_share_endpoint(line_a, line_b) is False


#============================================
def test_lines_share_endpoint_within_tolerance():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 10.3, "y1": 0.3, "x2": 20.0, "y2": 0.0}
	# within default tol=0.75
	assert lines_share_endpoint(line_a, line_b) is True


# ============================================
# parallel_error_degrees
# ============================================

#============================================
def test_parallel_error_degrees_parallel():
	assert parallel_error_degrees(0.0, 0.0) == pytest.approx(0.0)


#============================================
def test_parallel_error_degrees_perpendicular():
	assert parallel_error_degrees(0.0, 90.0) == pytest.approx(90.0)


#============================================
def test_parallel_error_degrees_antiparallel():
	assert parallel_error_degrees(0.0, 180.0) == pytest.approx(0.0)


#============================================
def test_parallel_error_degrees_near_antiparallel():
	assert parallel_error_degrees(1.0, 179.0) == pytest.approx(2.0)


# ============================================
# angle_difference_degrees
# ============================================

#============================================
def test_angle_difference_degrees_same():
	assert angle_difference_degrees(45.0, 45.0) == pytest.approx(0.0)


#============================================
def test_angle_difference_degrees_opposite():
	assert angle_difference_degrees(0.0, 180.0) == pytest.approx(180.0)


#============================================
def test_angle_difference_degrees_wrap():
	assert angle_difference_degrees(350.0, 10.0) == pytest.approx(20.0)


# ============================================
# lines_nearly_parallel
# ============================================

#============================================
def test_lines_nearly_parallel_parallel():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0}
	assert lines_nearly_parallel(line_a, line_b) is True


#============================================
def test_lines_nearly_parallel_not_parallel():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 10.0}
	assert lines_nearly_parallel(line_a, line_b) is False


#============================================
def test_lines_nearly_parallel_antiparallel():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 10.0, "y1": 5.0, "x2": 0.0, "y2": 5.0}
	assert lines_nearly_parallel(line_a, line_b) is True


# ============================================
# line_collinear_overlap_length
# ============================================

#============================================
def test_line_collinear_overlap_overlapping():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 5.0, "y1": 0.0, "x2": 15.0, "y2": 0.0}
	assert line_collinear_overlap_length(line_a, line_b) == pytest.approx(5.0)


#============================================
def test_line_collinear_overlap_non_overlapping():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 5.0, "y2": 0.0}
	line_b = {"x1": 10.0, "y1": 0.0, "x2": 15.0, "y2": 0.0}
	assert line_collinear_overlap_length(line_a, line_b) == pytest.approx(0.0)


#============================================
def test_line_collinear_overlap_non_collinear():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0}
	assert line_collinear_overlap_length(line_a, line_b) == pytest.approx(0.0)


#============================================
def test_line_collinear_overlap_contained():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 20.0, "y2": 0.0}
	line_b = {"x1": 5.0, "y1": 0.0, "x2": 15.0, "y2": 0.0}
	assert line_collinear_overlap_length(line_a, line_b) == pytest.approx(10.0)


# ============================================
# line_overlap_midpoint
# ============================================

#============================================
def test_line_overlap_midpoint_overlapping():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 5.0, "y1": 0.0, "x2": 15.0, "y2": 0.0}
	result = line_overlap_midpoint(line_a, line_b)
	assert result is not None
	assert result[0] == pytest.approx(7.5)
	assert result[1] == pytest.approx(0.0)


#============================================
def test_line_overlap_midpoint_non_overlapping():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 3.0, "y2": 0.0}
	line_b = {"x1": 10.0, "y1": 0.0, "x2": 15.0, "y2": 0.0}
	assert line_overlap_midpoint(line_a, line_b) is None


#============================================
def test_line_overlap_midpoint_non_collinear():
	line_a = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	line_b = {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0}
	assert line_overlap_midpoint(line_a, line_b) is None


# ============================================
# line_intersection_point
# ============================================

#============================================
def test_line_intersection_point_crossing():
	result = line_intersection_point((0.0, 0.0), (10.0, 10.0), (10.0, 0.0), (0.0, 10.0))
	assert result is not None
	assert result[0] == pytest.approx(5.0)
	assert result[1] == pytest.approx(5.0)


#============================================
def test_line_intersection_point_parallel():
	result = line_intersection_point((0.0, 0.0), (10.0, 0.0), (0.0, 5.0), (10.0, 5.0))
	assert result is None


#============================================
def test_line_intersection_point_non_overlapping():
	# segments don't actually reach each other
	result = line_intersection_point((0.0, 0.0), (1.0, 0.0), (5.0, -1.0), (5.0, 1.0))
	assert result is None


# ============================================
# convex_hull
# ============================================

#============================================
def test_convex_hull_triangle():
	pts = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0)]
	hull = convex_hull(pts)
	assert len(hull) == 3
	assert set(hull) == set(pts)


#============================================
def test_convex_hull_square():
	pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
	hull = convex_hull(pts)
	assert len(hull) == 4


#============================================
def test_convex_hull_with_interior_point():
	pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (5.0, 5.0)]
	hull = convex_hull(pts)
	assert len(hull) == 4
	assert (5.0, 5.0) not in hull


#============================================
def test_convex_hull_collinear():
	pts = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
	hull = convex_hull(pts)
	assert len(hull) == 2
	assert (0.0, 0.0) in hull
	assert (10.0, 0.0) in hull


#============================================
def test_convex_hull_single_point():
	pts = [(3.0, 4.0)]
	hull = convex_hull(pts)
	assert len(hull) == 1
	assert hull[0] == (3.0, 4.0)


# ============================================
# point_to_infinite_line_distance
# ============================================

#============================================
def test_point_to_infinite_line_distance_on_line():
	assert point_to_infinite_line_distance(
		(5.0, 0.0), (0.0, 0.0), (10.0, 0.0)
	) == pytest.approx(0.0)


#============================================
def test_point_to_infinite_line_distance_off_line():
	assert point_to_infinite_line_distance(
		(5.0, 3.0), (0.0, 0.0), (10.0, 0.0)
	) == pytest.approx(3.0)


#============================================
def test_point_to_infinite_line_distance_diagonal():
	# distance from (0,0) to line through (1,0) and (0,1) = 1/sqrt(2)
	result = point_to_infinite_line_distance((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))
	assert result == pytest.approx(1.0 / math.sqrt(2.0))


#============================================
def test_point_to_infinite_line_distance_degenerate():
	# degenerate line (single point) -> point-to-point distance
	result = point_to_infinite_line_distance((3.0, 4.0), (0.0, 0.0), (0.0, 0.0))
	assert result == pytest.approx(5.0)
