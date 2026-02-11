"""Tests for archive_matrix_summary strict mode enforcement behavior."""

# Standard Library
import argparse

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
import tools.archive_matrix_summary as archive_matrix_summary


#============================================
def _strict_failure_runtime_error() -> RuntimeError:
	"""Build one strict-overlap RuntimeError payload."""
	return RuntimeError(
		"Strict overlap failure in ARLRDM_furanose_alpha: "
		"bond/label line=C4_up_connector label=C4_up_label"
	)


#============================================
def test_parse_args_strict_mode_requires_regenerate(monkeypatch):
	"""Strict mode flags must require --regenerate-haworth-svgs."""
	monkeypatch.setattr(
		"sys.argv",
		[
			"archive_matrix_summary.py",
			"--strict-report-all",
		],
	)
	with pytest.raises(SystemExit):
		archive_matrix_summary.parse_args()


#============================================
def test_report_all_exits_nonzero_after_summary_generation(tmp_path, monkeypatch):
	"""Report-all mode continues, writes summary, then exits non-zero on failures."""
	repo_root = tmp_path / "repo"
	output_dir = repo_root / "output_smoke"
	archive_dir = repo_root / "neurotiker_haworth_archive"
	archive_dir.mkdir(parents=True)
	(archive_dir / "Alpha-D-Glucofuranose.svg").write_text("<svg/>", encoding="utf-8")
	args = argparse.Namespace(
		regenerate_haworth_svgs=True,
		strict_render_checks=False,
		strict_mode="report_all",
	)
	mapping_rows = [
		{
			"code": "ARLRDM",
			"ring_type": "furanose",
			"anomeric": "alpha",
			"sugar_name": "D-Glucose",
			"reference_svg_rel": "Alpha-D-Glucofuranose.svg",
		}
	]
	monkeypatch.setattr(archive_matrix_summary, "parse_args", lambda: args)
	monkeypatch.setattr(archive_matrix_summary, "get_repo_root", lambda: repo_root)
	monkeypatch.setattr(archive_matrix_summary, "load_archive_mapping", lambda _root: mapping_rows)
	monkeypatch.setattr(
		archive_matrix_summary,
		"_render_generated_preview_svg",
		lambda **_kwargs: (_ for _ in ()).throw(_strict_failure_runtime_error()),
	)
	monkeypatch.setattr(archive_matrix_summary, "build_summary_html", lambda **_kwargs: "<html/>")
	monkeypatch.setattr(archive_matrix_summary, "build_generated_only_html", lambda **_kwargs: "<html/>")
	with pytest.raises(SystemExit) as exit_info:
		archive_matrix_summary.main()
	assert int(exit_info.value.code) == 2
	assert (output_dir / "archive_matrix_summary.html").is_file()
	assert (output_dir / "l-sugar_matrix.html").is_file()


#============================================
def test_fail_fast_exits_immediately_on_first_failure(tmp_path, monkeypatch):
	"""Fail-fast mode exits non-zero at first strict failure before summary write."""
	repo_root = tmp_path / "repo"
	archive_dir = repo_root / "neurotiker_haworth_archive"
	archive_dir.mkdir(parents=True)
	(archive_dir / "Alpha-D-Glucofuranose.svg").write_text("<svg/>", encoding="utf-8")
	args = argparse.Namespace(
		regenerate_haworth_svgs=True,
		strict_render_checks=False,
		strict_mode="fail_fast",
	)
	mapping_rows = [
		{
			"code": "ARLRDM",
			"ring_type": "furanose",
			"anomeric": "alpha",
			"sugar_name": "D-Glucose",
			"reference_svg_rel": "Alpha-D-Glucofuranose.svg",
		}
	]
	monkeypatch.setattr(archive_matrix_summary, "parse_args", lambda: args)
	monkeypatch.setattr(archive_matrix_summary, "get_repo_root", lambda: repo_root)
	monkeypatch.setattr(archive_matrix_summary, "load_archive_mapping", lambda _root: mapping_rows)
	monkeypatch.setattr(
		archive_matrix_summary,
		"_render_generated_preview_svg",
		lambda **_kwargs: (_ for _ in ()).throw(_strict_failure_runtime_error()),
	)
	with pytest.raises(SystemExit) as exit_info:
		archive_matrix_summary.main()
	assert int(exit_info.value.code) == 2
	assert not (repo_root / "output_smoke" / "archive_matrix_summary.html").exists()
