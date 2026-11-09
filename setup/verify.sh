#!/usr/bin/env bash
# --quick checks runtime wiring; --full performs real engineering acceptance.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2}
case "${1:---quick}" in
  --quick) exec python3 setup/verify.py --quick ;;
  --full) exec python3 setup/verify.py --full ;;
  *) echo 'Usage: setup/verify.sh [--quick|--full]' >&2; exit 2 ;;
esac
