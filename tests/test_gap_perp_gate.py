"""Tests for the gap/perp gate tool."""

# Standard Library
import importlib.util
import json
import pathlib

# Local repo modules
import conftest
from get_repo_root import get_repo_root

conftest.add_oasa_to_sys_path()

# local repo modules
import oasa.render_geometry as render_geometry


#============================================
def _load_gate_module():
	"""Load the gap/perp gate module from the tools directory."""
	repo_root = pathlib.Path(get_repo_root())
	tool_path = repo_root / "tools" / "gap_perp_gate.py"
	spec = importlib.util.spec_from_file_location("gap_perp_gate", tool_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Could not load gate module from {tool_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


#============================================
def _write_svg(path: pathlib.Path, lines: list[dict], texts: list[dict]) -> None:
	"""Write one SVG document from explicit line and text primitive dicts."""
	line_parts = []
	for line in lines:
		line_parts.append(
			"<line "
			f"x1='{line['x1']}' y1='{line['y1']}' "
			f"x2='{line['x2']}' y2='{line['y2']}' "
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
def test_gate_module_loads():
	"""Gate module should load and expose expected public names."""
	gate = _load_gate_module()
	assert hasattr(gate, "FIXTURE_BUCKETS")
	assert hasattr(gate, "HAWORTH_GATE_TARGETS")
	assert hasattr(gate, "build_gate_report")
	assert hasattr(gate, "run_bucket")
	assert hasattr(gate, "parse_args")
	assert hasattr(gate, "main")
	# fixture buckets should include expected corpora
	assert "haworth" in gate.FIXTURE_BUCKETS
	assert "haworth_full" in gate.FIXTURE_BUCKETS
	assert "oasa_generic" in gate.FIXTURE_BUCKETS
	assert "bkchem" in gate.FIXTURE_BUCKETS
	# haworth targets should have 11 entries
	assert len(gate.HAWORTH_GATE_TARGETS) == 11


#============================================
def test_build_gate_report_structure(tmp_path):
	"""build_gate_report should return compact JSON with expected keys."""
	gate = _load_gate_module()
	# load measurement tool for analyze_svg_file
	repo_root = pathlib.Path(get_repo_root())
	measure_path = repo_root / "tools" / "measure_glyph_bond_alignment.py"
	measure_spec = importlib.util.spec_from_file_location(
		"measure_glyph_bond_alignment", measure_path,
	)
	measure = importlib.util.module_from_spec(measure_spec)
	measure_spec.loader.exec_module(measure)
	# create synthetic SVG with one label and one bond
	svg_path = tmp_path / "test.svg"
	_write_svg(
		path=svg_path,
		lines=[
			{"x1": 30.0, "y1": 10.0, "x2": 30.0, "y2": 30.0},
		],
		texts=[
			{"text": "OH", "x": 24.0, "y": 45.0},
		],
	)
	# analyze the SVG directly
	file_report = measure.analyze_svg_file(svg_path, render_geometry)
	# build gate report
	report = gate.build_gate_report([file_report], "test_bucket", "tmp/*.svg")
	# check required keys
	required_keys = {
		"bucket", "source", "files_analyzed", "labels_analyzed",
		"aligned_count", "missed_count", "no_connector_count",
		"alignment_rate", "per_label", "reason_counts",
	}
	assert set(report.keys()) == required_keys
	assert report["bucket"] == "test_bucket"
	assert report["files_analyzed"] == 1
	assert report["labels_analyzed"] >= 1
	# per_label should have OH entry
	assert "OH" in report["per_label"]
	oh_stats = report["per_label"]["OH"]
	assert "count" in oh_stats
	assert "aligned_count" in oh_stats
	assert "gap" in oh_stats
	assert "perp" in oh_stats
	# reason_counts should be a dict
	assert isinstance(report["reason_counts"], dict)


#============================================
def test_build_gate_report_reason_counts(tmp_path):
	"""Reason counts should tally all non-aligned label reasons."""
	gate = _load_gate_module()
	repo_root = pathlib.Path(get_repo_root())
	measure_path = repo_root / "tools" / "measure_glyph_bond_alignment.py"
	measure_spec = importlib.util.spec_from_file_location(
		"measure_glyph_bond_alignment", measure_path,
	)
	measure = importlib.util.module_from_spec(measure_spec)
	measure_spec.loader.exec_module(measure)
	# create two SVGs -- one with bond near label, one with bond far away
	near_path = tmp_path / "near.svg"
	far_path = tmp_path / "far.svg"
	_write_svg(
		path=near_path,
		lines=[{"x1": 30.0, "y1": 10.0, "x2": 30.0, "y2": 30.0}],
		texts=[{"text": "OH", "x": 24.0, "y": 45.0}],
	)
	_write_svg(
		path=far_path,
		lines=[{"x1": 200.0, "y1": 200.0, "x2": 220.0, "y2": 200.0}],
		texts=[{"text": "CH2OH", "x": 30.0, "y": 45.0}],
	)
	reports = [
		measure.analyze_svg_file(near_path, render_geometry),
		measure.analyze_svg_file(far_path, render_geometry),
	]
	report = gate.build_gate_report(reports, "test", "tmp/*.svg")
	# total reason count should equal missed + no_connector
	total_reasons = sum(report["reason_counts"].values())
	expected_total = report["missed_count"] + report["no_connector_count"]
	assert total_reasons == expected_total


#============================================
def test_run_bucket_empty_glob(tmp_path, monkeypatch):
	"""run_bucket with no matching files should return a skipped report."""
	gate = _load_gate_module()
	# monkeypatch FIXTURE_BUCKETS to point to an empty directory
	monkeypatch.setattr(
		gate, "FIXTURE_BUCKETS",
		{"empty_test": {
			"type": "glob",
			"glob": str(tmp_path / "nonexistent" / "*.svg"),
		}},
	)
	repo_root = pathlib.Path(get_repo_root())
	report = gate.run_bucket(repo_root, "empty_test")
	assert report["files_analyzed"] == 0
	assert report["labels_analyzed"] == 0
	assert report.get("skipped") is True


#============================================
def test_gate_haworth_targets_exist():
	"""All 11 haworth gate target SVGs should exist on disk."""
	repo_root = pathlib.Path(get_repo_root())
	gate = _load_gate_module()
	config = gate.FIXTURE_BUCKETS["haworth"]
	svg_dir = repo_root / config["dir"]
	missing = []
	for stem in gate.HAWORTH_GATE_TARGETS:
		path = svg_dir / f"{stem}.svg"
		if not path.exists():
			missing.append(stem)
	assert not missing, f"Missing target SVGs: {missing}"


#============================================
def test_gate_main_writes_json(tmp_path, monkeypatch):
	"""main() should write a valid JSON file."""
	gate = _load_gate_module()
	output_path = tmp_path / "gate_output.json"
	# create a small fixture bucket for testing
	svg_dir = tmp_path / "svgs"
	svg_dir.mkdir()
	_write_svg(
		path=svg_dir / "test1.svg",
		lines=[{"x1": 30.0, "y1": 10.0, "x2": 30.0, "y2": 30.0}],
		texts=[{"text": "OH", "x": 24.0, "y": 45.0}],
	)
	# override bucket config and repo root for isolation
	monkeypatch.setattr(
		gate, "FIXTURE_BUCKETS",
		{"test": {
			"type": "glob",
			"glob": str(svg_dir / "*.svg"),
		}},
	)
	monkeypatch.setattr(gate, "get_repo_root", lambda: tmp_path)
	import sys
	monkeypatch.setattr(
		sys, "argv",
		["gap_perp_gate.py", "--bucket", "test", "--output", str(output_path)],
	)
	gate.main()
	assert output_path.exists()
	data = json.loads(output_path.read_text(encoding="utf-8"))
	assert "generated_at" in data
	assert "buckets" in data
	assert "test" in data["buckets"]
	bucket = data["buckets"]["test"]
	assert bucket["files_analyzed"] == 1
	assert bucket["labels_analyzed"] >= 1
