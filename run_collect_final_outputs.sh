#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use the repo's venv Python to avoid global/user site-packages surprises.
"${SCRIPT_DIR}/.venv/Scripts/python.exe" "${SCRIPT_DIR}/collect_final_outputs.py"

