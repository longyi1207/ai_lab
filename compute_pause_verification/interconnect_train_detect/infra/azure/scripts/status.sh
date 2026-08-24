#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_node_env

echo "JOB_ID=${JOB_ID:-?} LAUNCHED_AT=${LAUNCHED_AT:-?}"
echo "node=$NODE_IP ($VM_ID) size=${VM_SIZE:-?}"
echo "collector=${COLLECTOR_URL:-?}"
echo "--- nvidia-smi ---"
ssh_node "nvidia-smi -L; uptime" || echo "(ssh failed)"
