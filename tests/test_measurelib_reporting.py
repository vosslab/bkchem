"""Tests for measurelib.reporting module."""

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

from measurelib.reporting import (
	format_stats_line,
	json_summary_compact,
	summary_stats,
	text_report,
	top_misses,
	violation_summary,
	JSON_SUMMARY_EXCLUDE_KEYS,
)


def _make_minimal_file_report():
	"""Build a minimal valid file report dict for testing."""
	return {
		"svg": "/tmp/test.svg",
		"diagnostic_svg": None,
		"text_labels_total": 1,
		"text_label_values": ["OH"],
		"labels_analyzed": 1,
		"aligned_count": 1,
		"missed_count": 0,
		"no_connector_count": 0,
		"alignment_outside_tolerance_count": 0,
		"lattice_angle_violation_count": 0,
		"glyph_glyph_overlap_count": 0,
		"bond_bond_overlap_count": 0,
		"hatched_thin_conflict_count": 0,
		"bond_glyph_overlap_count": 0,
		"wedge_bond_count": 0,
		"labels": [{
			"label_index": 0, "text": "OH", "text_raw": "OH",
			"aligned": True, "reason": "ok",
			"endpoint": [10.0, 20.0],
			"endpoint_alignment_error": 0.5,
			"endpoint_distance_to_target": 0.5,
			"endpoint_distance_to_glyph_body": 1.0,
			"endpoint_signed_distance_to_glyph_body": 1.0,
			"endpoint_gap_distance_to_glyph_body": 1.0,
			"endpoint_penetration_depth_to_glyph_body": 0.0,
			"endpoint_perpendicular_distance_to_alignment_center": 0.3,
			"alignment_center_point": [12.0, 20.0],
			"alignment_center_char": "O",
			"alignment_tolerance": 1.5,
			"alignment_score": 0.667,
			"connector_line_index": 0,
			"hull_boundary_points": None,
			"hull_ellipse_fit": None,
			"hull_contact_point": None,
			"hull_signed_gap_along_bond": None,
			"optical_gate_debug": None,
			"alignment_mode": "independent_glyph_primitives",
		}],
		"geometry_checks": {
			"bond_glyph_gap_tolerance": 0.65,
			"lattice_angle_violations": [],
			"glyph_glyph_overlaps": [],
			"bond_bond_overlaps": [],
			"hatched_thin_conflicts": [],
			"hashed_carrier_map": {},
			"bond_glyph_overlaps": [],
		},
		"haworth_base_ring": {"detected": False, "excluded": False, "line_indexes": [], "line_count": 0,
			"primitive_indexes": [], "primitive_count": 0, "node_count": 0, "centroid": None, "radius": 0.0, "source": None},
		"checked_line_indexes": [0],
		"checked_bond_line_indexes": [0],
		"excluded_line_indexes": [],
		"decorative_hatched_stroke_indexes": [],
		"decorative_hatched_stroke_count": 0,
		"line_lengths": {"all_lines": [10.0], "checked_lines_raw": [10.0], "checked_lines": [10.0],
			"connector_lines": [10.0], "non_connector_lines": [],
			"excluded_haworth_base_ring_lines": [], "decorative_hatched_stroke_lines": []},
		"line_lengths_rounded_sorted": {"all_lines": [10.0], "checked_lines_raw": [10.0], "checked_lines": [10.0],
			"connector_lines": [10.0], "non_connector_lines": [],
			"excluded_haworth_base_ring_lines": [], "decorative_hatched_stroke_lines": []},
		"line_lengths_grouped": {"checked_bonds_by_quadrant": {}, "checked_bonds_by_ring_region": {},
			"checked_bonds_by_quadrant_ring_region": {}},
		"line_lengths_grouped_rounded_sorted": {"checked_bonds_by_quadrant": {}, "checked_bonds_by_ring_region": {},
			"checked_bonds_by_quadrant_ring_region": {}},
		"line_length_rounded_counts": {"all_lines": [{"length": 10.0, "count": 1}], "checked_lines_raw": [{"length": 10.0, "count": 1}],
			"checked_lines": [{"length": 10.0, "count": 1}], "connector_lines": [{"length": 10.0, "count": 1}],
			"non_connector_lines": [], "excluded_haworth_base_ring_lines": [], "decorative_hatched_stroke_lines": []},
		"line_length_stats": {"all_lines": {"count": 1, "min": 10.0, "max": 10.0, "mean": 10.0, "stddev": 0.0, "coefficient_of_variation": 0.0},
			"checked_lines_raw": {"count": 1, "min": 10.0, "max": 10.0, "mean": 10.0, "stddev": 0.0, "coefficient_of_variation": 0.0},
			"checked_lines": {"count": 1, "min": 10.0, "max": 10.0, "mean": 10.0, "stddev": 0.0, "coefficient_of_variation": 0.0},
			"connector_lines": {"count": 1, "min": 10.0, "max": 10.0, "mean": 10.0, "stddev": 0.0, "coefficient_of_variation": 0.0},
			"non_connector_lines": {"count": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "stddev": 0.0, "coefficient_of_variation": 0.0},
			"excluded_haworth_base_ring_lines": {"count": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "stddev": 0.0, "coefficient_of_variation": 0.0},
			"decorative_hatched_stroke_lines": {"count": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "stddev": 0.0, "coefficient_of_variation": 0.0}},
	}


#============================================
def test_summary_stats_basic_fields():
	report = _make_minimal_file_report()
	result = summary_stats([report])
	assert result["files_analyzed"] == 1
	assert result["labels_analyzed"] == 1
	assert result["aligned_labels"] == 1
	assert result["missed_labels"] == 0
	assert result["alignment_rate"] == pytest.approx(1.0)


#============================================
def test_summary_stats_zero_files():
	result = summary_stats([])
	assert result["files_analyzed"] == 0
	assert result["labels_analyzed"] == 0
	assert result["alignment_rate"] == pytest.approx(0.0)


#============================================
def test_summary_stats_bond_length_fields():
	report = _make_minimal_file_report()
	result = summary_stats([report])
	assert result["total_bonds_detected"] == 1
	assert result["bond_length_stats_all"]["count"] == 1
	assert result["bond_length_stats_all"]["mean"] == pytest.approx(10.0)


#============================================
def test_summary_stats_alignment_distance():
	report = _make_minimal_file_report()
	result = summary_stats([report])
	assert result["max_endpoint_distance_to_target"] == pytest.approx(0.5)
	assert result["mean_endpoint_distance_to_target"] == pytest.approx(0.5)


#============================================
def test_summary_stats_violation_counts():
	report = _make_minimal_file_report()
	result = summary_stats([report])
	assert result["lattice_angle_violation_count"] == 0
	assert result["glyph_glyph_overlap_count"] == 0
	assert result["bond_bond_overlap_count"] == 0
	assert result["bond_glyph_overlap_count"] == 0


#============================================
def test_summary_stats_alignment_by_glyph():
	report = _make_minimal_file_report()
	result = summary_stats([report])
	assert "OH" in result["alignment_by_glyph"]
	glyph = result["alignment_by_glyph"]["OH"]
	assert glyph["count"] == 1
	assert glyph["aligned_count"] == 1
	assert glyph["alignment_rate"] == pytest.approx(1.0)


#============================================
def test_top_misses_with_missed_label():
	report = _make_minimal_file_report()
	report["labels"][0]["aligned"] = False
	report["labels"][0]["reason"] = "bond_line_not_pointing_to_primitive_center"
	entries = top_misses([report])
	assert len(entries) == 1
	assert entries[0]["text"] == "OH"
	assert entries[0]["distance"] == pytest.approx(0.5)


#============================================
def test_top_misses_all_aligned():
	report = _make_minimal_file_report()
	entries = top_misses([report])
	assert len(entries) == 0


#============================================
def test_top_misses_limit():
	report = _make_minimal_file_report()
	report["labels"][0]["aligned"] = False
	entries = top_misses([report], limit=0)
	assert len(entries) == 0


#============================================
def test_top_misses_limit_capped():
	report = _make_minimal_file_report()
	report["labels"][0]["aligned"] = False
	entries = top_misses([report], limit=1)
	assert len(entries) == 1


#============================================
def test_format_stats_line_with_data():
	stats = {"count": 5, "min": 1.0, "max": 10.0, "mean": 5.5, "stddev": 2.1}
	result = format_stats_line("Test", stats)
	assert "Test" in result
	assert "n=5" in result
	assert "min=1.000" in result
	assert "max=10.000" in result
	assert "mean=5.500" in result
	assert "sd=2.100" in result


#============================================
def test_format_stats_line_zero_count():
	stats = {"count": 0}
	result = format_stats_line("Empty", stats)
	assert result == "Empty: (none)"


#============================================
def test_format_stats_line_missing_count():
	stats = {}
	result = format_stats_line("Missing", stats)
	assert result == "Missing: (none)"


#============================================
def test_violation_summary_keys():
	summary = {
		"alignment_outside_tolerance_count": 2,
		"missed_labels": 1,
		"labels_without_connector": 0,
		"lattice_angle_violation_count": 0,
		"glyph_glyph_overlap_count": 0,
		"bond_bond_overlap_count": 1,
		"bond_glyph_overlap_count": 0,
		"hatched_thin_conflict_count": 0,
		"lattice_angle_violation_examples": [],
		"bond_glyph_overlap_examples": [],
		"bond_bond_overlap_examples": [],
		"alignment_label_type_stats": {},
	}
	result = violation_summary(summary, top_misses=[])
	assert result["alignment_outside_tolerance_count"] == 2
	assert result["missed_labels"] == 1
	assert result["bond_bond_overlap_count"] == 1
	assert result["total_violation_count"] == 3  # 2 + 0 + 0 + 1 + 0 + 0
	assert "top_misses" in result


#============================================
def test_violation_summary_total_violation_count():
	summary = {
		"alignment_outside_tolerance_count": 1,
		"lattice_angle_violation_count": 2,
		"glyph_glyph_overlap_count": 3,
		"bond_bond_overlap_count": 4,
		"bond_glyph_overlap_count": 5,
		"hatched_thin_conflict_count": 6,
	}
	result = violation_summary(summary, top_misses=[])
	assert result["total_violation_count"] == 1 + 2 + 3 + 4 + 5 + 6


#============================================
def test_json_summary_compact_removes_excluded_keys():
	summary = {
		"files_analyzed": 1,
		"alignment_rate": 0.95,
		"glyph_alignment_data_points": [{"a": 1}],
		"alignment_by_glyph": {"OH": {}},
		"bond_lengths_rounded_sorted_all": [10.0],
	}
	result = json_summary_compact(summary)
	assert "files_analyzed" in result
	assert "alignment_rate" in result
	assert "glyph_alignment_data_points" not in result
	assert "alignment_by_glyph" not in result
	assert "bond_lengths_rounded_sorted_all" not in result


#============================================
def test_json_summary_compact_all_excluded_keys():
	summary = {key: "value" for key in JSON_SUMMARY_EXCLUDE_KEYS}
	summary["keep_me"] = True
	result = json_summary_compact(summary)
	assert "keep_me" in result
	for key in JSON_SUMMARY_EXCLUDE_KEYS:
		assert key not in result


#============================================
def test_text_report_returns_string():
	report = _make_minimal_file_report()
	stats = summary_stats([report])
	misses = top_misses([report])
	result = text_report(stats, misses, input_glob="*.svg", exclude_haworth_base_ring=True)
	assert isinstance(result, str)
	assert "ALIGNMENT REPORT" in result


#============================================
def test_text_report_contains_summary_sections():
	report = _make_minimal_file_report()
	stats = summary_stats([report])
	misses = top_misses([report])
	result = text_report(stats, misses, input_glob="*.svg", exclude_haworth_base_ring=False)
	assert "ALIGNMENT SUMMARY" in result
	assert "GEOMETRY CHECKS" in result
	assert "BOND LENGTH STATISTICS" in result
	assert "TOP MISSES" in result


#============================================
def test_text_report_haworth_tags():
	report = _make_minimal_file_report()
	stats = summary_stats([report])
	misses = top_misses([report])
	result_excluded = text_report(stats, misses, input_glob="*.svg", exclude_haworth_base_ring=True)
	assert "excluded" in result_excluded
	result_included = text_report(stats, misses, input_glob="*.svg", exclude_haworth_base_ring=False)
	assert "included" in result_included
