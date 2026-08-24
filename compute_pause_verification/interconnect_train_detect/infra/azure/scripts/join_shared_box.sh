#!/usr/bin/env bash
# Join an ALREADY-EXISTING shared box instead of creating a new one — for the
# 2026-08-21..23 Italy North reservation (1 node, 8x NDm A100 v4, Azure ML
# Compute Instance), shared 3 ways with shortcut_forensics and
# theory-of-mind/empathy via CUDA_VISIBLE_DEVICES. Do NOT run launch.sh for
# this window — that provisions a NEW VM via this project's own Terraform,
# which is the wrong path here (see docs/REDTEAM.md "Shared-box operation").
# shortcut_forensics' infra/launch_aml.sh creates the one shared compute
# instance; this script just writes the connection info in the format
# bootstrap.sh/sync.sh/run.sh/pull.sh/status.sh/ssh.sh already expect
# (infra/azure/.active/node.env), so the rest of this project's tooling
# works unmodified against a shared box instead of a dedicated one.
#
# Usage (explicit):
#   ./join_shared_box.sh <ssh_host> <ssh_port> <ssh_user> <ssh_key_path>
# Usage (read shortcut_forensics' own launch_aml.sh output directly):
#   ./join_shared_box.sh --from-env /path/to/shortcut_forensics/infra/.active/<run_id>.env
#
# After this: ./bootstrap.sh && ./sync.sh && \
#   ICTD_GPU_INDICES=3,4,5 ./run.sh configs/azure_redteam_single_node.yaml --module src.run_redteam
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ACTIVE_DIR="$SCRIPT_DIR/../.active"
mkdir -p "$ACTIVE_DIR"

if [[ "${1:-}" == "--from-env" ]]; then
  SRC_ENV="${2:?usage: join_shared_box.sh --from-env <path>}"
  [[ -f "$SRC_ENV" ]] || { echo "no such file: $SRC_ENV" >&2; exit 1; }
  # shellcheck disable=SC1090
  source "$SRC_ENV"
  # shortcut_forensics' launch_aml.sh writes SSH_HOST/SSH_PORT/SSH_USER/SSH_KEY_PATH
  : "${SSH_HOST:?missing SSH_HOST in $SRC_ENV}" "${SSH_PORT:?}" "${SSH_USER:?}" "${SSH_KEY_PATH:?}"
  HOST="$SSH_HOST"; PORT="$SSH_PORT"; USER_="$SSH_USER"; KEY="$SSH_KEY_PATH"
else
  HOST="${1:?usage: join_shared_box.sh <host> <port> <user> <key_path>  (or --from-env <path>)}"
  PORT="${2:?missing ssh port}"
  USER_="${3:?missing ssh user}"
  KEY="${4:?missing ssh private key path}"
fi

[[ -f "$KEY" ]] || { echo "no SSH private key at $KEY" >&2; exit 1; }

# /mnt, not /home — on the Italy North box the root disk (/, ~119GB) is
# shared across all three projects and filled up fast (confirmed 2026-08-21:
# 100% full, pip install failing with ENOSPC). /mnt is a much larger,
# separately-backed disk (~2.8TB) with room to spare. Override via a 5th
# arg if this box's layout differs.
REMOTE_DIR="${5:-/mnt/interconnect_train_detect}"
JOB_ID="ictd-shared-$(date -u +%Y%m%d-%H%M%S)"
ENV_FILE="$ACTIVE_DIR/node.env"
cat >"$ENV_FILE" <<EOF
JOB_ID=$JOB_ID
AZURE_REGION=italynorth
SSH_USER=$USER_
SSH_KEY=$KEY
SSH_PORT=$PORT
REMOTE_DIR=$REMOTE_DIR
VM_ID=shared-aml-compute-instance
VM_SIZE=Standard_ND96amsr_A100_v4
NODE_IP=$HOST
NODE_PRIV_IP=$HOST
COLLECTOR_URL=http://127.0.0.1:8766
LAUNCHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
ln -sfn "$ENV_FILE" "$ACTIVE_DIR/latest.env"

echo "[join_shared_box] wrote $ENV_FILE"
echo "[join_shared_box] host=$HOST port=$PORT user=$USER_ remote_dir=$REMOTE_DIR"
echo "[join_shared_box] NEXT: ./bootstrap.sh && ./sync.sh"
echo "[join_shared_box] REMINDER: this is a SHARED box — bootstrap.sh's apt-get is idempotent/safe"
echo "                   alongside other projects' bootstraps, but confirm your GPU slice"
echo "                   (ICTD_GPU_INDICES / configs/azure_redteam_single_node.yaml's"
echo "                   telemetry.gpu_indices) before running anything that touches GPUs."
