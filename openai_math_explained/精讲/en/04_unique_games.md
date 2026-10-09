# The Unique Games Conjecture: where is the ceiling for approximation algorithms?

> You only need to know what a graph is (vertices and edges), how to do modular arithmetic (7 mod 3 = 1), that "polynomial time" roughly means "grows mildly with input size", and to have a vague sense of P vs NP. Every new idea is explained before it is used.
> Every number here is either computed by script (script: `精讲/scripts/04_ugc.py`) or has a source. **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter. ⚠ = I could not fully verify this.
> Estimated reading time: 60–90 minutes. You can split it into three sittings: §7.1–7.4 (NP-hardness, approximation, 0.878, PCP), §7.5–7.7 (what a unique game is, why it matters, the 24-year tug-of-war), §7.8–7.10 (OpenAI's result, verification, what it means).

---

## 7.0 The bottom line: the one thing this chapter explains

Many important optimization problems (cutting a network into two halves, placing the fewest guards to watch every road…) are believed to have **no fast exact algorithm**. As a fallback, we ask: **what percentage of the optimum can a fast algorithm guarantee at best?**

For the most classic of these, the Max-Cut problem, someone gave an algorithm in 1995 that guarantees **87.8%**. On the other side, in 1997–2001 it was proved that guaranteeing more than **94.1%** is NP-hard. For 30 years, nobody knew where the truth lay in the 6 percentage points in between.

This chapter explains one chain of cause and effect:

> How well you can approximate ⟸ is decided by how hard it is to "tell nearly satisfiable apart from far from satisfiable" ⟸ the most important such constraint system is called Unique Games ⟸ the Unique Games Conjecture (UGC) says: telling these apart is NP-hard.

**If UGC is true**, then 87.8% is **exactly** the limit for Max-Cut, and the same argument settles the approximation limits of a whole class of problems at once. Khot proposed it in 2002, and for 24 years nobody could prove or refute it. **OpenAI claims to have proved it**, with a Lean formal proof attached.

After this chapter you should be able to explain in your own words:
- why a "fully satisfiable" unique game is easy, while a "nearly satisfiable" one is conjectured to be hard;
- exactly how UGC relates to the number 0.878;
- what OpenAI's result means if true, and what it does **not** mean (it has nothing to do with P vs NP).

---

## 7.1 P vs NP and NP-hardness: the 5-minute version

### 7.1.1 "Easy to check" is not "easy to find"

Sudoku: given a filled-in grid, checking whether it's right takes seconds; filling it in from an empty grid can take a long time of trial and error.

- **P**: problems where you can **find** the answer in polynomial time (say n² or n³ steps).
- **NP**: problems where, given a candidate answer, you can **check** whether it is right in polynomial time.

**P vs NP** asks: is everything that is easy to check also easy to find? Almost everyone believes **P ≠ NP**, but nobody has proved it (it is one of the Clay Millennium Problems).

### 7.1.2 Reductions and NP-hardness

**Reduction**: quickly translate any instance of problem A into an instance of problem B, so that B's answer is A's answer. If you can do this, then "B has a fast algorithm" implies "A has a fast algorithm", so B is at least as hard as A.

**3SAT**: given a bunch of clauses like "(x₁ OR NOT x₂ OR x₅)", each with 3 variables, can you assign true/false to the variables so that all clauses hold at once? The Cook–Levin theorem (1971) says every problem in NP can be reduced to 3SAT.

**NP-hard**: if 3SAT can be reduced to problem B, B is called NP-hard. Meaning: **unless P = NP, B has no polynomial-time algorithm.**

> Every "X is NP-hard" in this chapter should be read as "unless P = NP, X cannot be done". None of them **proves** P ≠ NP; they just tie X's fate to P vs NP.

---

## 7.2 The fallback: approximation algorithms

### 7.2.1 Max-Cut

Given a graph, split the vertices into two groups (say, color them black and white). An edge is "cut" if its two ends have different colors. **Max-Cut** asks: what is the largest number of edges you can cut? Deciding "can you cut ≥ k edges" is one of Karp's 21 NP-complete problems from 1972.

Computed by script (brute-force enumeration of all colorings):

| Graph | Edges | Max cut | Expected cut of random coloring | Random / optimal |
|---|---|---|---|---|
| Triangle | 3 | 2 | 1.5 | 0.750 |
| 5-cycle (pentagon) | 5 | 4 | 2.5 | 0.625 |
| Petersen graph | 15 | 12 | 7.5 | 0.625 |

Why a triangle can cut at most 2: three vertices and only two colors means two vertices must share a color, and the edge between them can't be cut.

### 7.2.2 Approximation ratio, and "1/2 for free"

An **α-approximation algorithm**: runs in polynomial time and always returns a solution worth at least "α × the optimum".

**Random coloring**: each vertex flips an independent coin to pick its color. The two ends of an edge get different colors with probability 1/2, so the expected cut is "half the edges". Since the optimum can't exceed the number of edges, random coloring is at least a **1/2-approximation**.

From 1976 (Sahni–Gonzalez) until 1995, 1/2 was the best guarantee known.

**[Check 1]** What is the max cut of a 4-cycle (a square, 4 edges)? How many edges does a random coloring cut in expectation?

### 7.2.3 Another lead character: Vertex Cover

Pick the fewest vertices in a graph so that every edge has at least one endpoint picked (imagine posting guards at intersections to watch every road).

A simple algorithm known since the 1970s: repeatedly find an edge with neither end picked, and **pick both ends**. The optimal solution has to pick at least one end of that edge, and we picked both, so we use at most **2 times** the optimum. That is a **2-approximation**.

For 50 years, nobody has managed "1.99 times".

---

## 7.3 Goemans–Williamson: turning vertices into vectors

### 7.3.1 Relaxation: first solve a looser problem

Max-Cut is hard because each vertex can take only two values (black = +1, white = −1). An edge (i, j) is cut exactly when xᵢ·xⱼ = −1, so the number of cut edges = Σ (1 − xᵢxⱼ)/2.

The idea of Goemans–Williamson (1995): **replace each ±1 with a unit vector vᵢ**, and replace the product xᵢxⱼ with the inner product vᵢ·vⱼ:

```
maximize  Σ_edges (1 − vᵢ·vⱼ)/2      subject to: each vᵢ is a vector of length 1
```

This is called a **semidefinite program (SDP)**, and it can be solved (approximately) in polynomial time. Since ±1 are "one-dimensional unit vectors", every solution of the original problem is also a solution of this one, so **the SDP optimum ≥ the true max cut**. Intuitively: the more "opposite" the two ends of an edge are pushed (the closer their angle is to 180°), the better.

### 7.3.2 Random hyperplane: turning vectors back into black and white

Once you have the vectors, pick a random plane through the origin, splitting space in two: color the points on one side black and the other side white.

Key fact: **two vectors at angle θ are separated by a random plane with probability exactly θ/π.** It's easiest to see in 2D: a random line through the origin falls "between" the two vectors with probability θ/180°.

Verified by script with 1,000,000 random planes:

| Angle | Theory θ/π | Simulation |
|---|---|---|
| 90° | 0.5000 | 0.4994 |
| 120° | 0.6667 | 0.6659 |
| 150° | 0.8333 | 0.8337 |

### 7.3.3 Where 0.878 comes from

For each edge, compare two quantities:
- the "score" the SDP gives it: (1 − cos θ)/2;
- the probability it is actually cut after rounding: θ/π.

As long as, for **every** angle, the second is at least α times the first, the whole graph gets at least α times the SDP value, and so at least α times the optimum. So the guarantee = the minimum of this ratio over all angles:

```
α_GW = min over θ of  (θ/π) / ((1 − cos θ)/2)  =  min  2θ / (π(1 − cos θ))
```

Computed by script (numerical minimization):

| Angle θ | SDP score | Probability cut | Ratio |
|---|---|---|---|
| 60° | 0.250 | 0.333 | 1.333 |
| 90° | 0.500 | 0.500 | 1.000 |
| 120° | 0.750 | 0.667 | 0.889 |
| **133.56°** | **0.845** | **0.742** | **0.8786 (minimum)** |
| 150° | 0.933 | 0.833 | 0.893 |
| 180° | 1.000 | 1.000 | 1.000 |

**α_GW = 0.878567…**, attained at θ ≈ 133.56° (inner product ρ ≈ −0.689). This matches the 0.878567… given in Eq. (1.1) of OpenAI's Max-Cut paper.

### 7.3.4 An example: the pentagon

The optimal SDP solution for the 5-cycle places the 5 vectors in a plane, one every 144° (= 4π/5). Computed by script:
- SDP value = 5 × (1 − cos 144°)/2 = **4.5225**;
- true max cut = 4;
- expected cut of a random plane = 5 × 144/180 = **4.000**.

So on the pentagon the SDP value is noticeably higher than the true optimum (4/4.5225 = 0.8845). This kind of "SDP is too optimistic" gap is called the **integrality gap**. Feige–Schechtman (2002) built graphs where this ratio gets arbitrarily close to 0.878, so **this SDP plus any rounding method can never beat 0.878**. But that only says "this one algorithm" has hit its limit, not that "all algorithms" have.

---

## 7.4 Approximation can be hard too: the PCP theorem

### 7.4.1 The intuition behind the PCP theorem

The **PCP theorem** (Arora–Safra; Arora–Lund–Motwani–Sudan–Szegedy, 1992 conference, 1998 journal; Dinur 2007 gave a combinatorial proof) says something that sounds like magic:

> Any mathematical proof can be rewritten in a special format such that a referee who **randomly reads only a constant number of bits** of it can tell, with high confidence, whether the proof is right: a correct proof always passes; a wrong proof, no matter how it is written, gets caught with probability at least one half.

### 7.4.2 Why it has to do with "approximation"

Restate PCP: there is a reduction starting from 3SAT that produces a constraint system such that
- formula satisfiable ⇒ the constraint system can be **fully** satisfied;
- formula unsatisfiable ⇒ the constraint system can satisfy **at most** a fixed fraction s < 1.

This is called a **gap**. Now suppose some algorithm guarantees an approximation ratio α > s. Then you could use it to tell the two cases apart, and so solve 3SAT. Therefore: **a gap ⇒ approximating above the gap is NP-hard.**

The game for the following decades was to make this gap "sharper and sharper", until it sits exactly at the position of a known algorithm.

### 7.4.3 The gap for Max-Cut

Håstad (2001, *JACM*), together with the "gadgets" of Trevisan–Sorkin–Sudan–Williamson, proved: **approximating Max-Cut above 16/17 ≈ 0.941 is NP-hard.**

So:

```
0.5 ─────────── 0.878 ░░░░░░░░░ 0.941 ──── 1.0
     random        GW algo  ?unknown?   NP-hard
```

**Who owns the region between 0.878 and 0.941?** A better algorithm, or a stronger hardness proof? This is what UGC is meant to answer.

The top half of the figure below is the same number line; the bottom half is the "completeness ladder" for unique games that §7.5–7.7 explain (proved up to about 1/2 in 2018; UGC needs 1 − ε). Skim it now and come back after §7.7.

{{FIG_MAXCUT}}

Vertex cover has a similar gap: the algorithm achieves 2, and the NP-hardness lower bound was Dinur–Safra's **1.3606** (2005, *Annals*), raised in 2018 to **√2 ≈ 1.414** (Khot–Minzer–Safra, see §7.7.2).

---

## 7.5 What Unique Games are

### 7.5.1 Labeling games

A **label constraint system** has:
- a graph;
- an "alphabet": each vertex picks a label from {0, 1, …, k−1};
- a constraint on each edge, saying which labels at the two ends count as "compatible".

The goal: pick labels so that the fraction of satisfied constraints (called the instance's **value**) is as high as possible.

"Label Cover", the standard output of the PCP theorem, has exactly this form, except that its constraints are "many-to-one": once one end is fixed, the other end has several choices.

### 7.5.2 "Unique": fix one end and the other is determined

**Unique Game**: every edge constraint is a **permutation** (a one-to-one correspondence). Once one end picks a label, there is **exactly one** label at the other end that satisfies the edge.

The most common example, and the one this chapter uses: **difference equations mod k**

```
x_i − x_j ≡ c   (mod k)
```

Given x_j, x_i is uniquely determined as x_j + c. (OpenAI's paper uses "translation constraints" a(v) = a(u) + c, which just replace numbers mod k with bitwise XOR on 0/1 vectors; it's essentially the same.)

### 7.5.3 By hand: a triangle, mod 3

Three variables a, b, c, labels {0, 1, 2}:

**Instance A**: b − a ≡ 1, c − b ≡ 1, a − c ≡ 1 (mod 3).
Add them up around the loop: 0 ≡ 3 ≡ 0, no contradiction. Take a = 0; propagating gives b = 1, c = 2; check a − c = −2 ≡ 1 ✓. **Everything is satisfied; value = 1.**

**Instance B**: change the last one to a − c ≡ 2.
Add them up around the loop: 0 ≡ 1 + 1 + 2 = 4 ≡ 1, a contradiction. So the three can't all hold at once, but dropping any one of them makes the rest satisfiable. **Value = 2/3.** (Confirmed by the script by brute-force enumeration of all 27 labelings.)

The general rule: **on a cycle, add up the constraint constants around the loop; if the sum is not 0 (mod k), at least one constraint on that cycle must be violated.**

**[Check 2]** Four variables x₀…x₃, mod 5, constraints: x₁−x₀≡2, x₂−x₁≡3, x₃−x₂≡1, x₀−x₃≡4, x₂−x₀≡0. Can they all be satisfied? What if the last one is changed to x₂−x₀≡1?

### 7.5.4 Why "fully satisfiable" is easy

If a unique game can be **fully** satisfied, there is a simple polynomial-time algorithm:

1. in each connected component, pick any vertex and try one of its k labels;
2. propagate along the edges: each edge uniquely determines the neighbor's label;
3. on hitting a contradiction, move to the next starting label; if all k fail, it can't be fully satisfied.

Each attempt is one pass over the graph, k attempts in total. Compare brute-force enumeration: 100 variables mod 3 means trying 3¹⁰⁰ ≈ 10⁴⁷·⁷ possibilities (computed by script).

This is completely different from 3SAT: even when a 3SAT formula is "fully satisfiable", finding a solution is hard. **So UGC can't be about "satisfiable vs unsatisfiable"; it has to be about "nearly satisfiable vs far from satisfiable".** That is where the 1 − ε in UGC comes from.

### 7.5.5 Why "nearly satisfiable" might be hard

Once a few constraints are "wrong", propagation carries the error a long way. The script ran an experiment: a random graph with 2000 vertices and on average 6 edges per vertex, mod 7; first plant a reference answer, then randomly tamper with a fraction of the constraints; then assign labels by propagation (breadth-first) from random starting points, trying 20 starting points:

| Fraction tampered | Value of planted answer | Propagation, average value | Propagation, best value |
|---|---|---|---|
| 0% | 1.000 | 1.000 | 1.000 |
| 1% | 0.990 | 0.958 | 0.982 |
| 5% | 0.947 | 0.728 | 0.845 |
| 10% | 0.901 | 0.610 | 0.709 |

(Computed by script; the random graph has a very small number of isolated vertices, whose label defaults to 0; this doesn't affect the conclusion.)

The reason: a vertex's label is "passed along" a path from the starting point, and as soon as the path crosses one bad edge, everything downstream is shifted.

**To be honest**: this experiment only shows that "propagation" fails, not that the problem itself is hard. On **random** noisy instances like these, smarter algorithms (such as SDP) actually do very well. What UGC says is: there **exist** carefully constructed instances where no polynomial-time algorithm can tell "it is 99% satisfiable" from "it is only 1% satisfiable".

### 7.5.6 The precise statement of UGC

> **Unique Games Conjecture (Khot 2002)**: for every ε > 0 and δ > 0, there is an alphabet size k such that, for unique games with alphabet k, it is NP-hard to tell apart the following two cases:
> - YES: value ≥ 1 − ε (nearly all satisfiable);
> - NO: value ≤ δ (nearly all unsatisfiable).

Note the **order of quantifiers**: first ε and δ are given, **then** the alphabet size k is chosen. If you flip it and let k grow with the instance, there are known algorithms that solve it (the SDP algorithm of Charikar–Makarychev–Makarychev 2006 gets about 1 − O(√(ε log k)), which is very good when k is small). §1.2 of OpenAI's paper discusses this point specifically.

---

## 7.6 Why UGC matters: one conjecture governs a whole territory

The appeal of UGC: assuming it holds, the **exact** approximation limits of many problems can be computed, and they often **exactly equal some known algorithm**.

| Problem | Best algorithm | Unconditional NP-hardness (before 2026) | Assuming UGC |
|---|---|---|---|
| Max-Cut | 0.878 (GW 1995) | 16/17 ≈ 0.941 (Håstad 2001) | **0.878 is the limit** (KKMO 2004/07) |
| Vertex cover | 2 | √2 ≈ 1.414 (KMS 2018) | **2 is the limit** (Khot–Regev 2003/08) |
| All constraint satisfaction problems (CSPs) | Basic SDP + rounding | Varies | **Basic SDP is the optimal algorithm** (Raghavendra 2008) |

A few key results:

- **KKMO** (Khot–Kindler–Mossel–O'Donnell, FOCS 2004, *SICOMP* 2007): UGC ⇒ beating α_GW on Max-Cut is NP-hard. A probability statement they needed, "Majority Is Stablest", was later proved by Mossel–O'Donnell–Oleszkiewicz (2005, *Annals* 2010). The odd 133.56° angle in the GW algorithm corresponds exactly to the "noise" parameter in the hardness reduction: the algorithm and the hardness meet at the same number.
- **Khot–Regev** (CCC 2003, *JCSS* 2008): UGC ⇒ vertex cover can't achieve 2 − ε. The clumsy 1970s "pick both ends" algorithm is optimal.
- **Raghavendra** (STOC 2008): UGC ⇒ for **every** CSP, the same generic SDP algorithm is the optimal polynomial-time approximation algorithm. One algorithm plus one conjecture settles an entire class of problems.

This is why UGC is called "the map of the field of approximation algorithms". Khot received the 2014 Nevanlinna Prize for it.

---

## 7.7 A 24-year tug-of-war: support and doubt

### 7.7.1 Doubt: a subexponential-time algorithm (2010)

Arora–Barak–Steurer (FOCS 2010, *JACM* 2015) gave an algorithm that, for a unique game with alphabet k, n variables and value ≥ 1 − ε^c (c a fixed constant), finds a labeling satisfying 1 − ε in **exp(k·n^ε)** time.

Why did this make people doubt UGC? Because 3SAT is generally believed to need close to 2ⁿ time, while UG needs only 2 to "a small power of n". Comparison computed by script:

| n | 3ⁿ (brute force) | 2^(n^0.1) | 2^(n^(1/3)) | n³ |
|---|---|---|---|---|
| 100 | 10^47.7 | 3 | 10^1.4 | 10⁶ |
| 1,000 | 10^477 | 4.0 | 10^3.0 | 10⁹ |
| 1,000,000 | 10^477121 | 15.8 | 10^30.1 | 10¹⁸ |

If UGC holds, the reduction from 3SAT to UG must **blow up** the instance to a very large polynomial size (otherwise 3SAT would also have a subexponential algorithm). That is not a contradiction, but it shows that even if UG is hard, it is "not thoroughly hard". Some researchers leaned toward believing UGC is false because of this.

### 7.7.2 Support: the 2-to-2 theorem (2018)

**2-to-2 constraints**: a bit looser than unique; once one end is fixed, the other end has 2 allowed labels. A series of works by Khot–Minzer–Safra and Dinur–Khot–Kindler–Minzer–Safra in 2017–2018 (the last piece being the KMS FOCS 2018 theorem on expansion in Grassmann graphs) proved: **nearly satisfiable 2-to-2 games are NP-hard.**

Corollaries:
- Unique games with **completeness about 1/2** are NP-hard: telling "value ≥ 1/2 − ε" from "value ≤ δ". This has been called "half of UGC".
- Vertex cover to within √2 − ε is NP-hard.

What remained hard: pushing completeness from 1/2 to 1 − ε. §1.3 of OpenAI's paper also says: "Obtaining Unique Games completeness arbitrarily close to one was a separate problem."

### 7.7.3 September 2026: a race

According to Quanta (2026-10-07), MIT's Dor Minzer and his students Yumou Fei and Shuo Wang, after hearing rumors that OpenAI was about to release a proof of UGC, rushed out a proof of a 4-to-1 variant of Khot's 2-to-1 conjecture on 2026-09-14. O'Donnell's comment: "They solved the problem in the old-fashioned way, with their minds, and wrote it with their own fingers." [R]

---

## 7.8 What OpenAI claims

### 7.8.1 The main result

The abstract of the paper *The Unique Games Theorem* (2026-09-23, 58 pages, author listed as "OpenAI"):

> "We prove the Unique Games Conjecture. For every fixed ε, δ ∈ (0, 1/2), we give a deterministic polynomial-time reduction from 3SAT to Unique Games over a fixed finite alphabet, with completeness at least 1 − ε and soundness at most δ." [P]

In plain words: **for any fixed ε, δ, there is a deterministic polynomial-time reduction that translates 3SAT into unique games with a fixed alphabet: satisfiable formulas become instances with value ≥ 1 − ε, and unsatisfiable ones become instances with value ≤ δ.** This is exactly the statement of UGC from §7.5.6.

Theorem 1.1 also states a stronger form: the alphabet is the 0/1 vector space F₂ˢ, every constraint is a translation, and the graph is simple, bipartite and unweighted. The paper says this is a known equivalent form of UGC (citing KKMO), so "stronger" is not "swapping in a different problem".

### 7.8.2 Other papers in the same family (family 102)

| Paper | Pages | Conclusion |
|---|---|---|
| A Direct Proof of Optimal Max-Cut Hardness | 38 | Beating α_GW on Max-Cut is NP-hard |
| The Factor-Two Hardness Threshold for Vertex Cover | 25 | Vertex cover can't be approximated to any constant factor < 2 |
| Constant-factor hardness of Min-UnCut | — | Every constant factor is NP-hard |
| Constant-factor hardness of directed feedback vertex set | — | Every constant factor is NP-hard |

The repo's CONTENTS.md says these 4 papers are **independent direct reductions** that "use established PCP and Label Cover hardness results" and don't depend on the UGC paper. In other words, even if the UGC paper has an error, its two most famous consequences, Max-Cut 0.878 and vertex cover 2, have a separate independent path. The complexity theorist Dana Moshkovitz put it this way, in commentary that Aaronson posted as comment #2 on "The Mathocalypse" (it opens "Additional commentary from Dana on the UGC proof"): "The Unique Games Conjecture is true, though it wasn't really needed for the proof of its most famous corollaries", with optimal hardness of approximating Max-Cut and other constraint satisfaction problems as her examples in parentheses [R]. These 4 direct reductions are what she means.

In addition, **family 105** (*Perfect completeness for 2-to-1 games*) claims a proof of Khot's 2-to-1 conjecture (the perfect-completeness version). Footnote 1 of the UGC paper says it is "not an input to this proof".

### 7.8.3 Intuition for the method (I read only the introduction; this is a simplified version)

1. **Starting point**: Håstad's hardness result for "nearly satisfiable systems of parity equations" (each equation x + y + z ≡ b mod 2).
2. **Why the 2-to-2 road got stuck at 1/2**: in the "matrix short code" of Barak–Kothari–Steurer, the probability that an honest proof's answer stays unchanged under one random rank-one perturbation is (1 + 2^(−ℓ))/2, i.e. about 1/2. So completeness could only reach 1/2.
3. **The key new idea: a different kind of noise.** The paper constructs a nonlinear "encoder" C and a special noise μ: honest answers barely change under this noise (change probability ≤ an arbitrarily small p), but any "cheating", high-rank linear observation still notices the noise with probability at least 1/8. An analogy: design a jitter that barely affects correct readings but exposes forged ones. This lets completeness be pushed to 1 − ε while keeping the structural tools that the 2-to-2 approach uses for soundness.
4. **Soundness (unsatisfiable formulas have value ≤ δ)**: reuses the Grassmann expansion theorem of KMS 2018 (in the form of an "inverse short code theorem") to extract a strategy, then uses parallel repetition (Dinur–Steurer 2014) to push the success rate down to exp(−c·k^(1/3)), giving a contradiction.
5. **Finishing up**: remove weights and repeated edges to get a simple, unweighted, bipartite instance.

---

## 7.9 How far it has been verified

### 7.9.1 The Lean statement: much longer than the quasi-Riemann hypothesis, but still readable

The Lean statement of the quasi-Riemann hypothesis (§4) is a single line, because Mathlib already has the ζ function. UGC is different: Mathlib has **no** ready-made definitions of "unique game", "3SAT encoding" or "polynomial-time reduction to a graph", so the challenge file `ComparatorChallenges/UniqueGamesTheorem.lean` (239 lines) has to define all of these itself. The core theorem (full name `OAI.UniqueGamesTheorem.theorem11`; the translation below is from my reading of the Lean source [P]):

```lean
theorem theorem11 (ε δ : ℝ)
    (hε : 0 < ε) (hεhalf : ε < 1 / 2)
    (hδ : 0 < δ) (hδhalf : δ < 1 / 2) :
    Nonempty (Explicit.MachineOutputContract.BinaryGapReduction ε δ)
```

Word by word:
- `(ε δ : ℝ)`: ε and δ are real numbers.
- `hε`, `hδ`: assume 0 < ε < 1/2 and 0 < δ < 1/2.
- `Nonempty (BinaryGapReduction ε δ)`: the conclusion is "there **exists** a reduction satisfying all of the conditions below".

`BinaryGapReduction ε δ` is a structure that requires all of the following at once:

| Field | Meaning |
|---|---|
| `alphabet`, `dimension`, `coordinates` | Alphabet size k ≥ 2, identified with F₂ˢ (0/1 vectors) |
| `construct : List Bool → Instance alphabet` | Takes a string of bits (the encoding of a 3SAT formula) and outputs a unique game |
| `simpleBipartite` | The output graph is a simple bipartite graph |
| `translations` | Every constraint is a translation a(v) = a(u) + c |
| `computation : Turing.TM2ComputableInPolyTime …` | `construct` can be computed in polynomial time by Mathlib's multi-tape Turing machine |
| `finiteAlphabet` | The Turing machine's tape alphabet is finite |
| `completeness` | Input is a satisfiable formula ⇒ there is a labeling satisfying a fraction ≥ 1 − ε |
| `soundness` | Input is not a satisfiable formula ⇒ every labeling satisfies a fraction ≤ δ |

A few details worth noting:
- Permutations are represented as "forward table + inverse table + two proofs that they are inverses", so they really are one-to-one.
- Repeated edges are counted by multiplicity; there are no hidden weights.
- If the input string can't even be parsed as a formula, it counts as "unsatisfiable", and the reduction must still output an instance with value ≤ δ. This is a stricter requirement, not a loophole.
- Restricting ε, δ < 1/2 doesn't affect the conclusion: UGC is precisely about small ε, δ.
- Completeness is written as ≥ 1 − ε rather than = 1, which is correct: as §7.5.4 said, the fully satisfiable case is easy.

**My judgment: this is a faithful encoding of UGC, in a stronger form.** One outside fact the reader has to supply: the theorem says "reduces from 3SAT"; "therefore NP-hard" also needs the Cook–Levin theorem (3SAT is NP-complete). That step is not in this statement, but it is a textbook result and uncontroversial.

### 7.9.2 The proof itself

- Solution directory `OAI/Computability/UniqueGames/`: **478 Lean files, 186,782 lines** (counted by script).
- grep for `sorry`, `axiom`, `admit`, `native_decide`, `implemented_by`, `unsafe`: 0 hits. The Comparator config allows only three standard axioms (`propext`, `Quot.sound`, `Classical.choice`).
- Apart from Mathlib, the proof imports nothing from other directories in the repo. Since Mathlib has no PCP theorem, **the PCP theorem, Håstad's result, KMS's Grassmann expansion theorem, parallel repetition, and the polynomial-time Turing machine implementation** should all have been formalized from scratch within these 478 files. The subdirectory names (`PCP/` with 104 files, `Inverse/` with 39 files including `KMS…`, `Repetition/`, `Machines/` with 144 files) are consistent with this. ⚠ This is inferred from the directory structure and import relations; I did not open each one to check.
- The direct proofs for Max-Cut and vertex cover also have Lean: `MaxCut/` has 372 files, 186,763 lines; `VertexCover/` has 354 files, 66,335 lines. In the Max-Cut statement, α_GW is defined directly as the `sInf` of 2·arccos ρ / (π(1 − ρ)), which is exactly the formula from §7.3.3 (arccos ρ = θ).
- **What wasn't done**: I did not compile it. The Comparator config for the UGC family has `enable_nanoda: false`, meaning no second, independent kernel re-check. Unlike the quasi-Riemann hypothesis (§4), I found no third party who has publicly re-run this proof ⚠. The repo's `formalization.yaml` itself says `review: status: unchecked`.

### 7.9.3 Human experts

- Lance Fortnow (blog post "Open No More", 2026-10-07): "if they hold up, we've seen more progress in TCS in the last 24 hours than in the previous three decades combined." [R]
- Mark Braverman (Princeton, Quanta 2026-10-07): "Math by press release is not that healthy for math." [R]
- Quanta's report says this proof "didn't undergo any human editing or review by independent experts". [R]
- Dana Moshkovitz (a complexity theorist, and Aaronson's wife): her views come from private texts and comments that Aaronson posted on his blog, not from a formal review [R]. In the post body: "Basically the paper is so horribly written that it's impossible to read it without AI help"; in comment #2: "the writeup is poorly written". Her description of the method: "The UGC proof invents a completely new bizarre code with a noise test" (this is the new encoder and noise of step 3 in §7.8.3). Later, in comment #94, Aaronson wrote: "Dana tells me she now mostly understands the proof of the UGC". Secondhand retellings in outlets such as Implicator word this differently ⚠; go by the original on Aaronson's blog.
- Khot himself: as of 2026-10-08 I found no public statement ⚠.
- **As of 2026-10-08, no human expert has publicly said they have read through and verified these 58 pages.**

### 7.9.4 Remaining risks

1. **Statement level**: I read it line by line and found no problems, but I am not a complexity theory expert. The things most worth an expert's re-check are the use of `TM2ComputableInPolyTime` (whether the input and output encodings are reasonable, and whether the polynomial really is independent of the input), and whether the 3SAT encoding has a loophole that makes the problem easier.
2. **Compilation level**: depends on third parties or re-running it yourself. No nanoda re-check.
3. **Understanding level**: this is the same situation as the quasi-Riemann hypothesis (§4). It may already be proved in the machine sense, but nobody can explain "why that nonlinear noise works". The paper is very hard to read, which will slow down human understanding.

---

## 7.10 What it means if true (and what it doesn't)

### 7.10.1 For theoretical computer science

1. **A large batch of conditional results become theorems**: Max-Cut's 0.878, vertex cover's 2, Raghavendra's "SDP is optimal for every CSP", and so on. The premise is removed from the hundreds of papers of the past 20 years that say "assuming UGC, then…".
2. **The map of approximation algorithms is basically complete**: for many problems, the gap between "achievable" and "not achievable" is closed. The 1995 GW algorithm is proved optimal.
3. **The subexponential algorithm is no longer a counterexample**: UGC being true and ABS's exp(n^ε) algorithm coexist. This means the reduction from 3SAT to UG must produce an extremely large polynomial (the paper says the degree and constants of the polynomial depend only on ε, δ, but gives no concrete numbers).

### 7.10.2 What it does not mean

- **It does not resolve P vs NP.** Every conclusion is "X is NP-hard", i.e. "unless P = NP, X cannot be done". If someone proved P = NP tomorrow, all these hardness results would become void. Fortnow says in the same blog post that these results don't bring us closer to resolving P vs NP [R].
- **It does not affect practical engineering.** Industry uses heuristics for graph partitioning and clustering, and on real data they often do far better than the worst-case 0.878. UGC is about **guarantees** in the **worst case**.
- **It does not overturn any known algorithm.** It only proves that "existing algorithms can't be improved further".

### 7.10.3 For AI

- This is the result in OpenAI's batch **closest to AI researchers' daily work**: its core objects (SDP relaxations, randomized rounding, PCP-style verification) are basic tools of computer science.
- An association (**my speculation, not an established result**): the complexity-theoretic foundation of debate-style scalable oversight (Irving–Christiano–Amodei 2018, arXiv:1805.00899) is interactive proofs and PCP: "can a weak verifier, looking at only a little information, judge a strong prover's argument?" UGC characterizes the boundary where "a little noise makes efficient distinction impossible". For designing "weak overseer + strong model" protocols, it suggests there may be an essential computational-hardness difference between **perfect agreement** and **near agreement**.
- As with the quasi-Riemann hypothesis (§4), we again have the combination "a hard-to-read 58-page paper + 187,000 lines of Lean". The bottleneck of trust moves from "is the proof right" to "**was the statement encoded correctly**", which is exactly the spec review that §7.9.1 does.

---

## 7.11 Self-test

Try answering these after reading. If you can't, go back and reread the relevant section.

1. What exactly does "X is NP-hard" mean? Does it prove P ≠ NP? (§7.1.2)
2. Why is random coloring at least a 1/2-approximation? (§7.2.2)
3. In the GW algorithm, 0.878 is the minimum of the ratio of which two quantities, and where is it attained? (§7.3.3)
4. Why does the "gap" in the PCP theorem imply hardness of approximation? (§7.4.2)
5. Why can a fully satisfiable unique game be solved in polynomial time, while 3SAT can't? (§7.5.4)
6. Why does the order "first ε, δ, then the alphabet size" in UGC matter? (§7.5.6)
7. What has the 2-to-2 theorem already proved, and what was still missing? (§7.7.2)
8. What does the `soundness` field in the Lean statement say? What happens if the input string isn't a valid formula encoding at all? (§7.9.1)
9. Why might the optimality of Max-Cut 0.878 still hold even if the UGC paper has an error? (§7.8.2)

---

## Appendix: answers to the checks

- **Check 1**: A 4-cycle is bipartite; color it alternately black and white and all 4 edges are cut, so max cut = 4. A random coloring cuts 4 × 1/2 = 2 edges in expectation.
- **Check 2**: The first four constraints form the cycle x₀→x₁→x₂→x₃→x₀, with constant sum 2 + 3 + 1 + 4 = 10 ≡ 0 (mod 5), so no contradiction. The fifth, x₂ − x₀ ≡ 0: along the cycle, x₂ − x₀ = 2 + 3 = 5 ≡ 0 ✓. So everything can be satisfied, e.g. (x₀, x₁, x₂, x₃) = (0, 2, 0, 1). After changing it to x₂ − x₀ ≡ 1, the cycle x₀→x₁→x₂→x₀ sums to 2 + 3 − 1 = 4 ≢ 0, so at least one constraint is violated, and at most 4/5 can be satisfied (confirmed by the script by brute-force enumeration of all 625 labelings).

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| P / NP | Problems where you can quickly find the answer / problems where you can quickly check an answer |
| Reduction | Quickly translating problem A into problem B, so that a fast algorithm for B solves A |
| NP-hard | 3SAT reduces to it; unless P = NP, it has no polynomial-time algorithm |
| 3SAT | Boolean satisfiability with 3 variables per clause |
| Max-Cut | Split the vertices into two groups to maximize the edges crossing between groups |
| Vertex cover | Pick the fewest vertices that cover every edge |
| α-approximation | Always reaches α times the optimum in polynomial time |
| Semidefinite program (SDP) | An optimization problem that relaxes ±1 variables to unit vectors; solvable in polynomial time |
| Random hyperplane rounding | Make one random cut to turn vectors back into black and white |
| α_GW | 0.878567…, the guarantee of the GW algorithm |
| Integrality gap | The ratio gap between the relaxation's optimum and the true optimum |
| PCP theorem | Proofs can be rewritten in a form that can be verified by randomly spot-checking a constant number of bits |
| Gap | YES instances have value ≥ c, NO instances have value ≤ s, with c > s |
| Completeness / soundness | The fraction satisfiable in the YES case / the most that can be satisfied in the NO case |
| Label Cover | The standard output of the PCP theorem: a labeling problem with "many-to-one" constraints on each edge |
| Unique Game | A labeling problem where each edge constraint is a permutation (fix one end and the other is unique) |
| UGC | Telling apart unique games with value ≥ 1 − ε from those with value ≤ δ is NP-hard |
| 2-to-2 theorem | "Half of UGC" (completeness about 1/2), proved in 2018 |
| Subexponential time | Faster than any 2^(n^c) (for fixed c > 0), slower than polynomial |

## Appendix: Further reading

- **Ryan O'Donnell**, *Analysis of Boolean Functions* (Cambridge University Press, 2014; free online version https://analysisofbooleanfunctions.net/ ): Chapter 7 covers PCP and Håstad, Chapter 11 covers "Majority Is Stablest" and KKMO. The best textbook for understanding the UGC hardness proofs. ⚠ Chapter numbers from memory; go by the table of contents.
- **Williamson & Shmoys**, *The Design of Approximation Algorithms* (Cambridge, 2011; free PDF http://www.designofapproxalgs.com/ ): Chapter 6 covers the GW algorithm, Chapter 16 covers hardness of approximation and UGC. ⚠ Chapter numbers from memory.
- **Subhash Khot**, "On the Unique Games Conjecture" (survey, CCC 2010): a survey by the person who proposed it. https://cs.nyu.edu/~khot/papers/UGCSurvey.pdf
- **Erica Klarreich**, "Approximately Hard: The Unique Games Conjecture" (Simons Foundation, 2011): popular science for a general audience.
- **Quanta**, "As AI Closed In on 'Unique Games' Proof, Researchers Raced to Beat the Machines" (2026-10-07): https://www.quantamagazine.org/as-ai-closed-in-on-unique-games-proof-researchers-raced-to-beat-the-machines-20261007/
- **Lance Fortnow**, "Open No More" (2026-10-07): https://blog.computationalcomplexity.org/
- **Scott Aaronson**, "The Mathocalypse" (2026-10-07): https://scottaaronson.blog/?p=10169
- Classic original references: Goemans–Williamson, *JACM* 42 (1995); Håstad, *JACM* 48 (2001); Khot, STOC 2002; KKMO, *SICOMP* 37 (2007); Khot–Regev, *JCSS* 74 (2008); Raghavendra, STOC 2008; Arora–Barak–Steurer, FOCS 2010 / *JACM* 62 (2015); Khot–Minzer–Safra, FOCS 2018.
- Original paper: https://github.com/openai/math/blob/main/preprints/The-Unique-Games-Theorem-September-23-2026/paper.pdf
- Direct Max-Cut proof: https://github.com/openai/math/blob/main/preprints/A-Direct-Proof-of-Optimal-Max-Cut-Hardness-September-23-2026/paper.pdf
- Lean statement: https://github.com/openai/math/blob/main/lean/ComparatorChallenges/UniqueGamesTheorem.lean
