"""Numbers for 精讲/11_挂谷与Fourier限制.md (deck §14).

Pure Python 3, no extra dependencies. Runs in well under a minute.
Every section prints the numbers that the chapter copies into the text.

Sections
  A. The needle: disk, Pál triangle, Kakeya's deltoid (area by shoelace,
     constant tangent-segment length checked numerically).
  B. Box-counting dimension: segment, square, Cantor set, and {1/n}.
  C. Tubes: total volume of δ-tubes, Córdoba's 2D 1/log(1/δ) scale,
     the trivial (Hölder) maximal bound proved in the Lean file vs the
     conjectured δ^(-ε), and why λ^3 is the natural power.
  D. Finite-field Kakeya in F_q^2: exact minimum by exhaustive search
     (q = 3, 5, 7) vs Dvir's bound and the Blokhuis–Mazzocca formula;
     Dvir's polynomial-method argument checked by brute force for q = 3.
  E. Fourier extension from the sphere: E1(x) = 2 sin(2π|x|)/|x| checked
     by numerical integration; why p = 3 is the threshold.
  F. Exponent tables (Kakeya 3D/4D, restriction, Bochner–Riesz, Falconer).
  G. Dates.
"""

import itertools
import math
from datetime import date


def header(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ---------------------------------------------------------------------------
# A. The needle
# ---------------------------------------------------------------------------
header("A. Needle problem: areas of three regions where a unit needle can turn")

disk = math.pi / 4  # disk of diameter 1
tri = 1 / math.sqrt(3)  # equilateral triangle of height 1 (Pál 1921)
print(f"disk of diameter 1           area = pi/4    = {disk:.4f}")
print(f"equilateral triangle, h = 1  area = 1/sqrt3 = {tri:.4f}  (side = {2/math.sqrt(3):.4f})")

# Deltoid traced by a circle of radius r rolling inside a circle of radius 3r.
# Every tangent line meets the deltoid again in two points 4r apart, so r = 1/4
# gives a deltoid in which a unit needle can turn.
r = 0.25


def deltoid(t):
    return (2 * r * math.cos(t) + r * math.cos(2 * t),
            2 * r * math.sin(t) - r * math.sin(2 * t))


M = 200000
pts = [deltoid(2 * math.pi * k / M) for k in range(M)]
shoelace = 0.0
for k in range(M):
    x1, y1 = pts[k]
    x2, y2 = pts[(k + 1) % M]
    shoelace += x1 * y2 - x2 * y1
area_deltoid = abs(shoelace) / 2
print(f"Kakeya's deltoid (r = 1/4)   area (shoelace, {M} pts) = {area_deltoid:.6f};"
      f" pi/8 = {math.pi/8:.6f}")


def tangent_chord_length(t0):
    """Length of the tangent segment at parameter t0 between the two other
    intersection points of the tangent line with the deltoid."""
    h = 1e-6
    x0, y0 = deltoid(t0)
    xa, ya = deltoid(t0 + h)
    xb, yb = deltoid(t0 - h)
    dx, dy = xa - xb, ya - yb

    def g(s):
        x, y = deltoid(s)
        return dx * (y - y0) - dy * (x - x0)

    roots = []
    N = 20000
    prev_s, prev_g = 0.0, g(0.0)
    for k in range(1, N + 1):
        s = 2 * math.pi * k / N
        gs = g(s)
        if prev_g == 0 or prev_g * gs < 0:
            a, b = prev_s, s
            for _ in range(60):
                m = (a + b) / 2
                if g(a) * g(m) <= 0:
                    b = m
                else:
                    a = m
            root = (a + b) / 2
            d = abs((root - t0 + math.pi) % (2 * math.pi) - math.pi)
            if d > 1e-3:  # discard the (double) root at the tangency point
                roots.append(root)
        prev_s, prev_g = s, gs
    roots = sorted(set(round(x, 9) for x in roots))
    if len(roots) != 2:
        return None
    p, q_ = deltoid(roots[0]), deltoid(roots[1])
    return math.dist(p, q_)


for t0 in (0.3, 1.0, 2.2):
    L = tangent_chord_length(t0)
    print(f"  tangent segment at t = {t0}: length = {L:.6f}")

# ---------------------------------------------------------------------------
# B. Box counting
# ---------------------------------------------------------------------------
header("B. Box-counting dimension  dim ≈ log N(δ) / log(1/δ)")


def show(name, rows):
    print(name)
    for delta, n in rows:
        est = math.log(n) / math.log(1 / delta)
        print(f"   δ = {delta:<10.3g} N(δ) = {n:<10d} log N/log(1/δ) = {est:.4f}")


# segment [0,1]: boxes of size 1/m
show("segment [0,1]", [(1 / m, len({min(int(i / 10**6 * m), m - 1) for i in range(0, 10**6 + 1, 7)}))
                       for m in (10, 100, 1000)])

# square [0,1]^2 on a fine grid
G = 600
square_pts = [(i / (G - 1), j / (G - 1)) for i in range(G) for j in range(G)]
rows = []
for m in (10, 50, 100):
    rows.append((1 / m, len({(min(int(x * m), m - 1), min(int(y * m), m - 1)) for x, y in square_pts})))
show("square [0,1]^2", rows)

# Cantor set: left endpoints of level-K intervals, as integers in units of 3^-K
K = 12
cantor = [0]
for level in range(K):
    cantor = [3 * c for c in cantor] + [3 * c + 2 for c in cantor]
# after K steps the integers are sums of digits in {0,2} times 3^(K-1-j)
rows = []
for j in (2, 4, 6, 8, 10):
    boxes = {c // 3 ** (K - j) for c in cantor}
    rows.append((3.0 ** -j, len(boxes)))
show("Cantor set (level-12 approximation)", rows)
print(f"   exact value log2/log3 = {math.log(2)/math.log(3):.4f}")

# {1/n : n >= 1}: countable, Hausdorff dimension 0, but box dimension 1/2
NMAX = 2_000_000
rows = []
for delta in (1e-2, 1e-3, 1e-4, 1e-5):
    boxes = {int((1.0 / n) / delta) for n in range(1, NMAX + 1)}
    boxes.add(0)  # all points with n > NMAX lie in [0, 1/NMAX] ⊂ first box
    rows.append((delta, len(boxes)))
show("{1/n : n = 1, 2, 3, ...}  (countable set)", rows)
print("   (box dimension → 1/2, while Hausdorff dimension is 0)")
for delta, n in rows:
    print(f"   check N(δ) vs 2/sqrt(δ): δ = {delta:g}: {n} vs {2/math.sqrt(delta):.0f}")

# ---------------------------------------------------------------------------
# C. Tubes and maximal functions
# ---------------------------------------------------------------------------
header("C. δ-tubes, Córdoba scale, trivial vs conjectured maximal bound")

print("R^3: about δ^-2 tubes with δ-separated directions, each of volume πδ^2:")
for delta in (1e-1, 1e-2, 1e-3, 1e-4):
    n_tubes = delta ** -2
    print(f"   δ = {delta:g}: tubes ≈ {n_tubes:.0e}, one tube volume = {math.pi*delta**2:.2e},"
          f" total if disjoint ≈ {n_tubes*math.pi*delta**2:.4f}")

print("R^2 (Córdoba 1977, sharp up to constants): union area can be as small as ~ 1/log(1/δ):")
for delta in (1e-2, 1e-4, 1e-6, 1e-12, 1e-100):
    print(f"   δ = {delta:g}: 1/ln(1/δ) = {1/math.log(1/delta):.4f}")

print("Trivial bound proved in lean/OAI/Analysis/Kakeya/FixedScale.lean:")
print("   ||K_δ f||_3 <= (4π)^(1/3) (πδ^2)^(-1/3) ||f||_3   (grows like δ^(-2/3))")
for delta in (1e-2, 1e-4, 1e-6):
    triv = (4 * math.pi) ** (1 / 3) * (math.pi * delta ** 2) ** (-1 / 3)
    conj = delta ** (-0.01)
    print(f"   δ = {delta:g}: trivial constant = {triv:,.1f};  conjectured shape δ^(-0.01) = {conj:.3f}")

print("Why λ^3: f = indicator of the lit parts; each direction's best tube average >= λ,")
print("so (4π)^(1/3) λ <= C δ^(-ε) |union|^(1/3), i.e. |union| >= λ^3 · 4π / (C^3 δ^(-3ε)).")
print("Illustration of how much weaker λ^K is than λ^3 (K = 100 is a made-up value):")
for lam in (0.5, 0.1, 0.01):
    print(f"   λ = {lam}: λ^3 = {lam**3:.2e},  λ^100 = {lam**100:.2e}")

# ---------------------------------------------------------------------------
# D. Finite-field Kakeya in the plane
# ---------------------------------------------------------------------------
header("D. Finite-field Kakeya sets in F_q^2 (q prime)")


def lines_by_direction(q):
    """Return a list of directions; each direction is a list of q lines,
    each line a bitmask over the q^2 points (x, y) -> index x*q + y."""
    dirs = []
    for m in range(q):  # direction (1, m): lines y = m x + b
        lines = []
        for b in range(q):
            mask = 0
            for x in range(q):
                y = (m * x + b) % q
                mask |= 1 << (x * q + y)
            lines.append(mask)
        dirs.append(((1, m), lines))
    lines = []  # direction (0, 1): lines x = c
    for c in range(q):
        mask = 0
        for y in range(q):
            mask |= 1 << (c * q + y)
        lines.append(mask)
    dirs.append(((0, 1), lines))
    return dirs


def min_kakeya(q):
    dirs = lines_by_direction(q)
    vertical = dirs[-1][1][0]  # by translation, WLOG the vertical line is x = 0
    others = [d[1] for d in dirs[:-1]]
    best, best_choice, count_best = None, None, 0
    for choice in itertools.product(range(q), repeat=q):
        mask = vertical
        for lines, b in zip(others, choice):
            mask |= lines[b]
        size = bin(mask).count("1")
        if best is None or size < best:
            best, best_choice, count_best = size, choice, 1
        elif size == best:
            count_best += 1
    return best, best_choice, dirs, count_best


for q in (3, 5, 7):
    best, choice, dirs, cnt = min_kakeya(q)
    dvir = q * (q + 1) // 2
    bm = q * (q + 1) // 2 + (q - 1) // 2
    print(f"q = {q}: points = {q*q}, directions = {q+1}, choices searched = {q**q}")
    print(f"   exact minimum Kakeya set size = {best}   (choices attaining it: {cnt})")
    print(f"   Dvir / counting bound q(q+1)/2 = {dvir};  Blokhuis–Mazzocca q(q+1)/2+(q-1)/2 = {bm}")
    print(f"   fraction of the plane = {best/(q*q):.3f}")
    if q == 3:
        mask = dirs[-1][1][0]
        desc = ["x = 0"]
        for (v, lines), b in zip(dirs[:-1], choice):
            mask |= lines[b]
            desc.append(f"y = {v[1]}x + {b}")
        pts_ = sorted((i // q, i % q) for i in range(q * q) if mask >> i & 1)
        print("   one minimal set:", pts_)
        print("   its lines:", "; ".join(desc))

# Dvir's argument for q = 3, n = 2, degree <= q-1 = 2.
print()
print("Dvir's polynomial method, q = 3, n = 2:")
q = 3
monos = [(i, j) for i in range(3) for j in range(3) if i + j <= 2]
print(f"   monomials of degree <= 2: {len(monos)} -> {monos}  (= C(q+n-1, n) = C(4,2) = {math.comb(4,2)})")
plane = [(x, y) for x in range(q) for y in range(q)]


def ev(coeffs, x, y):
    return sum(c * pow(x, i, q) * pow(y, j, q) for c, (i, j) in zip(coeffs, monos)) % q


nonzero_polys = [c for c in itertools.product(range(q), repeat=len(monos)) if any(c)]
print(f"   nonzero polynomials of degree <= 2 over F_3: {len(nonzero_polys)}")
vanish_everywhere = [c for c in nonzero_polys if all(ev(c, x, y) == 0 for x, y in plane)]
print(f"   ... of these, vanishing on all 9 points of F_3^2: {len(vanish_everywhere)}")
ok = 0
for S in itertools.combinations(plane, 5):
    if any(all(ev(c, x, y) == 0 for x, y in S) for c in nonzero_polys):
        ok += 1
print(f"   5-point subsets with a nonzero degree<=2 polynomial vanishing on them: {ok} / {math.comb(9,5)}")

# Example: S = 5 points, find a vanishing polynomial and list which directions its
# top-degree part kills (S can contain full lines only in those directions).
S = [(0, 0), (0, 1), (0, 2), (1, 0), (2, 0)]
for c in nonzero_polys:
    if all(ev(c, x, y) == 0 for x, y in S):
        P = c
        break
terms = " + ".join(f"{a}·x^{i}y^{j}" for a, (i, j) in zip(P, monos) if a)
print(f"   example S = {S}; a vanishing polynomial: P = {terms} (mod 3)")
deg = max(i + j for a, (i, j) in zip(P, monos) if a)
top = [(a, (i, j)) for a, (i, j) in zip(P, monos) if a and i + j == deg]
dirs3 = [(1, 0), (1, 1), (1, 2), (0, 1)]
killed = [v for v in dirs3 if sum(a * pow(v[0], i, q) * pow(v[1], j, q) for a, (i, j) in top) % q == 0]
print(f"   degree {deg}, top part {top}; directions where top part vanishes: {killed}")
print("   -> S can contain a full line only in those directions (and indeed has x=0 and y=0).")

# Higher-dimensional numbers
print()
print("Lower bounds for Kakeya sets in F_q^n, q = 101:")
q = 101
for n in (2, 3, 4):
    print(f"   n = {n}: q^n = {q**n:,}; Dvir C(q+n-1,n) = {math.comb(q+n-1,n):,} "
          f"(= {math.comb(q+n-1,n)/q**n:.3f} q^n); q^n/n! = {q**n/math.factorial(n):,.0f}; "
          f"DKSS q^n/2^n = {q**n/2**n:,.0f}")

# ---------------------------------------------------------------------------
# E. Fourier extension from the sphere
# ---------------------------------------------------------------------------
header("E. Extension of the constant function 1 from the unit sphere S^2")


def E1_numeric(rr, steps=200000):
    # E1(x) = ∫_{S^2} e^{2πi x·ω} dσ(ω); put x on the z-axis, |x| = rr.
    # dσ = 2π du with u = cos θ ∈ [-1, 1]; the imaginary part cancels.
    h = 2.0 / steps
    s = 0.0
    for k in range(steps):
        u = -1 + (k + 0.5) * h
        s += math.cos(2 * math.pi * rr * u)
    return 2 * math.pi * s * h


for rr in (0.25, 1.3, 5.7):
    print(f"   |x| = {rr}: numeric = {E1_numeric(rr):.6f}, formula 2 sin(2π|x|)/|x| = "
          f"{2*math.sin(2*math.pi*rr)/rr:.6f}")
print(f"   at x = 0: E1 = 4π = {4*math.pi:.4f} (surface area of S^2)")


def tail_integral(p, R, steps_per_unit=400):
    # ∫_{1<|x|<R} |E1(x)|^p dx = ∫_1^R |2 sin(2πr)/r|^p 4π r^2 dr
    n = int((R - 1) * steps_per_unit)
    h = (R - 1) / n
    s = 0.0
    for k in range(n):
        rr = 1 + (k + 0.5) * h
        s += abs(2 * math.sin(2 * math.pi * rr) / rr) ** p * 4 * math.pi * rr * rr
    return s * h


for p in (3.0, 3.5, 4.0):
    vals = [tail_integral(p, R) for R in (10, 100, 1000)]
    print(f"   p = {p}: ∫_(1<|x|<R) |E1|^p for R = 10, 100, 1000: "
          + ", ".join(f"{v:.2f}" for v in vals))

# ---------------------------------------------------------------------------
# F. Exponent tables
# ---------------------------------------------------------------------------
header("F. Exponents")

print("Kakeya dimension lower bounds in R^4:")
for name, val in [("Wolff (n+2)/2", 3.0), ("Guth–Zahl et al. 3 + 1/40", 3 + 1 / 40),
                  ("Katz–Zahl maximal parameter", 3.049),
                  ("Borges et al. (159+sqrt145)/56", (159 + math.sqrt(145)) / 56),
                  ("Katz–Zahl Hausdorff", 3.059), ("sticky only: Rai Choudhuri 13/4", 13 / 4),
                  ("OpenAI claim", 4.0)]:
    print(f"   {name:<36s} {val:.4f}")
print(f"   share of the gap 3 -> 4 closed before OpenAI (Hausdorff): {(3.059-3)/1:.1%}")

print("Kakeya in R^3: Wolff 5/2 = 2.5; Wang–Zahl 2025 = 3")

print("Restriction to the sphere in R^3, bounded data: ||Eg||_p <= C ||g||_inf for p > p0")
for name, val in [("Tomas–Stein (L^2 -> L^4)", 4.0), ("Tao 2003 bilinear (not re-read)", 10 / 3),
                  ("Bourgain–Guth 2011 (not re-read)", 3.3), ("Guth 2016 13/4", 13 / 4),
                  ("Wang broom 42/13", 42 / 13), ("Wang–Wu 22/7", 22 / 7), ("conjecture / OpenAI", 3.0)]:
    print(f"   {name:<34s} p0 = {val:.4f}   gap to 3: {val-3:.4f}")


def br_threshold(n, p):
    if p == math.inf:
        inv = 0.0
    else:
        inv = 1 / p
    return max(n * abs(inv - 0.5) - 0.5, 0.0)


print("Bochner–Riesz conjectured order threshold δ > max(n|1/p-1/2| - 1/2, 0):")
for p in (1, 1.5, 2, 3, 4, 6, math.inf):
    print(f"   p = {p}: n=2 -> {br_threshold(2, p):.4f};  n=3 -> {br_threshold(3, p):.4f}")

print("Falconer distance thresholds (dimension needed for positive-measure distance set):")
print(f"   d=2: Falconer (d+1)/2 = 1.5, Wolff 4/3 = {4/3:.4f}, Guth–Iosevich–Ou–Wang 5/4 = 1.25, conjecture d/2 = 1")
print(f"   d=3: Falconer 2, Erdoğan d/2+1/3 = {1.5+1/3:.4f}, Du–Guth–Ou–Wang–Wilson–Zhang 9/5 = 1.8, conjecture 1.5")

# ---------------------------------------------------------------------------
# G. Dates
# ---------------------------------------------------------------------------
header("G. Dates")


def months(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month) + (b.day - a.day) / 30.44


events = {
    "Fujiwara–Kakeya 1917": date(1917, 1, 1),
    "Davies 1971 (n = 2)": date(1971, 1, 1),
    "Wang–Zahl arXiv:2502.17655 v1": date(2025, 2, 24),
    "Guth–Wang–Zahl arXiv:2601.14411 v1": date(2026, 1, 20),
    "Fields Medal to Hong Wang": date(2026, 7, 23),
    "OpenAI 3D maximal manuscript": date(2026, 9, 23),
    "OpenAI 4D manuscript": date(2026, 9, 24),
    "OpenAI public release": date(2026, 10, 6),
}
for k, v in events.items():
    print(f"   {v.isoformat()}  {k}")
print(f"   Wang–Zahl preprint -> OpenAI 4D manuscript: {months(events['Wang–Zahl arXiv:2502.17655 v1'], events['OpenAI 4D manuscript']):.1f} months")
print(f"   Guth–Wang–Zahl streamlined -> OpenAI 4D manuscript: {months(events['Guth–Wang–Zahl arXiv:2601.14411 v1'], events['OpenAI 4D manuscript']):.1f} months")
print(f"   Fields Medal -> public release: {(events['OpenAI public release'] - events['Fields Medal to Hong Wang']).days} days")
print(f"   1917 -> 2025: {2025-1917} years;  Davies 1971 -> Wang–Zahl 2025: {2025-1971} years")
