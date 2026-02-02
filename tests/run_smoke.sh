#!/usr/bin/env bash

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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

TESTS_TOTAL=4
TEST_INDEX=1
FAILURES=0

run_step() {
	local name status
	name="$1"
	shift
	echo "${TEST_INDEX} of ${TESTS_TOTAL}) ${name}"
	"$@"
	status=$?
	if [ "${status}" -ne 0 ]; then
		echo "FAILED: ${name}" >&2
		FAILURES=$((FAILURES + 1))
	fi
	TEST_INDEX=$((TEST_INDEX + 1))
	return 0
}

run_oasa_smoke() {
	TMP_OUTPUT="${TMPDIR:-/tmp}/oasa_smoke.png"
	python3 tests/oasa_smoke_png.py -o "${TMP_OUTPUT}"
	if [ ! -s "${TMP_OUTPUT}" ]; then
		echo "OASA smoke test did not produce output: ${TMP_OUTPUT}" >&2
		return 1
	fi
	return 0
}

run_step "BKChem GUI smoke test" run_filtered python3 tests/bkchem_gui_smoke.py
run_step "BKChem batch examples" run_filtered python3 tests/bkchem_batch_examples.py
run_step "OASA smoke render (PNG)" run_oasa_smoke
run_step "OASA smoke render (SVG/PDF/PNG)" python3 tests/oasa_smoke_formats.py

if [ "${FAILURES}" -ne 0 ]; then
	echo "Smoke tests completed with ${FAILURES} failure(s)." >&2
	exit 1
fi

echo "Smoke tests completed successfully."
