"""Tests for measurelib.diagnostic_svg module."""

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

from measurelib.diagnostic_svg import (
	clip_infinite_line_to_bounds,
	diagnostic_bounds,
	diagnostic_color,
	metric_alignment_center,
	metric_endpoint,
	select_alignment_primitive,
	viewbox_bounds,
	write_diagnostic_svg,
)

import defusedxml.ElementTree as ET


#============================================
def test_viewbox_bounds_valid():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 100'></svg>")
	result = viewbox_bounds(root)
	assert result == (0.0, 0.0, 200.0, 100.0)


#============================================
def test_viewbox_bounds_offset():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg' viewBox='10 20 300 150'></svg>")
	result = viewbox_bounds(root)
	assert result == (10.0, 20.0, 310.0, 170.0)


#============================================
def test_viewbox_bounds_missing():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
	result = viewbox_bounds(root)
	assert result is None


#============================================
def test_viewbox_bounds_invalid_not_enough_tokens():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200'></svg>")
	result = viewbox_bounds(root)
	assert result is None


#============================================
def test_viewbox_bounds_zero_width():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 0 100'></svg>")
	result = viewbox_bounds(root)
	assert result is None


#============================================
def test_viewbox_bounds_zero_height():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 0'></svg>")
	result = viewbox_bounds(root)
	assert result is None


#============================================
def test_diagnostic_bounds_with_viewbox():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 100'></svg>")
	result = diagnostic_bounds(root, lines=[], labels=[])
	assert result == (0.0, 0.0, 200.0, 100.0)


#============================================
def test_diagnostic_bounds_from_lines():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
	lines = [{"x1": 10.0, "y1": 20.0, "x2": 50.0, "y2": 60.0}]
	labels = []
	result = diagnostic_bounds(root, lines=lines, labels=labels)
	assert result[0] == pytest.approx(10.0 - 8.0)
	assert result[1] == pytest.approx(20.0 - 8.0)
	assert result[2] == pytest.approx(50.0 + 8.0)
	assert result[3] == pytest.approx(60.0 + 8.0)


#============================================
def test_diagnostic_bounds_from_labels():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
	labels = [{"svg_estimated_box": [5.0, 10.0, 40.0, 50.0]}]
	result = diagnostic_bounds(root, lines=[], labels=labels)
	assert result[0] == pytest.approx(5.0 - 8.0)
	assert result[1] == pytest.approx(10.0 - 8.0)
	assert result[2] == pytest.approx(40.0 + 8.0)
	assert result[3] == pytest.approx(50.0 + 8.0)


#============================================
def test_diagnostic_bounds_empty():
	root = ET.fromstring("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
	result = diagnostic_bounds(root, lines=[], labels=[])
	assert result == (-100.0, -100.0, 100.0, 100.0)


#============================================
def test_clip_infinite_line_horizontal():
	bounds = (0.0, 0.0, 100.0, 100.0)
	result = clip_infinite_line_to_bounds((50.0, 50.0), (70.0, 50.0), bounds)
	assert result is not None
	pa, pb = result
	# Horizontal line at y=50 should cross x=0 and x=100
	xs = sorted([pa[0], pb[0]])
	assert xs[0] == pytest.approx(0.0, abs=1e-6)
	assert xs[1] == pytest.approx(100.0, abs=1e-6)
	assert pa[1] == pytest.approx(50.0, abs=1e-6)
	assert pb[1] == pytest.approx(50.0, abs=1e-6)


#============================================
def test_clip_infinite_line_diagonal():
	bounds = (0.0, 0.0, 100.0, 100.0)
	result = clip_infinite_line_to_bounds((10.0, 10.0), (20.0, 20.0), bounds)
	assert result is not None
	pa, pb = result
	# Diagonal line y=x should cross (0,0) and (100,100)
	points_sorted = sorted([pa, pb], key=lambda p: p[0])
	assert points_sorted[0][0] == pytest.approx(0.0, abs=1e-6)
	assert points_sorted[0][1] == pytest.approx(0.0, abs=1e-6)
	assert points_sorted[1][0] == pytest.approx(100.0, abs=1e-6)
	assert points_sorted[1][1] == pytest.approx(100.0, abs=1e-6)


#============================================
def test_clip_infinite_line_no_crossing():
	# Line entirely outside bounds
	bounds = (0.0, 0.0, 10.0, 10.0)
	# Line at y=50 never crosses a box from 0,0 to 10,10
	result = clip_infinite_line_to_bounds((20.0, 50.0), (30.0, 50.0), bounds)
	assert result is None


#============================================
def test_clip_infinite_line_degenerate_point():
	bounds = (0.0, 0.0, 100.0, 100.0)
	result = clip_infinite_line_to_bounds((50.0, 50.0), (50.0, 50.0), bounds)
	assert result is None


#============================================
def test_clip_infinite_line_vertical():
	bounds = (0.0, 0.0, 100.0, 100.0)
	result = clip_infinite_line_to_bounds((30.0, 40.0), (30.0, 60.0), bounds)
	assert result is not None
	pa, pb = result
	ys = sorted([pa[1], pb[1]])
	assert ys[0] == pytest.approx(0.0, abs=1e-6)
	assert ys[1] == pytest.approx(100.0, abs=1e-6)
	assert pa[0] == pytest.approx(30.0, abs=1e-6)


#============================================
@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5, 6])
def test_diagnostic_color_aligned_green(index):
	color = diagnostic_color(index, aligned=True)
	assert isinstance(color, str)
	assert color.startswith("#")
	# green/teal family colors all have significant green component
	# check that it is from the green palette
	green_palette = ["#2a9d8f", "#06d6a0", "#40916c", "#52b788", "#74c69d", "#95d5b2"]
	assert color in green_palette


#============================================
@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5, 6])
def test_diagnostic_color_not_aligned_red(index):
	color = diagnostic_color(index, aligned=False)
	assert isinstance(color, str)
	assert color.startswith("#")
	red_palette = ["#d00000", "#e85d04", "#dc2f02", "#f48c06", "#e63946", "#ff6b6b"]
	assert color in red_palette


#============================================
@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5, 6])
def test_diagnostic_color_neutral(index):
	color = diagnostic_color(index, aligned=None)
	assert isinstance(color, str)
	assert color.startswith("#")
	neutral_palette = ["#ff006e", "#3a86ff", "#ffbe0b", "#2a9d8f", "#8338ec", "#fb5607"]
	assert color in neutral_palette


#============================================
def test_diagnostic_color_cycles_palette():
	color_a = diagnostic_color(0, aligned=True)
	color_b = diagnostic_color(6, aligned=True)
	assert color_a == color_b


#============================================
def test_metric_alignment_center_valid():
	metric = {"alignment_center_point": [10, 20]}
	result = metric_alignment_center(metric)
	assert result == (10.0, 20.0)


#============================================
def test_metric_alignment_center_missing_key():
	metric = {"other_key": 123}
	result = metric_alignment_center(metric)
	assert result is None


#============================================
def test_metric_alignment_center_invalid_type():
	metric = {"alignment_center_point": "not_a_list"}
	result = metric_alignment_center(metric)
	assert result is None


#============================================
def test_metric_alignment_center_wrong_length():
	metric = {"alignment_center_point": [1]}
	result = metric_alignment_center(metric)
	assert result is None


#============================================
def test_metric_alignment_center_non_numeric():
	metric = {"alignment_center_point": ["abc", "def"]}
	result = metric_alignment_center(metric)
	assert result is None


#============================================
def test_metric_endpoint_valid():
	metric = {"endpoint": [5, 15]}
	result = metric_endpoint(metric)
	assert result == (5.0, 15.0)


#============================================
def test_metric_endpoint_missing():
	metric = {}
	result = metric_endpoint(metric)
	assert result is None


#============================================
def test_metric_endpoint_invalid_type():
	metric = {"endpoint": 42}
	result = metric_endpoint(metric)
	assert result is None


#============================================
def test_metric_endpoint_wrong_length():
	metric = {"endpoint": [1, 2, 3]}
	result = metric_endpoint(metric)
	assert result is None


#============================================
def test_select_alignment_primitive_by_char():
	label = {
		"svg_estimated_primitives": [
			{"char": "H", "kind": "box", "box": [20, 10, 30, 20], "char_index": 1},
			{"char": "O", "kind": "ellipse", "cx": 10.0, "cy": 15.0, "rx": 4.0, "ry": 5.0, "char_index": 0},
		],
	}
	metric = {
		"alignment_center_char": "O",
		"alignment_center_point": [10.0, 15.0],
	}
	result = select_alignment_primitive(label, metric)
	assert result is not None
	assert result["char"] == "O"


#============================================
def test_select_alignment_primitive_no_primitives():
	label = {"svg_estimated_primitives": []}
	metric = {"alignment_center_char": "O", "alignment_center_point": [10.0, 15.0]}
	result = select_alignment_primitive(label, metric)
	assert result is None


#============================================
def test_select_alignment_primitive_missing_key():
	label = {}
	metric = {"alignment_center_char": "O"}
	result = select_alignment_primitive(label, metric)
	assert result is None


#============================================
def test_select_alignment_primitive_closest_when_multiple():
	label = {
		"svg_estimated_primitives": [
			{"char": "O", "kind": "ellipse", "cx": 100.0, "cy": 100.0, "rx": 4.0, "ry": 5.0, "char_index": 0},
			{"char": "O", "kind": "ellipse", "cx": 10.0, "cy": 15.0, "rx": 4.0, "ry": 5.0, "char_index": 1},
		],
	}
	metric = {
		"alignment_center_char": "O",
		"alignment_center_point": [10.0, 15.0],
	}
	result = select_alignment_primitive(label, metric)
	assert result is not None
	assert result["cx"] == pytest.approx(10.0)
	assert result["cy"] == pytest.approx(15.0)


#============================================
def test_write_diagnostic_svg_includes_bond_len_annotation(tmp_path):
	svg_path = tmp_path / "input.svg"
	out_path = tmp_path / "out.svg"
	svg_path.write_text(
		(
			"<?xml version='1.0' encoding='utf-8'?>"
			"<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'>"
			"<line x1='10' y1='10' x2='20' y2='10' stroke='#000' stroke-width='1'/>"
			"<text x='30' y='30' text-anchor='start' font-family='sans-serif' font-size='12'>OH</text>"
			"</svg>"
		),
		encoding="utf-8",
	)
	lines = [{"x1": 10.0, "y1": 10.0, "x2": 20.0, "y2": 10.0, "width": 1.0}]
	labels = [{"text": "OH", "svg_estimated_primitives": [], "svg_estimated_box": [30.0, 18.0, 44.0, 32.0]}]
	label_metrics = [
		{
			"label_index": 0,
			"connector_line_index": 0,
			"endpoint": [20.0, 10.0],
			"aligned": True,
			"endpoint_signed_distance_to_glyph_body": 1.5,
			"endpoint_perpendicular_distance_to_alignment_center": 0.03,
			"endpoint_alignment_error": 0.2,
			"bond_len": 10.0,
		}
	]
	write_diagnostic_svg(
		svg_path=svg_path,
		output_path=out_path,
		lines=lines,
		labels=labels,
		label_metrics=label_metrics,
	)
	out_text = out_path.read_text(encoding="utf-8")
	assert "bond_len=10.00" in out_text
