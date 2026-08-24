#!/usr/bin/env bash
# terraform apply → write infra/azure/.active/node.env
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/config.env" 2>/dev/null || source "$SCRIPT_DIR/config.env.example"
mkdir -p "$ACTIVE_DIR"
cd "$TF_DIR"

if [[ ! -f terraform.tfvars ]]; then
  echo "missing $TF_DIR/terraform.tfvars — copy terraform.tfvars.example" >&2
  exit 1
fi

terraform init -input=false
terraform apply -auto-approve

VM_ID=$(terraform output -raw vm_id)
NODE_IP=$(terraform output -raw public_ip)
NODE_PRIV_IP=$(terraform output -raw private_ip)
VM_SIZE=$(terraform output -raw vm_size)
COLLECTOR=$(terraform output -raw collector_url)

JOB_ID="ictd-azure-$(date -u +%Y%m%d-%H%M%S)"
ENV_FILE="$ACTIVE_DIR/node.env"
cat >"$ENV_FILE" <<EOF
JOB_ID=$JOB_ID
AZURE_REGION=$AZURE_REGION
SSH_USER=$SSH_USER
SSH_KEY=$SSH_KEY
REMOTE_DIR=$REMOTE_DIR
VM_ID=$VM_ID
VM_SIZE=$VM_SIZE
NODE_IP=$NODE_IP
NODE_PRIV_IP=$NODE_PRIV_IP
COLLECTOR_URL=$COLLECTOR
LAUNCHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
ln -sfn "$ENV_FILE" "$ACTIVE_DIR/latest.env"
echo "[launch] wrote $ENV_FILE"
echo "[launch] vm=$NODE_IP size=$VM_SIZE"
echo "[launch] NEXT: ./infra/azure/scripts/bootstrap.sh && ./infra/azure/scripts/sync.sh"
echo "[launch] ARM:  ./infra/azure/scripts/autodestroy.sh 4   # hard kill after 4h"
