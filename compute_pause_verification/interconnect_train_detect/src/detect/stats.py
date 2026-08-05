"""Welch t-test, Cohen's d, bootstrap CI for train vs infer GB/s separation."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np


@dataclass
class TwoSampleResult:
    name_a: str
    name_b: str
    n_a: int
    n_b: int
    mean_a: float
    mean_b: float
    std_a: float
    std_b: float
    mean_diff: float  # mean_a - mean_b
    cohens_d: float
    hedges_g: float
    t_stat: float
    df: float
    p_value: float
    ci95_diff: tuple[float, float]
    ci95_d: tuple[float, float]
    separable: bool  # heuristic: p < alpha and |d| >= d_min
    alpha: float
    d_min: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ci95_diff"] = list(self.ci95_diff)
        d["ci95_d"] = list(self.ci95_d)
        return d


def _as_arr(x: Sequence[float]) -> np.ndarray:
    a = np.asarray(list(x), dtype=np.float64)
    if a.size == 0:
        raise ValueError("empty sample")
    return a


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    """Pooled-SD Cohen's d (a - b)."""
    aa, bb = _as_arr(a), _as_arr(b)
    na, nb = len(aa), len(bb)
    va, vb = aa.var(ddof=1), bb.var(ddof=1)
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / max(na + nb - 2, 1))
    if pooled < 1e-15:
        return 0.0 if abs(aa.mean() - bb.mean()) < 1e-15 else math.copysign(math.inf, aa.mean() - bb.mean())
    return float((aa.mean() - bb.mean()) / pooled)


def hedges_g(a: Sequence[float], b: Sequence[float]) -> float:
    """Bias-corrected Cohen's d."""
    aa, bb = _as_arr(a), _as_arr(b)
    n = len(aa) + len(bb)
    if n <= 3:
        return cohens_d(aa, bb)
    J = 1.0 - 3.0 / (4.0 * (n - 2) - 1.0)
    return float(J * cohens_d(aa, bb))


def welch_t(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    """Return (t, df, two-sided p) via Welch–Satterthwaite + regularized incomplete beta."""
    aa, bb = _as_arr(a), _as_arr(b)
    na, nb = len(aa), len(bb)
    if na < 2 or nb < 2:
        raise ValueError("Welch t needs n>=2 per group")
    ma, mb = aa.mean(), bb.mean()
    va, vb = aa.var(ddof=1), bb.var(ddof=1)
    se2 = va / na + vb / nb
    if se2 <= 0:
        return 0.0, float(na + nb - 2), 1.0
    t = (ma - mb) / math.sqrt(se2)
    # Welch–Satterthwaite df
    num = se2 ** 2
    den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    df = num / den if den > 0 else float(na + nb - 2)
    p = _t_sf_two_sided(abs(t), df)
    return float(t), float(df), float(p)


def _t_sf_two_sided(t_abs: float, df: float) -> float:
    """Two-sided survival function of Student's t without scipy dependency."""
    # P(|T| > t) = incomplete beta relation
    x = df / (df + t_abs * t_abs)
    # regularized incomplete beta I_x(df/2, 1/2)
    try:
        from math import betainc  # py3.13+
        ib = betainc(df / 2.0, 0.5, x)
    except ImportError:
        ib = _betainc_reg(df / 2.0, 0.5, x)
    return float(ib)


def _betainc_reg(a: float, b: float, x: float) -> float:
    """Continued-fraction regularized incomplete beta (Numerical Recipes style)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    # use symmetry if needed for convergence
    def betacf(aa: float, bb: float, xx: float) -> float:
        MAXIT, EPS, FPMIN = 200, 3e-7, 1e-30
        qab = aa + bb
        qap = aa + 1.0
        qam = aa - 1.0
        c = 1.0
        d = 1.0 - qab * xx / qap
        if abs(d) < FPMIN:
            d = FPMIN
        d = 1.0 / d
        h = d
        for m in range(1, MAXIT + 1):
            m2 = 2 * m
            aa_ = m * (bb - m) * xx / ((qam + m2) * (aa + m2))
            d = 1.0 + aa_ * d
            if abs(d) < FPMIN:
                d = FPMIN
            c = 1.0 + aa_ / c
            if abs(c) < FPMIN:
                c = FPMIN
            d = 1.0 / d
            h *= d * c
            aa_ = -(aa + m) * (qab + m) * xx / ((aa + m2) * (qap + m2))
            d = 1.0 + aa_ * d
            if abs(d) < FPMIN:
                d = FPMIN
            c = 1.0 + aa_ / c
            if abs(c) < FPMIN:
                c = FPMIN
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < EPS:
                break
        return h

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(max(x, 1e-300)) * a + math.log(max(1 - x, 1e-300)) * b - lbeta) / a
    if x < (a + 1) / (a + b + 2):
        return front * betacf(a, b, x)
    return 1.0 - (math.exp(math.log(max(x, 1e-300)) * a + math.log(max(1 - x, 1e-300)) * b - lbeta) / b) * betacf(b, a, 1 - x)


def bootstrap_ci_diff(
    a: Sequence[float],
    b: Sequence[float],
    n_boot: int = 5000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    aa, bb = _as_arr(a), _as_arr(b)
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        sa = rng.choice(aa, size=len(aa), replace=True)
        sb = rng.choice(bb, size=len(bb), replace=True)
        diffs[i] = sa.mean() - sb.mean()
    lo, hi = np.quantile(diffs, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def bootstrap_ci_d(
    a: Sequence[float],
    b: Sequence[float],
    n_boot: int = 5000,
    alpha: float = 0.05,
    seed: int = 1,
) -> tuple[float, float]:
    aa, bb = _as_arr(a), _as_arr(b)
    rng = np.random.default_rng(seed)
    ds = np.empty(n_boot)
    for i in range(n_boot):
        sa = rng.choice(aa, size=len(aa), replace=True)
        sb = rng.choice(bb, size=len(bb), replace=True)
        ds[i] = cohens_d(sa, sb)
    # replace inf with large finite for quantile
    ds = np.nan_to_num(ds, nan=0.0, posinf=1e6, neginf=-1e6)
    lo, hi = np.quantile(ds, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def compare_two(
    a: Sequence[float],
    b: Sequence[float],
    name_a: str = "train",
    name_b: str = "infer",
    alpha: float = 0.05,
    d_min: float = 0.8,
    n_boot: int = 5000,
) -> TwoSampleResult:
    aa, bb = _as_arr(a), _as_arr(b)
    t, df, p = welch_t(aa, bb)
    d = cohens_d(aa, bb)
    g = hedges_g(aa, bb)
    ci_diff = bootstrap_ci_diff(aa, bb, n_boot=n_boot)
    ci_d = bootstrap_ci_d(aa, bb, n_boot=n_boot)
    return TwoSampleResult(
        name_a=name_a,
        name_b=name_b,
        n_a=len(aa),
        n_b=len(bb),
        mean_a=float(aa.mean()),
        mean_b=float(bb.mean()),
        std_a=float(aa.std(ddof=1)),
        std_b=float(bb.std(ddof=1)),
        mean_diff=float(aa.mean() - bb.mean()),
        cohens_d=float(d),
        hedges_g=float(g),
        t_stat=t,
        df=df,
        p_value=p,
        ci95_diff=ci_diff,
        ci95_d=ci_d,
        separable=(p < alpha and abs(d) >= d_min),
        alpha=alpha,
        d_min=d_min,
    )


def pairwise_by_label(
    samples: dict[str, Sequence[float]],
    pairs: list[tuple[str, str]] | None = None,
    **kwargs,
) -> list[TwoSampleResult]:
    labels = list(samples.keys())
    if pairs is None:
        pairs = [("train", "infer"), ("train", "diloco"), ("infer", "diloco")]
        pairs = [(a, b) for a, b in pairs if a in samples and b in samples]
        if not pairs and len(labels) >= 2:
            pairs = [(labels[0], labels[1])]
    return [compare_two(samples[a], samples[b], name_a=a, name_b=b, **kwargs) for a, b in pairs]
