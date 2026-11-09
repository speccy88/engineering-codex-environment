#!/usr/bin/env bash
# Run a script inside Blender's own Python runtime. No desktop or services needed.
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 script.py [script arguments...]" >&2
  exit 64
fi
script=$1
shift
[[ -f "$script" ]] || { echo "Missing Blender Python script: $script" >&2; exit 66; }
export LIBGL_ALWAYS_SOFTWARE=${LIBGL_ALWAYS_SOFTWARE:-1}
unset PYTHONHOME PYTHONPATH
exec /usr/bin/blender --background --factory-startup \
  --threads "${ENGINEERING_THREADS:-2}" --python-exit-code 1 \
  --python "$script" -- "$@"
