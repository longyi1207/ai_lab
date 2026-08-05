#!/usr/bin/env bash
# Hardened 2-node run: barrier file, health checks, timeout, teardown on FAIL.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_cluster_env

CONFIG_REL="${1:-configs/aws_g5.yaml}"
VENV="$REMOTE_DIR/.venv"
TIMEOUT_SEC="${ICTD_RUN_TIMEOUT_SEC:-7200}"
BARRIER="/tmp/ictd_barrier_$$"
RUN_ID="run-$(date -u +%Y%m%d%H%M%S)"

cleanup() {
  local rc=$?
  echo "[run] cleanup rc=$rc"
  ssh_node 0 "pkill -f 'src.run_cluster' || true; pkill -f 'src.monitor' || true" 2>/dev/null || true
  ssh_node 1 "pkill -f 'src.run_cluster' || true; pkill -f 'src.monitor' || true" 2>/dev/null || true
  exit "$rc"
}
trap cleanup EXIT

write_env() {
  local rank="$1"
  local node="node${rank}"
  ssh_node "$rank" "cat > $REMOTE_DIR/node.env" <<EOF
export ICTD_NODE_RANK=$rank
export ICTD_NODE=$node
export ICTD_MASTER_ADDR=$MASTER_ADDR
export ICTD_COLLECTOR=$COLLECTOR_URL
export ICTD_MASTER_PORT=29500
export ICTD_NCCL_COUNTER=/tmp/ictd_nccl_bytes
export NCCL_DEBUG=INFO
export NCCL_DEBUG_FILE=$REMOTE_DIR/outputs/nccl_node${rank}.log
export ICTD_NCCL_LOG=$REMOTE_DIR/outputs/nccl_node${rank}.log
export FI_PROVIDER=\${FI_PROVIDER:-efa}
export PYTHONPATH=$REMOTE_DIR
export ICTD_RUN_ID=$RUN_ID
EOF
}

write_env 0
write_env 1

ssh_node 0 "mkdir -p $REMOTE_DIR/outputs && rm -f /tmp/ictd_ready_node0 /tmp/ictd_ready_node1 /tmp/ictd_done_node0 /tmp/ictd_done_node1"
ssh_node 1 "mkdir -p $REMOTE_DIR/outputs && rm -f /tmp/ictd_ready_node0 /tmp/ictd_ready_node1 /tmp/ictd_done_node0 /tmp/ictd_done_node1"

echo "[run] starting node1 peer…"
ssh_node 1 "bash -lc '
  source $VENV/bin/activate
  source $REMOTE_DIR/node.env
  cd $REMOTE_DIR
  touch /tmp/ictd_ready_node1
  # wait until node0 collector is healthy
  for i in \$(seq 1 60); do
    if curl -sf \"\$ICTD_COLLECTOR/health\" >/dev/null; then break; fi
    sleep 2
  done
  timeout $TIMEOUT_SEC python -m src.run_cluster --config $CONFIG_REL --workloads-only
  echo \$? > /tmp/ictd_done_node1
'" &
PEER_PID=$!

echo "[run] waiting for node1 ready…"
for i in $(seq 1 60); do
  if ssh_node 1 "test -f /tmp/ictd_ready_node1"; then break; fi
  sleep 1
done

echo "[run] starting node0…"
ssh_node 0 "bash -lc '
  source $VENV/bin/activate
  source $REMOTE_DIR/node.env
  cd $REMOTE_DIR
  # start collector path via run_cluster
  touch /tmp/ictd_ready_node0
  # give collector a moment then signal
  (
    for i in \$(seq 1 30); do
      if curl -sf http://127.0.0.1:8765/health >/dev/null; then
        touch /tmp/ictd_collector_ok
        break
      fi
      sleep 1
    done
  ) &
  timeout $TIMEOUT_SEC python -m src.run_cluster --config $CONFIG_REL
  echo \$? > /tmp/ictd_done_node0
'"

wait "$PEER_PID" || true
RC0=$(ssh_node 0 "cat /tmp/ictd_done_node0 2>/dev/null || echo 1")
RC1=$(ssh_node 1 "cat /tmp/ictd_done_node1 2>/dev/null || echo 1")
echo "[run] node0_rc=$RC0 node1_rc=$RC1"
[[ "$RC0" == "0" && "$RC1" == "0" ]]
