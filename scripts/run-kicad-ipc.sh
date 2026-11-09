#!/usr/bin/env bash
# KiCad 9+ official IPC CLIENT. Requires a separately running IPC-enabled KiCad GUI.
# This environment is intentionally separate from the legacy pcbnew SWIG API.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$repo_dir/.venvs/kicad-ipc/bin/python" ]]; then
    echo 'KiCad IPC client runtime missing; run setup/install.sh first.' >&2
    exit 1
fi
unset PYTHONHOME PYTHONPATH
exec "$repo_dir/.venvs/kicad-ipc/bin/python" "$@"
