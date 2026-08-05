#!/usr/bin/env bash
# Shared helpers for ICTD infra scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ACTIVE_DIR="${ACTIVE_DIR:-$PROJECT_ROOT/infra/.active}"
TF_DIR="${TF_DIR:-$PROJECT_ROOT/infra/terraform}"

load_cluster_env() {
  local f="${1:-$ACTIVE_DIR/latest.env}"
  if [[ ! -f "$f" ]]; then
    echo "missing $f — run launch.sh first" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$f"
  : "${SSH_KEY:?}" "${NODE0_IP:?}" "${NODE1_IP:?}" "${REMOTE_DIR:?}"
}

ssh_opts() {
  echo -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$ACTIVE_DIR/known_hosts" -i "$SSH_KEY"
}

ssh_node() {
  local rank="$1"; shift
  local ip
  if [[ "$rank" == "0" ]]; then ip="$NODE0_IP"; else ip="$NODE1_IP"; fi
  # shellcheck disable=SC2046
  ssh $(ssh_opts) "${SSH_USER}@${ip}" "$@"
}

scp_to() {
  local rank="$1"; shift
  local ip
  if [[ "$rank" == "0" ]]; then ip="$NODE0_IP"; else ip="$NODE1_IP"; fi
  # shellcheck disable=SC2046
  scp $(ssh_opts) "$@" "${SSH_USER}@${ip}:"
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
