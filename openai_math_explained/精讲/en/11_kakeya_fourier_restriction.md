# The Kakeya problem and Fourier restriction: how little room a needle needs to turn around, and the next step after Hong Wang

> The only prerequisites: you can work with powers and logarithms, you know vectors and the dot product, and you know that a Fourier decomposition "breaks a signal into waves" (§4.3.1). Words like dimension, finite field and maximal function are explained the first time they appear.
> Every number in the text is either computed by script (script: `精讲/scripts/11_kakeya.py`, with results copied into the text) or has a source. The **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter. Tags: **[P]** = primary material read (paper, openai/math repository file or Lean source); **[R]** = secondary reporting (news, social media, encyclopedias); **⚠** = something I could not verify, or where sources conflict; [established] / [recent] / [speculation] separate textbook results, new results from 2024–2026, and my own judgment.
> Estimated reading time: 60–90 minutes. You can read it in three sittings: §14.1–14.4 (needles, dimension, the Kakeya conjecture, the finite-field toy), §14.5–14.6 (maximal functions, waves and Fourier restriction), §14.7–14.9 (what OpenAI claims, how far it has been verified, what it means).

---

## 14.0 The bottom line: the one thing this chapter explains

First, the line you may have heard: "OpenAI also helped Hong Wang solve the four-dimensional Kakeya problem." **That is not accurate.** The accurate version is:

- Hong Wang and Joshua Zahl proved the **three-dimensional** Kakeya set conjecture in February 2025 (arXiv:2502.17655), and Wang received the 2026 Fields Medal for it [R].
- Two OpenAI manuscripts dated 2026-09-23/24 (family 074) claim to prove **the next two targets**: the three-dimensional **Kakeya maximal conjecture** (stronger and more quantitative than the version Wang proved), and the **four-dimensional** Kakeya set conjecture [P].
- The author line of both papers says only "OpenAI", and no public material says Wang took part. But the proofs make heavy use of tools that Wang and her collaborators built over the last few years [P]. A more accurate way to put it: **AI, standing on Hong Wang's toolbox, claims to have finished on its own what she and her peers widely regard as "the next target".**
- As of 2026-10-09: neither paper has a Lean proof or a Comparator challenge, the repository contains only a 761-line, half-finished file that proves nothing beyond the trivial bound, and I found no human expert saying publicly that they have read and verified the proofs [P] ⚠.

This chapter explains a causal chain:

> A needle can turn around while sweeping an arbitrarily small area ⟹ area can't measure the size of such sets, so we switch to "dimension" ⟹ the Kakeya conjecture: a set with a needle in every direction must have full dimension ⟹ its quantitative version (the maximal conjecture) controls "how much thin tubes can overlap" ⟹ wave packets are thin tubes, so it holds up a whole chain of problems in Fourier analysis (restriction, Bochner–Riesz, local smoothing) ⟹ OpenAI claims to have broken through this whole chain at once in three dimensions, and to have pushed the set conjecture to four dimensions.

After reading this chapter, you should be able to explain in your own words:
- why "area zero" and "full dimension" don't contradict each other, and how box dimension differs from Hausdorff dimension;
- how the Kakeya set conjecture, the maximal conjecture and the restriction conjecture compare in strength, and why "tubes lit along only a fraction λ of their length" are the key;
- why the finite-field version can be proved in a few paragraphs (Dvir 2008), and work through it by hand on F₃²;
- what exactly OpenAI claims, how far it has been verified, and what is wrong with "OpenAI helped Hong Wang".

---

## 14.1 How a needle turns around: Kakeya's problem (1917)

### 14.1.1 The problem and three candidate shapes

Put a needle of length 1 in the plane. It has to move **continuously** and turn around by 180° (so its two ends swap places). What is the smallest possible area of the region it sweeps? The problem comes from a 1917 paper by Fujiwara and Sōichi Kakeya (both OpenAI papers cite it [P]).

| Region | How the needle turns | Area (computed by script) |
|---|---|---|
| Disk of diameter 1 | Spins in place about the center | π/4 ≈ 0.7854 |
| Equilateral triangle of height 1 | Pivots along the three sides in turn | 1/√3 ≈ 0.5774 |
| Kakeya's deltoid | The needle stays tangent to the curve | π/8 ≈ 0.3927 |

- Equilateral triangle: Pál proved (around 1921) that it is the smallest among **convex** regions [R].
- Deltoid: the curve traced by a point on a small circle of radius r rolling inside a large circle of radius 3r. Every tangent line cuts out a segment of length 4r inside it, so taking r = 1/4 gives length 1. The script checks at three tangent points that the tangent segment has length **1.000000**, and the shoelace formula gives the area **0.392699** = π/8. Kakeya seems to have conjectured that it is the smallest [R].

**[Check 1]** For an equilateral triangle of height 1, what are the side length and the area? (Hint: height = side × √3/2.)

### 14.1.2 Besicovitch: the area can be arbitrarily small

The answer is a surprise: **there is no positive minimum.** In 1928 Besicovitch proved that a needle can turn around inside a region of arbitrarily small area [P, per the introductions of both OpenAI papers]. Even earlier he had constructed a set of **area zero** that contains a unit segment in every direction (Wikipedia dates it to 1920 [R]; ⚠ go by the original paper for the year).

Two intuitions:
1. **Perron trees**. A triangle with a 60° apex angle contains segments in every direction within a 60° range. Cut the base into 2ᵏ pieces to get 2ᵏ thin triangles, then slide them left and right so that they overlap heavily; each piece still keeps its own range of directions. The total area can be pushed arbitrarily low, and three copies rotated by 60° from each other together cover all directions [R].
2. **Sliding along itself costs no area**. To shift the needle sideways a little, first slide it a long way along its own line, turn it by a tiny angle, and slide it back. This sweeps only two long, thin triangles.

The OpenAI three-dimensional paper takes care to point out that being able to turn around continuously and having a needle in every direction are two different things ("These are different requirements.") [P]. The second does not require the needle to move.

**Definition**: a set in ℝⁿ that contains a unit segment in every direction is called a **Kakeya set** (also a Besicovitch set). Its area (volume) can be 0. Then what is left to ask? The point is that **sets of area zero still come in different sizes.** A segment and a Cantor set both have area zero, but the segment is obviously "bigger". The "dimension" of the next section is the ruler for this kind of size.

---

## 14.2 Dimension: how to measure the size of a set with "area zero"

### 14.2.1 Counting boxes (box dimension)

Cover a set with small squares of side δ, and let N(δ) be the smallest number you need. A segment needs δ⁻¹ of them, a square needs δ⁻². The pattern is N(δ) ≈ δ^(−d), and the exponent d is the dimension:

```
d ≈ log N(δ) / log(1/δ)      (more accurate as δ gets smaller)
```

This is called the **box dimension** (box-counting dimension, also Minkowski dimension). The script's actual counts: for a segment, δ = 0.1, 0.01, 0.001 give N = 10, 100, 1000, and the estimate is 1.0000; the same computation for a square gives 2.0000.

### 14.2.2 The Cantor set: dimension need not be an integer

Start from [0, 1], remove the middle third, then remove the middle third of each remaining piece, and repeat forever. What is left, the **Cantor set**, has total length 0 (each step keeps 2/3), yet it has uncountably many points. Cover it with boxes of size δ = 3⁻ᵏ: after step k there are 2ᵏ pieces left, so N = 2ᵏ. The script uses level 12 as the approximation: at δ = 3⁻², 3⁻⁴, …, 3⁻¹⁰, N = 4, 16, 64, 256, 1024, and every estimate is **0.6309**.

**[Check 2]** Use N(3⁻ᵏ) = 2ᵏ to prove that the box dimension of the Cantor set is exactly log 2 / log 3.

### 14.2.3 Hausdorff dimension: allowing boxes of different sizes

Box dimension requires all the boxes to be **the same size**, and that causes trouble. Take the countable set {1, 1/2, 1/3, 1/4, …}: intuitively it is 0-dimensional. But the script's box counts are N = 20, 63, 200, 632 at δ = 10⁻², 10⁻³, 10⁻⁴, 10⁻⁵, exactly 2/√δ, so the box dimension is **1/2**. The reason is that the points crowd closer and closer together near 0, and equal-sized boxes can't see that they are really isolated points.

**Hausdorff dimension** allows covers by sets of **different sizes**. Write rᵢ for the diameter of the i-th piece and ask whether the "s-dimensional cost" Σ rᵢˢ can be made arbitrarily small; the smallest s for which it can be pushed to 0 is the Hausdorff dimension. The OpenAI four-dimensional paper uses exactly this covering definition, and stresses that it doesn't require the set to be measurable [P].

**[Check 3]** Give the k-th point of {1/n} an interval of length ε·2⁻ᵏ. Prove that for every s > 0, Σ (ε·2⁻ᵏ)ˢ tends to 0 as ε → 0.

In general, **Hausdorff dimension ≤ lower box dimension ≤ upper box dimension**. So "Hausdorff dimension = n" is the strongest statement, and it automatically implies that the box dimension is n too (§11.1 of the four-dimensional paper argues exactly this way [P]).

---

## 14.3 The Kakeya conjecture: the area can be zero, but the dimension can't drop

### 14.3.1 The statement and the tube version

> **Kakeya set conjecture**: every Kakeya set in ℝⁿ has Hausdorff dimension (and therefore box dimension) equal to n.

In plain words: you can pack the needles so tightly that the total volume is zero, but not so tightly that the set becomes "thinner" by a dimension.

What people actually work with is a finite version: thicken each needle into a **δ-tube** of radius δ and length 1. In ℝ³ there are about δ⁻² tubes whose directions differ pairwise by at least δ, each of volume πδ², so if they didn't overlap their total volume would be ≈ π (computed by script: 3.1416 for every δ from 0.1 to 0.0001). The question becomes: **how much can this many thin tubes, all pointing in different directions, overlap?** The box-dimension version of the conjecture is roughly equivalent to: the volume of the union is ≥ c_ε·δ^ε for every ε > 0. Overlap can only "save an arbitrarily small power of δ".

The plane is where you can see clearly how "area zero" and "full dimension" coexist. Córdoba's 1977 planar maximal estimate [P, cited] implies that in the plane the union of such tubes has area at least about 1/log(1/δ), and Besicovitch-type constructions show that this is roughly attained (⚠ I have not checked the sharpness details against the original). The script's actual numbers: at δ = 10⁻², 10⁻⁶, 10⁻¹², 10⁻¹⁰⁰, 1/ln(1/δ) = 0.2171, 0.0724, 0.0362, 0.0043. The area does go to 0, but more slowly than any δ^ε, so the dimension is still 2. **"Area zero" is a logarithmic saving; "less than full dimension" would need a power saving.**

### 14.3.2 A hundred years of progress

| Year | Who | Result |
|---|---|---|
| 1917 | Fujiwara–Kakeya | Posed the needle problem [P] cited |
| 1920/1928 | Besicovitch | The area can be zero; a needle can turn around in an arbitrarily small area [P] cited |
| 1971 | Davies | The conjecture holds for n = 2 [P] cited |
| 1991 | Bourgain | Systematically connected Kakeya to Fourier analysis [P] cited |
| 1995 | Wolff | Dimension ≥ (n+2)/2: 2.5 in 3D, 3 in 4D (the "hairbrush" argument) [P] cited |
| 2000 | Katz–Łaba–Tao | Box dimension > 5/2 in 3D; identified three structural features of extremal configurations: stickiness, planiness, graininess [P] cited |
| 2008 | Dvir | Finite-field version completely solved (§14.4) [P] abstract |
| 2019 | Katz–Zahl | Hausdorff dimension > 5/2 in 3D [P] cited |
| 2022–2025 | Wang–Zahl | Sticky Kakeya → Assouad dimension → **3D completely solved** [P] cited |
| 2026-01 | Guth–Wang–Zahl | Streamlined version of the 3D proof, arXiv:2601.14411 [P] cited |

"Sticky" means that tubes with nearby directions also sit close together in position, and that this holds at every scale. Wang and Zahl first proved the sticky case and then reduced the general case to it (this is how Guth's Bourbaki lecture notes summarize it [R]).

### 14.3.3 Wang–Zahl 2025 and the Fields Medal

- arXiv:2502.17655 was posted on 2025-02-24 [P, per the references]; reports say the full paper runs to 127 pages, and Quanta quotes Nets Katz describing it as a once-in-a-century result [R].
- Around 2026-07-23, at the International Congress of Mathematicians in Philadelphia, Wang received the 2026 Fields Medal for her "groundbreaking work in harmonic analysis and geometric measure theory" [R] (Quanta 2026-07-23; University of Waterloo news page). She is currently a professor at IHES and at NYU's Courant Institute [R].
- The same Quanta article says: "Another obvious target for Wang and her community is the 4D Kakeya conjecture" [R]. **Four dimensions is the publicly stated next target for her and her peers** (§14.9.3).

### 14.3.4 Four dimensions: stuck at 3.059 before OpenAI

The introduction of the OpenAI four-dimensional paper lists the earlier progress in four dimensions itself [P] (converted to decimals by script):

| Result | Lower bound in 4D |
|---|---|
| Wolff 1995, (n+2)/2 | 3.0000 |
| Guth–Zahl polynomial Wolff axioms + Zahl, Katz–Rogers (compact sets) | 3 + 1/40 = 3.0250 |
| Katz–Zahl "planebrush", maximal-estimate parameter | 3.0490 |
| Borges–Chan–Chen–Liu–Xi–Zhan 2025, maximal parameter (159+√145)/56 | 3.0543 |
| Katz–Zahl, Hausdorff dimension | **3.059** |
| Sticky sets only: Rai Choudhuri | 13/4 = 3.25 |
| **OpenAI's claim** | **4** |

Going from Wolff's 3 toward the target of 4, the roughly 30 years before OpenAI closed only **5.9%** of the gap (computed by script). Separately, Łaba–Tao proved in 2001 that the **box dimension** in four dimensions is strictly greater than 3 [P, cited].

A detail of timing: on 2026-09-18 Hong Wang and Dmitrii Zakharov posted *Kakeya and Furstenberg problems for sticky sets of tubes* on arXiv (arXiv:2609.22035), which gives a full-dimension estimate for the union of sticky tube families satisfying certain conditions. The four-dimensional paper cites it and notes that these conditions "do not cover arbitrary Kakeya sets" [P, per the references and introduction; ⚠ I have not read that paper itself]. The OpenAI four-dimensional manuscript is dated six days later.

---

## 14.4 The Kakeya problem over finite fields: a version you can work by hand

### 14.4.1 The F₃ plane and the smallest Kakeya sets

A **finite field F_q** (q a prime) is just the integers mod q, {0, 1, …, q−1}. In F₃, 2 + 2 = 1 and 2 × 2 = 1. The **F_q plane** has q² points; a line {a + t·v : t ∈ F_q} has exactly q points; and there are q + 1 directions in all (slopes 0…q−1 plus vertical). A **finite-field Kakeya set** is a set of points that contains a whole line in every direction. Wolff proposed it in 1999 as a toy model for the real problem [R].

In the plane there is an elementary lower bound: two lines in different directions meet in exactly one point, so the first line contributes q points, the second adds at least q−1 new ones, and so on, for a total ≥ q + (q−1) + … + 1 = q(q+1)/2.

The script enumerated every combination of "one line per direction" (using a translation to fix the vertical line as x = 0):

| q | Points in the plane | Combinations searched | Smallest Kakeya set | Elementary lower bound | Blokhuis–Mazzocca formula | Fraction |
|---|---|---|---|---|---|---|
| 3 | 9 | 27 | **7** | 6 | 7 | 0.778 |
| 5 | 25 | 3,125 | **17** | 15 | 17 | 0.680 |
| 7 | 49 | 823,543 | **31** | 28 | 31 | 0.633 |

The enumeration matches the exact formula of Blokhuis–Mazzocca 2008, q(q+1)/2 + (q−1)/2 for odd q [R, arXiv:0911.4370; I have not read the original, but all three values of q were verified by enumeration]. A smallest Kakeya set for q = 3 (script output):

```
Points: (0,0) (0,1) (0,2) (1,0) (1,1) (2,0) (2,2)
Lines: x = 0; y = 0; y = x; y = 2x + 1
```

**[Check 4]** Verify by hand that the 3 points of each of the four lines are among these 7 points (for y = 2x + 1, x = 0, 1, 2 give y = 1, 0, 2, mod 3).

The fraction is falling, toward 1/2, but **not toward 0**. This is the finite-field version of "full dimension": a Kakeya set has the same order of size as the whole space, qⁿ.

### 14.4.2 Dvir's polynomial method (2008)

In 2008 Dvir used a very short argument to prove that a Kakeya set in F_qⁿ has at least C_n·qⁿ points; before that, the best general lower bound was about q^(4n/7) [P, abstract of arXiv:0803.2336]. Here is the whole argument worked through for q = 3, n = 2:

**Step 1: if there are few points, some polynomial vanishes on all of them.** There are 6 monomials in two variables of degree ≤ 2: 1, y, y², x, xy, x². Requiring a polynomial to be 0 at every point of K gives |K| linear equations in the 6 coefficients. When |K| ≤ 5 there are more unknowns than equations, so a nonzero solution must exist. Script check: for **every one** of the 126 five-point subsets of F₃², such a nonzero polynomial exists.

**Step 2: vanishing on a whole line gives away the "top-degree part".** Restrict P to the line a + t·v to get a polynomial in one variable t. Its degree is ≤ 2, yet it is 0 at t = 0, 1, 2, so it is identically zero. Its t² coefficient is exactly the value at v of the top-degree homogeneous part of P. Conclusion: **if K contains a whole line in direction v, then the top-degree part of P vanishes at v.**

**Step 3: contradiction.** If K is a Kakeya set, the top-degree part vanishes in every direction, and hence at all 9 points of F₃². But the script checked all 728 nonzero polynomials of degree ≤ 2, and **0** of them vanish at all 9 points. So a Kakeya set has at least 6 points.

The general case works the same way: there are C(q+n−1, n) monomials in n variables of degree ≤ q−1, so |K| ≥ C(q+n−1, n) ≥ qⁿ/n!.

An example (script output): S = {(0,0), (0,1), (0,2), (1,0), (2,0)}, the "cross" made of x = 0 and y = 0. P = xy vanishes on all of it, and its top-degree part vanishes only in the directions (1,0) and (0,1), so S can contain whole lines in at most these two directions, which is exactly the case.

**[Check 5]** Verify that xy is 0 at all 5 points of the cross, and nonzero in the directions (1,1) and (1,2).

### 14.4.3 Why the real case is hard, and a migration route from CS to analysis

In F_q a line has only q points, and "a polynomial of degree < q that vanishes on a whole line is identically zero" applies directly. In ℝⁿ there are **infinitely many scales**: tubes can spread out at coarse scales and bunch together at fine scales, or the other way round. Nearly all the difficulty of the real problem lies in these multiple scales, and both the Wang–Zahl and the OpenAI papers spend many pages on them [P]. Over the reals there is also an "algebraic obstruction": the tubes may cluster near a low-degree algebraic surface, and Guth–Zahl's polynomial Wolff axioms exist to rule this out [P, cited].

Dvir is a theoretical computer scientist, and his argument shares its roots with polynomial interpolation in coding theory (Reed–Muller codes, Sudan's list decoding) [established]. Guth then carried it over to the real setting: the endpoint case of multilinear Kakeya in 2010 [P, cited], Guth–Katz on the Erdős distinct distances problem in 2015 [R], and in 2016 the use of "polynomial partitioning" to push three-dimensional restriction to p > 13/4 [P, cited]. **A CS counting trick became, a decade or so later, a workhorse of harmonic analysis.**

---

## 14.5 The Kakeya maximal conjecture: tubes that are only partly lit

### 14.5.1 The maximal function

Take a function f on ℝ³ (think of it as a cloud of "density"). For each direction ω, search all positions in space for the tube with direction ω, length 1 and radius δ that makes the average of |f| over the tube as large as possible:

```
K_δ f(ω) = max over all positions a of [ (1/(πδ²)) × ∫ over the tube T_δ(a, ω) of |f(x)| dx ]
```

This is the definition at the start of the OpenAI three-dimensional paper [P]. K_δ f is a function on the sphere: one number per direction.

> **Kakeya maximal conjecture (three dimensions)**: for every ε > 0 there is a C_ε such that for all 0 < δ < 1 and all f: ‖K_δ f‖_{L³(S²)} ≤ C_ε · δ^(−ε) · ‖f‖_{L³(ℝ³)}.

Here ‖g‖_{L³} = (∫|g|³)^(1/3).

### 14.5.2 The trivial bound δ^(−2/3)

By Hölder's inequality, the average over a single tube is ≤ (πδ²)^(−1/3)·‖f‖₃; then integrate over the sphere:

```
‖K_δ f‖₃ ≤ (4π)^(1/3) · (πδ²)^(−1/3) · ‖f‖₃      (grows like δ^(−2/3))
```

This is exactly the **only** substantive theorem about the maximal function in the Lean file in the OpenAI repository (`maximal_norm_le_holder`, §14.8.1) [P]. Compared with the shape of the conjecture (taking ε = 0.01), the script's actual numbers are:

| δ | Constant in the trivial bound | Conjecture shape δ^(−0.01) |
|---|---|---|
| 10⁻² | 34.2 | 1.047 |
| 10⁻⁴ | 736.8 | 1.096 |
| 10⁻⁶ | 15,874.0 | 1.148 |

### 14.5.3 λ and λ³: why the maximal version is stronger

**Maximal ⟹ set**. Take f to be the indicator function of a union of tubes. In every direction there is a tube lying entirely inside the union, where the average is 1, so the left side is ≈ (4π)^(1/3), while on the right ‖f‖₃ = (volume of the union)^(1/3). Substituting gives volume of the union ≳ δ^(3ε), which is the discrete version of the set conjecture.

**Light up only part of each tube.** In each tube T only a subset Y(T) is lit, with |Y(T)| ≥ λ·|T| and 0 < λ ≤ 1. Take f to be the indicator function of the union of the lit pieces, and compute the same way:

```
(average in each direction ≥ λ)  ⟹  (4π)^(1/3) · λ ≤ C δ^(−ε) · |union of lit pieces|^(1/3)
                                 ⟹  |union of lit pieces| ≳ δ^(3ε) · λ³
```

This is exactly inequality (1.1) of the three-dimensional paper: |∪Y(T)| ≳ δ^ε · λ³ · Σ|T| [P]. The "3" in λ³ comes from the L³ norm.

**[Check 6]** If the constant in the maximal inequality is C·δ^(−ε) and exactly half of every tube is lit (λ = 1/2), at least how large is the volume of the union of the lit pieces?

**Why the power of λ is the key**. The paper says that Wang and Zahl's set theorem gives a dependence of the form λ^(K(ε)), and that "the need to replace it by λ³ is stated explicitly after their theorem" [P]. To compare orders of magnitude, take a **made-up** K = 100 (⚠ not the real exponent; computed by script): at λ = 0.5, λ³ = 0.125 while λ¹⁰⁰ = 7.89×10⁻³¹. In applications f has to be split into layers by the size of its values, and each layer is a family of tubes "lit along a fraction λ", with λ running through 1/2, 1/4, 1/8, …; a dependence like λ¹⁰⁰ blows up when the layers are summed, while λ³ matches L³ exactly. **The set conjecture can still be derived from a somewhat worse dependence on λ (the paper: "A set-dimension conclusion can follow from weaker dependence on λ"), but the maximal conjecture requires the optimal λ³, so it is strictly stronger**; the applications in §14.6 all need the maximal version.

**The dual version**: a **Nikodym set** requires that for every point in a large set of points, some segment passes through that point and lies almost entirely in the set. §11 of the three-dimensional paper uses the transfer theorem of Gao–Liu–Xi to derive a Nikodym maximal estimate from the maximal theorem [P].

---

## 14.6 Why analysts care: waves, Fourier restriction and Bochner–Riesz

### 14.6.1 Waves with a single wavelength: extension from the sphere

The "sine waves" of ℝ³ are the plane waves e^(2πi x·ξ): their crests form a family of parallel planes perpendicular to ξ, and the wavelength is 1/|ξ|. Every function is a superposition of plane waves. Now allow only |ξ| = 1, that is, waves that **all have wavelength 1 but may point in any direction**, and give each direction ω a complex weight g(ω):

```
Eg(x) = ∫ over the unit sphere S² of g(ω) · e^(2πi x·ω) dσ(ω)
```

This is the **extension operator** of paper 077 [P]. Physically, it is the field you get by superposing "monochromatic waves of the same frequency arriving from every direction". Where the name comes from: Stein originally asked whether the Fourier transform can be meaningfully **restricted** to the sphere, a set of zero volume, and the sphere's **curvature** makes this possible within a certain range; extension is the dual of restriction [established].

### 14.6.2 The simplest example and the p > 3 threshold

Take g ≡ 1. The integral can be done exactly (the paper gives it [P]): E1(x) = 2 sin(2π|x|) / |x|. A script checked this by numerical integration: at |x| = 0.25, 1.3 and 5.7 it gives 8.000000, 1.463164 and −0.333704, matching the formula.

It decays like 1/|x|. ∫|E1|ᵖ over ℝ³ is roughly ∫ r^(−p)·r² dr, which is **finite for p > 3 and divergent for p ≤ 3**. Actual numbers from the script (∫ over 1 < |x| < R):

| p | R = 10 | R = 100 | R = 1000 |
|---|---|---|---|
| 3 | 97.95 | 196.19 | 294.43 |
| 3.5 | 76.66 | 101.09 | 108.82 |
| 4 | 66.75 | 73.53 | 74.21 |

At p = 3, every tenfold increase in R adds about 98: a logarithmic divergence. At p = 3.5 and 4 the integral converges.

> **Stein restriction conjecture (three dimensions, bounded data)**: for every p > 3 there is a constant C_p such that every bounded g satisfies ‖Eg‖_{Lᵖ(ℝ³)} ≤ C_p · sup|g|.

In other words, "all the waves converging at the origin" is already the worst case. In n dimensions the threshold is p > 2n/(n−1); two dimensions (p > 4) was solved in the 1970s (Fefferman, Zygmund) [R]. Progress in three dimensions:

| Who | Threshold for p | Source |
|---|---|---|
| Tomas–Stein (L² → L⁴) | 4 | [P] |
| Tao 2003, bilinear | 10/3 ≈ 3.3333 | [R] ⚠ original not reread |
| Bourgain–Guth 2011, multilinear | 3.3 | [R] ⚠ original not reread |
| Guth 2016, polynomial partitioning | 13/4 = 3.25 | [P] |
| Hong Wang, from 2018, the "brooms" method (paraboloid) | 42/13 ≈ 3.2308 | [P] |
| Wang–Wu 2024, two-ends Furstenberg + refined decoupling | 22/7 ≈ 3.1429 | [P] |
| **OpenAI claims** | **3 (the entire open range)** | [P] |

(The [P] thresholds all appear directly in the introduction of paper 077.)

### 14.6.3 Why the restriction conjecture controls Kakeya: wave packets are thin tubes

This is the most important step in the whole chapter:
1. **The uncertainty principle.** Cut the sphere into small caps of diameter about δ. If you use only the directions inside one cap, the superposed wave is concentrated on a tube of width about 1/δ and length about 1/δ², oriented perpendicular to the cap. This is called a **wave packet** [established]. You have seen the same thing in EEG time-frequency analysis: the narrower in frequency, the wider in time. (V1 simple cells are often modeled with Gabor functions, Daugman 1985, which are also "wave packets" localized in both space and frequency; this is only an analogy.)
2. **One tube per cap.** After shrinking coordinates by a factor of δ², these become tubes of length 1 and width δ whose directions differ pairwise by about δ: exactly the Kakeya configuration of §14.3.1.
3. **Overlap ⟹ larger Lᵖ norm.** Give each wave packet a random sign; then |Eg|² is roughly "the number of tubes passing through the point". If the tubes overlap heavily, the way they do in a Besicovitch set, the energy is squeezed into a very small set, and for p > 2 the Lᵖ norm becomes large. The restriction estimate forbids this. **Restriction conjecture ⟹ Kakeya conjecture** [established, going back to Bourgain 1991].

The converse fails: Kakeya only counts how tubes overlap, so it is like "the restriction problem with the phases thrown away"; restriction also has to deal with interference between the waves, so it is harder.

### 14.6.4 A surprise about the ideal low-pass filter: Fefferman 1971 and Bochner–Riesz

The most natural filter in engineering is the "ideal low-pass" filter: keep the frequencies with |ξ| ≤ 1 and cut off the rest. In one dimension this is bounded on every Lᵖ (1 < p < ∞) [established]. **Fefferman proved in 1971 that in two or more dimensions the spherical cutoff is bounded only for p = 2**, and the counterexample is built precisely from a Besicovitch set (introduction of paper 078: "Using a Kakeya construction, Fefferman proved…" [P]).

The remedy is to round off the edge of the cutoff: multiply by (1 − |ξ|²)^δ (for |ξ| < 1). This is called the **Bochner–Riesz mean**. Here δ measures how much the edge is rounded; it has nothing to do with the tube radius and is just historical notation.

> **Bochner–Riesz conjecture**: if δ > max( n·|1/p − 1/2| − 1/2, 0 ), the mean is bounded on Lᵖ [P, paper 078].

Three-dimensional thresholds computed by script: 1.0 at p = 1 or ∞; 0.5 at p = 6; 0.25 at p = 4; **0 for 3/2 ≤ p ≤ 3**, where any amount of rounding is enough. Two dimensions was solved by Carleson–Sjölin; in three dimensions the previous best was max{p, p′} ≥ 22/7 (Gao–Wu–Xi) [P, introduction of paper 078].

**[Check 7]** For n = 3 and p = 4, what is the threshold 3·|1/4 − 1/2| − 1/2?

### 14.6.5 A chain of implications

In three dimensions these conjectures line up in a chain (each arrow is cited in the introduction of the corresponding OpenAI paper [P]):

```
Local smoothing (wave equation) ⟹ Bochner–Riesz ⟹ Fourier restriction ⟹ Kakeya maximal ⟹ Kakeya set
                              Sogge         Tao 1999               §14.6.3          §14.5.3
```

**Local smoothing**: solutions of the three-dimensional wave equation lose some smoothness at any fixed time, but averaging over an interval of time recovers almost all of it. This is Sogge's 1991 conjecture [R]; the two-dimensional case was solved by Guth–Wang–Zhang [P, cited].

OpenAI claims to have pushed through this chain **from end to end** in three dimensions within two days (§14.7.2); before this, only the last link had been taken, by Hong Wang and Zahl.

---

## 14.7 What OpenAI claims

### 14.7.1 The two papers of family 074

The 074 entry of `CONTENTS.md` [P]: "Resolves the Kakeya maximal conjecture in three dimensions and the Hausdorff-dimension conjecture in four."

**Paper A**: *The Kakeya maximal conjecture in three dimensions* (2026-09-23, 97 pages). Abstract [P]:

> "We prove the Kakeya maximal conjecture in three dimensions. For every ε > 0, the maximal average over unit tubes of radius δ maps L³(ℝ³) to L³(S²) with norm at most C_ε δ^(−ε)."

**Paper B**: *Every four-dimensional Kakeya set has full Hausdorff dimension* (2026-09-24, 175 pages). Abstract [P]:

> "We prove the four-dimensional Hausdorff-dimension Kakeya conjecture: every subset of ℝ⁴ containing a unit line segment in every direction has Hausdorff dimension four. No compactness or regularity assumption is imposed on the set or its witnessing line family."

It does **not** claim the four-dimensional maximal conjecture. For the corollaries in §11 of each paper, see §14.9.1.

### 14.7.2 The same cluster: 073, 077, 078, 079

Within the same two days there was a whole cluster of harmonic analysis results that cite one another [P]:

| No. | Paper (pages) | Claim | Previous best |
|---|---|---|---|
| 073 | Falconer distance conjecture, all dimensions (64) | Every compact set in ℝᵈ of dimension > d/2 has a distance set of positive length | Plane: 5/4 (Guth–Iosevich–Ou–Wang, pinned version); three dimensions: 9/5 |
| 074 | The two papers above (97 + 175) | Three-dimensional maximal, four-dimensional set | §14.3.4, §14.5.3 |
| 077 | Elliptic capacity propagation and restriction to the sphere (103) | Restriction for the sphere with bounded data, p > 3 | p > 22/7 |
| 077 | Diagonal extension for positively curved surfaces (25) | Any compact positively curved surface, Lᵖ → Lᵖ, p > 3 | p > 22/7 (Wang–Wu) |
| 078 | Three-dimensional Bochner–Riesz (114) | The whole strict range | max{p, p′} ≥ 22/7 |
| 079 | Three-dimensional critical local smoothing (165) | Arbitrarily small loss at p = 3 | At p = 3 a loss > 1/12 was needed (obtained by interpolating results of Gan–He–Li–Wu) |

A few details [P]:
- **The Falconer distance problem** (1985 [R]): if a set has dimension greater than d/2, must the distances between pairs of its points fill out an interval of positive length?
- The 077 sphere paper uses Bourgain's factorization theorem to upgrade the bounded-data result to L^q → L^q (3 < q < ∞), then interpolates to get the whole mixed range except the endpoint line. **What it claims is the entire open range of the Stein restriction conjecture for the sphere in three dimensions.**
- One of the two inputs of the 077 surface paper is the three-dimensional maximal theorem of 074. Paper 078 mentions that Zipeng Wang has also put forward a proof of Bochner–Riesz in all dimensions (arXiv version 6); ⚠ I did not check its status.

### 14.7.3 The idea of the three-dimensional maximal paper (introduction only, simplified)

A paraphrase of §1.2 of the paper; the details go far beyond this [P]:
1. **Proof by contradiction**: define a "critical exponent", the least extra power of N (N = 1/δ) that must be multiplied in for the inequality to hold for every configuration. If it is > 0, there is a sequence of extremal configurations that "almost attain equality" (compare a minimal counterexample in combinatorics).
2. **Extremal configurations are forced into specific shapes**: multilinear Kakeya (Bennett–Carbery–Tao, and Guth's endpoint version) implies that over short time blocks the directions are nearly coplanar; the Ren–Wang planar Furstenberg theorem implies that there is enough density inside "plates". These are exactly the planiness and graininess described by Katz–Łaba–Tao. A "minimum-delay" argument then forces the time profile into the canonical form F(s) = β(s − τ)₊, which the paper calls stationarity.
3. **Information-theoretic bookkeeping**: each tube is described by four coordinates, position X, Y and velocity U, V, and **conditional entropy** (normalized by log N, which you can read as a cell count on a logarithmic scale) measures how much information each coordinate carries. Two events on the same line give two "reference frames", which differ by a 2×2 matrix; planar projection theorems constrain the entropy growth rates (the "pinning" step is adapted from Shmerkin–Wang and Orponen–Shmerkin–Wang).
4. **The contradiction**: if a constraint failed, there would have to be a positive amount of mutual information between the actual joint distribution and the independent product distribution, but an averaged estimate shows that less than that is available. So the critical exponent is 0. The estimate is then extended to arbitrary L³ functions, keeping λ³ throughout.

For CS readers: this is like a lower-bound proof that uses "amount of information" as a potential function (my analogy).

### 14.7.4 The idea of the four-dimensional paper (again, introduction only)

1. **Proof by contradiction**: assume there is a Kakeya set of Hausdorff dimension < 4, and turn it into a "weighted line problem": fit the lines with "charts" (a chart is a collection of line pieces plus a time interval, on which a certain **quadratic polynomial test** stays small). A counterexample means the fit must pay a positive "time cost" (horizon H(E) > 0) [P]. The quadratic polynomial corresponds to the algebraic obstruction described in §14.4.3.
2. **Three cases according to "narrowness" ℓ** [P]: when ℓ = 0, an approximate polynomial "potential field" is assembled, and the cubic and quartic terms (the obstruction is directions lying near a conic) are encoded into a quadratic correction (Proposition 6.8); when 0 < ℓ < ∞, the problem is projected to a one-dimensional model, which either improves directly or is forced into a "horizontal model" Y′ = −Z + tv in which the two horizontal directions do not commute (this reminds me of the known hard examples of Heisenberg-group type; the paper does not use that name, so this is speculation); when ℓ = ∞, the final projection gives a time cost tending to 0, which contradicts the counterexample.
3. **Inputs**: Lemma 2.3 of OpenAI's own three-dimensional maximal paper (a weighted "full-time plank" bound, coming from Guth–Wang–Zahl); the determinant-type multilinear Kakeya of Carbery–Valdimarsson; the restricted-triples dot-product theorem of Wang–Zahl; the multiplicative convolution estimate of Orponen–de Saxcé–Shmerkin; Balog–Szemerédi–Gowers [P].

**Dependency**: the four-dimensional paper uses a lemma from the three-dimensional maximal paper. If the three-dimensional paper contains an error, the four-dimensional one is affected too.

### 14.7.5 What is wrong with "OpenAI helped Hong Wang solve four-dimensional Kakeya"

| The claim | What is actually the case |
|---|---|
| "Helped Hong Wang" | The author line says only "OpenAI"; no public material says Hong Wang was involved [P] |
| "Hong Wang's problem" | Wang–Zahl solved the three-dimensional set conjecture; what OpenAI claims is the three-dimensional maximal conjecture and the four-dimensional set conjecture, which are the **next step** |
| "Already solved" | Only claimed: not peer reviewed, no Lean proof, no public verification by experts (§14.8) |
| Relation to Hong Wang | Heavy reliance on tools from her and her collaborators: Wang–Zahl (three papers), Guth–Wang–Zahl, Ren–Wang, Wang–Wu, Shmerkin–Wang, Orponen–Shmerkin–Wang, Guth–Wang–Zhang [P, the reference lists of each paper] |

The confusion probably comes from Ivanisvili's widely shared remark in §14.8.4: it puts "Kakeya in 3D won a Fields Medal" side by side with "Kakeya in 4D was solved by AI", and in retelling this easily turns into "helped Hong Wang".

What is easy to miss: the Ren–Wang planar Furstenberg theorem is the shared engine of this cluster. The three-dimensional maximal, sphere restriction, Bochner–Riesz and local smoothing papers all list it as a key input [P]. **Hong Wang's tools appear at almost every key point of this batch of AI results.**

---

## 14.8 How far it has been verified

### 14.8.1 Lean: only an unfinished 761-line file

§3 explained that the value of a Lean proof is that "humans only need to audit the statement". In the snapshot `openai/math@fd4aeeb` (2026-10-07) [P]:
- 074, 077, 078 and 079 are **absent** from `lean/formalization.yaml` (which registers 200 Comparator configurations), from `lean/docs/` and from `ComparatorChallenges/`.
- The only relevant file is `lean/OAI/Analysis/Kakeya/FixedScale.lean`: 761 lines, imported on line 106 of `OAI.lean`, with no `sorry`.

It writes down the **statement** of the three-dimensional maximal conjecture:

```lean
def MaximalConjecture : Prop :=
  ∀ ε : ℝ, 0 < ε → ∃ C : ℝ, 0 < C ∧
    ∀ δ : ℝ, 0 < δ → δ < 1 → ∀ f : Space → ℂ,
      MemLp f (3 : ℝ≥0∞) (volume : Measure Space) →
      MemLp (maximal δ f) (3 : ℝ≥0∞) surfaceMeasure ∧
      eLpNorm (maximal δ f) (3 : ℝ≥0∞) surfaceMeasure ≤
        ENNReal.ofReal (C * δ ^ (-ε)) *
          eLpNorm f (3 : ℝ≥0∞) (volume : Measure Space)
```

Word-by-word translation:
- `def MaximalConjecture : Prop`: this is a **definition** (of a proposition), **not a theorem**.
- The middle three lines: for every ε there is a constant C such that, for all 0 < δ < 1 and every complex-valued function f in L³,
- The last two lines: the L³ norm of the maximal function on the sphere is ≤ C·δ^(−ε) times the L³ norm of f.

In the file, `tube` is a + t·ω + u (|t| ≤ 1/2, u ⊥ ω, ‖u‖ ≤ δ), the average is divided by πδ², and the total mass of the sphere measure is proved to be 4π (`surfaceMeasure_univ`). I checked it clause by clause, and this statement agrees with Theorem 1.1 of the paper (this is my own reading).

**But no theorem anywhere in the repository proves `MaximalConjecture`.** What the file actually proves is: that the tubes and the maximal function are measurable, the trivial bound `maximal_norm_le_holder` from §14.5.2, a normalization lemma, and a finite weighted sampling lemma (`logarithmic_indexed_sample`; ⚠ I did not check which step of the paper it corresponds to). The four-dimensional theorem does not even have a statement. **The statement is written, the proof is not done, and the machine guarantee is zero.** Compare §4 and §9: both of those chapters have complete Lean proofs and Comparator configurations.

### 14.8.2 Comparison within the cluster: only Falconer has been formalized

| No. | Lean status [P] |
|---|---|
| 073 Falconer | Yes. `docs/073.md` links two Comparator challenges: `PlanarFalconer.lean` and `FalconerAllDimensions.lean`. The proof is in `MeasureTheory/Falconer/` and `FalconerCompletion/`: 2,796 files, about 247,000 lines in total; grep finds no `sorry`, no added axioms and no `native_decide`; both configurations have `"enable_nanoda": false`. ⚠ `formalization.yaml` registers only the planar one |
| 074 Kakeya | No proof, only the 761-line file above |
| 077, 078, 079 | None |

The Falconer Lean proof contains a special case of a planar Furstenberg-type incidence estimate (`Incidence/PublishedFurstenberg.lean`) [P]; ⚠ it looks weaker than Ren–Wang's sharp version, but I did not check the exact relationship. 074 is not among the 10 families whose reasoning summaries are published in the README, nor on the 10-07 list of retractions and revisions [P].

### 14.8.3 Several routes corroborate each other, but they are not independent

This cluster has an unusual structure: several conclusions have **two independently claimed proof routes** [P]:

| Conclusion | Route 1 | Route 2 |
|---|---|---|
| Three-dimensional Kakeya maximal | 074, direct proof | 077 sphere restriction ⟹ Corollary 1.3 |
| Sphere restriction, p > 3 | 077, direct proof | 078 Bochner–Riesz ⟹ Tao 1999 |
| Three-dimensional Bochner–Riesz | 078, direct proof | 079 local smoothing ⟹ Corollary 11.2 |

If the routes were truly independent, an error in one would not affect the other. But they **share** the same unreleased model, the same key inputs (Ren–Wang appears in all three main routes, 074, 077 and 078) and the same methodological style. Software engineering has a classic lesson here: Knight and Leveson's 1986 experiment found that multiple versions of a program developed independently failed at highly correlated places [established]. **"Redundant" proofs from the same generator may have correlated failure modes** (speculation).

### 14.8.4 Human experts

- **Paata Ivanisvili** (UC Irvine): "Kakeya in 3D won a Fields Medal. Kakeya in 4D was solved by AI. Let that sink in." [R] ([X post](https://x.com/PI010101/status/2107604089265688691), via officechai)
- **Rodrigo Porto** (Princeton): "Kakeya maximal conjecture solved?!", and "It's a stronger version of the Kakeya conjecture. Hong Wang literally won a fields medal for making progress on the latter" [R] ([X post](https://x.com/NotRod_xyz/status/2107619958037328368), via officechai)
- **Levent Alpöge** (Anthropic): "There are some sad stories related to their users getting scooped / conflicts of interest (kakeya maximal comes to mind)" [R] ([X post](https://x.com/__alpoge__/status/2107616859595981117), via officechai). ⚠ The post does not say who was involved or what happened, and I cannot verify it.
- ⚠ **As of 2026-10-09, I found no public comment on these papers from Hong Wang, Zahl, Guth or Tao**, and nobody has publicly said they have read and verified these 97 + 175 pages (I searched both Chinese and English coverage). The three items above are reactions, not reviews.

**Remaining risk**: the statement risk is low (the three-dimensional maximal conjecture is a standard statement, and the Lean version agrees with the paper; the four-dimensional one is a single sentence). The proof risk is high (272 pages, no machine check, no human review, and the four-dimensional paper depends on the three-dimensional one). In arguments of this kind the most error-prone points are the order in which limits are taken and whether "losses smaller than any power" get amplified; the end of §1.3 of the three-dimensional paper explains the order of limits specifically [P], and this is where experts should look first (speculation).

---

## 14.9 What it would mean if true (and what it would not)

### 14.9.1 For mathematics

1. **Four-dimensional Kakeya: from 3.059 straight to 4**, whereas the previous 30 or so years had closed only 5.9% of the gap. Side results [P]: the box dimension is also 4; Kakeya sets in ℝᵈ (d ≥ 4) all have dimension ≥ 4; Nikodym sets on four-dimensional manifolds of constant curvature have dimension 4 (the four-dimensional case of Conjecture 1.4 of Gao–Liu–Xi); a dimension formula for direction sets (Keleti–Máthé: a set containing a line segment in every direction in D has dimension ≥ 1 + dim D).
2. **Three-dimensional Kakeya maximal**: the optimal λ³ dependence. It gives Nikodym maximal estimates on ℝ³ and on three-dimensional manifolds of constant curvature, and a class of curved Kakeya maximal estimates [P], and it is an input to 077's restriction theorem for positively curved surfaces.
3. **If the whole cluster is true**: in three dimensions, the entire chain local smoothing ⟹ Bochner–Riesz ⟹ restriction ⟹ Kakeya holds in the strict range. These have been central problems of harmonic analysis for the past 50 years; closing them all at once in three dimensions would carry the weight of a whole generation's research program (speculation).
4. **What remains open**: the Kakeya set conjecture in five or more dimensions; the maximal, restriction, Bochner–Riesz and local smoothing conjectures in four or more dimensions; the endpoint cases in three dimensions (every paper says explicitly that it does not handle endpoints) [P].

### 14.9.2 For CS

- **Kakeya over the reals has no direct impact on CS** (speculation). CS uses the finite field version, which Dvir solved in 2008.
- The finite field version is used in **randomness extraction** (turning a "biased" random source into nearly uniform bits). Dvir–Wigderson 2008 (*Kakeya sets, new mergers and old extractors*) used Kakeya-type bounds to analyze "mergers": among several random variables, one is uniform but you don't know which; output a point on the line through them, and the Kakeya bound guarantees that the output still has high entropy [R]. Dvir–Kopparty–Saraf–Sudan 2009 improved the lower bound to qⁿ/2ⁿ and used it to build extractors with logarithmic seed length [P, abstract of arXiv:0901.2529].
- For the opposite direction, see §14.4.3: the polynomial method came from CS into real analysis.

### 14.9.3 For AI

- **Speed**: from the Wang–Zahl preprint (2025-02-24) to OpenAI's four-dimensional manuscript (2026-09-24): **19.0 months**; from the streamlined Guth–Wang–Zahl version (2026-01-20) to the four-dimensional manuscript: **8.1 months**; from the Fields Medal to OpenAI's public release: **75 days** (computed by script).
- **"Scooped"**: Quanta called four dimensions the obvious next target for Hong Wang and her peers [R]; Wang–Zakharov's paper on sticky families of tubes came out six days before the four-dimensional manuscript [P]; Alpöge pointed to scooping and conflicts of interest around "kakeya maximal" [R] ⚠. A 175-page manuscript that nobody has reviewed and that has no Lean proof may already have changed the research topics of a number of PhD students and postdocs: if it is wrong, the field must spend people's time finding the error; if it is right, research programs must be rewritten. This is what §23.9, "Political economy of AI-produced knowledge", looks like in practice: control lies in when to publish, what to publish, and whether to attach a proof. The people who can read these papers are essentially the few dozen cited authors and their students, so **the cost of verification is borne by the community that was scooped** (speculation).
- **A methodological observation**: this cluster shares the engine "extremal configurations + entropy bookkeeping + Ren–Wang". That may mean the model found a reusable engine, or it may mean the errors are correlated (§14.8.3) (speculation).

### 14.9.4 What it does not mean

- **It does not mean Hong Wang's work has been surpassed or devalued**: these proofs are built on her tools, and the three-dimensional set conjecture was proved by her and Zahl.
- **It does not mean anything has been proved**: as of 2026-10-09 there is no Lean proof and no public review; and the higher-dimensional problems remain open (§14.9.1, item 4).

---

## 14.10 Self-test

Try answering these after reading. If you can't, go back and reread the corresponding section.

1. A needle can be turned around within a region of arbitrarily small area, so why is the Kakeya conjecture still meaningful? (§14.1.2, §14.2)
2. The box dimension of {1/n} is 1/2, while its Hausdorff dimension is 0. Where does the difference come from? (§14.2.3)
3. Restate Dvir's polynomial method in three steps. (§14.4.2)
4. In what way is the maximal conjecture stronger than the set conjecture? Where does the 3 in λ³ come from? (§14.5.3)
5. Why does a conjecture in Fourier analysis imply a geometric conjecture about thin tubes? (§14.6.3)
6. Write down the chain of implications in three dimensions, and mark which link had already been proved before OpenAI. (§14.6.5)
7. What does family 074 have in Lean, and what is missing? How does it compare with 073? (§14.8.1–14.8.2)
8. In which ways is "OpenAI helped Hong Wang solve the four-dimensional Kakeya problem" inaccurate? (§14.7.5)

---

## Appendix: answers to the checks

- **Check 1**: side length = 2/√3 ≈ 1.1547; area = ½ × side × height = 1/√3 ≈ 0.5774 (checked by script).
- **Check 2**: log 2ᵏ / log 3ᵏ = k·log 2 / (k·log 3) = log 2 / log 3 ≈ 0.6309, which does not depend on k.
- **Check 3**: Σₖ (ε·2⁻ᵏ)ˢ = εˢ · Σₖ 2^(−ks) = εˢ / (2ˢ − 1). For s > 0 the denominator is a positive constant, so the whole expression → 0 as ε → 0, and the Hausdorff dimension is 0.
- **Check 4**: x = 0 → (0,0), (0,1), (0,2); y = 0 → (0,0), (1,0), (2,0); y = x → (0,0), (1,1), (2,2); y = 2x + 1 → (0,1), (1,0), (2,2). All of these are among the 7 points, and the directions of the four lines are exactly vertical and slopes 0, 1 and 2.
- **Check 5**: every point of the cross has either x = 0 or y = 0, so xy = 0. Direction (1,1): 1·1 = 1 ≠ 0; direction (1,2): 1·2 = 2 ≠ 0.
- **Check 6**: (4π)^(1/3)·λ ≤ C δ^(−ε)·V^(1/3), so V ≥ 4π·λ³·δ^(3ε)/C³ = (π/2)·δ^(3ε)/C³.
- **Check 7**: 3 × 0.25 − 0.5 = 0.25 (checked by script).

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| Kakeya set (Besicovitch set) | A set that contains a unit line segment in every direction |
| Box dimension (Minkowski dimension) | Cover with boxes of equal size; the d in N(δ) ≈ δ^(−d) |
| Hausdorff dimension | Covers with pieces of different sizes are allowed; the smallest s for which the "s-dimensional cost" can be pushed down to 0 |
| Kakeya set conjecture | Every Kakeya set in ℝⁿ has dimension n |
| Kakeya maximal conjecture | The Lⁿ norm of the largest tube average in each direction is only a factor δ^(−ε) larger than the norm of f |
| Shading and λ | Each tube "lights up" only a portion that makes up a fraction λ of it |
| Fourier extension operator | Builds a field in space by superposing monochromatic plane waves arriving from every direction on the sphere |
| Wave packet | A wave whose frequencies are concentrated in a small cap; in space it is concentrated on a tube |
| Stein restriction conjecture | The extension operator is bounded for p > 2n/(n−1) |
| Bochner–Riesz mean | Rounds off the edge of the spherical cutoff, (1 − \|ξ\|²)^δ |
| Local smoothing | Solutions of the wave equation recover smoothness after averaging in time |
| Planar Furstenberg estimate | A lower bound for counting point–tube incidences in the plane; Ren–Wang's sharp version is a shared input of this cluster |

## Appendix: Further reading

- **Introductions**: Quanta 2025-03-14: https://www.quantamagazine.org/once-in-a-century-proof-settles-maths-kakeya-conjecture-20250314/ ; Quanta 2026-07-23 (Fields Medal): https://www.quantamagazine.org/hong-wang-wins-2026-fields-medal-the-third-woman-ever-20260723/
- **Surveys**: Joshua Zahl, *A survey of the Kakeya conjecture, 2000–2025*: https://arxiv.org/abs/2512.09397 ; Larry Guth, Séminaire Bourbaki lecture notes 1251 (2026-03): https://www.bourbaki.fr/TEXTES/Exp1251-Guth.pdf
- **The restriction problem**: Terence Tao, *Some recent progress on the restriction conjecture* (2003): https://arxiv.org/abs/math/0303136 (the standard exposition of the wave packet argument in §14.6.3)
- **The three-dimensional proof**: Wang–Zahl https://arxiv.org/abs/2502.17655 ; Guth–Wang–Zahl https://arxiv.org/abs/2601.14411
- **Finite fields**: Dvir https://arxiv.org/abs/0803.2336 (the argument is very short; I recommend reading it yourself); Dvir–Kopparty–Saraf–Sudan https://arxiv.org/abs/0901.2529 ; Blokhuis–Mazzocca https://arxiv.org/abs/0911.4370 ; Guth, *Polynomial Methods in Combinatorics* (AMS, 2016)
- **OpenAI's original papers**: three-dimensional maximal https://github.com/openai/math/blob/main/preprints/The-Kakeya-maximal-conjecture-in-three-dimensions-September-23-2026/paper.pdf ; four-dimensional https://github.com/openai/math/blob/main/preprints/Every-four-dimensional-Kakeya-set-has-full-Hausdorff-dimension-September-24-2026/paper.pdf (read Section 1 of each first); for the rest of the cluster, 073/077/078/079, see the corresponding entries in https://github.com/openai/math/blob/main/CONTENTS.md
- **Lean**: https://github.com/openai/math/blob/main/lean/OAI/Analysis/Kakeya/FixedScale.lean
- **Reactions** (source of the quotes in §14.8.4): https://officechai.com/ai/mathematicians-react-with-shock-and-wonder-after-openai-releases-over-300-math-proofs-at-once/
