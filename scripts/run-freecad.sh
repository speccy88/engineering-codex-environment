#!/usr/bin/env bash
# FreeCAD's Debian bindings require Debian Python, not the scientific venv.
set -euo pipefail
gui=0
if [[ ${1:-} == --gui ]]; then gui=1; shift; fi
if [[ $# -lt 1 ]]; then
  echo 'Usage: run-freecad.sh [--gui] script.py [arguments...]' >&2
  exit 2
fi
export QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-offscreen}
export LIBGL_ALWAYS_SOFTWARE=${LIBGL_ALWAYS_SOFTWARE:-1}
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-$repo_root/.local/xdg/cache}
export XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-$repo_root/.local/xdg/config}
export XDG_DATA_HOME=${XDG_DATA_HOME:-$repo_root/.local/xdg/share}
mkdir -p "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
if [[ -z ${XDG_RUNTIME_DIR:-} ]]; then
  export XDG_RUNTIME_DIR="$repo_root/.local/xdg/runtime"
  mkdir -p "$XDG_RUNTIME_DIR"
  chmod 700 "$XDG_RUNTIME_DIR"
fi
unset PYTHONHOME
export PYTHONPATH="/usr/lib/freecad/lib:/usr/share/freecad/Mod:/usr/share/freecad/Ext"
export WB_FREECAD_GUI=$gui
export PATH="$repo_root/.local/sysroot/usr/bin:$PATH"
launcher=()
if [[ $gui == 1 ]]; then
  export QT_QPA_PLATFORM=xcb
  if [[ -z ${DISPLAY:-} ]]; then
    launcher=(xvfb-run -a -s '-screen 0 1280x1024x24 -nolisten tcp')
  fi
fi
exec "${launcher[@]}" /usr/bin/python3 - "$@" <<'PY'
import os
import runpy
import sys
from pathlib import Path
import FreeCAD as App
for module_path in Path('/usr/share/freecad/Mod').iterdir():
    if module_path.is_dir():
        sys.path.append(str(module_path))
if os.environ['WB_FREECAD_GUI'] == '1':
    from PySide2 import QtWidgets
    qt_application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    import FreeCADGui as Gui
    Gui.showMainWindow()
    Gui.getMainWindow().hide()
    App.ParamGet('User parameter:BaseApp/Preferences/Document').SetBool('SaveThumbnail', False)
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
PY
