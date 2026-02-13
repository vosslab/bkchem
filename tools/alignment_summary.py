#!/usr/bin/env python3
"""Print alignment summary from an existing JSON report without re-running analysis.

Usage:
	python tools/alignment_summary.py
	python tools/alignment_summary.py --json-report path/to/report.json
"""

# Standard Library
import argparse
import json
import math
import pathlib
import sys


DEFAULT_JSON_REPORT = "output_smoke/glyph_bond_alignment_report.json"


#============================================
def _get_repo_root() -> pathlib.Path:
	"""Walk up from this script to find the repo root (contains .git/)."""
	current = pathlib.Path(__file__).resolve().parent
	while current != current.parent:
		if (current / ".git").exists():
			return current
		current = current.parent
	return pathlib.Path.cwd()


#============================================
def print_summary(file_summary: dict, file_top_misses: list[dict]) -> None:
	"""Print concise alignment summary to stdout."""
	alignment_pct = file_summary["alignment_rate"] * 100.0
	print(f"{'Files analyzed:':<42}{file_summary['files_analyzed']:>6}")
	print(f"{'Labels analyzed:':<42}{file_summary['labels_analyzed']:>6}")
	print(
		f"{'  Aligned:':<42}{file_summary['aligned_labels']:>6}"
		f"  ({alignment_pct:.1f}%)"
	)
	print(
		f"{'Bonds (detected / checked):':<42}"
		f"{file_summary['total_bonds_detected']:>6} / {file_summary['total_bonds_checked']}"
	)
	print()
	# violation summary -- only print nonzero categories
	violation_total = (
		file_summary.get("alignment_outside_tolerance_count", 0)
		+ file_summary.get("lattice_angle_violation_count", 0)
		+ file_summary.get("glyph_glyph_overlap_count", 0)
		+ file_summary.get("bond_bond_overlap_count", 0)
		+ file_summary.get("bond_glyph_overlap_count", 0)
		+ file_summary.get("hatched_thin_conflict_count", 0)
	)
	print(f"{'Violations:':<42}{violation_total:>6}")
	if violation_total > 0:
		violation_items = [
			("  Alignment outside tolerance", "alignment_outside_tolerance_count"),
			("  Lattice angle violations", "lattice_angle_violation_count"),
			("  Glyph/glyph overlaps", "glyph_glyph_overlap_count"),
			("  Bond/bond overlaps", "bond_bond_overlap_count"),
			("  Bond/glyph overlaps", "bond_glyph_overlap_count"),
			("  Hatched/thin conflicts", "hatched_thin_conflict_count"),
		]
		for label, key in violation_items:
			count = file_summary.get(key, 0)
			if count > 0:
				print(f"{label + ':':<42}{count:>6}")
	print()
	# top misses -- show at most 3
	if file_top_misses:
		print("Top misses:")
		for item in file_top_misses[:3]:
			dist = item["distance"]
			dist_text = "inf" if math.isinf(dist) else f"{dist:.3f}"
			svg_name = pathlib.Path(str(item["svg"])).stem
			print(
				f"  {svg_name:<28}  label={item['text']:<6}"
				f"  reason={item['reason']:<30}  dist={dist_text}"
			)
		remaining = len(file_top_misses) - 3
		if remaining > 0:
			print(f"  ... and {remaining} more (see text report)")
	# per-label alignment stats
	label_stats = file_summary.get("alignment_label_type_stats", {})
	if label_stats:
		def _fmt_triple(stats: dict) -> str:
			if stats.get("count", 0) == 0:
				return "(none)"
			return f"{stats['mean']:.2f}/{stats['stddev']:.2f}/{stats['median']:.2f}"
		print(f"Per-label alignment:  {'bond_end_gap(a/s/m)':>21}  {'perp_offset(a/s/m)':>20}")
		# ALL row
		total_ct = file_summary.get("labels_analyzed", 0)
		total_al = file_summary.get("aligned_labels", 0)
		total_rate = file_summary.get("alignment_rate", 0.0) * 100.0
		all_gap = file_summary.get("glyph_to_bond_end_signed_distance_stats", {})
		all_aln = file_summary.get("alignment_distance_stats", {})
		print(
			f"  {'ALL':<8} {total_al:>3}/{total_ct:<3} ({total_rate:>5.1f}%)"
			f"  {_fmt_triple(all_gap):>18}  {_fmt_triple(all_aln):>20}"
		)
		for label_text in sorted(label_stats.keys()):
			entry = label_stats[label_text]
			count = entry["count"]
			aligned_ct = entry["aligned_count"]
			rate = entry["alignment_rate"] * 100.0
			gap_s = entry.get("gap_distance_stats", {})
			align_s = entry.get("alignment_distance_stats", {})
			print(
				f"  {label_text:<8} {aligned_ct:>3}/{count:<3} ({rate:>5.1f}%)"
				f"  {_fmt_triple(gap_s):>18}  {_fmt_triple(align_s):>20}"
			)
		print()


#============================================
def main() -> None:
	"""Load JSON report and print summary."""
	parser = argparse.ArgumentParser(
		description="Print alignment summary from an existing JSON report.",
	)
	parser.add_argument(
		"--json-report",
		default=DEFAULT_JSON_REPORT,
		help=f"Path to JSON report file (default: {DEFAULT_JSON_REPORT})",
	)
	args = parser.parse_args()

	json_path = pathlib.Path(args.json_report)
	if not json_path.is_absolute():
		json_path = (_get_repo_root() / json_path).resolve()

	if not json_path.exists():
		print(f"Error: JSON report not found: {json_path}", file=sys.stderr)
		print("Run tools/measure_glyph_bond_alignment.py first to generate it.", file=sys.stderr)
		raise SystemExit(1)

	with open(json_path, encoding="utf-8") as fh:
		json_data = json.load(fh)

	file_summary = json_data["debug"]["full_summary"]
	file_top_misses = json_data.get("top_misses", [])

	print(f"Report: {json_path}")
	print(f"Generated: {json_data.get('generated_at', 'unknown')}")
	print()
	print_summary(file_summary, file_top_misses)


if __name__ == "__main__":
	main()
