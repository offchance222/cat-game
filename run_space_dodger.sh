#!/usr/bin/env bash
# Launcher for Space Dodger: prefer built executable, otherwise run from venv, otherwise system python
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [ -x "$SCRIPT_DIR/dist/space_dodger" ]; then
  exec "$SCRIPT_DIR/dist/space_dodger"
fi
if [ -d "$SCRIPT_DIR/venv" ]; then
  # Activate venv and exec python so the process replaces the script
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/venv/bin/activate"
  exec python "$SCRIPT_DIR/game.py"
fi
exec python3 "$SCRIPT_DIR/game.py"
