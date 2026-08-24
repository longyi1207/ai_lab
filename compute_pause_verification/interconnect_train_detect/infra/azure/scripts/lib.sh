#!/usr/bin/env bash
# Shared helpers for ICTD Azure infra scripts. Single VM — no NODE0/NODE1 rank dance,
# just NODE_IP. Compare ../../scripts/lib.sh (AWS, 2-node) for the pattern this mirrors.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ACTIVE_DIR="${ACTIVE_DIR:-$PROJECT_ROOT/infra/azure/.active}"
TF_DIR="${TF_DIR:-$PROJECT_ROOT/infra/azure/terraform}"

load_node_env() {
  local f="${1:-$ACTIVE_DIR/latest.env}"
  if [[ ! -f "$f" ]]; then
    echo "missing $f — run launch.sh first (own VM) or join_shared_box.sh (shared AML compute instance)" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$f"
  : "${SSH_KEY:?}" "${NODE_IP:?}" "${REMOTE_DIR:?}"
  # SSH_PORT defaults to 22 (raw-VM path via launch.sh); Azure ML Compute
  # Instances use a non-standard port (e.g. 50000) — join_shared_box.sh
  # writes the real one.
  SSH_PORT="${SSH_PORT:-22}"
}

ssh_opts() {
  echo -p "$SSH_PORT" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$ACTIVE_DIR/known_hosts" -i "$SSH_KEY"
}

ssh_node() {
  # shellcheck disable=SC2046
  ssh $(ssh_opts) "${SSH_USER}@${NODE_IP}" "$@"
}

scp_to() {
  # scp's port flag is -P (capital); ssh_opts() emits -p (lowercase, ssh's
  # and rsync's own -e ssh flag — correct for ssh_node/wait_ssh/pull.sh).
  # Re-emitting ssh_opts() verbatim here silently breaks scp: it parses
  # "-p 50000" as -p (preserve-attributes, no argument) followed by a
  # literal positional arg "50000", which scp then tries to stat as a
  # source file. Swap just that one flag.
  local opts=()
  local prev=""
  for tok in $(ssh_opts); do
    if [[ "$prev" == "-p" ]]; then
      opts+=("-P" "$tok")
    elif [[ "$tok" != "-p" ]]; then
      opts+=("$tok")
    fi
    prev="$tok"
  done
  scp "${opts[@]}" "$@" "${SSH_USER}@${NODE_IP}:"
}

wait_ssh() {
  local ip="$1"
  echo "[wait] SSH $ip"
  for i in $(seq 1 60); do
    if ssh $(ssh_opts) -o ConnectTimeout=5 "${SSH_USER}@${ip}" "echo ok" >/dev/null 2>&1; then
      echo "[wait] ready $ip"
      return 0
    fi
    sleep 5
  done
  echo "SSH timeout: $ip" >&2
  return 1
}
