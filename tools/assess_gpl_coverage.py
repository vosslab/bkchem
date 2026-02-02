#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later

"""Assess GPL/LGPL coverage based on git history.

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


def classify_file(first_date, last_date, cutoff):
	if not first_date:
		return "Untracked"
	if first_date >= cutoff:
		return "Pure LGPL-3.0-or-later"
	if last_date < cutoff:
		return "Pure GPL-2.0"
	return "Mixed"


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
	total_days = (last_day - first_day).days
	if total_days <= 0:
		return None
	end = min(last_day, cutoff_day)
	days_before = (end - first_day).days
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


def build_records(repo_root, cutoff, include_lines):
	records = []
	files = iter_python_files(repo_root)
	total = len(files)
	show_progress = sys.stderr.isatty()
	bar_width = 30
	for index, path in enumerate(files, start=1):
		rel_path = os.path.relpath(path, repo_root)
		first_date = first_commit_date(repo_root, rel_path)
		last_date = last_commit_date(repo_root, rel_path)
		total_commits = count_commits(repo_root, rel_path)
		commits_before = count_commits(repo_root, rel_path, before=cutoff)
		commits_after = count_commits(repo_root, rel_path, since=cutoff)
		classification = classify_file(first_date, last_date, cutoff)
		gpl_commit_pct = (commits_before / total_commits) * 100.0 if total_commits else None
		lines_before = None
		lines_after = None
		gpl_line_pct = None
		if include_lines:
			lines_before = count_lines_added(repo_root, rel_path, before=cutoff)
			lines_after = count_lines_added(repo_root, rel_path, since=cutoff)
			total_lines = lines_before + lines_after
			if total_lines:
				gpl_line_pct = (lines_before / total_lines) * 100.0
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
			"gpl_commit_pct": gpl_commit_pct,
			"lines_before": lines_before,
			"lines_after": lines_after,
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
	for key in ("Pure GPL-2.0", "Pure LGPL-3.0-or-later", "Mixed", "Untracked"):
		count = counts[key]
		pct = (count / total * 100.0) if total else 0.0
		print(f"{key}: {count} ({pct:.1f}%)")


def print_mixed(records):
	mixed = [r for r in records if r["classification"] == "Mixed"]
	if not mixed:
		return
	print("\nMixed files (reporting only):")
	print("Path\tTotal\tGPL\tLGPL\tGPL% (commits)")
	for record in mixed:
		gpl_pct = record["gpl_commit_pct"]
		gpl_text = f"{gpl_pct:.1f}" if gpl_pct is not None else ""
		print(
			f"{record['path']}\t{record['total_commits']}\t"
			f"{record['commits_before']}\t{record['commits_after']}\t{gpl_text}"
		)


def print_spdx_issues(records):
	missing = []
	mismatched = []
	for record in records:
		expected = expected_spdx(record["classification"])
		spdx = record["spdx"]
		if not spdx and expected:
			missing.append(record["path"])
		elif spdx and expected and spdx != expected:
			mismatched.append((record["path"], spdx, expected))
	if missing:
		print("\nMissing SPDX headers:")
		for path in missing:
			print(path)
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
		"first_date",
		"last_date",
		"total_commits",
		"commits_before",
		"commits_after",
		"gpl_commit_pct",
		"gpl_time_pct",
		"spdx",
	]
	if include_lines:
		fieldnames.extend(["lines_before", "lines_after", "gpl_line_pct"])
	writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
	writer.writeheader()
	for record in records:
		row = {key: record.get(key, "") for key in fieldnames}
		writer.writerow(row)


def print_file_report(records, file_path):
	matches = [r for r in records if r["path"] == file_path]
	if not matches:
		print(f"No data for file: {file_path}")
		return
	record = matches[0]
	print(f"File: {record['path']}")
	print(f"Classification: {record['classification']}")
	print(f"First commit: {record['first_date']}")
	print(f"Last commit: {record['last_date']}")
	print(
		f"Commits: total={record['total_commits']} "
		f"before={record['commits_before']} after={record['commits_after']}"
	)
	if record["gpl_commit_pct"] is not None:
		print(f"GPL commit percentage: {record['gpl_commit_pct']:.1f}%")
	if record["gpl_line_pct"] is not None:
		print(f"GPL line percentage: {record['gpl_line_pct']:.1f}%")
	if record["gpl_time_pct"] is not None:
		print(f"GPL time percentage: {record['gpl_time_pct']:.1f}%")
	if record["spdx"]:
		print(f"SPDX: {record['spdx']}")
	else:
		print("SPDX: (missing)")


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
		records = build_records(repo_root, args.cutoff, args.include_lines)
	except GitError as exc:
		print(f"ERROR: {exc}", file=sys.stderr)
		return 2
	if args.csv:
		output_csv(records, args.include_lines)
		return 0
	if args.file_path:
		print_file_report(records, args.file_path)
		return 0
	if args.missing_headers:
		list_missing_headers(records)
		return 0
	if args.summary:
		print_summary(records)
		return 0
	print_full_report(records, args.cutoff)
	return 0


if __name__ == "__main__":
	sys.exit(main())
