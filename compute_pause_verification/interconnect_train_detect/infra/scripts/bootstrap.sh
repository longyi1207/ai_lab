#!/usr/bin/env bash
# Wait for SSH, install repo deps, EFA/NCCL env on both nodes.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/config.env" 2>/dev/null || source "$SCRIPT_DIR/config.env.example"
load_cluster_env

wait_ssh "$NODE0_IP"
wait_ssh "$NODE1_IP"

bootstrap_one() {
  local rank="$1"
  ssh_node "$rank" bash -s <<EOS
set -euo pipefail
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv git rsync ibverbs-utils || true
nvidia-smi || { echo "no GPU"; exit 1; }
fi_info -p efa -t FI_EP_RDM 2>/dev/null | head -5 || echo "no EFA (ok for g5)"
mkdir -p $REMOTE_DIR
python3 -m venv $REMOTE_DIR/.venv
echo "bootstrap ok \$(hostname) GPUs=\$(nvidia-smi -L | wc -l)"
EOS
}

bootstrap_one 0
bootstrap_one 1
echo "[bootstrap] both nodes ready — next: ./infra/scripts/sync.sh"
