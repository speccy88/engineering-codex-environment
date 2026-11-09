#!/usr/bin/env bash
# Prepare/refresh the published Debian 13 workbench; no service is started.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/workspace/.cache/uv}"
export UV_SYSTEM_CERTS=true
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
mkdir -p .local/downloads .local/sysroot .venvs "$UV_CACHE_DIR"
stage() { printf '\nStage: %s\n' "$1"; df -h "$ROOT"; }
stage 'Native prerequisites (retained in the published filesystem)'
for bin in /usr/bin/python3 /usr/bin/freecad /usr/bin/kicad-cli /usr/bin/blender /usr/bin/openscad; do
  if [[ ! -x "$bin" ]]; then
    echo "Missing native prerequisite $bin. See docs/cloud-environment.md for a full native rebuild." >&2
    exit 1
  fi
done
command -v uv >/dev/null
command -v java >/dev/null
command -v ffmpeg >/dev/null
command -v magick >/dev/null

fetch() {
  local url=$1 target=$2 digest=$3
  if [[ ! -f "$target" ]] || ! printf '%s  %s\n' "$digest" "$target" | sha256sum --check --status; then
    curl --fail --location --retry 2 --output "$target.part" "$url"
    printf '%s  %s\n' "$digest" "$target.part" | sha256sum --check --status
    mv "$target.part" "$target"
  fi
}
deb() {
  local name=$1 url=$2 sha=$3 sentinel=$4
  local filename="${url##*/}"
  local marker=".local/sysroot/.${name}.sha256"
  if [[ -e ".local/sysroot/$sentinel" && -f "$marker" ]] && [[ "$(cat "$marker")" == "$sha" ]]; then return; fi
  fetch "$url" ".local/downloads/$filename" "$sha"
  dpkg-deb --extract ".local/downloads/$filename" .local/sysroot
  printf '%s\n' "$sha" > "$marker"
  rm -- ".local/downloads/$filename"
}
stage 'Native simulation, full KiCad 3D library and headless X server (workspace prefix)'
while IFS=$'\t' read -r name url sha sentinel; do
  deb "$name" "$url" "$sha" "$sentinel"
done < <(python3 -c 'import json; files=["setup/native-extras.json","setup/pyspice-native.json"]; [print("\t".join(p[k] for k in ("name","url","sha256","sentinel"))) for f in files for p in json.load(open(f))["packages"]]')
python3 setup/configure_native.py
stage 'Isolated scientific and OCCT Python runtime'
python_bin="${WB_PYTHON312:-$(command -v python3)}"
"$python_bin" -c 'import sys; assert sys.version_info[:2] == (3,12), "Set WB_PYTHON312 to Python 3.12"'
[[ -x .venvs/engineering/bin/python ]] || uv venv --python "$python_bin" .venvs/engineering
uv pip sync --python .venvs/engineering/bin/python --require-hashes setup/requirements.lock
stage 'Isolated optional KiCad IPC client (requires a live KiCad IPC server to use)'
[[ -x .venvs/kicad-ipc/bin/python ]] || uv venv --python "$python_bin" .venvs/kicad-ipc
uv pip sync --python .venvs/kicad-ipc/bin/python --require-hashes setup/kicad-ipc.lock
stage 'Freerouting'
if [[ -f setup/freerouting.json ]]; then
  readarray -t routing < <("$python_bin" -c 'import json; d=json.load(open("setup/freerouting.json")); print(d["url"]); print(d["path"]); print(d["sha256"])')
  mkdir -p "$(dirname -- "${routing[1]}")"
  fetch "${routing[0]}" "${routing[1]}" "${routing[2]}"
else
  echo 'Missing locked Freerouting metadata: setup/freerouting.json' >&2
  exit 1
fi
stage 'Readiness'
bash setup/verify.sh --quick
