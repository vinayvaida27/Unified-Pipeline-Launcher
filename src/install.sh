#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if command -v python3 >/dev/null 2>&1; then PYTHON=python3
  elif command -v python >/dev/null 2>&1; then PYTHON=python
  else
    echo "Python 3 is required. Install it, then run install.sh again." >&2
    exit 1
  fi
fi

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$ROOT/requirements.txt"
while IFS= read -r requirements; do
  "$PYTHON" -m pip install -r "$requirements"
done < <(find "$ROOT/../apps" -mindepth 2 -maxdepth 2 -type f -name requirements.txt \
  ! -path '*/app_template/*' | sort)
echo "Launcher and application dependencies installed."
