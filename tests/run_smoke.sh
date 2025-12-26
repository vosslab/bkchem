#!/usr/bin/env bash
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"

run_filtered() {
	local output status
	output="$("$@" 2>&1)"
	status=$?
	if [ -n "${output}" ]; then
		echo "${output}" | sed -E '/^Could not load module /d'
	fi
	return "${status}"
}

echo "Running BKChem smoke tests..."
run_filtered python3 tests/run_bkchem_gui_smoke.py
run_filtered python3 tests/run_bkchem_batch_examples.py

echo "Running OASA smoke test..."
TMP_OUTPUT="${TMPDIR:-/tmp}/oasa_smoke.png"
python3 tests/oasa_smoke_png.py -o "${TMP_OUTPUT}"
if [ ! -s "${TMP_OUTPUT}" ]; then
	echo "OASA smoke test did not produce output: ${TMP_OUTPUT}" >&2
	exit 1
fi
