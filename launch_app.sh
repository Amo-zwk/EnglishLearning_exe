#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ -x "runtime/.venv/bin/python" ]; then
  runtime/.venv/bin/python scripts/launch_app.py
else
  echo "Runtime environment was not found. Please run install_environment.sh first."
  if command -v python3 >/dev/null 2>&1; then
    python3 scripts/launch_app.py
  else
    python scripts/launch_app.py
  fi
fi
