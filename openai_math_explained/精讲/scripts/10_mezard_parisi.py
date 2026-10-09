"""Calculations for 精讲 10 (Mézard–Parisi). All numbers in the chapter come from here."""
import itertools, math, time
import numpy as np
from scipy.optimize import linear_sum_assignment

rng = np.random.default_rng(20261008)
P = lambda *a: print(*a, flush=True)

def configs(n):
    return np.array(list(itertools.product([1, -1], repeat=n)))

# ---------- 1. two spins, ferromagnetic J=1: H = -J s1 s2
P("== 1. two-spin ferromagnet ==")
S = configs(2)
E = -S[:, 0] * S[:, 1]
for beta in [0.0, 0.5, 1.0, 2.0, 5.0]:
    w = np.exp(-beta * E); Z = w.sum(); p = w / Z
    P(f"beta={beta}: Z={Z:.4f}  P(each aligned)={p[0]:.4f}  P(each anti)={p[1]:.4f}  P(aligned total)={p[0]+p[3]:.4f}")

# ---------- 2. triangles
P("== 2. triangles ==")
S = configs(3)
for name, J in [("ferro J=+1", 1), ("antiferro J=-1", -1)]:
    E = -J * (S[:, 0]*S[:, 1] + S[:, 1]*S[:, 2] + S[:, 0]*S[:, 2])
    vals, cnt = np.unique(E, return_counts=True)
    P(name, "energies:", dict(zip(vals.tolist(), cnt.tolist())))
    for beta in [0.5, 1, 2, 5]:
        Z = np.exp(-beta*E).sum()
        F = -math.log(Z)/beta
        Emean = (E*np.exp(-beta*E)).sum()/Z
        Sent = beta*(Emean - F)
        P(f"  beta={beta}: Z={Z:.4f} F={F:.4f} <E>={Emean:.4f} S={Sent:.4f}")
    P("  ground-state entropy ln(deg)=", math.log(cnt[0]), "per spin", math.log(cnt[0])/3)
# check formula Z = 2e^{-3b}+6e^{b} for antiferro
b = 1.0; P("formula Z(1)=", 2*math.exp(-3*b)+6*math.exp(b))
# random-sign triangle frustration probability
P("P(triangle frustrated | iid ±1 signs) = fraction with product J<0:",
  np.mean([np.prod(j) < 0 for j in itertools.product([1, -1], repeat=3)]))

# ---------- 3. SK small N: local minima and ground states vs ferromagnet
P("== 3. landscape: ferro vs SK, N=12 ==")
def local_minima_count(Jm):
    n = Jm.shape[0]; S = configs(n)
    E = -0.5*np.einsum('ki,ij,kj->k', S, Jm, S)
    fields = S @ Jm  # local field h_i = sum_j J_ij s_j
    stable = np.all(S*fields >= 0, axis=1)  # flipping any spin does not lower energy
    return int(stable.sum()), E
n = 12
Jf = np.ones((n, n))/n; np.fill_diagonal(Jf, 0)
cf, Ef = local_minima_count(Jf)
P("ferro: #single-flip-stable configs =", cf, " min E/N=", Ef.min()/n)
cs = []
for t in range(20):
    G = rng.normal(0, 1/math.sqrt(n), (n, n)); Jm = np.triu(G, 1); Jm = Jm+Jm.T
    c, E = local_minima_count(Jm); cs.append(c)
P("SK N=12 over 20 samples: #single-flip-stable configs mean", np.mean(cs), "min", min(cs), "max", max(cs))
for n in [16]:
    cs = []
    for t in range(5):
        G = rng.normal(0, 1/math.sqrt(n), (n, n)); Jm = np.triu(G, 1); Jm = Jm+Jm.T
        c, E = local_minima_count(Jm); cs.append(c)
    P(f"SK N={n} over 5 samples: mean #stable", np.mean(cs), cs)

# ---------- 4. SK ground state energy per spin by exhaustive enumeration
P("== 4. SK ground-state energy per spin (exhaustive) ==")
def sk_ground(n, samples):
    S = configs(n).astype(np.float32)
    out = []
    for _ in range(samples):
        G = rng.normal(0, 1/math.sqrt(n), (n, n)).astype(np.float32); Jm = np.triu(G, 1)
        E = -np.einsum('ki,ij,kj->k', S, Jm, S)
        out.append(E.min()/n)
    return np.mean(out), np.std(out)/math.sqrt(samples)
for n, smp in [(8, 400), (12, 200), (16, 40), (20, 8)]:
    t = time.time(); m, se = sk_ground(n, smp)
    P(f"N={n} samples={smp}: E0/N = {m:.4f} ± {se:.4f}  ({time.time()-t:.1f}s)")
P("Parisi value (literature): -0.763166...")

# ---------- 5. annealed vs quenched, replica identity
P("== 5. quenched vs annealed (SK N=10, beta=2) ==")
n = 10; S = configs(n).astype(float); beta = 2.0
logZs = []; Zs = []
for _ in range(2000):
    G = rng.normal(0, 1/math.sqrt(n), (n, n)); Jm = np.triu(G, 1)
    E = -np.einsum('ki,ij,kj->k', S, Jm, S)
    a = -beta*E; mx = a.max(); lz = mx + math.log(np.exp(a-mx).sum())
    logZs.append(lz)
logZs = np.array(logZs)
quenched = logZs.mean()/n
annealed = (logZs.max() + math.log(np.mean(np.exp(logZs-logZs.max()))))/n
P(f"(1/N)E[log Z] = {quenched:.4f}   (1/N)log E[Z] (empirical) = {annealed:.4f}")
P("theory annealed for SK (N->inf): ln2 + beta^2/4 =", math.log(2)+beta**2/4)
# replica trick identity log Z = lim (E Z^n - 1)/n  -> E log Z = lim (E[Z^n]-1)/n ; use normalized Z
z = np.exp(logZs - logZs.mean())
for k in [1, 0.5, 0.1, 0.01, 0.001]:
    P(f"n={k}: (E[z^n]-1)/n = {(np.mean(z**k)-1)/k:.5f}   (target E log z = {np.mean(np.log(z)):.5f})")
P("toy: log 5 =", math.log(5), [(k, (5**k-1)/k) for k in [1, 0.1, 0.01, 0.001]])

# ---------- 6. sparse random graph locally tree-like: triangles in ER(N, c/N)
P("== 6. sparse ER graph, mean degree c=3: number of triangles vs N ==")
def er_triangles(N, c):
    M = rng.poisson(c*N/2)
    e = rng.integers(0, N, size=(M, 2)); e = e[e[:, 0] != e[:, 1]]
    e = np.sort(e, axis=1); e = np.unique(e, axis=0)
    adj = [set() for _ in range(N)]
    for a, b in e: adj[a].add(b); adj[b].add(a)
    tri = 0
    for a, b in e:
        tri += len(adj[a] & adj[b])
    deg = np.array([len(x) for x in adj])
    return tri//3, deg.mean(), np.mean(deg == 0)
for N in [100, 1000, 10000, 100000]:
    res = [er_triangles(N, 3) for _ in range(20 if N <= 10000 else 5)]
    P(f"N={N}: mean #triangles={np.mean([r[0] for r in res]):.2f}  mean degree={np.mean([r[1] for r in res]):.3f} frac isolated={np.mean([r[2] for r in res]):.4f}")
P("theory: E[#triangles] -> c^3/6 =", 27/6, " P(deg=0)=e^-3=", math.exp(-3))

# ---------- 7. cavity / belief propagation exact on tree, not on loop
P("== 7. cavity (BP) on a tree vs loop ==")
def exact_mags(n, edges, h, beta):
    S = configs(n).astype(float)
    E = -sum(J*S[:, i]*S[:, j] for i, j, J in edges) - S @ h
    w = np.exp(-beta*E); w /= w.sum()
    return (w[:, None]*S).sum(0), math.log(np.exp(-beta*E).sum())
def bp_mags(n, edges, h, beta, iters=200):
    # cavity fields u_{i->j}: message in field units
    nb = {i: [] for i in range(n)}
    for i, j, J in edges: nb[i].append((j, J)); nb[j].append((i, J))
    u = {(i, j): 0.0 for i in range(n) for j, _ in nb[i]}
    for _ in range(iters):
        new = {}
        for (i, j) in u:
            Jij = [J for k, J in nb[i] if k == j][0]
            hc = h[i] + sum(u[(k, i)] for k, _ in nb[i] if k != j)  # cavity field on i without j
            new[(i, j)] = math.atanh(math.tanh(beta*Jij)*math.tanh(beta*hc))/beta
        u = new
    return np.array([math.tanh(beta*(h[i] + sum(u[(k, i)] for k, _ in nb[i]))) for i in range(n)])
beta = 1.0
tree = [(0, 1, 1.0), (1, 2, -0.7), (1, 3, 0.5), (3, 4, -1.2)]
h = np.array([0.3, -0.2, 0.1, 0.4, -0.5])
ex, _ = exact_mags(5, tree, h, beta); bp = bp_mags(5, tree, h, beta)
P("tree exact:", np.round(ex, 6)); P("tree BP   :", np.round(bp, 6)); P("max diff", np.abs(ex-bp).max())
loop = tree + [(0, 2, 0.9), (2, 4, 1.0)]
ex, _ = exact_mags(5, loop, h, beta); bp = bp_mags(5, loop, h, beta)
P("loopy exact:", np.round(ex, 4)); P("loopy BP   :", np.round(bp, 4)); P("max diff", np.abs(ex-bp).max())
# hand-checkable: 2 spins, J=1, h=(0.5,0) beta=1: m2 = tanh(atanh(tanh1*tanh0.5))
ex, _ = exact_mags(2, [(0, 1, 1.0)], np.array([0.5, 0.0]), 1.0)
P("2-spin chain: exact m2=", ex[1], " cavity formula tanh(1)*tanh(0.5)=", math.tanh(1)*math.tanh(0.5))

# ---------- 8. random assignment
P("== 8. random assignment, Exp(1) costs ==")
P("pi^2/6 =", math.pi**2/6)
for n in [1, 2, 3, 5, 10, 30, 100, 300, 1000]:
    trials = {1: 200000, 2: 200000, 3: 100000, 5: 50000, 10: 20000, 30: 4000, 100: 1000, 300: 200, 1000: 40}[n]
    t = time.time(); vals = np.empty(trials)
    for k in range(trials):
        C = rng.exponential(1.0, (n, n)); r, c = linear_sum_assignment(C); vals[k] = C[r, c].sum()
    exact = sum(1/k**2 for k in range(1, n+1))
    P(f"n={n:5d} trials={trials:6d}: sim mean={vals.mean():.4f} ± {vals.std()/math.sqrt(trials):.4f}  Parisi sum_(k<=n)1/k^2={exact:.4f}  greedy-ish naive (identity) E=n  ({time.time()-t:.1f}s)")
# greedy row-by-row comparison n=100
n = 100; g = []
for _ in range(200):
    C = rng.exponential(1.0, (n, n)); used = np.zeros(n, bool); tot = 0
    for i in range(n):
        row = np.where(used, np.inf, C[i]); j = int(row.argmin()); used[j] = True; tot += C[i, j]
    g.append(tot)
P("greedy row-by-row n=100 mean cost:", np.mean(g))
# n=2 by hand check: E[min(a+d, b+c)] with 4 iid Exp(1) = 5/4
C = rng.exponential(1.0, (2_000_000, 4))
P("n=2 direct: E[min(a+d,b+c)] =", np.minimum(C[:, 0]+C[:, 3], C[:, 1]+C[:, 2]).mean())

# ---------- 9. Hopfield capacity
P("== 9. Hopfield retrieval, N=1000 ==")
N = 1000
for alpha in [0.05, 0.10, 0.12, 0.13, 0.14, 0.15, 0.17, 0.20]:
    Pn = int(alpha*N); ms = []
    for rep in range(3):
        X = rng.choice([-1, 1], size=(Pn, N)).astype(np.float32)
        W = X.T @ X / N; np.fill_diagonal(W, 0)
        for mu in range(min(Pn, 10)):
            s = X[mu].copy(); hloc = W @ s
            for sweep in range(50):  # asynchronous sweeps in random order
                changed = 0
                for i in rng.permutation(N):
                    v = 1.0 if hloc[i] >= 0 else -1.0
                    if v != s[i]:
                        hloc += (v - s[i]) * W[:, i]; s[i] = v; changed += 1
                if changed == 0: break
            ms.append(float(s @ X[mu] / N))
    ms = np.array(ms)
    P(f"alpha={alpha:.2f} (P={Pn}): mean final overlap m={ms.mean():.3f}  frac m>0.95={np.mean(ms > 0.95):.2f}")
P("AGS 1985 theory: alpha_c ~ 0.138, overlap just below alpha_c ~ 0.967")
