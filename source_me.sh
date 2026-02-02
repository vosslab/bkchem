# source_me.sh - Set up environment for testing and development
#
# This script is for TESTING AND DEVELOPMENT ONLY, not for installation.
# It configures PYTHONPATH so you can run tests and scripts that import
# from packages/oasa and packages/bkchem.
#
# Usage:
#   source source_me.sh
#   . source_me.sh

# Determine repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Add packages to PYTHONPATH
export PYTHONPATH="${REPO_ROOT}/packages/oasa:${REPO_ROOT}/packages/bkchem:${PYTHONPATH}"

# Use Python 3.12 (per AGENTS.md)
export PYTHON="/opt/homebrew/opt/python@3.12/bin/python3.12"

# Avoid .pyc files and enable unbuffered output
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

echo "Environment configured:"
echo "  REPO_ROOT=${REPO_ROOT}"
echo "  PYTHONPATH=${PYTHONPATH}"
echo "  PYTHON=${PYTHON}"
echo ""
echo "You can now run:"
echo "  \$PYTHON -c 'from oasa import haworth; print(haworth)'"
echo "  \$PYTHON packages/oasa/oasa/selftest_sheet.py --format png"
