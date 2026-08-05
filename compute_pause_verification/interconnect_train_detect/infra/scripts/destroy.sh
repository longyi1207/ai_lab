#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
source "$SCRIPT_DIR/lib.sh"
load_cluster_env

echo "[destroy] terminating terraform stack (2× GPU)…"
cd "$TF_DIR"
terraform destroy -auto-approve
rm -f "$ACTIVE_DIR/cluster.env" "$ACTIVE_DIR/latest.env"
echo "[destroy] done"
