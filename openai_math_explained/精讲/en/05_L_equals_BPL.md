# Explainer 05: L = RL = BPL (in small-memory computation, randomness doesn't help)

> This is the "explained from zero" version of §8 of the deck in `notes/openai_math_explained/`. You only need these prerequisites: you know what log₂ is, you know the phrase "an algorithm's running time grows with the input size n", and you have seen matrix multiplication. Every new concept is explained before it is used.
> Every number in the text is either computed by script or has a source (scripts: `精讲/scripts/05_bpl_toy.py`, `05_bpl_spec.py`, implemented in numpy). The **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter. Tags: **[Established]** = a published, peer-reviewed result; **[OpenAI claim]** = a manuscript in the openai/math repository; **[Speculation]** = my own judgment; **⚠** = something I could not fully verify.
> Estimated reading time: 60–90 minutes. You can read it in three sittings: Sections 1–3 (memory complexity and randomness), Sections 4–6 (random walks, Reingold, the history of derandomization), Sections 7–9 (OpenAI's result, its verification status, and what it means).

---

## 0. The bottom line: the one thing this chapter explains

Picture a machine with tiny memory: it can read the input as much as it likes, but its working memory only holds **a few pointers**. If this machine can flip coins, can it solve more problems?

This chapter explains the following causal chain:

> The whole computation of a small-memory machine ⟺ a random walk on a "configuration graph" ⟺ acceptance probability = a sum of powers of a large matrix ⟹ derandomization = computing this probability accurately with very little memory ⟹ the difficulty is that the precision and the recursion depth needed to "compute it accurately" eat up the memory.

**L** is the set of problems that deterministic small-memory computation can solve. **BPL** is the set of problems solvable with "small memory + coin flips + a small allowed probability of error". Almost everyone believes L = BPL, but since 1999 the best unconditional result has only reached "BPL can be simulated deterministically with (log n)^1.5 memory". That has always been a factor of √log n away from log n.

OpenAI claims to have closed this gap completely: **L = RL = BPL**. Few people ever doubted the conclusion itself; the hard part is the proof. It comes with a Lean formalization, but as of 2026-10-08 no human expert has publicly said they have read and verified this 108-page paper.

After reading this chapter, you should be able to explain in your own words:
- why "O(log n) bits of memory" roughly equals "can store a constant number of pointers", and why such a machine must halt in polynomial time;
- why a random walk can solve undirected graph connectivity with tiny memory, and why the same method fails on directed graphs;
- why "seed length" is the central measure in this field, and what separates Nisan's log² n from the target log n;
- what OpenAI's result would mean if true, and what it does **not** mean (it does not mean P = BPP, and it does not mean L = NL).

---

## 1. Space complexity: memory is a resource

### 1.1 Time and space

There are two rulers for measuring an algorithm:
- **Time**: how many steps it takes.
- **Space**: the maximum number of bits of **working memory** it uses at any one moment.

There is a key convention here: **the input does not count toward space**. The input sits on a "read-only tape"; the machine can read it back and forth but cannot write to it. Only the "work tape" (read-write scratch paper) counts as space. This is what lets us talk about "memory smaller than the input".

The engineering analogy is **streaming plus random access**: the data sits on a big read-only disk, you can seek to any position and read it, but your local RAM is only a few dozen bytes.

### 1.2 Logarithmic space L: room for a constant number of pointers

**L** (logspace) = the problems that a deterministic machine can decide with O(log n) bits of working memory.

Why log n? Because a pointer that can point to any position in the input needs ⌈log₂ n⌉ bits. O(log n) bits means "a constant number of pointers or counters".

| Input length n | log₂ n (one pointer) | (log₂ n)^1.5 | (log₂ n)² |
|---|---|---|---|
| 10³ | 10 | 31 | 99 |
| 10⁶ | 20 | 89 | 397 |
| 10⁹ | 30 | 163 | 894 |
| 10¹² | 40 | 252 | 1,589 |

(Computed by script; the unit is bits.) With an input of 10⁹ bytes, L allows only tens to hundreds of bits of memory, about the size of a few registers. The (log n)² and (log n)^1.5 columns will come up again and again; they are the two milestones in the history of derandomization.

**[Check 1]** The input is a graph with 10⁹ vertices. How many bits does it take to store one vertex ID? How many bits in total, roughly, to store "current vertex + target vertex + a step counter (counting up to at most n³)"?

### 1.3 An important fact: a deterministic logspace machine must halt in polynomial time

The machine's complete state at a given moment is called its **configuration**: control state + the positions of all read/write heads + the contents of the work tape. The work tape has only c·log n bits, so it has at most 2^(c·log n) = n^c possible contents; the read head has n possible positions; the control state has a constant number of possibilities. So **the total number of configurations is polynomial in n**.

If a deterministic machine halts, it can never pass through the same configuration twice (otherwise it would loop forever). So its number of steps is at most the number of configurations, which means polynomial time.

**This fact that "the number of configurations is polynomial" is the cornerstone of the whole chapter.** Everything that follows can be seen as working on a polynomial-size "configuration graph".

---

## 2. What randomness can buy

### 2.1 Example: polynomial identity testing

You are given two polynomials written as formulas and asked whether they are identical. For example, (x+y)² and x² + 2xy + y².

You can settle this example by expanding by hand. The hard case is when the polynomial is written as a very compact formula or circuit that would have exponentially many terms once expanded (for example, an n×n determinant has n! terms when expanded). In that case no fast **deterministic** algorithm is known to this day. This is the **PIT problem** (polynomial identity testing). [Established]

The randomized algorithm is simple: **plug in a few random numbers and check whether the two sides are equal.**
- If the polynomials are identical, any input gives equal values.
- If they are not identical, the difference of the two sides is a nonzero polynomial, and it has few roots. The Schwartz–Zippel lemma says: if you pick values at random from a set of size |S|, the probability that a nonzero polynomial of degree d evaluates to 0 is ≤ d/|S|. [Established]

**Worked example**: the false "identity" (x+y)² = x² + y². The difference of the two sides is 2xy, a degree-2 polynomial. Pick x and y at random from {0, …, 99}: 10,000 combinations in total.

**[Check 2]** How many combinations make the two sides exactly equal (that is, "fool" the random test)?

Computed by script: 199, or 1.99%. The Schwartz–Zippel bound is d/|S| = 2/100 = 2%, which matches. With one random substitution, the chance of being fooled is under 2%; with 10 independent substitutions, it is under 2%¹⁰ ≈ 10⁻¹⁷.

### 2.2 P and BPP

- **P**: problems solvable in deterministic polynomial time.
- **BPP**: problems solvable in polynomial time + random bits, with error probability ≤ 1/3 on every input.

The number 1/3 does not matter, because you can **amplify**: run independently k times and take a majority vote.

| Repetitions k | Majority-vote error probability (single-run success 2/3) | Bits needed for the counter |
|---|---|---|
| 1 | 3.3 × 10⁻¹ | 1 |
| 11 | 1.2 × 10⁻¹ | 4 |
| 51 | 6.9 × 10⁻³ | 6 |
| 101 | 2.7 × 10⁻⁴ | 7 |
| 201 | 5.5 × 10⁻⁷ | 8 |

(Computed by script, summing binomial tails.) Note the last column: amplification only needs a counter, **so it works for small-memory machines too**. That is why it doesn't matter whether the definition of BPL uses a threshold of 2/3 or 0.51.

**The mainstream conjecture is P = BPP**, meaning randomness gives no fundamental advantage. The evidence is strong: Impagliazzo–Wigderson 1997 proved that as long as certain problems require exponential-size circuits (a widely believed "hardness assumption"), P = BPP. [Established] But proving P = BPP **unconditionally** is considered extremely hard: Kabanets–Impagliazzo 2004 proved that even just derandomizing PIT would imply certain circuit lower bounds that we currently have no idea how to prove. [Established]

This is the "hardness vs. randomness" framework: **derandomization and proving lower bounds are almost the same thing.** The time version is blocked by this wall. The space version has no known barrier of the same kind, which is why L = BPL has long been seen as "the derandomization conjecture most likely to be proved unconditionally".

---

## 3. RL and BPL: small memory + coin flips

### 3.1 Definitions

The machine gains one ability: at each step it can get a fresh fair coin. The constraints are:
- O(log n) bits of working memory;
- it halts in polynomial time for **all** coin sequences;
- **coins are single-use**: once read, a coin is gone. To use it again, the machine must store it on its work tape itself, and the work tape has only log n bits.

The last constraint is crucial. The time version, BPP, can store the random string and reread it as often as it likes; a small-memory machine cannot. It can only "use the coins as it flips them", like an online, single-pass stream.

Two ways of making errors:
- **RL** (one-sided error): when the answer is "no", it always rejects; when the answer is "yes", it accepts with probability at least 1/2.
- **BPL** (two-sided error): when the answer is "yes", it accepts with probability at least 2/3; when the answer is "no", it accepts with probability at most 1/3.

Known inclusions [Established]:

```
L ⊆ RL ⊆ BPL ⊆ L^{3/2} (Saks–Zhou 1999)
RL ⊆ NL ⊆ L² (Savitch 1970)
```

NL is "nondeterministic" logspace (the machine can "guess"). Reachability in directed graphs is the representative NL problem.

### 3.2 The whole computation = a random walk on a graph

Use the fact from Section 1.3: a randomized machine has polynomially many configurations on input x. Draw each configuration as a node; if flipping one coin can take configuration u to configuration v, draw an edge from u to v with weight 1/2.

So **the machine's run on x = a random walk on this configuration graph, starting from the start node**; **the acceptance probability = the probability that the walk reaches an "accept" configuration within the time limit**.

**Worked example**: a toy machine with only 3 states, flipping one coin per step:
- State 0: heads goes to 0, tails goes to 1
- State 1: heads goes to 2, tails goes to 0
- State 2: absorbing (stays at 2 forever); it represents "accept"

Write this as a transition matrix T, start from v = (1, 0, 0), and at each step compute v ← vT:

| Step | P(at 0) | P(at 1) | P(at 2) |
|---|---|---|---|
| 1 | 0.5 | 0.5 | 0 |
| 2 | 0.5 | 0.25 | 0.25 |
| 3 | 0.375 | 0.25 | 0.375 |
| 4 | 0.3125 | 0.1875 | 0.5 |

(Computed by script; it also enumerated all 2⁴ = 16 coin sequences, and exactly 8 of them reach state 2, matching the 0.5 from the matrix.)

**[Check 3]** By hand only, verify the distribution after step 2, (0.5, 0.25, 0.25).

This turns the problem into linear algebra: **acceptance probability = some powers of the transition matrix applied to the start vector.** The OpenAI paper starts the same way: it turns the machine into a matrix S, and the acceptance probability is one component of (I − S)⁻¹e, which is equivalent to Σⱼ Sʲe (Section 7.2).

### 3.3 Why "just compute it" is not in L

If it is just matrix powers, why not compute it deterministically? The problem is **memory**:
- The matrix is n^c × n^c. It cannot be stored, so each entry has to be computed on demand.
- When computing Tᵗ by "repeated squaring", each entry of Tᵗ depends on entries of T^(t/2), each entry of T^(t/2) depends on entries of T^(t/4), and so on. The recursion has log t ≈ O(log n) levels, and each level has to remember where it is (O(log n) bits), plus the bits of numerical precision.
- Total space ≈ levels × per level = O(log n) × O(log n) = **O(log² n)**.

This is the intuition behind Borodin–Cook–Pippenger 1983's result that "randomized logspace ⊆ deterministic log² space", and it has the same structure as the "recursion stack" in Savitch's theorem. [Established] **Forty years of work in this field have been about pushing down this "levels × per level".**

---

## 4. Undirected connectivity: the classic win for random walks

### 4.1 The problem

**USTCON** (undirected s-t connectivity): given an undirected graph and two vertices s and t, are they connected?

BFS/DFS makes this easy, but they need a "visited" array, which takes n bits. What do you do with only O(log n) bits?

### 4.2 The random walk algorithm (AKLLR 1979)

In 1979, Aleliunas, Karp, Lipton, Lovász and Rackoff gave a minimal algorithm [Established]:

```
v ← s
repeat N steps:
    if v = t, answer "connected"
    v ← a random neighbor of v
answer "not connected"
```

It only needs to remember "the current vertex v" and "a step counter": O(log n) bits. If s and t are not connected, it never reaches t, so it **never turns a "no" into a "yes"**; if they are connected, then for large enough N it reaches t with high probability. This is exactly the one-sided error form of RL.

The key bound they proved: on a connected graph, the expected number of steps for a random walk to visit every vertex (the **cover time**) is ≤ 2|E|(n−1), where |E| is the number of edges. Since |E| ≤ n², this is on the order of ≤ n³. Taking N = 4n³ and applying Markov's inequality pushes the failure probability below 1/2.

### 4.3 Measured by script

**Small example**: 6 vertices, edges 0–1, 0–2, 1–2, 2–3, 3–4, 4–5 (a triangle with a tail attached). Walk from 0 to 5.

One actual simulated trajectory (script, random seed 1):

```
0 1 0 2 0 2 1 2 3 4 3 2 1 0 2 1 0 2 1 0 1 2 0 1 0 1 2 3 2 1 0 1 2 1 0 2 0 1 2 1 0 2 3 2 0 2 0 2 3 4 3 4 5
```

It took 52 steps. It circled around the triangle for a long time, because from 2 it has only a 1/3 chance of heading into the tail, and once at 3 it has a 1/2 chance of going back.

Averaged over 20,000 simulations: about 29.1 steps from 0 to 5, and about 30.4 steps to cover the whole graph. The upper bound 2|E|(n−1) = 2·6·5 = 60; the measurements are within the bound.

**Hitting times on several kinds of graphs**:

| Graph | n | Measured / exact expected steps | Comparison |
|---|---|---|---|
| Path (from one end to the other) | 10 | 81.7 (simulated) | exact value (n−1)² = 81 |
| Path | 40 | 1,523.7 (simulated) | (n−1)² = 1,521 |
| "Lollipop" (complete graph on n/2 vertices + a tail of n/2 vertices) | 40 | 8,019 (solving a linear system, exact) | n³ = 64,000, ratio 0.125 |
| Lollipop | 80 | 64,039 (exact) | n³ = 512,000, ratio 0.125 |

(Computed by script.) The lollipop graph is the worst case for random walks: the walk spins around inside the complete graph, rarely enters the tail, and easily falls back out once it does. Brightwell–Winkler 1990 proved that the maximum hitting time on an n-vertex graph is about (4/27)n³ ≈ 0.148n³ (attained when the clique takes 2/3 of the vertices). [Established; ⚠ constant quoted from memory of the literature, not checked against the original] Our "half and half" version gives 0.125n³, the same order of magnitude. So **n³ steps are generally enough, and you basically can't do with fewer**.

### 4.4 Why the same method fails on directed graphs

Consider a directed graph with vertices 0, 1, …, n. From vertex i there are two edges: one to i+1 and one back to 0. The target is n.

A random walk from 0 must choose "forward" n times in a row to get there. The expected number of steps is 2^(n+1) − 2:

| n | Expected steps (exact, solving a linear system) |
|---|---|
| 5 | 62 |
| 10 | 2,046 |
| 20 | 2,097,150 |
| 30 | 2,147,483,646 |

(Computed by script; matches the formula exactly.) **Exponential.** So random walks cannot solve directed reachability. Directed reachability is NL-complete; whether it is in L (L = NL?) is still open, and it is **unrelated to this chapter's result**.

**[Check 4]** Compute this expected value by hand for n = 2. Hint: let hᵢ be the expected number of steps to reach n starting from i; hₙ = 0, and hᵢ = 1 + ½hᵢ₊₁ + ½h₀.

**Why undirected graphs are nice**: an undirected edge can be walked back along, so the random walk cannot get stuck in a "one-way trap". In linear-algebra terms, the transition matrix of an undirected graph is symmetric (after normalization), its eigenvalues are all real, and its "mixing" speed is controlled by the spectral gap, which is the star of Section 5.

---

## 5. Reingold 2005: undirected connectivity is in L (SL = L)

### 5.1 History

After AKLLR, people tried to remove the randomness from USTCON:
- Nisan–Szemerédi–Wigderson 1992: O(log^1.5 n) space [Established]
- Armoni–Ta-Shma–Wigderson–Zhou 2000: O(log^(4/3) n) space [Established]
- **Reingold 2005**: O(log n) space, i.e. USTCON ∈ L. [Established] STOC 2005, JACM 2008, Gödel Prize.

SL (symmetric logspace) is the class for which USTCON is complete, so this result is also written **SL = L**. It was a milestone in "removing the randomness from a specific problem", but only for one structure: undirected graphs.

### 5.2 Expanders: graphs that are "very well" connected

An **expander** is a graph with very small degree (each vertex has only a constant number of edges) that is nonetheless extremely well connected: any small set of vertices has many edges going out of it.

The measure is the **spectral gap**: the largest eigenvalue of the random-walk transition matrix is 1, the second largest is λ₂, and the gap = 1 − λ₂. The larger the gap, the faster the random walk "forgets" its starting point. Roughly, the number of steps needed to mix ∝ (log n) / gap.

| n | Gap of the cycle (degree 2) | 1/gap | Gap of a random 4-regular graph | 1/gap |
|---|---|---|---|---|
| 64 | 0.00482 | 208 | 0.162 | 6.2 |
| 256 | 0.00030 | 3,320 | 0.138 | 7.2 |
| 1024 | 0.00002 | 53,122 | 0.134 | 7.4 |

(Computed by script, eigenvalues via numpy; the random 4-regular graph is built as the union of two random permutations.) The cycle's gap falls to 0 like 1/n², while the random 4-regular graph's gap stays at a constant (the theoretical optimum is 1 − 2√3/4 ≈ 0.134, the Ramanujan bound, and the measurement is already right up against it).

**An expander has diameter only O(log n).** So if the graph is a constant-degree expander, you can **enumerate all paths of length O(log n)**: each step has only a constant number of choices, a path can be described in O(log n) bits, and there are d^O(log n) = polynomially many paths in total. A counter can try them one by one, with no randomness needed.

### 5.3 Reingold's idea: "rebuild" any graph into an expander

The difficulty is that the input graph is not necessarily an expander. Reingold repeatedly rebuilds it with two operations (each connected component is rebuilt separately):
1. **Squaring** (powering): in the new graph, two vertices are adjacent if and only if there is a path of length 2 between them in the original graph. The spectral gap roughly doubles (λ₂ becomes λ₂²), at the cost of squaring the degree.
2. **The zig-zag product** (Reingold–Vadhan–Wigderson 2000): "replace" each vertex with a small fixed expander, which brings the degree back down to a constant while losing only a constant factor in the gap. [Established]

Alternating these for O(log n) rounds grows the gap from 1/poly(n) to a constant.

**Why it doesn't eat memory**: the rebuilt graph is **never stored explicitly**. To look up "the i-th neighbor of vertex v in the new graph", you recursively send queries to the graph one level up. The key is that the zig-zag design makes each level cost only a **constant** number of extra bits (rather than log n bits). O(log n) levels × O(1) bits = O(log n).

Compare with Section 3.3: in "levels × per level", Reingold pushed "per level" from log n down to a constant. Engineering analogy: multi-level virtual address translation where each level only has to remember an offset of a few bits rather than a full address.

**Limitation**: both zig-zag and squaring rely on the graph's symmetry (undirectedness). The configuration graph of a general BPL computation is directed. Reingold–Trevisan–Vadhan 2006 extended the approach to special cases such as "regular directed graphs", but did not cover the general case. [Established]

---

## 6. Derandomizing general BPL: stuck at 3/2 for 25 years

### 6.1 Pseudorandom generators and "seed length"

The most naive way to derandomize: **try every random string and count the fraction that accept.** A BPL machine reads poly(n) random bits, so there are 2^poly(n) random strings. Far too many.

The idea of a **pseudorandom generator** (PRG): use a short **seed** to generate a long string of bits that "looks random". "Looks random" is relative to some class of observers: for any small-memory machine, the acceptance probability with the pseudorandom string is almost the same as with a truly random string.

Given a PRG with seed length s, derandomization is: enumerate all 2^s seeds, run once on each, and tally. The space needed is about s + O(log n).

| Seed length | Number of seeds to enumerate | Derandomization result |
|---|---|---|
| poly(n) (truly random) | 2^poly(n) | useless |
| O(log² n) (Nisan 1992) | n^O(log n) (quasi-polynomial) | BPL ⊆ L² |
| O(log n) (the dream) | poly(n) | L = BPL |

So **the whole problem boils down to: for small-memory machines, can we build a PRG with seed length O(log n)?** This question went unsolved for more than 30 years.

### 6.2 Nisan's generator (1992): why log²

Nisan's core observation: **a small-memory machine cannot remember which random bits it has used, so they can be safely "reused".** [Established]

The construction (simplified):
- Seed = a random string x of O(log n) bits, plus k random hash functions h₁, …, h_k, each of O(log n) bits.
- Level 1: output x, h₁(x).
- Level 2: output x, h₁(x), h₂(x), h₂(h₁(x)).
- Each added level doubles the output length.

Intuition: after the machine has read the first half, its state is only O(log n) bits, so it has almost "forgotten" the specific contents of the first half. So the second half can be replaced by "the first half passed through a hash", and the machine can't tell.

To output poly(n) bits takes k = O(log n) levels, each with an O(log n)-bit hash function, so the total seed length is O(log n) × O(log n) = **O(log² n)**. "Levels × per level" again.

Nisan 1994 then proved that this simulation can achieve polynomial time and O(log² n) space at the same time (BPL ⊆ SC). [Established] (Note: Borodin–Cook–Pippenger 1983 had already obtained log² space with the matrix method, but not polynomial time.)

### 6.3 Saks–Zhou 1999: 3/2

Saks and Zhou cut Nisan's log n levels into √log n segments of √log n levels each. Each segment uses Nisan's method to approximately compute a matrix power, and then the low-order bits of the result are **randomly rounded** away. This makes each segment's result almost independent of which particular hash functions were used, so **all segments can share the same set of hash functions**. [Established; this description is heavily simplified, ⚠ see the original for details]

Space: one set of hash functions, √log n × log n, plus the recursion, √log n segments × log n per segment, for a total of **O(log^1.5 n)**.

### 6.4 Later progress, and the stall

| Year | Result | Deterministic space |
|---|---|---|
| 1983 | Borodin–Cook–Pippenger | log² n |
| 1992 | Nisan PRG | log² n |
| 1999 | Saks–Zhou | log^1.5 n |
| 2021 | Hoza (weighted pseudorandomness) | log^1.5 n / √(log log n) |
| 2026 | **OpenAI (claimed)** | **log n** |

(The Hoza bound is based on [19, Theorem 1.6 and Corollary A.5] as cited in §1.1 of the OpenAI paper, and on my memory; the deck author's research notes originally flagged it ⚠, and this time I checked it against the paper's citation; the two agree.)

Hoza 2021 saved only a factor of √(log log n), which for n = 10⁹ is only about 2.2×. The exponent for general BPL has been stuck near 3/2 for 27 years.

**Along the way there were many wins on "special structures"**: Reingold (undirected graphs), Reingold–Trevisan–Vadhan (regular directed graphs), Ahmadinejad et al. (computing random-walk probabilities to high precision on Eulerian graphs), Cohen–Doron–Sberlo–Ta-Shma (long products of random matrices). [Established] In addition, Cheng–Hoza 2022 proved that a logspace-enumerable "hitting set" (which only guarantees finding one accepted input, and is weaker than a PRG) is enough to imply L = BPL. [Established] All of this shows that the "shape" of the problem had been mapped out very clearly; only the last step was missing.

---

## 7. What OpenAI claims

### 7.1 The main result

The paper is *Exact Derandomization of Logarithmic Space: L = RL = BPL* (2026-09-23, 108 pages, authorship credited to "OpenAI"). The abstract is a single sentence:

> "We prove L = RL = BPL, resolving the derandomization problem for polynomial-time randomized logarithmic space."

In plain words: every randomized computation that is "polynomial time + logarithmic space + bounded error probability" can be simulated in deterministic logarithmic space.

The paper also gives a **stronger quantitative version** (Theorem 1.2): for any such randomized machine M and input x, the acceptance probability can be estimated deterministically to precision 2^(−q), using O(log n + q) space and poly(n)·2^O(q) time. When q = O(log n), this means precision of any inverse polynomial can be computed in logarithmic space. This is much stronger than "deciding whether the probability is above 2/3 or below 1/3": it can even estimate probabilities that have "no gap".

In addition, Section 13 gives a **compiler**: given the source program of a randomized machine and its time/space bounds, it outputs a deterministic decider together with explicit resource bounds.

### 7.2 Intuition for the method (I only read the introduction, §1–§2; what follows is a simplified version)

1. **Turn it into matrix inversion** (§2). Write the configuration graph of the machine on input x as a matrix S (each configuration carries a timestamp, and edges only point to later times, so S is "strictly forward" and nilpotent). The acceptance probability is p₀ = the value of (I − S)⁻¹e at the start node, where e marks the accepting configurations. This is the same thing as the toy example in Section 3.2.
2. **"Correction and copy hierarchy"** (§4). The authors use a sequence of transformations to replace S with new matrices C₁, C₂, …. Each step "moves" part of the transition probability into a reward vector (using the identity I − D = (I + E)(I − C)), and copies some vertices to spread out large matrix entries. After O(log n) stages, reading off the accumulated reward along a single "main copy" path gives the acceptance probability with inverse-polynomial error.
3. **Estimate using only O(log n) random bits** (§5–§9). These matrices are not stored explicitly; instead they are estimated by sampling with a **shared finite random environment** σ (an encoding of length O(log n)). The paper proves that on more than 3/4 of the σ's, the estimate is accurate; and for **every** σ (including the ones where the estimate is inaccurate), the estimation procedure halts within O(log n) space.
4. **Enumerate + take the median** (§12). σ has only O(log n) bits, so there are only polynomially many σ's in total. Enumerate them one by one, take the median, and compare it with 1/2. This step is the "enumerate the seeds" idea from Section 6.1, except that instead of building a general-purpose PRG, it squeezes the randomness down to O(log n) bits for this one specific estimator.
5. **Keep the recursion from eating memory** (§9–§11). Use short **fingerprints** (polynomial evaluation + affine hashing) instead of full vertex addresses for comparisons; use a shared "catalytic" bit vector; use Cook–McKenzie's "walk around the tree's contour" trick to recover incoming edges without a stack. The data kept by each recursive call is held within A(w − w′) + D(t − j) bits, and this **telescopes** along the call chain, for a total of O(log n).

Compare step 5 with Sections 3.3 and 5.3: it is still a "levels × per level" problem, and the solution is to tie the number of bits each level spends to "how much the recursion budget drops", so the whole call chain adds up to no more than one O(log n) total budget. Engineering analogy: a recursive call stack in which the size of each frame is bounded by a global quota, and the quota shrinks as you go down the stack.

**Two details that surprised me**:
- The mixing bound for "conditional averaging" in §6 relies on a result of Shalom 1999 about **Kazhdan's property (T)** (a deep property from group theory). [OpenAI claim] Group-theoretic tools showing up in small-memory derandomization is uncommon in the existing literature. [Speculation]
- The "shared catalytic bit vector" is reminiscent of recent work on **catalytic computing**: borrow a piece of memory that is already full of data, use it, and give it back exactly as it was. Cook–Mertz used it to bring the space for the tree evaluation problem down to O(log n · log log n), and Ryan Williams 2025 built on this to prove that "a computation running in time t can be simulated in about √(t log t) space". [Established] If OpenAI's proof holds, catalytic tricks may once again be a key component. [Speculation, ⚠ I did not read the details of §11]

---

## 8. How far it has been verified

### 8.1 The Lean statement: you can read it yourself

The last line of `lean/ComparatorChallenges/LogspaceEquality.lean` is:

```lean
theorem exact_logarithmic_space_derandomization :
    L = RL ∧ RL = BPL
```

Word-by-word translation:
- `L = RL ∧ RL = BPL`: L equals RL, **and** RL equals BPL.

This line is very short; the real content is all in the **definitions**. Unlike the quasi-Riemann hypothesis, the L, RL and BPL here are **not** standard Mathlib definitions (Mathlib has no such complexity classes). OpenAI wrote them itself in the challenge file. So the definitions are what need reviewing. Here is what I found, reading them one by one:

| Definition | What it says | Matches the textbook? |
|---|---|---|
| `Machine q w h` | A finite-state machine with h read-only input heads and w binary work tapes; reads one coin b per step | Yes, a standard multi-tape Turing machine |
| `readInput` | The input has end markers at both ends | Yes |
| `step` | A configuration that has already produced output (halted) no longer changes | Yes |
| `spaceThrough` | Up to time t, the sum over work tapes of the **number of distinct cells visited** | Yes, and fairly strict (blank cells that were visited also count) |
| `LogSpace` | There exists c > 0 such that for **all** inputs, **all** coin sequences and **all** times, space ≤ c·⌈log₂(n+2)⌉ | Yes |
| `Deterministic` | The transition function does not depend on the coin | Yes |
| `acceptanceProbability` | At clock time t, the fraction of the 2^t coin strings that stop in "accept" | Yes |
| `L` | Deterministic + logspace + gives the correct answer at some time on every input | Yes (no time bound is written, but Section 1.3 shows that a halting deterministic logspace machine is automatically polynomial-time) |
| `RL` | Logspace + halts within c·(n+2)^k steps for **all** coin sequences + if yes, probability ≥ 1/2, otherwise probability = 0 | Yes |
| `BPL` | Same as above, with thresholds 2/3 and 1/3 | Yes |

**My judgment: they match the standard definitions.** One choice worth noting is "halts in polynomial time for all coin sequences". This is standard BPL; if you drop the time bound you get a different class (§1.1 of the paper also specifically stresses the difference between a "space bound" and "simultaneous time and space bounds"). This agrees with the conclusion in the author's research notes.

### 8.2 The Comparator configuration

`LogspaceEquality.json` locks **20 definitions** (from `Word` to `BPL`; I counted), which means the solution file cannot quietly swap out any of them. The only allowed axioms are Lean's three standard axioms (`propext`, `Quot.sound`, `Classical.choice`).

**Note**: this configuration has `"enable_nanoda": false`, meaning there is **no requirement for re-checking by a second, independent kernel**. (Only 2 of the 416 configurations in the whole repository turn on nanoda; this is from the author's count over all configurations in the repository.)

### 8.3 The proof itself (what I found)

- Solution directory `lean/OAI/Computability/Logspace/`: **39 files, about 43,000 lines** (commit fd4aeeb, counted by script with `wc -l`).
- grep for `sorry | axiom | admit | native_decide | implemented_by | unsafe`: **0 hits**.
- Apart from Mathlib, it imports nothing from other `OAI.*` directories in the repository. So there is no "custom code hidden in a dependency library" problem; in this respect it is cleaner than the quasi-Riemann hypothesis.
- The top-level proof is only three lines: `L ⊆ RL` (trivial), `RL ⊆ BPL` (trivial, amplify a bit), `BPL ⊆ L` (all the difficulty is here).
- **What I didn't do**: I did not compile it, and I did not run Comparator. ⚠ **I found no public record of any third party rerunning Comparator on this family** (the quasi-Riemann hypothesis had an independent re-check by Goldblatt; this family has none).
- The paper's **compiler** and **explicit running-time bounds** are not in the Lean statement. The scope document `lean/docs/103.md` says verbatim: "The paper's explicit compiler and numerical running-time bounds are not separately stated in this Comparator target." Theorem 1.2 (arbitrary-precision estimation) is not formalized either.

### 8.4 Human experts (as of 2026-10-08)

- **Scott Aaronson** (blog post "The Mathocalypse", 2026-10-07): "L=BPL (i.e., probabilistic logspace and deterministic logspace are the same thing), one of the great derandomization conjectures short of P=BPP." He also said: "its truth was never in serious doubt, there was a whole subcommunity focused on proving this." [R]
- **Lance Fortnow** (blog post "Open No More", 2026-10-07) lists it as "A full derandomization of randomized log space", and says: "And none of these results get us any closer to settling P v NP." [R]
- **Ran Raz** (Princeton, as reported by *Scientific American* on 2026-10-08): "We have strong reasons to believe that, but we don't know how to prove it", and, earlier, "I didn't see any directions that were promising". [R, ⚠ the quotes were relayed through a web-fetch tool; check the original for context (whether he meant L = BPL itself or derandomization more generally)]
- **No human expert has publicly said they have read and verified the 108 pages.** Aaronson's comment on the whole batch of results: "it also appears that no human has understood just about any of these proofs yet." [R]

### 8.5 An inconsistency worth flagging

⚠ Fortnow's "OpenAI Math: TCS Selection" page (lance.fortnow.com, dated 10-07) **shows no Lean marker** for number 103, while the repository at commit fd4aeeb (10-07 22:20 PT) contains the full Lean challenge and solution. history.md says 6 formalizations were "added" on 10-07, so one possible explanation is that 103's Lean was added that day and Fortnow's page was based on an earlier snapshot. I could not confirm which 6 they were (the repository has only one merge commit, so per-file history is not visible). This judgment is based only on a web-fetch tool's summary; I did not see the page myself.

### 8.6 How to think about the trust structure here

Compared with the quasi-Riemann hypothesis: **the definitions are self-written**, but they are only 142 lines, and I read them one by one and they match the standard; **the proof is self-contained** (it depends only on Mathlib), with no large-scale patches; **the conclusion is widely believed**, so "the conclusion is right" cannot be turned around into evidence that "the proof is right". Nearly all the credibility rests on the Lean kernel and on "whether anyone has actually compiled it successfully" (⚠ no third-party report yet).

---

## 9. What it would mean if true (and what it would not)

### 9.1 For complexity theory

1. **The first natural computational resource class to be "fully derandomized" unconditionally.** Within "logarithmic space + polynomial time", flipping coins is of no use at all. This answers a question stated explicitly back in AKLLR 1979.
2. **It does not imply P = BPP.** The time version is blocked by the "derandomization ⇒ circuit lower bounds" wall (Section 2.2). The proof of the space version goes around that wall but does not tear it down. A deterministic polynomial-time algorithm for PIT is still unknown.
3. **It does not imply L = NL, and it is even further from P vs NP.** It is still unknown whether directed reachability (Section 4.4) can be solved in logarithmic space. The new picture of inclusions is:

```
L = RL = BPL ⊆ NL ⊆ L²
```

4. **Theorem 1.2 may be more useful than 1.1.** Being able to estimate random-walk probabilities to high precision in logarithmic space means that many small-space linear algebra problems (for example, Laplacian solving, or stationary distributions of Markov chains) may get new deterministic algorithms. [Speculation]
5. **The technique may matter more than the conclusion.** Aaronson says the conclusion was "never in serious doubt", so what the field really wants is the **proof method**. Unfortunately, nobody understands it yet. If the proof holds but nobody can extract reusable ideas from it, that would be a very strange situation: the problem is closed, but the field learned nothing. [Speculation]

### 9.2 For engineering

Almost no direct impact on real systems: the randomized algorithms used in practice (hashing, sampling, Bloom filters) are already fast enough, and most of them are not in the extreme "logarithmic space" setting anyway. The theorem only guarantees that a deterministic replacement algorithm **exists**; the polynomial's degree and constants are likely astronomical. [Speculation] The implications for streaming algorithms are also limited: the streaming model can read the input only in a single pass, while L allows repeated reads.

### 9.3 For AI

- Like the other headline results, this is a case of "AI produces a proof of a recognized hard open problem, with a machine check attached".
- What sets it apart is that **everyone believes the conclusion; the hard part is the proof**. Problems of this kind may suit AI especially well: the direction is clear, there's no need to "guess the right conclusion", and what's needed is to get every step of a 108-page complex construction right, which Lean can check step by step. [Speculation]
- The lesson for AI safety research is the same as in §16 of this deck: once you have Lean, the bottleneck of trust moves from "is the proof right?" to "**were the statement and definitions written correctly?**" This family's definitions are self-written, so the table in Section 8.1 is a spec review. It is the same kind of work as auditing the behavioral spec of an AI agent.

---

## 10. Self-test

Try answering these after reading. If you can't, go back and reread the corresponding section.

1. Why does "O(log n) bits of working memory" roughly equal "can store a constant number of pointers"? Why must such a deterministic machine halt in polynomial time? (Sections 1.2, 1.3)
2. What is the difference between RL and BPL? Why does the restriction "once a coin is read, it's gone" matter? (Section 3.1)
3. Why does the random walk algorithm work on undirected graphs and fail on directed graphs? Give a number for each. (Sections 4.3–4.4)
4. In Reingold's algorithm, what are "levels" and "per level" in "levels × per level"? How does this differ from "levels × per level" in Nisan's generator? (Sections 5.3, 6.2)
5. Why is "a PRG with seed length O(log n)" enough to imply L = BPL? (Section 6.1)
6. In OpenAI's Lean statement, who defined L, RL and BPL? How is this different from the quasi-Riemann hypothesis case? Why does it matter? (Section 8.1)
7. Why does L = BPL not imply P = BPP? (Sections 2.2, 9.1)

---

## Appendix: answers to the checks

- **Check 1**: ⌈log₂ 10⁹⌉ = 30 bits. Current vertex 30 + target vertex 30 + counter (n³ = 10²⁷, needing ⌈log₂ 10²⁷⌉ = 90 bits) = 150 bits, less than 20 bytes.
- **Check 2**: the two sides are equal ⇔ 2xy = 0 ⇔ x = 0 or y = 0. There are 100 combinations with x = 0 and 100 with y = 0; (0, 0) is counted twice, so there are 199 in total (checked by script).
- **Check 3**: after step 1 the distribution is (0.5, 0.5, 0). Step 2: of state 0's 0.5, half stays at 0 and half goes to 1; of state 1's 0.5, half goes to 2 and half goes back to 0. So P(0) = 0.25 + 0.25 = 0.5, P(1) = 0.25, P(2) = 0.25.
- **Check 4**: h₂ = 0; h₁ = 1 + ½·0 + ½h₀; h₀ = 1 + ½h₁ + ½h₀, i.e. h₀ = 2 + h₁. Substituting gives h₁ = 1 + ½(2 + h₁) = 2 + ½h₁, so h₁ = 4 and h₀ = 6 = 2³ − 2.

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| Space complexity | The maximum number of bits of working memory used at any one moment (the input doesn't count) |
| L | Problems decidable deterministically with O(log n) bits of working memory |
| NL | Nondeterministic logspace; directed reachability is its representative problem |
| RL | Logspace + polynomial time + coins, one-sided error ("no" is never accepted) |
| BPL | Logspace + polynomial time + coins, two-sided error (≥ 2/3 vs ≤ 1/3) |
| BPP | Polynomial time + coins, two-sided error |
| Configuration | The machine's complete state at a given moment; a logspace machine has only polynomially many configurations |
| PIT | Polynomial identity testing; has a simple randomized algorithm, but no known deterministic polynomial-time algorithm |
| USTCON | Undirected s-t connectivity |
| Cover time | The expected number of steps for a random walk to visit every vertex |
| Expander | A graph with small degree but excellent connectivity; its spectral gap is a constant |
| Spectral gap | 1 − λ₂; measures how fast a random walk "forgets its starting point" |
| Zig-zag product | A graph operation that reduces a high-degree expander to constant degree while mostly preserving the gap |
| Pseudorandom generator (PRG) | Stretches a short seed into a bit string that "looks random to a certain class of observers" |
| Seed length | The number of truly random bits a PRG needs; O(log n) means the seeds can be enumerated |
| Derandomization | Turning a randomized algorithm into a deterministic one |
| Hardness vs. randomness | A family of theorems of the form "hard functions exist" ⇒ "derandomization is possible" |
| Catalytic computing | Computing with borrowed memory that is already full, and returning it exactly as it was |
| Comparator | A Lean FRO tool that checks that a solution proves exactly the statement in the challenge file, using only allowed axioms |

## Appendix: Further reading

- **Sanjeev Arora & Boaz Barak**, *Computational Complexity: A Modern Approach* (Cambridge University Press, 2009): Chapter 4 (space complexity), Chapter 7 (randomized computation), Chapter 21 (expanders and Reingold's algorithm). Free draft: https://theory.cs.princeton.edu/complexity/
- **Salil Vadhan**, *Pseudorandomness* (Foundations and Trends in TCS, 2012): Chapter 2 (random walks and USTCON), Chapter 4 (expanders), Chapters 7–8 (PRGs). Free: https://people.seas.harvard.edu/~salil/pseudorandomness/
- **William Hoza**, *Recent Progress on Derandomizing Space-Bounded Computation* (BEATCS survey, 2022): the best introductory survey of the current state of the L vs BPL field. ⚠ Please search for and confirm the link yourself.
- Original literature: AKLLR, FOCS 1979; Nisan, *Combinatorica* 12(4), 1992; Saks & Zhou, *JCSS* 58(2), 1999; Reingold, *JACM* 55(4), 2008; Hoza, APPROX/RANDOM 2021, LIPIcs 207:28.
- The original paper: https://github.com/openai/math/blob/main/preprints/Exact-Derandomization-of-Logarithmic-Space-L-equals-RL-equals-BPL-September-23-2026/paper.pdf
- Lean statement: https://github.com/openai/math/blob/main/lean/ComparatorChallenges/LogspaceEquality.lean ; scope: `lean/docs/103.md`
- Reactions: Aaronson https://scottaaronson.blog/?p=10169 ; Fortnow https://blog.computationalcomplexity.org/2026/10/open-no-more.html ; Fortnow's selection page https://lance.fortnow.com/openai-math-tcs.htm ; *Scientific American* https://www.scientificamerican.com/article/the-most-exciting-claims-from-openais-heap-of-new-proofs/
