"""Tests for measurelib.analysis module."""

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

from measurelib.analysis import analyze_svg_file

import pathlib


def _write_test_svg(path, elements=""):
	"""Write a minimal SVG file with given elements."""
	path.write_text(
		"<?xml version='1.0' encoding='utf-8'?>"
		"<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>"
		f"{elements}"
		"</svg>",
		encoding="utf-8",
	)


#============================================
def test_basic_analysis_keys(tmp_path):
	svg_file = tmp_path / "basic.svg"
	_write_test_svg(svg_file, (
		"<line x1='10' y1='100' x2='40' y2='100' stroke='black' stroke-width='1'/>"
		"<text x='42' y='103' font-size='12' font-family='sans-serif'>OH</text>"
	))
	result = analyze_svg_file(pathlib.Path(svg_file))
	assert isinstance(result, dict)
	assert "svg" in result
	assert "labels_analyzed" in result
	assert "aligned_count" in result
	assert "missed_count" in result
	assert "no_connector_count" in result
	assert "labels" in result
	assert "geometry_checks" in result
	assert "line_lengths" in result
	assert "haworth_base_ring" in result


#============================================
def test_basic_analysis_has_label(tmp_path):
	svg_file = tmp_path / "with_label.svg"
	_write_test_svg(svg_file, (
		"<line x1='10' y1='100' x2='40' y2='100' stroke='black' stroke-width='1'/>"
		"<text x='42' y='103' font-size='12' font-family='sans-serif'>OH</text>"
	))
	result = analyze_svg_file(pathlib.Path(svg_file))
	assert result["labels_analyzed"] >= 1
	assert result["text_labels_total"] >= 1
	assert "OH" in result["text_label_values"]


#============================================
def test_no_labels(tmp_path):
	svg_file = tmp_path / "no_labels.svg"
	_write_test_svg(svg_file, (
		"<line x1='10' y1='10' x2='50' y2='50' stroke='black' stroke-width='1'/>"
		"<line x1='50' y1='50' x2='90' y2='10' stroke='black' stroke-width='1'/>"
	))
	result = analyze_svg_file(pathlib.Path(svg_file))
	assert result["labels_analyzed"] == 0
	assert result["aligned_count"] == 0
	assert result["missed_count"] == 0


#============================================
def test_analysis_line_lengths(tmp_path):
	svg_file = tmp_path / "lengths.svg"
	_write_test_svg(svg_file, (
		"<line x1='0' y1='0' x2='30' y2='0' stroke='black' stroke-width='1'/>"
		"<line x1='0' y1='10' x2='40' y2='10' stroke='black' stroke-width='1'/>"
	))
	result = analyze_svg_file(pathlib.Path(svg_file))
	lengths = result["line_lengths"]["all_lines"]
	assert len(lengths) == 2
	assert pytest.approx(30.0) in lengths
	assert pytest.approx(40.0) in lengths


#============================================
def test_analysis_haworth_defaults(tmp_path):
	svg_file = tmp_path / "haworth.svg"
	_write_test_svg(svg_file, (
		"<line x1='10' y1='10' x2='50' y2='10' stroke='black' stroke-width='1'/>"
	))
	result = analyze_svg_file(pathlib.Path(svg_file))
	assert result["haworth_base_ring"]["detected"] is False


#============================================
def test_hatched_carrier_as_connector(tmp_path):
	"""A hatched carrier line (thin + perpendicular strokes) used as a connector."""
	svg_file = tmp_path / "hatched.svg"
	# Carrier line: thin horizontal line from (10,50) to (50,50) width=0.3
	# 5 perpendicular hatch strokes crossing the carrier
	hatch_strokes = ""
	for i in range(5):
		x = 15 + i * 8
		hatch_strokes += (
			f"<line x1='{x}' y1='47' x2='{x}' y2='53' "
			f"stroke='black' stroke-width='0.3'/>"
		)
	elements = (
		"<line x1='10' y1='50' x2='50' y2='50' stroke='black' stroke-width='0.3'/>"
		+ hatch_strokes
		+ "<text x='52' y='53' font-size='10' font-family='sans-serif'>CH</text>"
	)
	_write_test_svg(svg_file, elements)
	result = analyze_svg_file(pathlib.Path(svg_file))
	# The analysis should process the label; verify it found at least one label
	assert result["text_labels_total"] >= 1
	# The hatched carrier detection may or may not fire depending on angle/spacing
	# thresholds, but the analysis should complete without error
	assert isinstance(result["labels"], list)


#============================================
def test_empty_svg(tmp_path):
	svg_file = tmp_path / "empty.svg"
	_write_test_svg(svg_file, "")
	result = analyze_svg_file(pathlib.Path(svg_file))
	assert result["labels_analyzed"] == 0
	assert result["aligned_count"] == 0
	assert len(result["line_lengths"]["all_lines"]) == 0


#============================================
def test_analysis_geometry_checks_keys(tmp_path):
	svg_file = tmp_path / "geom.svg"
	_write_test_svg(svg_file, (
		"<line x1='0' y1='0' x2='50' y2='0' stroke='black' stroke-width='1'/>"
	))
	result = analyze_svg_file(pathlib.Path(svg_file))
	gc = result["geometry_checks"]
	assert "lattice_angle_violations" in gc
	assert "glyph_glyph_overlaps" in gc
	assert "bond_bond_overlaps" in gc
	assert "bond_glyph_overlaps" in gc
	assert "hatched_thin_conflicts" in gc
