"""Power analysis: how many replicates to detect train≫infer at given d, α, power."""
from __future__ import annotations

import argparse
import math
from dataclasses import asdict, dataclass

from ..util import setup_logging, write_json

log = setup_logging("power")


@dataclass
class PowerResult:
    alpha: float
    power: float
    cohens_d: float
    n_per_group: int
    two_sided: bool
    method: str
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


def _z(p: float) -> float:
    """Approx inverse CDF of standard normal (Acklam)."""
    if p <= 0 or p >= 1:
        raise ValueError("p in (0,1)")
    # coefficients
    a = [ -3.969683028665376e+01,  2.209460984245205e+02,
          -2.759285104469687e+02,  1.383577518672690e+02,
          -3.066479806614716e+01,  2.506628277459239e+00 ]
    b = [ -5.447609879822406e+01,  1.615858368580409e+02,
          -1.556989798598866e+02,  6.680131188771972e+01,
          -1.328068155288572e+01 ]
    c = [ -7.784894002430293e-03, -3.223964580411365e-01,
          -2.400758277161838e+00, -2.549732539343734e+00,
           4.374664141464968e+00,  2.938163982698783e+00 ]
    d = [  7.784695709041462e-03,  3.224671290700398e-01,
           2.445134137142996e+00,  3.754408661907416e+00 ]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) * q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def n_per_group_two_sample(
    cohens_d: float = 0.8,
    alpha: float = 0.05,
    power: float = 0.8,
    two_sided: bool = True,
) -> PowerResult:
    """Equal-n two-sample z approximation (good enough for planning GPU hours).

    n ≈ 2 * ((z_{1-α/2} + z_{power}) / d)^2
    """
    if abs(cohens_d) < 1e-9:
        raise ValueError("d must be non-zero")
    z_a = _z(1 - alpha / (2 if two_sided else 1))
    z_b = _z(power)
    n = 2.0 * ((z_a + z_b) / abs(cohens_d)) ** 2
    n_i = max(2, int(math.ceil(n)))
    return PowerResult(
        alpha=alpha, power=power, cohens_d=cohens_d, n_per_group=n_i,
        two_sided=two_sided, method="equal_n_z_approx",
        note=f"plan ≥{n_i} replicate windows per label (train & infer)",
    )


def hours_estimate(
    n_per_group: int,
    minutes_per_rep: float = 8.0,
    n_labels: int = 3,
    cluster_hourly_usd: float = 32.6,
) -> dict:
    """Rough wall + $ for replicate campaign on 2-node cluster."""
    # each rep runs all labels sequentially
    wall_min = n_per_group * minutes_per_rep
    wall_h = wall_min / 60.0
    # +30% overhead bootstrap/sync
    wall_h *= 1.3
    return {
        "n_per_group": n_per_group,
        "n_labels": n_labels,
        "minutes_per_rep": minutes_per_rep,
        "wall_hours_est": round(wall_h, 2),
        "cluster_hourly_usd": cluster_hourly_usd,
        "cost_usd_est": round(wall_h * cluster_hourly_usd, 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Sample-size / power for ICTD")
    ap.add_argument("--d", type=float, default=0.8)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.8)
    ap.add_argument("--minutes-per-rep", type=float, default=8.0)
    ap.add_argument("--cluster-hourly", type=float, default=32.6, help="g5×2 default")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pr = n_per_group_two_sample(args.d, args.alpha, args.power)
    cost = hours_estimate(pr.n_per_group, args.minutes_per_rep, cluster_hourly_usd=args.cluster_hourly)
    out = {**pr.to_dict(), **cost}
    log.info("n/group=%d wall≈%.2fh cost≈$%.0f (d=%.2f α=%.2f power=%.2f)",
             pr.n_per_group, cost["wall_hours_est"], cost["cost_usd_est"],
             args.d, args.alpha, args.power)
    if args.out:
        write_json(args.out, out)
    else:
        import json
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
