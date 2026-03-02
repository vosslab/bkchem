#!/usr/bin/env python3
"""Regenerate methanol A/B smoke SVGs via the authoritative pytest.

This wrapper intentionally avoids a separate rendering code path. It runs the
pytest target that writes:
  - output_smoke/methanol_A_mask.svg
  - output_smoke/methanol_B_clip.svg

Usage:
	source source_me.sh && python3 tools/compare_bond_mask_vs_clip.py
"""

# Standard Library
import os
import subprocess
import sys


_PREFERRED_PYTHON = "/opt/homebrew/opt/python@3.12/bin/python3.12"
_TEST_PATH = "packages/oasa/tests/test_methanol_ab_compare.py"
_TEST_FILTER = "svg_output_smoke"


#============================================
def _repo_root() -> str:
	"""Return absolute repository root for this script."""
	return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


#============================================
def _resolve_python() -> str:
	"""Prefer Homebrew Python 3.12; fall back to current interpreter."""
	if os.path.isfile(_PREFERRED_PYTHON):
		return _PREFERRED_PYTHON
	if sys.executable:
		return sys.executable
	return "python3"


#============================================
def main() -> int:
	repo_root = _repo_root()
	python_bin = _resolve_python()
	cmd = [
		python_bin,
		"-m",
		"pytest",
		_TEST_PATH,
		"-k",
		_TEST_FILTER,
		"-q",
	]
	print("Running:", " ".join(cmd))
	result = subprocess.run(cmd, cwd=repo_root)
	if result.returncode != 0:
		print("Pytest failed; methanol smoke SVGs were not refreshed.", file=sys.stderr)
		return result.returncode
	out_dir = os.path.join(repo_root, "output_smoke")
	print(f"Generated: {os.path.join(out_dir, 'methanol_A_mask.svg')}")
	print(f"Generated: {os.path.join(out_dir, 'methanol_B_clip.svg')}")
	return 0


#============================================
if __name__ == "__main__":
	raise SystemExit(main())
