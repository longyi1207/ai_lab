#!/usr/bin/env bash
# rsync project → both nodes.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_cluster_env

RSYNC_SSH="ssh -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$ACTIVE_DIR/known_hosts -i $SSH_KEY"

sync_one() {
  local rank="$1"
  local ip
  [[ "$rank" == "0" ]] && ip="$NODE0_IP" || ip="$NODE1_IP"
  echo "[sync] → node$rank ($ip)"
  ssh_node "$rank" "mkdir -p $REMOTE_DIR"
  rsync -az --delete -e "$RSYNC_SSH" \
    --exclude '.venv' --exclude 'outputs' --exclude 'infra/.active' \
    --exclude '.pytest_cache' --exclude '__pycache__' --exclude '.git' \
    "$PROJECT_ROOT/" "${SSH_USER}@${ip}:${REMOTE_DIR}/"
  ssh_node "$rank" "source $REMOTE_DIR/.venv/bin/activate && pip install -q -U pip && pip install -q -r $REMOTE_DIR/requirements.txt"
}

sync_one 0
sync_one 1
echo "[sync] done"
