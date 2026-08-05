#!/usr/bin/env bash
# Spot interruption watcher — dumps checkpoint marker + pulls logs before death.
# Run on each node via: nohup ./infra/scripts/spot_watch.sh &
set -euo pipefail
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu/ictd}"
TOKEN=$(curl -sf -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" || true)
HDR=()
[[ -n "$TOKEN" ]] && HDR=(-H "X-aws-ec2-metadata-token: $TOKEN")

echo "[spot_watch] armed"
while true; do
  ACTION=$(curl -sf "${HDR[@]}" http://169.254.169.254/latest/meta-data/spot/instance-action 2>/dev/null || true)
  if [[ -n "$ACTION" ]]; then
    echo "[spot_watch] INTERRUPT: $ACTION"
    mkdir -p "$REMOTE_DIR/outputs"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$REMOTE_DIR/outputs/SPOT_INTERRUPTION"
    echo "$ACTION" >> "$REMOTE_DIR/outputs/SPOT_INTERRUPTION"
    # best-effort flush
    sync || true
    pkill -TERM -f 'src.run_cluster' || true
    sleep 5
    exit 0
  fi
  sleep 5
done
