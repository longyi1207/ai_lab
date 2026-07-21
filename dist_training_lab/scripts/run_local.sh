#!/usr/bin/env bash
# Phase 1: single-process training on MPS/CPU.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python src/train.py "$@"
