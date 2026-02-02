"""Smoke tests for reference output files."""

# Standard Library
import os

# Local repo modules
import conftest

ROOT_DIR = conftest.repo_root()
OUTPUT_DIR = os.path.join(ROOT_DIR, "docs", "reference_outputs")
REFERENCE_FILES = [
	os.path.join(OUTPUT_DIR, "haworth_reference.svg"),
	os.path.join(OUTPUT_DIR, "haworth_reference.png"),
	os.path.join(OUTPUT_DIR, "wavy_glucose_reference.svg"),
	os.path.join(OUTPUT_DIR, "wavy_glucose_reference.png"),
]


#============================================
def test_reference_outputs_exist():
	for path in REFERENCE_FILES:
		assert os.path.isfile(path)
		assert os.path.getsize(path) > 0
