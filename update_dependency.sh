#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -File "$ROOT/src/scripts/update_dependencies.ps1" "$@"
elif command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ROOT/src/scripts/update_dependencies.ps1" "$@"
else
  echo "PowerShell 7 or Windows PowerShell is required for dependency updates." >&2
  exit 1
fi
