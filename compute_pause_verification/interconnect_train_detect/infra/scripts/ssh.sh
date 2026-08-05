#!/usr/bin/env bash
# ssh into node0 (default) or node1: ./ssh.sh 1
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_cluster_env
RANK="${1:-0}"
shift || true
ssh_node "$RANK" "$@"
