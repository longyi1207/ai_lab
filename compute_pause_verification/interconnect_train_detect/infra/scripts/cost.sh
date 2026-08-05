#!/usr/bin/env bash
# Live OD price × 2 nodes via AWS Pricing API (us-east-1). Falls back to hardcoded.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_cluster_env

TYPE=$(cd "$TF_DIR" && terraform output -raw cost_warning 2>/dev/null | sed -n 's/.*2× \([^ ]*\).*/\1/p' || echo "g5.48xlarge")
REGION="${AWS_REGION:-us-east-1}"
PROFILE="${AWS_PROFILE:-default}"

python3 - <<PY
import json, subprocess, datetime, sys
itype = "$TYPE"
region = "$REGION"
profile = "$PROFILE"
fallback = {"g5.48xlarge": 16.288, "p4d.24xlarge": 21.9576, "p5.48xlarge": 98.32}

def live_price():
    # AWS Price List Query API (us-east-1 endpoint hosts the index)
    try:
        import urllib.request
        # use aws cli get-products if available
        cmd = [
            "aws", "pricing", "get-products",
            "--region", "us-east-1",
            "--profile", profile,
            "--service-code", "AmazonEC2",
            "--filters",
            f"Type=TERM_MATCH,Field=instanceType,Value={itype}",
            "Type=TERM_MATCH,Field=location,Value=US East (N. Virginia)",
            "Type=TERM_MATCH,Field=operatingSystem,Value=Linux",
            "Type=TERM_MATCH,Field=tenancy,Value=Shared",
            "Type=TERM_MATCH,Field=capacitystatus,Value=Used",
            "Type=TERM_MATCH,Field=preInstalledSw,Value=NA",
            "--max-results", "1",
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        data = json.loads(out)
        raw = json.loads(data["PriceList"][0])
        terms = raw["terms"]["OnDemand"]
        for _, term in terms.items():
            for _, dim in term["priceDimensions"].items():
                return float(dim["pricePerUnit"]["USD"]), "aws_pricing_api"
    except Exception as e:
        return fallback.get(itype, 16.288), f"fallback ({e.__class__.__name__})"

rate, src = live_price()
launched = "${LAUNCHED_AT}"
t0 = datetime.datetime.strptime(launched, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
hours = (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds() / 3600
print(f"type={itype} ×2")
print(f"od_rate_each=\${rate:.4f}/hr  source={src}")
print(f"elapsed={hours:.2f}h  est_cost=\${hours*rate*2:.2f}")
print("destroy: ./infra/scripts/destroy.sh")
print("arm timer: ./infra/scripts/autodestroy.sh 4")
PY
