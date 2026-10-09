# The quasi-Riemann hypothesis: a ceiling on the noise in the primes

> Number theory · OpenAI family 003. All you need going in: you can work with powers and logarithms, you know the summation sign Σ, and you know what a function is. Every new concept is explained before it is used.
> Every number in this chapter was either computed by script or has a source. Tags: [P] = a primary source we read directly (paper, repo file, Lean source), [R] = secondary reporting, ⚠ = unverified or doubtful. The **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter.
> Estimated reading time: 60–90 minutes. You can read it in three sittings: §4.1–4.3 (primes and the error), §4.4–4.6 (the ζ function and its zeros), §4.7–4.10 (OpenAI's result and what it means).

---

## 4.0 The bottom line: the one thing this chapter explains

Prime numbers (2, 3, 5, 7, 11, …) look randomly scattered, but taken as a whole they are very regular. Mathematicians can write down a formula that predicts, accurately, "roughly how many primes there are up to x." The truly hard question is: **how wrong can that prediction be, at most?**

This chapter explains one causal chain:

> How big the prediction error is ⟸ is determined by a set of "waves" ⟸ each wave corresponds to a "zero" of the ζ function ⟸ the farther a zero sits from a certain line, the bigger the error.

The Riemann hypothesis says that all the zeros line up neatly on one line, so the error is as small as it can be. Nobody can prove it.

The **quasi-Riemann hypothesis** is a much weaker version. It does not require the zeros to lie on that line; it only requires that they **not sit too far to the right**. Nobody has proved even this weak version in 125 years. OpenAI claims to have proved it.

After reading this chapter, you should be able to explain in your own words:
- what exactly the relationship is between "zeros" and "the error in counting primes";
- why there is a qualitative difference between "a zero-free region that gets narrower and narrower" and "a zero-free region of fixed width";
- what OpenAI's claimed result, if true, concretely means, and what it does not mean.

---

## 4.1 Primes: count them, look for a pattern

### 4.1.1 What primes are and why they matter

A prime is an integer greater than 1 that is divisible only by 1 and itself: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, …

They matter because **every integer can be split into a product of primes in exactly one way** (the fundamental theorem of arithmetic):
- 12 = 2 × 2 × 3
- 360 = 2 × 2 × 2 × 3 × 3 × 5

So primes are the "atoms" of the integers. The HTTPS encryption (RSA) you use every day rests on one fact: multiplying two large primes is easy, but splitting the product back apart is extremely hard.

### 4.1.2 Counting

Write **π(x)** for "the number of primes that are at most x." This π is just a name. It has nothing to do with the circle constant; it is a historical notation.

| x | π(x) (actual count) |
|---|---|
| 10 | 4 (2, 3, 5, 7) |
| 100 | 25 |
| 1,000 | 168 |
| 1,000,000 | 78,498 |
| 1,000,000,000 | 50,847,534 |

Primes get sparser as you go further out. Below 100, one number in four is prime. Near 1 million, only about 72 in every 1000 numbers are prime (that is the estimate from the 1/ln x rule in the next section; counted by script, the 1000 numbers from 999,001 to 1,000,000 actually contain 65 primes).

### 4.1.3 The first pattern: the density is about 1/ln x

As a teenager, Gauss stared at prime tables and noticed: **near x, about one number in every ln x is prime.**

Here ln is the natural logarithm, with base e ≈ 2.718. ln(1,000,000) ≈ 13.8, which means that near 1 million about one number in 14 is prime. The script count above was 65 per 1000, or about one in 15. Very close.

**[Check 1]** ln(1000) ≈ 6.9. By this rule, about how many primes are there per 1000 numbers near 1000?

### 4.1.4 The prime number theorem

Integrate the "density 1/ln t" from 2 to x and you get a prediction for the number of primes up to x:

```
π(x) ≈ Li(x) = ∫₂ˣ dt / ln t
```

Li(x) is called the "logarithmic integral." If you are not comfortable with integrals, that is fine: think of it as "add up the density 1/ln t at every position."

| x | actual π(x) | rough prediction x/ln x | precise prediction Li(x) | error of Li |
|---|---|---|---|---|
| 1,000 | 168 | 145 | 177 | +9 |
| 1,000,000 | 78,498 | 72,382 | 78,627 | +129 |
| 1,000,000,000 | 50,847,534 | 48,254,942 | 50,849,235 | +1,701 |

(Li(10⁹) uses the standard value from the literature; the rest were computed by script.)

The **prime number theorem** (proved independently by Hadamard and de la Vallée Poussin in 1896) says that the **ratio** of π(x) to Li(x) tends to 1. You can see this in the table: the absolute error is growing (9 → 129 → 1,701), but relative to the total it becomes more and more negligible (at 10⁹ it is off by only 0.3 parts in 10,000).

---

## 4.2 The real question: how big is the error?

### 4.2.1 Two ways of saying "the error is getting smaller," with very different strength

The prime number theorem only says "error / x → 0," that is, the relative error goes to 0. It does not say **how fast** it goes to 0.

An intuitive way to measure this: roughly what power of x is the error?
- If the error ≈ x^0.5 = √x: at 10⁹, √x ≈ 31,623. The actual error in the table above, 1,701, is even smaller than that.
- If the error ≈ x^0.875 = x^(7/8): at 10⁹ this is about 75 million, far bigger than the actual error.

Note: the **actual error** and the **error bound you can prove** are two different things. Numerically, the actual error is very small (roughly on the order of √x). But mathematicians need a **proof**: "for all x, the error is definitely no more than such-and-such." Everything in this chapter is about the **bound you can prove**.

### 4.2.2 "Power saving": why x^(7/8) is a qualitative change

Since 1958, the best provable bound has roughly had the form:

```
error ≤ x · exp(−c · (ln x)^0.6)       (c is some small constant)
```

Compare this with x^(7/8) by looking at how "error / x" (the relative error) changes with x. To compare the trends, take c = 1 below (the real c is smaller, so the old bound is actually even worse):

| x | relative error of the old bound exp(−(ln x)^0.6) | relative error of the new bound x^(−1/8) |
|---|---|---|
| 10¹⁰⁰ | 10^(−11.4) | 10^(−12.5) |
| 10¹⁰⁰⁰ | 10^(−45.2) | 10^(−125) |
| 10¹⁰⁰⁰⁰ | 10^(−180) | 10^(−1250) |

(Computed by script.)

The old bound also shrinks, but **more slowly than any "negative power of x."** The new bound is "x to the power −1/8," and the gap widens the further out you go. Mathematicians call this a **power saving**: the error is smaller than x by a fixed power.

**Why this matters**: many harder problems in number theory plug the error term of the prime number theorem into further calculations. If the error is only "a little" smaller than x (like the old bound), it often gets swamped by other error terms once you plug it in. If it is smaller by a fixed power, you have room to spare for all kinds of consequences.

---

## 4.3 The key turn: the error is made of "waves"

This was Riemann's stroke of genius in 1859, and it is the single most important step in the chapter.

### 4.3.1 First, an analogy with sound

A sound (say, a chord) can be broken down into a sum of pure tones (sine waves). Each pure tone has two properties:
- **frequency**: how fast it vibrates
- **amplitude**: how loud it is

This is called **Fourier decomposition**. The EEG spectra you saw in neuroscience (alpha waves at 8–12 Hz, beta waves, …) are the same idea: break a complicated signal into waves of different frequencies.

### 4.3.2 Riemann's discovery

Riemann discovered that the error in counting primes can be broken down the same way:

```
(weighted count of primes) = (smooth main term) − Σ(individual "waves") − (some small corrections)
```

(To keep the formula clean, mathematicians usually use a weighted version of the prime count, ψ(x), in which each prime p gets weight ln p. It is essentially the same thing as π(x).)

The main term is smooth, roughly just x. All of the error comes from those "waves," and:
- **Each wave corresponds to one zero of the ζ function** (§4.5 explains what a zero is).
- A zero is written in the form ρ = β + iγ, with two coordinates β and γ.
- **γ determines the wave's frequency** (how fast it oscillates).
- **β determines how fast the wave's amplitude grows with x**: the size of this wave is about x^β.

So:
- If every zero has β equal to 1/2, each wave has size about √x, and the error is about √x. This is exactly the **Riemann hypothesis**.
- If some zero has β close to 1, its wave has size close to x, almost as big as the main term, and the error will be huge.
- If you can prove that **every zero has β at most θ**, then the error is at most about x^θ.

**In one sentence: the β coordinate of the zeros (how far "to the right" they sit) directly determines how big the error in counting primes is.** That is why number theorists care so much about "where the zeros are."

### 4.3.3 Why complex numbers show up

To describe these "waves" we need complex numbers. The next section explains them first.

---

## 4.4 Complex numbers: the 5-minute version

### 4.4.1 A complex number is a point in the plane

Real numbers sit on a line. **Complex numbers are points in a plane**: the horizontal coordinate is called the real part, the vertical coordinate the imaginary part.

```
s = σ + i·t      σ is the horizontal coordinate (real part, written Re s), t is the vertical coordinate (imaginary part, written Im s)
```

i is a symbol satisfying i² = −1. Don't worry about whether it "exists"; treat it as a marker for "one step in the vertical direction" and that is enough.

### 4.4.2 Multiplying by a complex number = scaling + rotation

The most useful property of complex numbers: **multiplying by a complex number rotates a point around the origin and scales it.** For example, multiplying by i rotates 90 degrees counterclockwise: 1 → i → −1 → −i → 1, one full turn.

### 4.4.3 x to a complex power = "size part" × "rotation part"

For a positive real number x and a complex number β + iγ:

```
x^(β+iγ) = x^β × (cos(γ·ln x) + i·sin(γ·ln x))
```

- **x^β** is the size part: it grows with x, and how fast is set by β.
- **cos(γ·ln x) + i·sin(γ·ln x)** is the rotation part: its length is always 1; it just goes around the unit circle. How fast it turns is set by γ.

These are the "waves" from §4.3: **β controls the amplitude (x^β), γ controls the frequency (oscillation on the scale of ln x).**

---

## 4.5 The ζ function and its zeros

### 4.5.1 Definition of the ζ function

```
ζ(s) = 1/1^s + 1/2^s + 1/3^s + 1/4^s + ...
```

**At s = 2**: ζ(2) = 1 + 1/4 + 1/9 + 1/16 + … = π²/6 ≈ 1.6449 (computed by Euler in 1734; here π is the circle constant).

**At s = 1**: ζ(1) = 1 + 1/2 + 1/3 + 1/4 + …, the "harmonic series," which **diverges to infinity**. Computed by script: the sum of the first 1000 terms ≈ 7.49, the first 1 million terms ≈ 14.39. It grows very slowly but never stops.

### 4.5.2 The Euler product: how ζ "knows" about primes

Euler discovered:

```
ζ(s) = 1/(1−2^(−s)) × 1/(1−3^(−s)) × 1/(1−5^(−s)) × 1/(1−7^(−s)) × ...   (product over all primes)
```

**Why it holds**: each factor 1/(1−p^(−s)) expands into 1 + 1/p^s + 1/p^(2s) + … (a geometric series). Multiply these expansions together over all primes, and every term has the form 1/(p₁^a · p₂^b · …)^s. Because every integer has a **unique** prime factorization, each 1/n^s appears exactly once, and the product is exactly ζ(s).

**By hand for s = 2** (checked by script):
- Multiplying only the three factors for p = 2, 3, 5: (4/3)(9/8)(25/24) = 1.5625
- Multiplying the factors for all primes below 100: 1.6419
- True value π²/6 = 1.6449

So **the ζ function ties "all integers" to "all primes"**, and this is the bridge for the whole story.

**A beautiful consequence** (Euler's proof that "there are infinitely many primes"): at s = 1 the left side is the harmonic series, which diverges to infinity. If there were only finitely many primes, the right side would be a product of finitely many finite numbers and could not be infinite. So there must be infinitely many primes.

### 4.5.3 "Analytic continuation": extending the definition to the whole plane

The sum above only converges (adds up to a finite number) when the real part of s is > 1. But Riemann needed to talk about ζ(s) on the whole complex plane.

An analogy for how to extend it:

```
1 + x + x² + x³ + ... = 1/(1−x)
```

The left side converges only when |x| < 1 (for example, at x = 2 the left side is 1+2+4+8+…, which diverges), but the right side 1/(1−x) makes sense everywhere except x = 1 (at x = 2 it equals −1). We can **use the right side to define** something that originally only made sense for |x| < 1. This is called **analytic continuation**.

One can prove mathematically that such a continuation, if it exists, is unique. Riemann used a similar but more elaborate technique to continue ζ(s) to the whole complex plane (except the single point s = 1).

### 4.5.4 Zeros

A **zero** is a complex number s that makes ζ(s) = 0.
- **Trivial zeros**: s = −2, −4, −6, …, which come from a simple factor in the continuation formula. Nothing mysterious.
- **Non-trivial zeros**: all the other zeros. They all lie in the vertical strip **0 < Re s < 1**, which is called the **critical strip**.

The first three non-trivial zeros (in the upper half-plane) are approximately:

```
½ + 14.13i,   ½ + 21.02i,   ½ + 25.01i
```

Their real parts are all exactly 1/2.

### 4.5.5 The Riemann hypothesis

> **Riemann hypothesis (1859)**: every non-trivial zero has real part equal to 1/2.

Numerical checks have examined **more than ten trillion zeros**, all on the line Re s = 1/2 (Gourdon in 2004 verified the first 10¹³ zeros ⚠ defer to the original paper for the exact figure). But no amount of checking is a proof. It is one of the seven Clay Millennium Prize Problems, with a $1 million prize.

Connecting §4.3 to here: **Riemann hypothesis ⇔ every wave has amplitude √x ⇔ the error in counting primes is about √x.**

---

## 4.6 Zero-free regions: what can be proved when the Riemann hypothesis can't

Since nobody can prove "all zeros are on the line 1/2," mathematicians take a step back and ask: **can we at least prove where the zeros are not?** A region proved to contain no zeros is called a **zero-free region**.

### 4.6.1 Step one: no zeros on the line Re s = 1 (1896)

The proof of the prime number theorem essentially amounts to proving that **there are no zeros on the vertical line Re s = 1**.

The key trick is a trigonometric identity:

```
3 + 4cos θ + cos 2θ ≥ 0      (holds for all θ)
```

**[Check 2]** Use cos 2θ = 2cos²θ − 1 to prove that 3 + 4cos θ + cos 2θ = 2(1 + cos θ)², so it is always ≥ 0. (The script swept 6,284 points on [0, 2π]; the minimum was 1.4×10⁻¹⁴, i.e. 0 plus rounding error.)

Combining this identity with the Euler product, one can show that if 1 + iγ were a zero, it would lead to a contradiction.

### 4.6.2 Step two: a strip to the left of Re s = 1 that "keeps getting narrower" (1899, 1958)

de la Vallée Poussin (1899) pushed the result a little further: not only are there no zeros on Re s = 1, there are none in **a narrow strip to its left** either:

```
zero-free region: Re s > 1 − c / ln(t)     (t is the height, i.e. the imaginary part)
```

Note the ln t in the denominator: **the bigger the height t, the narrower this strip.**
- At t = 100, the width is about c / 4.6
- At t = 10¹⁰, the width is about c / 23
- As t → ∞, the width → 0

Vinogradov–Korobov (1958) widened the strip a bit (the denominator changes from ln t to (ln t)^(2/3) times an even smaller factor), but **it still shrinks toward 0 with height**. This was the best result for the following 60-plus years.

### 4.6.3 Why "keeps getting narrower" and "fixed width" are qualitatively different

Back to §4.3: the error is the sum of the waves from all zeros, and **the rightmost zero** sets the size of the error.
- If the zero-free region keeps getting narrower: in principle, higher and higher up there could be zeros whose β gets closer and closer to 1. You cannot rule them out, so the error bound can only be "a little" smaller than x. That is the exp(−c(ln x)^0.6) from §4.2.
- If there is a zero-free region of **fixed width**, say no zeros at all in Re s > 7/8: then every zero has β ≤ 7/8, every wave is ≤ x^(7/8), and the error bound becomes of order x^(7/8). That is the **power saving** from §4.2.

The **quasi-Riemann hypothesis** is exactly such a statement:

> There is some θ < 1 such that ζ has no zeros anywhere in the region Re s > θ.

It is much weaker than the Riemann hypothesis (θ = 1/2), but before 2026 **nobody could prove it for any θ < 1**.

The figure below puts §4.5 and this section on one picture of the complex plane: the known zeros, the classical zero-free region that narrows as you go up, and the fixed-width zero-free region OpenAI claims.

{{FIG_ZETA}}

### 4.6.4 Why the classical methods can't do it

The "3 + 4cos θ + cos 2θ ≥ 0"-type argument from §4.6.1 starts from properties of the Euler product in Re s > 1 and "seeps" a little way to the left. But this seeping power decays with the height t, so all you can get is a strip that keeps getting narrower. To get a fixed width, you need **a fundamentally different mechanism**.

Another line of attack is called "zero-density estimates" (for example, the important breakthrough of Guth–Maynard 2024, [arXiv:2405.20552](https://arxiv.org/abs/2405.20552)). These can prove that "there are **few** zeros with Re s > σ," but not that "there are **none at all**." The introduction of OpenAI's paper makes the same distinction explicitly [P]. And for the error bound, even a single zero with β close to 1 is enough to make the error large.

---

## 4.7 Dirichlet L-functions and Siegel zeros

OpenAI's result is not only about ζ; it also covers all **Dirichlet L-functions**.

### 4.7.1 Primes in arithmetic progressions

Apart from 2, all primes are odd, so each has the form 4k+1 (5, 13, 17, …) or 4k+3 (3, 7, 11, 19, …).

Computed by script:
- Below 100: 11 of type 4k+1, 13 of type 4k+3
- Below 1000: 80 of type 4k+1, 87 of type 4k+3

The two types are roughly half and half (type 4k+3 is usually slightly ahead, but not always: at x = 26,861 type 4k+1 takes the lead for the first time; this phenomenon is called Chebyshev's bias). In 1837 Dirichlet proved that for any modulus q and any a coprime to q, there are infinitely many primes of the form qk + a, and that in the long run the classes split evenly.

### 4.7.2 Dirichlet L-functions

To study each class separately, Dirichlet built variants of ζ:

```
L(s, χ) = χ(1)/1^s + χ(2)/2^s + χ(3)/3^s + ...
```

χ (pronounced "chi") is called a "character." It is a function that maps integers to certain complex numbers, and its job is to "pick out" and "tell apart" the different residue classes. For example, the non-trivial character mod 4: χ(odd numbers 4k+1) = 1, χ(odd numbers 4k+3) = −1, χ(even numbers) = 0.

**Just like ζ, the zeros of L-functions control the error in the distribution of primes across the classes mod q.**

### 4.7.3 Siegel zeros: a ghost that has haunted the field for 90 years

For certain special L-functions, classical methods cannot rule out one possibility: **that it has a real zero very, very close to 1**. Such a hypothetical zero is called a **Siegel zero** (or Landau–Siegel zero).

If one exists, the consequences are strange: primes for the corresponding modulus would be heavily skewed toward certain residue classes. Although people widely believe it does not exist, nobody can rule it out.

Worse, Siegel's related theorem from 1935 is "ineffective": it proves that a certain constant **exists** but tells you nothing at all about **how big** it is. As a result, a whole set of problems, such as "how large is the class number of an imaginary quadratic field at least," can only get "there exists a bound," not an actual number.

**If the quasi-Riemann hypothesis holds for all Dirichlet L-functions, Siegel zeros are automatically ruled out**: there are no zeros anywhere in Re s > 7/8, so of course there is no zero close to 1.

---

## 4.8 What OpenAI claims

### 4.8.1 The main result

Abstract of the paper [*The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane ℜs > 7/8*](https://github.com/openai/math/blob/main/preprints/The-Quasi-Riemann-Hypothesis-September-30-2026/paper.pdf) (2026-09-30, 199 pages) [P]:

> "We prove that all finite-order Hecke L-functions over Q(√−3) and all Dirichlet L-functions are zero-free in the half-plane ℜs > 7/8 … In particular, the Riemann zeta function is zero-free in this half-plane, proving the quasi-Riemann hypothesis."

In plain terms: **ζ and all Dirichlet L-functions have no zeros anywhere in the half-plane Re s > 7/8.**

The paper itself makes a point of stressing: "The Riemann hypothesis remains open." The Riemann hypothesis says the zeros are all at 1/2; this only proves they are all ≤ 7/8. Between 7/8 and 1/2 there is still a large unknown territory.

There are two more papers in the same family (family 003): one proves an 11/12 version by a different method (49 pages; the README says its writing was edited by humans), and a 9-page paper separately proves that Siegel zeros are uniformly ruled out.

### 4.8.2 Intuition for the method (we only read the introduction; this is a simplified version)

1. **Switch number systems.** Instead of working in the ordinary integers, work in the "Eisenstein integers" ℤ[ω], where ω is a cube root of unity: ω³ = 1, ω ≠ 1. You can picture them as a triangular lattice of points in the plane (the ordinary integers are points on a line, the Gaussian integers a square lattice, the Eisenstein integers a triangular lattice). The field corresponding to this number system is written ℚ(√−3).
2. **Build one quantity and compute it two ways.** The authors build a sum from the Fourier coefficients of a "cubic theta series" (the paper calls it a "completed sum"), which can be computed along two independent routes: one uses a "reflection formula," the other uses "Poisson summation." The result of the second route contains terms like 1/L(s, η), i.e. the reciprocal of an L-function.
3. **Contradiction.** If some L-function had a zero in Re s > 7/8, 1/L would blow up there, and the two computations could not agree. Think of it as weighing the same object on two independent scales: if an assumption would make the two scales read differently, the assumption is wrong.
4. **Transfer to ordinary Dirichlet L-functions.** Using a factorization formula L_F(s, χ∘N) = L(s, χ) · L(s, χχ₋₃), the conclusion over ℚ(√−3) can be "split" back into L-functions over the ordinary integers, including ζ.

Technically there are two stages: first a simpler version gives 11/12, then extra correction terms push it to 7/8. The tools used include the sextic large sieve, Heath-Brown's estimates for cubic sums, and Dunn–Radziwiłł's 2024 Annals result on the Patterson conjecture.

---

## 4.9 How far it has been verified

### 4.9.1 The Lean statement: one line, and you can read it yourself

The "challenge statement" file in the repo, `lean/ComparatorChallenges/QuasiRiemannHypothesis.lean` (it imports only Mathlib) [P]:

```lean
theorem riemannZeta_ne_zero_of_seven_eighths_lt_re {s : ℂ} (hs : (7/8 : ℝ) < s.re) :
    riemannZeta s ≠ 0
```

Word by word:
- `theorem …`: the name of the theorem, which literally means "ζ is nonzero when the real part is greater than 7/8."
- `{s : ℂ}`: s is a complex number (ℂ is the set of complex numbers).
- `(hs : (7/8 : ℝ) < s.re)`: the hypothesis hs is "the real part of s > 7/8."
- `riemannZeta s ≠ 0`: the conclusion is "ζ(s) is not equal to 0."

So this one line says: **for any complex number s, if its real part is greater than 7/8, then ζ(s) ≠ 0.** That is exactly the quasi-Riemann hypothesis.

The `riemannZeta` here is the **standard definition** that has long been maintained in Mathlib (Lean's community mathematics library), not something OpenAI wrote itself. This matters: if the definition were home-made, it could quietly "change the subject."

### 4.9.2 The proof itself

- The proof is about 2,926 Lean files and 487,000 lines [P].
- We grepped it: no `sorry` ("leave this step blank for now"), no added axioms, no `native_decide` (a backdoor that trusts the compiler) [P].
- Independent re-check: Dave Goldblatt used the Lean FRO's Comparator tool, plus an independently implemented checking kernel (nanoda), and got the proof to go through, in about 63 minutes; `#print axioms` lists only the three standard axioms (`propext`, `Quot.sound`, `Classical.choice`) [P]. Re-check repo: [davegoldblatt/openai-zeta-proof-check](https://github.com/davegoldblatt/openai-zeta-proof-check).
- ⚠ **Remaining risk**: the dependency patch `lean/patches/PrimeNumberTheoremAnd-lean4341.patch` is about 40,000 lines, and in it two upstream `sorry`s were removed and replaced with proofs. In other words, part of the so-called "dependency library" is OpenAI's own code. (PrimeNumberTheoremAnd is the prime-number-theorem formalization project that Kontorovich, quoted below, started.) The Lean kernel checks these proofs, but if definitions were changed, that could affect what the statement means. Nobody has reviewed this line by line yet.
- **The formalization covers only the zero-free regions themselves.** Comparator checks four statements: the 7/8 zero-free region for ζ, for Dirichlet L-functions and for Hecke L-functions over ℚ(√−3), plus a uniform gap for Siegel zeros. The scope note `lean/docs/003.md` says, verbatim, "The paper's later applications are not included" [P]. So the least-quadratic-non-residue bound and the square-root algorithm in §4.10.2 have only the paper's human-readable proof, not a Lean proof.

### 4.9.3 Human experts

- Alex Kontorovich (Rutgers; he himself started PrimeNumberTheoremAnd, the Lean formalization project for the prime number theorem): "Quasi-RH?!?!???! Are you kidding me? If a human did this, it would be an instant Fields Medal…" [R] ([X post](https://x.com/AlexKontorovich/status/2107609087902941646); we quote it via officechai, as the original post could not be fetched)
- Levent Alpöge (Anthropic): "Big, big, big, big props for quasiriemann and no Siegel zeroes." [R] ([X post](https://x.com/__alpoge__/status/2107616859595981117), quoted via Latent Space)
- ⚠ **As of 2026-10-08, no human expert has publicly said they have read and verified the 199-page paper.** Both comments above are reactions, not referee reports.

### 4.9.4 How to think about "proved by machine, but not understood by people"

If you believe two things, (1) Mathlib's definition of ζ is correct and (2) the Lean kernel has no bugs, then this theorem has been proved in the machine sense, and it is an order of magnitude more trustworthy than a paper nobody has refereed. The remaining risk sits in the build chain: the patches and dependency libraries all come from OpenAI (see 9.2).

But the mathematical community usually also asks for **understanding**: why is it true? Does the method generalize? This is what Tao means by "the end of Math 1.0": a conclusion can be confirmed by machine first, and understanding may only catch up much later.

---

## 4.10 If true, what it means (and what it does not mean)

### 4.10.1 For mathematics

1. **For the first time, the prime number theorem has an error bound with a power saving**: π(x) − Li(x) = O(x^(7/8) · (ln x)²). This is one of the biggest single steps forward in the theory of the distribution of primes in 125 years.
2. **Siegel zeros are ruled out**: an obstacle that since 1935 has blocked a set of "can this constant be computed?" problems disappears, and a large batch of constants that "exist but can't be computed" become computable, e.g. effective lower bounds for class numbers of imaginary quadratic fields (§4.7.3).
3. **Pushing from 1 to 7/8 is a qualitative change, but it is still far from 1/2.** The Riemann hypothesis remains open.

### 4.10.2 For computer science: square roots mod p

One of the paper's corollaries is an upper bound on the "least quadratic non-residue." First, what that means.

**Quadratic residue**: a number that "is the square of something" mod p. Take p = 7 as an example:
- 1² = 1, 2² = 4, 3² = 9 ≡ 2, 4² = 16 ≡ 2, 5² = 25 ≡ 4, 6² = 36 ≡ 1 (mod 7)
- So the squares mod 7 are {1, 2, 4}; these are called quadratic residues. The rest, {3, 5, 6}, are called **quadratic non-residues**.
- The **least quadratic non-residue** is 3.

**[Check 3]** Which numbers are quadratic residues mod 23? What is the least quadratic non-residue? (Answer at the end of the chapter.)

**Why it matters**: to take a square root mod p (given a, find x with x² ≡ a), there is a classical algorithm (Tonelli–Shanks) that first needs to find **any one** quadratic non-residue. Pick a number at random and there is a one-in-two chance it is a non-residue, so the randomized algorithm is fast. But a **deterministic** algorithm (no dice) has to guarantee that "if you try numbers upward from 2, you will hit a non-residue quickly," and for that you need to know how small the least non-residue is.

The paper's Corollary 1.2 derives: least quadratic non-residue ≤ C · (ln p)^32 (C is an absolute constant; the paper says 32 is just one workable value and was not optimized) [P]. That is, trying upward from 2, you are guaranteed to find one within on the order of (ln p)^32 tries, so taking square roots gets an **unconditional** deterministic polynomial-time algorithm. Previously this conclusion required assuming the "generalized Riemann hypothesis."

The same fixed-width zero-free region also makes the **Miller primality test** (Miller 1976, which likewise relied on the generalized Riemann hypothesis) an unconditional deterministic polynomial-time algorithm. This one is stated in the introduction of the companion 11/12 paper in the same family [P]; Corollary 1.2 of the 7/8 paper itself only states the non-residue bound and square roots. Since 7/8 is stronger than 11/12, the conclusion carries over.

A reminder (see 9.2): none of these corollaries is inside the Lean formalization.

**No impact on practical cryptography**:
- In practice people have always used the randomized algorithm, which is already fast.
- A deterministic polynomial-time algorithm for primality testing has existed since 2002 (AKS).
- The security of RSA and elliptic-curve cryptography rests on "factoring large numbers is hard" and "discrete logarithms are hard," which have nothing to do with this result.

### 4.10.3 For AI

This is one of the strongest cases of "AI gets a result on an open problem that humans agree is hard-core, and the result is machine-verified." It also creates a new situation: **a 199-page paper + 480,000 lines of Lean**, where trust rests mainly on "are the kernel and the definitions correct," not on "has anyone understood it." Human reviewing bandwidth has become the new bottleneck.

---

## 4.11 Self-test

Try to answer these after reading. If you can't, go back and reread the corresponding section.

1. In one sentence: why does the "real part" of the zeros affect the error in counting primes? (§4.3)
2. What is the fundamental difference in shape between de la Vallée Poussin's zero-free region and the quasi-Riemann hypothesis's zero-free region? Why does that difference matter? (§4.6.2–4.6.3)
3. Why can't zero-density estimates, however good, replace a zero-free region? (§4.6.4)
4. What is a Siegel zero? Why does the quasi-Riemann hypothesis rule it out? (§4.7.3)
5. In the Lean statement, what does the hypothesis `hs` in front of `riemannZeta s ≠ 0` say? (§4.9.1)
6. Why does this result not affect the security of RSA? (§4.10.2)

---

## Appendix: answers to the checks

- **Check 1**: about 1000/6.9 ≈ 145 primes per 1000 numbers. In reality there are 168 primes below 1000, so the order of magnitude matches.
- **Check 2**: cos 2θ = 2cos²θ − 1; substituting gives 3 + 4cos θ + 2cos²θ − 1 = 2cos²θ + 4cos θ + 2 = 2(cos θ + 1)² ≥ 0.
- **Check 3**: the quadratic residues mod 23 are {1, 2, 3, 4, 6, 8, 9, 12, 13, 16, 18} (11 of them, exactly half of 22), and the least quadratic non-residue is **5** (checked by script).

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| Prime number theorem | The number of primes up to x is about Li(x); the ratio tends to 1 |
| Power saving | The error is smaller than x by a fixed power, e.g. x^(7/8) |
| Complex number | A point in the plane; multiplication = scaling + rotation |
| ζ function | 1/1^s + 1/2^s + …, connected to the primes through the Euler product |
| Analytic continuation | Uniquely extending a function defined only on part of a region to a larger region |
| Zero | A point where the function's value is 0 |
| Critical strip | The vertical strip 0 < Re s < 1, where all non-trivial zeros lie |
| Riemann hypothesis | Every non-trivial zero has real part 1/2 |
| Zero-free region | A region proved to contain no zeros |
| Quasi-Riemann hypothesis | There is a fixed θ < 1 such that there are no zeros where Re s > θ |
| Dirichlet L-function | A variant of ζ used to study primes in arithmetic progressions |
| Siegel zero | A hypothetical real zero of certain L-functions, very close to 1 |
| Quadratic residue | A number that is the square of something mod p |

## Appendix: Further reading

- **3Blue1Brown**, *Visualizing the Riemann zeta function and analytic continuation* (YouTube): an animated version of §4.5.3, "analytic continuation." Highly recommended.
- **3Blue1Brown**, *But what is the Fourier Transform?*: the intuition behind §4.3, "breaking a signal into waves."
- **Barry Mazur & William Stein**, *Prime Numbers and the Riemann Hypothesis* (Cambridge University Press, 2016): a book written specifically for readers who are not math specialists; the first half needs only high-school math.
- Original paper: https://github.com/openai/math/blob/main/preprints/The-Quasi-Riemann-Hypothesis-September-30-2026/paper.pdf
- Companion papers: the 11/12 version https://github.com/openai/math/blob/main/preprints/The-Quasi-Riemann-Hypothesis-October-5-2026/paper2.pdf ; Siegel zeros https://github.com/openai/math/blob/main/preprints/Uniform-exclusion-of-Landau-Siegel-zeros-October-1-2026/paper.pdf
- Lean scope note: https://github.com/openai/math/blob/main/lean/docs/003.md ; challenge statement: https://github.com/openai/math/blob/main/lean/ComparatorChallenges/QuasiRiemannHypothesis.lean
- Dave Goldblatt's independent re-check: https://github.com/davegoldblatt/openai-zeta-proof-check
