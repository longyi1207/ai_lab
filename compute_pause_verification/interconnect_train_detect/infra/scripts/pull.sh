#!/usr/bin/env bash
# Pull traces/report/dashboard from node0.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_cluster_env

LOCAL_OUT="${1:-$PROJECT_ROOT/outputs/aws_$(date -u +%Y%m%d_%H%M%S)}"
mkdir -p "$LOCAL_OUT"

# shellcheck disable=SC2046
rsync -az -e "ssh $(ssh_opts | xargs echo)" \
  "${SSH_USER}@${NODE0_IP}:${REMOTE_DIR}/outputs/" "$LOCAL_OUT/"

echo "[pull] → $LOCAL_OUT"
if [[ -f "$LOCAL_OUT/cluster_baseline/dashboard.html" ]]; then
  echo "[pull] open $LOCAL_OUT/cluster_baseline/dashboard.html"
elif [[ -f "$LOCAL_OUT/dashboard.html" ]]; then
  echo "[pull] open $LOCAL_OUT/dashboard.html"
fi
ls -la "$LOCAL_OUT" | head -20
