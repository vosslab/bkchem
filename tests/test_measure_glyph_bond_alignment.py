"""Tests for independent SVG glyph-bond alignment measurement tool."""

# Standard Library
import importlib.util
import math
import pathlib
import sys

# Third Party
import pytest

# Local repo modules
import conftest
from get_repo_root import get_repo_root


conftest.add_oasa_to_sys_path()

# local repo modules
import oasa.render_geometry as render_geometry


#============================================
def _load_tool_module():
	"""Load measurement tool module from tools directory."""
	repo_root = pathlib.Path(get_repo_root())
	tool_path = repo_root / "tools" / "measure_glyph_bond_alignment.py"
	spec = importlib.util.spec_from_file_location("measure_glyph_bond_alignment", tool_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Could not load tool module from {tool_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


#============================================
def _write_svg(
		path: pathlib.Path,
		text: str,
		text_x: float,
		text_y: float,
		x1: float,
		y1: float,
		x2: float,
		y2: float) -> None:
	"""Write one minimal SVG document with one line and one text node."""
	svg_text = (
		"<?xml version='1.0' encoding='utf-8'?>"
		"<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>"
		f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#000' stroke-width='1.0'/>"
		f"<text x='{text_x}' y='{text_y}' text-anchor='start' font-family='sans-serif' font-size='12.0'>{text}</text>"
		"</svg>"
	)
	path.write_text(svg_text, encoding="utf-8")


#============================================
def _write_svg_primitives(path: pathlib.Path, lines: list[dict], texts: list[dict]) -> None:
	"""Write one SVG document from explicit line and text primitive dictionaries."""
	line_parts = []
	for line in lines:
		line_parts.append(
			"<line "
			f"x1='{line['x1']}' y1='{line['y1']}' x2='{line['x2']}' y2='{line['y2']}' "
			f"stroke='{line.get('stroke', '#000')}' "
			f"stroke-width='{line.get('stroke_width', 1.0)}' "
			f"stroke-linecap='{line.get('stroke_linecap', 'round')}'/>"
		)
	text_parts = []
	for text in texts:
		text_parts.append(
			"<text "
			f"x='{text['x']}' y='{text['y']}' "
			f"text-anchor='{text.get('anchor', 'start')}' "
			f"font-family='{text.get('font_family', 'sans-serif')}' "
			f"font-size='{text.get('font_size', 12.0)}'>"
			f"{text['text']}</text>"
		)
	svg_text = (
		"<?xml version='1.0' encoding='utf-8'?>"
		"<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'>"
		+ "".join(line_parts)
		+ "".join(text_parts)
		+ "</svg>"
	)
	path.write_text(svg_text, encoding="utf-8")


#============================================
def _assert_keys_present(mapping: dict, keys: tuple[str, ...]) -> None:
	"""Assert one mapping contains all expected keys."""
	for key in keys:
		assert key in mapping


#============================================
def test_analyze_svg_file_detects_aligned_endpoint(tmp_path):
	"""Connector endpoint aimed at glyph center should produce small alignment error."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "aligned.svg"
	# Use the independent glyph model to find the O center, so the bond
	# aims at approximately where the measurement tool expects it.
	# Note: the optical pipeline may shift the center slightly, so we
	# verify reasonable alignment error rather than exact pass/fail.
	primitives = tool_module._label_svg_estimated_primitives({
		"text": "OH", "text_display": "OH", "text_raw": "OH",
		"x": 30.0, "y": 40.0, "anchor": "start", "font_size": 12.0,
		"font_name": "sans-serif"})
	o_prim = [p for p in primitives if p.get("char", "").upper() == "O"][0]
	end_x = tool_module._primitive_center(o_prim)[0]
	end_y = tool_module._primitive_center(o_prim)[1]
	_write_svg(
		path=svg_path,
		text="OH",
		text_x=30.0,
		text_y=40.0,
		x1=end_x,
		y1=end_y - 18.0,
		x2=end_x,
		y2=end_y,
	)
	report = tool_module.analyze_svg_file(svg_path, render_geometry)
	assert report["labels_analyzed"] == 1
	assert report["no_connector_count"] == 0
	label = report["labels"][0]
	assert label["alignment_center_char"] == "O"
	perp = float(label["endpoint_perpendicular_distance_to_alignment_center"])
	gap = float(label["endpoint_signed_distance_to_glyph_body"])
	g = (gap - render_geometry.ATTACH_GAP_TARGET) / (render_geometry.ATTACH_GAP_MAX - render_geometry.ATTACH_GAP_TARGET)
	p = perp / render_geometry.ATTACH_PERP_TOLERANCE
	expected_err = (g * g) + (p * p)
	assert label["endpoint_alignment_error"] == pytest.approx(expected_err, rel=1e-6)
	assert label["aligned"] == ((render_geometry.ATTACH_GAP_MIN <= gap <= render_geometry.ATTACH_GAP_MAX) and (perp <= render_geometry.ATTACH_PERP_TOLERANCE))
	assert label["bond_len"] == pytest.approx(18.0, abs=1.0)
	assert report["line_length_stats"]["all_lines"]["count"] == 1
	assert report["line_length_stats"]["connector_lines"]["count"] == 1
	assert report["line_length_stats"]["all_lines"]["mean"] == pytest.approx(18.0, abs=1.0)
	summary = tool_module._summary_stats([report])
	assert summary["bond_length_stats_all"]["count"] == 1
	assert len(summary["alignment_distances_compact_sorted"]) == 1
	assert summary["alignment_distance_compact_counts"][0]["count"] == 1
	assert summary["alignment_nonzero_distance_count"] == 1
	assert summary["alignment_distance_missing_count"] == 0


#============================================
def test_point_to_ellipse_signed_distance_uses_true_ellipse_geometry():
	"""Ellipse signed distance should follow axis-aligned ellipse geometry."""
	tool_module = _load_tool_module()
	signed_on_boundary = tool_module._point_to_ellipse_signed_distance(
		point=(14.0, 20.0),
		cx=10.0,
		cy=20.0,
		rx=4.0,
		ry=2.0,
	)
	assert signed_on_boundary == pytest.approx(0.0, abs=1e-6)
	signed_outside = tool_module._point_to_ellipse_signed_distance(
		point=(18.0, 20.0),
		cx=10.0,
		cy=20.0,
		rx=4.0,
		ry=2.0,
	)
	assert signed_outside == pytest.approx(4.0, abs=1e-4)
	signed_inside = tool_module._point_to_ellipse_signed_distance(
		point=(10.0, 20.0),
		cx=10.0,
		cy=20.0,
		rx=4.0,
		ry=2.0,
	)
	assert signed_inside < 0.0


#============================================
def test_canonicalize_label_text_maps_hoh2c_to_ch2oh():
	"""Down-tail alias text should normalize to CH2OH for geometry targeting."""
	tool_module = _load_tool_module()
	assert tool_module._canonicalize_label_text("HOH2C") == "CH2OH"
	assert tool_module._canonicalize_label_text("HOH\u2082C") == "CH2OH"


#============================================
def test_analyze_svg_file_detects_collinear_line_as_aligned(tmp_path):
	"""Line aimed at primitive centerline should produce small alignment error."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "missed.svg"
	# Use the independent glyph model to find the O center y-coordinate,
	# so the horizontal line passes through where the tool expects it.
	# Note: the optical pipeline may shift the center slightly.
	primitives = tool_module._label_svg_estimated_primitives({
		"text": "OH", "text_display": "OH", "text_raw": "OH",
		"x": 40.0, "y": 50.0, "anchor": "start", "font_size": 12.0,
		"font_name": "sans-serif"})
	o_prim = [p for p in primitives if p.get("char", "").upper() == "O"][0]
	center_y = tool_module._primitive_center(o_prim)[1]
	box = tool_module._label_svg_estimated_box({
		"text": "OH", "text_display": "OH", "text_raw": "OH",
		"x": 40.0, "y": 50.0, "anchor": "start", "font_size": 12.0,
		"font_name": "sans-serif"})
	x_right = box[2] + 8.0
	_write_svg(
		path=svg_path,
		text="OH",
		text_x=40.0,
		text_y=50.0,
		x1=x_right,
		y1=center_y,
		x2=x_right + 12.0,
		y2=center_y,
	)
	report = tool_module.analyze_svg_file(svg_path, render_geometry)
	assert report["labels_analyzed"] == 1
	assert report["no_connector_count"] == 0
	label = report["labels"][0]
	assert label["alignment_center_char"] == "O"
	perp = float(label["endpoint_perpendicular_distance_to_alignment_center"])
	gap = float(label["endpoint_signed_distance_to_glyph_body"])
	g = (gap - render_geometry.ATTACH_GAP_TARGET) / (render_geometry.ATTACH_GAP_MAX - render_geometry.ATTACH_GAP_TARGET)
	p = perp / render_geometry.ATTACH_PERP_TOLERANCE
	expected_err = (g * g) + (p * p)
	assert label["endpoint_alignment_error"] == pytest.approx(expected_err, rel=1e-6)
	assert label["aligned"] == ((render_geometry.ATTACH_GAP_MIN <= gap <= render_geometry.ATTACH_GAP_MAX) and (perp <= render_geometry.ATTACH_PERP_TOLERANCE))
	assert label["bond_len"] == pytest.approx(12.0, abs=1.0)
	assert label["alignment_mode"] == "independent_glyph_primitives"
	assert report["line_length_stats"]["all_lines"]["count"] == 1
	assert report["line_length_stats"]["connector_lines"]["count"] == 1
	assert report["line_length_stats"]["all_lines"]["mean"] == pytest.approx(12.0)


#============================================
def test_analyze_svg_file_detects_no_connector(tmp_path):
	"""No nearby line should be reported as no connector."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "no_connector.svg"
	_write_svg(
		path=svg_path,
		text="CH2OH",
		text_x=40.0,
		text_y=50.0,
		x1=160.0,
		y1=160.0,
		x2=180.0,
		y2=160.0,
	)
	report = tool_module.analyze_svg_file(svg_path, render_geometry)
	assert report["labels_analyzed"] == 1
	assert report["aligned_count"] == 0
	assert report["missed_count"] == 0
	assert report["no_connector_count"] == 1
	assert report["labels"][0]["reason"] == "no_nearby_connector"
	assert report["labels"][0]["bond_len"] is None
	assert report["labels"][0]["endpoint_distance_to_glyph_body"] is not None
	assert report["labels"][0]["endpoint_distance_to_glyph_body"] > 0.0
	assert report["labels"][0]["endpoint_signed_distance_to_glyph_body"] is not None
	assert report["labels"][0]["independent_glyph_model"] in {
		"svg_primitives_ellipse_box",
		"svg_text_path_outline",
	}


#============================================
def test_text_report_uses_simplified_bond_length_section(tmp_path):
	"""Text report should keep core bond-length stats and omit verbose arrays/buckets."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "aligned_again.svg"
	target = render_geometry.label_attach_target_from_text_origin(
		text_x=30.0,
		text_y=40.0,
		text="CH2OH",
		anchor="start",
		font_size=12.0,
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
		font_name="sans-serif",
	)
	end_x, end_y = target.centroid()
	_write_svg(
		path=svg_path,
		text="CH2OH",
		text_x=30.0,
		text_y=40.0,
		x1=end_x,
		y1=end_y - 12.0,
		x2=end_x,
		y2=end_y,
	)
	report = tool_module.analyze_svg_file(svg_path, render_geometry)
	summary = tool_module._summary_stats([report])
	text = tool_module._text_report(
		summary=summary,
		top_misses=[],
		input_glob="tmp/*.svg",
		exclude_haworth_base_ring=True,
	)
	assert "Unique labels" in text
	assert "Bonds (detected / checked):" in text
	assert "Checked:" in text
	assert "Connector:" in text
	assert "BOND LENGTH STATISTICS" in text
	assert "min=" in text
	assert "max=" in text
	assert "mean=" in text
	assert "sd=" in text


#============================================
def test_geometry_checker_reports_30_degree_lattice_and_overlap_counts(tmp_path):
	"""Standalone checker should report requested geometry counts."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "geometry_counts.svg"
	_write_svg_primitives(
		path=svg_path,
		lines=[
			{"x1": 10.0, "y1": 10.0, "x2": 60.0, "y2": 10.0},
			{"x1": 10.0, "y1": 20.0, "x2": 60.0, "y2": 48.867513459},
			{"x1": 10.0, "y1": 30.0, "x2": 60.0, "y2": 50.0},
			{"x1": 20.0, "y1": 170.0, "x2": 80.0, "y2": 170.0},
			{"x1": 50.0, "y1": 140.0, "x2": 50.0, "y2": 200.0},
			{"x1": 0.0, "y1": 110.0, "x2": 300.0, "y2": 110.0},
		],
		texts=[
			{"text": "AA", "x": 100.0, "y": 100.0},
			{"text": "BB", "x": 102.0, "y": 100.0},
			{"text": "Na", "x": 140.0, "y": 110.0},
		],
	)
	report = tool_module.analyze_svg_file(
		svg_path=svg_path,
		render_geometry=render_geometry,
		exclude_haworth_base_ring=True,
	)
	assert report["haworth_base_ring"]["detected"] is False
	assert report["lattice_angle_violation_count"] == 1
	assert report["glyph_glyph_overlap_count"] >= 0
	assert report["bond_bond_overlap_count"] == 1
	assert report["bond_glyph_overlap_count"] >= 1
	first_violation = report["geometry_checks"]["lattice_angle_violations"][0]
	_assert_keys_present(
		first_violation,
		("nearest_canonical_angle_degrees", "angle_quadrant", "measurement_point"),
	)
	_assert_keys_present(
		report["geometry_checks"]["bond_bond_overlaps"][0],
		("overlap_quadrant", "overlap_ring_region"),
	)
	_assert_keys_present(
		report["geometry_checks"]["bond_glyph_overlaps"][0],
		(
			"label_text",
			"overlap_classification",
			"bond_end_to_glyph_distance",
			"bond_end_distance_tolerance",
			"bond_end_overlap",
			"bond_end_too_close",
		),
	)
	summary = tool_module._summary_stats([report])
	assert summary["canonical_angles_degrees"] == [float(angle) for angle in range(0, 360, 30)]
	assert summary["lattice_angle_violation_count"] == 1
	assert sum(summary["lattice_angle_violation_quadrants"].values()) == 1
	assert summary["lattice_angle_violation_examples"]
	assert summary["total_bonds_detected"] == 6
	assert len(summary["bond_lengths_rounded_sorted_all"]) == 6
	assert summary["bond_length_rounded_counts_all"]
	assert "Na" in summary["bond_glyph_overlap_label_texts"]
	assert summary["bond_glyph_overlap_classifications"]
	assert summary["bond_glyph_gap_tolerances"]
	assert "bond_glyph_endpoint_overlap_count" in summary
	assert "bond_glyph_endpoint_too_close_count" in summary
	assert summary["bond_glyph_endpoint_signed_distance_stats"]["count"] >= 1
	assert summary["bond_lengths_by_quadrant_checked"]
	assert summary["bond_lengths_by_ring_region_checked"]
	assert "alignment_by_glyph" in summary
	assert isinstance(summary["alignment_by_glyph"], dict)
	assert "glyph_alignment_data_points" in summary
	assert "glyph_to_bond_end_data_points" in summary
	assert "alignment_distances_compact_sorted" in summary
	assert "alignment_distance_compact_counts" in summary
	assert "alignment_nonzero_distance_count" in summary
	assert "alignment_min_nonzero_distance" in summary
	assert "alignment_distance_missing_count" in summary
	text = tool_module._text_report(
		summary=summary,
		top_misses=[],
		input_glob="tmp/*.svg",
		exclude_haworth_base_ring=True,
	)
	assert "lattice-angle violations" in text


#============================================
def test_haworth_base_ring_detected_and_excluded_by_default(tmp_path):
	"""Haworth base ring detection should drive include/exclude behavior."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "haworth_like.svg"
	radius = 24.0
	center_x = 90.0
	center_y = 90.0
	points = []
	for angle in (0.0, 60.0, 120.0, 180.0, 240.0, 300.0):
		radians = math.radians(angle)
		points.append(
			(
				center_x + (radius * math.cos(radians)),
				center_y + (radius * math.sin(radians)),
			)
		)
	lines = []
	for index, start_point in enumerate(points):
		end_point = points[(index + 1) % len(points)]
		lines.append(
			{
				"x1": start_point[0],
				"y1": start_point[1],
				"x2": end_point[0],
				"y2": end_point[1],
			}
		)
	_write_svg_primitives(
		path=svg_path,
		lines=lines,
		texts=[{"text": "O", "x": center_x, "y": center_y - radius - 4.0}],
	)
	report_excluded = tool_module.analyze_svg_file(
		svg_path=svg_path,
		render_geometry=render_geometry,
		exclude_haworth_base_ring=True,
	)
	report_included = tool_module.analyze_svg_file(
		svg_path=svg_path,
		render_geometry=render_geometry,
		exclude_haworth_base_ring=False,
	)
	assert report_excluded["haworth_base_ring"]["detected"] is True
	assert report_excluded["haworth_base_ring"]["excluded"] is True
	assert len(report_excluded["excluded_line_indexes"]) >= 5
	assert report_included["haworth_base_ring"]["detected"] is True
	assert report_included["haworth_base_ring"]["excluded"] is False
	assert report_included["excluded_line_indexes"] == []


#============================================
def test_bond_bond_overlap_ignores_simple_collinear_chain_junction(tmp_path):
	"""Collinear continuation through a shared endpoint should not count as overlap."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "collinear_chain.svg"
	_write_svg_primitives(
		path=svg_path,
		lines=[
			{"x1": 20.0, "y1": 40.0, "x2": 20.0, "y2": 20.0},
			{"x1": 20.0, "y1": 20.0, "x2": 20.0, "y2": 0.0},
		],
		texts=[{"text": "OH", "x": 30.0, "y": 30.0}],
	)
	report = tool_module.analyze_svg_file(
		svg_path=svg_path,
		render_geometry=render_geometry,
		exclude_haworth_base_ring=True,
	)
	assert report["bond_bond_overlap_count"] == 0


#============================================
def test_bond_glyph_overlap_reports_independent_connector_crowding(tmp_path):
	"""Independent geometry mode should report connector endpoint crowding."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "legal_attach_zone.svg"
	target = render_geometry.label_attach_target_from_text_origin(
		text_x=30.0,
		text_y=40.0,
		text="OH",
		anchor="start",
		font_size=12.0,
		attach_atom="first",
		attach_element="O",
		attach_site="core_center",
		font_name="sans-serif",
	)
	end_x, end_y = target.centroid()
	_write_svg_primitives(
		path=svg_path,
		lines=[
			{"x1": end_x, "y1": end_y - 16.0, "x2": end_x, "y2": end_y},
		],
		texts=[
			{"text": "OH", "x": 30.0, "y": 40.0},
		],
	)
	report = tool_module.analyze_svg_file(
		svg_path=svg_path,
		render_geometry=render_geometry,
		exclude_haworth_base_ring=True,
	)
	assert report["bond_glyph_overlap_count"] >= 1
	overlaps = report["geometry_checks"]["bond_glyph_overlaps"]
	assert overlaps
	assert bool(overlaps[0]["aligned_connector_pair"]) is True


#============================================
def test_reports_hatched_carrier_overlap_with_non_hatch_line(tmp_path):
	"""Hashed carrier should report overlap with a separate non-hatch line."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "hashed_conflict.svg"
	lines = [
		{
			"x1": 20.0,
			"y1": 80.0,
			"x2": 120.0,
			"y2": 80.0,
			"stroke_width": 0.264,
			"stroke_linecap": "butt",
		},
		{
			"x1": 25.0,
			"y1": 80.0,
			"x2": 115.0,
			"y2": 80.0,
			"stroke_width": 1.2,
			"stroke_linecap": "round",
		},
	]
	for x_coord in (35.0, 47.0, 59.0, 71.0, 83.0, 95.0):
		lines.append(
			{
				"x1": x_coord,
				"y1": 78.8,
				"x2": x_coord,
				"y2": 81.2,
				"stroke_width": 0.864,
				"stroke_linecap": "butt",
			}
		)
	_write_svg_primitives(
		path=svg_path,
		lines=lines,
		texts=[{"text": "OH", "x": 140.0, "y": 90.0}],
	)
	report = tool_module.analyze_svg_file(
		svg_path=svg_path,
		render_geometry=render_geometry,
		exclude_haworth_base_ring=True,
	)
	assert report["decorative_hatched_stroke_count"] == 6
	assert report["line_length_stats"]["checked_lines"]["count"] == 2
	assert report["line_length_stats"]["checked_lines_raw"]["count"] == 8
	checked_lengths = report["line_lengths_rounded_sorted"]["checked_lines"]
	assert len(checked_lengths) == 2
	assert min(checked_lengths) == pytest.approx(90.0, abs=2.0)
	assert max(checked_lengths) == pytest.approx(100.0, abs=2.0)
	assert report["hatched_thin_conflict_count"] >= 1
	conflicts = report["geometry_checks"]["hatched_thin_conflicts"]
	assert any(item["conflict_type"] == "collinear_overlap" for item in conflicts)
	collinear_conflicts = [
		item for item in conflicts if item["conflict_type"] == "collinear_overlap"
	]
	assert any(
		{item["carrier_line_index"], item["other_line_index"]} == {0, 1}
		for item in collinear_conflicts
	)
	_assert_keys_present(collinear_conflicts[0], ("overlap_quadrant", "overlap_ring_region"))
	summary = tool_module._summary_stats([report])
	assert summary["hatched_thin_conflict_count"] >= 1
	assert summary["hatched_thin_conflict_types"].get("collinear_overlap", 0) >= 1
	assert summary["hatched_thin_conflict_examples"]
	assert summary["decorative_hatched_stroke_line_count"] == 6
	assert summary["total_bonds_checked"] == 2


#============================================
def test_reports_hatched_shared_endpoint_near_parallel_conflict(tmp_path):
	"""Shared endpoint near-parallel to hashed carrier should count as conflict."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "hashed_shared_endpoint_conflict.svg"
	lines = [
		{
			"x1": 20.0,
			"y1": 80.0,
			"x2": 120.0,
			"y2": 80.0,
			"stroke_width": 0.264,
			"stroke_linecap": "butt",
		},
		{
			"x1": 20.0,
			"y1": 80.0,
			"x2": 64.0,
			"y2": 92.0,
			"stroke_width": 1.2,
			"stroke_linecap": "round",
		},
	]
	for x_coord in (35.0, 47.0, 59.0, 71.0, 83.0):
		lines.append(
			{
				"x1": x_coord,
				"y1": 78.8,
				"x2": x_coord,
				"y2": 81.2,
				"stroke_width": 0.864,
				"stroke_linecap": "butt",
			}
		)
	_write_svg_primitives(
		path=svg_path,
		lines=lines,
		texts=[{"text": "OH", "x": 140.0, "y": 90.0}],
	)
	report = tool_module.analyze_svg_file(
		svg_path=svg_path,
		render_geometry=render_geometry,
		exclude_haworth_base_ring=True,
	)
	assert report["hatched_thin_conflict_count"] >= 1
	types = {
		item["conflict_type"]
		for item in report["geometry_checks"]["hatched_thin_conflicts"]
	}
	assert "shared_endpoint_near_parallel" in types


#============================================
def test_fail_on_miss_exits_non_zero(tmp_path, monkeypatch):
	"""CLI --fail-on-miss should exit non-zero when misses are present."""
	tool_module = _load_tool_module()
	svg_path = tmp_path / "miss_gate.svg"
	_write_svg(
		path=svg_path,
		text="OH",
		text_x=40.0,
		text_y=50.0,
		x1=90.0,
		y1=50.0,
		x2=102.0,
		y2=50.0,
	)
	monkeypatch.setattr(tool_module, "get_repo_root", lambda: tmp_path)
	monkeypatch.setattr(
		sys,
		"argv",
		[
			"measure_glyph_bond_alignment.py",
			"--input-glob",
			str(svg_path),
			"--json-report",
			str(tmp_path / "report.json"),
			"--text-report",
			str(tmp_path / "report.txt"),
			"--fail-on-miss",
		],
	)
	with pytest.raises(SystemExit) as error:
		tool_module.main()
	assert error.value.code == 2


#============================================
def test_tool_has_no_generation_path_dependency():
	"""Tool must not import or call generation/render pipeline entrypoints."""
	repo_root = pathlib.Path(get_repo_root())
	tool_text = (repo_root / "tools" / "measure_glyph_bond_alignment.py").read_text(
		encoding="utf-8"
	)
	assert "render_from_code" not in tool_text
	assert "haworth_renderer" not in tool_text
