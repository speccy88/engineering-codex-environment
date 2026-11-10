#!/usr/bin/env bash
# Native upstream Fritzing, isolated Qt state, CPU/offscreen rendering, no server.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="$ROOT/.local/sysroot"
binary="${FRITZING_BIN:-$prefix/usr/bin/fritzing.real}"
data="${FRITZING_DATA_DIR:-$prefix/usr/share/fritzing}"
parts="${FRITZING_PARTS_DIR:-$data/parts}"
[[ -x "$binary" ]] || { echo 'Missing Fritzing engine; run bash setup/install-fritzing.sh once during setup.' >&2; exit 127; }
[[ -d "$parts/core" ]] || { echo "Missing Fritzing parts: $parts" >&2; exit 1; }
[[ $# -gt 0 ]] || { echo 'Usage: run-fritzing.sh --version | --svg DIRECTORY | --gerber DIRECTORY | FILE.fzz' >&2; exit 2; }
mkdir -p "$ROOT/.local/fritzing-runs"
run_dir=$(mktemp -d "$ROOT/.local/fritzing-runs/run.XXXXXXXX")
child=''
cleanup() { [[ -z "$child" ]] || kill "$child" 2>/dev/null || true; rm -rf -- "$run_dir"; }
trap cleanup EXIT
trap 'exit 130' INT TERM
mkdir -p "$run_dir/parts/svg" "$run_dir/config" "$run_dir/cache" "$run_dir/data" "$run_dir/runtime" "$run_dir/documents"
chmod 700 "$run_dir/runtime"
for entry in "$parts"/*; do
  name=${entry##*/}
  [[ "$name" == parts.db || "$name" == svg ]] && continue
  ln -s "$entry" "$run_dir/parts/$name"
done
for entry in "$parts/svg"/*; do ln -s "$entry" "$run_dir/parts/svg/${entry##*/}"; done
database="$parts/parts.db"
[[ -f "$database" ]] || database="$data/parts.db.distrib"
[[ -f "$database" ]] || { echo "Missing Fritzing parts database in $parts or $data" >&2; exit 1; }
cp -- "$database" "$run_dir/parts/parts.db"
printf 'XDG_DOCUMENTS_DIR="%s"\n' "$run_dir/documents" > "$run_dir/config/user-dirs.dirs"
export XDG_CONFIG_HOME="$run_dir/config" XDG_CACHE_HOME="$run_dir/cache" XDG_DATA_HOME="$run_dir/data" XDG_RUNTIME_DIR="$run_dir/runtime"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" LIBGL_ALWAYS_SOFTWARE=1
export LD_LIBRARY_PATH="$prefix/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export QT_PLUGIN_PATH="$prefix/usr/lib/x86_64-linux-gnu/qt5/plugins${QT_PLUGIN_PATH:+:$QT_PLUGIN_PATH}"
python3 "$ROOT/scripts/fritzing-offline.py" "$binary" --folder "$data" --parts "$run_dir/parts" "$@" &
child=$!
status=0
wait "$child" || status=$?
child=''
exit "$status"
