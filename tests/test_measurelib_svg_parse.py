"""Tests for measurelib.svg_parse module."""

# Standard Library
import os
import sys

# Third Party
import defusedxml.ElementTree as ET
import pytest

# Local
import conftest
_tools_dir = os.path.join(conftest.repo_root(), "tools")
if _tools_dir not in sys.path:
	sys.path.insert(0, _tools_dir)

from measurelib.svg_parse import (
	collect_svg_labels,
	collect_svg_lines,
	collect_svg_ring_primitives,
	collect_svg_wedge_bonds,
	local_tag_name,
	node_is_overlay_group,
	parse_float,
	path_points,
	points_bbox,
	polygon_points,
	svg_number_tokens,
	svg_tag_with_namespace,
	visible_text,
)


SVG_NS = "http://www.w3.org/2000/svg"


#============================================
def test_local_tag_name_plain():
	assert local_tag_name("line") == "line"


#============================================
def test_local_tag_name_namespaced():
	assert local_tag_name("{http://www.w3.org/2000/svg}line") == "line"


#============================================
def test_local_tag_name_other_namespace():
	assert local_tag_name("{http://example.com/ns}circle") == "circle"


#============================================
@pytest.mark.parametrize("raw, default, expected", [
	("3.14", 0.0, 3.14),
	("  -7.5  ", 0.0, -7.5),
	("0", 99.0, 0.0),
	("abc", 5.0, 5.0),
	(None, 42.0, 42.0),
	("", 1.0, 1.0),
])
def test_parse_float(raw, default, expected):
	assert parse_float(raw, default) == pytest.approx(expected)


#============================================
@pytest.mark.parametrize("text, expected", [
	("10 20 30.5", [10.0, 20.0, 30.5]),
	("-5 3.2 -0.7", [-5.0, 3.2, -0.7]),
	("", []),
	("100", [100.0]),
	("1.5e2 -3e1", [150.0, -30.0]),
])
def test_svg_number_tokens(text, expected):
	result = svg_number_tokens(text)
	assert len(result) == len(expected)
	for a, b in zip(result, expected):
		assert a == pytest.approx(b)


#============================================
def test_points_bbox_normal():
	pts = [(1.0, 2.0), (5.0, 0.0), (3.0, 8.0)]
	bbox = points_bbox(pts)
	assert bbox == pytest.approx((1.0, 0.0, 5.0, 8.0))


#============================================
def test_points_bbox_empty():
	assert points_bbox([]) is None


#============================================
def test_points_bbox_single_point():
	bbox = points_bbox([(4.0, 7.0)])
	assert bbox == pytest.approx((4.0, 7.0, 4.0, 7.0))


#============================================
def test_polygon_points_basic():
	pts = polygon_points("0,0 10,0 10,10 0,10")
	assert len(pts) == 4
	assert pts[0] == pytest.approx((0.0, 0.0))
	assert pts[1] == pytest.approx((10.0, 0.0))
	assert pts[2] == pytest.approx((10.0, 10.0))
	assert pts[3] == pytest.approx((0.0, 10.0))


#============================================
def test_polygon_points_empty():
	pts = polygon_points("")
	assert pts == []


#============================================
def test_path_points_basic():
	pts = path_points("M 0 0 L 10 10")
	assert len(pts) == 2
	assert pts[0] == pytest.approx((0.0, 0.0))
	assert pts[1] == pytest.approx((10.0, 10.0))


#============================================
def test_path_points_multiple_segments():
	pts = path_points("M 5 5 L 15 15 L 25 5")
	assert len(pts) == 3
	assert pts[0] == pytest.approx((5.0, 5.0))
	assert pts[1] == pytest.approx((15.0, 15.0))
	assert pts[2] == pytest.approx((25.0, 5.0))


#============================================
def test_node_is_overlay_group_diagnostic():
	svg_str = f"<svg xmlns='{SVG_NS}'><g id='codex-glyph-bond-diagnostic-overlay'/></svg>"
	root = ET.fromstring(svg_str)
	group = list(root)[0]
	assert node_is_overlay_group(group) is True


#============================================
def test_node_is_overlay_group_noise():
	svg_str = f"<svg xmlns='{SVG_NS}'><g id='codex-overlay-noise'/></svg>"
	root = ET.fromstring(svg_str)
	group = list(root)[0]
	assert node_is_overlay_group(group) is True


#============================================
def test_node_is_overlay_group_label_diag_prefix():
	svg_str = f"<svg xmlns='{SVG_NS}'><g id='codex-label-diag-OH'/></svg>"
	root = ET.fromstring(svg_str)
	group = list(root)[0]
	assert node_is_overlay_group(group) is True


#============================================
def test_node_is_overlay_group_normal():
	svg_str = f"<svg xmlns='{SVG_NS}'><g id='molecules'/></svg>"
	root = ET.fromstring(svg_str)
	group = list(root)[0]
	assert node_is_overlay_group(group) is False


#============================================
def test_node_is_overlay_group_non_group():
	svg_str = f"<svg xmlns='{SVG_NS}'><rect id='codex-glyph-bond-diagnostic-overlay'/></svg>"
	root = ET.fromstring(svg_str)
	rect = list(root)[0]
	assert node_is_overlay_group(rect) is False


#============================================
def test_node_is_overlay_group_no_id():
	svg_str = f"<svg xmlns='{SVG_NS}'><g/></svg>"
	root = ET.fromstring(svg_str)
	group = list(root)[0]
	assert node_is_overlay_group(group) is False


#============================================
def test_collect_svg_lines_basic():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<line x1='0' y1='0' x2='10' y2='10' stroke-width='1.5' stroke-linecap='round'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	lines = collect_svg_lines(root)
	assert len(lines) == 1
	line = lines[0]
	assert line["x1"] == pytest.approx(0.0)
	assert line["y1"] == pytest.approx(0.0)
	assert line["x2"] == pytest.approx(10.0)
	assert line["y2"] == pytest.approx(10.0)
	assert line["width"] == pytest.approx(1.5)
	assert line["linecap"] == "round"


#============================================
def test_collect_svg_lines_default_width():
	svg_str = f"<svg xmlns='{SVG_NS}'><line x1='1' y1='2' x2='3' y2='4'/></svg>"
	root = ET.fromstring(svg_str)
	lines = collect_svg_lines(root)
	assert len(lines) == 1
	assert lines[0]["width"] == pytest.approx(1.0)
	assert lines[0]["linecap"] == "butt"


#============================================
def test_collect_svg_lines_excludes_overlay():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<g id='codex-glyph-bond-diagnostic-overlay'>"
		f"<line x1='0' y1='0' x2='10' y2='10'/>"
		f"</g>"
		f"<line x1='20' y1='20' x2='30' y2='30'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	lines = collect_svg_lines(root)
	assert len(lines) == 1
	assert lines[0]["x1"] == pytest.approx(20.0)


#============================================
def test_collect_svg_lines_multiple():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<line x1='0' y1='0' x2='10' y2='0'/>"
		f"<line x1='10' y1='0' x2='20' y2='0'/>"
		f"<line x1='20' y1='0' x2='30' y2='0'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	lines = collect_svg_lines(root)
	assert len(lines) == 3


#============================================
def test_collect_svg_labels_basic():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<text x='50' y='30' font-size='14' font-family='Arial' text-anchor='middle'>OH</text>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	labels = collect_svg_labels(root)
	assert len(labels) == 1
	label = labels[0]
	assert label["text"] == "OH"
	assert label["text_raw"] == "OH"
	assert label["text_display"] == "OH"
	assert label["canonical_text"] == "OH"
	assert label["x"] == pytest.approx(50.0)
	assert label["y"] == pytest.approx(30.0)
	assert label["anchor"] == "middle"
	assert label["font_size"] == pytest.approx(14.0)
	assert label["font_name"] == "Arial"
	assert label["is_measurement_label"] is True


#============================================
def test_collect_svg_labels_not_measurement():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<text x='10' y='10' font-size='12'>Br</text>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	labels = collect_svg_labels(root)
	assert len(labels) == 1
	assert labels[0]["is_measurement_label"] is False


#============================================
def test_collect_svg_labels_skips_empty_text():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<text x='10' y='10' font-size='12'></text>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	labels = collect_svg_labels(root)
	assert len(labels) == 0


#============================================
def test_collect_svg_labels_defaults():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<text>CH3</text>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	labels = collect_svg_labels(root)
	assert len(labels) == 1
	label = labels[0]
	assert label["x"] == pytest.approx(0.0)
	assert label["y"] == pytest.approx(0.0)
	assert label["anchor"] == "start"
	assert label["font_size"] == pytest.approx(12.0)
	assert label["font_name"] == "sans-serif"


#============================================
def test_collect_svg_ring_primitives_polygon():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 20,0 20,20 0,20' fill='black'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	prims = collect_svg_ring_primitives(root)
	assert len(prims) == 1
	prim = prims[0]
	assert prim["kind"] == "polygon"
	assert prim["bbox"] == pytest.approx((0.0, 0.0, 20.0, 20.0))
	assert prim["centroid"] == pytest.approx((10.0, 10.0))


#============================================
def test_collect_svg_ring_primitives_path():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<path d='M 5 5 L 15 5 L 15 15 L 5 15 Z' fill='red'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	prims = collect_svg_ring_primitives(root)
	assert len(prims) == 1
	assert prims[0]["kind"] == "path"
	assert prims[0]["bbox"] == pytest.approx((5.0, 5.0, 15.0, 15.0))


#============================================
def test_collect_svg_ring_primitives_skips_unfilled():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 10,0 10,10' fill='none'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	prims = collect_svg_ring_primitives(root)
	assert len(prims) == 0


#============================================
def test_collect_svg_ring_primitives_skips_transparent():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 10,0 10,10' fill='transparent'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	prims = collect_svg_ring_primitives(root)
	assert len(prims) == 0


#============================================
def test_collect_svg_ring_primitives_skips_no_fill():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 10,0 10,10'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	prims = collect_svg_ring_primitives(root)
	assert len(prims) == 0


#============================================
def test_collect_svg_wedge_bonds_narrow_polygon():
	# Create a narrow wedge-like polygon: long in x, narrow in y.
	# Aspect ratio should be > 1.8 and spine_length > 3.
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 20,1 20,-1' fill='black'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	wedges = collect_svg_wedge_bonds(root)
	assert len(wedges) == 1
	wedge = wedges[0]
	assert "points" in wedge
	assert "bbox" in wedge
	assert "spine_start" in wedge
	assert "spine_end" in wedge
	assert "fill" in wedge
	assert wedge["fill"] == "black"


#============================================
def test_collect_svg_wedge_bonds_rejects_square():
	# A roughly square polygon should be filtered out (aspect ratio < 1.8).
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 10,0 10,10 0,10' fill='black'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	wedges = collect_svg_wedge_bonds(root)
	assert len(wedges) == 0


#============================================
def test_collect_svg_wedge_bonds_rejects_unfilled():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 20,1 20,-1' fill='none'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	wedges = collect_svg_wedge_bonds(root)
	assert len(wedges) == 0


#============================================
def test_collect_svg_wedge_bonds_rejects_too_small():
	# A very small polygon with spine_length < 3 should be rejected.
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 2,0.1 2,-0.1' fill='black'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	wedges = collect_svg_wedge_bonds(root)
	assert len(wedges) == 0


#============================================
def test_collect_svg_wedge_bonds_rejects_too_few_points():
	# Fewer than 3 points should be rejected.
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<polygon points='0,0 20,1' fill='black'/>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	wedges = collect_svg_wedge_bonds(root)
	assert len(wedges) == 0


#============================================
def test_svg_tag_with_namespace_present():
	svg_str = f"<svg xmlns='{SVG_NS}'/>"
	root = ET.fromstring(svg_str)
	result = svg_tag_with_namespace(root, "line")
	assert result == f"{{{SVG_NS}}}line"


#============================================
def test_svg_tag_with_namespace_absent():
	svg_str = "<svg/>"
	root = ET.fromstring(svg_str)
	result = svg_tag_with_namespace(root, "line")
	assert result == "line"


#============================================
def test_visible_text_plain():
	svg_str = f"<svg xmlns='{SVG_NS}'><text>Hello</text></svg>"
	root = ET.fromstring(svg_str)
	text_node = list(root)[0]
	assert visible_text(text_node) == "Hello"


#============================================
def test_visible_text_with_tspan():
	svg_str = (
		f"<svg xmlns='{SVG_NS}'>"
		f"<text><tspan>CH</tspan><tspan>3</tspan></text>"
		f"</svg>"
	)
	root = ET.fromstring(svg_str)
	text_node = list(root)[0]
	assert visible_text(text_node) == "CH3"


#============================================
def test_visible_text_whitespace_removed():
	svg_str = f"<svg xmlns='{SVG_NS}'><text>  O H  </text></svg>"
	root = ET.fromstring(svg_str)
	text_node = list(root)[0]
	assert visible_text(text_node) == "OH"


#============================================
def test_visible_text_empty():
	svg_str = f"<svg xmlns='{SVG_NS}'><text></text></svg>"
	root = ET.fromstring(svg_str)
	text_node = list(root)[0]
	assert visible_text(text_node) == ""
