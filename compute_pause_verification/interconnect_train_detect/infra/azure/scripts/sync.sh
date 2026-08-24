#!/usr/bin/env bash
# rsync project → the Azure node.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_node_env

RSYNC_SSH="ssh -p $SSH_PORT -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$ACTIVE_DIR/known_hosts -i $SSH_KEY"

echo "[sync] → $NODE_IP:$SSH_PORT"
ssh_node "mkdir -p $REMOTE_DIR"
# infra/terraform/.terraform + infra/azure/terraform/.terraform (downloaded provider
# plugins, hundreds of MB, gitignored, and IRRELEVANT on the remote box — nothing there
# ever runs terraform) are the ones that actually bit us: a pre-existing local .terraform/
# from AWS setup wasn't excluded and got rsynced across the network at ~270KB/s before
# being caught. Excluded explicitly now, not just relying on .gitignore (rsync doesn't
# read it).
rsync -az --delete -e "$RSYNC_SSH" \
  --exclude '.venv' --exclude 'outputs' --exclude 'infra/.active' --exclude 'infra/azure/.active' \
  --exclude '.pytest_cache' --exclude '__pycache__' --exclude '.git' \
  --exclude '.terraform' --exclude '.terraform.lock.hcl' --exclude '*.tfstate*' --exclude 'terraform.tfvars' \
  "$PROJECT_ROOT/" "${SSH_USER}@${NODE_IP}:${REMOTE_DIR}/"
ssh_node "source $REMOTE_DIR/.venv/bin/activate && pip install -q -U pip && pip install -q -r $REMOTE_DIR/requirements.txt"
echo "[sync] done"
