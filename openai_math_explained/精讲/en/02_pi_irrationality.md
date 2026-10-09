# How well can fractions approximate π: the irrationality exponent μ(π) = 2

> Number theory · OpenAI family 017 (§5.7.4 also covers family 005 from the same release: Catalan's constant). All you need going in: you can work with fractions, powers and logarithms, and you know what it means for an infinite sum to "converge." Every new concept is explained before it is used.
> Every number in this chapter was either computed by script (Python + mpmath, with π to 3000 digits of precision) or has a source. Tags: [P] = a primary source we read directly (paper, repo file, Lean source), [R] = secondary reporting, ⚠ = unverified or doubtful. The **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter.
> Estimated reading time: 60–80 minutes. You can read it in three sittings: §5.1–5.3 (approximating by fractions, continued fractions, Dirichlet), §5.4–5.6 (the irrationality exponent, the history for π, the Flint Hills series), §5.7–5.9 (OpenAI's result, its verification and what it means).

---

## 5.0 The bottom line: the one thing this chapter explains

π is irrational: it cannot be written as a fraction. But it can be **approximated** by fractions: 3, 22/7, 355/113, … The bigger the denominator, the more accurate the approximation, which is nothing special. The real question is:

> **Relative to the size of the denominator, how "well" can π be approximated?**

This chapter explains one chain:

> Any irrational number can be approximated to within "error ≈ 1/q²" (Dirichlet; everyone gets this) ⟹ the question becomes "can you do **much better than 1/q²**, and do so infinitely often" ⟹ a number μ (the irrationality exponent) measures this capacity for "exceptional approximation" ⟹ almost every real number has μ = 2, but for the **specific** number π, for 70 years all anyone could prove was μ ≤ 7.1.

OpenAI claims to have proved μ(π) = 2. That is: in this respect π is as ordinary as "a real number picked at random"; there are not infinitely many "absurdly good" fractional approximations. As a side effect, it settles a popular puzzle: the Flint Hills series Σ 1/(n³ sin²n) converges.

After reading this chapter, you should be able to explain in your own words:
- how to measure precisely "how well a number can be approximated by fractions," and why the baseline is 1/q²;
- why "almost every number has μ = 2" is easy to prove, while "π has μ = 2" is extremely hard;
- what playbook OpenAI's proof uses (in one sentence: "a nonzero integer is at least 1"), and how far it has been verified;
- what this result does **not** mean (it is not transcendence, not "normality," not "bounded continued fraction").

---

## 5.1 Approximating π by fractions: from 3 to 355/113

### 5.1.1 A table

π = 3.14159265358979…. Some historically famous fractions:

| Fraction | Origin | Error \|π − p/q\| | 1/q² | q² × error |
|---|---|---|---|---|
| 3/1 | Antiquity | 1.42×10⁻¹ | 1 | 0.142 |
| 314/100 | Decimal truncation | 1.59×10⁻³ | 1×10⁻⁴ | 15.9 |
| 22/7 | Archimedes' "yuelü" ("approximate ratio") | 1.26×10⁻³ | 2.04×10⁻² | 0.062 |
| 333/106 | | 8.32×10⁻⁵ | 8.90×10⁻⁵ | 0.935 |
| 355/113 | Zu Chongzhi's "milü" ("close ratio," 5th century) | 2.67×10⁻⁷ | 7.83×10⁻⁵ | **0.0034** |
| 103993/33102 | | 5.78×10⁻¹⁰ | 9.13×10⁻¹⁰ | 0.633 |

(Computed by script.)

### 5.1.2 Why divide by the "cost of the denominator"

A smaller error is not remarkable in itself: if you allow denominators up to 10⁶, you can just take 3141593/1000000 and push the error down to around 10⁻⁷. So looking only at the error is unfair; you have to look at the error **relative to the size of the denominator**.

Compare 314/100 and 22/7: their errors are about the same (both around 10⁻³), but 22/7 uses only the denominator 7, while 314/100 uses the denominator 100. 22/7 is much better "value for money."

A natural measure: **the error is one over what power of the denominator?** If |π − p/q| ≈ q^(−ν), we say this approximation has "effective exponent" ν. The bigger ν, the more "exceptional" the approximation.

- 314/100: error ≈ 100^(−1.4), ν ≈ 1.4. Decimal truncation only reaches about the ν ≈ 1 level (error ~ 1/q).
- 22/7: ν ≈ 3.43 (computed by script).
- 355/113: ν ≈ 3.20 (computed by script). This is what is magical about the "milü": a three-digit denominator gives accuracy of about 10⁻⁷ (the first 6 decimal places are all correct).

The last column of the table, q² × error, is another angle: if it is < 1, the error is smaller than 1/q². For 355/113 this column is 0.0034, i.e. about **290 times** better than 1/q².

**[Check 1]** Verify with a calculator: 355/113 = 3.14159292…; how far is it from π? What is 113²? Roughly what is the error times 113²?

---

## 5.2 Continued fractions: a machine for finding "best approximations"

The fractions 3, 22/7, 333/106, 355/113 in the table were not cobbled together; they are the output of a machine. The machine is called a **continued fraction**.

### 5.2.1 The algorithm: take the integer part, take the reciprocal, repeat

For a number x:
1. Write down the integer part a₀; what remains is the fractional part r.
2. Take the reciprocal 1/r, write down its integer part a₁, and keep the new fractional part.
3. Repeat.

The first two steps for π by hand:
- π = 3 + 0.14159…, so a₀ = 3.
- 1/0.14159… = 7.0625…, so a₁ = 7.
- 1/0.0625… = 15.996…, so a₂ = 15.

Continuing (computed by script):

```
π = [3; 7, 15, 1, 292, 1, 1, 1, 2, 1, 3, 1, 14, 2, 1, 1, 2, 2, 2, 2, …]
```

This means π = 3 + 1/(7 + 1/(15 + 1/(1 + 1/(292 + …)))).

### 5.2.2 Truncation = good fractions

Cut it off at some position and you get a fraction, called a **convergent**:
- Cut at [3] → 3
- Cut at [3; 7] → 3 + 1/7 = 22/7
- Cut at [3; 7, 15] → 333/106
- Cut at [3; 7, 15, 1] → 355/113
- Cut at [3; 7, 15, 1, 292] → 103993/33102

A classical theorem (Lagrange and others, 18th century): convergents are "best approximations." Among all fractions with denominator at most q, none is closer to x.

### 5.2.3 The bigger the next number, the more accurate the current fraction

This is the most useful rule of thumb in the chapter:

> The error of a convergent p/q is about 1 / (a_next × q²), where a_next is the number in the continued fraction that **comes right after the cut** (called a "partial quotient").

- 22/7 is followed by 15: error ≈ 1/(15 × 49) ≈ 1.4×10⁻³; actual 1.26×10⁻³.
- 355/113 is followed by **292**: error ≈ 1/(292 × 12769) ≈ 2.7×10⁻⁷; actual 2.67×10⁻⁷.
- 333/106 is followed by 1: error ≈ 1/(1 × 106²), the same order as 1/q², not "exceptional" at all (q² × error = 0.935).

So **asking "can π be approximated exceptionally well" is equivalent to asking "do especially huge partial quotients show up in π's continued fraction."** 292 is one. Will there be even more outrageous ones later?

### 5.2.4 Control group: some "well-behaved-looking" numbers

| Number | Continued fraction (computed by script) | Pattern |
|---|---|---|
| Golden ratio φ = (1+√5)/2 | [1; 1, 1, 1, 1, …] | All 1s; the hardest number to approximate |
| √2 | [1; 2, 2, 2, 2, …] | Always 2 |
| e | [2; 1, 2, 1, 1, 4, 1, 1, 6, 1, 1, 8, …] | 1, 1, 2k pattern; grows slowly |
| π | [3; 7, 15, 1, 292, 1, 1, 1, 2, …] | **No known pattern** |

For patterned numbers like √2 and e, the size of the partial quotients is obvious at a glance, so "how well it can be approximated" can be computed directly. π's continued fraction has **no known pattern at all**, and that is the root of the difficulty: you can't just stare at its continued fraction and prove "a super-large number will never appear later."

**[Check 2]** Compute the continued fraction of 355/113 by hand. (Hint: 355 = 3 × 113 + 16; then continue with 113/16.)

---

## 5.3 Dirichlet's theorem: exponent 2 comes free for everyone

### 5.3.1 The statement

> **Dirichlet's approximation theorem (1842)**: for any irrational number x, there are infinitely many fractions p/q with |x − p/q| < 1/q².

In other words, effective exponent 2 is "free": every irrational number can achieve it. That is why the baseline is 1/q² and not something else.

### 5.3.2 Proof: the pigeonhole principle, doable by hand

Take an integer Q, say Q = 10. Look at the **fractional parts** of the 11 numbers 0·π, 1·π, 2·π, …, 10·π (computed by script):

| q | fractional part of qπ |
|---|---|
| 0 | 0.000 |
| 1 | 0.142 |
| 2 | 0.283 |
| 3 | 0.425 |
| 4 | 0.566 |
| 5 | 0.708 |
| 6 | 0.850 |
| 7 | 0.991 |
| 8 | 0.133 |
| 9 | 0.274 |
| 10 | 0.416 |

Cut [0, 1) into 10 drawers of length 0.1. Put 11 numbers into 10 drawers and **at least two land in the same drawer**. From the table: q = 1 (0.142) and q = 8 (0.133) are both in [0.1, 0.2).

Subtract: 8π − 1π = 7π, and the fractional parts differ by only 0.009. This says 7π is very close to an integer: 7π ≈ 21.991, only 0.0089 away from 22. So

```
|7π − 22| < 1/10   ⟹   |π − 22/7| < 1/(7 × 10) ≤ 1/7²
```

In general, with Q drawers and Q+1 numbers, you can always find q ≤ Q with |qx − p| < 1/Q, so |x − p/q| < 1/(qQ) ≤ 1/q². Letting Q grow larger and larger gives infinitely many such fractions. QED.

**[Check 3]** Find another pair of q values in the table that land in the same drawer. What is their difference? Which fraction does it give?

### 5.3.3 Can you do better than 1/q²?

Computed by script: among all reduced fractions with denominators 2 ≤ q ≤ 100,000, count how many satisfy |π − p/q| < q^(−ν):

| ν | Number of fractions that satisfy it | Their denominators |
|---|---|---|
| 2 | 8 | 6, 7, 106, 113, 33102, 33215, 66317, 99532 |
| 2.2 | 2 | 7, 113 |
| 2.5 | 2 | 7, 113 |
| 3 | 2 | 7, 113 |

At ν = 2 the count keeps growing (Dirichlet guarantees infinitely many). Just above 2 a few remain (computed by script: denominators 6, 106, 33102, 33215, 66317 and 99532 have effective exponents between 2.01 and 2.11); once ν ≥ 2.2, within 100,000 only two "early miracles" remain: 22/7 and 355/113.

**μ(π) = 2 says exactly this**: for any ν > 2 (even 2.0001), there are only **finitely many** such fractions. There can be a few miracles early on, but miracles cannot keep appearing forever.

---

## 5.4 The irrationality exponent μ: definition and a "zoo"

### 5.4.1 Definition

> **Irrationality exponent** (also called the irrationality measure)
> μ(x) = the supremum of all ν such that "|x − p/q| < q^(−ν) has infinitely many solutions."

In plain words: μ(x) is the highest exponent at which x can be "exceptionally approximated infinitely many times." The bigger μ is, the easier it is to approximate x very well by fractions, and in that sense the "closer to rational" x is.

Continued-fraction version (a standard result): μ(x) = 2 + limsup (ln a_{n+1} / ln q_n). That is, **μ = 2 if and only if the partial quotients a_{n+1} grow more slowly than any positive power of q_n.**

An example computed by script: among the first 1000 terms of π's continued fraction, the largest partial quotient is 20776 (term 431), and the denominator of the convergent just before it has 216 digits. The effective exponent of this approximation is only **2.020**. With a denominator that big, even a partial quotient of more than 20,000 contributes almost nothing to the exponent. By contrast, 355/113 has effective exponent 3.20; that was "luck while the denominator was small."

### 5.4.2 The zoo

| Number | μ | Who proved it |
|---|---|---|
| Rational numbers | 1 | Trivial |
| Any irrational number | ≥ 2 | Dirichlet 1842 (§5.3) |
| Quadratic irrationals such as √2 | 2 | Liouville-type argument, see 4.3 |
| Any algebraic irrational (e.g. ∛2) | 2 | **Roth 1955**, Fields Medal 1958 |
| e | 2 | Computed directly from its patterned continued fraction |
| Almost every real number (in the Lebesgue-measure sense) | 2 | Khinchin (1920s), see 4.5 |
| Liouville number Σ 10^(−k!) | ∞ | Liouville, mid-19th century |
| π | Known ≤ 7.10; **OpenAI claims = 2** | See §5.5 and 7 |

### 5.4.3 A proof you can do by hand: why √2 can't be approximated exceptionally well

This small proof contains the core playbook of the whole chapter (including OpenAI's proof), so it is worth reading slowly.

For any fraction p/q, look at the integer p² − 2q²:
- It is **not 0** (because √2 is irrational).
- It is an **integer**.
- So |p² − 2q²| **≥ 1**.

On the other hand, p² − 2q² = q² (p/q − √2)(p/q + √2). So

```
|√2 − p/q| = |p² − 2q²| / (q² · (p/q + √2)) ≥ 1 / (q² · (p/q + √2)) ≈ 1/(2.83 q²)
```

The error is never smaller than about 0.35/q², so the effective exponent can't exceed 2, and μ(√2) = 2.

By hand for p/q = 7/5: p² − 2q² = 49 − 50 = −1, absolute value exactly 1. Predicted error = 1/(25 × (1.4 + 1.41421)) = 0.01421; actual |1.41421 − 1.4| = 0.01421. (The script also checked that for the convergents of √2, q² × error stays steady at around 0.35.)

**The core playbook**:
> Build a quantity tied to the approximation. **Arithmetically**: it is a nonzero integer, so it is ≥ 1. **Analytically**: if the approximation were too good, it would be < 1. The two contradict each other.

Remember this sentence; you will meet it again in §5.7.

### 5.4.4 Liouville numbers: the monsters with μ = ∞

L = Σ 10^(−k!) = 0.110001000000000000000001000… (the 1s are at decimal places 1, 2, 6, 24, 120, …).

Cut it off after one of the 1s, and the resulting fraction has a tiny error (computed by script):
- Cut at place 2: q = 10², error ≈ 10⁻⁶ = q^(−3)
- Cut at place 6: q = 10⁶, error ≈ 10⁻²⁴ = q^(−4)
- Cut at place 24: q = 10²⁴, error ≈ 10⁻¹²⁰ = q^(−5)

The effective exponents 3, 4, 5, … grow without bound, so μ(L) = ∞. Liouville used numbers of this kind to construct the first numbers in history that were **proved to be transcendental** (since algebraic numbers have finite μ, a number with μ = ∞ cannot be algebraic).

**This point is crucial for understanding the difficulty**: Liouville numbers are transcendental, with μ = ∞. π is also transcendental (Lindemann 1882). So **the fact that "π is transcendental" is of no help at all for μ(π)**: any argument that uses only "π is transcendental" would be refuted by Liouville numbers. To prove μ(π) = 2, you have to use structure that only π has.

### 5.4.5 Why "almost every number has μ = 2" is easy to prove

Throw a random point x into [0, 1]. For a fixed q, the region where "x is within q^(−ν) of some p/q" has total length about q small intervals × length 2q^(−ν) each = 2q^(1−ν).

Add this up over all q: Σ 2q^(1−ν). When ν > 2, the exponent 1 − ν < −1, and the sum **converges** (it is just 2 times ζ(ν−1) from §4; ζ(s) is finite for s > 1). Probability theory has a result called the Borel–Cantelli lemma: if the probabilities of a sequence of events have a finite sum, then almost surely only finitely many of the events happen. So almost every x has only finitely many exceptional approximations with exponent ν, and μ(x) ≤ ν. ν can be taken arbitrarily close to 2, so almost every x has μ = 2.

**This argument cannot be applied to π at all**: it is about "a random number," and π is one specific number. It's like how "almost nobody is left-handed" can't tell you whether a particular person is left-handed. This is the typical shape of problems like this: **typical behavior is obvious at a glance; a specific instance is extremely hard to prove** ("π is normal" has the same shape, and is still unsolved).

---

## 5.5 The history of upper bounds for π: 70 years from 42 to 7.1

### 5.5.1 Timeline

| Year | Author | Proved upper bound on μ(π) | Source |
|---|---|---|---|
| 1953 | Mahler | 42 (and said it could eventually be brought to 30) | *On the approximation of π*, Indag. Math. 15 |
| 1974 | Mignotte | 21 (all denominators) / 20 (eventually) | Bull. SMF Mém. 37 |
| 1993 | Hata | 8.01604539… | Acta Arith. 63 |
| 2008 | Salikhov | 7.606308… | Russ. Math. Surveys 63(3) |
| 2020 | Zeilberger–Zudilin | 7.103205334137… | Moscow J. Comb. Number Theory 9(4); arXiv:1912.06345 |
| 2026-09 | Bai (preprint) | 7.101862832357 | arXiv:2609.11276 ⚠ not peer-reviewed |
| 2026-09-24 | OpenAI (claimed) | **= 2** | §5.7 of this chapter |

(Values in the table follow the survey in §1.1 of the OpenAI paper, cross-checked against the deck author's research notes.)

Note the size of the last jump: the first 70 years went 42 → 7.10, each step a large amount of delicate work; then a single jump to 2, and it is an **exact value**, not yet another upper bound.

### 5.5.2 The ceiling of the old methods

All previous upper bounds came from the same framework (Zudilin's survey arXiv:math/0404523 explains it clearly):

1. Build a sequence of "linear forms" with integer coefficients, aₙπ − bₙ, that are **very small but not 0**. Usually these are built from carefully designed integrals.
2. Two quantities pull against each other:
   - how fast the linear form decays (faster is better);
   - how fast the coefficients aₙ grow (slower is better). To make the coefficients integers, you usually have to multiply by a large number like lcm(1, 2, …, n) to "clear denominators," and this cost is high.
3. A standard lemma: if the decay rate is e^(−βn) and the coefficient growth is e^(αn), you get μ ≤ 1 + α/β.

To get μ = 2 you need α and β to be almost equal, i.e. the "cost of clearing denominators" has to be almost zero. For every known integral construction for π, this ratio is far from 1. The Zeilberger–Zudilin generation of work was tightening screws inside this framework (optimizing the parameters of the integrals), and each time could only move the bound a little.

### 5.5.3 Why Roth's method can't be used directly

Roth's theorem gives μ = 2 for all algebraic numbers, and its method is **multivariable**: take several approximations p₁/q₁, p₂/q₂, … at once, with wildly different denominators, build a multivariable polynomial, and derive a contradiction using the "nonzero integer ≥ 1" playbook from §5.4.3.

But Roth's proof fundamentally uses the fact that x satisfies a polynomial equation with integer coefficients (x is algebraic). π is not algebraic, so there is no such equation to use. And as §5.4.4 said, you also can't use only "π is transcendental." OpenAI's reasoning summary happens to record the moment the model ran into this wall (verbatim):

> "Wait this would work for any transcend, contradiction with Liouville. Examine."

Meaning: it noticed that one of its arguments, if valid, would work for **all transcendental numbers**, but Liouville numbers are a counterexample, so the argument must have a hole.

---

## 5.6 A concrete consequence: the Flint Hills series

### 5.6.1 What the series is

```
Σ 1/(n³ sin² n) = 1/(1³ sin²1) + 1/(2³ sin²2) + 1/(3³ sin²3) + …     (n in radians)
```

The question: does it converge? Pickover popularized the problem, and it stayed a popular puzzle for more than two decades; Alekseyev 2011 (arXiv:1104.5100) discussed it systematically, and it remained unsolved.

### 5.6.2 Why it is related to approximating π

The denominator contains sin n. When an integer n is very close to some integer multiple kπ of π, sin n is very small, and that term blows up. And "n ≈ kπ" means "n/k ≈ π," i.e. **n/k is a good fractional approximation of π**.

Partial sums computed by script:

| n | This term | Partial sum |
|---|---|---|
| 1 | 1.412 | 1.412 |
| 3 | 1.860 | 3.423 |
| 21 | 0.00015 | 3.555 |
| **22** (22/7) | **1.199** | 4.754 |
| 354 | 3.2×10⁻⁸ | 4.807 |
| **355** (355/113) | **24.60** | 29.406 |
| 1,000 | 1.5×10⁻⁹ | 30.175 |
| 103,993 (103993/33102) | 2.4×10⁻⁶ | 30.3145 |
| 1,000,000 | 8.2×10⁻¹⁸ | 30.3145 |

Here are the partial sums for n ≤ 400, plotted:

{{FIG_FLINT}}

The whole curve is a staircase: most of the time it barely moves, and every time n hits the numerator of an exceptionally good approximation of π, it jumps. The n = 355 term alone contributes 24.6, which is 81% of the sum of the first 1 million terms.

**[Check 4]** Explain why the n = 355 term is about 24.6. (Hint: sin(355) = sin(355 − 113π), and 355 − 113π ≈ 3.01×10⁻⁵; the sine of a very small angle ≈ the angle itself.)

### 5.6.3 Whether it converges is decided entirely by μ(π)

- If π has infinitely many "too good" approximations, there will be infinitely many large enough jumps, and the series diverges.
- If exceptional approximations are rare enough, the jumps add up to something finite, and the series converges.

Two published criteria tie this precisely to μ(π):
- Alekseyev 2011: if the series converges, then μ(π) ≤ 5/2.
- Meiburg 2022 (arXiv:2208.13356): if μ(π) < 5/2, then the series converges.

So you only need to prove μ(π) < 2.5 to settle the problem. But the best known bound was 7.10, far away. OpenAI's reasoning summary shows that the model's initial goal was exactly μ < 5/2, and only later did it find it could push all the way to 2 (see §5.7.3).

The Flint Hills corollary in OpenAI's paper (Corollary 1.2) takes exactly this route: the main theorem gives μ(π) = 2 < 5/2, and Meiburg's published human result then gives convergence [P]. §5 of the paper also gives its own short proof (group the integers n by the nearest qπ, and control each group with |sin n| ≥ (2/π)·|n − qπ|), and derives a more general result: Σ 1/(nᵃ |sin n|ᵇ) converges if and only if a > max{1, b}.

---

## 5.7 What OpenAI claims

### 5.7.1 The main result

Abstract of the paper [*The irrationality exponent of π is 2*](https://github.com/openai/math/blob/main/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/paper.pdf) (OpenAI, 2026-09-24, 23 pages) [P]:

> "We prove the conjecture that the irrationality exponent of π is 2. As a consequence, the classical Flint–Hills series Σ_{n≥1} 1/(n³ sin² n) converges, with angles in radians."

The precise statement of the main theorem (Theorem 1.1):

> For every real number ν > 2, there exists an integer Q(ν) such that for all integers p and all q ≥ Q(ν), |π − p/q| ≥ q^(−ν).

The paper itself spells out three points (all important):
1. p/q is not required to be in lowest terms.
2. **Q(ν) is not effectively computable**: "the argument does not give it effectively". That is, it proves "from some denominator on, there are no more exceptional approximations with exponent ν," but does not tell you where that starts.
3. **μ = 2 is not the same as "bounded partial quotients"**: "an exponent of 2 is different from a uniform positive lower bound of the form c/q², or equivalently from bounded continued-fraction partial quotients". The latter (whether the partial quotients of π's continued fraction are bounded) is still unsolved.

The paper also records other claims in the same area: Mantzakouras and López Zapata's Flint Hills convergence claim was withdrawn in 2026-09; Carella claims μ(π) = 2 and the stronger "bounded partial quotients," and the OpenAI paper points out in a footnote that his proof of the stronger claim has a sign error (this is OpenAI's side of the story ⚠, with no third-party confirmation).

The paper says that Waldschmidt recorded this statement as a conjecture in *Open Diophantine problems* (Moscow Math. J. 4(1), 2004, p. 265).

### 5.7.2 Intuition for the method (we only read the introduction and the paper's §5; this is a simplified version)

Recall the playbook from §5.4.3: "a nonzero integer is ≥ 1, but an approximation that is too good would make it < 1." OpenAI's proof is a very heavy-duty version of this playbook.

1. **Proof by contradiction.** Fix some ν > 2, and assume π has infinitely many exceptional approximations with exponent ν.
2. **Pick a few, with widely separated denominators.** From these infinitely many, pick m of them, each denominator much bigger than the last: q₁ ≪ q₂ ≪ … ≪ q_m. This step is the same as Roth (multivariable, separated denominators).
3. **Use structure only π has: it is a period of the exponential function.** e^(2πi) = 1, so 2πi·j is a "period" of the exponential function, and also the source of the multivaluedness of the logarithm. The authors turn the exceptional approximations pᵢ/qᵢ into 2i·j·pᵢ/qᵢ, which approximate the true periods 2πi·j. This step answers the question from §5.4.4: the proof does not use "π is transcendental," but "this specific relationship between π and exp/log," which Liouville numbers do not have.
4. **Build a big determinant.** Take a multivariable polynomial P(Y, X₁, …, X_m), expand it along the "logarithmic curve" Y = 1 + t, Xᵢ = cᵢ + log(1 + t), take the Taylor coefficients, and arrange them into a big matrix. A new theorem in Section 2 of the paper ("separated-weight interpolation," using tools from algebraic geometry such as blowups and ampleness) guarantees that this matrix has full rank, so a **nonzero** determinant can be picked out.
5. **Arithmetic lower bound.** The matrix entries are all in ℚ(i) (of the form a + bi, with a and b fractions). After multiplying out the denominators, the determinant is a nonzero "Gaussian integer," with absolute value ≥ 1.
6. **Analytic upper bound.** Swap the approximations 2i·j·pᵢ/qᵢ back for the true periods 2πi·j, and many rows become Taylor coefficients of the same functions, nearly dependent on one another, so the determinant cancels heavily (the paper calls this "quadratic saving"); the remaining terms carry the tiny approximation errors |π − pᵢ/qᵢ| as factors. Result: the determinant has absolute value < 1.
7. **Contradiction.** ≥ 1 and < 1 at the same time is impossible, so the assumption is false, and there are only finitely many exceptional approximations with exponent ν.

Why it reaches any ν > 2: the dimension m (how many approximations you pick) can grow with ν. The higher the dimension, the faster the "cancellation saving" grows, until it eventually beats the cost of any ν > 2.
Why Q(ν) can't be computed: the argument starts from "assume there are infinitely many," and the approximations it picks have no concrete location. This is the same source as the "ineffectivity" of Roth's theorem.

### 5.7.3 The reasoning summary: how the AI got here

OpenAI released a 42-page "abridged chain-of-thought summary" ([`reasoning_traces/irrationality-exponent-of-pi.pdf`](https://github.com/openai/math/blob/main/reasoning_traces/irrationality-exponent-of-pi.pdf)) [P]. The script read its full table of contents; the structure is:

- **The summary's first part (sections 1–44)**: the goal is only the μ < 5/2 needed for Flint Hills. The model tried dozens of routes, including the BBP formula, modular forms, Padé approximation, the Chudnovsky series, p-adic logarithms and elliptic functions, and kept running into the wall it repeatedly called "height vs denominator cost" (height barrier), i.e. the "cost of clearing denominators" from §5.5.2. Along the way it repeatedly drew on the determinant idea from OpenAI's own Catalan's-constant manuscript (the phrase "OpenAI's Catalan determinants" recurs in the summary; the manuscript is covered in §5.7.4). In the end it used a weighted interpolation determinant to get μ ≤ 62/25 = 2.48, and hence Flint Hills convergence. Almost all the titles of sections 32–44 are "audit" or "stress-testing," i.e. repeated self-checking of this step.
- **The summary's second part (section 45)**: "takes the earlier report's interpolation-and-determinant technique as a starting point and claims exponent two, explicitly without assuming the earlier approximation bound". On the same technique, it tuned parameters and raised the dimension, pushing to μ = 2.

This document is itself a good case study of the research process: the goal was set conservatively (2.5), and the audit revealed that the technique's actual limit was 2.

### 5.7.4 Another result from the same release: Catalan's constant is irrational (family 005)

The "Catalan manuscript" that the reasoning summary keeps borrowing from is another paper in the same release: [*Catalan's constant is irrational*](https://github.com/openai/math/blob/main/preprints/Catalans-constant-is-irrational-September-24-2026/paper.pdf) (2026-09-24, 44 pages) [P]. It pairs with the π result: on method, the π proof borrowed its determinants; on the problem, it was stuck at the same wall as §5.5.2.

**What it is.** Catalan's constant G = 1 − 1/3² + 1/5² − 1/7² + … ≈ 0.91597. It is the value at s = 2 of the Dirichlet beta function β(s) = 1 − 1/3^s + 1/5^s − … (here β is a function name, unrelated to the decay rate β in §5.5.2). Put another way, it is the value at s = 2 of the Dirichlet L-function for the mod-4 character in §5.7.2 of §4.

**Why it was hard.** In the language of §5.5.2: to prove a constant irrational you want a sequence of integer linear forms aₙG − bₙ that are nonzero but tend to 0. In 1978 Apéry proved ζ(3) irrational this way (van der Poorten's article telling the story is titled *A proof that Euler missed*). The same idea fails for G: Zudilin built Apéry-like recurrences whose fractions bₙ/aₙ converge to G quickly, but after clearing denominators the linear forms **do not tend to 0**, so the "cost of clearing denominators" wins [P, as summarized in §1.1 of the paper]. The best previous results were family results: at least one of the five numbers β(2), β(4), …, β(10) is irrational (Rivoal–Zudilin 2003 first proved it up to β(14), Zudilin 2019 narrowed it to β(12), Lai–Zhou 2022 to β(10)), with no way to say which one.

**What OpenAI claims**: G is irrational. On the Lean side, `lean/docs/005.md` says the claim is formalized, and the challenge statement is `Irrational (∑' j : ℕ, (-1 : ℝ) ^ j / ((2 * j + 1 : ℕ) : ℝ) ^ 2)`, again using only standard Mathlib concepts [P]. The solution is about 981 files and 574,000 lines, and grep finds no `sorry` [P]. ⚠ It is likewise **not registered** in `formalization.yaml`; and unlike the π proof, it depends on Catalan modules that OpenAI added to the PrimeNumberTheoremAnd library by patch (the same ~40,000-line patch as in §5.9.2 of §4; we did not grep that part or run the comparator).

**If it holds**: it is one of the most important results of the "this single classical constant is irrational" kind in the nearly half-century since Apéry.

---

## 5.8 How far it has been verified

### 5.8.1 The Lean statement: you can read it yourself

The "challenge statement" file in the repo, `lean/ComparatorChallenges/PiExponent.lean` (it imports only Mathlib; the scope note is `lean/docs/017.md`) [P]:

```lean
theorem main :
  (∀ ν : ℝ, 2 < ν → ∃ Q : ℤ, 2 ≤ Q ∧
    ∀ p q : ℤ, Q ≤ q →
      (q : ℝ) ^ (-ν) ≤ |Real.pi - (p : ℝ) / (q : ℝ)|) ∧
  sSup {ν : ℝ | 0 < ν ∧
    Set.Infinite {r : ℚ | 2 ≤ r.den ∧
      0 < |Real.pi - (r : ℝ)| ∧
      |Real.pi - (r : ℝ)| < (r.den : ℝ) ^ (-ν)}} = 2
```

Piece by piece:
- **First part** (before the `∧`):
  - `∀ ν : ℝ, 2 < ν →`: for any real number ν greater than 2,
  - `∃ Q : ℤ, 2 ≤ Q ∧`: there exists an integer threshold Q ≥ 2,
  - `∀ p q : ℤ, Q ≤ q →`: such that for all integers p and all integers q ≥ Q,
  - `(q : ℝ) ^ (-ν) ≤ |Real.pi - p/q|`: the distance between π and p/q is at least q^(−ν).
  - This is exactly Theorem 1.1. Note that it only says "Q exists"; it does not give Q, consistent with the paper's "not effective."
- **Second part** (after the `∧`):
  - `{r : ℚ | 2 ≤ r.den ∧ 0 < |π − r| ∧ |π − r| < r.den^(−ν)}`: the set of all rationals with denominator ≥ 2 that are exceptional approximations with exponent ν (Lean's ℚ is automatically in lowest terms; `r.den` is the denominator).
  - `Set.Infinite …`: this set is infinite.
  - `sSup {ν | 0 < ν ∧ …} = 2`: the supremum of all ν that "have infinitely many solutions" is 2. This is the definition of μ from §5.4.1, matched word for word.

Two details worth noting:
- The statement **uses only Mathlib's standard definitions** (`Real.pi`, `sSup`, `Set.Infinite`, `ℚ`), and no concepts defined by OpenAI. This is much more trustworthy than "writing the statement with custom definitions."
- Lean's `sSup` has a "junk value" convention: for an empty set or a set with no upper bound, it returns 0. Here the conclusion is = 2, not = 0, so it does not fall into this trap.

### 5.8.2 The proof itself (counted by script on a local sparse clone, snapshot fd4aeeb) [P]

- Solution directory `lean/OAI/NumberTheory/PiExponent/`: **869 .lean files, 94,948 lines** (about 95,000).
- grep: 0 occurrences of `sorry`, 0 of `native_decide`, 0 custom `axiom`s.
- The comparator config `PiExponent.json` allows only the three standard axioms (`propext`, `Quot.sound`, `Classical.choice`).
- The solution imports only Mathlib and files in its own directory, and **does not depend on any patched external library in `lean/patches/`** (the script checked every import). Compare §4: the proof of the quasi-Riemann hypothesis depends on a patch library of about 40,000 lines, which is one of its main remaining risks; the π proof does not have this problem.
- The entry file `Main.lean` also contains a `flint_hills_summable`: it uses Mathlib's `Summable` to state that Σ 1/(n³ sin²n) converges, and gives a proof. But the official scope note `lean/docs/017.md` says Flint Hills is "outside this selected statement," meaning it is **not in the statement the comparator checks**. The accurate way to put it: a Lean proof of Flint Hills exists in the repo, but it has not gone through the same "statement–proof" comparison process as the main theorem.

### 5.8.3 What has not been done (⚠)

- ⚠ This formalization is **not registered** in `lean/formalization.yaml` (we grepped for PiExponent and 017 and found neither). It may have been missed in the 10-07 update.
- ⚠ We **did not compile and run** the comparator ourselves, and we **found no third-party re-check** (Dave Goldblatt's independent check in §4 covered only the ζ proof).
- On 2026-10-07, an issue appeared in Google DeepMind's formal-conjectures repository (#6909, by mo271) proposing to mark its `flint_hills_series_converges` as solved, but the issue itself notes it was "prepared with AI assistance and may contain mistakes" and asks people to check it first. When we looked, it had no comments.
- ⚠ **As of 2026-10-08, we found no named expert in Diophantine approximation / transcendental number theory publicly commenting on the correctness of this paper.** John D. Cook's 2026-10-07 blog post is only a popular explainer and does not assess the proof [R].

### 5.8.4 How to think about it

Compared with the quasi-Riemann hypothesis, this one is cleaner on the "machine verification" dimension: the statement uses only standard Mathlib concepts and reads like the textbook definition; the proof does not depend on a patch library; and the size (about 95,000 lines) is much smaller. If you trust that Mathlib's definitions of π, real powers and suprema are sound, and that the Lean kernel has no bugs, then "μ(π) = 2" is very credible in the machine sense. The remaining gaps are procedural (nobody has run a third-party comparator) and about understanding (no human expert has publicly said they understand the proof).

---

## 5.9 If true, what it means (and what it does not mean)

### 5.9.1 For mathematics: what it means

1. **A formally recorded conjecture is solved**: π is "typical" in its approximation properties, like almost every real number. The 70-year race of upper bounds (42 → 7.10) ends with an "exact value."
2. **The Flint Hills series converges**: a puzzle popular for more than two decades is settled, along with a complete convergence criterion for the more general Σ 1/(nᵃ |sin n|ᵇ).
3. **The method may matter more than the result.** If "separated-weight interpolation along the logarithmic curve + determinants" generalizes, the next targets would be the irrationality exponents of log 2, ζ(3) and other logarithm values (section 43 of the reasoning summary mentions the model "considered an extension to algebraic logarithms," but this is a speculative direction with no conclusion ⚠). The same family of determinant techniques was also used in the Catalan's-constant manuscript from the same release (§5.7.4).

### 5.9.2 For mathematics: what it does not mean

| Commonly confused claim | Relation to μ(π) = 2 |
|---|---|
| π is irrational | Long known (Lambert 1761). μ = 2 is far stronger than "irrational" |
| π is transcendental | Long known (Lindemann 1882). And transcendental numbers can have μ = ∞ (Liouville numbers), so neither implies the other |
| The partial quotients of π's continued fraction are bounded | **Still unsolved.** The paper says explicitly that μ = 2 is not the same thing |
| π is normal (every digit string appears with the same frequency) | **Still unsolved**; a completely different problem |
| You can compute "from which denominator on there are no more exceptional approximations" | **No**; Q(ν) is not effectively computable |
| Good approximations like 22/7 and 355/113 don't exist | Of course they exist. μ = 2 only says there are finitely many "miracles with exponent > 2" |

### 5.9.3 For computer science

Almost no direct impact.

- Floating-point trig functions need "argument reduction" (reducing a large x into the interval [−π/4, π/4]), and the worst case depends on how close some floating-point number gets to a multiple of π/2. But this is a **finite-range** problem (the range of a double is finite), and engineers long ago computed the worst cases directly with continued fractions (see J.-M. Muller, *Elementary Functions*, the chapter on argument reduction ⚠ check the original book for the exact chapter). An "asymptotic theorem that gives no threshold" will not change these concrete numbers.
- No connection to cryptography or complexity theory.

### 5.9.4 For AI

1. This is a relatively **easy-to-check** case of "AI solves a classical conjecture formally recorded in the literature": the statement is short, uses only standard definitions, and the Lean proof does not depend on a patch library. If you want to show someone "which results in this batch are the most trustworthy," it is a better example than the quasi-Riemann hypothesis (§4).
2. The reasoning summary shows a process feature worth studying: a conservative goal (2.5) + a long stretch of failed exploration (40-plus sections) + extensive self-auditing, ending with the discovery of the technique's true limit. This is useful for studying the research process of AI itself (and for eval design).
3. At the ecosystem level: in the same month there is Bai's 7.1018 preprint (the deck author's research notes record that Bai's acknowledgments mention help from OpenAI models ⚠ not checked against the original), a withdrawn Flint Hills claim, and an AI-drafted issue on formal-conjectures. The number of "AI-assisted math claims" is surging, and human expert reviewing bandwidth is still the bottleneck, consistent with the conclusion of §4.

---

## 5.10 Self-test

Try to answer these after reading. If you can't, go back and reread the corresponding section.

1. Why can't you judge a fractional approximation by the size of its error alone? How is the "effective exponent ν" defined? (§5.1.2)
2. Why is 355/113 especially accurate? Explain in the language of continued fractions. (§5.2.3)
3. Use the pigeonhole principle to explain why every irrational number has μ ≥ 2. (§5.3.2)
4. In the "nonzero integer ≥ 1" playbook, what quantity plays that role in the √2 proof, and in OpenAI's proof? (§5.4.3, 7.2)
5. Why doesn't "π is transcendental" help prove μ(π) = 2? What structure of π does OpenAI's proof use? (§5.4.4, 7.2)
6. Why are the partial sums of the Flint Hills series a staircase? Why is μ(π) < 5/2 enough to make it converge? (§5.6)
7. Which words in the definition of μ does the second part of the Lean statement, `sSup {…} = 2`, correspond to? (§5.8.1)
8. Does μ(π) = 2 imply "the partial quotients of π's continued fraction are bounded"? Does it imply "π is normal"? (§5.9.2)

---

## Appendix: answers to the checks

- **Check 1**: 355/113 = 3.14159292…, which differs from π by about 2.67×10⁻⁷; 113² = 12769; the product is about 0.0034, i.e. about 290 times better than 1/q².
- **Check 2**: 355 = 3 × 113 + 16, so 355/113 = 3 + 16/113 = 3 + 1/(113/16); 113 = 7 × 16 + 1, so 113/16 = 7 + 1/16. Putting it together, 355/113 = [3; 7, 16]. (π itself is [3; 7, 15, 1, …], and [3; 7, 15, 1] = [3; 7, 16]; the two forms are the same fraction.)
- **Check 3**: q = 2 (0.283) and q = 9 (0.274) are both in [0.2, 0.3); the difference is 7, giving 22/7 again. (q = 3 and q = 10 are both in [0.4, 0.5), also with difference 7. With Q = 10 the pigeonhole principle can only "see" fractions with denominator ≤ 10, and the best of those is 22/7.)
- **Check 4**: sin(355) = sin(355 − 113π) ≈ 3.01×10⁻⁵ (computed by script: 355 − 113π = 3.0144×10⁻⁵). sin² ≈ 9.09×10⁻¹⁰; 355³ ≈ 4.47×10⁷; the product ≈ 0.0407, and its reciprocal ≈ 24.6.

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| Effective exponent ν | If \|x − p/q\| ≈ q^(−ν), then ν is how "exceptional" this approximation is |
| Continued fraction | The expansion [a₀; a₁, a₂, …] obtained by repeatedly "taking the integer part, taking the reciprocal" |
| Convergent | A fraction obtained by truncating a continued fraction; the best approximation among fractions with comparable denominators |
| Partial quotient | Each aᵢ in a continued fraction; the bigger it is, the more accurate the convergent just before it |
| Dirichlet's approximation theorem | Every irrational number has infinitely many approximations with \|x − p/q\| < 1/q² |
| Irrationality exponent μ(x) | The largest ν at which x can be approximated "infinitely many times" to accuracy q^(−ν) |
| Algebraic number | A root of some polynomial with integer coefficients, such as √2 or ∛2 |
| Transcendental number | A number that is not algebraic, such as π, e, or Liouville numbers |
| Roth's theorem | Every algebraic irrational has μ = 2 (1955, Fields Medal) |
| Liouville number | A number with μ = ∞, e.g. Σ 10^(−k!) |
| Linear form aπ − b | The "very small but nonzero" quantity built by the old methods to put an upper bound on μ |
| Ineffective | A proof shows a constant exists but cannot compute its value |
| Flint Hills series | Σ 1/(n³ sin²n); whether it converges is decided by μ(π) |
| Bounded partial quotients (badly approximable) | \|x − p/q\| ≥ c/q² holds for all fractions; stronger than μ = 2 |
| Normal number | A number in whose expansion every digit string appears with the same frequency; unrelated to μ |
| Catalan's constant G | 1 − 1/3² + 1/5² − …; OpenAI claims, in the same release, to prove it irrational (§5.7.4) |

## Appendix: Further reading

- **Numberphile**, *The Golden Ratio (why it is so irrational)* (YouTube, Ben Sparks): an intuitive version of §5.2.4's "the golden ratio is the hardest number to approximate," which is about its continued fraction being all 1s.
- **Mathologer**, *Infinite fractions and the most irrational number* (YouTube): continued fractions and approximation, with clear animations.
- **A. Ya. Khinchin**, *Continued Fractions* (Dover reprint): a slim book, the classical source for §5.2–5.4 and §5.4.5; readable with undergraduate math.
- **Wadim Zudilin**, *An essay on irrationality measures of π and other logarithms*, arXiv:math/0404523: the authoritative survey of §5.5.2's "linear forms framework."
- **Michel Waldschmidt**, *Open Diophantine problems*, Moscow Math. J. 4(1), 2004: https://webusers.imj-prg.fr/~michel.waldschmidt/articles/pdf/odp.pdf (p. 265 records this conjecture)
- Zeilberger–Zudilin, arXiv:1912.06345; Alekseyev, arXiv:1104.5100; Meiburg, arXiv:2208.13356.
- Original paper: https://github.com/openai/math/blob/main/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/paper.pdf
- Reasoning summary: https://github.com/openai/math/blob/main/reasoning_traces/irrationality-exponent-of-pi.pdf
- Lean scope note: https://github.com/openai/math/blob/main/lean/docs/017.md ; challenge statement: https://github.com/openai/math/blob/main/lean/ComparatorChallenges/PiExponent.lean
- Catalan's-constant paper (§5.7.4): https://github.com/openai/math/blob/main/preprints/Catalans-constant-is-irrational-September-24-2026/paper.pdf ; Lean scope note: https://github.com/openai/math/blob/main/lean/docs/005.md
- formal-conjectures issue #6909: https://github.com/google-deepmind/formal-conjectures/issues/6909
- John D. Cook popular explainer: https://www.johndcook.com/blog/2026/10/07/irrationality-exponent-of-pi/
