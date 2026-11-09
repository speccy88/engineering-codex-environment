#!/usr/bin/env bash
# Native ngspice is deliberately independent of the CAD Python environments.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v ngspice >/dev/null 2>&1; then
  exec ngspice "$@"
elif [[ -x "$root/.local/sysroot/usr/bin/ngspice" ]]; then
  export LD_LIBRARY_PATH="$root/.local/sysroot/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export SPICE_LIB_DIR="$root/.local/ngspice"
  exec "$root/.local/sysroot/usr/bin/ngspice" "$@"
else
  printf '%s\n' 'ngspice is unavailable; run setup/install.sh (see docs/toolchain.md).' >&2
  exit 127
fi
