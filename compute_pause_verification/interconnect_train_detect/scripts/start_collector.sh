#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-outputs/manual}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8765}"
mkdir -p "$OUT"
exec python -m src.monitor.collector --host "$HOST" --port "$PORT" --out "$OUT"
