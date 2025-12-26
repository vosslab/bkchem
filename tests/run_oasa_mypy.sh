#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)

mypy --config-file "${ROOT_DIR}/tests/oasa_mypy.ini" \
	"${ROOT_DIR}/packages/oasa/oasa" \
	"${ROOT_DIR}"/tests/oasa_*.py
