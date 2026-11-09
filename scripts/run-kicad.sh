#!/usr/bin/env bash
# KiCad 9 SWIG bindings are compiled for Debian's Python, not the CAD venv.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$ROOT/.local/xdg/config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$ROOT/.local/xdg/cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$ROOT/.local/xdg/data}"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME"
PROFILE="$XDG_CONFIG_HOME/kicad/9.0"
mkdir -p "$PROFILE"
for table in fp-lib-table sym-lib-table; do
  if [[ ! -f "$PROFILE/$table" ]]; then cp "/usr/share/kicad/template/$table" "$PROFILE/$table"; fi
done
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export KICAD9_SYMBOL_DIR="${KICAD9_SYMBOL_DIR:-/usr/share/kicad/symbols}"
export KICAD9_FOOTPRINT_DIR="${KICAD9_FOOTPRINT_DIR:-/usr/share/kicad/footprints}"
if [[ -d "$ROOT/.local/sysroot/usr/share/kicad/3dmodels" ]]; then
  export KICAD9_3DMODEL_DIR="${KICAD9_3DMODEL_DIR:-$ROOT/.local/sysroot/usr/share/kicad/3dmodels}"
else
  export KICAD9_3DMODEL_DIR="${KICAD9_3DMODEL_DIR:-/usr/share/kicad/3dmodels}"
fi
if [[ "${1:-}" == python ]]; then
  shift
  unset PYTHONHOME PYTHONPATH
  exec /usr/bin/python3 "$@"
fi
if [[ "${1:-}" == cli ]]; then shift; fi
exec /usr/bin/kicad-cli "$@"
