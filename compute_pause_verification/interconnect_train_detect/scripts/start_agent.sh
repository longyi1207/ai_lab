#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
COLLECTOR="${COLLECTOR:-http://127.0.0.1:8765}"
NODE="${NODE:-$(hostname)}"
BACKENDS="${BACKENDS:-ib,proc_net,nvml}"
IFACE="${IFACE:-}"
IB_DEVICE="${IB_DEVICE:-}"
POLL_HZ="${POLL_HZ:-20}"

args=(--collector "$COLLECTOR" --node "$NODE" --backends "$BACKENDS" --poll-hz "$POLL_HZ")
[[ -n "$IFACE" ]] && args+=(--iface "$IFACE")
[[ -n "$IB_DEVICE" ]] && args+=(--ib-device "$IB_DEVICE")
exec python -m src.monitor.agent "${args[@]}"
