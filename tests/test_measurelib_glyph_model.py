"""Tests for measurelib.glyph_model module."""

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

from measurelib.glyph_model import (
	canonicalize_label_text,
	font_family_candidates,
	glyph_char_advance,
	glyph_char_vertical_bounds,
	glyph_primitive_from_char,
	glyph_primitives_bounds,
	glyph_text_width,
	is_measurement_label,
	label_geometry_text,
	label_svg_estimated_box,
	label_svg_estimated_primitives,
	line_closest_endpoint_to_box,
	nearest_endpoint_to_box,
	point_to_label_signed_distance,
	primitive_center,
)


def _make_label(**overrides):
	"""Build a minimal label dict with sensible defaults."""
	label = {
		"text": "OH",
		"text_display": "OH",
		"text_raw": "OH",
		"canonical_text": "OH",
		"x": 50.0,
		"y": 30.0,
		"anchor": "start",
		"font_size": 12.0,
		"font_name": "sans-serif",
		"is_measurement_label": True,
	}
	label.update(overrides)
	return label


def _make_line(x1, y1, x2, y2, width=1.0):
	"""Build a minimal line dict."""
	return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "width": width, "linecap": "butt"}


#============================================
@pytest.mark.parametrize("text, expected", [
	("OH", True),
	("HO", True),
	("CH3", True),
	("C2H5", True),
	("SCH3", True),
	("SH", True),
	("Br", False),
	("N", False),
	("", False),
	("F", False),
])
def test_is_measurement_label(text, expected):
	assert is_measurement_label(text) is expected


#============================================
@pytest.mark.parametrize("text, expected", [
	("OH", "OH"),
	("HOH2C", "CH2OH"),
	("H2COH", "CH2OH"),
	("C2HOH", "CH2OH"),
	("Br", "Br"),
	("", ""),
])
def test_canonicalize_label_text(text, expected):
	assert canonicalize_label_text(text) == expected


#============================================
def test_canonicalize_label_text_unicode_subscript_2():
	assert canonicalize_label_text("CH\u20822") == "CH22"


#============================================
def test_canonicalize_label_text_unicode_subscript_3():
	assert canonicalize_label_text("CH\u2083") == "CH3"


#============================================
def test_label_geometry_text_with_display():
	label = _make_label(text_display="HO", text_raw="HO", text="OH")
	assert label_geometry_text(label) == "HO"


#============================================
def test_label_geometry_text_fallback_to_raw():
	label = _make_label(text_display="", text_raw="HO", text="OH")
	assert label_geometry_text(label) == "HO"


#============================================
def test_label_geometry_text_fallback_to_text():
	label = _make_label(text_display="", text_raw="", text="OH")
	assert label_geometry_text(label) == "OH"


#============================================
def test_label_geometry_text_all_empty():
	label = _make_label(text_display="", text_raw="", text="")
	assert label_geometry_text(label) == ""


#============================================
def test_font_family_candidates_simple():
	result = font_family_candidates("Arial")
	assert result[0] == "Arial"
	assert "DejaVu Sans" in result
	assert "sans-serif" in result


#============================================
def test_font_family_candidates_sans_serif():
	result = font_family_candidates("sans-serif")
	assert result[0] == "sans-serif"
	# No duplicates
	assert result.count("sans-serif") == 1


#============================================
def test_font_family_candidates_empty():
	result = font_family_candidates("")
	assert "sans-serif" in result
	assert len(result) >= 1


#============================================
def test_font_family_candidates_comma_separated():
	result = font_family_candidates("'Helvetica', Arial, sans-serif")
	assert result[0] == "Helvetica"
	assert "Arial" in result
	assert "sans-serif" in result
	# All unique
	assert len(result) == len(set(r.lower() for r in result))


#============================================
def test_glyph_char_advance_curved():
	# 'O' is in GLYPH_CURVED_CHAR_SET
	advance = glyph_char_advance(12.0, "O")
	assert advance == pytest.approx(12.0 * 0.62)


#============================================
def test_glyph_char_advance_stem():
	# 'H' is in GLYPH_STEM_CHAR_SET
	advance = glyph_char_advance(12.0, "H")
	assert advance == pytest.approx(12.0 * 0.58)


#============================================
def test_glyph_char_advance_narrow():
	# 'I' is in narrow set (I, L, 1)
	advance = glyph_char_advance(12.0, "I")
	assert advance == pytest.approx(12.0 * 0.38)


#============================================
def test_glyph_char_advance_wide():
	# 'W' is in wide set (W, M)
	advance = glyph_char_advance(12.0, "W")
	assert advance == pytest.approx(12.0 * 0.82)


#============================================
def test_glyph_char_advance_digit():
	advance = glyph_char_advance(12.0, "5")
	assert advance == pytest.approx(12.0 * 0.52)


#============================================
def test_glyph_char_advance_lowercase():
	advance = glyph_char_advance(12.0, "a")
	assert advance == pytest.approx(12.0 * 0.50)


#============================================
def test_glyph_char_advance_empty():
	advance = glyph_char_advance(12.0, "")
	assert advance == pytest.approx(12.0 * 0.55)


#============================================
def test_glyph_char_advance_min_font_size():
	# Font size below 1.0 should be clamped to 1.0.
	advance = glyph_char_advance(0.1, "O")
	assert advance == pytest.approx(1.0 * 0.62)


#============================================
def test_glyph_char_vertical_bounds_returns_tuple():
	top, bottom = glyph_char_vertical_bounds(100.0, 12.0, "O")
	assert isinstance(top, float)
	assert isinstance(bottom, float)


#============================================
def test_glyph_char_vertical_bounds_top_less_than_bottom():
	# In SVG Y-down coordinates, top < bottom.
	top, bottom = glyph_char_vertical_bounds(100.0, 12.0, "H")
	assert top < bottom


#============================================
def test_glyph_char_vertical_bounds_digit_shifted():
	top, bottom = glyph_char_vertical_bounds(100.0, 12.0, "2")
	# Digit baseline is shifted down by size * 0.22.
	local_baseline = 100.0 + (12.0 * 0.22)
	assert top == pytest.approx(local_baseline - (12.0 * 0.52))
	assert bottom == pytest.approx(local_baseline + (12.0 * 0.18))


#============================================
def test_glyph_char_vertical_bounds_lowercase():
	top, bottom = glyph_char_vertical_bounds(100.0, 12.0, "a")
	assert top == pytest.approx(100.0 - (12.0 * 0.60))
	assert bottom == pytest.approx(100.0 + (12.0 * 0.22))


#============================================
def test_glyph_text_width_single_char():
	width = glyph_text_width("O", 12.0)
	# Single character: just the advance, no tracking.
	expected = glyph_char_advance(12.0, "O")
	assert width == pytest.approx(expected)


#============================================
def test_glyph_text_width_two_chars():
	width = glyph_text_width("OH", 12.0)
	adv_o = glyph_char_advance(12.0, "O")
	adv_h = glyph_char_advance(12.0, "H")
	tracking = 12.0 * 0.04
	expected = adv_o + adv_h + tracking
	assert width == pytest.approx(expected)


#============================================
def test_glyph_text_width_empty():
	width = glyph_text_width("", 12.0)
	# Empty text returns font_size * 0.75.
	assert width == pytest.approx(12.0 * 0.75)


#============================================
def test_glyph_primitive_from_char_ellipse():
	prim = glyph_primitive_from_char("O", 0, 0.0, 10.0, 0.0, 12.0)
	assert prim["kind"] == "ellipse"
	assert prim["char"] == "O"
	assert prim["char_index"] == 0
	assert "cx" in prim
	assert "cy" in prim
	assert "rx" in prim
	assert "ry" in prim
	assert prim["cx"] == pytest.approx(5.0)
	assert prim["cy"] == pytest.approx(6.0)


#============================================
def test_glyph_primitive_from_char_box():
	prim = glyph_primitive_from_char("H", 1, 10.0, 20.0, 0.0, 12.0)
	assert prim["kind"] == "box"
	assert prim["char"] == "H"
	assert prim["char_index"] == 1
	assert "box" in prim
	box = prim["box"]
	assert len(box) == 4
	# Box should be inset from edges.
	assert box[0] > 10.0
	assert box[2] < 20.0


#============================================
def test_glyph_primitive_from_char_curved_c():
	prim = glyph_primitive_from_char("C", 0, 0.0, 10.0, 0.0, 12.0)
	assert prim["kind"] == "ellipse"
	# C uses rx_factor=0.35, ry_factor=0.43.
	assert prim["rx"] == pytest.approx(max(0.3, 10.0 * 0.35))
	assert prim["ry"] == pytest.approx(max(0.3, 12.0 * 0.43))


#============================================
def test_label_svg_estimated_primitives_oh():
	label = _make_label(text="OH", text_display="OH", font_size=12.0, anchor="start")
	prims = label_svg_estimated_primitives(label)
	assert len(prims) == 2
	# O should be ellipse, H should be box.
	assert prims[0]["kind"] == "ellipse"
	assert prims[0]["char"] == "O"
	assert prims[1]["kind"] == "box"
	assert prims[1]["char"] == "H"


#============================================
def test_label_svg_estimated_primitives_empty_text():
	label = _make_label(text="", text_display="", text_raw="")
	prims = label_svg_estimated_primitives(label)
	assert prims == []


#============================================
def test_label_svg_estimated_primitives_anchor_middle():
	label_start = _make_label(anchor="start", x=50.0)
	label_middle = _make_label(anchor="middle", x=50.0)
	prims_start = label_svg_estimated_primitives(label_start)
	prims_middle = label_svg_estimated_primitives(label_middle)
	# Middle anchor should shift primitives to the left relative to start.
	assert prims_middle[0]["cx"] < prims_start[0]["cx"]


#============================================
def test_label_svg_estimated_primitives_anchor_end():
	label_start = _make_label(anchor="start", x=50.0)
	label_end = _make_label(anchor="end", x=50.0)
	prims_start = label_svg_estimated_primitives(label_start)
	prims_end = label_svg_estimated_primitives(label_end)
	# End anchor should shift primitives further left.
	assert prims_end[0]["cx"] < prims_start[0]["cx"]


#============================================
def test_glyph_primitives_bounds_basic():
	prims = [
		{"kind": "ellipse", "cx": 5.0, "cy": 6.0, "rx": 3.0, "ry": 4.0},
		{"kind": "box", "box": (10.0, 2.0, 20.0, 10.0)},
	]
	bounds = glyph_primitives_bounds(prims)
	assert bounds is not None
	# x_min = min(5-3, 10) = 2.0, y_min = min(6-4, 2) = 2.0
	# x_max = max(5+3, 20) = 20.0, y_max = max(6+4, 10) = 10.0
	assert bounds[0] == pytest.approx(2.0)
	assert bounds[1] == pytest.approx(2.0)
	assert bounds[2] == pytest.approx(20.0)
	assert bounds[3] == pytest.approx(10.0)


#============================================
def test_glyph_primitives_bounds_empty():
	assert glyph_primitives_bounds([]) is None


#============================================
def test_glyph_primitives_bounds_single_ellipse():
	prims = [{"kind": "ellipse", "cx": 10.0, "cy": 20.0, "rx": 5.0, "ry": 3.0}]
	bounds = glyph_primitives_bounds(prims)
	assert bounds == pytest.approx((5.0, 17.0, 15.0, 23.0))


#============================================
def test_primitive_center_ellipse():
	prim = {"kind": "ellipse", "cx": 5.0, "cy": 6.0, "rx": 3.0, "ry": 4.0}
	center = primitive_center(prim)
	assert center == pytest.approx((5.0, 6.0))


#============================================
def test_primitive_center_box():
	prim = {"kind": "box", "box": (10.0, 20.0, 30.0, 40.0)}
	center = primitive_center(prim)
	assert center == pytest.approx((20.0, 30.0))


#============================================
def test_primitive_center_unknown_kind():
	prim = {"kind": "polygon"}
	assert primitive_center(prim) is None


#============================================
def test_primitive_center_box_no_box():
	prim = {"kind": "box", "box": None}
	assert primitive_center(prim) is None


#============================================
def test_label_svg_estimated_box_returns_4tuple():
	label = _make_label()
	box = label_svg_estimated_box(label)
	assert isinstance(box, tuple)
	assert len(box) == 4
	# All coordinates should be finite floats.
	for coord in box:
		assert math.isfinite(coord)


#============================================
def test_label_svg_estimated_box_start_anchor():
	label = _make_label(anchor="start", x=50.0, y=30.0, font_size=12.0)
	box = label_svg_estimated_box(label)
	x1, y1, x2, y2 = box
	# For start anchor, x1 should be near the label x.
	assert x1 < x2
	assert y1 < y2


#============================================
def test_label_svg_estimated_box_middle_anchor():
	label = _make_label(anchor="middle", x=50.0, y=30.0, font_size=12.0)
	box = label_svg_estimated_box(label)
	x1, y1, x2, y2 = box
	# For middle anchor, the box should be centered around x=50.
	mid_x = (x1 + x2) * 0.5
	assert mid_x == pytest.approx(50.0, abs=2.0)


#============================================
def test_line_closest_endpoint_to_box_first_closer():
	line = _make_line(0.0, 0.0, 100.0, 100.0)
	box = (5.0, 5.0, 15.0, 15.0)
	point, dist = line_closest_endpoint_to_box(line, box)
	assert point == pytest.approx((0.0, 0.0))
	assert dist < 10.0


#============================================
def test_line_closest_endpoint_to_box_second_closer():
	line = _make_line(100.0, 100.0, 10.0, 10.0)
	box = (5.0, 5.0, 15.0, 15.0)
	point, dist = line_closest_endpoint_to_box(line, box)
	assert point == pytest.approx((10.0, 10.0))
	assert dist == pytest.approx(0.0)


#============================================
def test_nearest_endpoint_to_box_basic():
	lines = [
		_make_line(0.0, 0.0, 50.0, 0.0),
		_make_line(100.0, 100.0, 200.0, 200.0),
		_make_line(8.0, 8.0, 80.0, 80.0),
	]
	box = (5.0, 5.0, 15.0, 15.0)
	point, dist, line_idx = nearest_endpoint_to_box(lines, [0, 1, 2], box)
	# Line 2 endpoint (8,8) is inside the box.
	assert point == pytest.approx((8.0, 8.0))
	assert dist == pytest.approx(0.0)
	assert line_idx == 2


#============================================
def test_nearest_endpoint_to_box_no_candidates():
	lines = [_make_line(0.0, 0.0, 10.0, 10.0)]
	point, dist, line_idx = nearest_endpoint_to_box(lines, [], (0.0, 0.0, 5.0, 5.0))
	assert point is None
	assert dist is None
	assert line_idx is None


#============================================
def test_nearest_endpoint_to_box_invalid_indexes():
	lines = [_make_line(0.0, 0.0, 10.0, 10.0)]
	point, dist, line_idx = nearest_endpoint_to_box(lines, [-1, 5], (0.0, 0.0, 5.0, 5.0))
	assert point is None
	assert dist is None
	assert line_idx is None


#============================================
def test_point_to_label_signed_distance_with_estimated_box():
	label = _make_label(x=50.0, y=30.0, font_size=12.0)
	box = label_svg_estimated_box(label)
	label["svg_estimated_box"] = box
	# Point far away should have positive distance.
	dist = point_to_label_signed_distance((200.0, 200.0), label)
	assert dist > 0.0
	assert math.isfinite(dist)


#============================================
def test_point_to_label_signed_distance_inside_box():
	label = _make_label(x=50.0, y=30.0, font_size=12.0)
	box = label_svg_estimated_box(label)
	label["svg_estimated_box"] = box
	# Point at the center of the box should be negative (inside).
	cx = (box[0] + box[2]) * 0.5
	cy = (box[1] + box[3]) * 0.5
	dist = point_to_label_signed_distance((cx, cy), label)
	assert dist < 0.0


#============================================
def test_point_to_label_signed_distance_with_primitives():
	label = _make_label(x=50.0, y=30.0, font_size=12.0)
	prims = label_svg_estimated_primitives(label)
	label["svg_estimated_primitives"] = prims
	# Point far away should have positive distance.
	dist = point_to_label_signed_distance((200.0, 200.0), label)
	assert dist > 0.0
	assert math.isfinite(dist)


#============================================
def test_point_to_label_signed_distance_no_geometry():
	label = {"text": "X"}
	dist = point_to_label_signed_distance((0.0, 0.0), label)
	assert dist == float("inf")
