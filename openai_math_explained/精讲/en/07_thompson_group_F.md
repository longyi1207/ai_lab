# Thompson's group F is nonamenable: a problem "proven" and withdrawn for decades

> Group theory · family 248 of the openai/math release. All you need: fraction arithmetic, what a function and function composition f(g(x)) are, and the length and inner product of vectors. **No group theory is needed.** Every new concept is explained before it is used.
> Every number here is either computed by script (`精讲/scripts/07_thompson.py`, exact arithmetic with Python's `Fraction`) or sourced. **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter. Tags: **[P]** = primary material we read (paper PDF, Lean files, arXiv manuscripts and withdrawal notices); **[R]** = secondhand reporting or paraphrase; **⚠** = unverified or conflicting. As of 2026-10-08.
> Estimated reading time: 60–90 minutes. You can split it into three sittings: §10.1–10.3 (groups, free groups, "fair averages"), §10.4–10.5 (Banach–Tarski, Thompson's group itself), §10.6–10.9 (OpenAI's proof, its verification, and what it means).

---

## 10.0 The bottom line: the one thing this chapter explains

On some infinite "sets of operations" (mathematicians call them **groups**) you can define a **fair average**: shift everything over, and the average does not change. The integers allow this. On other groups such an average is **impossible**. The classic example is the "free group". The reason it cannot be fairly averaged is that it can be cut up, shifted around, and reassembled into **two copies** of itself. This is the mechanism behind the famous Banach–Tarski paradox (cut a ball into a few pieces and reassemble them into two balls).

For a long time mathematicians thought that "cannot be fairly averaged" was always caused by a free group hidden inside. Counterexamples overturned this starting in 1980. But **Thompson's group F**, the most natural and most famous candidate, stayed undecided: it contains no free group, yet it does not belong to any type that "obviously can be averaged". In 1979 Geoghegan conjectured that it **cannot** be averaged. Over the next 47 years, people announced proofs in both directions, and one after another they were found to be wrong and withdrawn.

This chapter explains one causal chain:

> F can be fairly averaged ⟺ F contains finite sets that "barely leak" (Følner sets) ⟹ averaging over such a set produces an approximate fixed point for a map that "pushes every point away by at least ½" ⟹ contradiction. So F cannot be fairly averaged.

OpenAI gave this argument in a 13-page paper on 2026-09-23, together with a Lean formalization.

After this chapter, you should be able to explain in your own words:
- what "amenable" actually means, and why it is the same thing as the Banach–Tarski paradox;
- what the two generators of Thompson's group F look like, and how to compose them by hand;
- why F is the most famous "litmus test" in this field, and why its history makes Lean verification especially valuable;
- which "borrowed" phenomenon OpenAI's proof uses (maps with no fixed point in infinite-dimensional space), and what this result does and does not mean.

---

## 10.1 Groups: a set of operations you can compose and undo

### 10.1.1 A concrete example first: the symmetries of a square

Take a square card and label its four corners A, B, C, D. Which operations put it back into its original outline (the corner labels may move around)?
- Rotations by 0°, 90°, 180°, 270° (4 rotations);
- Flips about the vertical axis, the horizontal axis, and the two diagonals (4 flips).

That is 8 operations in total. Starting from "rotate 90° (call it r)" and "flip about the vertical axis (call it s)" and combining them repeatedly, the script generates exactly these 8, no more and no fewer.

These 8 operations have a few properties:
1. **They compose**: do one, then another, and the result is still one of the 8. Write r∘s for "first s, then r" (the same order as function composition f(g(x)): the one on the right happens first).
2. **There is a "do nothing"**: rotate by 0°, written e (the identity).
3. **Every operation can be undone**: rotating 90° is undone by rotating 270°; each flip is undone by itself.
4. **Associativity**: (a∘b)∘c = a∘(b∘c). Function composition satisfies this automatically.

But **order matters**: computed by script, r∘s and s∘r send the four corners to different places (one swaps A and C, the other swaps B and D). So groups are in general **not commutative**.

### 10.1.2 A second example: adding integers

Take all integers ℤ = {…, −2, −1, 0, 1, 2, …}; an "operation" is "add some number". Composition is addition, the identity is 0, and +3 is undone by −3. This is an **infinite** group, and it is commutative.

### 10.1.3 Definition

> **Group** = a set G together with an operation that combines two elements into one, such that: there is an identity element, every element has an inverse, and the operation is associative.

You can always think of a group as "all the symmetry operations of some object". Every group in this chapter is like that: the symmetries of a square, the translations of the integers, certain stretchings of the interval [0,1] (§10.5).

### 10.1.4 Generators and relations

Many groups can be built entirely out of **a few operations**. These operations are called **generators**.
- The 8 symmetries of the square are generated by r and s.
- ℤ is generated by the single element "+1" (−1 is its inverse, and every integer is a string of +1's or −1's).

Generators often satisfy **relations**. For example, in the square, r∘r∘r∘r = e (four rotations bring you back) and s∘s = e. Relations make different "spellings" give the same element.

---

## 10.2 The free group F₂: a group with no relations at all

### 10.2.1 Reduced words

Take two generators a, b and their inverses a⁻¹, b⁻¹ (also written A, B below). The elements of the **free group F₂** are "words" spelled with these four letters. The only simplification rule is that an adjacent a and a⁻¹ (or b and b⁻¹) cancel. A word with everything cancelled is called a **reduced word**. Apart from that there are **no relations at all**: abab⁻¹ and baba⁻¹ are different elements, and so are ab and ba.

Let's count the reduced words of length n. The first letter has 4 choices; each later letter cannot be the inverse of the letter before it, so it has 3 choices. So there are 4·3ⁿ⁻¹ words of length n.

| Length n | Words of length exactly n ("sphere") | Words of length ≤ n ("ball") | Sphere / ball |
|---|---|---|---|
| 0 | 1 | 1 | 1.000 |
| 1 | 4 | 5 | 0.800 |
| 2 | 12 | 17 | 0.706 |
| 3 | 36 | 53 | 0.679 |
| 5 | 324 | 485 | 0.668 |
| 10 | 78,732 | 118,097 | 0.667 |

(The script counts by enumerating reduced words one by one. Ball size = 2·3ⁿ − 1.)

**Two key points**:
- The number of elements **grows exponentially** with n (roughly 2·3ⁿ). Compare: ℤ has only 2n+1 elements of length ≤ n; ℤ² (with L1 distance) has only 2n²+2n+1, which is 221 for n=10.
- **The outermost layer holds about 2/3 of everything**, and this fraction does not shrink as n grows. The outermost layer of ℤ has only 2 points, a fraction of 2/(2n+1) → 0.

**[Check 1]** There are 12 reduced words of length exactly 2. Write them all out. (Hint: aa, ab, aB, …)

### 10.2.2 Cayley graphs: drawing a group

Draw each element of the group as a point. If multiplying g on the right by a generator gives g′, draw an edge between g and g′. This picture is called the **Cayley graph**.
- ℤ (generator +1): an infinite straight line.
- ℤ² (generators (1,0), (0,1)): an infinite square grid.
- F₂ (generators a, b): an **infinite tree in which every point has 4 edges**. Because there are no relations, different paths from the origin never come back to the same point, so there are no cycles.

In network terms: ℤ² is like a 2D mesh, where the number of nodes grows polynomially with the radius; F₂ is like a 4-way fan-out tree, where **most nodes are on the boundary**. This property is the key to everything below.

---

## 10.3 Amenability: can you "average fairly"?

### 10.3.1 Where the question comes from

Averaging over a finite group is easy: add up the values at every element and divide by the number of elements. This average is "fair": shift the whole group (multiply every element on the left by the same h), and you are just adding the same numbers in a different order, so the average does not change.

On an infinite group this gets hard. There is no "uniform distribution" on ℤ: if every integer has the same probability, that probability must be 0, and then the total is not 1.

Mathematicians get around this by relaxing the requirement. They ask only for a **mean**: a rule that assigns a score M(φ) to every bounded function φ: G → ℝ, such that
1. **Linear**: M(φ + ψ) = M(φ) + M(ψ), M(cφ) = c·M(φ);
2. **Positive**: if φ ≥ 0 everywhere, then M(φ) ≥ 0;
3. **Normalized**: the mean of the constant function 1 is 1;
4. **Left-invariant**: shifting the whole function (replacing φ by g ↦ φ(hg)) does not change the mean.

If such an M exists on a group, the group is called **amenable**; otherwise it is **nonamenable**. This is exactly the definition used in the OpenAI paper and in the Lean statement (see §10.7).

Intuitively, M is an idealized version of "sprinkling a handful of sand evenly over the whole group". It only needs to be **finitely additive** (not countably additive). That is what gives groups like ℤ a chance to qualify.

### 10.3.2 The Følner criterion: find a finite set that "barely leaks"

The definition above is very abstract (M usually cannot be written down; proving it exists requires the axiom of choice). In 1955 Følner gave an equivalent criterion with a combinatorial flavor:

> A group G is amenable ⟺ for any finite collection of "shifts" h and any small ε > 0, you can find a finite set A with |hA △ A| / |A| < ε.

Here hA = {h·a : a ∈ A} is the result of shifting all of A, and △ is the "symmetric difference" (the elements that appear on only one side). |hA △ A|/|A| measures "after one shift, what fraction of the elements changed". The intuition: if A barely changes when shifted, averaging over A approximates a fair average; make A bigger and less and less "leaky", take the limit, and you get M.

**Computed by script**:

| Group | Set A | \|A\| | Shift h | \|hA △ A\| / \|A\| |
|---|---|---|---|---|
| ℤ | {−n,…,n}, n=10 | 21 | +1 | 0.0952 |
| ℤ | n=1000 | 2,001 | +1 | 0.0010 |
| ℤ² | (2n+1)×(2n+1) square, n=10 | 441 | (1,0) | 0.0952 |
| ℤ² | n=100 | 40,401 | (1,0) | 0.0100 |
| F₂ | ball of length ≤ 4 | 161 | a | 1.006 |
| F₂ | ball of length ≤ 10 | 118,097 | a | 1.000 |

For ℤ and ℤ² the fraction → 0, so they are amenable. Shift a ball in F₂ and the fraction **tends to 1**: about half the elements move out and the same number of new elements move in (|hA △ A| counts both sides). The reason is what §10.2 said: "most elements are on the boundary".

**[Check 2]** In ℤ, let A = {−n,…,n} and h = +1. Which two elements make up hA △ A? Use this to verify that the fraction is 2/(2n+1).

### 10.3.3 But "balls fail" does not mean "every set fails"

The table above tried only balls. The Følner criterion asks whether **some** A exists. In principle F₂ could contain some oddly shaped set that does much better than a ball. To prove that F₂ is not amenable, you need an argument that works for **every** set. The cleanest one is the following.

**F₂ can be reassembled into two copies of itself.** Let W(a) = "the reduced words starting with a", and define W(a⁻¹), W(b), W(b⁻¹) the same way. Then:
- F₂ = {e} ∪ W(a) ∪ W(a⁻¹) ∪ W(b) ∪ W(b⁻¹), five pieces with no overlap.
- But **W(a) ∪ a·W(a⁻¹) is already all of F₂**: for any word w that does not start with a, putting a⁻¹ in front gives a⁻¹w, which starts with a⁻¹ (nothing cancels), and w = a·(a⁻¹w).
- Likewise W(b) ∪ b·W(b⁻¹) is also all of F₂.

(The script checked both statements for every word of length ≤ 7, and both hold; in the ball of length ≤ 8, each of the four W pieces has 3,280 words.)

Now suppose F₂ has a fair mean M. Treat "belongs to a set" as a function taking values 0/1; then M gives each piece a "share". By left-invariance, the share of a·W(a⁻¹) equals the share of W(a⁻¹). So:
- M(W(a)) + M(W(a⁻¹)) ≥ M(all of F₂) = 1;
- M(W(b)) + M(W(b⁻¹)) ≥ 1;
- Added together, the four pieces have total share ≥ 2. But they are non-overlapping parts of F₂, so their total share is ≤ 1. Contradiction.

So **F₂ is not amenable**. This "make two copies of yourself out of a few pieces" is called a **paradoxical decomposition**. In 1938 Tarski proved that a group is nonamenable **if and only if** it has a paradoxical decomposition. So "cannot be fairly averaged" and "can duplicate itself" are two sides of the same thing.

Also: **if a group contains a nonamenable subgroup, the group itself is nonamenable** (a standard fact). So every group containing F₂ is nonamenable.

---

## 10.4 The Banach–Tarski paradox and von Neumann's question

### 10.4.1 The paradox

**Banach–Tarski (1924)**: a solid ball in three-dimensional space can be cut into finitely many pieces which, using only rotations and translations, can be reassembled into **two** solid balls each the same size as the original.

This does not violate physics, because the pieces are non-measurable "weird sets" (they require the axiom of choice) and have no volume to speak of. Its mathematical root is exactly the paradoxical decomposition from §10.3.3: the 3D rotation group SO(3) **hides a copy of F₂** (take two rotations about different axes with suitably chosen angles; there are no relations between them). Transfer F₂'s "one copy becomes two" onto the sphere, and you get the paradox.

### 10.4.2 von Neumann, 1929

von Neumann asked: why does this paradox exist in three dimensions but not in two (the plane)? His answer: **the key is not the space but the group of operations**. The group of rotations and translations of the plane is amenable, so it can be fairly averaged. That means the plane admits a "finitely additive, motion-invariant" notion of area, and the paradox cannot happen. The group of motions of 3D space contains F₂ and is nonamenable, so there is room for the paradox. This is how the concept of "amenable" was born (German *messbar*; the English name "amenable" was coined later by Day).

### 10.4.3 The von Neumann–Day problem

Since "contains F₂ ⟹ nonamenable", the natural question is the converse:

> **Must every nonamenable group contain F₂?**

This is usually called the von Neumann problem or the von Neumann–Day problem (Day stated it explicitly in 1957). The answer is **no**, but the counterexamples were hard to come by:

| Year | Author | Counterexample | Features |
|---|---|---|---|
| 1980 | Ol'shanskii | "Tarski monster" groups | Infinite, but every proper subgroup is a finite cyclic group; the construction is extremely complicated |
| 1982 | Adyan | Free Burnside groups with large odd exponent | Some fixed power of every element is the identity |
| 2002 | Ol'shanskii–Sapir | A finitely presented counterexample | The first counterexample that can be written down with finitely many generators and finitely many relations |
| 2013 | Monod | Groups of "piecewise projective" homeomorphisms of the real line | The first "natural" counterexamples; they look a lot like Thompson's groups |
| 2016 | Lodha–Moore | A finitely presented subgroup of Monod's group | Finitely presented and **torsion-free** (no elements of finite order) |

(Monod: *Groups of piecewise projective homeomorphisms*, PNAS 2013; Lodha–Moore: *A nonamenable finitely presented group of piecewise projective homeomorphisms*, Groups Geom. Dyn. 10 (2016) 177–200.)

**Note**: a common claim is that "the counterexamples are all weird, and F would be the first natural counterexample". That was true before 2013; **since 2013, Monod and Lodha–Moore have given natural, finitely presented, torsion-free counterexamples**. So F's significance is not "the first natural counterexample" but "**the most famous, most studied group in this field** finally has an answer".

---

## 10.5 Thompson's group F

### 10.5.1 Definition

> **F** = all functions f: [0,1] → [0,1] such that:
> 1. f is continuous and strictly increasing, with f(0) = 0 and f(1) = 1;
> 2. f is **piecewise linear**, with finitely many breakpoints;
> 3. the x-coordinates of the breakpoints are all **dyadic rationals** (numbers of the form k/2ⁿ, e.g. 1/2, 3/4, 5/8);
> 4. the **slope of every piece is an integer power of 2** (…, 1/4, 1/2, 1, 2, 4, …).
>
> The group operation is function composition.

You can check that composing two such functions gives another such function, and so does taking the inverse (reflecting the graph across the diagonal). So F really is a group. It is infinite: for example, you can squeeze [0,1] to the left by arbitrarily large amounts.

F was introduced by Richard Thompson in 1965 (originally for a problem in logic); McKenzie–Thompson 1973 gave an early published construction. The 1996 survey by Cannon–Floyd–Parry, *Introductory notes on Richard Thompson's groups*, is the standard introduction.

### 10.5.2 The two generators, written out

**x₀**: breakpoints (0,0) → (½,¼) → (¾,½) → (1,1).

| Interval | Maps to | Slope |
|---|---|---|
| [0, ½] | [0, ¼] | ½ |
| [½, ¾] | [¼, ½] | 1 |
| [¾, 1] | [½, 1] | 2 |

Intuitively: squeeze the left half to half its size, stretch the rightmost quarter to twice its size, and shift the middle. The overall effect is to "push points to the left".

The left half of the figure below is the graph of x₀: all three pieces lie below the dashed line y = x, so every interior point is pushed to the left. The right half recaps §10.3: "can you average fairly?" for ℤ versus F₂.

{{FIG_THOMPSON}}

**x₁**: do nothing on [0, ½]; on [½, 1], do a "scaled-down x₀". Breakpoints (0,0) → (½,½) → (¾,⅝) → (⅞,¾) → (1,1), with slopes 1, ½, 1, 2 in order.

Cannon–Floyd–Parry proved: **every element of F can be built from x₀, x₁ and their inverses**.

### 10.5.3 Composing by hand

Exact computation with fractions (checked by script):
- x₀(3/8): 3/8 lies in [0,½], where the slope is ½, so the result is 3/16.
- Breakpoints of x₀∘x₁ (first x₁, then x₀): (0,0) → (¾,⅜) → (⅞,½) → (1,1), slopes ½, 1, 4.
- Breakpoints of x₁∘x₀ (first x₀, then x₁): (0,0) → (½,¼) → (⅞,⅝) → (15/16,¾) → (1,1), slopes ½, 1, 2, 4.
- The two differ, so F is **not commutative**. A concrete example: x₁(x₀(7/8)) = 5/8, while x₀(x₁(7/8)) = 1/2.
- Breakpoints of x₀⁻¹: (0,0) → (¼,½) → (½,¾) → (1,1), slopes 2, 1, ½ (just swap the coordinates of each breakpoint of x₀).

**[Check 3]** Compute the breakpoints and slopes of x₀∘x₀. (Hint: first compute x₀(½) and x₀(¾), then plug them into x₀; you also need to find which point the first x₀ sends to ¾.)

### 10.5.4 Relations: why F is not a free group

F has relations. The most intuitive one comes from "**functions with disjoint supports commute**": if f only moves points in [0, ¾] and g only moves points in [¾, 1], it does not matter which one you do first.

Computed by script:
- u = x₀∘x₁⁻¹ has breakpoints (0,0) → (½,¼) → (¾,¾) → (1,1), and is the identity on [¾, 1].
- v = x₀⁻¹∘x₁∘x₀ has breakpoints (0,0) → (¾,¾) → (⅞,13/16) → (15/16,⅞) → (1,1), and is the identity on [0, ¾].
- So u and v commute: u∘v = v∘u. The script checked that u⁻¹v⁻¹uv = identity, and it holds; it also holds with v replaced by x₀⁻²∘x₁∘x₀².

These two are **all** the defining relations of F (Cannon–Floyd–Parry): F is **finitely presented** with 2 generators and 2 relations.

**Relations make the balls smaller.** Using x₀, x₁ and their inverses as generators, count the distinct elements of length ≤ n (the script deduplicates using exact breakpoints):

| n | Ball in F | Ball in F₂ |
|---|---|---|
| 1 | 5 | 5 |
| 4 | 161 | 161 |
| 5 | 475 | 485 |
| 6 | 1,381 | 1,457 |
| 8 | 11,237 | 13,121 |

The first 4 layers are identical; from layer 5 on, there are 10 fewer. The reason: the shortest relation, u⁻¹v⁻¹uv, has length 2+3+2+3 = 10, so length 5 is the first point at which two different words can represent the same element. F still grows exponentially (layer 8 still has 7,280 new elements), but exponential growth by itself does not decide amenability (some exponentially growing groups are amenable).

### 10.5.5 Why F is the litmus test of this field

Both standard tools **fail** on F:
- **"Contains F₂ ⟹ nonamenable" does not apply**: Brin–Squier proved in 1985 that F contains no non-abelian free subgroup (Inventiones 79).
- **"Built from abelian and finite groups ⟹ amenable" does not apply either**: F is not an "elementary amenable" group (Cannon–Floyd–Parry Theorem 4.10).

So F falls through the gap between the two standard methods of deciding the question. Add to this that its definition is simple and it has very nice properties (Brown–Geoghegan proved in 1984 that it has strong finiteness properties), and it became the single most watched group after the von Neumann–Day problem. Geoghegan conjectured in 1979 that F is **nonamenable** (recorded in Cannon–Floyd–Parry 1996, p. 227).

**Historical claims and retractions** (each row has a primary source [P]: the arXiv manuscripts and the authors' withdrawal notices):

| Date | Claim | Direction | Outcome |
|---|---|---|---|
| 2009-02 | Akhmedov, arXiv:0902.3849 | Nonamenable | Withdrawn by the author (v8, 2013-12, pointing to the new manuscript 1310.4395) |
| 2009-06 | Shavgulidze, arXiv:0906.0107 (a related paper was published in a journal) | Amenable | Moore 2011 (arXiv:1102.0747) lists specific errors and writes that those who studied it carefully agree: "the errors are serious and do not seem to be repairable"; he also notes that the Math Reviews review is inaccurate |
| 2011-12 | Beklaryan, arXiv:1112.1942 | Nonamenable | Withdrawn by the author in 2012-11, citing "a crucial error in Theorem B*" |
| 2012-09 | **Justin Moore**, arXiv:1209.2063 | Amenable | Withdrawn by the author on 2012-10-01: "Azer Akhmedov pointed out a serious error in Lemma 4.13. This error appears to be both serious and irreparable." |
| 2013/2021 | Akhmedov, arXiv:1310.4395v3 | Nonamenable | The OpenAI paper only says it "claims"; ⚠ I found no evidence that the community accepted it, and before 2026 the problem was generally listed as open |

There are also solid partial results. For example, Moore proved in 2013 that **if** F is amenable, its Følner sets must be astonishingly large ("tower-type" growth, *Groups Geom. Dyn.* 7).

Note Moore's retraction: he is one of the leading experts on this problem, and a fatal error was still found by peer checking within three weeks. This is the key background for understanding "why it matters that this result comes with Lean".

---

## 10.6 What OpenAI claims

### 10.6.1 The main result [P]

The paper is *Thompson's group F is nonamenable* (authored by OpenAI, family 248 of the openai/math release, 2026-09-23, **13 pages in total including the appendix**: the proof is on pages 1–7, pages 8–11 are appendices, pages 12–13 are references). The full abstract:

> "We prove that Thompson's group F is nonamenable. This confirms Geoghegan's conjecture and resolves the amenability problem for F."

Main theorem: **Theorem 1.1. Thompson's group F is not amenable.**

Page 1 of the paper honestly lists the failed historical claims above, and specifically notes that what Moore withdrew was a different paper, not his published Ramsey characterization.

### 10.6.2 The borrowed tool: a map that "pushes everything away"

First recall a classical theorem.

**Brouwer fixed-point theorem**: on a closed ball of **finite dimension** (a segment, a disk, a solid ball, …), every continuous map f has at least one fixed point, f(x) = x. Intuition: you cannot continuously crumple a disk and put it back inside the disk while moving every point.

**This theorem fails in infinite-dimensional space.** The infinite-dimensional example is ℓ²: all infinite sequences (x₁, x₂, x₃, …) whose squares have a finite sum, with length √(x₁² + x₂² + …). Kakutani's classic example:

```
f(x) = (1 − ‖x‖, x₁, x₂, x₃, ...)       (shift the sequence right by one slot, and put 1 − ‖x‖ in front)
```

It maps the unit ball into the unit ball, and it **has no fixed point** (a fixed point would need all coordinates to be equal and the sum of squares to be finite, so they would all be 0; but then the first slot is 1, a contradiction).

But this example is not strong enough: its "displacement" can be **arbitrarily small**. Computed by script: take x = (t, t, …, t) (N coordinates) with t = 1/(1+√N); then f(x) − x is t in the (N+1)-th coordinate only:

| N | Displacement ‖f(x) − x‖ |
|---|---|
| 1 | 0.500 |
| 100 | 0.091 |
| 10⁴ | 0.0099 |
| 10⁶ | 0.0010 |

So Kakutani's f has "**approximate** fixed points".

**Benyamini–Sternfeld (1983)** proved something stronger: on the unit ball of any infinite-dimensional normed space, there is a **Lipschitz** map f (it never stretches the distance between two points by more than a factor L) that **moves every point by at least δ > 0**. Such an f does not even have approximate fixed points. Appendix A of the OpenAI paper builds its own version with δ = ½ on L²([0,1]; ℝ²) (using a curve in infinite-dimensional space and a "tube" around it), and every Lipschitz estimate in the appendix is written out.

### 10.6.3 Skeleton of the proof (§10.2, about 5 pages)

The overall strategy in one sentence: **if F has finite sets A that barely leak, then averaging over A produces an approximate fixed point of the map f above.** This contradicts "every point is moved by at least δ".

Five steps, explained as intuitively as possible:

1. **Color the "dyadic partitions" of [0,1].** A partition cuts [0,1] into small cells of the form [k/2ʳ, (k+1)/2ʳ]. Fix in advance D pairwise non-adjacent "parent intervals" I₁ < … < I_D. For a partition T, take its part inside each parent interval and stretch it back to [0,1]; this gives a smaller partition T_{Iⱼ}. Define the "color" of T (a vector in the unit ball) recursively:

   ```
   p(T) = f( (p(T_{I₁}) + … + p(T_{I_D})) / D )      (if T cuts at every Iⱼ)
   p(T) = 0                                           (otherwise)
   ```

   Each restriction to a subinterval strictly reduces the number of cells, so the recursion always terminates.

2. **Let elements of F produce partitions.** An element g of F sends each cell of a uniform partition to a dyadic interval (Lemma 2.1 of the paper), so each g brings a family of colors: X_i(g) is the color of the i-th parent interval, and Y_ij(g) is the color of the j-th "grandchild interval" inside the i-th parent interval. The recursive definition directly gives **X_i = f(z_i)**, where z_i is the average of Y_i1, …, Y_iD. Let m = the average of all the X_i.

3. **F can move any pair of separated intervals to any other pair** (Lemma 2.2: refill the gaps with dyadic cells, and map them linearly one-to-one in order). So for any two separated intervals I < J there is an element h_{I,J} of F that moves them to the reference pair (I₁, I₂), and the colors move along exactly. Let S be the **finite** set made of these h_{I,J}. It is fixed in advance and does not depend on A.

4. **Average over a Følner set.** Let η = the largest leakage fraction |hA △ A|/|A| of A under S. When averaging over A, "replacing g by hg" barely changes the average, with error at most η. So: **for any two separated intervals, the average over A of the inner product of their colors is within η of the same constant α.** It is like saying: on a sample that is almost translation-invariant, all "pairs of separated positions" look equally correlated.

5. **A variance estimate, then a contradiction.** Expand ‖z_i − m‖². Among its inner-product terms, the vast majority are "separated interval pairs", whose averages are all about α, and positive and negative contributions cancel; only the "nested pairs" (a grandchild interval and its own parent), a fraction 1/D, are not controlled, but their inner products have absolute value at most 1. Working it out (equation 2.16 of the paper):

   ```
   average over A of ‖z_i − m‖² ≤ 4/D + 4(1 − 1/D)·η
   ```

   On the other hand, m is also the average of the f(z_i); using convexity and the Lipschitz property:

   ```
   δ² ≤ ‖m − f(m)‖² ≤ (L²/D)·Σ‖z_i − m‖²
   ```

   Combining: δ² ≤ L²·(4/D + 4(1−1/D)·η). Rearranging gives (Proposition 2.3):

   ```
   η ≥ (δ²/L² − 4/D) / (4(1 − 1/D))
   ```

   As long as D is chosen in advance to be larger than 4L²/δ², the right-hand side is a **positive number that does not depend on A**. In other words: **every finite set A in F leaks at least a fixed positive fraction under this fixed finite set S.** This directly violates the Følner criterion, so F is not amenable.

**A feel for the numbers** (computed by script; L is an assumed value, since the paper does not give a concrete number for the appendix map's L ⚠): with δ = ½ you need D > 16L². If L = 10, taking D = 3,200 gives a lower bound of about 3.1×10⁻⁴; taking D = 1,601 (just past the threshold) gives about 3.9×10⁻⁷. The fraction is tiny, but the proof only needs it to be positive and independent of A.

**Why this proof is surprising**: most earlier attempts looked for something inside F's own combinatorial structure (trees, graphs, Ramsey properties, height functions). Here the key "impossibility" comes from **infinite-dimensional geometry**. F only supplies the flexibility to "move any pair of intervals to any pair", plus the self-similar recursion of dyadic partitions.

### 10.6.4 Two corollaries (relying on companion papers)

Section 3 of the paper derives two corollaries: F has a representation that is "almost isometric but cannot be unitarized" (relying on another OpenAI paper, *Unitarizability implies amenability for discrete groups*); and percolation on the Cayley graph of F has p_c < p_u (relying on another OpenAI paper on percolation). The paper states explicitly that these two corollaries are **not used** in proving the main theorem. ⚠ We have not checked these two companion papers.

---

## 10.7 How far it has been verified

### 10.7.1 The Lean statement: F is defined from scratch, and you can read it line by line

Unlike the quasi-Riemann hypothesis in §4, this statement **does not rely on a ready-made F in Mathlib** (Mathlib has none). Instead, the challenge file `ComparatorChallenges/ThompsonNonamenability.lean` (89 lines, including imports) defines everything from scratch. The core:

```lean
def IsDyadic (x : ℝ) : Prop := ∃ (k : ℤ) (n : ℕ), x = (k : ℝ) / (2 : ℝ) ^ n

structure DyadicPLWitness (f : IntervalHomeomorph) where
  pieceCount : ℕ                       -- number of pieces
  knots : Fin (pieceCount + 1) → UnitInterval   -- list of breakpoints
  strictMono_knots : StrictMono knots  -- breakpoints in increasing order
  first : knots 0 = 0;  last : knots (last index) = 1
  dyadic : ∀ i, IsDyadic (knots i)     -- breakpoints are dyadic rationals
  exponent : Fin pieceCount → ℤ        -- one integer exponent per piece
  affine : ... (f x) = f(knot_i) + 2^(exponent i) * (x − knot_i)   -- each piece has slope a power of 2
  ...

def F := {f : IntervalHomeomorph // StrictMono f ∧ HasDyadicPLPieces f}

structure InvariantMean (G) [Group G] where
  toLinearMap : BoundedReal G →ₗ[ℝ] ℝ                       -- linear
  positive : ∀ f, (∀ g, 0 ≤ f g) → 0 ≤ toLinearMap f       -- positive
  normalized : toLinearMap 1 = 1                             -- normalized
  left_invariant : ∀ h f, toLinearMap (leftPull h f) = toLinearMap f   -- left-invariant

theorem thompson_F_nonamenable_composition :
    ∃ group : Group F, letI := group;
      (∀ (h g : F) (x : UnitInterval),
        (h * g).val.toHomeomorph x = h.val.toHomeomorph (g.val.toHomeomorph x)) ∧
      ¬ Nonempty (InvariantMean F)
```

(A few technical fields in the middle of the definitions are omitted; the full file is in the repository.)

Word-by-word translation:
- `IntervalHomeomorph`: a homeomorphism from [0,1] to itself (continuous, invertible, with a continuous inverse).
- `F`: the homeomorphisms that are "strictly increasing" and have "a witness of being dyadic piecewise linear". This is the definition from §10.5.1, with nothing missing.
- `BoundedReal G`: bounded real-valued functions on G (Mathlib's ℓ∞). `leftPull h f` is the function g ↦ f(hg).
- `InvariantMean`: the four conditions from §10.3.1: linear, positive, normalized, left-invariant.
- The theorem says: **there exists** a group structure on F whose multiplication **is function composition** (h*g acting on x equals h(g(x))), and under this group structure there **is no** invariant mean.

**Why "there exists a group structure" is not a loophole**: once the group multiplication is required to be composition, the identity and the inverses are uniquely determined. So this "exists" just means "F really is a group under composition", and leaves no room for cheating. The multiplication convention hg = h∘g also matches the paper.

**Our assessment: the statement is faithful to Theorem 1.1 of the paper** [P]. In addition, the Lean proof includes a file `StandardCharacterization.lean` proving that the definitions in the challenge file are equivalent to the "textbook" formulation, and `MeanToFolner.lean`, which **proves in Lean itself** the direction "invariant mean ⟹ Følner sets". So the Følner criterion that the paper cites is also machine-checked, not taken as an axiom.

### 10.7.2 The proof itself

- The proof lives under `lean/OAI/GroupTheory/Thompson/`: **68 files, 9,457 lines** (about 9,500; counted by script on snapshot fd4aeeb) [P]. Of these, 22 files (with names starting with `Analytic` or `Tube`) construct the map from Appendix A.
- We grepped it: this directory contains no `sorry`, no `axiom` declarations, and no `native_decide`.
- The Comparator configuration allows only Lean's three standard axioms (`propext`, `Quot.sound`, `Classical.choice`), and `enable_nanoda` is `false` (no second independent kernel check is turned on).
- **We did not compile it locally, and we did not run Comparator.** "Verified in Lean" is currently OpenAI's claim, plus our static inspection of the source.
- Unlike the quasi-Riemann hypothesis in §4: **as of 2026-10-08, we found no public record of any third party independently running this proof** (the quasi-Riemann hypothesis had an independent recheck by Dave Goldblatt using Comparator + nanoda). ⚠

### 10.7.3 Human experts [R]

- Gil Kalai (blog post, 2026-10-07) cited his 2009 post introducing Thompson's group and wrote: "The new manuscript announces that Thompson's group (F) is nonamenable." He uses "announces", a neutral wording.
- Group theorist Xiaolei Wu (compiled on proofsandprompts.com): "So Thompson's group F is non-amenable. OK, I had tried it many times using ChatGPT, but I guess I didn't have the newest model or enough tokens."
- **As of 2026-10-08, we found no public comments from central figures such as Geoghegan, Moore, or Akhmedov, and no named expert has publicly said they have read and verified the paper.** ⚠

### 10.7.4 Remaining risks

1. **Statement risk is very low**: the challenge file is under 90 lines and relies only on standard Mathlib objects (real numbers, homeomorphisms, ℓ∞, linear maps), and the definitions can be checked line by line against a textbook. This is the ideal form of the division of labor "humans check the statement, machines check the proof".
2. **Compilation and toolchain risk**: we did not compile it ourselves, and there is no second-kernel check. Such risks are usually small, but not zero.
3. **Correspondence between the paper and Lean**: Lean proves Theorem 1.1 itself, so even if the paper's write-up has flaws, the main conclusion is unaffected. The two corollaries (§10.6.4) are outside what Lean covers.
4. **An unusual piece of good news**: the core proof in this paper is only about 5 pages, and the tools it uses (Hilbert-space inner products, convexity, Lipschitz estimates, dyadic intervals) are all standard. Compared with the 199-page quasi-Riemann hypothesis paper (§4), it is one of the headline results that **human experts are most likely to read in full and independently confirm in the short term**. (This is speculation.)

---

## 10.8 What it means if true (and what it doesn't)

### 10.8.1 For mathematics

1. **A 47-year-old problem (1979→2026) has been solved, and the answer matches Geoghegan's conjecture**: F is not amenable.
2. **F becomes the most famous counterexample to the von Neumann–Day problem**: nonamenable, yet containing no F₂. But as §10.4.3 said, it is **not the first natural counterexample** (Monod 2013 and Lodha–Moore 2016 came first).
3. **A methodological surprise**: translate "averaging over a group" into "a fixed-point problem on the infinite-dimensional unit ball", then borrow a counterintuitive phenomenon from functional analysis, like Benyamini–Sternfeld, to reach a contradiction. Whether this route works for other groups (for example other groups of piecewise linear/piecewise projective homeomorphisms) is a natural open question. (Speculation.)
4. **What it does not mean**: the paper gives no explicit constant for a specific generating set (the Lean document `docs/248.md` says verbatim: "No explicit boundary constant or prescribed generating set is given."); nor does it answer F's other famous questions.

### 10.8.2 For AI and for "verification" itself

This is the best case for "why Lean matters", for concrete reasons:
- The human history of this problem is a string of "proof announced → error found → withdrawn", in both directions, and even the leading expert withdrew once (the table in §10.5.5). Going by past experience, the community might take years to reach consensus on a new 13-page claim.
- With Lean, the object of trust shifts from "the author" to "**the kernel + an 89-line statement (imports included) that can be audited line by line**".
- At the same time, it reminds us what Lean cannot do: it cannot judge the **significance** of the result, it cannot tell whether the method generalizes, and it cannot replace human understanding of "why it is true".

For you (an AI safety researcher), this case has one more layer: it is a sample of "AI gives a short proof of a problem humans failed at for a long time, and humans can recheck it in a short time". Together with "AI gives a 480,000-line proof that humans can barely recheck" (the quasi-Riemann hypothesis in §4), it marks the two ends of a **scalable-oversight** spectrum. (Speculation, but worth writing down.)

---

## 10.9 Self-test

Try to answer these after reading. If you can't, go back and reread the corresponding section.

1. Explain in one sentence what "amenable" means. (§10.3.1)
2. Why are balls in F₂ not good Følner sets? Why is that not enough to prove F₂ is nonamenable? (§10.3.2–10.3.3)
3. Why does W(a) ∪ a·W(a⁻¹) = F₂ imply that F₂ has no fair mean? (§10.3.3)
4. The Banach–Tarski paradox holds in three dimensions but not in two. What did von Neumann think was the root cause? (§10.4.2)
5. Why does F fall "through the gap between the two standard methods of deciding the question"? (§10.5.5)
6. Neither the Kakutani map nor the Benyamini–Sternfeld map has a fixed point. What is the difference? Why does OpenAI's proof need the latter? (§10.6.2)
7. Why is "there exists a group structure" in the Lean statement not a loophole? (§10.7.1)

---

## Appendix: answers to the checks

- **Check 1**: **aa, ab, aB, AA, Ab, AB, bb, ba, bA, BB, Ba, BA**. aA, Aa, bB, Bb don't count, because they cancel to the empty word. Each first letter has 3 choices after it, 4×3 = 12 (checked by script).
- **Check 2**: hA = {−n+1, …, n+1}. Compared with A, it gains n+1 and loses −n, so hA △ A = {−n, n+1}, 2 elements, fraction 2/(2n+1). For n=10 this is 2/21 ≈ 0.0952, matching the table.
- **Check 3**: x₀(½) = ¼, x₀(¾) = ½. Apply x₀ again: x₀(¼) = ⅛, x₀(½) = ¼. You also need the point that the first x₀ sends to ¾: on [¾,1], x₀ is y = ½ + 2(x − ¾); setting y = ¾ gives x = ⅞. So the breakpoints of x₀∘x₀ are **(0,0) → (½,⅛) → (¾,¼) → (⅞,½) → (1,1)**, with slopes **¼, ½, 2, 4** (checked by script). The slopes are still all powers of 2 and the breakpoints are still dyadic rationals, so it is still in F.

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| Group | A set of operations that compose, have an identity, and can each be undone |
| Generators | A few elements from which the whole group can be built |
| Relations | Equations between generators that make different spellings represent the same element |
| Free group F₂ | The group with two generators and no relations at all |
| Cayley graph | The graph with group elements as points and edges given by generators; for F₂ it is a 4-way tree |
| Invariant mean | A rule for scoring bounded functions: linear, positive, normalized, invariant under left shifts |
| Amenable | An invariant mean exists; equivalent to having Følner sets |
| Følner set | A finite set in which only a tiny fraction of elements change after a shift |
| Paradoxical decomposition | Cutting a group into a few pieces and shifting them to form two copies of itself; equivalent to nonamenability (Tarski) |
| von Neumann–Day problem | Must every nonamenable group contain F₂? Answer: no |
| Thompson's group F | The group, under composition, of piecewise linear increasing homeomorphisms of [0,1] with dyadic breakpoints and slopes that are powers of 2 |
| Fixed point | A point with f(x) = x |
| Lipschitz map | A map that stretches the distance between two points by at most a factor L |
| Benyamini–Sternfeld | On the infinite-dimensional unit ball there is a Lipschitz map that moves every point by at least δ |

## Appendix: Further reading

- **The original paper** (13 pages; Section 2 is fully within your reach): https://github.com/openai/math/blob/main/preprints/Thompsons-group-F-is-nonamenable-September-23-2026/paper.pdf
- **Lean statement**: https://github.com/openai/math/blob/main/lean/ComparatorChallenges/ThompsonNonamenability.lean ; scope notes: https://github.com/openai/math/blob/main/lean/docs/248.md
- **Cannon, Floyd, Parry**, *Introductory notes on Richard Thompson's groups*, L'Enseignement Math. 42 (1996) 215–256: the standard introduction to F; the generators and relations in §10.5 all come from here.
- **Terence Tao**, *The Banach–Tarski paradox* (lecture notes, UCLA): full derivations of the paradoxical decomposition and amenability from §10.3.3 and 4. Search for "Tao Banach-Tarski paradox notes".
- **Juschenko**, *Amenability of discrete groups by examples* (AMS Mathematical Surveys and Monographs, 2022): a modern textbook on amenability, with a chapter on F. ⚠ Chapter number not checked.
- Primary historical sources: Moore's note on Shavgulidze https://arxiv.org/abs/1102.0747 ; Moore's withdrawn manuscript https://arxiv.org/abs/1209.2063 ; Akhmedov https://arxiv.org/abs/0902.3849 and https://arxiv.org/abs/1310.4395 ; Beklaryan https://arxiv.org/abs/1112.1942
- Natural counterexamples to von Neumann–Day: Monod PNAS 2013 (*Groups of piecewise projective homeomorphisms*); Lodha–Moore https://arxiv.org/abs/1308.4250
- Gil Kalai's 2009 blog post introducing F: https://gilkalai.wordpress.com/2009/05/01/the-thompson-group/ ; the 2026 update: https://gilkalai.wordpress.com/2026/10/07/updates-sharing-ai-progress-on-mathematics-amazing-and-my-lecture-plans/
- Compilation of reactions: https://proofsandprompts.com/2026/10/08/100-reactions-to-100-solutions/
