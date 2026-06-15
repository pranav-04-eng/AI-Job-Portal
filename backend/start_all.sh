#!/usr/bin/env bash
# Launch the whole backend: 4 services behind 1 gateway.
# Each service runs on its own port; the gateway (:8000) is what the frontend hits.
#
#   ./start_all.sh
#
# Ctrl-C stops everything.
set -euo pipefail

cd "$(dirname "$0")"                 # backend/
export PYTHONPATH="$PWD"             # so `from common...` and `services...` resolve

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then PY="python3"; fi

pids=()
cleanup() { echo; echo "Stopping services..."; kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

start() {  # name  module:app  port
  echo "  -> $1 on :$3"
  "$PY" -m uvicorn "$2" --port "$3" --reload &
  pids+=($!)
}

echo "Starting backend services..."
start auth-service      services.auth.main:app       9001
start jobs-service      services.jobs.main:app       9002
start screening-service services.screening.main:app  9003
start interview-service services.interview.main:app  9004
start gateway           gateway:app                  8000

echo
echo "Gateway ready at http://localhost:8000  (frontend talks to this)"
echo "Press Ctrl-C to stop all services."
wait
