"""Scaffold checks for glyph-alignment fixture corpus and runner command."""

# Standard Library
import json
import pathlib


#============================================
def test_glyph_alignment_fixture_scaffold_files_exist():
	"""Expected scaffold fixture SVG+JSON pairs should exist."""
	repo_root = pathlib.Path(__file__).resolve().parents[1]
	fixture_dir = repo_root / "tests" / "fixtures" / "glyph_alignment"
	expected_stems = (
		"unit_01_isolated_glyph_fit",
		"unit_02_mixed_subscript_no_bonds",
		"unit_03_bonds_nearby_strokes",
		"torture_4x4_grid",
	)
	for stem in expected_stems:
		svg_path = fixture_dir / f"{stem}.svg"
		json_path = fixture_dir / f"{stem}.json"
		assert svg_path.is_file(), f"Missing fixture SVG: {svg_path}"
		assert json_path.is_file(), f"Missing fixture sidecar JSON: {json_path}"


#============================================
def test_glyph_alignment_fixture_sidecars_have_expectations_block():
	"""All sidecars should include an expectations dictionary scaffold."""
	repo_root = pathlib.Path(__file__).resolve().parents[1]
	fixture_dir = repo_root / "tests" / "fixtures" / "glyph_alignment"
	for json_path in sorted(fixture_dir.glob("*.json")):
		payload = json.loads(json_path.read_text(encoding="utf-8"))
		assert isinstance(payload, dict), f"Sidecar must be object: {json_path}"
		expectations = payload.get("expectations")
		assert isinstance(expectations, dict), f"Missing expectations dict: {json_path}"


#============================================
def test_glyph_alignment_fixture_runner_script_exists():
	"""Runner script for scaffold fixtures should exist."""
	repo_root = pathlib.Path(__file__).resolve().parents[1]
	runner_path = repo_root / "tools" / "run_glyph_alignment_fixture_runner.py"
	assert runner_path.is_file(), f"Missing runner: {runner_path}"

