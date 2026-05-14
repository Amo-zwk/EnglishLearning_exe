#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ -x "runtime/.venv/bin/python" ]; then
  runtime/.venv/bin/python scripts/configure_environment.py
else
  echo "Runtime environment was not found. Falling back to system Python."
  if command -v python3 >/dev/null 2>&1; then
    python3 scripts/configure_environment.py
  else
    python scripts/configure_environment.py
  fi
fi
