"""Tests for measurelib.util module."""

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

from measurelib.util import (
	alignment_score,
	compact_float,
	compact_sorted_values,
	compact_value_counts,
	display_float,
	display_point,
	group_length_append,
	increment_counter,
	length_stats,
	line_endpoints,
	line_length,
	line_midpoint,
	normalize_box,
	point_distance_sq,
	point_to_box_distance,
	point_to_box_signed_distance,
	point_to_ellipse_signed_distance,
	point_to_glyph_primitive_signed_distance,
	point_to_glyph_primitives_distance,
	point_to_glyph_primitives_signed_distance,
	rounded_sorted_values,
	rounded_value_counts,
	safe_token,
)


# ============================================
# line_length
# ============================================

#============================================
def test_line_length_horizontal():
	line = {"x1": 0.0, "y1": 0.0, "x2": 5.0, "y2": 0.0}
	assert line_length(line) == pytest.approx(5.0)


#============================================
def test_line_length_vertical():
	line = {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 7.0}
	assert line_length(line) == pytest.approx(7.0)


#============================================
def test_line_length_diagonal():
	line = {"x1": 0.0, "y1": 0.0, "x2": 3.0, "y2": 4.0}
	assert line_length(line) == pytest.approx(5.0)


#============================================
def test_line_length_zero():
	line = {"x1": 2.0, "y1": 3.0, "x2": 2.0, "y2": 3.0}
	assert line_length(line) == pytest.approx(0.0)


# ============================================
# length_stats
# ============================================

#============================================
def test_length_stats_empty():
	result = length_stats([])
	assert result["count"] == 0
	assert result["min"] == pytest.approx(0.0)
	assert result["max"] == pytest.approx(0.0)
	assert result["mean"] == pytest.approx(0.0)
	assert result["stddev"] == pytest.approx(0.0)
	assert result["coefficient_of_variation"] == pytest.approx(0.0)


#============================================
def test_length_stats_single():
	result = length_stats([4.0])
	assert result["count"] == 1
	assert result["min"] == pytest.approx(4.0)
	assert result["max"] == pytest.approx(4.0)
	assert result["mean"] == pytest.approx(4.0)
	assert result["stddev"] == pytest.approx(0.0)
	assert result["coefficient_of_variation"] == pytest.approx(0.0)


#============================================
def test_length_stats_multiple():
	result = length_stats([2.0, 4.0, 6.0])
	assert result["count"] == 3
	assert result["min"] == pytest.approx(2.0)
	assert result["max"] == pytest.approx(6.0)
	assert result["mean"] == pytest.approx(4.0)
	# population stddev = sqrt(((2-4)^2+(4-4)^2+(6-4)^2)/3) = sqrt(8/3)
	assert result["stddev"] == pytest.approx(math.sqrt(8.0 / 3.0))
	assert result["coefficient_of_variation"] == pytest.approx(math.sqrt(8.0 / 3.0) / 4.0)


# ============================================
# line_endpoints
# ============================================

#============================================
def test_line_endpoints_basic():
	line = {"x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0}
	p1, p2 = line_endpoints(line)
	assert p1 == (1.0, 2.0)
	assert p2 == (3.0, 4.0)


#============================================
def test_line_endpoints_negative_coords():
	line = {"x1": -5.0, "y1": -10.0, "x2": 5.0, "y2": 10.0}
	p1, p2 = line_endpoints(line)
	assert p1 == (-5.0, -10.0)
	assert p2 == (5.0, 10.0)


# ============================================
# line_midpoint
# ============================================

#============================================
def test_line_midpoint_basic():
	line = {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
	mx, my = line_midpoint(line)
	assert mx == pytest.approx(5.0)
	assert my == pytest.approx(0.0)


#============================================
def test_line_midpoint_diagonal():
	line = {"x1": 2.0, "y1": 4.0, "x2": 8.0, "y2": 12.0}
	mx, my = line_midpoint(line)
	assert mx == pytest.approx(5.0)
	assert my == pytest.approx(8.0)


#============================================
def test_line_midpoint_same_point():
	line = {"x1": 3.0, "y1": 7.0, "x2": 3.0, "y2": 7.0}
	mx, my = line_midpoint(line)
	assert mx == pytest.approx(3.0)
	assert my == pytest.approx(7.0)


# ============================================
# normalize_box
# ============================================

#============================================
def test_normalize_box_already_normal():
	box = (1.0, 2.0, 5.0, 6.0)
	assert normalize_box(box) == (1.0, 2.0, 5.0, 6.0)


#============================================
def test_normalize_box_reversed_corners():
	box = (5.0, 6.0, 1.0, 2.0)
	assert normalize_box(box) == (1.0, 2.0, 5.0, 6.0)


#============================================
def test_normalize_box_mixed():
	box = (5.0, 2.0, 1.0, 6.0)
	assert normalize_box(box) == (1.0, 2.0, 5.0, 6.0)


# ============================================
# point_distance_sq
# ============================================

#============================================
def test_point_distance_sq_same():
	assert point_distance_sq((3.0, 4.0), (3.0, 4.0)) == pytest.approx(0.0)


#============================================
def test_point_distance_sq_different():
	# distance = 5, squared = 25
	assert point_distance_sq((0.0, 0.0), (3.0, 4.0)) == pytest.approx(25.0)


#============================================
def test_point_distance_sq_negative():
	assert point_distance_sq((-1.0, -1.0), (2.0, 3.0)) == pytest.approx(25.0)


# ============================================
# point_to_box_distance
# ============================================

#============================================
def test_point_to_box_distance_inside():
	assert point_to_box_distance((5.0, 5.0), (0.0, 0.0, 10.0, 10.0)) == pytest.approx(0.0)


#============================================
def test_point_to_box_distance_outside():
	# point is 3 units to the left
	assert point_to_box_distance((-3.0, 5.0), (0.0, 0.0, 10.0, 10.0)) == pytest.approx(3.0)


#============================================
def test_point_to_box_distance_on_edge():
	assert point_to_box_distance((0.0, 5.0), (0.0, 0.0, 10.0, 10.0)) == pytest.approx(0.0)


#============================================
def test_point_to_box_distance_corner():
	# point is at (-3, -4), box starts at (0,0); distance = 5
	assert point_to_box_distance((-3.0, -4.0), (0.0, 0.0, 10.0, 10.0)) == pytest.approx(5.0)


# ============================================
# point_to_box_signed_distance
# ============================================

#============================================
def test_point_to_box_signed_distance_inside():
	# point (5, 5) in box (0,0,10,10): min depth is 5
	result = point_to_box_signed_distance((5.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert result < 0.0
	assert result == pytest.approx(-5.0)


#============================================
def test_point_to_box_signed_distance_outside():
	result = point_to_box_signed_distance((-3.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert result > 0.0
	assert result == pytest.approx(3.0)


#============================================
def test_point_to_box_signed_distance_near_edge_inside():
	# point (1, 5) in box (0,0,10,10): min depth is 1
	result = point_to_box_signed_distance((1.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert result == pytest.approx(-1.0)


# ============================================
# point_to_ellipse_signed_distance
# ============================================

#============================================
def test_point_to_ellipse_signed_distance_center():
	# at center of circle r=5, signed distance should be -5
	result = point_to_ellipse_signed_distance((0.0, 0.0), 0.0, 0.0, 5.0, 5.0)
	assert result == pytest.approx(-5.0)


#============================================
def test_point_to_ellipse_signed_distance_inside():
	# inside a circle of radius 5 at (3,0): distance to boundary ~ 2
	result = point_to_ellipse_signed_distance((3.0, 0.0), 0.0, 0.0, 5.0, 5.0)
	assert result < 0.0
	assert result == pytest.approx(-2.0, abs=0.01)


#============================================
def test_point_to_ellipse_signed_distance_outside():
	# outside a circle of radius 5 at (8,0): distance to boundary ~ 3
	result = point_to_ellipse_signed_distance((8.0, 0.0), 0.0, 0.0, 5.0, 5.0)
	assert result > 0.0
	assert result == pytest.approx(3.0, abs=0.01)


#============================================
def test_point_to_ellipse_signed_distance_on_boundary():
	# on boundary of circle r=5 at (5, 0)
	result = point_to_ellipse_signed_distance((5.0, 0.0), 0.0, 0.0, 5.0, 5.0)
	assert result == pytest.approx(0.0, abs=0.01)


# ============================================
# alignment_score
# ============================================

#============================================
def test_alignment_score_zero_distance():
	assert alignment_score(0.0, 10.0) == pytest.approx(1.0)


#============================================
def test_alignment_score_over_tolerance():
	assert alignment_score(15.0, 10.0) == pytest.approx(0.0)


#============================================
def test_alignment_score_half():
	assert alignment_score(5.0, 10.0) == pytest.approx(0.5)


#============================================
def test_alignment_score_none_distance():
	assert alignment_score(None, 10.0) == pytest.approx(0.0)


#============================================
def test_alignment_score_none_tolerance():
	assert alignment_score(5.0, None) == pytest.approx(0.0)


#============================================
def test_alignment_score_zero_tolerance():
	assert alignment_score(5.0, 0.0) == pytest.approx(0.0)


# ============================================
# compact_float
# ============================================

#============================================
def test_compact_float_none():
	assert compact_float(None) is None


#============================================
def test_compact_float_normal():
	assert compact_float(3.14159265358979) == pytest.approx(3.14159265359)


#============================================
def test_compact_float_integer_like():
	assert compact_float(5.0) == pytest.approx(5.0)


# ============================================
# display_float
# ============================================

#============================================
def test_display_float_none():
	assert display_float(None) is None


#============================================
def test_display_float_rounding():
	assert display_float(3.14159) == pytest.approx(3.142)


#============================================
def test_display_float_custom_decimals():
	assert display_float(3.14159, decimals=1) == pytest.approx(3.1)


# ============================================
# display_point
# ============================================

#============================================
def test_display_point_none():
	assert display_point(None) is None


#============================================
def test_display_point_list():
	result = display_point([3.14159, 2.71828])
	assert result == [pytest.approx(3.142), pytest.approx(2.718)]


#============================================
def test_display_point_tuple():
	result = display_point((1.23456, 7.89012))
	assert result == [pytest.approx(1.235), pytest.approx(7.890)]


#============================================
def test_display_point_non_list():
	assert display_point("hello") == "hello"


#============================================
def test_display_point_wrong_length():
	assert display_point([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]


# ============================================
# safe_token
# ============================================

#============================================
def test_safe_token_normal():
	assert safe_token("hello") == "hello"


#============================================
def test_safe_token_special_chars():
	assert safe_token("a/b c!d") == "a_b_c_d"


#============================================
def test_safe_token_empty():
	assert safe_token("") == "unknown"


#============================================
def test_safe_token_none():
	assert safe_token(None) == "unknown"


#============================================
def test_safe_token_only_special():
	assert safe_token("!!!") == "unknown"


# ============================================
# increment_counter
# ============================================

#============================================
def test_increment_counter_new_key():
	counter = {}
	increment_counter(counter, "apples")
	assert counter["apples"] == 1


#============================================
def test_increment_counter_existing_key():
	counter = {"apples": 3}
	increment_counter(counter, "apples")
	assert counter["apples"] == 4


#============================================
def test_increment_counter_multiple_keys():
	counter = {}
	increment_counter(counter, "a")
	increment_counter(counter, "b")
	increment_counter(counter, "a")
	assert counter["a"] == 2
	assert counter["b"] == 1


# ============================================
# group_length_append
# ============================================

#============================================
def test_group_length_append_new_key():
	groups = {}
	group_length_append(groups, "bond", 3.5)
	assert groups == {"bond": [3.5]}


#============================================
def test_group_length_append_existing_key():
	groups = {"bond": [3.5]}
	group_length_append(groups, "bond", 7.0)
	assert groups == {"bond": [3.5, 7.0]}


#============================================
def test_group_length_append_converts_to_float():
	groups = {}
	group_length_append(groups, "key", 5)
	assert groups["key"] == [5.0]
	assert isinstance(groups["key"][0], float)


# ============================================
# compact_sorted_values
# ============================================

#============================================
def test_compact_sorted_values_sorted_order():
	result = compact_sorted_values([3.0, 1.0, 2.0])
	assert result == [pytest.approx(1.0), pytest.approx(2.0), pytest.approx(3.0)]


#============================================
def test_compact_sorted_values_empty():
	assert compact_sorted_values([]) == []


#============================================
def test_compact_sorted_values_preserves_precision():
	result = compact_sorted_values([1.123456789012])
	assert len(result) == 1
	assert result[0] == pytest.approx(1.123456789012)


# ============================================
# compact_value_counts
# ============================================

#============================================
def test_compact_value_counts_basic():
	result = compact_value_counts([1.0, 2.0, 1.0, 3.0, 2.0, 1.0])
	# sorted by value: 1.0 (3), 2.0 (2), 3.0 (1)
	assert len(result) == 3
	assert result[0]["value"] == pytest.approx(1.0)
	assert result[0]["count"] == 3
	assert result[1]["value"] == pytest.approx(2.0)
	assert result[1]["count"] == 2
	assert result[2]["value"] == pytest.approx(3.0)
	assert result[2]["count"] == 1


#============================================
def test_compact_value_counts_single():
	result = compact_value_counts([5.0])
	assert len(result) == 1
	assert result[0]["value"] == pytest.approx(5.0)
	assert result[0]["count"] == 1


#============================================
def test_compact_value_counts_empty():
	assert compact_value_counts([]) == []


# ============================================
# rounded_sorted_values
# ============================================

#============================================
def test_rounded_sorted_values_sorted():
	result = rounded_sorted_values([3.456, 1.234, 2.345])
	assert result == [pytest.approx(1.234), pytest.approx(2.345), pytest.approx(3.456)]


#============================================
def test_rounded_sorted_values_rounding():
	result = rounded_sorted_values([1.23456], decimals=2)
	assert result == [pytest.approx(1.23)]


#============================================
def test_rounded_sorted_values_empty():
	assert rounded_sorted_values([]) == []


# ============================================
# rounded_value_counts
# ============================================

#============================================
def test_rounded_value_counts_basic():
	result = rounded_value_counts([1.0001, 1.0002, 2.0001])
	# default decimals=3 -> 1.0 appears twice, 2.0 once
	assert len(result) == 2
	assert result[0]["length"] == pytest.approx(1.0)
	assert result[0]["count"] == 2
	assert result[1]["length"] == pytest.approx(2.0)
	assert result[1]["count"] == 1


#============================================
def test_rounded_value_counts_custom_decimals():
	result = rounded_value_counts([1.11, 1.12, 1.19], decimals=1)
	# rounded to 1 decimal: 1.1 (2 values), 1.2 (1 value)
	assert len(result) == 2
	assert result[0]["length"] == pytest.approx(1.1)
	assert result[0]["count"] == 2


#============================================
def test_rounded_value_counts_empty():
	assert rounded_value_counts([]) == []


# ============================================
# point_to_glyph_primitive_signed_distance
# ============================================

#============================================
def test_glyph_primitive_ellipse():
	prim = {"kind": "ellipse", "cx": 0.0, "cy": 0.0, "rx": 5.0, "ry": 5.0}
	# at center: -5
	assert point_to_glyph_primitive_signed_distance((0.0, 0.0), prim) == pytest.approx(-5.0)


#============================================
def test_glyph_primitive_box():
	prim = {"kind": "box", "box": (0.0, 0.0, 10.0, 10.0)}
	# inside at (5,5): signed distance is -5
	assert point_to_glyph_primitive_signed_distance((5.0, 5.0), prim) == pytest.approx(-5.0)


#============================================
def test_glyph_primitive_unknown_kind_no_box():
	prim = {"kind": "polygon"}
	result = point_to_glyph_primitive_signed_distance((0.0, 0.0), prim)
	assert result == float("inf")


#============================================
def test_glyph_primitive_unknown_kind_with_box():
	prim = {"kind": "polygon", "box": (0.0, 0.0, 10.0, 10.0)}
	result = point_to_glyph_primitive_signed_distance((5.0, 5.0), prim)
	assert result == pytest.approx(-5.0)


# ============================================
# point_to_glyph_primitives_signed_distance
# ============================================

#============================================
def test_glyph_primitives_signed_empty():
	assert point_to_glyph_primitives_signed_distance((0.0, 0.0), []) == float("inf")


#============================================
def test_glyph_primitives_signed_single():
	prim = {"kind": "box", "box": (0.0, 0.0, 10.0, 10.0)}
	result = point_to_glyph_primitives_signed_distance((5.0, 5.0), [prim])
	assert result < 0.0


#============================================
def test_glyph_primitives_signed_multiple_inside_one():
	prim_a = {"kind": "box", "box": (0.0, 0.0, 4.0, 4.0)}
	prim_b = {"kind": "box", "box": (10.0, 10.0, 20.0, 20.0)}
	# point (2,2) is inside prim_a (depth -2), outside prim_b
	result = point_to_glyph_primitives_signed_distance((2.0, 2.0), [prim_a, prim_b])
	assert result < 0.0


#============================================
def test_glyph_primitives_signed_outside_all():
	prim_a = {"kind": "box", "box": (0.0, 0.0, 4.0, 4.0)}
	prim_b = {"kind": "box", "box": (10.0, 10.0, 20.0, 20.0)}
	# point (7,7) is outside both
	result = point_to_glyph_primitives_signed_distance((7.0, 7.0), [prim_a, prim_b])
	assert result > 0.0


# ============================================
# point_to_glyph_primitives_distance
# ============================================

#============================================
def test_glyph_primitives_distance_inside():
	prim = {"kind": "box", "box": (0.0, 0.0, 10.0, 10.0)}
	# inside -> clamped to 0
	result = point_to_glyph_primitives_distance((5.0, 5.0), [prim])
	assert result == pytest.approx(0.0)


#============================================
def test_glyph_primitives_distance_outside():
	prim = {"kind": "box", "box": (0.0, 0.0, 10.0, 10.0)}
	# point (13, 5) is 3 units outside right edge
	result = point_to_glyph_primitives_distance((13.0, 5.0), [prim])
	assert result == pytest.approx(3.0)


#============================================
def test_glyph_primitives_distance_empty():
	result = point_to_glyph_primitives_distance((0.0, 0.0), [])
	assert result == float("inf")


#============================================
def test_glyph_primitives_distance_non_negative():
	prim = {"kind": "box", "box": (0.0, 0.0, 10.0, 10.0)}
	result = point_to_glyph_primitives_distance((5.0, 5.0), [prim])
	assert result >= 0.0
