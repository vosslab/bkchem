#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later

"""Assess GPL/LGPL coverage using git blame line dates.

Reporting-only tool: metrics inform scope and outreach, not relicensing.
"""

# Standard Library
import argparse
import csv
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path


SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9\.-]+)")


class GitError(RuntimeError):
	pass


def run_git(args, repo_root):
	try:
		result = subprocess.run(
			args,
			cwd=repo_root,
			check=False,
			capture_output=True,
			text=True,
		)
	except FileNotFoundError as exc:
		raise GitError("git was not found on PATH") from exc
	if result.returncode != 0:
		stderr = result.stderr.strip()
		raise GitError(stderr or "git command failed")
	return result.stdout


def iter_python_files(repo_root):
	paths = [repo_root / "packages", repo_root / "tests"]
	files = []
	for root in paths:
		if not root.exists():
			continue
		files.extend(root.rglob("*.py"))
	return sorted(files)


def parse_iso_date(text):
	if not text:
		return None
	try:
		return datetime.datetime.fromisoformat(text.strip())
	except ValueError:
		return None


def cutoff_timestamp(cutoff):
	cutoff_dt = datetime.datetime.fromisoformat(cutoff)
	cutoff_dt = cutoff_dt.replace(tzinfo=datetime.timezone.utc)
	return int(cutoff_dt.timestamp())


def as_date_string(text):
	parsed = parse_iso_date(text)
	if not parsed:
		return ""
	return parsed.date().isoformat()


def first_commit_date(repo_root, rel_path):
	output = run_git(
		["git", "log", "--follow", "--format=%aI", "--reverse", "--", rel_path],
		repo_root,
	)
	lines = [line for line in output.splitlines() if line.strip()]
	return lines[0] if lines else ""


def last_commit_date(repo_root, rel_path):
	output = run_git(
		["git", "log", "--format=%aI", "-n1", "--", rel_path],
		repo_root,
	)
	lines = [line for line in output.splitlines() if line.strip()]
	return lines[0] if lines else ""


def count_commits(repo_root, rel_path, before=None, since=None):
	cmd = ["git", "log", "--oneline"]
	if before:
		cmd.append(f"--before={before}")
	if since:
		cmd.append(f"--since={since}")
	cmd.extend(["--", rel_path])
	output = run_git(cmd, repo_root)
	return len([line for line in output.splitlines() if line.strip()])


def count_lines_added(repo_root, rel_path, before=None, since=None):
	cmd = ["git", "log", "--numstat", "--pretty=%H"]
	if before:
		cmd.append(f"--before={before}")
	if since:
		cmd.append(f"--since={since}")
	cmd.extend(["--", rel_path])
	output = run_git(cmd, repo_root)
	total = 0
	for line in output.splitlines():
		if "\t" not in line:
			continue
		parts = line.split("\t")
		if len(parts) < 2:
			continue
		added = parts[0]
		if added.isdigit():
			total += int(added)
	return total


def line_commit_times(repo_root, rel_path):
	try:
		output = run_git(
			["git", "blame", "--line-porcelain", "--date=unix", "--", rel_path],
			repo_root,
		)
	except GitError:
		return None
	times = []
	for line in output.splitlines():
		if line.startswith("committer-time "):
			parts = line.split()
			if len(parts) == 2 and parts[1].isdigit():
				times.append(int(parts[1]))
	return times


def blame_line_samples(repo_root, rel_path, cutoff, sample_size):
	try:
		output = run_git(
			["git", "blame", "--line-porcelain", "--date=unix", "--", rel_path],
			repo_root,
		)
	except GitError:
		return None
	cutoff_ts = cutoff_timestamp(cutoff)
	entries = []
	current = {}
	for line in output.splitlines():
		if not line:
			continue
		if line[0] != "\t" and " " in line:
			parts = line.split()
			hash_text = parts[0]
			if hash_text.startswith("^"):
				hash_text = hash_text[1:]
			if hash_text and re.fullmatch(r"[0-9a-f]{7,}", hash_text):
				current = {
					"hash": hash_text[:10],
					"final_lineno": int(parts[2]) if len(parts) > 2 else None,
					"committer_time": None,
				}
				continue
		if line.startswith("committer-time "):
			parts = line.split()
			if len(parts) == 2 and parts[1].isdigit():
				current["committer_time"] = int(parts[1])
			continue
		if line.startswith("\t"):
			if current.get("committer_time") is None:
				continue
			entries.append({
				"hash": current.get("hash", ""),
				"final_lineno": current.get("final_lineno"),
				"committer_time": current["committer_time"],
				"text": line[1:],
			})
	if not entries:
		return None
	before = [e for e in entries if e["committer_time"] < cutoff_ts]
	after = [e for e in entries if e["committer_time"] >= cutoff_ts]
	before_sorted = sorted(before, key=lambda e: e["committer_time"])
	after_sorted = sorted(after, key=lambda e: e["committer_time"])
	return {
		"before": before_sorted[-sample_size:],
		"after": after_sorted[:sample_size],
	}


def line_date_stats(repo_root, rel_path, cutoff):
	times = line_commit_times(repo_root, rel_path)
	if times is None:
		return "Untracked"
	if not times:
		return {
			"total": 0,
			"before": 0,
			"after": 0,
			"min": "",
			"max": "",
		}
	cutoff_ts = cutoff_timestamp(cutoff)
	total = len(times)
	before = sum(1 for ts in times if ts < cutoff_ts)
	after = total - before
	min_ts = min(times)
	max_ts = max(times)
	min_date = datetime.datetime.fromtimestamp(min_ts, tz=datetime.timezone.utc).date().isoformat()
	max_date = datetime.datetime.fromtimestamp(max_ts, tz=datetime.timezone.utc).date().isoformat()
	return {
		"total": total,
		"before": before,
		"after": after,
		"min": min_date,
		"max": max_date,
	}


def gpl_time_percentage(first_date, last_date, cutoff):
	first_dt = parse_iso_date(first_date)
	last_dt = parse_iso_date(last_date)
	if not first_dt or not last_dt:
		return None
	first_day = first_dt.date()
	last_day = last_dt.date()
	if last_day < first_day:
		return None
	cutoff_day = datetime.date.fromisoformat(cutoff)
	if last_day <= cutoff_day:
		return 100.0
	if first_day >= cutoff_day:
		return 0.0
	total_days = (last_day - first_day).days
	if total_days <= 0:
		return None
	end = min(last_day, cutoff_day)
	days_before = max(0, (end - first_day).days)
	return (days_before / total_days) * 100.0


def get_spdx_identifier(path):
	try:
		lines = path.read_text(encoding="utf-8").splitlines()
	except (OSError, UnicodeDecodeError):
		return ""
	for line in lines[:5]:
		match = SPDX_RE.search(line)
		if match:
			return match.group(1)
	return ""


def expected_spdx(classification):
	if classification == "Pure LGPL-3.0-or-later":
		return "LGPL-3.0-or-later"
	if classification in ("Pure GPL-2.0", "Mixed"):
		return "GPL-2.0"
	return ""


def build_records(repo_root, cutoff, include_lines, files=None, show_progress=None):
	records = []
	if files is None:
		files = iter_python_files(repo_root)
	else:
		files = [Path(path) for path in files]
	total = len(files)
	if show_progress is None:
		show_progress = sys.stderr.isatty() and total > 1
	bar_width = 30
	for index, path in enumerate(files, start=1):
		rel_path = os.path.relpath(path, repo_root)
		first_date = first_commit_date(repo_root, rel_path)
		last_date = last_commit_date(repo_root, rel_path)
		total_commits = count_commits(repo_root, rel_path)
		commits_before = count_commits(repo_root, rel_path, before=cutoff)
		commits_after = count_commits(repo_root, rel_path, since=cutoff)
		line_stats = line_date_stats(repo_root, rel_path, cutoff)
		if line_stats == "Untracked":
			classification = "Untracked"
			classification_source = "blame"
			line_total = 0
			line_before = 0
			line_after = 0
			line_min_date = ""
			line_max_date = ""
		else:
			line_total = line_stats["total"]
			line_before = line_stats["before"]
			line_after = line_stats["after"]
			line_min_date = line_stats["min"]
			line_max_date = line_stats["max"]
			if line_total == 0:
				classification = "Untracked"
			elif line_before == 0:
				classification = "Pure LGPL-3.0-or-later"
			elif line_after == 0:
				classification = "Pure GPL-2.0"
			else:
				classification = "Mixed"
			classification_source = "blame"
		gpl_commit_pct = (commits_before / total_commits) * 100.0 if total_commits else None
		line_add_before = None
		line_add_after = None
		gpl_line_pct = None
		if line_total:
			gpl_line_pct = (line_before / line_total) * 100.0
		if include_lines:
			line_add_before = count_lines_added(repo_root, rel_path, before=cutoff)
			line_add_after = count_lines_added(repo_root, rel_path, since=cutoff)
		gpl_time_pct = gpl_time_percentage(first_date, last_date, cutoff)
		spdx = get_spdx_identifier(path)
		records.append({
			"path": rel_path,
			"first_date": first_date,
			"last_date": last_date,
			"total_commits": total_commits,
			"commits_before": commits_before,
			"commits_after": commits_after,
			"classification": classification,
			"classification_source": classification_source,
			"gpl_commit_pct": gpl_commit_pct,
			"line_total": line_total,
			"line_before": line_before,
			"line_after": line_after,
			"line_min_date": line_min_date,
			"line_max_date": line_max_date,
			"line_add_before": line_add_before,
			"line_add_after": line_add_after,
			"gpl_line_pct": gpl_line_pct,
			"gpl_time_pct": gpl_time_pct,
			"spdx": spdx,
		})
		if show_progress:
			done = int((index / total) * bar_width) if total else bar_width
			bar = "#" * done + "-" * (bar_width - done)
			sys.stderr.write(f"\r[{bar}] {index}/{total}")
			sys.stderr.flush()
	if show_progress and total:
		sys.stderr.write("\n")
		sys.stderr.flush()
	return records


def print_summary(records):
	total = len(records)
	counts = {
		"Pure GPL-2.0": 0,
		"Pure LGPL-3.0-or-later": 0,
		"Mixed": 0,
		"Untracked": 0,
	}
	for record in records:
		counts[record["classification"]] += 1
	print(f"Total Python files: {total}")
	labels = [
		("Pure GPL-2.0", "Pure GPLv2 (2024 and earlier)"),
		("Pure LGPL-3.0-or-later", "Pure LGPLv3 (2025 and later)"),
		("Mixed", "Mixed (GPLv2 + LGPLv3)"),
		("Untracked", "Untracked (no blame data)"),
	]
	for key, label in labels:
		count = counts[key]
		pct = (count / total * 100.0) if total else 0.0
		print(f"{label}: {count} ({pct:.1f}%)")


def print_mixed(records):
	mixed = [r for r in records if r["classification"] == "Mixed"]
	if not mixed:
		return
	print("\nMixed files (reporting only):")
	print("Path\tTotal\tGPLv2\tLGPLv3\tGPLv2% (lines)")
	for record in mixed:
		gpl_pct = record["gpl_line_pct"]
		gpl_text = f"{gpl_pct:.1f}" if gpl_pct is not None else ""
		print(
			f"{record['path']}\t{record['line_total']}\t"
			f"{record['line_before']}\t{record['line_after']}\t{gpl_text}"
		)


def print_spdx_issues(records):
	mismatched = []
	for record in records:
		expected = expected_spdx(record["classification"])
		spdx = record["spdx"]
		if spdx and expected and spdx != expected:
			mismatched.append((record["path"], spdx, expected))
	if mismatched:
		print("\nSPDX mismatches:")
		for path, spdx, expected in mismatched:
			print(f"{path}: {spdx} (expected {expected})")


def print_full_report(records, cutoff):
	print("GPL/LGPL coverage report (reporting only)")
	print(f"Cutoff date: {cutoff}")
	print_summary(records)
	print_mixed(records)
	print_spdx_issues(records)


def output_csv(records, include_lines):
	fieldnames = [
		"path",
		"classification",
		"classification_source",
		"first_date",
		"last_date",
		"total_commits",
		"commits_before",
		"commits_after",
		"gpl_commit_pct",
		"line_total",
		"line_before",
		"line_after",
		"line_min_date",
		"line_max_date",
		"gpl_time_pct",
		"spdx",
	]
	if include_lines:
		fieldnames.extend(["line_add_before", "line_add_after"])
	fieldnames.append("gpl_line_pct")
	writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
	writer.writeheader()
	for record in records:
		row = {key: record.get(key, "") for key in fieldnames}
		writer.writerow(row)


def print_file_report(records, file_path, repo_root, cutoff):
	matches = [r for r in records if r["path"] == file_path]
	if not matches:
		print(f"No data for file: {file_path}")
		return
	record = matches[0]
	print(f"File: {record['path']}")
	class_map = {
		"Pure GPL-2.0": "Pure GPLv2 (2024 and earlier)",
		"Pure LGPL-3.0-or-later": "Pure LGPLv3 (2025 and later)",
		"Mixed": "Mixed (GPLv2 + LGPLv3)",
		"Untracked": "Untracked (no blame data)",
	}
	print(f"Classification: {class_map.get(record['classification'], record['classification'])}")
	print(f"Cutoff date: {cutoff}")
	print(f"First commit: {record['first_date']} ({as_date_string(record['first_date'])})")
	print(f"Last commit: {record['last_date']} ({as_date_string(record['last_date'])})")
	print(
		f"Commits: total={record['total_commits']} "
		f"GPLv2={record['commits_before']} LGPLv3={record['commits_after']}"
	)
	print(
		f"Lines: total={record['line_total']} GPLv2={record['line_before']} "
		f"LGPLv3={record['line_after']}"
	)
	if record["gpl_line_pct"] is not None:
		print(f"GPLv2 line percentage: {record['gpl_line_pct']:.1f}%")
	if record["line_min_date"] or record["line_max_date"]:
		print(f"Line date range: {record['line_min_date']} .. {record['line_max_date']}")
	if record.get("line_add_before") is not None or record.get("line_add_after") is not None:
		print(
			f"Lines added: GPLv2={record.get('line_add_before')} "
			f"LGPLv3={record.get('line_add_after')}"
		)
	if record["gpl_commit_pct"] is not None:
		print(f"GPLv2 commit percentage (reporting only): {record['gpl_commit_pct']:.1f}%")
	if record["gpl_time_pct"] is not None:
		print(f"GPLv2 time percentage: {record['gpl_time_pct']:.1f}%")
	print_spot_check(repo_root, file_path, cutoff)


def print_spot_check(repo_root, rel_path, cutoff, sample_size=3):
	samples = blame_line_samples(repo_root, rel_path, cutoff, sample_size)
	if samples is None:
		print("Spot check: no blame samples available.")
		return
	def format_entry(entry):
		timestamp = datetime.datetime.fromtimestamp(
			entry["committer_time"], tz=datetime.timezone.utc
		)
		date_text = timestamp.date().isoformat()
		lineno = entry.get("final_lineno")
		text = entry.get("text", "").rstrip()
		if not text:
			text = "(blank)"
		return f"{date_text} {entry.get('hash','')}:{lineno} {text}"
	print("Spot check samples (closest to cutoff):")
	print("GPLv2 side (before cutoff):")
	if samples["before"]:
		for entry in samples["before"]:
			print(format_entry(entry))
	else:
		print("(none)")
	print("LGPLv3 side (after cutoff):")
	if samples["after"]:
		for entry in samples["after"]:
			print(format_entry(entry))
	else:
		print("(none)")


def list_missing_headers(records):
	for record in records:
		if not record["spdx"] and expected_spdx(record["classification"]):
			print(record["path"])


def parse_args():
	parser = argparse.ArgumentParser(
		description="Assess GPL/LGPL coverage based on git history (reporting only)."
	)
	parser.add_argument(
		"--summary",
		action="store_true",
		help="Show summary counts only",
	)
	parser.add_argument(
		"--csv",
		action="store_true",
		help="Output CSV instead of the text report",
	)
	parser.add_argument(
		"--file",
		dest="file_path",
		default=None,
		help="Report details for a single file (repo-relative path)",
	)
	parser.add_argument(
		"--missing-headers",
		action="store_true",
		help="List files missing SPDX headers",
	)
	parser.add_argument(
		"--show-spdx",
		action="store_true",
		help="Include SPDX mismatch reporting in the full report",
	)
	parser.add_argument(
		"--cutoff",
		default="2025-01-01",
		help="Cutoff date for reporting (YYYY-MM-DD)",
	)
	parser.add_argument(
		"--include-lines",
		action="store_true",
		help="Include line-add metrics in the report",
	)
	return parser.parse_args()


def main():
	args = parse_args()
	repo_root = Path(__file__).resolve().parents[1]
	if not (repo_root / ".git").exists():
		raise GitError("Repository .git directory was not found")
	try:
		if args.file_path:
			file_path = (repo_root / args.file_path).resolve()
			records = build_records(
				repo_root,
				args.cutoff,
				args.include_lines,
				files=[file_path],
				show_progress=False,
			)
		else:
			records = build_records(repo_root, args.cutoff, args.include_lines)
	except GitError as exc:
		print(f"ERROR: {exc}", file=sys.stderr)
		return 2
	if args.csv:
		output_csv(records, args.include_lines)
		return 0
	if args.file_path:
		print_file_report(records, args.file_path, repo_root, args.cutoff)
		return 0
	if args.missing_headers:
		list_missing_headers(records)
		return 0
	if args.summary:
		print_summary(records)
		return 0
	if args.show_spdx:
		print_full_report(records, args.cutoff)
	else:
		print("GPL/LGPL coverage report (reporting only)")
		print(f"Cutoff date: {args.cutoff}")
		print_summary(records)
		print_mixed(records)
	return 0


if __name__ == "__main__":
	sys.exit(main())
