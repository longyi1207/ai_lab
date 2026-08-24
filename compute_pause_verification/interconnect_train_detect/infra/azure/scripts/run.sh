#!/usr/bin/env bash
# Single-VM run: SSH in, activate venv, `python -m <module> --config <path>`, stream logs,
# propagate exit code.
#
# Unlike ../../scripts/run_remote.sh (AWS, 2 nodes) there is no barrier file, no peer
# coordination, and no master_addr/collector cross-node handshake to build — one VM, nothing
# to rendezvous with.
#
# --module lets this invoke either src.run_experiment (default, exists today) or
# src.run_redteam (being built in parallel under src/redteam/ — not assumed to exist yet).
# Only --config is assumed as a common CLI flag; no other flags of src.run_redteam are assumed.
#
# Usage:
#   ./run.sh [configs/some.yaml] [--module src.run_experiment|src.run_redteam]
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_node_env

MODULE="src.run_experiment"
CONFIG_REL="configs/smoke.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
  --module)
    MODULE="$2"
    shift 2
    ;;
  --module=*)
    MODULE="${1#--module=}"
    shift
    ;;
  *)
    CONFIG_REL="$1"
    shift
    ;;
  esac
done

VENV="$REMOTE_DIR/.venv"
TIMEOUT_SEC="${ICTD_RUN_TIMEOUT_SEC:-7200}"
RUN_ID="run-$(date -u +%Y%m%d%H%M%S)"

interrupt() {
  echo "[run] interrupted — killing remote $MODULE"
  ssh_node "pkill -f '$MODULE' || true" 2>/dev/null || true
  exit 130
}
trap interrupt INT TERM

# ICTD_GPU_INDICES (shared-box GPU slice, e.g. "3,4,5" — see
# src/run_redteam.py and docs/REDTEAM.md "Shared-box operation") is read
# from the LOCAL environment here and forwarded explicitly, since SSH does
# not propagate local env vars into the remote session on its own.
GPU_INDICES_EXPORT=""
if [[ -n "${ICTD_GPU_INDICES:-}" ]]; then
  GPU_INDICES_EXPORT="export ICTD_GPU_INDICES=$ICTD_GPU_INDICES
  export CUDA_VISIBLE_DEVICES=$ICTD_GPU_INDICES"
fi

echo "[run] module=$MODULE config=$CONFIG_REL run_id=$RUN_ID timeout=${TIMEOUT_SEC}s gpu_indices=${ICTD_GPU_INDICES:-<from config>}"
ssh_node "mkdir -p $REMOTE_DIR/outputs"

# Runs inside a detached tmux session ("ictd") server-side, built as a
# script file (not an inline nested-quoted ssh/tmux/bash command — three
# levels of shell-quoting nesting is exactly the kind of thing that looks
# right and silently isn't) rather than a plain foreground SSH command, so
# a dropped laptop connection (real risk over a run lasting tens of
# minutes on a shared box) doesn't kill the job. This script polls for
# completion instead of blocking on one unbroken SSH connection; re-attach
# any time with `ssh -i $SSH_KEY -p $SSH_PORT ${SSH_USER}@${NODE_IP} -t
# 'tmux attach -t ictd'` if you want to watch it live.
RC_MARKER="$REMOTE_DIR/outputs/.run_rc_${RUN_ID}"
LOCAL_SCRIPT="$(mktemp)"
cat >"$LOCAL_SCRIPT" <<EOF
#!/usr/bin/env bash
source $VENV/bin/activate
cd $REMOTE_DIR
export PYTHONPATH=$REMOTE_DIR
export ICTD_COLLECTOR=$COLLECTOR_URL
export ICTD_NODE=azurevm0
export ICTD_RUN_ID=$RUN_ID
export NCCL_DEBUG=INFO
export NCCL_DEBUG_FILE=$REMOTE_DIR/outputs/nccl.log
export ICTD_NCCL_LOG=$REMOTE_DIR/outputs/nccl.log
$GPU_INDICES_EXPORT
timeout $TIMEOUT_SEC python -m $MODULE --config $CONFIG_REL
echo \$? > $RC_MARKER
EOF
REMOTE_SCRIPT="$REMOTE_DIR/outputs/.run_${RUN_ID}.sh"
if ! scp_to "$LOCAL_SCRIPT"; then
  echo "[run] FATAL: scp of launch script to the remote box failed" >&2
  rm -f "$LOCAL_SCRIPT"
  exit 1
fi
# scp_to (lib.sh) drops files in the SSH user's home dir by scp convention;
# move it into place under REMOTE_DIR instead, then clean up the local temp.
if ! ssh_node "mv ~/$(basename "$LOCAL_SCRIPT") $REMOTE_SCRIPT && chmod +x $REMOTE_SCRIPT"; then
  echo "[run] FATAL: could not place launch script at $REMOTE_SCRIPT on the remote box" >&2
  rm -f "$LOCAL_SCRIPT"
  exit 1
fi
rm -f "$LOCAL_SCRIPT"

ssh_node "tmux kill-session -t ictd 2>/dev/null; tmux new-session -d -s ictd \"$REMOTE_SCRIPT\""
sleep 3
if ! ssh_node "tmux has-session -t ictd" 2>/dev/null; then
  echo "[run] FATAL: tmux session 'ictd' isn't up 3s after launch — it exited immediately (bad script? bad config path?). Check:" >&2
  echo "[run]   ssh -i $SSH_KEY -p $SSH_PORT ${SSH_USER}@${NODE_IP} cat $REMOTE_SCRIPT" >&2
  exit 1
fi

echo "[run] running in tmux session 'ictd' on the remote box — polling for completion"
echo "[run] (safe to Ctrl-C this poller; the remote job keeps running — reattach with:"
echo "[run]  ssh -i $SSH_KEY -p $SSH_PORT ${SSH_USER}@${NODE_IP} -t 'tmux attach -t ictd')"

# Ground truth is the rc marker file, not tmux session presence. Confirmed
# 2026-08-21: a per-user systemd `Linger=no` setting (shared-box-wide, fixed
# now via `loginctl enable-linger`, but defense-in-depth here regardless)
# tore down the whole detached-session scope, including tmux, whenever the
# last SSH connection to the box happened to close between polls — while
# the actual job process kept running unaffected, orphaned from tmux. A
# missing tmux session is a WARNING to investigate, not proof the job died.
GONE_STREAK=0
while true; do
  if ssh_node "test -f $RC_MARKER" 2>/dev/null; then
    break
  fi
  if ssh_node "tmux has-session -t ictd" 2>/dev/null; then
    GONE_STREAK=0
  else
    GONE_STREAK=$((GONE_STREAK + 1))
    echo "[run] tmux session not visible (streak=$GONE_STREAK) — still polling for rc marker; job may just be orphaned, not dead" >&2
    if [[ "$GONE_STREAK" -ge 30 ]]; then
      echo "[run] tmux gone for $((GONE_STREAK * 10))s straight with no rc marker — giving up. Check by hand:" >&2
      echo "[run]   ssh -i $SSH_KEY -p $SSH_PORT ${SSH_USER}@${NODE_IP} 'ps aux | grep run_redteam; cat $RC_MARKER'" >&2
      exit 1
    fi
  fi
  sleep 10
done
RC=$(ssh_node "cat $RC_MARKER" 2>/dev/null || echo 1)
echo "[run] remote exit rc=$RC"
exit "$RC"
