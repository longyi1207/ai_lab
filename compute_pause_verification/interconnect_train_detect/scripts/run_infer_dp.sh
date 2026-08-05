#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export ICTD_COLLECTOR="${ICTD_COLLECTOR:-http://127.0.0.1:8765}"
NNODES="${NNODES:-1}"
NPROC="${NPROC:-8}"
NODE_RANK="${NODE_RANK:-0}"
MASTER_ADDR="${MASTER_ADDR:-127.0.0.1}"
MASTER_PORT="${MASTER_PORT:-29500}"

torchrun \
  --nnodes="$NNODES" --nproc_per_node="$NPROC" --node_rank="$NODE_RANK" \
  --master_addr="$MASTER_ADDR" --master_port="$MASTER_PORT" \
  -m src.workloads.infer_dp "$@"
