#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PY_ROOT}"

# Run pyflakes on core app files and capture output
PYFLAKES_OUT="${SCRIPT_DIR}/pyflakes.txt"
find "${PY_ROOT}/bkchem" \
	-type d \( -name __pycache__ -o -name plugins -o -name oasa \) -prune -o \
	-type f -name "*.py" -print0 \
	| xargs -0 pyflakes > "${PYFLAKES_OUT}" 2>&1 || true

RESULT=$(wc -l < "${PYFLAKES_OUT}")

# Success if no errors were found
if [ "${RESULT}" -eq 0 ]; then
    echo "No errors found!!!"
    exit 0
fi

	echo "First 15 errors"
	head -n 15 "${PYFLAKES_OUT}"
	echo ""

	echo "Last 15 errors"
	tail -n 15 "${PYFLAKES_OUT}"
	echo ""

echo "Found ${RESULT} pyflakes errors"

# Fail if any errors were found
exit 1
