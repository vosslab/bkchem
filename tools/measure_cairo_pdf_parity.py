#!/usr/bin/env python3
"""Measure Cairo PDF rendering parity against SVG baseline output."""

# Standard Library
import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys

# Ensure the tools/ directory is on sys.path so that the measurelib
# subpackage can be imported when this file is loaded via
# importlib.util.spec_from_file_location().
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
	sys.path.insert(0, _TOOLS_DIR)

import defusedxml.ElementTree as ET

from measurelib.pdf_parse import (
	collect_pdf_labels,
	collect_pdf_lines,
	collect_pdf_ring_primitives,
	collect_pdf_wedge_bonds,
	open_pdf_page,
	resolve_pdf_paths,
)
from measurelib.svg_parse import (
	collect_svg_labels,
	collect_svg_lines,
	collect_svg_ring_primitives,
	collect_svg_wedge_bonds,
	resolve_svg_paths,
)
from measurelib.parity import (
	match_labels,
	match_lines,
	match_ring_primitives,
	match_wedge_bonds,
	parity_summary,
)
from measurelib.pdf_analysis import analyze_pdf_file

DEFAULT_POSITION_TOLERANCE = 2.0
DEFAULT_PDF_GLOB = "output_smoke/*.pdf"
DEFAULT_JSON_REPORT = "output_smoke/cairo_parity_report.json"
DEFAULT_TEXT_REPORT = "output_smoke/cairo_parity_report.txt"


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments for Cairo PDF parity analysis."""
	parser = argparse.ArgumentParser(
		description="Measure Cairo PDF rendering parity against SVG baseline.",
	)
	parser.add_argument(
		"-s", "--svg-glob",
		dest="svg_glob",
		type=str,
		default=None,
		help="SVG file glob pattern (optional; enables parity mode).",
	)
	parser.add_argument(
		"-p", "--pdf-glob",
		dest="pdf_glob",
		type=str,
		default=DEFAULT_PDF_GLOB,
		help="PDF file glob pattern (required).",
	)
	parser.add_argument(
		"-j", "--json-report",
		dest="json_report",
		type=str,
		default=DEFAULT_JSON_REPORT,
		help="Output path for JSON report.",
	)
	parser.add_argument(
		"-t", "--text-report",
		dest="text_report",
		type=str,
		default=DEFAULT_TEXT_REPORT,
		help="Output path for text summary report.",
	)
	parser.add_argument(
		"-f", "--fail-on-mismatch",
		dest="fail_on_mismatch",
		action="store_true",
		help="Exit non-zero when parity violations detected.",
	)
	parser.add_argument(
		"-a", "--accept-mismatch",
		dest="fail_on_mismatch",
		action="store_false",
		help="Always exit zero, even when mismatches are detected.",
	)
	parser.add_argument(
		"--position-tolerance",
		dest="position_tolerance",
		type=float,
		default=DEFAULT_POSITION_TOLERANCE,
		help="Max coordinate delta for matched primitives.",
	)
	parser.add_argument(
		"--exclude-haworth-base-ring",
		dest="exclude_haworth_base_ring",
		action="store_true",
		help="Exclude Haworth ring geometry from PDF analysis.",
	)
	parser.add_argument(
		"--include-haworth-base-ring",
		dest="exclude_haworth_base_ring",
		action="store_false",
		help="Include Haworth ring geometry in PDF analysis.",
	)
	parser.set_defaults(fail_on_mismatch=False)
	parser.set_defaults(exclude_haworth_base_ring=True)
	return parser.parse_args()


#============================================
def get_repo_root() -> pathlib.Path:
	"""Return repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		raise RuntimeError("Could not detect repo root via git rev-parse --show-toplevel")
	return pathlib.Path(result.stdout.strip())


#============================================
def pair_files_by_stem(
		svg_paths: list[pathlib.Path],
		pdf_paths: list[pathlib.Path]) -> list[tuple[pathlib.Path, pathlib.Path]]:
	"""Match SVG and PDF files by stem name.

	Args:
		svg_paths: list of SVG file paths.
		pdf_paths: list of PDF file paths.

	Returns:
		list of (svg_path, pdf_path) tuples matched by stem.
	"""
	svg_by_stem = {path.stem: path for path in svg_paths}
	pairs = []
	for pdf_path in pdf_paths:
		svg_path = svg_by_stem.get(pdf_path.stem)
		if svg_path is not None:
			pairs.append((svg_path, pdf_path))
	return pairs


#============================================
def analyze_parity_pair(
		svg_path: pathlib.Path,
		pdf_path: pathlib.Path,
		position_tolerance: float) -> dict:
	"""Run parity comparison on one SVG/PDF file pair.

	Args:
		svg_path: path to SVG file.
		pdf_path: path to PDF file.
		position_tolerance: max delta for matching.

	Returns:
		dict with parity metrics for the file pair.
	"""
	# extract SVG primitives
	svg_root = ET.parse(str(svg_path)).getroot()
	svg_lines = collect_svg_lines(svg_root)
	svg_labels = collect_svg_labels(svg_root)
	svg_rings = collect_svg_ring_primitives(svg_root)
	svg_wedges = collect_svg_wedge_bonds(svg_root)
	# extract PDF primitives
	page, pdf_obj = open_pdf_page(str(pdf_path))
	pdf_lines = collect_pdf_lines(page)
	pdf_labels = collect_pdf_labels(page)
	pdf_rings = collect_pdf_ring_primitives(page)
	pdf_wedges = collect_pdf_wedge_bonds(page)
	pdf_obj.close()
	# match primitives
	line_matches = match_lines(svg_lines, pdf_lines, tolerance=position_tolerance)
	label_matches = match_labels(svg_labels, pdf_labels, tolerance=position_tolerance * 2.5)
	ring_matches = match_ring_primitives(svg_rings, pdf_rings, tolerance=position_tolerance * 2.5)
	wedge_matches = match_wedge_bonds(svg_wedges, pdf_wedges, tolerance=position_tolerance * 2.5)
	# compute summary
	summary = parity_summary(line_matches, label_matches, ring_matches, wedge_matches)
	# count matched per category for the compact report
	lines_matched = sum(1 for m in line_matches if m["matched"])
	labels_matched = sum(1 for m in label_matches if m["matched"])
	# compute max delta for matched lines
	line_max_delta = 0.0
	for m in line_matches:
		if m["matched"] and m["midpoint_delta"] is not None:
			line_max_delta = max(line_max_delta, float(m["midpoint_delta"]))
	# compute max delta for matched labels
	label_max_delta = 0.0
	for m in label_matches:
		if m["matched"]:
			x_d = float(m.get("x_delta") or 0.0)
			y_d = float(m.get("y_delta") or 0.0)
			label_max_delta = max(label_max_delta, x_d, y_d)
	return {
		"svg": str(svg_path),
		"pdf": str(pdf_path),
		"lines": {
			"svg_count": len(svg_lines),
			"pdf_count": len(pdf_lines),
			"matched": lines_matched,
			"max_delta": round(line_max_delta, 4),
		},
		"labels": {
			"svg_count": len(svg_labels),
			"pdf_count": len(pdf_labels),
			"matched": labels_matched,
			"max_delta": round(label_max_delta, 4),
		},
		"rings": {
			"svg_count": len(svg_rings),
			"pdf_count": len(pdf_rings),
			"matched": sum(1 for m in ring_matches if m["matched"]),
		},
		"wedges": {
			"svg_count": len(svg_wedges),
			"pdf_count": len(pdf_wedges),
			"matched": sum(1 for m in wedge_matches if m["matched"]),
		},
		"parity_score": round(summary["parity_score"], 4),
		"parity_summary": summary,
	}


#============================================
def build_parity_report(
		pair_reports: list[dict],
		args: argparse.Namespace) -> dict:
	"""Build a full JSON parity report from file pair results.

	Args:
		pair_reports: list of per-pair analysis dicts.
		args: parsed CLI arguments.

	Returns:
		full JSON report dict.
	"""
	# aggregate summary stats
	total_line_matches = sum(r["lines"]["matched"] for r in pair_reports)
	total_label_matches = sum(r["labels"]["matched"] for r in pair_reports)
	total_svg_lines = sum(r["lines"]["svg_count"] for r in pair_reports)
	total_pdf_lines = sum(r["lines"]["pdf_count"] for r in pair_reports)
	total_svg_labels = sum(r["labels"]["svg_count"] for r in pair_reports)
	total_pdf_labels = sum(r["labels"]["pdf_count"] for r in pair_reports)
	# compute overall parity score from individual scores
	scores = [r["parity_score"] for r in pair_reports]
	overall_score = sum(scores) / float(len(scores)) if scores else 0.0
	return {
		"schema_version": 1,
		"mode": "parity",
		"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
		"svg_glob": args.svg_glob,
		"pdf_glob": args.pdf_glob,
		"position_tolerance": args.position_tolerance,
		"file_pairs": [
			{
				"svg": r["svg"],
				"pdf": r["pdf"],
				"lines": r["lines"],
				"labels": r["labels"],
				"rings": r["rings"],
				"wedges": r["wedges"],
				"parity_score": r["parity_score"],
			}
			for r in pair_reports
		],
		"summary": {
			"files_compared": len(pair_reports),
			"overall_parity_score": round(overall_score, 4),
			"total_line_matches": total_line_matches,
			"total_label_matches": total_label_matches,
			"unmatched_svg_lines": total_svg_lines - total_line_matches,
			"unmatched_pdf_lines": total_pdf_lines - total_line_matches,
			"unmatched_svg_labels": total_svg_labels - total_label_matches,
			"unmatched_pdf_labels": total_pdf_labels - total_label_matches,
		},
	}


#============================================
def build_pdf_only_report(
		pdf_reports: list[dict],
		args: argparse.Namespace) -> dict:
	"""Build a full JSON report for PDF-only analysis mode.

	Args:
		pdf_reports: list of per-file analysis dicts from analyze_pdf_file.
		args: parsed CLI arguments.

	Returns:
		full JSON report dict.
	"""
	return {
		"schema_version": 1,
		"mode": "pdf_only",
		"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
		"pdf_glob": args.pdf_glob,
		"exclude_haworth_base_ring": bool(args.exclude_haworth_base_ring),
		"files": pdf_reports,
		"summary": {
			"files_analyzed": len(pdf_reports),
			"total_labels": sum(r.get("text_labels_total", 0) for r in pdf_reports),
			"total_bonds": sum(
				r.get("line_length_stats", {}).get("all_lines", {}).get("count", 0)
				for r in pdf_reports
			),
		},
	}


#============================================
def format_parity_text_report(report: dict) -> str:
	"""Format parity report as human-readable text.

	Args:
		report: full JSON report dict.

	Returns:
		formatted text string.
	"""
	banner = "=" * 56
	text_lines = []
	text_lines.append(banner)
	text_lines.append(" CAIRO PDF PARITY REPORT")
	text_lines.append(banner)
	text_lines.append(f"Generated: {report.get('generated_at', 'unknown')}")
	text_lines.append(f"Mode: {report.get('mode', 'unknown')}")
	text_lines.append("")
	if report.get("mode") == "parity":
		summary = report.get("summary", {})
		text_lines.append(f"{'Files compared:':<42}{summary.get('files_compared', 0):>6}")
		text_lines.append(
			f"{'Overall parity score:':<42}"
			f"{summary.get('overall_parity_score', 0.0):>6.4f}"
		)
		text_lines.append(f"{'Total line matches:':<42}{summary.get('total_line_matches', 0):>6}")
		text_lines.append(f"{'Total label matches:':<42}{summary.get('total_label_matches', 0):>6}")
		text_lines.append(
			f"{'Unmatched SVG lines:':<42}"
			f"{summary.get('unmatched_svg_lines', 0):>6}"
		)
		text_lines.append(
			f"{'Unmatched PDF lines:':<42}"
			f"{summary.get('unmatched_pdf_lines', 0):>6}"
		)
		text_lines.append("")
		# per-file details
		for pair in report.get("file_pairs", []):
			svg_name = pathlib.Path(str(pair.get("svg", ""))).name
			pdf_name = pathlib.Path(str(pair.get("pdf", ""))).name
			text_lines.append(f"  {svg_name} <-> {pdf_name}")
			text_lines.append(
				f"    Lines: {pair['lines']['matched']}/{pair['lines']['svg_count']} matched"
				f"  (max delta {pair['lines']['max_delta']:.4f})"
			)
			text_lines.append(
				f"    Labels: {pair['labels']['matched']}/{pair['labels']['svg_count']} matched"
				f"  (max delta {pair['labels']['max_delta']:.4f})"
			)
			text_lines.append(f"    Parity score: {pair.get('parity_score', 0.0):.4f}")
			text_lines.append("")
	elif report.get("mode") == "pdf_only":
		summary = report.get("summary", {})
		text_lines.append(f"{'Files analyzed:':<42}{summary.get('files_analyzed', 0):>6}")
		text_lines.append(f"{'Total labels:':<42}{summary.get('total_labels', 0):>6}")
		text_lines.append(f"{'Total bonds:':<42}{summary.get('total_bonds', 0):>6}")
	text_lines.append("")
	return "\n".join(text_lines) + "\n"


#============================================
def main() -> None:
	"""Run Cairo PDF parity analysis and write reports."""
	args = parse_args()
	repo_root = get_repo_root()
	# resolve PDF paths
	pdf_paths = resolve_pdf_paths(repo_root, args.pdf_glob)
	if not pdf_paths:
		raise RuntimeError(f"No PDF files matched pdf_glob: {args.pdf_glob!r}")
	# determine mode: parity (SVG+PDF) or PDF-only
	parity_mode = args.svg_glob is not None
	has_violations = False
	if parity_mode:
		# resolve SVG paths and pair with PDF
		svg_paths = resolve_svg_paths(repo_root, args.svg_glob)
		if not svg_paths:
			raise RuntimeError(f"No SVG files matched svg_glob: {args.svg_glob!r}")
		pairs = pair_files_by_stem(svg_paths, pdf_paths)
		if not pairs:
			raise RuntimeError("No SVG/PDF file pairs found with matching stem names.")
		print(f"Parity mode: {len(pairs)} file pairs found.")
		# run parity analysis on each pair
		pair_reports = []
		for svg_path, pdf_path in pairs:
			pair_report = analyze_parity_pair(svg_path, pdf_path, args.position_tolerance)
			pair_reports.append(pair_report)
			score = pair_report["parity_score"]
			svg_name = svg_path.name
			# brief per-file output
			print(f"  {svg_name}: parity={score:.4f}")
			if score < 1.0:
				has_violations = True
		json_report = build_parity_report(pair_reports, args)
	else:
		# PDF-only mode
		print(f"PDF-only mode: {len(pdf_paths)} files found.")
		pdf_reports = []
		for pdf_path in pdf_paths:
			report = analyze_pdf_file(
				pdf_path,
				exclude_haworth_base_ring=args.exclude_haworth_base_ring,
			)
			pdf_reports.append(report)
			pdf_name = pdf_path.name
			labels = report.get("text_labels_total", 0)
			print(f"  {pdf_name}: labels={labels}")
		json_report = build_pdf_only_report(pdf_reports, args)
	# write reports
	text_content = format_parity_text_report(json_report)
	json_report_path = pathlib.Path(args.json_report)
	text_report_path = pathlib.Path(args.text_report)
	if not json_report_path.is_absolute():
		json_report_path = (repo_root / json_report_path).resolve()
	if not text_report_path.is_absolute():
		text_report_path = (repo_root / text_report_path).resolve()
	json_report_path.parent.mkdir(parents=True, exist_ok=True)
	text_report_path.parent.mkdir(parents=True, exist_ok=True)
	json_report_path.write_text(json.dumps(json_report, indent=2), encoding="utf-8")
	text_report_path.write_text(text_content, encoding="utf-8")
	print(f"\nWrote JSON report: {json_report_path}")
	print(f"Wrote text report: {text_report_path}")
	if args.fail_on_mismatch and has_violations:
		raise SystemExit(2)


if __name__ == "__main__":
	main()
