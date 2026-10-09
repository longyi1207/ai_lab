# Explainer 06: The chromatic number of the plane χ ≥ 6 (the Hadwiger–Nelson problem)

> This is the "explained from zero" version of §9 of the deck in `notes/openai_math_explained/` (`<section id="color">`). The only prerequisites: you know what a graph is (vertices + edges), you can use the Pythagorean theorem to compute the distance between two points, and you know cos/sin. Words like measure and ergodic theory are explained the first time they appear.
> Every number in the text is either computed by script (script: `精讲/scripts/06_coloring.py`, with results copied into the text) or has a source. The **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter.
> Estimated reading time: 50–80 minutes. You can read it in three sittings: Sections 1–4 (graph coloring, lower bound 4, upper bound 7), Sections 5–7 (the 2018 breakthrough, "weird sets" and the axiom of choice, why 6 is hard), Sections 8–10 (OpenAI's result, verification, what it means).

---

## 0. The bottom line: the one thing this chapter explains

The problem itself is something a grade-schooler can understand: **give every point in the plane a color, so that any two points at distance exactly 1 have different colors. What is the minimum number of colors?** This minimum is called the "chromatic number of the plane", written χ(ℝ²).

Since 1950 it has been known that the answer is between 4 and 7, and then it stayed stuck for 68 years. In 2018 the lower bound was pushed to 5. OpenAI claims to have pushed it to 6, so the answer can only be 6 or 7.

This chapter explains a causal chain:

> Lower bounds come from "finding a finite point set that can't be colored" (the Moser spindle → de Grey's 1581-point graph) ⟸ in principle you can always find one this way (the de Bruijn–Erdős compactness theorem) ⟸ but the point set needed may be too large to find by search ⟸ OpenAI took a different road: first turn "any weird coloring" into "a measurable coloring" (ergodic theory), then use geometry to rule out measurable 5-colorings, and the last step comes back to the 7-point Moser spindle.

After reading this chapter, you should be able to explain in your own words:
- why 3 colors are not enough (you can prove it by drawing 7 points by hand), and why 7 colors are enough (a hexagonal tiling);
- why "are the color classes measurable or not" is the real difficulty in this problem, and how it relates to the axiom of choice;
- what OpenAI's proof does structurally, why its Lean statement can be checked at a glance, and what it does **not** settle (6 or 7).

---

## 1. Graph coloring: an old friend from CS

### 1.1 Definitions

A **graph** is a set of vertices plus a set of edges. A **proper coloring**: give each vertex a color so that any two vertices joined by an edge have different colors. The minimum number of colors a graph needs is its **chromatic number** χ(G).

You've seen this in CS:
- **Register allocation**: variables are vertices, two variables that are "live at the same time" are joined by an edge, and colors are registers. Chromatic number = the minimum number of registers needed.
- **Course/exam scheduling**: courses are vertices, two courses that share a student are joined by an edge, and colors are time slots.

Deciding whether a general graph can be 3-colored is NP-complete. This will matter later: with brute-force computer search, once the graph gets big, the search becomes infeasible.

### 1.2 A few toys to work by hand

- One edge: needs 2 colors.
- **Triangle** (3 points, all pairwise connected): 2 colors aren't enough. The script enumerated all 2³ = 8 colorings and found **0** proper ones. So a triangle needs 3 colors.
- In general, if a graph has k points all pairwise connected (called a k-clique), it needs at least k colors. The converse doesn't hold: the chromatic number can be larger than the largest clique. The Moser spindle below is an example: it has no 4-clique, yet it needs 4 colors.

**[Check 1]** A ring of 5 points (a 5-cycle, where each point is connected only to its left and right neighbors): what is the minimum number of colors? Why aren't 2 enough?

---

## 2. Turning the whole plane into a graph

### 2.1 The unit-distance graph

Now treat **every point of the plane** as a vertex (there are uncountably infinitely many), and join two points by an edge if and only if their distance is **exactly 1**. This enormous graph is called the **unit-distance graph** of the plane, and its chromatic number is χ(ℝ²).

An equivalent way to say it: split the plane into k pieces (one color per piece) such that **no** piece contains two points at distance exactly 1. What is the minimum number of pieces?

Two things to note:
- The distance is "exactly 1", not "less than 1". Two points at distance 0.999 or 1.001 may have the same color.
- **There is no requirement at all on the shape of the color pieces.** They can be nice hexagons, or weird sets built with the axiom of choice that can't be drawn at all. This is the core difficulty of the whole problem; Section 6 is devoted to it.

### 2.2 The first few steps

- **χ ≥ 2**: any two points at distance 1 already need 2 colors.
- **χ ≥ 3**: draw an equilateral triangle with side 1. Its three points are pairwise at distance 1; it's the triangle from Section 1.2, and 2 colors aren't enough.

The recipe for lower bounds is set right here: **find a finite set of points in the plane whose unit-distance edges form a graph, prove that this finite graph can't be colored with k colors, and then the plane can't be colored with k colors either** (because any proper coloring of the plane, restricted to these few points, is a proper coloring of this small graph).

---

## 3. Lower bound 4: the Moser spindle (1961)

### 3.1 Step one: a rhombus forces its two tips to share a color

Put two equilateral triangles of side 1 together to form a rhombus: O=(0,0), B=(1/2, √3/2), C=(1,0), T=(3/2, √3/2). O–B–C is one triangle, B–C–T is the other, and they share the edge BC.

With only 3 colors: O, B and C are pairwise adjacent, so each takes one of the three colors; T is adjacent to both B and C, so T can only use the remaining color, which is O's color. **Conclusion: with 3 colors, O and T must have the same color.** Script check: this rhombus has 6 proper 3-colorings in total, and in every one of them O and T have the same color.

The distance between O and T is √3 ≈ 1.732 (computed by script), not 1, so their sharing a color does not by itself break any rule.

### 3.2 Step two: add a second rhombus and rotate it

Rotate the whole rhombus about O by an angle θ to get a second rhombus O, B₂, C₂, T₂. By the same argument, T₂ must also have the same color as O. Now choose θ so that the distance between T and T₂ is exactly 1.

Both tips lie on the circle centered at O with radius √3, separated by angle θ. The square of their distance is:

```
|T − T₂|² = (√3)² + (√3)² − 2·3·cos θ = 6 − 6 cos θ
```

Setting it equal to 1 gives **cos θ = 5/6**, θ ≈ 33.56° (computed by script).

Now T and T₂ must both have the same color as O, but they are at distance 1 from each other, so they must have different colors. **Contradiction. So 3 colors aren't enough, and χ ≥ 4.**

### 3.3 Script check

The script builds 7 points from the coordinates above:

| Point | Coordinates (four decimal places) |
|---|---|
| O | (0, 0) |
| B₁ | (0.5, 0.866) |
| C₁ | (1, 0) |
| T₁ | (1.5, 0.866) |
| B₂ | (−0.062, 0.9981) |
| C₂ | (0.8333, 0.5528) |
| T₂ | (0.7713, 1.5508) |

It then checks the distances of all 21 pairs of points; exactly **11 pairs** are at distance 1: 5 edges from each rhombus, plus T₁–T₂. No unexpected extra unit distances.

Then brute-force enumeration:
- 3 colors: 3⁷ = 2187 colorings, **0** proper.
- 4 colors: **384** proper (= 4! × 16, i.e. if you ignore the names of the colors there are 16 essentially different colorings).

So this 7-point, 11-edge graph has chromatic number exactly 4. It is called the **Moser spindle** (published by the Moser brothers in 1961).

**[Check 2]** Above we used |T − T₂|² = 6 − 6cos θ. Derive it yourself using the law of cosines, and verify that the distance really is 1 when cos θ = 5/6.

**Remember this 7-point graph**: the last step of OpenAI's 62-page proof still uses it.

---

## 4. Upper bound 7: a hexagonal tiling

Lower bounds come from "finding a small graph that can't be colored". An upper bound requires **giving a coloring that is proper for the entire plane**.

### 4.1 The construction

1. Tile the plane with regular hexagons (a honeycomb). The paper takes the hexagons' circumradius to be r = 2/5.
2. Any two points in the same hexagon are at distance at most its diameter, 2r = 0.8 < 1. **So a whole hexagon can be given one color**, and no pair of points inside it is at distance 1.
3. Color the hexagons periodically with 7 colors, so that two different hexagons of the same color are far enough apart. In the paper, the centers of same-colored hexagons are at least √21·r ≈ 1.833 apart, so points in the two pieces are at least (√21 − 2)·r ≈ **1.033 > 1** apart (computed by script).
4. Points on the boundaries can be assigned to any one of the adjacent pieces (this is how the paper handles them, and the Lean version also covers the boundaries).

### 4.2 Where "7 colors" comes from

The centers of the hexagons form a triangular lattice. The paper writes it with complex numbers: lattice points have the form a·(m + n·ω), where ω = e^(2πi/3) is a cube root of unity (the Eisenstein integers from Explainer 01 §8.2 show up again).

Multiplying by (2 − ω) gives a sublattice that is "scaled up and rotated a bit". It makes up 1/7 of the original lattice, because |2 − ω|² = 7 (computed by script: 7.000000000000001, where the last digit is floating-point error). The original lattice splits into 7 classes according to "which translated copy of the sublattice a point belongs to", and each class gets one color. In the script this corresponds to a very simple rule: the center a·(m + nω) gets color (m + 2n) mod 7.

### 4.3 Script check

The script randomly scattered **200,000** pairs of points at distance exactly 1 (for each pair, pick a random point, then walk distance 1 in a random direction), colored them with the rule above, and found **0 pairs with the same color**.

**[Check 3]** r can't be just anything. For the construction to work, we need 2r < 1 and (√21 − 2)·r > 1. What is the allowed range of r?

So **4 ≤ χ(ℝ²) ≤ 7**. This interval held from 1950 (Nelson got 4 and Isbell got 7, neither published at the time; Soifer later pieced together the historical record; Hadwiger published it formally in 1961) until 2018.

---

## 5. 2018: de Grey pushes the lower bound to 5

### 5.1 A breakthrough by an amateur mathematician

In April 2018, Aubrey de Grey (known for his research on the biology of aging; mathematics is a hobby for him) posted *The chromatic number of the plane is at least 5* on arXiv (arXiv:1804.02385). The method was still the recipe from Section 2.2: assemble a huge finite unit-distance graph out of many parts like the Moser spindle, and prove that it **can't be 4-colored**. The corrected graph has **1581 vertices**, and the "can't be 4-colored" step was verified by computer.

### 5.2 Follow-ups: making the evidence smaller and readable

| Year | Who | What they did | Source |
|---|---|---|---|
| 2018 | Heule | Used a SAT solver plus "unsatisfiable core" extraction to get a 553-vertex graph needing 5 colors | arXiv:1805.12181 |
| 2018/2020 | Exoo, Ismailescu | Independently gave another proof of χ ≥ 5 | arXiv:1805.00157 |
| 2020 | Parts | Shrank the graph to 509 vertices (graph minimization) | arXiv:2010.12665 |
| 2020 | Parts | Gave a proof of χ ≥ 5 that **a human can check by hand** | arXiv:2010.12661 |

This phase also included the crowdsourced project Polymath16 (organized by Dustin Mixon on his blog), and the work above was intertwined with it.

**Where the 509 points come from**: according to the introduction of the OpenAI paper, SAT plus unsatisfiable cores gave Heule's **553** points; the **509** points came from Parts's graph minimization. Both are connected to Polymath16.

### 5.3 Why this road keeps getting harder

A graph with n vertices and k colors has kⁿ possible colorings (orders of magnitude computed by script):

| Graph | Vertices | Colors | kⁿ ≈ |
|---|---|---|---|
| Moser spindle | 7 | 3 | 10^3.3 |
| Parts | 509 | 4 | 10^306 |
| Heule | 553 | 4 | 10^333 |
| de Grey | 1581 | 4 | 10^952 |

A SAT solver of course doesn't enumerate these one by one; it relies on pruning. But to prove "there are none at all", the solver has to rule out the whole space, and the graph for 5 colors is expected to be much larger still. Going from 4 to 5 already needed a graph with over a thousand points; going from 5 to 6, nobody knows how big the graph has to be, and nobody found one during Polymath16.

### 5.4 A safety-net theorem: de Bruijn–Erdős compactness

If the finite graph we're looking for might be absurdly large, **does it necessarily exist**? Yes. This is the **de Bruijn–Erdős theorem (1951)**:

> A graph (possibly infinite) can be colored with k colors if and only if **every finite subgraph** of it can be colored with k colors.

So "the plane can't be 5-colored" is equivalent to "some finite unit-distance graph can't be 5-colored". But the proof of this theorem is **non-constructive**: it guarantees that such a finite graph exists, but doesn't tell you what it looks like or how big it is.

Here is an analogy that comes naturally to CS people: it's like "if every finite subset of the constraints is satisfiable, then the whole infinite constraint system is satisfiable". The proof uses compactness of an infinite product space (Tychonoff's theorem), which requires the **axiom of choice** (explained in the next section). §4 of the OpenAI paper states this step explicitly: "using product compactness in ZFC".

---

## 6. The real difficulty: weird sets, measurability and the axiom of choice

### 6.1 What "measurable" means

Roughly speaking, a set in the plane is **measurable** if it has a sensible "area". Every shape you can draw (polygons, disks, countable unions of them, plus some more complicated but "well-behaved" sets) is measurable.

But in the usual set theory (ZFC, the axiom system that includes the **axiom of choice**), you can construct **non-measurable** sets: they have no sensible area, you can never draw them, and you can only prove they exist. The most famous examples are the Vitali set and the Banach–Tarski paradox (a ball is cut into finitely many pieces and reassembled into two balls of the same size; the pieces are non-measurable).

**The axiom of choice** says: given infinitely many nonempty boxes, you can always pick one element from each box, even if you can't write down a rule for picking. The vast majority of mathematicians accept it by default.

### 6.2 The measurable chromatic number: a different problem

If you require each color class to be measurable, the minimum number of colors is called the **measurable chromatic number** χ_m(ℝ²). Clearly χ_m ≥ χ (an extra restriction can only make coloring harder).

- **Falconer (1981)**: χ_m(ℝ²) ≥ 5. The tool is "density points": near almost every point of a measurable set, the set fills almost 100% of the area. Around such a point, it's hard for the unit circle to avoid points of the same color; combined with a rotation argument, this gives a contradiction.

In other words, **under the "measurable" restriction, 5 was proved back in 1981**, 37 years before de Grey. The hard part is removing the "measurable" condition.

### 6.3 A cautionary example

The introduction of the OpenAI paper cites an example by Payne (2009) that illustrates the issue well: consider a subgraph of the plane in which two points are joined only when their difference is exactly "a unit vector with rational coordinates" (for example, (3/5, 4/5)).
- If any coloring is allowed, **2 colors** are enough for this graph;
- If the coloring must be measurable, it needs **at least 5 colors**.

So "measurable colorings" and "arbitrary colorings" can't be assumed to be the same, even when their distance constraints look identical. (⚠ I didn't read Payne's original; this restates what §1 of the OpenAI paper says.)

### 6.4 Shelah–Soifer: the answer might depend on the axioms

In *Axiom of choice and chromatic number of the plane* (J. Combin. Theory Ser. A 103 (2003) 387–391), Shelah and Soifer constructed some "distance graphs" whose chromatic number **depends on which axioms you use**: it is 2 in ZFC, but uncountable in the axiom system that "drops the axiom of choice and replaces it with 'every set of reals is measurable'" (ZF + DC + LM; Solovay proved in 1970 that this system is consistent, provided you assume an "inaccessible cardinal" exists).

They also proposed a conditional theorem, roughly: if all finite unit-distance graphs can be 4-colored, then the chromatic number of the plane is 4 in ZFC, but at least 5 in ZF+DC+LM (because in that world every coloring is measurable, so Falconer's result applies). (⚠ I paraphrased the exact statement of the conditional theorem from Soifer's later survey and did not check it word for word against the original.)

The premise of this conditional theorem has been refuted by de Grey, but the possibility it reveals is still there: **"how many colors the plane really needs" might not have an answer independent of the axioms.** That is also why the OpenAI paper states at the very start that it is "working throughout in ZFC".

### 6.5 "Nice" colorings: the answer is already known to be 7

If you require the color pieces to be "map-like" (with regular curves as boundaries), the situation is different again:
- Townsend (announced 1981, details published 2005): map-like colorings need at least **6** colors.
- Sokolov–Voronov (2025, arXiv:2502.01958): in a "polygonal, locally finite" framework, at least **7** colors are needed.

In other words, **for colorings "you can draw", the answer is 7**. The remaining question is: can weird sets save colors compared with nice colorings?

---

## 7. Why ≥ 6 is hard: both roads are blocked

Before 2026, the situation looked like this:

| Approach | What it can achieve | Where it gets stuck |
|---|---|---|
| Finite graphs + computers (de Grey, Heule, Parts) | χ ≥ 5 | The finite graph needed for 6 colors may be enormous; nobody has found one |
| Measurability / density points (Falconer) | χ_m ≥ 5 | Holds only for measurable colorings; says nothing about weird sets |
| Regular boundaries (Townsend, Sokolov–Voronov) | map-like ≥ 6, polygonal = 7 | Requires regular boundaries; says nothing about general measurable sets, let alone weird sets |

To get to 6, you need to clear two hurdles at once:
1. **From arbitrary colorings to measurable colorings**: how do you make weird sets "analyzable"?
2. **From measurable colorings to a geometric contradiction**: the boundaries of measurable sets can be extremely irregular, so you can't just draw them as a map.

OpenAI's paper corresponds exactly to these two steps.

---

## 8. What OpenAI claims

### 8.1 The main result

The abstract of the paper *The Euclidean plane is not five-colorable* (OpenAI, 2026-09-23, 62 pages, Family 158):

> "We prove that every coloring of the Euclidean plane with five colors has a monochromatic unit-distance pair, with no regularity assumption on the color classes. Consequently, the chromatic number of the plane is either six or seven."

In plain words: **every 5-coloring of the plane contains two points at distance 1 with the same color, and no regularity is required of the color pieces. So the chromatic number of the plane is 6 or 7.**

The paper's Theorem 1.1 writes this as 6 ≤ χ(ℝ²) ≤ 7, and immediately adds: "The remaining alternatives six and seven are unresolved."

**A common misreading**: it is easy to assume this result is "find a bigger finite graph and verify it with SAT". **It isn't.** The paper never gives a single finite graph that can't be 5-colored.

### 8.2 The two halves of the proof

The paper splits the proof into two theorems:

- **Theorem 1.3 (transfer theorem)**: for every k, "a proper k-coloring exists" ⇔ "a **weakly measurable** k-coloring exists". This holds for all k, not just 5.
- **Theorem 1.4**: no weakly measurable 5-coloring exists.

Together: if there were a proper 5-coloring, then by 1.3 there would be a weakly measurable 5-coloring, contradicting 1.4.

**What a "weakly measurable k-coloring" is** (a plain-language version of Definition 1.2): every color piece is measurable, and the "same-colored unit-distance pairs" are null in the sense of measure. That is, exceptional same-colored pairs are allowed, but there are so few of them that they have zero area and can be ignored. This is weaker than a "proper coloring" (it allows measure-zero violations), and more regular than an "arbitrary coloring" (it must be measurable).

### 8.3 Intuition for the first half: "averaging" a weird coloring into a statistical regularity

What follows is my simplified paraphrase of §1.1 of the paper; the technical details go far beyond this.

1. **First shrink to a countable point set.** Take all points whose coordinates are **algebraic numbers** (roots of polynomial equations, like √2 or (1+√5)/2), and call this set E. It has only countably many points, but it is dense in the plane, and it is closed under "multiplying by an algebraic complex number of absolute value 1" (that is, rotation by an algebraic angle).
2. **Average over translations and rotations.** Restrict the weird coloring to E, then "take the average" over all translations and rotations to get a **random coloring** whose statistics are invariant under any translation or rotation. Averaging like this relies on these groups being **amenable** (roughly, "you can take a fair average over them"; the chapter on Thompson's group, family 248, covers this in detail).

   An analogy with something familiar: this is like turning a very irregular signal into a **stationary random process**. A single sample may be weird, but its statistics (for example, its autocorrelation function) are regular.
3. **Use the spectral theorem for a "Fourier decomposition".** A stationary process can be decomposed by frequency (compare the power spectrum of an EEG). Here the "frequencies" come in two kinds: ordinary continuous frequencies (corresponding to ordinary waves exp(iξ·z) on the plane), and a kind of "wild" frequency that only makes sense on the countable point set E.
4. **Rigidity theorem (Theorem 2.3)**: any distribution that is invariant under rotations and does not sit on the ordinary frequencies **must be completely uniform noise** (Haar measure). Uniform noise has zero correlation under any nonzero translation, so throwing it away doesn't break the correlation condition "unit-distance pairs have different colors". The proof of this step uses the **Furstenberg–Zimmer structure of compact extensions**, a tool from ergodic theory developed for proving Szemerédi's theorem.
5. **The remaining ordinary-frequency part can be extended to the whole plane**, giving a genuine measurable function. Then taking the most likely color at each point gives a weakly measurable coloring.

The reverse direction (weakly measurable ⇒ proper) uses a Falconer-style density-point argument plus the de Bruijn–Erdős compactness from Section 5.4.

### 8.4 Intuition for the second half: ruling out 5 colors with geometry

Again a simplified paraphrase:

1. **"Palette"**: around each point x, look at the unit circle and record which colors appear in which directions on the circle. The paper proves that almost every such palette has **at most 2 colors** (§5).
2. **A "boundary graph" between colors**: treat the 5 colors as vertices and record which pairs of colors have a lot of transitions between them. The paper proves this graph contains a **cycle** (§6–7, using mollification, thresholding and a topological argument about coverings of the plane).
3. **A cycle on 5 colors can only have length 3, 4 or 5**, and §8 rules them out one by one:
   - 5-cycle: a combinatorial contradiction about a "6-letter angle word";
   - 4-cycle: a parity contradiction;
   - 3-cycle: it leaves an open region that uses only 3 colors, and then a "placement certificate" with rational coordinates puts **the 7 points of the Moser spindle** into this region. Section 3 already proved that 3 colors aren't enough for those 7 points: contradiction.

You can see the definition of this "three-color region" directly in the Lean code (`OAI/Geometry/PlaneColoring/Moser.lean`):

```lean
def ThreeLabelRegion (x y : ℝ) : Prop :=
  0<x^2+y^2 ∧ x^2+y^2<4 ∧
    y^2*(3*x^2-y^2)^2 < (x^2+y^2)^3*(1-(x^2+y^2)/4)*(x^2+y^2-1)^2
```

It's a region of the plane described by polynomial inequalities, and each point of the spindle has to be verified to lie inside it. **The whole 62-page argument starts from the 7-point toy of 1961 and comes back to it in the end.**

### 8.5 Two side results

- **Corollary 1.5 (the "bad fraction" has a positive lower bound)**: there is a constant δ > 0 such that in any 5-coloring, the fraction of "randomly placed needles of length 1 whose two ends have the same color" is at least δ. But the paper itself says: "The graph and the positive constant here are existential." That is, δ is **only known to exist; nobody knows how big it is**, because it comes from that finite graph needing 6 colors whose shape nobody knows.
- **Footnote 1 (Reed's manuscript, 2026-05)**: Reed claims χ = 7 and attaches a "formalized theorem". The OpenAI paper points out that this theorem put a **false** density upper bound in as a **hypothesis** (counterexample: the half-open arc {e^(it) : 0 ≤ t < π/3}), so the formalization itself is not wrong; what's wrong is the proposition being proved. ⚠ I didn't read Reed's original manuscript; I only saw OpenAI's account of it. This example will be used in Section 9.

---

## 9. How far it has been verified

### 9.1 The Lean statement: two lines, you can read it yourself

File `lean/ComparatorChallenges/EuclideanFiveColor.lean` (snapshot fd4aeeb):

```lean
def ProperColoring (colorCount : ℕ) (coloring : ℂ → Fin colorCount) : Prop :=
  ∀ point otherPoint : ℂ, ‖point - otherPoint‖ = 1 → coloring point ≠ coloring otherPoint

theorem no_proper_five_coloring : ¬ ∃ coloring : ℂ → Fin 5, ProperColoring 5 coloring
```

Word-by-word translation:
- `coloring : ℂ → Fin colorCount`: a coloring is just a function that maps each complex number (i.e. a point in the plane, using ℂ as the plane) to a color in {0, 1, …, colorCount−1}. **The function can be arbitrary**; there's no requirement like "measurable" or "continuous".
- `∀ point otherPoint : ℂ`: for any two points in the plane.
- `‖point - otherPoint‖ = 1 →`: if their distance (the modulus of the complex difference) is exactly 1,
- `coloring point ≠ coloring otherPoint`: then their colors differ. This is exactly "proper coloring".
- `¬ ∃ coloring : ℂ → Fin 5, ProperColoring 5 coloring`: there **does not exist** any proper 5-coloring.

This is exactly the original statement of "5 colors aren't enough" for the Hadwiger–Nelson problem, with no sneaked-in measurability and no extra premises. Compared with the quasi-Riemann hypothesis in Explainer 01, it doesn't even depend on whether Mathlib's definition of some complicated function (like ζ) is correct; it only uses complex numbers, the modulus and finite sets. **This is one of the easiest statements for a human to audit in the entire OpenAI repository.**

The upper bound is formalized too: `properColoring_seven` in `ComparatorChallenges/PlaneColoring.lean`, where the plane is `EuclideanSpace ℝ (Fin 2)` and the condition is `dist x y = 1 → c x ≠ c y`. The proof file `Seven.lean` is only 68 lines.

### 9.2 The proof itself (statistics we ran ourselves)

- The proof entry point is `OAI/Geometry/PlaneColoring/Five.lean`. A script followed its `import`s to collect all of its transitive dependencies inside the OAI directory: **70 files, 30,406 lines**.
- grep over these 70 files: **no** `sorry`, `admit`, custom `axiom` or `native_decide`.
- The final assembly corresponds exactly to the two halves of the paper:

  ```lean
  theorem no_proper_five_coloring : ¬ ∃ c : ℂ → Fin 5, ProperColoring 5 c := by
    rintro ⟨c,hc⟩
    obtain ⟨d,hd,hw⟩ := proper_to_borel_weak hc        -- transfer theorem (Theorem 1.3)
    exact no_measurable_weak_five_coloring hd hw         -- geometric obstruction (Theorem 1.4)
  ```

- The Comparator configuration (`EuclideanFiveColor.json`) allows only the three standard axioms: `propext`, `Quot.sound` and `Classical.choice`. Note:
  - `Classical.choice` is the **axiom of choice** in Lean. So what this formalization proves is "in mathematics with the axiom of choice, the plane can't be 5-colored", which agrees with the paper's "in ZFC". The point in Section 6.4 that "with a different set of axioms the answer may differ" is not touched by this proof.
  - `"enable_nanoda": false`: an independent second checking kernel is **not** enabled. Someone independently re-checked the quasi-Riemann hypothesis of Explainer 01 with nanoda; for this one, as of 2026-10-08 we found no public record of an independent re-check ⚠.
- We did **not compile** this proof ourselves; the above comes from reading the source.

### 9.3 Human experts

- **Gil Kalai** (blog post, 2026-10-07): "The new manuscript raises the lower bound to six, leaving six and seven as the two possible answers." The disclaimer section of the same post says "even Lean verification may have issues".
- **As of 2026-10-08, we found no public statement from de Grey, Polymath16 members or other combinatorial geometry experts saying they had read and verified the 62 pages.**
- The 2026-10-07 history of the OpenAI repository lists 3 retractions and 14 revisions; **this paper is not among them**. Family 158 is also **not** among the 10 families whose reasoning summaries are published in the README.

### 9.4 How to think about the remaining risk

- **Statement risk: very low.** Two lines that anyone can check against the original problem; see 9.1.
- **Proof risk: depends on the Lean kernel and Mathlib.** The measure theory, spectral theorem and so on used in the proof come from Mathlib or from these 70 files; the kernel checks every step. As long as the kernel has no bug and the statement is right, the conclusion holds.
- **Understanding risk: high.** Ergodic theory plus geometric topology, 62 pages, and no human expert has publicly read it all yet.
- **Reed as a cautionary tale**: Reed's "formalized theorem" doesn't count because the error was hidden in a **hypothesis**. OpenAI's statement has no hypotheses; nothing at all comes before `no_proper_five_coloring`, so the same problem can't arise. This shows exactly what the human half should be auditing in the division of labor "humans audit the statement, machines audit the proof".

---

## 10. What it would mean if true (and what it would not)

### 10.1 For mathematics

1. **χ(ℝ²) ∈ {6, 7}.** This is the first progress since 2018, and the first time the lower bound has been pushed without a finite graph.
2. **The transfer theorem itself may matter more than the "6"**: it holds for all k, which amounts to saying that "arbitrary colorings" and "weakly measurable colorings" are the same thing for this problem. Future work on the problem can go straight to the measurable world and use analytic tools, without worrying about weird sets. (This is my judgment; it counts as speculation.)
3. **A new open problem**: by de Bruijn–Erdős, there must be a finite unit-distance graph that can't be 5-colored, but nobody knows what it looks like or how big it is. Finding it (for example, with a SAT solver) would give a completely independent proof that can be verified finitely. This is a natural follow-up target for "AI + SAT" (speculation).

### 10.2 What it does not mean

- **It doesn't decide between 6 and 7.** The paper says explicitly that both possibilities remain unresolved.
- Section 6.5 says "nice colorings need 7 colors", so if the answer is 6, the coloring must use weird sets or extremely irregular measurable sets. Some people will guess from this that the answer is 7, but that's only intuition, not evidence (speculation).
- **It says nothing about worlds without the axiom of choice.** The proof is carried out in ZFC (`Classical.choice` in Lean). The question from Section 6.4 of what happens in a world where "all sets are measurable" is still open. Intuitively, in that world every coloring is measurable, so the geometric part, Theorem 1.4, would seem to be enough; but I haven't checked whether its proof uses more choice than DC ⚠ (speculation).
- **It gives no numerical value for δ**, and no concrete finite graph needing 6 colors.

### 10.3 For AI and AI safety

- This is verifiability in its ideal form: **a two-line statement, a 30,000-line proof**, and humans only need to audit the two lines. Compared with the quasi-Riemann hypothesis, it doesn't even need the layer of trust "is Mathlib's definition of ζ correct?".
- Reed's counterexample shows the other side: **Lean only guarantees that "the given statement has been proved"**; the statement and its hypotheses still need human checking. This is the same kind of problem as specification gaming in reward models: the optimizer satisfies the spec you wrote down, not necessarily what you wanted.
- The "surprising" method (ergodic theory + geometric topology, rather than a bigger finite graph) deserves attention: if it holds up, it's an example of "the model found a route nobody in the field had taken", rather than "computing faster along a known route". Whether nobody had really taken it needs a domain expert's judgment ⚠.

---

## 11. Self-test

Try answering these after reading. If you can't, go back and reread the corresponding section.

1. Why does finding a finite point set in the plane that can't be k-colored imply χ(ℝ²) > k? (Section 2.2)
2. In three sentences, restate why the Moser spindle proves that 3 colors aren't enough. (Section 3)
3. In the hexagonal 7-coloring, which two inequalities does r = 2/5 satisfy? What does each one guarantee? (Section 4)
4. What does the de Bruijn–Erdős theorem say? Why does it guarantee that a finite graph needing 6 colors exists, but not help you find it? (Section 5.4)
5. Falconer proved "5" back in 1981, so why was de Grey's "5" in 2018 still a breakthrough? (Section 6.2)
6. What are the two halves of OpenAI's proof? Which half holds for every number of colors k? (Section 8.2)
7. What is the fundamental difference in trustworthiness between Reed's "formalized theorem" and OpenAI's `no_proper_five_coloring`? (Sections 8.5, 9.4)

---

## Appendix: answers to the checks

- **Check 1**: 3 colors. With 2 colors, the colors must alternate around the ring (red, blue, red, blue, …). On a ring of odd length, when you go all the way around back to the start, the starting point would have to share a color with its own neighbor: contradiction. In general, a graph can be 2-colored if and only if it has no cycle of odd length.
- **Check 2**: T and T₂ are both at distance √3 from O, with angle θ between them. Law of cosines: |T − T₂|² = 3 + 3 − 2·√3·√3·cos θ = 6 − 6cos θ. When cos θ = 5/6 this equals 6 − 5 = 1, so the distance is 1.
- **Check 3**: 2r < 1 ⇒ r < 1/2; (√21 − 2)r > 1 ⇒ r > 1/(√21 − 2) ≈ 0.3872 (computed by script). So 0.3872 < r < 0.5, and the paper's choice r = 0.4 is in range.

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| Proper coloring | A coloring in which adjacent vertices have different colors |
| Chromatic number χ(G) | The minimum number of colors a proper coloring needs |
| Unit-distance graph | Vertices are points in the plane; two points at distance exactly 1 are joined by an edge |
| χ(ℝ²) | The chromatic number of the plane's unit-distance graph, i.e. the answer to the Hadwiger–Nelson problem |
| Moser spindle | A 7-point, 11-edge unit-distance graph that can't be 3-colored; proves χ ≥ 4 |
| de Bruijn–Erdős theorem | An infinite graph can be k-colored ⇔ every finite subgraph can be k-colored (needs the axiom of choice) |
| SAT solver | A program that decides whether a set of Boolean constraints can be satisfied simultaneously; used to verify that a finite graph can't be k-colored |
| Measurable set | A set with a sensible "area" |
| Measurable chromatic number χ_m | The minimum number of colors when all color pieces must be measurable; Falconer proved ≥ 5 |
| Axiom of choice | You can always pick one element from each of infinitely many nonempty sets; it lets you build non-measurable sets |
| Weakly measurable coloring | Color pieces are measurable and same-colored unit pairs have measure zero (measure-zero exceptions allowed) |
| Amenable | The property of a group that "you can take a fair average" over it |
| Ergodic theory | The branch of mathematics that studies "long-run averages" and invariant statistical regularities |
| Haar measure | The completely uniform distribution on a group; corresponds to "pure noise" |
| Palette | The set of colors appearing on the unit circle around a point |

## Appendix: Further reading

- **The original paper**: https://github.com/openai/math/blob/main/preprints/The-Euclidean-plane-is-not-five-colorable-September-23-2026/paper.pdf (read Section 1 and Figure 1 in §1.1 first; the rest is technical detail)
- **Lean statement**: https://github.com/openai/math/blob/main/lean/ComparatorChallenges/EuclideanFiveColor.lean ; scope note `lean/docs/158.md`
- **Gil Kalai's 2026-10-07 blog post**: https://gilkalai.wordpress.com/2026/10/07/updates-sharing-ai-progress-on-mathematics-amazing-and-my-lecture-plans/
- **Gil Kalai's 2018 introduction to de Grey's result** (the best entry point): https://gilkalai.wordpress.com/2018/04/10/aubrey-de-grey-the-chromatic-number-of-the-plane-is-at-least-5/
- **de Grey 2018**: https://arxiv.org/abs/1804.02385 ; **Heule's 553 points**: https://arxiv.org/abs/1805.12181 ; **Parts's hand-checkable proof**: https://arxiv.org/abs/2010.12661
- **Quanta Magazine**, *Decades-Old Graph Problem Yields to Amateur Mathematician* (2018-04, popular coverage of de Grey)
- **Alexander Soifer**, *The Mathematical Coloring Book* (Springer, 2009; second edition 2024): the full history of the problem, including the chapters on Shelah–Soifer and the axiom of choice ("What If We Had No Choice?").
- **Shelah & Soifer**, *Axiom of choice and chromatic number of the plane*, J. Combin. Theory Ser. A 103 (2003) 387–391.
- **Payne**, *Unit distance graphs with ambiguous chromatic number*: https://arxiv.org/abs/0707.1177
- **Sokolov & Voronov**, map-like colorings need at least 7 colors: https://arxiv.org/abs/2502.01958
- **Terence Tao**, *254A Lecture 9: Ergodicity* (the ergodic theory introduction cited by the paper): https://terrytao.wordpress.com/2008/02/04/254a-lecture-9-ergodicity/
