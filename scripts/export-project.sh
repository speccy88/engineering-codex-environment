#!/usr/bin/env bash
# Package a project without altering its editable source files.
set -euo pipefail
if [[ $# != 2 ]]; then echo 'Usage: export-project.sh PROJECT_DIRECTORY OUTPUT.zip' >&2; exit 2; fi
exec python3 - "$@" <<'PY'
from pathlib import Path
import sys, zipfile
source, target = (Path(x).resolve() for x in sys.argv[1:])
if not source.is_dir() or target.exists() or target.is_relative_to(source):
    raise SystemExit('Source must be a directory; output must be a new ZIP outside it.')
excluded = {'.git', '.venvs', 'node_modules', '__pycache__', '.pytest_cache', '.local', '.cache'}
files = [p for p in source.rglob('*') if p.is_file() and not p.is_symlink()
         and not any(x in excluded for x in p.relative_to(source).parts)
         and p.name != '.env' and not p.name.startswith('.env.')]
if not files:
    raise SystemExit('No project files to export')
target.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(files):
        archive.write(p, Path(source.name) / p.relative_to(source))
print(f'{target}: {len(files)} files; inspect contents before sharing.')
PY
