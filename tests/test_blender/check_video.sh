#!/usr/bin/env bash
# Encode the actual Blender frame sequence, probe it and compare decoded poses.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
out=${1:-"$root/artifacts/animation"}
[[ -s "$out/render-result.json" ]] || { echo 'Run animation_acceptance.py first' >&2; exit 66; }
ffmpeg -v error -y -framerate 8 -start_number 1 -i "$out/frames/frame_%04d.png" \
  -frames:v 8 -c:v libx264 -threads 2 -pix_fmt yuv420p -movflags +faststart "$out/animation.mp4"
ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,nb_read_frames,duration \
  -show_entries format=duration -of json "$out/animation.mp4" > "$out/ffprobe.json"
ffmpeg -v error -y -i "$out/animation.mp4" \
  -vf 'select=eq(n\,0)+eq(n\,7)' -vsync 0 -frames:v 2 -threads 1 "$out/decoded_%02d.png"
/usr/bin/python3 - "$out" <<'PY'
import json
from pathlib import Path
import statistics
import subprocess
import sys

out = Path(sys.argv[1]).resolve()
render = json.loads((out / 'render-result.json').read_text())
assert render['status'] == 'passed' and render['frame_count'] == 8
probe = json.loads((out / 'ffprobe.json').read_text())
stream = probe['streams'][0]
assert stream['codec_name'] == 'h264', stream
assert (stream['width'], stream['height']) == (128, 128), stream
assert int(stream['nb_read_frames']) == 8, stream
numerator, denominator = map(int, stream['r_frame_rate'].split('/'))
assert abs(numerator / denominator - 8) < 1e-9
duration = float(probe['format']['duration'])
assert abs(duration - 1.0) < 0.02, duration
checks = []
for filename in ['decoded_01.png', 'decoded_02.png']:
    image = out / filename
    process = subprocess.run(['magick', str(image), '-colorspace', 'gray', '-depth', '8', 'gray:-'], check=True, capture_output=True)
    pixels = list(process.stdout)
    assert len(pixels) == 128 * 128
    deviation = statistics.pstdev(pixels)
    assert deviation > 5, deviation
    checks.append((pixels, deviation))
difference = statistics.fmean(abs(a - b) for a, b in zip(checks[0][0], checks[1][0]))
assert difference > 2, difference
result = {
    'status': 'passed', 'codec': 'h264', 'pixel_format': 'yuv420p',
    'frame_count': 8, 'fps': 8, 'duration_seconds': duration, 'resolution': [128, 128],
    'decoded_frame_stddev_8bit': [item[1] for item in checks],
    'decoded_first_last_mean_absolute_difference_8bit': difference,
    'native_animation_reopen': render['native_reopen_with_keyframes'],
    'ffmpeg': subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0],
    'outputs': [str(out / 'animation.mp4'), str(out / 'animation.blend'), str(out / 'frames')],
}
(out / 'video-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
PY
