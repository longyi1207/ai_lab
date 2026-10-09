# The Mézard–Parisi formula (diluted spin glasses): from magnets to the energy landscapes of neural networks

> Prerequisites: you can work with exponentials and logarithms (e^x, ln x), you know what an "expectation" (average) is, and you know the summation sign Σ. The physics concepts (energy, temperature, free energy) are all explained from scratch. The Hopfield network you met in neuroscience comes back in §13.10.
> Every number in the text was computed by script or has a source; [P] marks primary material read (paper, repo, Lean source), and ⚠ marks something unverified or conflicting. **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter.
> Estimated reading time: 70–100 minutes. You can split it into three sittings: §13.1–13.4 (spins, free energy, the replica method), §13.5–13.7 (sparse graphs, the cavity method, the problem itself), §13.8–13.10 (OpenAI's result, how well it is verified, and what it means).

---

## 13.0 The bottom line: the one thing this chapter explains

A magnet contains a huge number of tiny compass needles ("spins"), each of which can only point up or down. If the interactions between the needles are **random**, with some pairs wanting to align and others wanting to point opposite ways, you get a situation where "no arrangement can satisfy everyone." Such a system is called a **spin glass**. The central quantity physicists care about is the **free energy**: once you know it, you can derive almost every macroscopic property of the system at every temperature.

Between 1979 and 2001, physicists (mainly Parisi and Mézard) wrote down formulas for the free energy using a set of **mathematically non-rigorous** methods (the replica method, the cavity method). Mathematicians spent decades turning parts of this into theorems. The chain of reasoning in this chapter is:

> Free energy = the minimum of a "hierarchical trial functional" ⟸ the upper bound was proved long ago (the interpolation method, 2003–04) ⟸ the lower bound (equality) requires controlling "the spin patterns seen by several replicas at once" ⟸ in the dense model (SK), pairwise overlaps are enough; in sparse models they are not, and this step was stuck for over twenty years.

OpenAI claims (family 221, 2026-09-23, a 36-page paper + about 56,000 lines of Lean) [P] to have filled in the lower bound for **one class of sparse models** (Poisson-diluted, even-arity interactions, satisfying the Panchenko–Talagrand condition), thereby proving that equality holds, and has given a Lean formalization.

Note: the name "Mézard–Parisi" refers to at least two different things in the literature. What OpenAI proved is the **hierarchical cavity formula for diluted spin glasses** (Mézard–Parisi 2001), **not** the famous **random assignment problem ζ(2) = π²/6** (Mézard–Parisi 1985–87, proved by Aldous in 2001). §13.6 covers the latter, because it is the best example for understanding "why physicists' non-rigorous methods are trustworthy."

After reading this chapter, you should be able to explain in your own words:
- what free energy is, why "averaging log Z" is hard, and what trick the replica method uses to get around it;
- the difference between dense (SK) and sparse (Viana–Bray / Bethe lattice) models, and why the cavity method is exact on trees;
- what exactly the theorem OpenAI proved covers and does not cover (3-SAT, the fixed-degree Bethe lattice, and Hopfield are all outside it);
- which of its connections to ML / neuroscience are real and which are only analogies.

---

## 13.1 Magnets and spins: the Ising model

### 13.1.1 Spins

Think of a magnet as a row of tiny compass needles, each with only two states: up is written σ = +1, down is written σ = −1. This variable that can only take ±1 is called a **spin**. One assignment of values to N spins (for example +1, −1, −1, +1) is called a **configuration**, and there are 2^N configurations in total.

You have seen the same thing in neuroscience: the binary "firing / not firing" model of a neuron, which is exactly how a Hopfield network encodes it.

### 13.1.2 Energy

Between two spins i, j there is a **coupling strength** Jᵢⱼ. The energy of the system (physicists call it the Hamiltonian) is:

```
H(σ) = − Σ_{connected i,j} Jᵢⱼ · σᵢ · σⱼ   (sometimes with an extra term − Σ hᵢσᵢ, where h is an external magnetic field)
```

Look at a single pair of spins:
- Jᵢⱼ > 0 (**ferromagnetic**): when σᵢ = σⱼ, the product σᵢσⱼ = +1 and the energy contribution is −J, which is low; so they "want to align."
- Jᵢⱼ < 0 (**antiferromagnetic**): they "want to point opposite ways."

Physical systems tend toward low-energy states. The configuration with the lowest energy is called the **ground state**.

This energy function connects directly to your neuroscience background: the energy of a Hopfield network (1982), E = −½ Σ Wᵢⱼσᵢσⱼ, has exactly this form, i.e. it is a spin-glass-style Hamiltonian. Stored memories are local minima of this energy; starting from a partial cue, the network updates so that the energy never goes up, and it settles into a nearby minimum (§13.10.3 comes back to this in detail).

### 13.1.3 The Boltzmann distribution: where temperature comes in

At temperature T > 0, the system doesn't stick to the ground state. Instead, it appears in every configuration with some probability, given by the **Boltzmann distribution**:

```
P(σ) = e^(−β·H(σ)) / Z,     Z = Σ_all configurations e^(−β·H(σ)),     β = 1/T
```

β is called the **inverse temperature**. Z is the normalizing constant obtained by adding up all the weights, called the **partition function**. You see this formula in ML every day: it is just **softmax**, with the "logit" replaced by −β·energy. β is the softmax's inverse-temperature parameter.

**Smallest example**: two spins, J = 1 (ferromagnetic), H = −σ₁σ₂. Four configurations: (+,+) and (−,−) have energy −1; (+,−) and (−,+) have energy +1. Computed by script:

| β | Z | P(a given aligned configuration) | P(a given anti-aligned configuration) | P(aligned, total) |
|---|---|---|---|---|
| 0 (infinite temperature) | 4.000 | 0.250 | 0.250 | 0.500 |
| 0.5 | 4.511 | 0.366 | 0.135 | 0.731 |
| 1 | 6.172 | 0.440 | 0.060 | 0.881 |
| 2 | 15.05 | 0.491 | 0.009 | 0.982 |
| 5 | 296.8 | 0.500 | 0.000 | 1.000 |

At high temperature all four configurations are equally likely (thermal motion smooths everything out); at low temperature essentially only the ground states remain. Temperature is the knob that sets the weighting between "energy" and "disorder."

**[Check 1]** By hand, compute P(+,+) = e / (2e + 2e⁻¹) at β = 1 and verify that it is about 0.440.

---

## 13.2 Frustration and spin glasses

### 13.2.1 The frustrated triangle

Put three spins on a triangle, with all three edges antiferromagnetic (J = −1): every pair wants to point opposite ways. The energy is H = σ₁σ₂ + σ₂σ₃ + σ₁σ₃.

The problem: three numbers that can only be ±1 cannot all be pairwise different. So **no matter how you arrange them, at least one edge is unhappy**. This is called **frustration**.

The script enumerates all 8 configurations:

| | Ground-state energy | Number of ground states | Zero-temperature entropy ln(number of ground states) |
|---|---|---|---|
| Ferromagnetic triangle (J = +1) | −3 (all three edges satisfied) | 2 (all up, all down) | ln 2 ≈ 0.693 |
| Antiferromagnetic triangle (J = −1) | −1 (only two edges can be satisfied) | **6** | ln 6 ≈ 1.792 |

The partition function of the antiferromagnetic triangle is Z(β) = 2e^(−3β) + 6e^(β) (at β = 1 the script gets 16.409, matching the formula). Frustration has two consequences: (1) the ground-state energy is "raised" (−1 instead of −3); (2) the ground state is **highly degenerate** (many configurations tie for the lowest energy).

**[Check 2]** List the 8 configurations of the antiferromagnetic triangle with their energies, and confirm that exactly 2 have energy +3 and 6 have energy −1.

### 13.2.2 Spin glasses: random couplings

If each edge's Jᵢⱼ has a **random** sign (or is a random Gaussian number), frustration is everywhere: pick three random ±1 signs, and the probability that the triangle is frustrated (the product of the three signs is negative) is exactly 1/2 (the script enumerates the 8 sign combinations). Such a system is called a **spin glass**. The name comes from real materials (for example copper with a small amount of manganese mixed in): at low temperature their spins "freeze" in disordered directions, "orderly disordered" like glass.

There is a key distinction here that also shows up in ML: the couplings J are "**frozen randomness**" (quenched disorder), drawn once and then fixed; the spins σ are the variables that undergo "thermal motion" under the Boltzmann distribution. Analogy: J is a training set, and σ are the parameters on that training set.

### 13.2.3 A rugged energy landscape

"Frustration everywhere" produces a **rugged energy landscape**: many local minima, separated from each other by energy barriers. A script experiment: call a configuration where "flipping any single spin cannot lower the energy" a **single-flip stable configuration** (a local minimum), and count them:

| System | N | Number of single-flip stable configurations |
|---|---|---|
| Fully connected ferromagnet (all J = 1/N) | 12 | 2 (all up, all down) |
| SK spin glass (random Gaussian J) | 12 | 13.1 on average (20 samples, min 6, max 24) |
| SK spin glass | 16 | 23.2 on average (5 samples) |

The literature result is that the number of single-flip stable configurations in SK grows **exponentially** with N, roughly as e^(0.199·N) (Tanaka–Edwards 1980 / Bray–Moore 1980 ⚠ constant quoted from memory of the literature, not rechecked against the original). Plugging in N = 12 and 16 gives 10.9 and 24.2, consistent in magnitude with the computed values in the table above.

---

## 13.3 Free energy: why physicists want it

### 13.3.1 Definition

```
Free energy   F = −(1/β) · ln Z
"Pressure"    per spin, (1/N) · ln Z  (this is the quantity the OpenAI paper uses, called pressure)
```

Pressure = −βF/N: the two differ only by a factor of −β/N (−β from the sign and temperature, 1/N from "per spin"), so they are essentially the same thing.

### 13.3.2 Why they want it

Because ln Z is a "generating function": differentiating it gives almost every macroscopic quantity. For example, the mean energy ⟨E⟩ = −∂(ln Z)/∂β, and the entropy S = β(⟨E⟩ − F). Computed by script on the frustrated triangle: at β = 5, the entropy of the antiferromagnetic triangle is S = 1.7918, almost exactly ln 6 = 1.7918 (6 equally likely ground states); the entropy of the ferromagnetic triangle is 0.6931 = ln 2.

The ML counterpart: ln Z is just log-sum-exp; the ELBO is a lower bound on ln Z.

### 13.3.3 The real difficulty: you have to average ln Z

For a spin glass, Z itself is random (it depends on which J you drew). What is physically meaningful is the free energy of a **typical** sample, that is, **E[ln Z]** (the "quenched average").

**ln E[Z]** (the "annealed average") is much easier to compute: E[Z] is the expectation of Σ e^(...), so you can move the expectation inside the sum, and each term is a Gaussian integral. But the two are not equal. Since ln is concave, Jensen's inequality gives E[ln Z] ≤ ln E[Z].

Computed by script (SK model, N = 10, β = 2, 2000 random samples, exact enumeration of the 1024 configurations for each sample):

| Quantity | Value per spin |
|---|---|
| Quenched (1/N)·E[ln Z] | **1.387** |
| Annealed (1/N)·ln E[Z] (exact formula ln 2 + β²(N−1)/(4N)) | 1.593 |

The gap is large. The reason is that E[Z] is dominated by a very few "unusually lucky" samples and doesn't represent the typical case. For the SK model, as N → ∞ the two are equal for β ≤ 1 and separate for β > 1 (low temperature); this is exactly the spin glass phase transition (an established result).

**All the difficulty in this chapter comes from "you have to compute E[ln Z], and ln cannot be swapped with the expectation."**

---

## 13.4 The replica method and replica symmetry breaking: a tradition that is "not rigorous, but right"

### 13.4.1 The replica trick

Physicists use an identity:

```
ln Z = lim_{n→0} (Z^n − 1) / n
```

Check (script): ln 5 = 1.6094; for n = 1, 0.1, 0.01, 0.001, (5^n − 1)/n is 4.000, 1.746, 1.622, 1.611 in turn, which does approach ln 5.

The benefit: when n is a **positive integer**, Z^n = Z·Z·…·Z is the partition function of **n independent copies** ("replicas"), and E[Z^n] can be computed (again, you can move the expectation inside the sum). So the strategy is:

1. Compute E[Z^n] for integer n;
2. "Pretend" the resulting formula also holds for real n;
3. Let n → 0.

Step 2 has no mathematical justification at all (the values at the integers do not uniquely determine a function on the reals), and step 3 also requires swapping the two limits n → 0 and N → ∞. This is why it is called "non-rigorous."

### 13.4.2 Replica symmetry and its failure

When computing E[Z^n], an n × n matrix Q_ab appears, called the **overlap**:

```
Q_ab = (1/N) Σᵢ σᵢ^a · σᵢ^b    (how similar the configurations of replica a and replica b are, a value between −1 and 1)
```

The most natural guess is that all replicas are "equal," so all off-diagonal Q_ab are the same. This is called **replica symmetric** (RS). Sherrington and Kirkpatrick did exactly this for the SK model in 1975, and the result was clearly wrong at low temperature: the zero-temperature entropy came out as **−1/(2π) ≈ −0.159**, while the entropy of an Ising system cannot be negative (there is at least 1 configuration, and ln 1 = 0); the RS prediction for the ground-state energy, −√(2/π) ≈ −0.798, also disagrees with numerical simulations.

### 13.4.3 Parisi's replica symmetry breaking

In 1979 Parisi proposed that the replicas are not equal but form a **hierarchy**. Split the n replicas into large groups, split each large group into smaller groups, those into even smaller groups… Overlaps within the same small group are large; overlaps between different large groups are small. Splitting into r levels is called **r-step replica symmetry breaking** (r-RSB), and r → ∞ is called full RSB.

The physical interpretation (built up gradually starting with Mézard–Parisi–Sourlas–Toulouse–Virasoro 1984): at low temperature the Gibbs distribution splits into many "pure states" (roughly corresponding to the deep valleys of the energy landscape), and these valleys form a **tree**: the more "closely related" two valleys are, the deeper their common ancestor in the tree. This kind of distance structure is called **ultrametric**: among any three points, the two largest distances are equal, just like the distances between species on a biological taxonomy tree.

The parameters 0 < m₁ < m₂ < … < m_r < 1 that appear in the Parisi formula are the "branching strengths" at each level of the tree. The `Exponents m` in the OpenAI paper and Lean code later on refer to exactly these.

The figure below puts the two ideas side by side. On the left is the frustrated triangle from §13.2.1: all three bonds want opposite spins, none of the 8 configurations satisfies all three (the dashed bond always fails), and the ground state is 6-fold degenerate. On the right is Parisi's hierarchical tree: pure states first split into large groups, and the large groups split again; the deeper the common ancestor of two pure states (the "closer relatives" they are), the larger their overlap. The note at the bottom right, "diluted: need all multi-replica overlaps," is the difficulty that §13.7.3 explains.

{{FIG_SPIN}}

### 13.4.4 The physics was right; the math took 27 years

| Year | Event | Nature |
|---|---|---|
| 1975 | Sherrington–Kirkpatrick propose the SK model (every pair of spins is coupled) | Definition |
| 1979–80 | Parisi writes down the SK free energy formula (RSB) | Physical derivation, non-rigorous |
| 2003 | Guerra uses the "interpolation method" to prove the Parisi formula is an **upper bound** on the free energy | Theorem |
| 2006 | Talagrand proves **equality** (Annals of Math. 163) | Theorem |
| 2013 | Panchenko proves ultrametricity (Annals of Math. 177) | Theorem |
| 2021 | Parisi wins the Nobel Prize in Physics (shared with Manabe and Hasselmann) | — |
| 2024 | Talagrand wins the Abel Prize (spin glass work is one of the main reasons) | — |

The numerical value of the SK ground-state energy: the Parisi formula gives **−0.7632** per spin (high-precision value −0.763166…, Crisanti–Rizzo 2002 ⚠ as cited in the literature). The script enumerates small systems exactly (H = −Σ_{i<j} Jᵢⱼσᵢσⱼ, Jᵢⱼ ~ N(0, 1/N)):

| N | Number of samples | Ground-state energy per spin |
|---|---|---|
| 8 | 400 | −0.571 ± 0.006 |
| 12 | 200 | −0.609 ± 0.006 |
| 16 | 40 | −0.655 ± 0.013 |
| 20 | 8 | −0.683 ± 0.022 |

As N grows, the value moves toward −0.763, but slowly (finite-size corrections decay roughly like N^(−2/3), ⚠ a result from the literature, not verified here by fitting). The point of this table: **brute-force enumeration of small systems cannot give you the limiting value; you need a formula.**

**This is the most important background in this chapter**: in the field of spin glasses, physicists' non-rigorous methods have repeatedly given the right answers, and mathematicians have then spent anywhere from ten to several tens of years catching up. This OpenAI result is one link in that "catching up" chain.

---

## 13.5 Sparse graphs and the cavity method

### 13.5.1 Dense vs. sparse

In the SK model, **every pair** of spins is coupled, each spin has N − 1 neighbors, and each coupling is very weak (of order 1/√N). This is called a **dense** (mean-field) model.

Real physics and many computational problems are **sparse**: each spin interacts with only **finitely many** other spins, so even when N is large, each spin has only a constant number of neighbors, like 3 or 5. Two standard random constructions:
- **Poisson dilution** (Viana–Bray 1985): scatter αN edges at random (in OpenAI's theorem the number of edges is itself drawn as Poisson(αN)); each spin's degree is approximately Poisson-distributed.
- **Bethe lattice / random regular graph**: every spin has the same **fixed** degree. The original Mézard–Parisi 2001 paper uses this one.

### 13.5.2 Sparse random graphs "look locally like trees"

The key property: sparse random graphs have **very few short cycles**. Computed by script (Erdős–Rényi graphs with average degree 3):

| N | Average number of triangles | Average degree | Fraction of isolated vertices |
|---|---|---|---|
| 100 | 4.8 | 2.82 | 0.058 |
| 1,000 | 3.8 | 2.99 | 0.053 |
| 10,000 | 4.1 | 3.01 | 0.049 |
| 100,000 | 3.4 | 3.00 | 0.049 |

Theoretical values: the number of triangles tends to c³/6 = 4.5 (**it does not grow with N**), and the fraction of isolated vertices tends to e⁻³ ≈ 0.0498. In other words, the bigger the graph, the closer to zero the fraction of vertices with a short cycle nearby: looking a few steps out from any vertex, what you see is almost always a tree.

### 13.5.3 The cavity method: exact on trees

The idea of the **cavity method**: remove one spin and see how the rest of the system "treats" the empty slot.

On a **tree** this is completely exact. After removing spin i, its neighbors belong to separate subtrees that are not connected to each other, so they are independent. Each neighbor j sends i a "message" (an effective field u_{j→i}), and i adds up the messages it receives to get its own state. The update rule for messages is:

```
u_{j→i} = (1/β) · artanh( tanh(β·Jᵢⱼ) · tanh(β·h_j^cavity) )
```

where h_j^cavity is "the total field felt by j after i is removed." This is **belief propagation (BP)** from ML: the same algorithm, invented separately by physicists and by Pearl.

**Smallest example** (**[Check 3]** has you compute it by hand): two spins, J = 1, an external field h = 0.5 on spin 1, β = 1. The magnetization (mean value) of spin 2 is exactly tanh(1)·tanh(0.5) = 0.35195. Exact enumeration by script gives 0.35195, which matches.

The script also does a tree with 5 vertices and random couplings and external fields: comparing the 5 magnetizations computed by exact enumeration of the 32 configurations against the BP result, the largest difference is **4.9 × 10⁻¹⁶** (machine precision). Add two more edges to create cycles, and the largest difference becomes **0.16**. **Cavity / BP is exact on trees and inexact with short cycles.** Sparse random graphs "look locally like trees," so there is reason to expect the cavity method to become exact as N → ∞, but this needs proof.

### 13.5.4 The complication: with many pure states, messages become "distributions of distributions"

At high temperature, BP has a unique fixed point, with one message per edge; averaging over random graphs, the order parameter is "**a distribution of messages**" ζ ∈ P(ℝ). This is the RS level (r = 0).

In the low-temperature spin glass phase there are many pure states (the tree from §13.4.3), and the message on an edge differs from one pure state to another. So you have to describe "how the message is distributed across pure states," then average over the randomness of the graph, and the order parameter becomes "**a distribution of distributions of messages**"; with r levels of RSB, there are r + 1 levels of nesting:

```
Level 0: ℝ (one message)
Level 1: P(ℝ) (a distribution of messages)
Level 2: P(P(ℝ)) (a distribution of distributions of messages)
……
```

The `Hierarchy` in the Lean statement is exactly this definition: `H₀ = ℝ`, `H_{r+1} = P(H_r)`. This is what "hierarchical" means in "**hierarchical cavity formula**."

Mézard–Parisi 2001 (*The Bethe lattice spin glass revisited*, EPJ B 20:217) wrote down this framework and an explicit 1RSB functional for the fixed-degree Bethe lattice; the general form for any finite number of levels r, and the proof that it is an upper bound on the free energy, come from Panchenko–Talagrand 2004 (see §13.7).

---

## 13.6 The other "Mézard–Parisi": random assignment and ζ(2)

This section is not OpenAI's result, but it is the most beautiful example of "physicists' non-rigorous method → mathematical theorem," and it is the same number as ζ(2) = π²/6 in the quasi-Riemann hypothesis (§4).

### 13.6.1 The problem

n workers, n jobs. The cost Cᵢⱼ for worker i to do job j is an independent random number, exponentially distributed with mean 1. Find a one-to-one assignment that minimizes the total cost. Question: what is the expected minimum total cost?

Intuition might say it grows with n (after all, you are adding n numbers), but the optimal assignment picks very small numbers from each row, and as n grows, the "very small numbers" get smaller and smaller.

### 13.6.2 Prediction and proof

- **Mézard–Parisi 1985/1987**: using the replica method, they predicted that as n → ∞ the expected minimum cost → **ζ(2) = π²/6 ≈ 1.6449**.
- **Aldous 2001** (*The ζ(2) limit in the random assignment problem*, Random Structures & Algorithms 18): a rigorous proof, using "local weak convergence" (the same idea as the cavity method's "locally tree-like").
- **Parisi 1998** went further and conjectured an **exact** formula for finite n: E[minimum cost] = 1 + 1/4 + 1/9 + … + 1/n². This was proved independently by Linusson–Wästlund in 2004 and Nair–Prabhakar–Sharma in 2005.

Computed by script (optimal assignment via the Hungarian algorithm, scipy `linear_sum_assignment`):

| n | Number of trials | Simulated mean minimum cost | Parisi formula Σ_{k≤n} 1/k² |
|---|---|---|---|
| 1 | 200,000 | 1.0000 ± 0.0022 | 1.0000 |
| 2 | 200,000 | 1.2498 ± 0.0019 | 1.2500 |
| 3 | 100,000 | 1.3628 ± 0.0023 | 1.3611 |
| 5 | 50,000 | 1.4614 ± 0.0026 | 1.4636 |
| 10 | 20,000 | 1.5500 ± 0.0029 | 1.5498 |
| 30 | 4,000 | 1.6093 ± 0.0038 | 1.6122 |
| 100 | 1,000 | 1.6373 ± 0.0042 | 1.6350 |
| 300 | 200 | 1.6435 ± 0.0055 | 1.6416 |
| 1000 | 40 | 1.6381 ± 0.0066 | 1.6439 |

Every row agrees within one or two standard errors, and for large n both approach π²/6 = 1.6449. For comparison, a greedy method where "each worker in turn picks the cheapest remaining job" has an average cost of **5.14** at n = 100, more than three times the optimum.

**[Check 4]** For n = 2, with four costs a, b, c, d (matrix [[a,b],[c,d]]), the minimum cost is min(a+d, b+c). Prove that its expectation is 5/4. (Hint: the sum X of two independent Exp(1) variables satisfies P(X > t) = (1+t)e^(−t); for a non-negative random variable, E[Y] = ∫₀^∞ P(Y > t) dt. A direct script simulation with 2 million trials gives 1.24989.)

**Lesson**: the number the replica method gave (π²/6) was right, and was later proved rigorously. Success stories like this, piling up, are the reason mathematicians are willing to spend decades proving the Parisi / Mézard–Parisi formulas.

---

## 13.7 What exactly is the problem: the upper bound is known, equality is open

### 13.7.1 What needs to be proved

For the diluted model, define the per-spin pressure F_N = (1/N)·E[ln Z_N]. The hierarchical cavity functional B_r(ζ, m) gives a number for any "trial law" ζ (the nested distributions from §13.5.4) and any branching parameters 0 < m₁ < … < m_r < 1. The conjecture is:

```
lim_{N→∞} F_N  =  inf_{r ≥ 0}  inf_{ζ, m}  B_r(ζ, m)
```

The right-hand side takes the infimum over **all finite numbers of levels and all trial laws**.

### 13.7.2 Half of it is already proved: the upper bound (2003–04)

- **Franz–Leone 2003** (J. Stat. Phys. 111): carried Guerra's interpolation method over to diluted models and proved the RS and 1RSB upper bounds for even-arity models.
- **Panchenko–Talagrand 2004** (PTRF 130): proved the upper bound for any finite number of levels r: for every r, ζ, m, lim sup F_N ≤ B_r(ζ, m). After Theorem 4 they **explicitly state equality as a conjecture**. The OpenAI paper says this is the conjecture it resolves (within the same model class).

The intuition for the interpolation method: build a path that continuously deforms "the real model" into "a trial model made of independent messages," and prove that the derivative of the pressure along the path has a fixed sign. Determining the sign uses a positivity condition; this is where E[(−b)ⁿ] ≥ 0 in the Panchenko–Talagrand condition below comes from, and also why only **even-arity** interactions can be handled.

### 13.7.3 Why the lower bound is hard

In SK, when Talagrand proved the lower bound, he only needed to control the **pairwise overlaps** Q_ab. In a sparse model, a newly inserted spin connects simultaneously to p − 1 old spins, and you need to know what pattern several replicas see **at the same time** at those positions. This depends on all the **multioverlaps**:

```
R_S = (1/N) Σᵢ Π_{a∈S} σᵢ^a      (S is a set of replicas)
```

The ultrametric structure of pairwise overlaps does not determine all the multioverlaps (in the words of §1 of the paper: "pair overlaps alone do not determine all these patterns").

Existing partial progress (listed in the paper's introduction): Panchenko 2013 gave a different exact variational formula using "spin distributions," but not in hierarchical cavity form; Panchenko 2016 (arXiv:1406.4702) proved for "modified models" that finite-RSB Gibbs measures have the Mézard–Parisi structure, but was missing the step "a general state can be approximated by finite RSB"; Coja-Oghlan–Perkins 2019 gave another variational formula for random regular factor graphs under a positivity condition; Concetti 2025 (arXiv:2508.17049) gave a full-RSB upper bound for random regular graphs, with equality still a conjecture.

Neighboring known results (background):
- **Ferromagnetic** sparse Ising models (no frustration): Dembo–Montanari 2010 proved the Bethe formula.
- **Random k-SAT** (each clause is a k-ary interaction): Ding–Sly–Sun (STOC 2015, Annals 2022) proved the satisfiability threshold for **sufficiently large k**, which is exactly what the 1RSB formula predicts.

---

## 13.8 What OpenAI claims

### 13.8.1 The main result

Abstract of the paper *The Mézard–Parisi formula for diluted spin glasses* (OpenAI, 2026-09-23, 36 pages, family 221) [P]:

> "We prove the Mézard–Parisi hierarchical cavity formula for diluted even-arity Ising models in the Panchenko–Talagrand class. This resolves the variational equality conjecture for that class: the limiting pressure equals the infimum of the trial functional over all finite hierarchy depths and trial laws. Only first moments of the interaction and external field are required."

Main theorem (Theorem 2.1): under assumptions (2.1)–(2.4), the thermodynamic limit exists, and lim F_N = inf_r Φ_r.

The key trick in one sentence: shift every branching depth down one level, then average over depths, which gives control of all multi-replica overlaps (step 3 in §13.8.4).

### 13.8.2 What the model is (plain-language version)

- Fix an **even** p ≥ 2 (how many spins each interaction involves) and a density α > 0.
- Scatter M_N ~ Poisson(αN) interactions; each picks p spins at random (**with replacement**, so repeats are allowed) and applies a random function θ. Each spin also gets a random external field h.
- The only requirement is E[max|θ|] + E[|h|] < ∞ ("only first moments are needed": the interactions are not required to be bounded).

**The Panchenko–Talagrand condition**: e^θ can be written in the form a·(1 + b·f₁(s₁)·…·f_p(s_p)), where the f's are i.i.d., b is independent of them, and **E[(−b)ⁿ] ≥ 0 holds for all n ≥ 1**.

Check it on the Viana–Bray model (p = 2, θ = βJ·s₁s₂, with J symmetrically distributed): take a = cosh(βJ), b = tanh(βJ), f(s) = s.

**[Check 5]** Verify that e^(βJ·s₁s₂) = cosh(βJ)·(1 + tanh(βJ)·s₁s₂), separately for s₁s₂ = +1 and −1. (The script, with βJ = 0.7, verifies that both sides are 2.01375 and 0.49659.)

Because J is symmetric, the odd moments of b = tanh(βJ) are 0 and the even moments are positive, so the positivity condition holds.

The coverage listed in Section 10 of the paper (OpenAI's claim):
- the **Viana–Bray model** (p = 2, symmetric random couplings);
- **diluted p-spin models with even p** (symmetric couplings);
- **soft random even K-SAT**, at every positive temperature ("soft": a violated clause is only penalized by energy βW, not strictly forbidden).
- Corollary 10.3: lowering the temperature to zero gives the limit of "maximum energy / minimum number of violated clauses," with error ≤ ln 2 / β.

### 13.8.3 What it does not cover (important)

- **Odd arity**: random **3-SAT** is not included. The paper's Remark 10.4 says so itself, and points to another OpenAI paper from the same batch, *Computing the Random 3-SAT Threshold* (2026-09-27), which uses a different trial functional (OpenAI's claim; not read for this chapter).
- **Fixed-degree Bethe lattice / random regular graphs**: the degrees in the theorem come from Poisson edge scattering. The setting of the original Mézard–Parisi 2001 paper is exactly the fixed-degree one, and that case is **not** covered by the theorem. In other words, the "Mézard–Parisi formula" in the paper's title refers to its counterpart on Poisson-diluted models.
- **Ferromagnetic models** (my inference; I haven't seen the paper say it explicitly ⚠): for fixed J > 0, the standard decomposition gives b = tanh(βJ) > 0, so E[(−b)ⁿ] alternates in sign and the positivity condition fails. But the ferromagnetic case was already handled by Dembo–Montanari 2010, so it is not a gap.
- **The zero-temperature hard-constraint SAT threshold**: the theorem is a result at every positive temperature; the zero-temperature limit only gives the minimum number of violations, not the satisfiability threshold directly. So it does **not** re-prove or extend Ding–Sly–Sun.
- **Hopfield networks**: fully connected (dense), with couplings determined by the stored patterns, so different edges are not independent; they are outside the theorem. The connections in §13.10.3 (Hopfield, perceptrons, loss landscapes) are about where the ideas came from, not consequences of this theorem.
- It **does not claim** that the infimum is attained by some trial law, and it does not construct an infinite-level limiting Gibbs state (the remarks after Theorem 2.1 in the paper).

### 13.8.4 Intuition for the method (I only read the introduction and §13.2.2; what follows is a simplified version)

The upper bound reuses the interpolation method (§13.4). The lower bound has four steps:

1. **Choose a "cavity reservoir"**: compare the system with N spins and with N + 1 spins, adding a sublinear number of small perturbations. These don't change the pressure, but they make the system satisfy certain "identities" (the perturbed statistics concentrate).
2. **Prescribe branching patterns**: develop a "calculus" on finite probability trees that expands the effect of inserting a new spin into a signed sum over replica paths, using independent labels to pick out any specified replica branching pattern.
3. **Concentrate all multioverlaps** (the core trick): **shift every internal branching depth of the target tree down one level, all at once**. That way the new branchings always land on depths the old tree hasn't used; each new branching pays a small factor, which exactly cancels the small factor in the normalizing coefficient, so the error stays controllable after division. Then **average over the branching depths** (it doesn't need to hold uniformly for every depth), and inductively make the conditional covariances decay.
4. **Recover independent cavity messages**: once the multioverlaps are concentrated, the messages at different positions can be replaced by independent copies, giving a valid trial value that is close to the true pressure.

Order of limits: for each fixed depth, first let N → ∞, then deepen the hierarchy. Finally a truncation removes the "bounded interactions" assumption, leaving only first moments.

The reasoning summary (`reasoning_traces/mezard-parisi-formula.pdf`, 5 pages) records this process. Two lines verbatim:

> "Aha recursive structure: overfitting shared variable can simulate original model at smaller scale."

> "Great! Need carefully prove average error little with shifted depths not rare"

The summary also candidly records failed attempts: the pinning method (fixing some spins) could not reconcile the observed distributions; a claim of "exact purity" "proves too strong"; and before "shifting the branching depths," various expansions all had errors that were too large after dividing by small exponent gaps.

### 13.8.5 Neighboring results in the same batch (OpenAI's claims; not verified for this chapter)

The same release also contains a whole group of spin glass results: family 222 (perceptron free energy, jamming exponents), 281 (full support of the zero-temperature SK Parisi measure; QAOA reaching the SK ground-state energy), 235 (computability and variance of the random k-SAT threshold; priority for the existence of the 3-SAT threshold goes to Gaia Carenini's ECCC TR26-229), 217 and others (SK fluctuations and dynamics). §13.10.3 uses 222 and 281.

---

## 13.9 How well has it been verified

### 13.9.1 The Lean statement

The main theorem of the challenge file `lean/ComparatorChallenges/DilutedSpin.lean` (154 lines):

```lean
theorem mezard_parisi {p : ℕ} (M : Model p) (hM : Admissible M) :
    Tendsto (pressure M) atTop (𝓝 (variationalValue M))
```

Word-by-word translation:
- `{p : ℕ}`: p is a natural number, the arity of the interactions.
- `(M : Model p)`: a model, made of three things: the density `alpha`, the distribution of interactions `disorder` (together with the decomposition witnesses θ, a, b, f), and the distribution of external fields `field`.
- `(hM : Admissible M)`: the assumption that the model satisfies the conditions. The `Admissible` structure spells them out one by one: `arity : 2 ≤ p`, `even : Even p`, `density : 0 < alpha`, two first-moment integrability conditions, `factorization` (e^θ = a(1 + b·Πf), with |b·Πf| < 1), the f's i.i.d. and b independent of the f's, all moments of b integrable, and `positivity : 0 ≤ E[(−b)ⁿ]`. These correspond one-to-one with (2.1)–(2.4) in the paper.
- `pressure M`: a sequence whose N-th term is F_N. The definition is written very concretely: take the expectation over Poisson(αN) interactions and i.i.d. external fields, **average uniformly** over all possible index choices (implementing "uniform sampling with replacement"), take log-sum-exp over the 2^N configurations, and divide by N.
- `variationalValue M`: `⨅ r, phi M r`, i.e. the infimum over all numbers of levels r; `phi M r` is the infimum of `functional` over all ζ ∈ `Hierarchy (r+1)` and all m satisfying `Exponents` (0 < m₁ < … < m_r < 1), and `functional` corresponds term by term to the paper's (2.11) B_r = ln 2 + E ln T₀V_s − α(p−1)·E ln T₀V_e.
- `Tendsto … atTop (𝓝 …)`: as N → ∞, F_N converges to this value. This also includes "the limit exists."

The difference from the quasi-Riemann hypothesis (§4): that statement used only Mathlib's standard definition `riemannZeta`; **here almost all the definitions (`pressure`, `Hierarchy`, `functional`, …) are written by the challenge file itself**, so "is the statement faithful" depends on a human reading these 154 lines. I read them item by item against Section 2 of the paper [P] and found no inconsistencies, but I am not an expert in this field ⚠.

### 13.9.2 The proof itself

- Solution module `OAI/Probability/DilutedSpin/`: **405 .lean files, 56,285 lines** (counted by script) [P]. grep for `sorry` / `admit` / `native_decide` / `axiom` declarations: **0**.
- The definitions in the solution module's `Model.lean` are **word-for-word identical** to those in the challenge file (I diffed the section from `Spin` to `variationalValue`).
- Comparator config `DilutedSpin.json`: only Lean's three standard axioms are allowed (`propext`, `Quot.sound`, `Classical.choice`); **`enable_nanoda: false`**, meaning no second, independent kernel is configured for a re-check.
- **We did not actually compile the proof or run Comparator** (the full library is very large). `formalization.yaml` is marked `review: status: unchecked` overall.
- Unlike the quasi-Riemann hypothesis (§4), **I found no report of any third party (someone like Goldblatt) independently running this proof successfully** ⚠.

### 13.9.3 Human experts

As of 2026-10-08, I found no named comment or verification report on this paper from any spin glass / probability expert ⚠ (searched; I only found aggregator blogs restating family 221). Panchenko, Talagrand, Coja-Oghlan, and others are the natural referees.

### 13.9.4 Remaining risks

1. **Faithfulness of the statement**: Lean proves the statement written in the challenge file. A few places deserve a close look from an expert: each level of `Hierarchy` uses the Borel σ-algebra of the weak topology (the file's comments say this follows the paper); the indexing convention for m in `logMean` (`m 0` corresponds to the paper's m₁); and `pressure` uses "average over all indices" in place of "random sampling." I believe these are all equivalent, but I haven't checked formally ⚠.
2. **Paper title vs. scope**: readers can easily take "the Mézard–Parisi formula" to mean the Bethe lattice (fixed-degree) case of Mézard–Parisi 2001, or to include 3-SAT. Neither is included (§13.8.3). This is the "spec vs. intent" gap that keeps recurring in this series.
3. **Readability of the proof**: a 36-page paper against 56,000 lines of Lean; the paper is written in summary style. It may take humans quite some time to understand why the "shifting the branching depths" trick works.

---

## 13.10 What it would mean if true (and what it would not mean)

### 13.10.1 For mathematics

1. **A roughly 20-year-old open conjecture (Panchenko–Talagrand 2004) is resolved in its original model class**, and it needs only first moments, a weaker assumption than the original problem set.
2. **The new technique may matter more than the conclusion**: "shift the branching depths + average over depths" to control all multioverlaps. If it holds up, it may generalize to other sparse models (fixed degree, odd arity). The paper itself says the lower-bound part **holds for any bounded interaction that is invariant under permutations of its inputs**, without needing the decomposition or the positivity condition (end of §2.2 of the paper); what is stuck is the upper bound. In other words, if someone later extends the interpolation upper bound to odd arity, the lower-bound half is already done.
3. **What it does not mean**: the formula for the random 3-SAT threshold, a complete solution of the Bethe lattice spin glass, and "ultrametricity" on sparse models are all still unsolved.

### 13.10.2 For physics

Physicists already "knew" in 2001 that this formula was right, and used it to compute a large number of numerical predictions. The theorem doesn't change any physical prediction. Its role is to **upgrade the cavity method from "a trustworthy heuristic" to a theorem** for one class of sparse systems. This is the same kind of significance as Talagrand 2006 for SK, but with a narrower scope.

### 13.10.3 For ML and neuroscience (the honest version)

**Connections that really exist**:

- **A Hopfield network (1982) is an Ising system.** Energy E = −½ Σ Wᵢⱼσᵢσⱼ, and the Hebb rule Wᵢⱼ = (1/N) Σ_μ ξᵢ^μ ξⱼ^μ stores P patterns; each memory is a minimum of the energy. When too many are stored, the "crosstalk" from the other patterns acts like random couplings and creates frustration, and the system falls into "spin glass states" that don't correspond to any memory. Amit–Gutfreund–Sompolinsky 1985 used the replica method to compute the capacity **α_c = P/N ≈ 0.138**. Script simulation (N = 1000, zero-temperature asynchronous updates, starting from a stored pattern, 30 runs per α):

  | α = P/N | 0.05 | 0.10 | 0.12 | 0.13 | 0.14 | 0.15 | 0.17 | 0.20 |
  |---|---|---|---|---|---|---|---|---|
  | Mean final overlap m | 1.000 | 0.998 | 0.992 | 0.974 | 0.941 | 0.917 | 0.583 | 0.363 |

  Retrieval quality clearly collapses between 0.13 and 0.17, consistent with the 0.138 prediction. At N = 1000 the transition is smeared out by finite-size effects, and past 0.138 the overlap doesn't drop to zero right away, so this table is only a qualitative check. Hopfield and Hinton won the 2024 Nobel Prize in Physics.
- **Perceptron capacity**: Gardner 1988 used the replica method to compute the capacity of the spherical perceptron, α = 2; for the Ising perceptron (weights ±1), Krauth–Mézard 1989 predicted about 0.833, and rigorous proofs have only recently made partial progress (Ding–Sun 2019 proved the lower bound; Huang 2024 gave a matching upper bound under a numerical assumption ⚠ not rechecked). Family 222 in the same batch gives the free energies of the Ising perceptron and the spherical perceptron at **positive temperature**, plus jamming exponents for the spherical perceptron with negative margin (−1) (OpenAI's claim, per the 222 entry in the repo's `CONTENTS.md`), not the zero-temperature capacity itself.
- **Random optimization landscapes and algorithms**: Montanari 2019 (arXiv:1812.10897) gave a polynomial-time algorithm that approximately finds the SK ground state, **provided** the zero-temperature Parisi measure has "no overlap gap." Family 281 in the same batch claims to prove this full-support property (OpenAI's claim, not verified ⚠). If it holds, "the SK ground state can be approximated efficiently" becomes unconditional. This is the most direct answer spin glass theory gives to "can random landscapes be optimized efficiently," and it is closer to ML's concerns than 221 itself.
- **Inference on sparse graphs**: LDPC decoding, community detection, and the information-theoretic thresholds of sparse constraint satisfaction problems all rely on cavity / BP-type variational formulas. 221 adds one more rigorous cornerstone to arguments of the form "physics prediction = true threshold" (speculative extrapolation).

**Where to discount**:

- **221 does not cover Hopfield.** Hopfield is fully connected (dense), and its couplings are determined by the patterns, so different edges are not independent; 221 requires sparse models with independent interactions. The "sparse Hopfield" models in neuroscience (for example the strongly diluted model of Derrida–Gardner–Zippelius 1987) also don't fit the Panchenko–Talagrand decomposition.
- The intuition of a "rugged landscape with hierarchically clustered minima" for loss landscapes comes from spin glasses; the best-known example is the analogy **deep network loss landscape ≈ spherical spin glass** (Choromanska et al. 2015). Such analogies rely on strong simplifying assumptions and are mostly **heuristic**. This theorem won't tell you what SGD will find, where it converges, or how well a model generalizes.
- The second half of this chapter's title, "from magnets to the energy landscapes of neural networks," is about an **intellectual lineage** (energy functions, the replica method, rugged landscapes), not a claim that this theorem has direct consequences for neural networks.

### 13.10.4 For AI

This is a textbook case of "AI fills in a missing step in a classic research program": the problem has a clear origin (the conjecture after Theorem 4 of PT 2004), a Lean statement, and a candid reasoning summary. It is also a teaching case for "spec vs. intent": the scope Lean covers (Poisson, even arity, positivity) is narrower than the paper's title suggests, and judging that gap takes domain knowledge; Lean can't do it for you.

---

## 13.11 Self-test

Try to answer these after reading. If you can't, go back and reread the corresponding section.

1. Why do physicists compute E[ln Z] rather than the easier ln E[Z]? When do the two differ? (§13.3.3)
2. Which step of the replica trick has no mathematical justification? (§13.4.1)
3. What is wrong with the replica-symmetric SK solution? Give a clearly unphysical number. (§13.4.2)
4. Why is cavity / BP exact on trees but inexact on graphs with short cycles? Why is there still hope for sparse random graphs? (§13.5.2–13.5.3)
5. What does "hierarchical" refer to in the hierarchical cavity formula? How is `Hierarchy` defined in Lean? (§13.5.4, 9.1)
6. What is the relationship between the π²/6 of the random assignment problem and the formula OpenAI proved? (§13.0, 6)
7. In the Panchenko–Talagrand conjecture, which half was proved long ago? Why is the other half harder in sparse models than in SK? (§13.7.2–13.7.3)
8. List three classes of models that OpenAI's theorem does **not** cover. (§13.8.3)
9. Why can't you say "this theorem proves such-and-such a property of Hopfield networks"? (§13.10.3)

---

## Appendix: answers to the checks

- **Check 1**: e¹ ≈ 2.7183, e⁻¹ ≈ 0.3679, 2e + 2e⁻¹ ≈ 6.1724, so P(+,+) ≈ 2.7183 / 6.1724 ≈ 0.4404 (script: 0.44040).
- **Check 2**: H = σ₁σ₂ + σ₂σ₃ + σ₁σ₃. For (+,+,+) and (−,−,−), all three terms are +1, so H = +3. The other 6 configurations all have "two of one sign, one of the other": the same-sign pair contributes +1, and the other two pairs contribute −1 each, so H = −1. So there are 2 with +3 and 6 with −1.
- **Check 3** (the example from §13.5.3): only spin 1 has an external field. Z = Σ e^(σ₁σ₂ + 0.5σ₁). The total weight for σ₂ = +1 is e^(1.5) + e^(−1.5), and for σ₂ = −1 it is e^(−0.5) + e^(0.5). m₂ = [e^1.5 + e^−1.5 − e^0.5 − e^−0.5] / [e^1.5 + e^−1.5 + e^0.5 + e^−0.5] = (4.7048 − 2.2553)/(4.7048 + 2.2553) ≈ 0.3519 = tanh(1)·tanh(0.5).
- **Check 4**: a + d and b + c are two independent Gamma(2, 1) variables, with P(X > t) = (1+t)e^(−t). So P(min > t) = (1+t)²e^(−2t), and E[min] = ∫₀^∞ (1 + 2t + t²)e^(−2t) dt = 1/2 + 2·(1/4) + 2/8 = 5/4.
- **Check 5**: when s₁s₂ = +1, the right-hand side = cosh(βJ) + sinh(βJ) = e^(βJ); when s₁s₂ = −1, the right-hand side = cosh(βJ) − sinh(βJ) = e^(−βJ). In both cases it equals the left-hand side.

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| Spin | A variable taking only ±1, representing a tiny compass needle (or a binary neuron) |
| Ising model | A spin system with energy −Σ Jᵢⱼσᵢσⱼ |
| Boltzmann distribution | P(σ) ∝ e^(−βH(σ)), i.e. a softmax with −β·energy as the logit |
| Partition function Z | The sum of the weights of all configurations; the normalizing constant |
| Free energy / pressure | F = −(1/β) ln Z; pressure = (1/N) ln Z; they differ by a factor |
| Frustration | A situation where it is impossible to satisfy all interactions at once |
| Spin glass | A spin system with randomly signed couplings and frustration everywhere |
| Quenched / annealed average | E[ln Z] / ln E[Z]; physics needs the former |
| Replica method | A non-rigorous trick that computes E[ln Z] via ln Z = lim (Zⁿ − 1)/n |
| Overlap Q_ab | The similarity of two replica configurations, (1/N)Σσᵢ^aσᵢ^b |
| Multioverlap | The spatial average of a product of spins across several replicas; sparse models require controlling all of them |
| RSB (replica symmetry breaking) | Replicas form a hierarchy (a tree), corresponding to many pure states |
| Ultrametric | A distance structure where, among any three points, the two largest distances are equal, like a taxonomy tree |
| SK model | A dense spin glass in which every pair of spins has a random coupling |
| Viana–Bray model | A Poisson-diluted two-body spin glass |
| Bethe lattice | A sparse (random regular) graph in which every vertex has the same fixed degree |
| Cavity method / BP | Remove a spin and compute its state from messages sent by its neighbors; exact on trees |
| Hierarchical cavity formula | A variational formula expressing the free energy in terms of "distributions of distributions of messages…" |
| Panchenko–Talagrand class | Even-arity interactions with e^θ = a(1 + b·Πf) and E[(−b)ⁿ] ≥ 0 |
| Interpolation method | Guerra's trick: interpolate continuously between the real model and a trial model to obtain an upper bound |

## Appendix: Further reading

- **Mézard & Montanari**, *Information, Physics, and Computation* (Oxford University Press, 2009): covers spin glasses, the cavity method, BP, random k-SAT, and coding in one book, written for CS readers; Chapters 14–19 cover exactly §13.5–13.7 of this chapter. Most recommended.
- **Panchenko**, *Introduction to the SK model* (survey, arXiv:1412.0170): https://arxiv.org/abs/1412.0170 ; the full version is his book *The Sherrington–Kirkpatrick Model* (Springer, 2013).
- **Nobel 2021 popular information** (the Parisi part): https://www.nobelprize.org/prizes/physics/2021/popular-information/
- **Mézard & Parisi 2001**, *The Bethe lattice spin glass revisited*, EPJ B 20:217 (arXiv:cond-mat/0009418 ⚠ ID from memory, please verify).
- **Panchenko & Talagrand 2004**, *Bounds for diluted mean-fields spin glass models*, PTRF 130:319, https://doi.org/10.1007/s00440-004-0342-2 .
- **Panchenko 2016**, *Structure of finite-RSB asymptotic Gibbs measures in the diluted spin glass models*: https://arxiv.org/abs/1406.4702
- **Aldous 2001**, *The ζ(2) limit in the random assignment problem*, Random Structures & Algorithms 18:381–418.
- **Montanari 2019**, *Optimization of the Sherrington–Kirkpatrick Hamiltonian*: https://arxiv.org/abs/1812.10897
- **Concetti 2025** (random regular graphs, the open part): https://arxiv.org/abs/2508.17049
- The original paper: https://github.com/openai/math/blob/main/preprints/The-Mezard-Parisi-formula-for-diluted-spin-glasses-September-23-2026/paper.pdf
- The Lean statement: https://github.com/openai/math/blob/main/lean/ComparatorChallenges/DilutedSpin.lean ; scope notes: https://github.com/openai/math/blob/main/lean/docs/221.md
- The reasoning summary: https://github.com/openai/math/blob/main/reasoning_traces/mezard-parisi-formula.pdf
