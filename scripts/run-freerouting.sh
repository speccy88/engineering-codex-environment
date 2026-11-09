#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$ROOT/.local/xdg/cache}"
mkdir -p "$XDG_CACHE_HOME"
JAR="${FREEROUTING_JAR:-$ROOT/.local/share/freerouting/freerouting-2.1.0.jar}"
[[ -f "$JAR" ]] || { echo "Missing $JAR; run setup/install.sh" >&2; exit 1; }
exec java -Djava.awt.headless=true -Duser.home="$ROOT/.local/share/freerouting" -Xmx2g -jar "$JAR" -da --gui.enabled=false "$@"
