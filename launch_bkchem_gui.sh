#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/opt/homebrew/opt/python@3.12/bin/python3.12"

if [[ ! -x "${PYTHON_BIN}" ]]; then
	echo "Python 3.12 not found at ${PYTHON_BIN}" >&2
	exit 1
fi

export PYTHONPATH="${ROOT_DIR}/packages/bkchem:${ROOT_DIR}/packages/bkchem/bkchem:${ROOT_DIR}/packages/oasa:${ROOT_DIR}/packages/oasa/oasa:${ROOT_DIR}:${PYTHONPATH:-}"

exec "${PYTHON_BIN}" -m bkchem.cli "$@"
