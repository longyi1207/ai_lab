#!/usr/bin/env bash
# terraform apply → write infra/.active/cluster.env
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

IDS=$(terraform output -json instance_ids)
PUB=$(terraform output -json public_ips)
PRIV=$(terraform output -json private_ips)
MASTER=$(terraform output -raw master_addr)
COLLECTOR=$(terraform output -raw collector_url)

NODE0_IP=$(python3 -c "import json,sys; print(json.load(sys.stdin)[0])" <<<"$PUB")
NODE1_IP=$(python3 -c "import json,sys; print(json.load(sys.stdin)[1])" <<<"$PUB")
NODE0_PRIV=$(python3 -c "import json,sys; print(json.load(sys.stdin)[0])" <<<"$PRIV")
NODE1_PRIV=$(python3 -c "import json,sys; print(json.load(sys.stdin)[1])" <<<"$PRIV")
ID0=$(python3 -c "import json,sys; print(json.load(sys.stdin)[0])" <<<"$IDS")
ID1=$(python3 -c "import json,sys; print(json.load(sys.stdin)[1])" <<<"$IDS")

JOB_ID="ictd-$(date -u +%Y%m%d-%H%M%S)"
ENV_FILE="$ACTIVE_DIR/cluster.env"
cat > "$ENV_FILE" <<EOF
JOB_ID=$JOB_ID
AWS_REGION=$AWS_REGION
AWS_PROFILE=$AWS_PROFILE
SSH_USER=$SSH_USER
SSH_KEY=$SSH_KEY
REMOTE_DIR=$REMOTE_DIR
INSTANCE_ID_0=$ID0
INSTANCE_ID_1=$ID1
NODE0_IP=$NODE0_IP
NODE1_IP=$NODE1_IP
NODE0_PRIV=$NODE0_PRIV
NODE1_PRIV=$NODE1_PRIV
MASTER_ADDR=$MASTER
COLLECTOR_URL=$COLLECTOR
LAUNCHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
ln -sfn "$ENV_FILE" "$ACTIVE_DIR/latest.env"
echo "[launch] wrote $ENV_FILE"
echo "[launch] node0=$NODE0_IP node1=$NODE1_IP master=$MASTER"
echo "[launch] NEXT: ./infra/scripts/bootstrap.sh && ./infra/scripts/sync.sh"
echo "[launch] ARM:  ./infra/scripts/autodestroy.sh 4   # hard kill after 4h"
echo "[launch] SPOT: on each node, nohup bash infra/scripts/spot_watch.sh &"
