#!/usr/bin/env bash
# Install the Debian 13 Fritzing engine and parts in the workspace, without root.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ $(uname -m) == x86_64 ]] || { echo 'Fritzing lock targets Debian 13 amd64.' >&2; exit 1; }
for tool in curl dpkg-deb sha256sum python3; do command -v "$tool" >/dev/null; done
# Debian workbench prerequisites: seccomp enforces offline execution; QtSvg is
# supplied by the existing FreeCAD/PySide2 runtime and produces PNG previews.
/usr/bin/python3 -c 'import ctypes; ctypes.CDLL("libseccomp.so.2"); from PySide2 import QtSvg'
mkdir -p .local/downloads .local/sysroot
while IFS=$'\t' read -r name url digest sentinel; do
  marker=".local/sysroot/.fritzing-${name}.sha256"
  if [[ -e ".local/sysroot/$sentinel" && -f "$marker" ]] && [[ $(cat "$marker") == "$digest" ]]; then continue; fi
  filename=".local/downloads/${url##*/}"
  if [[ ! -f "$filename" ]] || ! printf '%s  %s\n' "$digest" "$filename" | sha256sum --check --status; then
    curl --fail --location --retry 2 --connect-timeout 20 --max-time 180 --output "$filename.part" "$url"
    printf '%s  %s\n' "$digest" "$filename.part" | sha256sum --check --status
    mv -- "$filename.part" "$filename"
  fi
  dpkg-deb --extract "$filename" .local/sysroot
  printf '%s\n' "$digest" > "$marker"
  rm -- "$filename"
done < <(python3 -c 'import json; [print("\t".join(p[k] for k in ("name","url","sha256","sentinel"))) for p in json.load(open("setup/fritzing-native.json"))["packages"]]')
# The Debian launcher normally creates this database under the user's HOME.
# Keep our copy alongside the retained parts; each invocation copies it privately.
cp .local/sysroot/usr/share/fritzing/parts.db.distrib .local/sysroot/usr/share/fritzing/parts/parts.db
missing=$(LD_LIBRARY_PATH="$ROOT/.local/sysroot/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ldd .local/sysroot/usr/bin/fritzing.real | awk '/not found/ { print }')
[[ -z "$missing" ]] || { printf 'Missing native prerequisites:\n%s\n' "$missing" >&2; exit 1; }
bash scripts/run-fritzing.sh --version
