#!/usr/bin/env bash
# Schedule terraform destroy after N hours (default 4). Call after launch.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_node_env

HOURS="${1:-4}"
SECS=$((HOURS * 3600))
LOG="$ACTIVE_DIR/autodestroy.log"
PIDFILE="$ACTIVE_DIR/autodestroy.pid"

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "autodestroy already running pid=$(cat "$PIDFILE")"
  exit 0
fi

nohup bash -c "
  echo \"[\$(date -u)] autodestroy armed for ${HOURS}h\" >> '$LOG'
  sleep $SECS
  echo \"[\$(date -u)] firing destroy\" >> '$LOG'
  '$SCRIPT_DIR/destroy.sh' >> '$LOG' 2>&1
" >/dev/null 2>&1 &
echo $! >"$PIDFILE"
echo "[autodestroy] armed ${HOURS}h pid=$(cat "$PIDFILE") log=$LOG"
echo "[autodestroy] cancel: kill \$(cat $PIDFILE) && rm $PIDFILE"
