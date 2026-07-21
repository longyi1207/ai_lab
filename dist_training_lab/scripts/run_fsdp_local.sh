#!/usr/bin/env bash
# Phase 3: simulate N-process FSDP2 locally on CPU (gloo backend) — same free-verification
# pattern as run_ddp_local.sh. Confirmed working: training, eval (collective forward), best/
# periodic/final checkpoint save (collective state-dict gather), and resume (incl. optimizer
# state) all round-trip correctly with 4 real processes and zero cloud spend.
set -euo pipefail
cd "$(dirname "$0")/.."

NPROC="${1:-4}"
shift || true

GLOO_SOCKET_IFNAME=lo0 .venv/bin/torchrun \
  --nproc_per_node="$NPROC" \
  --master_addr=127.0.0.1 --master_port=29501 \
  src/train.py --device cpu --parallelism fsdp "$@"
