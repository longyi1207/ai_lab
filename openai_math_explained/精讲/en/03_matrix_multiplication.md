# How fast can matrices be multiplied? ω ≤ 9/4

> You only need to know matrix multiplication, how to take a logarithm (things like log₂ 8 = 3), and what "complexity O(n³)" means. New ideas such as tensors, rank and "tensor characters" are all explained before they are used.
> Every number here is either computed by script (script: `精讲/scripts/03_matmul.py`, with symbolic checks in sympy) or has a source. **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter. ⚠ = I could not fully verify this.
> Estimated reading time: 60–90 minutes. You can split it into three sittings: §6.1–6.3 (Strassen and ω), §6.4–6.7 (tensors, approximation, the asymptotic spectrum), §6.8–6.10 (OpenAI's result and what it means).
> One difference from the quasi-Riemann hypothesis (§4): this paper is **only 13 pages, and I read all of it** (not just the introduction). So §6.8 can lay out the full skeleton of the proof.

---

## 6.0 The bottom line: the one thing this chapter explains

Multiplying two n×n matrices the textbook way takes n³ multiplications. In 1969 Strassen found that you can do it with fewer. Ever since, theoretical computer science has been asking: **what is the smallest power of n you need?** That power is called **ω** (the matrix multiplication exponent).

This chapter explains one chain of cause and effect:

> How small ω is ⟸ how fast the rank of the matrix multiplication "tensor" grows with n ⟸ (Strassen's duality theorem) how large every "tensor character" is on matrix multiplication ⟸ OpenAI: using a simpler tensor, **polynomial multiplication**, they pinned down the value of every character.

Result: ω ≤ 9/4 = 2.25. The previous best human result was about 2.3712 (2026-08), and for 35 years progress had only moved the third decimal place.

After this chapter you should be able to explain in your own words:
- why "one fewer multiplication for 2×2" can rewrite the whole n³;
- what ω means exactly, and why it is the same thing as "the rank of a tensor";
- roughly what steps OpenAI's 13-page proof takes, and why it is not the same road as the "laser method" of the past 35 years;
- why this result **gives no direct speedup at all to GPUs or LLM training**.

---

## 6.1 Matrix multiplication: counting the multiplications

### 6.1.1 The textbook algorithm

C = A·B. Each entry of C is a row times a column:

```
c_ij = a_i1·b_1j + a_i2·b_2j + … + a_in·b_nj
```

C has n² entries, and each takes n multiplications and n−1 additions. In total: **n³ multiplications + (n³ − n²) additions**. For 2×2: 8 multiplications, 4 additions.

### 6.1.2 Why theorists only count "multiplications"

You may find this odd: additions also take time, so why count only multiplications? The reason is recursion (you'll see it in §6.2 shortly). When a and b are themselves matrix blocks, "adding blocks" takes only (n/2)² operations, while "multiplying blocks" has to recurse, which costs far more. **In a recursion, the number of multiplications sets the exponent; additions only affect the constant.**

### 6.1.3 How this connects to your daily work

Most of the FLOPs in LLM training are GEMMs (general matrix multiplies). The GEMMs in cuBLAS and CUTLASS use the n³ algorithm, just cut into small tiles that fit Tensor Cores and shared memory (tiling). That will still be true at the end of this chapter; §6.10.2 explains why.

---

## 6.2 Strassen 1969: 7 is enough

### 6.2.1 Seven products

Let A = [[a,b],[c,d]] and B = [[e,f],[g,h]]. Use only 7 multiplications:

```
M1=(a+d)(e+h)   M2=(c+d)e   M3=a(f−h)   M4=d(g−e)
M5=(a+b)h       M6=(c−a)(e+f)           M7=(b−d)(g+h)

C11 = M1+M4−M5+M7    C12 = M3+M5
C21 = M2+M4          C22 = M1−M2+M3+M6
```

Check C12: M3 + M5 = af − ah + ah + bh = af + bh ✓. (The script expanded all four entries with sympy and checked them; all four are correct.)

**[Check 1]** Verify by hand that C21 = M2 + M4 = ce + dg.

The cost: multiplications go down from 8 to 7, but additions/subtractions go up from 4 to 18. Doesn't look like a good deal, does it?

### 6.2.2 The key: the formulas never use ab = ba

Notice that in these 7 products, every multiplication has "only entries of A on the left, only entries of B on the right", and the order of multiplication is never swapped. So a…h can **themselves be matrix blocks** (matrix multiplication is not commutative, but we never need it to be). So:

- cut the n×n matrix into 4 blocks of size (n/2)×(n/2);
- do 7 "block multiplications" (each one a recursive call) + 18 "block additions";
- recurrence: T(n) = 7·T(n/2) + 18·(n/2)².

Unroll the recursion: at each level down, the number of multiplications goes ×7 and the size goes ÷2. There are log₂ n levels, so the total number of multiplications = 7^(log₂ n) = n^(log₂ 7).

```
log₂ 7 = 2.807354… (computed by script)
```

**The one saved multiplication compounds at every level of the recursion.** The table below compares exact counts for n = 2^k, recursing all the way down to 1×1:

| n | Naive multiplications n³ | Strassen multiplications 7^k | Ratio | Naive total ops | Strassen total ops (incl. 18 block additions) | Ratio |
|---|---|---|---|---|---|---|
| 2 | 8 | 7 | 0.875 | 12 | 25 | 2.08 |
| 16 | 4,096 | 2,401 | 0.586 | 7,936 | 15,271 | 1.92 |
| 128 | 2,097,152 | 823,543 | 0.393 | 4,177,920 | 5,666,497 | 1.36 |
| 1024 | 1,073,741,824 | 282,475,249 | 0.263 | 2,146,435,072 | 1,971,035,287 | **0.918** |
| 4096 | 6.87×10¹⁰ | 1.38×10¹⁰ | 0.201 | 1.37×10¹¹ | 9.68×10¹⁰ | 0.704 |

(Computed by script.) Two things are worth noticing:
1. Counting only multiplications, Strassen wins right away. Counting additions too, **it only starts winning at n = 1024** (if you recurse all the way to 1×1). Real implementations switch to the naive algorithm once blocks get small enough (say 64), which moves the crossover earlier. But the pattern "asymptotically faster ≠ faster at small sizes" will come up again and again in this chapter.
2. This is only the operation count. Real hardware also has memory traffic and numerical stability; more on that in §6.10.2.

---

## 6.3 ω: the matrix multiplication exponent

### 6.3.1 Definition

**ω** = the infimum of all τ such that, for every ε > 0, n×n matrix multiplication can be done with O(n^(τ+ε)) arithmetic operations (+, −, ×).

Unpacking this:
- "Infimum": ω itself might not be achievable, but you can get arbitrarily close to it.
- "+ε": allows a tiny bit of slack. That way something like n²·log n still counts as exponent 2.
- The constant inside O(…) **can grow arbitrarily large as ε shrinks**. This is the root of the "galactic algorithms" in §6.10.
- The computation is exact, over the complex numbers (or any fixed field). Floating-point error and the bit length of numbers are ignored.

### 6.3.2 Why 2 ≤ ω ≤ 3

- **ω ≤ 3**: the textbook algorithm.
- **ω ≥ 2**: the output has n² numbers, and each has to be computed at least once. (Reading in the 2n² inputs also takes that many steps.)
- Strassen proved ω ≤ 2.807.

**The mainstream conjecture: ω = 2.** That is, matrix multiplication can be almost as fast as "reading the data once". Nobody can prove it, and nobody can prove ω > 2 either.

### 6.3.3 Why it matters

For many basic problems, the best known algorithm's complexity can be written directly as n^ω: solving linear systems, matrix inversion, determinants, LU decomposition, transitive closure of a graph, maximum matching in bipartite graphs, and more [P] (standard results; see the Bürgisser–Clausen–Shokrollahi textbook in "Further reading"). Linear-programming solvers are on the list too: the interior-point method of Cohen–Lee–Song (*Solving Linear Programs in the Current Matrix Multiplication Time*, STOC 2019, arXiv:1810.07896) solves a linear program with n variables in about n^ω time at the current ω (ignoring log factors) [P]. When ω goes down, their theoretical complexity goes down with it.

---

## 6.4 Tensors: turning "an algorithm" into "a number"

This section is the foundation of the whole chapter. It replaces the task of "designing an algorithm" with the task of "finding the rank of a three-dimensional array".

### 6.4.1 Starting from the rank of a matrix

The rank of a matrix = the smallest number of "outer products" (column vector × row vector) it can be written as a sum of. For example, [[1,2],[2,4]] = [1,2]ᵀ·[1,2], which has rank 1.

### 6.4.2 The matrix multiplication tensor

Write matrix multiplication as a big "polynomial" in three groups of variables (a trilinear form):

```
T_n = Σ_{i,j,k} x_ij · y_jk · z_ki
```

x stands for the entries of A, y for the entries of B, and z is a placeholder for "position (i,k) of C". The expression means: "entry (i,j) of A times entry (j,k) of B contributes to position (i,k) of C." Arrange the coefficients into a three-dimensional array and you have a **tensor** (think of it as a three-dimensional matrix). Its three groups of variables x, y, z are called its three **legs**.

For 2×2, T₂ has 2³ = 8 terms, matching the 8 multiplications of the textbook algorithm.

### 6.4.3 Tensor rank = the minimum number of multiplications

The **rank of a tensor R(T)** = the smallest number of "rank-1 terms" it can be written as a sum of, where each rank-1 term looks like:

```
(some linear combination of x) · (some linear combination of y) · (some linear combination of z)
```

Compare with Strassen's M1 = (a+d)(e+h): the first two brackets are exactly "a linear combination of x" and "a linear combination of y", and the third bracket records which positions of C M1 gets added to (C11 and C22). **A rank-r decomposition = an algorithm that uses only r multiplications**, and vice versa (such algorithms are called "bilinear algorithms"). So:

> Strassen 1969 ⇔ R(T₂) ≤ 7. (Winograd 1971 proved that 7 is optimal: R(T₂) = 7 [P].)

### 6.4.4 Tensor product = recursion

"Multiply" T_n and T_m (the tensor product, which pairs up the indices on each leg) and you get exactly T_{nm}. This is the algebraic version of the "blocks inside blocks" recursion from §6.2.2. So R(T_{nm}) ≤ R(T_n)·R(T_m), and:

> As soon as you find a k×k decomposition using r multiplications, you get ω ≤ log_k r.

| Size k | Multiplications r | Source | log_k r (computed by script) |
|---|---|---|---|
| 2 | 8 | Naive | 3.0000 |
| 2 | 7 | Strassen 1969 | 2.8074 |
| 3 | 23 | Laderman 1976 | 2.8540 |
| 4 | 49 | Strassen applied twice | 2.8074 |
| 4 | 48 | AlphaEvolve 2025 (over the complex numbers) | 2.7925 |
| 4 | 47 | AlphaTensor 2022 (GF(2) only, i.e. arithmetic mod 2) | 2.7773 |

Note: **by "finding one good decomposition of a fixed small size", the best anyone has reached is about 2.77.** Every upper bound on ω below that number comes from the "asymptotic" methods of §6.5–6.7.

**[Check 2]** If someone found a 4×4 decomposition with 46 multiplications, what bound on ω would follow?

### 6.4.5 Another tensor: polynomial multiplication (the star of OpenAI's proof)

Multiply two polynomials: (x₀ + x₁t)·(y₀ + y₁t) = x₀y₀ + (x₀y₁ + x₁y₀)t + x₁y₁t². Written as a tensor:

```
C(a, b) = Σ_{i<a, j<b} x_i · y_j · z_{i+j}
```

a and b are the numbers of coefficients of the two input polynomials, and the output has a + b − 1 coefficients. The naive method takes a·b multiplications. But its rank is only **a + b − 1**:

- evaluate both polynomials at a + b − 1 different points and multiply the values (a + b − 1 multiplications);
- then recover the coefficients of the product polynomial by interpolation (interpolation uses only additions and multiplication by constants, which don't count as "variable × variable" multiplications).

The case a = b = 2 is the **Karatsuba trick**: 3 multiplications P0 = x₀y₀, P1 = (x₀+x₁)(y₀+y₁), P2 = x₁y₁, and the middle coefficient = P1 − P0 − P2 (checked by script: it expands to x₀y₁ + x₁y₀ ✓). This is also where the idea behind fast FFT multiplication comes from.

**Key point: the rank of polynomial multiplication is known exactly (a + b − 1); the rank of matrix multiplication is unknown.** OpenAI's entire proof is "use the known thing to pin down the unknown thing".

**[Check 3]** Using "evaluate at the three points t = 0, 1, −1", design a different 3-multiplication algorithm for (x₀ + x₁t)(y₀ + y₁t), and write down how to recover the middle coefficient.

---

## 6.5 Approximations count too: border rank and "degeneration"

### 6.5.1 A strange example

Look at this small tensor (it has nothing to do with matrix multiplication; it's just a demonstration):

```
W = x₀y₀z₁ + x₀y₁z₀ + x₁y₀z₀
```

One can prove its rank is 3. But look at this expression (ε is a small parameter):

```
[ (x₀+εx₁)(y₀+εy₁)(z₀+εz₁) − x₀y₀z₀ ] / ε
  = W + ε·(x₀y₁z₁ + x₁y₀z₁ + x₁y₁z₀) + ε²·x₁y₁z₁
```

(Expanded and checked by script with sympy.) The left side has only **2** rank-1 terms, and as ε → 0 it tends to W. So W can be approximated arbitrarily well by "something of rank 2". We say W has **border rank** 2.

### 6.5.2 Bini's interpolation: approximate algorithms can become exact ones

Bini et al. found in 1979 that a variant of 2×2 matrix multiplication shows this kind of "approximately save a multiplication" behavior, and Bini 1980 proved a key fact [P]: **asymptotically, approximate algorithms are as good as exact ones.** The method: treat the expression containing ε as a polynomial in ε, compute it at several different values of ε, then interpolate out the ε⁰ term. The cost is only a factor independent of n, which disappears in the exponent.

### 6.5.3 "Degeneration": giving variables weights

The ε trick above has a more systematic version, which OpenAI's proof uses over and over:

1. give each variable an integer **weight** w;
2. multiply each variable by ε^w;
3. the total weight of a term = the sum of the weights of its three variables; **keep only the terms with the smallest total weight**. All other terms carry higher powers of ε and vanish in the limit.

Getting B from A this way is written A ⇝ B. Bini's interpolation guarantees that B is no "harder" than A. This is a powerful tool: **by choosing weights cleverly, you can "cut" the small tensor you want out of a big tensor, while throwing away every term you don't want.**

---

## 6.6 Fifty years of history: a war over the third decimal place

### 6.6.1 The asymptotic sum inequality and the laser method

- **Schönhage 1981**: if you can compute several **mutually independent** matrix multiplications **at the same time** more cheaply than computing them separately, you also get an upper bound on ω (the "asymptotic sum inequality"). Note that "independent" means no variables are shared on any of the three legs. This is called a **full direct sum**.
- **Strassen 1986–87: the laser method.** Find a tensor that is not itself matrix multiplication but has very low rank, take a very high power of it (tensor it with itself many times), and then "cut" a large number of mutually independent matrix multiplications out of it. Like a laser, it filters the in-phase part out of messy light.
- **Coppersmith–Winograd 1990**: found a particularly good starting tensor (the CW tensor) and, combined with the combinatorics of "sets with no three-term arithmetic progression" for the cutting, got 2.3755.

From 1986 to August 2026, nearly 40 years, almost all progress on the upper bound for ω came from refining the laser method (every row after 1986 in the table below).

### 6.6.2 Timeline

| Year | Authors | Upper bound on ω | Drop from the previous row (computed by script) |
|---|---|---|---|
| 1969 | Strassen | 2.8074 | — |
| 1978 | Pan | 2.796 | 0.011 |
| 1979 | Bini et al. (border rank) | 2.780 | 0.016 |
| 1981 | Schönhage (asymptotic sum inequality) | 2.522 | 0.258 |
| 1986 | Strassen (laser method) | 2.479 | 0.043 |
| 1990 | Coppersmith–Winograd | 2.3755 | 0.104 |
| 2014 | Le Gall (preceded by Stothers 2010, Vassilevska Williams 2012) | 2.3728639 | 0.0026 |
| 2021 | Alman–Vassilevska Williams | 2.3728596 | 0.0000043 |
| 2023 | Duan–Wu–Zhou | 2.371866 | 0.00099 |
| 2024 | Vassilevska Williams–Xu–Xu–Zhou | 2.371552 | 0.00031 |
| 2024 | Alman–Duan–Vassilevska Williams–Xu–Xu–Zhou | 2.371339 | 0.00021 |
| 2026-08 | Dupont et al. (incl. AlphaEvolve) | **2.371177** | 0.00016 |
| 2026-09-24 | OpenAI claim (any field, still within the laser-method framework) [P] | 2.371054886 | 0.00012 |
| 2026-09-24 | OpenAI claim (complex numbers) [P] | 2.258 | 0.113 |
| 2026-10-02 | OpenAI claim (complex numbers, the subject of this chapter) [P] | **2.25 = 9/4** | 0.008 |

(Values before 2026-08 are all peer-reviewed results [P]; Dupont et al.'s 2.371177 is the arXiv preprint 2608.16884, and OpenAI's 9/4 paper itself cites it as the previous record. The three OpenAI rows are taken from the papers in the openai/math repo and have not been peer-reviewed.)

A few comparisons computed by script:
- The 34 years from 1990 → 2024: a total drop of 0.0041.
- The 12 years from 2014 → 2026-08: a total drop of 0.0017.
- 2026-08 → 9/4: a single drop of **0.121**.

### 6.6.3 The wall the laser method hit

Ambainis–Filmus–Le Gall (STOC 2015) [P] proved that this kind of laser-method analysis, applied to powers of the CW tensor, **cannot go below about 2.3078**. Later, Alman–Vassilevska Williams and others gave more general barriers [P] ⚠ (I did not check the specific values one by one). So 2.25 cannot be "the laser method optimized a bit more"; it has to come from a different road. This is exactly what Aaronson means by "via a completely different approach".

The figure below puts the timeline from §6.6.2 and this barrier together: OpenAI's 2.25 sits below the dashed line (about 2.3078).

{{FIG_OMEGA}}

---

## 6.7 Strassen's asymptotic spectrum: "measuring" instead of "constructing"

This section is the key to understanding OpenAI's proof, and also the most abstract part of the chapter. I'll use engineering analogies as much as I can, and flag where an analogy breaks down.

### 6.7.1 "Which tensor is stronger"

**A ≥ B** (B is a "restriction" of A) means: you can get B by applying a linear substitution to each of A's three legs. Intuitively, **if you can compute A, you can compute B**. For example:

- R(T) ≤ r is equivalent to "r independent scalar multiplications ≥ T" (where r denotes "a sum of r mutually unrelated xyz terms").
- Drop all terms of T_n with i ≠ j, and what's left is n independent scalar multiplications, so T_n ≥ n.

### 6.7.2 Tensor characters: a "consistent measuring device"

A **tensor character** (also called a "point" of the asymptotic spectrum) is a function λ that maps tensors to non-negative real numbers and satisfies four properties:

| Property | Meaning | Engineering analogy |
|---|---|---|
| λ(1) = 1 | A single scalar multiplication has value 1 | Unit calibration |
| λ(A ⊕ B) = λ(A) + λ(B) | Independent tasks run in parallel; values add | Throughput adds up |
| λ(A ⊗ B) = λ(A) · λ(B) | Nesting (recursion); values multiply | Recursive costs multiply |
| A ≥ B ⇒ λ(A) ≥ λ(B) | If you can compute A you can compute B, so A's value is no smaller | Monotone |

These four immediately imply: **for any nonzero tensor, 1 ≤ λ(A) ≤ R(A)**. So every character gives a **lower bound** on rank.

**Example: flattening rank.** Stand one leg of the three-dimensional array up vertically and lay the other two legs out together as a row. You get an ordinary matrix; take its matrix rank. This satisfies all four properties, and these are the three simplest characters. For T_n, the flattening rank is n².

### 6.7.3 Every character's value on matrix multiplication is n^(3t)

§2.1 of the paper uses a small trick to prove that for any character λ there is a number t > 0 such that

```
λ(T_n) = n^(3t)    for all n
```

(Proof idea: T_n can be split into a tensor product of three "dot product" tensors, and each dot product has value some power of m under λ; multiplying gives n^(p_X + p_Y + p_Z), and we write 3t = p_X + p_Y + p_Z.)

For example, flattening rank: λ(T_n) = n² ⇒ 3t = 2, t = 2/3.

### 6.7.4 Strassen's duality theorem: measurements decide everything

Strassen 1986–88 [P] proved a deep theorem (Appendix A of the OpenAI paper re-proves the special case it needs):

> The rank exponent of matrix multiplication ω ≤ 3·(the largest t over all characters). More precisely: if R(T_d) is large, then there must be some character λ that "detects" it, i.e. λ(T_d) is also large.

**Analogy**: this is a lot like duality in linear programming, or Farkas' lemma: either a good algorithm exists, or there is a "certificate" (a character) proving it doesn't. So to prove "a good algorithm exists" (ω is small), you **don't need to construct the algorithm**. You only need to prove that "**no** certificate can show it doesn't exist", i.e. **every character has t ≤ 3/4**.

This is the most important turn in the chapter:
- Laser method: **construct** one specific large tensor decomposition.
- Asymptotic spectrum: **bound every possible measurement**, then use the duality theorem to conclude that an algorithm exists.

**An honest note**: Strassen proposed the asymptotic-spectrum route back in the 1980s. The hard part is that nobody knows what all the characters look like. Over the complex numbers, the only known infinite family is the "quantum functionals" of Christandl–Vrana–Zuiddam (JAMS 2023) [P]. OpenAI's proof **sidesteps** this difficulty: it doesn't need to know what the characters look like, and derives its inequalities from the four properties alone.

If the ω = 2 conjecture is true, then every character has t = 2/3 on matrix multiplication (the same as flattening rank). The 9/4 result says: t ≤ 3/4.

---

## 6.8 What OpenAI claims

### 6.8.1 The main result

The abstract of the paper *An Upper Bound of 9/4 for the Matrix Multiplication Exponent* (2026-10-02, 13 pages) is a single sentence:

> "We prove that the exponent of matrix multiplication over the complex numbers is at most 9/4." [P]

Theorem 1.1: "For every ε > 0, two n × n complex matrices can be multiplied using O_ε(n^{9/4+ε}) arithmetic operations. In particular, ω ≤ 9/4."

The paper itself also says: "Theorem 1.1 concerns the asymptotic arithmetic exponent; its proof does not specify a competitive finite matrix size."

The same family (number 107) has two more manuscripts:
- *Complex Matrix Multiplication Below 2.258 and Rectangular Bounds* (2026-09-24, 83 pages): over fields of characteristic 0, ω < 2.258, the "dual exponent" α > 0.465, and ω(1, 0.709, 1) < 2.092. Once 9/4 came out, the 2.258 was superseded by it.
- *Staggered extraction for exact matrix multiplication over every field* (2026-09-24, 35 pages): over **every field** (including finite fields and positive characteristic), ω < 2.371054886006746. Still within the laser-method framework; about 1.2×10⁻⁴ better than Dupont et al.

### 6.8.2 The skeleton of the proof (I read the whole paper; this is a faithful simplification)

The whole proof uses only the tools from §6.4–6.7. It has five steps.

**Step 1: separate blocks that "share a leg" (paper §3, the separation lemma).**

An old problem for the laser method is that the small blocks you cut out often share variables, so they are not fully independent. OpenAI's core construction handles this case: M blocks that are independent of each other on the y and z legs but **share** the x leg. The method:
- make 5M copies, and give each one a phase from a different power of an L = 5M-th root of unity ζ (this is a finite Fourier transform), tagging each x variable with a "tentative label" g;
- then use the "weighting" from §6.5.3: x gets weight g², y gets weight hu − h², z gets weight −hv. On the terms that survive the Fourier transform, the total weight is exactly **(g − h)²**;
- keep only the terms with weight 0, i.e. g = h: each block gets its own private copy of x, and the blocks become fully independent. As a side effect, each block also gains a "dot product" of length M.

The intuition for this step: **use the square (g−h)² ≥ 0 as a "penalty", so that every term whose labels don't match vanishes as ε → 0.** Combined with the standard "count by frequency" technique, this gives an entropy inequality (Corollary 3.2).

**Step 2: look only at polynomial multiplication.** For any character λ, define the "symmetrized value" P(a, b) of the polynomial multiplication tensor C(a, b) (evaluate all 6 permutations of the three legs, multiply the 6 values together, then take the 1/(6t)-th power; see the paper's eq. 4.4). It satisfies three simple properties (Eq. 4.5):
- P(a, b) = P(b, a);
- P(1, b) = b (C(1, b) is just a dot product);
- **P(a, b) ≤ (a + b − 1)^(1/t)**: because the rank of polynomial multiplication is a + b − 1 (§6.4.5), and a character is ≤ rank.

Here t is exactly the "exponent of λ on matrix multiplication" from §6.7.3.

**Step 3: two new inequalities (paper §4).**
- **Discrete concavity**: 2P(a, b) ≥ P(a, b+1) + P(a, b−1). (A "determinantal filtration" degenerates C(a, b) ⊗ dot product into two blocks, C(a, b+1) and C(a, b−1); then apply Step 1.)
- **Shifted tripling**: P(a, 3h + a − 1) ≥ 3·P(a, h). (Cut the y and z indices of C(a, 3h+a−1) into left, middle and right segments; after weighting, exactly three copies of C(a, h) remain.)

You can work out the smallest case of shifted tripling by hand: a = 2, h = 1, i.e. C(2, 4), which has 8 terms x_i·y_j·z_{i+j}. Cut y into left {0}, middle {1, 2}, right {3}; cut z into left {0, 1}, middle {2}, right {3, 4}. Middle y gets weight +1, middle z gets weight −1, everything else 0:

| Term (x, y, z) | Weight | Result |
|---|---|---|
| (0,0,0), (1,0,1) | 0 | Left block kept |
| (0,2,2), (1,1,2) | +1−1 = 0 | Middle block kept |
| (0,3,3), (1,3,4) | 0 | Right block kept |
| (0,1,1), (1,2,3) | +1 | **Vanishes** |

(Checked term by term by script; matches Figure 1 of the paper.) The three blocks don't overlap on y or z, and they share x: exactly the shape Step 1 can handle.

**[Check 4]** Without looking at the table, work out why the term (0,1,1) has weight +1.

**Step 4: a pure sequence argument (paper §5, Lemma 5.1).** Using only "symmetry + P(1,b) = b + concavity + shifted tripling", you can derive growth along the diagonal:

```
P(a, a) ≥ a^(4/3)
```

This step is entirely elementary: concavity says the increments decrease, tripling says the increments can't decrease too fast, and together they squeeze out a recurrence H_a ≥ (1 + 1/(3(a−1)))·H_{a−1}, finished off with (1 + 1/(3m))³ ≥ 1 + 1/m. The script checked this chain of lower bounds (for example, at a = 1000 the paper's intermediate lower bound gives P(a,a) ≥ 16,790, while a^(4/3) = 10,000).

**Step 5: squeeze from both sides.** Step 2 gives an upper bound and Step 4 gives a lower bound:

```
a^(4/3) ≤ P(a, a) ≤ (2a − 1)^(1/t)
```

As a → ∞, the left side behaves like a^1.333 and the right side like a^(1/t). For this to hold for all a, we need 1/t ≥ 4/3, i.e. **t ≤ 3/4**. Computed by script: if some character had t = 0.8, this inequality would already be violated at a = 32,761; with t = 0.76 it would take until a ≈ 3.8×10²².

So **every** character has λ(T_d) = d^(3t) ≤ d^(9/4). Then by the duality theorem of §6.7.4, the rank exponent is ≤ 9/4, so **ω ≤ 9/4**.

### 6.8.3 Why the final answer is a rational number

Laser-method bounds come from the optimal value of a numerical optimization problem, so they are "computed" irrational-looking numbers like 2.3728639. Here 9/4 = 3 × 3/4; the 3/4 comes from "growth like the 4/3 power", and the 4/3 in turn comes from the 3 in the "tripling" construction. Hence Aaronson's line: "a *rational* exponent for once (!)" [R].

### 6.8.4 What "does not specify a size" actually means

The last paragraph of the paper turns "ω ≤ 9/4" into an algorithm: by the definition of the rank exponent, there **exists** some fixed u and a decomposition of T_u with r < u^(9/4+δ) multiplications; then you recurse as Strassen did. But the proof **doesn't tell you what u is, and doesn't give the decomposition**, because the duality theorem of §6.7.4 uses compactness and a fixed-point theorem (Schauder–Tychonoff). It is essentially an existence proof.

What this means for engineering can be estimated with known lower bounds (computed by script):
- u = 2: R(T₂) = 7 > 2^2.25 ≈ 4.76. Impossible.
- u = 4: you'd need r ≤ 22, but Bläser 2003 proved R(T_n) ≥ 2.5n² − 3n [P] ⚠ (details of the source not re-checked), which gives a lower bound of 28 at n = 4. Impossible.
- By this lower bound, **u must be at least 34** for a decomposition meeting the requirement to possibly exist. The real u may be far larger; nobody knows.

Remark 5.2 of the paper adds that the coefficients of this decomposition can be taken to be algebraic numbers (in some number field). So in principle it could be found by a finite search, but there is no practical feasibility at all. (This is my inference ⚠.)

A comment on Aaronson's blog (Bram Cohen, #42) says the result "isn't constructive". That judgment is right, but his description "ramsey type thing" is inaccurate: the non-constructiveness comes from the compactness + fixed-point argument in the duality theorem, not from a Ramsey-type combinatorial argument.

---

## 6.9 How far it has been verified

### 6.9.1 The Lean statement: read the model first, then the theorem

Unlike the quasi-Riemann hypothesis (§4), ω here is not a ready-made Mathlib definition; it is written by the challenge file `lean/ComparatorChallenges/MatrixMultiplication.lean` itself. So **reviewing the definitions** matters more than reviewing the theorem. Here is my block-by-block translation from reading the Lean source [P]:

- `Gate`: there are only five kinds of "gate": `constant` (a constant), `input` (read one input), `add`, `sub`, `mul` (operate on two existing registers).
- `Gate.cost`: constants and inputs cost 0; **add, subtract and multiply each cost 1** (the source reads `.constant _ => 0`, `.input _ => 0`, and `=> 1` for each of `.add`, `.sub`, `.mul`). So this is the standard "number of arithmetic operations" model. (Multiplying by a constant also uses a `mul` gate, so it also costs 1.)
- `Program`: a sequence of gates, where each gate can only refer to earlier registers. This is a "straight-line program": no loops, no branches, no division.
- `MatrixAlgorithm F a b c`: a program, plus "which register each position of the output matrix takes".
- `Correct`: for **all** input matrices A, B, the output equals `A * B` (Mathlib's standard matrix multiplication).
- `AdmissibleExponent F τ`: for every ε > 0 there is a constant C such that for **every** n ≥ 1 there is a correct program with cost ≤ C·n^(τ+ε).
- `omega F := sInf {τ | AdmissibleExponent F τ}`: the infimum.

Then the theorem itself:

```lean
theorem complex_omega_le_nine_quarters :
    Arithmetic.omega ℂ ≤ (9 : ℝ) / 4
```

Its full name is `OAI.MatrixMultiplication.complex_omega_le_nine_quarters`. Translation: **over the complex numbers, the matrix multiplication exponent, defined by the model above, is ≤ 9/4.** This matches the definition in §6.3.1. Note that it is "non-uniform" (each n may have a different program; there is no requirement for one uniform algorithm that generates them), which is also the standard definition of ω in the literature (non-uniform algebraic complexity). My judgment: the model is consistent with the literature, with no hidden assumptions.

**A specification trap worth noting** (especially interesting for AI safety people): in Lean/Mathlib, **the sInf of the empty set is defined to be 0**, and the sInf of a set with no lower bound is also defined to be 0. So if some definition were written wrong so that "no program is ever judged correct", then omega = 0 and "omega ≤ 9/4" would hold **trivially**. I checked this: the solution proves `omega_le_three` (the naive algorithm works, so the set is non-empty) and `admissibleExponent_two_le` (every admissible exponent is ≥ 2, so the set is bounded below), and the 9/4 derivation goes through `csInf_le`, which requires actually exhibiting an admissible exponent. So this trap is ruled out.

The same challenge file has two more theorems: α > 93/200 and ω(ℂ; 1, 0.709, 1) < 523/250.

### 6.9.2 The proof itself

- The Lean proof of the 9/4 theorem is in `OAI/LinearAlgebra/MatrixMultiplication/AuxiliarySeparation/` (73 files, 10,895 lines). Computing the import closure from its `Main.lean`, the project-internal total is **129 files, about 20,700 lines** (computed by script, including shared directories such as Arithmetic, Tensor and Polynomial). The whole matrix multiplication directory (including 2.258 and the rectangular bounds) is 509 files, about 83,000 lines.
- I grepped: no `sorry`, no custom `axiom`, no `native_decide` (the three hits for `admit` are all the English word "admits" in comments).
- The Comparator config allows only three standard axioms: `propext`, `Quot.sound`, `Classical.choice`. Note that the config has `"enable_nanoda": false`, i.e. **this challenge did not turn on a second, independent kernel**.
- **External dependency**: the fixed-point theorem in Appendix A uses the third-party library `fixed-point-theorems-lean4` (harfe, the Brouwer fixed-point theorem). OpenAI applied a porting patch to it (about 77 lines added, 63 deleted). I looked at it: it mainly adapts imports and syntax to Lean 4.34, and I saw no `sorry` or new axioms.
- A small documentation oddity: the scope note `lean/docs/107.md` lists only the 2.258 and staggered papers, not the 9/4 paper; but the 9/4 theorem is indeed proved in `AuxiliarySeparation/Main.lean` (the file comment says "Theorem 1.1").

### 6.9.3 Independent re-checks

- **erenciracioglu-dotcom/openai-math-9-4-lean-check** [R]: compiled these three theorems with Lean v4.34.1 on Windows 11, used `pp.all` to compare the challenge statement and the solution statement and found them identical, and reports dependence on only the three standard axioms. But it says itself: "It does **not** replace Comparator: there was no sandbox and no second, independent kernel replay." Also, it used openai/math commit `adc7f12`, not the `fd4aeeb` used in these notes ⚠ (I did not compare whether this part changed between the two commits).
- I **did not compile** it myself.

### 6.9.4 Human experts

- Scott Aaronson ("The Mathocalypse", 2026-10-07): "Matrix multiplication in n^{9/4+o(1)} time—a rational exponent for once (!), and via a completely different approach than was used for O(n^{2.373}) and so forth" [R]. This is a comment, not a verification.
- **As of 2026-10-08, I found no laser-method / tensor expert (Vassilevska Williams, Alman, Le Gall, Zuiddam, Christandl, etc.) publicly saying they have read and verified this paper** ⚠. The vibemathed.com entry also says "No independent mathematician has checked this yet" [R].
- One favorable factor (my judgment): the paper is only 13 pages, uses only standard tools, and Appendix A fully re-proves the special case of the duality theorem it needs. It is **one of the headline results of the whole openai/math release most likely to be fully understood by human experts within a few weeks**.

### 6.9.5 Remaining risks

1. The custom computational model: I read it and think it is faithful (§6.9.1). But that is the level of "one person read it once".
2. No second-kernel re-check.
3. Correctness of the third-party fixed-point library: the Lean kernel checks its proofs, so the risk is mainly at the level of definitions, and it is low.
4. Risks beyond correctness: the conclusion is right, but humans don't yet understand "why nobody made this road work before".

---

## 6.10 What it means if true (and what it doesn't)

### 6.10.1 For mathematics and theoretical computer science

1. **The biggest single step in 35 years**: from 2.3712 to 2.25, a drop about 70 times the total of the previous 12 years (computed by script: 0.121 vs 0.0017).
2. **It gets around the laser-method barrier** (§6.6.3), showing that Strassen's asymptotic-spectrum route is workable, and can be used in a quite "elementary" way.
3. The theoretical upper bounds of all algorithms whose complexity is written as n^ω (§6.3.3) go down together.
4. **Is ω = 2 now closer?** This is speculation. Where this method's bottleneck lies (whether the 4/3 growth rate is a limit of the method itself), and whether it can be pushed to 2, the paper doesn't discuss ⚠.
5. **Only for the complex numbers** (and, via the algebraic-coefficient argument in the paper's Remark 5.2). Over fields of positive characteristic, OpenAI only claims 2.371054886.

### 6.10.2 For GPUs and LLM training: no direct impact

This is where engineers most easily get it wrong, so let me be concrete:

1. **We barely use even Strassen.** The table in §6.2.2 shows that, counting additions, plain Strassen only wins on operation count at n ≈ 1024. On real hardware there is also: (a) the extra block additions need extra memory reads and writes with an irregular access pattern, and GEMM is often bound by memory bandwidth and Tensor Core throughput; (b) Tensor Cores only accelerate "multiply-add", so block additions don't get accelerated; (c) numerical stability is worse than the naive algorithm (Higham's textbook analyzes this specifically). Some work has achieved practical Strassen speedups on CPUs (Huang et al., "Strassen's Algorithm Reloaded", SC16), but mainstream deep learning libraries don't use it.
2. **The 9/4 algorithm is a "galactic algorithm"**: asymptotically faster, but only wins on absurdly large inputs. The paper gives no constant, so what follows is a **hypothetical** calculation (computed by script): if the 9/4 algorithm's constant is C and the naive algorithm's is 2n³, the crossover is around n ≈ (C/2)^(4/3). With C = 10⁶, n ≈ 4×10⁷, and a single such fp16 matrix takes about 3×10¹⁵ bytes (3 PB). And nobody knows the real constant; as §6.8.4 said, even the size u of the base decomposition is at least 34, and the actual decomposition is unknown.
3. **The 2.37 laser-method algorithms are galactic algorithms too.** So this is not a problem specific to 9/4: **none of the results with ω below about 2.77 has ever been usable in practice.**
4. **Compare AlphaTensor / AlphaEvolve**: AlphaTensor (Fawzi et al., *Nature* 610, 2022) [P] and AlphaEvolve (2025, 48 multiplications for 4×4 complex matrices) [R] look for low-rank decompositions of a **fixed small size**. That kind of thing can be written directly into a kernel and gives constant-factor speedups (the AlphaTensor paper even optimized decompositions for specific GPUs). ω is about the exponent as n → ∞. The two are almost different problems. Dupont et al. (2026-08) used AlphaEvolve to optimize parameters inside the laser method; that was the first time AI helped set a new record bound on ω, but the improvement was only 1.6×10⁻⁴.

### 6.10.3 For AI

- **This is a "new idea", not a "bigger optimization".** Compared with Dupont et al. "using AI to tune parameters and squeeze out 1.6×10⁻⁴", the 9/4 proof switched to a different route, and the final argument is short enough to write out by hand. If it holds up, it is one of the clearest examples of "AI producing a mathematical idea that humans didn't find in 35 years".
- **13 pages + about 20,000 lines of Lean make a good touchstone for human verification.** Unlike the 199 pages + 480,000 lines of Lean for the quasi-Riemann hypothesis (§4), here human experts can read the whole thing independently. How experts assess it over the next few weeks is a good signal for judging "the credibility of the whole openai/math release".
- **Spec review matters more than proof review** (§6.9.1): a Lean proof is only trustworthy if "the computational model is written correctly". This is the math version of the "spec gaming" problem in AI safety, and here the review only requires reading 100 lines of definitions.

---

## 6.11 Self-test

Try answering these after reading. If you can't, go back and reread the relevant section.

1. Why can Strassen's 7-multiplication formula be used recursively? Which property does it crucially not use? (§6.2.2)
2. What is the relationship between "a rank-r tensor decomposition" and "an algorithm using r multiplications"? (§6.4.3)
3. Why is the rank of the polynomial multiplication tensor C(a, b) equal to a + b − 1? How does this relate to Karatsuba? (§6.4.5)
4. What four properties must a tensor character satisfy? Why is every character ≤ rank? (§6.7.2)
5. Between the laser method and the asymptotic-spectrum route, which is "constructing" and which is "measuring"? Why can the latter get around the known barriers? (§6.6.3, §6.7.4)
6. In the last step of OpenAI's proof, which two inequalities squeeze out t ≤ 3/4? (§6.8.2, step 5)
7. In Lean, why does "sInf of the empty set = 0" create a specification risk? How is it ruled out here? (§6.9.1)
8. Why won't ω ≤ 9/4 make your GPU training faster? Give at least three reasons. (§6.10.2)

---

## Appendix: answers to the checks

- **Check 1**: M2 + M4 = (c+d)e + d(g−e) = ce + de + dg − de = ce + dg ✓.
- **Check 2**: ω ≤ log₄ 46 ≈ 2.7618 (computed by script). Better than Strassen's 2.8074, but far from the laser method's 2.37.
- **Check 3**: Evaluate at t = 0: P0 = x₀y₀; t = 1: P1 = (x₀+x₁)(y₀+y₁); t = −1: P2 = (x₀−x₁)(y₀−y₁). The product polynomial is c₀ + c₁t + c₂t², so P1 = c₀ + c₁ + c₂ and P2 = c₀ − c₁ + c₂. Hence c₀ = P0, c₁ = (P1 − P2)/2, c₂ = (P1 + P2)/2 − P0. Dividing by 2 is multiplication by a constant, not a "variable × variable" multiplication.
- **Check 4**: In (0,1,1), the y index 1 is in the middle segment, weight +1; the z index 1 is in the left segment {0, 1}, weight 0. The total weight is +1 > 0, so it vanishes as ε → 0.

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| ω (matrix multiplication exponent) | The optimal exponent for the number of arithmetic operations needed for n×n matrix multiplication; 2 ≤ ω ≤ 3 |
| Bilinear algorithm | An algorithm in which every multiplication is "a linear combination of A's entries × a linear combination of B's entries" |
| Tensor | A three-dimensional array; here equivalent to a trilinear form Σ c·x·y·z |
| Leg | One of the tensor's three groups of variables x, y, z |
| Tensor rank | The smallest number of rank-1 terms it can be written as a sum of; equals the minimum number of multiplications of a bilinear algorithm |
| Border rank | The smallest rank when approximation by expressions containing ε is allowed |
| Degeneration | Give variables weights as powers of ε and keep only the lowest-weight terms |
| Restriction | Get another tensor by linear substitutions on the three legs; A ≥ B means "if you can compute A you can compute B" |
| Full direct sum | A sum of several tensors that share no variables on any of the three legs |
| Laser method | Cutting many independent matrix multiplications out of a high power of some low-rank tensor (Strassen 1986) |
| Asymptotic spectrum / tensor character | The set of all "measurement functions" that are normalized, additive, multiplicative and monotone; Strassen proved they determine asymptotic complexity |
| Flattening rank | The rank of the tensor after laying it out as a matrix; the simplest tensor character |
| Galactic algorithm | An algorithm that is asymptotically faster but only wins on unrealistically large inputs |
| Straight-line program | A sequence of operations with no loops or branches; the Lean formalization uses it to model algorithms |

## Appendix: Further reading

- **The original paper** (13 pages, readable in full): https://github.com/openai/math/blob/main/preprints/Matrix-Multiplication-Nine-Fourths-October-2-2026/paper.pdf
- **Lean statement** (about 100 lines; I recommend reading the definitions yourself): https://github.com/openai/math/blob/main/lean/ComparatorChallenges/MatrixMultiplication.lean
- **Independent Lean re-check**: https://github.com/erenciracioglu-dotcom/openai-math-9-4-lean-check
- **Quanta Magazine**, *New Breakthrough Brings Matrix Multiplication Closer to Ideal* (2024-03-07): popular coverage of the Duan–Wu–Zhou step, with intuitive pictures of the laser method. https://www.quantamagazine.org/new-breakthrough-brings-matrix-multiplication-closer-to-ideal-20240307/
- **Markus Bläser**, *Fast Matrix Multiplication* (Theory of Computing Graduate Surveys 5, 2013): the best introductory survey, free. https://theoryofcomputing.org/articles/gs005/
- **J. M. Landsberg**, *The complexity of matrix multiplication: developments since 2014* (arXiv 1811.11667): a survey from a more geometric point of view.
- **Bürgisser, Clausen, Shokrollahi**, *Algebraic Complexity Theory* (Springer 1997): Chapters 14–15 cover tensor rank, the laser method and the asymptotic spectrum; the standard textbook.
- **Christandl, Vrana, Zuiddam**, *Universal points in the asymptotic spectrum of tensors* (JAMS 36, 2023; arXiv 1709.07851): "what the known characters look like" from §6.7.
- **Ambainis, Filmus, Le Gall**, the laser-method barrier (STOC 2015): https://arxiv.org/abs/1411.5414
- **Alman et al.**, *More Asymmetry Yields Faster Matrix Multiplication* (SODA 2025): https://arxiv.org/abs/2404.16349
- **Dupont et al.**, *Improving the matrix multiplication exponent with modern optimization and AlphaEvolve* (2026-08): https://arxiv.org/abs/2608.16884
- **Fawzi et al.**, *Discovering faster matrix multiplication algorithms with reinforcement learning* (AlphaTensor, *Nature* 610, 2022)
- **Huang, Smith, Henry, van de Geijn**, *Strassen's Algorithm Reloaded* (SC16): when Strassen is worth using on real hardware.
- **Scott Aaronson**, *The Mathocalypse* (2026-10-07): https://scottaaronson.blog/?p=10169
- **3Blue1Brown**, *Linear transformations and matrices* (YouTube, Essence of Linear Algebra episodes 3–4): if you want to shore up the intuition that "matrix multiplication = composition of linear transformations" first.
