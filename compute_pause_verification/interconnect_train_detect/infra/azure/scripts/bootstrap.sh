#!/usr/bin/env bash
# Wait for SSH, install repo deps, verify GPU (+ optionally IB) on the single node.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/config.env" 2>/dev/null || source "$SCRIPT_DIR/config.env.example"
load_node_env

wait_ssh "$NODE_IP"

# Persistent outputs dir on the OS disk, symlinked from $REMOTE_DIR/outputs.
# Confirmed 2026-08-21 on the Italy North shared box: $REMOTE_DIR itself may
# sit on Azure's EPHEMERAL temp disk (/mnt — cheap to rebuild via sync.sh,
# but subject to loss with NO recovery, even mid-run, per
# /mnt/EPHEMERAL_DISK_DATALOSS_WARNING.txt on that box). Code+venv there is
# fine (rebuildable); actual run outputs are not, so they go on the OS disk
# instead. Same pattern shortcut_forensics uses
# (scfx_ly_persistent_outputs) — matching it for consistency.
PERSISTENT_OUTPUTS_DIR="/home/${SSH_USER}/$(basename "$REMOTE_DIR")_outputs"

ssh_node PERSISTENT_OUTPUTS_DIR="$PERSISTENT_OUTPUTS_DIR" bash -s <<EOS
set -euo pipefail
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv git rsync ibverbs-utils || true
nvidia-smi || { echo "no GPU"; exit 1; }
echo "GPUs=\$(nvidia-smi -L | wc -l)"
# InfiniBand check is non-fatal: the Ubuntu-HPC image should have it, but this experiment
# doesn't need cross-node fabric, so don't hard-fail bootstrap over its absence.
if ls /sys/class/infiniband >/dev/null 2>&1; then
  echo "IB devices: \$(ls /sys/class/infiniband)"
  command -v ibv_devinfo >/dev/null 2>&1 && ibv_devinfo 2>/dev/null | head -20
else
  echo "no /sys/class/infiniband (non-fatal — single-node run doesn't need it)"
fi
mkdir -p $REMOTE_DIR
python3 -m venv $REMOTE_DIR/.venv

mkdir -p "\$PERSISTENT_OUTPUTS_DIR"
if [[ -d "$REMOTE_DIR/outputs" && ! -L "$REMOTE_DIR/outputs" ]]; then
  # pre-existing real directory (not yet a symlink) — move its contents over first, don't discard them
  shopt -s dotglob nullglob
  mv "$REMOTE_DIR"/outputs/* "\$PERSISTENT_OUTPUTS_DIR"/ 2>/dev/null || true
  rmdir "$REMOTE_DIR/outputs" 2>/dev/null || true
fi
[[ -L "$REMOTE_DIR/outputs" ]] || ln -s "\$PERSISTENT_OUTPUTS_DIR" "$REMOTE_DIR/outputs"
echo "outputs -> \$(readlink -f "$REMOTE_DIR/outputs")"

echo "bootstrap ok \$(hostname) GPUs=\$(nvidia-smi -L | wc -l)"
EOS
echo "[bootstrap] node ready — next: ./infra/azure/scripts/sync.sh"
