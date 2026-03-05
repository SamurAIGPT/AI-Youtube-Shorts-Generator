#!/usr/bin/env bash
# ─────────────────────────────────────────
#  1Key Website – Local Dev Server
# ─────────────────────────────────────────
PORT=${1:-3000}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer npx serve, fall back to Python
if command -v npx &>/dev/null; then
  echo "Starting with Node serve on http://localhost:$PORT"
  npx serve "$SCRIPT_DIR" -l "$PORT"
elif command -v python3 &>/dev/null; then
  echo "Starting with Python on http://localhost:$PORT"
  python3 -m http.server "$PORT" --directory "$SCRIPT_DIR"
else
  echo "ERROR: Neither Node.js nor Python3 found. Please install one."
  exit 1
fi
