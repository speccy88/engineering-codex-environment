#!/usr/bin/env bash
# OpenSCAD CSG/STL exports need no desktop. Override platform if a GUI is desired.
set -euo pipefail
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
exec openscad "$@"
