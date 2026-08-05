#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_cluster_env

echo "JOB_ID=${JOB_ID:-?} LAUNCHED_AT=${LAUNCHED_AT:-?}"
echo "node0=$NODE0_IP ($INSTANCE_ID_0)  node1=$NODE1_IP ($INSTANCE_ID_1)"
echo "master=$MASTER_ADDR collector=$COLLECTOR_URL"
for rank in 0 1; do
  echo "--- node$rank nvidia-smi ---"
  ssh_node "$rank" "nvidia-smi -L; uptime" || echo "(ssh failed)"
done
