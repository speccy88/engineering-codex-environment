#!/usr/bin/env bash
# Isolated CPython 3.12 scientific, geometry, and file conversion runtime.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$repo_dir/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$repo_dir/.local/xdg/config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$repo_dir/.local/share}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$XDG_CACHE_HOME/matplotlib}"
export KICAD9_SYMBOL_DIR="${KICAD9_SYMBOL_DIR:-/usr/share/kicad/symbols}"
export KICAD_SYMBOL_DIR="${KICAD_SYMBOL_DIR:-$KICAD9_SYMBOL_DIR}"
export LD_LIBRARY_PATH="$repo_dir/.local/sysroot/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SPICE_LIB_DIR="$repo_dir/.local/ngspice"
mkdir -p "$MPLCONFIGDIR"
if [[ ! -x "$repo_dir/.venvs/engineering/bin/python" ]]; then
    echo 'Engineering runtime missing; run setup/install.sh first.' >&2
    exit 1
fi
exec "$repo_dir/.venvs/engineering/bin/python" "$@"
