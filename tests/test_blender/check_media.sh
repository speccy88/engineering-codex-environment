#!/usr/bin/env bash
# Real still-image transforms exercise both installed media executables.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
out=${1:-"$root/artifacts/blender"}
input="$out/assembly-preview.png"
[[ -s "$input" ]] || { echo "Run Blender acceptance first: $input missing" >&2; exit 66; }
magick "$input" -background white -alpha remove -resize 320x240 "$out/imagemagick-preview.jpg"
ffmpeg -v error -y -i "$input" -vf scale=320:240 -frames:v 1 -threads 1 "$out/ffmpeg-preview.png"
[[ $(magick identify -format '%wx%h' "$out/imagemagick-preview.jpg") == 320x240 ]]
[[ $(magick identify -format '%wx%h' "$out/ffmpeg-preview.png") == 320x240 ]]
/usr/bin/python3 - "$out" <<'PY'
import json
from pathlib import Path
import subprocess
import sys
out = Path(sys.argv[1]).resolve()
versions = {}
for name, command in {"ffmpeg": ["ffmpeg", "-version"], "imagemagick": ["magick", "-version"]}.items():
    proc = subprocess.run(command, check=True, capture_output=True, text=True)
    versions[name] = proc.stdout.splitlines()[0]
data = {"status": "passed", "versions": versions, "transforms": ["PNG to 320x240 JPEG with ImageMagick", "PNG resize to 320x240 with FFmpeg"], "outputs": [str(out / "imagemagick-preview.jpg"), str(out / "ffmpeg-preview.png")]}
(out / "media-result.json").write_text(json.dumps(data, indent=2) + "\n")
print(json.dumps(data, indent=2))
PY
