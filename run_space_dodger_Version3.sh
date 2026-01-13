#!/usr/bin/env bash
# Launcher script for Space Dodger
# - If a built executable exists at dist/space_dodger, run it.
# - Otherwise activate venv (if present) and run python game.py from the project dir.
set -e

# Determine script directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer the built executable if available
if [ -x "$SCRIPT_DIR/dist/space_dodger" ]; then
  exec "$SCRIPT_DIR/dist/space_dodger"
fi

# Otherwise run from source using venv if available
if [ -d "$SCRIPT_DIR/venv" ]; then
  # Activate venv in current shell and run
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/venv/bin/activate"
  exec python "$SCRIPT_DIR/game.py"
else
  # No venv: try system python
  exec python3 "$SCRIPT_DIR/game.py"
fi