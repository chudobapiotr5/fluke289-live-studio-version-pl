#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Najpierw wykonaj instalację opisaną w README.md.' >&2
  exit 1
fi
if ! .venv/bin/python -c 'import serial' 2>/dev/null; then
  echo 'Brakuje biblioteki pyserial. W tym folderze wykonaj:' >&2
  echo '  .venv/bin/python -m pip install .' >&2
  exit 1
fi
exec .venv/bin/python -m fluke289 "$@"
