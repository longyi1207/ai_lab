#!/usr/bin/env bash
# On-node helper: detect EFA/IB iface + write monitor hints.
set -euo pipefail
echo "=== GPUs ==="
nvidia-smi -L
echo "=== EFA ==="
fi_info -p efa -t FI_EP_RDM 2>/dev/null | head -20 || echo "no EFA"
echo "=== IB sysfs ==="
ls /sys/class/infiniband 2>/dev/null || echo "no /sys/class/infiniband"
echo "=== NICs ==="
ip -br link
echo "=== suggested ICTD env ==="
IFACE=$(ip -br link | awk '/UP/ && $1!~/lo|docker/ {print $1; exit}')
echo "export ICTD_IFACE=$IFACE"
ls /sys/class/infiniband 2>/dev/null | head -1 | awk '{print "export ICTD_IB_DEVICE="$1}'
