#!/usr/bin/env bash
# Live hourly rate for the deployed vm_size/region via the public, UNAUTHENTICATED Azure
# Retail Prices API (no az login / credentials needed — just a normal HTTPS GET). Falls back
# to FALLBACK_HOURLY (a real number, last verified live 2026-08-17 — see that dict) if the API
# call fails. Prices drift; the live lookup is always preferred, the fallback is a dated
# sanity check, not a promise of current pricing.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
source "$SCRIPT_DIR/config.env" 2>/dev/null || true
load_node_env

REGION="${AZURE_REGION:-eastus}"
SIZE="${VM_SIZE:-Standard_ND96asr_v4}"

python3 - "$SIZE" "$REGION" "${LAUNCHED_AT:-}" <<'PY'
import sys, json, urllib.request, urllib.parse, datetime

size, region, launched_at = sys.argv[1], sys.argv[2], sys.argv[3]

# Verified live 2026-08-17 against https://prices.azure.com/api/retail/prices (eastus,
# on-demand Linux, Consumption meter — excludes Spot/Low-Priority/Windows/Reservation).
# These WILL drift — Azure repriced these SKUs before and will again. Only trust this as a
# same-order-of-magnitude sanity check; the live lookup above is the actual source of truth.
FALLBACK_HOURLY = {
    "Standard_ND96asr_v4": 27.197,       # ND A100 v4, on-demand, verified 2026-08-17
    "Standard_ND96isr_H100_v5": 98.320,  # ND H100 v5, on-demand, verified 2026-08-17 — note this is ~3.6x the A100 rate
}


def live_price():
    filt = (
        f"armRegionName eq '{region}' and armSkuName eq '{size}' "
        "and priceType eq 'Consumption' and serviceFamily eq 'Compute'"
    )
    url = "https://prices.azure.com/api/retail/prices?$filter=" + urllib.parse.quote(filt)
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.load(r)
        items = data.get("Items", [])
        # Prefer a plain Linux consumption meter: skip Windows-licensed and Spot/Low-Priority
        # meters so we're comparing like-for-like with the on-demand Linux VM this deploys.
        candidates = [
            it
            for it in items
            if "windows" not in it.get("productName", "").lower()
            and "spot" not in it.get("meterName", "").lower()
            and "low priority" not in it.get("meterName", "").lower()
        ]
        if not candidates:
            candidates = items
        if candidates:
            return float(candidates[0]["retailPrice"]), "azure_retail_prices_api (live)"
    except Exception as e:
        print(f"[cost] live API lookup failed: {e.__class__.__name__}: {e}", file=sys.stderr)
    fb = FALLBACK_HOURLY.get(size)
    if fb is not None:
        return fb, "fallback (last live-verified 2026-08-17 — live lookup failed just now, this may be stale)"
    return None, "unknown"


rate, src = live_price()

hours = None
if launched_at:
    try:
        t0 = datetime.datetime.strptime(launched_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        )
        hours = (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds() / 3600
    except ValueError:
        pass

print(f"size={size} region={region} (1 VM)")
if rate is None:
    print("od_rate=UNKNOWN — live API lookup failed and no verified fallback exists for this size.")
    print("Verify manually before trusting any cost estimate:")
    print("  https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/")
else:
    print(f"od_rate=${rate:.4f}/hr  source={src}")
    if hours is not None:
        print(f"elapsed={hours:.2f}h  est_cost=${hours * rate:.2f}")
print("destroy: ./infra/azure/scripts/destroy.sh")
print("arm timer: ./infra/azure/scripts/autodestroy.sh 4")
PY
