#!/usr/bin/env bash
# Phase 2: simulate N-process DDP locally on CPU (gloo backend) — validates the DDP code path
# for free, no real GPUs needed. Not a speed test (CPU contention across N processes), a
# correctness test: does init_process_group/all-reduce/no_sync/checkpointing all work right
# when there's actually more than one process.
#
# --device cpu is required: gloo has no collective-communication support for MPS tensors.
# --master_addr=127.0.0.1 (not the default "localhost") sidesteps a macOS-specific bug where
# c10d's rendezvous does a reverse-DNS lookup on "localhost" that hangs/retries for minutes if
# your machine has no PTR record configured for ::1 — pass an IP literal and it's skipped.
set -euo pipefail
cd "$(dirname "$0")/.."

NPROC="${1:-4}"
shift || true

GLOO_SOCKET_IFNAME=lo0 .venv/bin/torchrun \
  --nproc_per_node="$NPROC" \
  --master_addr=127.0.0.1 --master_port=29501 \
  src/train.py --device cpu "$@"
