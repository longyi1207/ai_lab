# Explainer 09: The relativistic Vlasov–Maxwell system (can a plasma model break down on its own?)

> This is the "explained from zero" version of §12 of the `notes/openai_math_explained/` deck. Prerequisites: you can take a derivative, you know the dot product and cross product of vectors, and you know that "a differential equation describes how something changes over time." You don't need to have studied partial differential equations (PDEs) or plasma physics. Every new concept is explained before it is used.
> Every number in the text was computed by script or has a source. **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter.
> Estimated reading time: 60–90 minutes. You can split it into three sittings: Sections 1–4 (plasma, phase space, the equations themselves), Sections 5–7 (relativity, what "the solution breaks down" means, 40 years of history), Sections 8–10 (OpenAI's result, how well it is verified, and what it means).

---

## 0. The bottom line: the one thing this chapter explains

Plasma (the ionized gas inside a fusion reactor or in the solar wind) has a standard mathematical model: the **relativistic Vlasov–Maxwell system**. It says: charged particles are pushed around by the electromagnetic field, the particles' motion creates currents, and those currents in turn change the electromagnetic field. This loop is nonlinear.

The question mathematicians want answered is: **starting from a normal initial state, can a solution of this model "break down" in finite time?** That is, can some quantity suddenly become infinite, so that the equations stop making sense from then on?

This chapter explains one chain of reasoning:

> Whether the solution breaks down ⟸ (Glassey–Strauss 1986) depends only on "whether the momentum of the fastest particle can shoot to infinity in finite time" ⟸ if you can prove "each doubling of momentum takes at least c/log P time" ⟸ these times add up to a divergent series (like the harmonic series 1 + 1/2 + 1/3 + …), so momentum cannot double infinitely many times in finite time.

OpenAI claims (2026-09-23, a 49-page paper + about 90,000 lines of Lean): in the **three-dimensional, single-species** case, for smooth initial data of any size and with no symmetry requirement, the solution **never breaks down** (it exists globally, is smooth, and is unique). This was an open problem for about 40 years.

After reading this chapter, you should be able to explain in your own words:
- why plasma has to be described by a "phase-space density" f(t, x, v) rather than an ordinary density;
- why the whole problem reduces to "can a particle's momentum blow up in finite time," and why "the sum of the doubling times diverges" is enough;
- how well OpenAI's result has been verified, and what extra risks it carries compared with the ζ-function chapter;
- what it means for fusion engineering (almost nothing directly), and why.

---

## 1. Plasma: why we care

### 1.1 What a plasma is

Heat a gas to a high enough temperature and electrons get knocked out of the atoms. The gas turns into a soup of **positively charged ions + negatively charged electrons**. That is a plasma, often called the "fourth state" of matter.

Two examples you know:
- **Fusion reactors** (tokamaks, such as ITER): the core temperature is on the order of 10 keV. Converting to temperature: 1 eV corresponds to about 11,604.5 K, so 10 keV ≈ **116 million K** (computed by script).
- **The solar wind**: plasma the Sun continuously blows outward, with a typical speed of about 400 km/s (⚠ this is the commonly quoted typical value; the real speed varies between roughly 300 and 800 km/s). As a fraction of the speed of light: 400 / 299,792 ≈ **0.0013** (computed by script).

### 1.2 "Collisionless": why fluid equations don't work

In an ordinary gas, molecules collide countless times per second. Collisions quickly turn the local velocity distribution into a "thermal equilibrium" bell curve, so the gas can be described by just a few quantities: density, mean velocity, and temperature. (That is fluid dynamics, for example Navier–Stokes in Explainer 08.)

A hot, thin plasma is different: a particle can travel a very long way between two collisions, in many cases farther than the size of the device (⚠ the actual numbers vary a lot with density and temperature; only the order-of-magnitude relationship is stated here). Collisions don't have time to "smooth out" the velocity distribution. At the same location there can be a group of fast particles and a group of slow ones at once, or even two streams of particles moving in opposite directions. **Recording only the mean velocity throws away key information.**

So we need a different description: record not only "how many particles are here," but also "at what velocity each of the particles here is moving." That is the phase space of the next section.

---

## 2. Phase space and the distribution function f(t, x, v)

### 2.1 Phase space: record position and velocity together

A particle's state is determined by two things: **where it is (x)** and **which way and how fast it is moving (v)**. Put the two together and you get a point (x, v). The space of all possible (x, v) is called **phase space**.

- On a one-dimensional line, x is one number and v is one number, so phase space is a **two-dimensional plane**.
- In real three-dimensional space, x has 3 components and v has 3 components, so phase space is **6-dimensional**. Add time, and f(t, x, v) is a function of 7 variables.

The **distribution function** f(t, x, v) means: at time t, roughly how many particles there are per unit volume of phase space near (x, v). Integrate f over all velocities and you get back the ordinary density:

```
ρ(t, x) = ∫ f(t, x, v) dv      (total number of particles at position x, regardless of velocity)
```

### 2.2 A toy example: why position alone is not enough

Four particles on a line, two scenarios:

| | Particle positions | Particle velocities |
|---|---|---|
| Scenario A (two counter-streaming beams) | 0, 0, 1, 1 | +1, −1, +1, −1 |
| Scenario B (at rest) | 0, 0, 1, 1 | 0, 0, 0, 0 |

At t = 0, **looking only at positions**, the two scenarios are identical: 2 particles at position 0 and 2 at position 1.

But at t = 2 (each particle moves according to x + v·t):
- Scenario A: the particles are at 2, −2, 3, −1. They have spread out.
- Scenario B: the particles are still at 0, 0, 1, 1.

So the ordinary density ρ cannot predict the future, but **the phase-space density f can**. Physically, "counter-streaming beams" are exactly the typical configuration that triggers an instability in a plasma (the two-stream instability), and a fluid description can't see it.

### 2.3 Drawing a histogram in phase space (computed by script)

Here is a slightly larger example. 12 particles, positions x between 0 and 4, velocities ±0.5 or ±1. Count them in bins of width 1 by position:

| Position bin | [−1,0) | [0,1) | [1,2) | [2,3) | [3,4) | [4,5) |
|---|---|---|---|---|---|---|
| Particles per bin at t = 0 | 0 | 3 | 3 | 4 | 2 | 0 |
| Particles per bin at t = 1 (each particle moves v×1) | 1 | 0 | 5 | 3 | 2 | 1 |

(Computed by script; the particle data is in `精讲/scripts/09_vlasov_maxwell.py`.)

If you only have the 4 numbers in the t = 0 row, you cannot derive the t = 1 row. If you have "how many particles of each velocity are in each bin" (that is, a two-dimensional histogram in phase space), you can. **f is the limit of this two-dimensional histogram as the bins become infinitely small and the particles infinitely many.**

---

## 3. The Vlasov equation: particles follow trajectories, and f moves with them

### 3.1 First, no forces (free streaming)

With no forces at all, each particle moves in a straight line at constant speed: x(t) = x₀ + v·t, and velocity doesn't change. A "clump of particles" in phase space just gets translated and sheared; particles don't appear or disappear. So

```
f(t, x, v) = f₀(x − v·t, v)
```

This means: "the particle at (x, v) at time t is the particle that was at (x − vt, v) at time 0."

Differentiate this expression with respect to t and you can verify that it satisfies

```
∂f/∂t + v · ∂f/∂x = 0
```

**[Check 1]** Let f₀(x, v) = e^(−x²)·g(v), so under free streaming f(t, x, v) = e^(−(x−vt)²)·g(v). Compute ∂f/∂t and ∂f/∂x directly and verify that ∂f/∂t + v·∂f/∂x = 0.

### 3.2 Adding a force: the Vlasov equation

When a force F acts, velocity changes too: dv/dt = F (taking mass to be 1 here). f is still "constant along particle trajectories"; the trajectories are just curved now. As an equation:

```
∂f/∂t + v · ∇ₓf + F · ∇ᵥf = 0
```

- ∇ₓf is the vector of partial derivatives of f with respect to the three components of position; ∇ᵥf is the same with respect to the three components of velocity.
- The three terms mean: the change of f over time + the change due to particles moving in position + the change due to the force altering particle velocities = 0.

This is the **Vlasov equation** (1938), also called the "collisionless Boltzmann equation": add a collision term on the right-hand side and you get the Boltzmann equation.

**An important consequence**: since f is constant along trajectories, the **maximum of f can never grow** (0 ≤ f ≤ the maximum of f₀). This is Lemma 3.1 in the paper. It means the bad scenario "particles crowd together in phase space to infinite density" cannot happen. Any danger has to come from somewhere else.

### 3.3 Where the force comes from: the Lorentz force

The force on a charged particle is the **Lorentz force** (charge and mass both normalized to 1):

```
F = E + v × B
```

- E is the electric field, which pushes the particle directly;
- B is the magnetic field, which makes the particle **turn** through the cross product v × B. v × B is always perpendicular to v, so the magnetic field **only changes direction and does no work**. It doesn't change the particle's speed.

**[Check 2]** Take v = (1, 0, 0), B = (0, 0, 1). Compute v × B and verify that its dot product with v is 0.

---

## 4. Maxwell's equations: how particles create fields in return

### 4.1 The four equations in plain language

Set the speed of light c = 1 and absorb the various constants (this is the normalization the paper uses). Maxwell's equations are:

```
∂E/∂t − ∇×B = −j       (the current j and a changing magnetic field produce a change in the electric field)
∂B/∂t + ∇×E = 0        (a changing electric field produces a change in the magnetic field; Faraday's law)
∇·E = ρ                (charge is the "source" of the electric field; Gauss's law)
∇·B = 0                (there is no "magnetic charge")
```

In plain language:
- **∇· (divergence)**: how much a field "flows outward" from a point. ∇·E = ρ says "wherever there is charge, the electric field flows out of it."
- **∇× (curl)**: how much a field "swirls" around a point. The first two equations say "the electric and magnetic fields drive each other by swirling." This mutual driving propagates outward at the **speed of light**; it is the electromagnetic wave (light, radio).

### 4.2 Self-consistent coupling: a nonlinear loop

Connect the particles and the fields:

```
ρ(t, x) = ∫ f dv                (charge density: add up the particles of all velocities)
j(t, x) = ∫ (particle velocity) · f dv  (current: particles carry their charge as they move)
```

This forms a loop:

> f determines ρ and j → ρ and j determine E and B through Maxwell's equations → E and B determine how the particles move through the Lorentz force → the particles' motion changes f again.

Taken alone, the Vlasov equation is linear in f (for given E and B), and Maxwell's equations are linear in E and B. **The nonlinearity comes entirely from this loop**: the force E + v×B itself depends on f. This is the same kind of structure as "the velocity field transports itself" in Navier–Stokes in Explainer 08.

### 4.3 Two "conserved quantities"

Two things in this system never change (Section 3 of the paper uses exactly these):
- **the number of particles** (f is constant along trajectories, and phase-space volume is preserved);
- **the total energy** = the kinetic energy of all particles + the electromagnetic field energy ½∫(|E|² + |B|²)dx.

So "the total energy blows up" is impossible. If anything breaks, it can only be because **energy concentrates onto a very few particles, or onto extremely small scales**. This point is the key to understanding everything that follows.

---

## 5. Why relativity

### 5.1 The problem with the non-relativistic version

If you use Newtonian mechanics (velocity = momentum / mass, which can be arbitrarily large), particles can move faster than light. But in Maxwell's equations the fields propagate at the speed of light. Once a particle outruns the field it is producing, the model contradicts itself. So **the physically consistent version must be relativistic**: particle speeds are always below the speed of light.

### 5.2 The relation between momentum and velocity

Take c = 1 and mass = 1, and write the momentum as p (a three-dimensional vector). In relativity:

```
velocity v̂ = p / √(1 + |p|²)
```

⚠ **Notation warning**: in OpenAI's paper and Lean code, the letter **v denotes momentum**, and the velocity is written u(v) = v / √(1+|v|²) (written v̂ in the reasoning summary). So the v in f(t, x, v) is actually momentum. Below I consistently use p for momentum and v̂ for velocity, to avoid confusion.

(Computed by script)

| Momentum p | Velocity v̂ | Gap to light speed 1 − v̂ |
|---|---|---|
| 0.1 | 0.0995 | 0.90 |
| 0.5 | 0.447 | 0.55 |
| 1 | 0.707 | 0.29 |
| 2 | 0.894 | 0.11 |
| 10 | 0.995 | 0.0050 |
| 100 | 0.99995 | 0.00005 |
| 1000 | 0.9999995 | 0.0000005 |

At small momentum v̂ ≈ p (Newtonian mechanics). At large momentum v̂ gets arbitrarily close to 1 but never reaches it. **Momentum can be arbitrarily large; velocity always stays below the speed of light.** This is why the "blowup" below has to be discussed in terms of momentum rather than velocity: velocity cannot possibly blow up.

**[Check 3]** What is v̂ when p = 3? (Hint: √10 ≈ 3.162)

### 5.3 Where real particles sit in this table (computed by script)

The electron's rest energy is 511 keV. Given a kinetic energy K, we have γ = 1 + K/511, p = √(γ² − 1), v̂ = p/γ:

| Electron kinetic energy | Momentum p (in units of m·c) | Velocity v̂/c |
|---|---|---|
| 1 keV | 0.063 | 0.062 |
| 10 keV (order of fusion core temperature) | 0.20 | 0.19 |
| 100 keV | 0.66 | 0.55 |
| 1 MeV | 2.78 | 0.94 |
| 10 MeV | 20.5 | 0.9988 |

Tokamaks have a dangerous phenomenon called **runaway electrons**: under a strong electric field, a small number of electrons are continuously accelerated to MeV or even tens of MeV (⚠ the order of magnitude comes from fusion physics reviews, for example Breizman et al., *Nuclear Fusion* 59 (2019) 083001, not checked word for word). At that point relativistic effects cannot be ignored at all. Note: runaway electrons are a **physical phenomenon**, with very large but finite momentum. They are not the same thing as the "mathematically, momentum → ∞ in finite time" discussed below.

### 5.4 The light cone: why Maxwell is harder than Poisson

If you ignore the magnetic field and assume the electric field responds "instantly" to the charge distribution (∇·E = ρ and E is the gradient of some potential), you get the simpler **Vlasov–Poisson** system. Its large-data problem in three dimensions was solved in 1991–92 (Pfaffelmoser 1992, Lions–Perthame 1991, Schaeffer 1991; the paper cites Pfaffelmoser, [20]).

Maxwell's fields don't respond instantly; they propagate at the speed of light. The field a particle feels at (t, x) comes from certain points in past spacetime: exactly those points that can send a signal to (t, x) at the speed of light. Together they form a **backward light cone**. The field produced this way is called the **retarded field**.

The difficulty: a source particle moving close to the speed of light is almost **running alongside the light it emits**. Its field piles up along the direction of motion (physicists call this "relativistic field compression"). When the source particle's velocity is almost parallel to the direction of the light ray, large factors appear in the retarded-field formula. The "loss" the OpenAI paper talks about (Section 8) happens right here.

---

## 6. What "the solution breaks down" actually means

### 6.1 An ODE toy: finite-time blowup

Look at the simplest equation dp/dt = p², p(0) = 1. The solution is p(t) = 1/(1 − t): 2 at t = 0.5, 10 at t = 0.9, 100 at t = 0.99, and **it goes to infinity as t → 1**. The equation itself is perfectly smooth, yet the solution breaks down at t = 1. This is called **finite-time blowup**.

Count it another way: p doubles from 1 to 2, from 2 to 4, from 4 to 8… Going from 2ᵏ to 2ᵏ⁺¹ (k = 0, 1, 2, …) takes time 1/2ᵏ − 1/2ᵏ⁺¹ = 1/2ᵏ⁺¹.

| Doubling number | Time taken by this doubling | Cumulative time |
|---|---|---|
| 1st | 1/2 | 0.5 |
| 2nd | 1/4 | 0.75 |
| 3rd | 1/8 | 0.875 |
| 60 doublings | … | 1 − 2⁻⁶⁰ (computed by script ≈ 1.0) |

**The doubling times get shorter and shorter, and their sum converges** (the geometric series sums to 1), so momentum can double infinitely many times in finite time. That is blowup.

### 6.2 The other way around: the sum of doubling times diverges ⇒ no blowup

If you can prove "the k-th doubling takes at least c/k time," then the total time for N doublings is at least c·(1 + 1/2 + … + 1/N). This sum is called the **harmonic series**, and it **diverges**:

| N | 1 + 1/2 + … + 1/N (computed by script) |
|---|---|
| 10 | 2.93 |
| 60 | 4.68 |
| 100 | 5.19 |
| 1,000 | 7.49 |
| 1,000,000 | 14.39 |

It grows very slowly (roughly like ln N), but without bound. So within any finite time T, momentum can only double finitely many times, and momentum stays bounded.

This contrast is the skeleton of the entire proof, and it is what the staircase figure in the deck (FIG_HARMONIC) shows:

> Geometric series 1/2 + 1/4 + … (converges) → can blow up; harmonic series 1 + 1/2 + 1/3 + … (diverges) → cannot blow up.

**[Check 4]** If all you can prove is "the k-th doubling takes at least 1/k² time," can you conclude there is no blowup? Why or why not?

(By the way: in Explainer 01, ζ(1) = 1 + 1/2 + 1/3 + … diverges; it is the same series.)

### 6.3 "Global regularity" for PDEs

For a PDE, "the solution breaks down" means some derivative or some quantity becomes infinite at a finite time, after which the equation can no longer hold pointwise. The opposite properties are:

- **Local existence**: starting from smooth initial data, a smooth solution exists at least for a short time interval [0, T). For Vlasov–Maxwell this was proved by Wollman 1984 (paper [29]).
- **Global regularity** / **global classical solution**: this smooth solution can be continued for all time t ≥ 0. This is what OpenAI claims.

There is another concept that is easy to confuse with these: **weak solutions**. DiPerna–Lions 1989 (paper [5]) proved that "weak solutions" exist globally for large data. A weak solution is allowed to be non-smooth, satisfies the equation only "on average," and is not known to be unique. So the existence of weak solutions **does not mean** the problem is solved. This is exactly the same situation as Leray's 1934 weak solutions for Navier–Stokes.

---

## 7. 40 years of history: how the problem was reduced, and where it got stuck

### 7.1 Glassey–Strauss 1986: you only need to control the fastest particle

**Glassey & Strauss, "Singularity formation in a collisionless plasma could occur only at high velocities", ARMA 92 (1986) 59–90.** The title is the conclusion:

> If on [0, T) the momenta of all particles stay below some finite number, then the solution can be continued smoothly past T.

Take the contrapositive: if the solution breaks down at a finite time T, then **some particle's momentum must have shot toward infinity before T**. The whole problem is reduced to a question about single particles:

> **Can a particle be accelerated to infinite momentum in finite time by the self-consistent electromagnetic field?**

This criterion was later re-proved and strengthened many times: Klainerman–Staffilani 2002 with Fourier methods, Bouchut–Golse–Pallard 2003 with physical-space methods; Luk–Strain 2014 proved that it is enough to control the projection of momentum onto some fixed plane; Pallard, Sospedra-Alfonso–Illner and others gave various moment conditions (§1.1 of the paper lists the sources). But all of these are **conditional**: they tell you "it's enough for momentum to be bounded," not "momentum really is bounded."

### 7.2 Lower dimensions: Glassey–Schaeffer

If you make the problem "a few dimensions smaller," it can be done:
- **1½ dimensions** (1D position, 2D momentum): Glassey–Schaeffer 1990;
- **2½ dimensions**: Glassey–Schaeffer 1997;
- **2 dimensions** (2D position): Glassey–Schaeffer 1998, two papers (ARMA 141).

(All cited from the paper's references [6, 7, 9, 10].) In lower dimensions the singularity of the field is weaker, and energy conservation is enough to control acceleration. In three dimensions this "just barely enough" margin disappears.

### 7.3 Small data, symmetry

- **Small data / dilute plasma**: Glassey–Strauss 1987 (paper [12]), followed by Schaeffer 2004, Bigorgne 2020/2025, Wang 2022, Wei–Yang 2021, and others. The idea: if the particles are sparse enough, the field is weak and the acceleration is limited.
- **Symmetry**: Xuecheng Wang's large-data result under cylindrical symmetry (arXiv:2203.01199, v1 in 2022, v2 on 2026-07-16; the paper says "to appear in Annals of Mathematics"; a second paper is arXiv:2607.14685, 2026-07-16). This was the closest large-data result before OpenAI, but it requires the initial data to be rotationally symmetric about an axis.

**Up to before 2026-09** (going by the survey in §1.1 of the paper), the three-dimensional large-data problem **with no size or symmetry restrictions** remained open.

### 7.4 Where the difficulty lies (intuitive version)

Conservation of total energy gives a "budget." To prove that a particle isn't accelerated to infinity, you need to estimate the total impulse it receives over a period of time. The most direct approach is to add up the **absolute values** of the force. But in three dimensions this estimate overshoots what you need by a factor of √w (w is the energy of the receiving particle). It falls just short and can't be closed. The loss happens when the source particle's velocity is almost parallel to the direction of the light ray (Section 5.4).

So you have to exploit **cancellation**: the force is sometimes positive and sometimes negative, and its direction changes; if you integrate first and then take the absolute value, the result can be much smaller. The hard part is capturing this cancellation in a rigorous proof.

---

## 8. What OpenAI claims

### 8.1 The main result

The abstract of the paper *Global classical solutions of the three-dimensional relativistic Vlasov–Maxwell system* (OpenAI, 2026-09-23, 49 pages):

> "We prove global existence and uniqueness for arbitrary smooth admissible initial data in the three-dimensional, one-species relativistic Vlasov–Maxwell system. The particle density is initially compactly supported, and the electromagnetic fields have finite energy and bounded derivatives of all orders. The solution remains smooth on every finite time interval. This resolves the large-data global classical regularity problem for this model, without size or symmetry restrictions on the data."

Breaking it down:
- **Dimension**: three-dimensional space + three-dimensional momentum ("3+3 dimensions").
- **Direction**: this is **global regularity** (no blowup), not blowup. That is the opposite direction from Navier–Stokes in Explainer 08.
- **One species**: there is only one kind of charged particle, with charge and mass both normalized to 1, and no background charge.
- **Initial data conditions** ("admissible"): f₀ is smooth, non-negative, and **compactly supported** (nonzero only in a bounded region of phase space, so the initial momentum is bounded); E₀, B₀ are smooth, with all derivatives bounded and finite energy (they belong to L²); and they satisfy the two Gauss constraints ∇·E₀ = ρ₀, ∇·B₀ = 0.
- **Conclusion**: there exists a unique global classical solution; it is smooth on every finite time interval [0, T], and the particle support is compact (momentum is bounded, but **the bound may grow with T**).

The paper also points out specifically (after Theorem 1.1) that the total charge is allowed to be nonzero (so the electric field has a Coulomb tail ~1/r² far away), and it does not require all derivatives of the fields to be square-integrable.

**[Check 5]** The Coulomb field of total charge Q has magnitude about Q/(4πr²). Verify that outside radius R, the electric field energy ½∫|E|²dx is finite (you only need to check whether ∫_R^∞ (1/r²)²·r² dr converges). This shows that "allowing nonzero total charge" and "finite energy" don't contradict each other.

### 8.2 The skeleton of the proof: two propositions

Section 2 of the paper splits the whole proof into two pieces:

**Proposition 2.2 (local theory + continuation criterion)**: the solution exists locally and is unique; if the maximal existence time T_max is finite, then the maximal momentum must be unbounded. This is the Glassey–Strauss criterion (in the formulation of Luk–Strain 2014), plus a technical fix: the Luk–Strain version requires the fields to be in H⁵ (a Sobolev space, roughly "5 derivatives square-integrable"), while the initial data here only require bounded derivatives and finite energy, so the two don't quite match. The paper's approach is to keep the Coulomb part, cut off the rest of the field far away, and then add back the difference using "Maxwell solutions in vacuum," relying on "finite signal propagation speed" to guarantee that this doesn't affect the particles within the given time (§10). In the reasoning summary, the model found this gap itself and went back to check it several times.

**Proposition 2.1 (signed momentum increment estimate)**: for a receiving particle with energy about w, over a time interval of length I,

```
|change in momentum| ≤ M·P·√I + A·I·P²·log(2+P) / w
```

where P is an upper bound on the current maximal momentum, and M, A are constants. The key word is "**signed**": first integrate the force over time (giving an impulse vector), then take its length, instead of first taking the magnitude of the force and then integrating.

### 8.3 From Proposition 2.1 to "no blowup": it's the staircase from Section 6

The paper's derivation (§2, "Proof of Theorem 1.1") goes like this: suppose T_max is finite; then the maximal momentum is unbounded. Let tₙ be the first time the maximal energy reaches 2ⁿ. During the n-th doubling, Proposition 2.1 gives

```
tₙ − tₙ₋₁ ≥ c / log(2 + 1024·2ⁿ)
```

The denominator is about n·log 2, so the n-th doubling takes at least ~c/n time: **exactly the harmonic series**. Summing the paper's exact form (with c = 1) (computed by script):

| Number of doublings N | Σ 1/log(2 + 1024·2ⁿ), n = 1…N |
|---|---|
| 10 | 0.96 |
| 100 | 3.40 |
| 1,000 | 6.59 |
| 10,000 | 9.90 |
| 100,000 | 13.22 |

The sum grows without bound, which contradicts "doubling infinitely many times before a finite T_max." So T_max = ∞.

**This step is the simplest in the whole paper.** About 40 of the 49 pages go into proving Proposition 2.1.

### 8.4 How Proposition 2.1 is proved (I only read the introduction and Section 2; what follows is a simplified version)

1. **Retarded fields + light-cone binning.** Follow the trajectories of the source particles to find where they intersect the backward light cone of the receiving particle, and sort the contributions into "bins" by momentum size, distance, and three angles (between the source velocity, the receiving velocity, and the direction of the light ray). Using the flux of energy through the light cone, plus estimates of "how long a source particle can stay in each bin" (occupation, i.e. occupation time), you get an upper bound on the **absolute value** of the force (§3–5).
2. **Find the loss.** When the receiving energy is ~w, the absolute-value estimate overshoots what is needed by a factor of √w. The loss is concentrated in a narrow strip of angles where "the source particle's velocity is closer to the light-ray direction than the receiving particle's is."
3. **Signed cancellation** (§6). In this narrow strip, first integrate along the source particle's trajectory, then take the absolute value. An exact identity combines "the part without the source particle's acceleration" and "the part with the source particle's acceleration": the former exactly cancels a term produced by differentiating the light-cone geometry. The force is thereby written as "a total derivative + some less singular terms." One of these terms contains **the receiving particle's own acceleration**, which in turn equals the force on the receiving particle, so it becomes "error ∝ the force on the receiving particle," and the coefficient in front of it has to be controlled.
4. **Count direction changes** (§7). Under the assumption that "all signed increments satisfy Proposition 2.1," the same identity is used to prove that the number of times a particle changes direction (turns through a given angle) is finite and countable. Between two turns, the relative motion is monotone, so the time a particle spends crossing a given angular region is compressed further, giving a better occupation estimate.
5. **Pick only the bins you need** (§8). The signed argument is used only on bins where the direct estimate exceeds a certain summable threshold. On those bins, after summing, the coefficient of the receiving particle's force is at most a constant × w^(−1/2), which **exactly cancels** the √w loss.
6. **Bootstrap** (§9). All of the above is done under the premise "assume Proposition 2.1 holds on [0, τ]." What comes out at the end is a **strictly better** estimate, and a continuity argument then pushes the assumption to the whole interval. Figure 1 in the paper draws this dependency graph.

An analogy in distributed-systems language: a bootstrap is a lot like "proving a protocol safe with an inductive invariant." Assume the invariant holds up to time τ, prove that it still holds a little beyond τ, and with margin to spare (a strict improvement), so it holds forever.

### 8.5 What the reasoning summary says

OpenAI published a 6-page "reasoning summary" (`reasoning_traces/relativistic-vlasov-maxwell.pdf`, released 2026-10-06). Some points worth noting:
- The model first tried a Pfaffelmoser-style "dwell time" strategy (exactly the route that solved Vlasov–Poisson in 1992), and also considered generalizing Wang's cylindrical-symmetry method to the general case.
- It hit a wall partway through and left concrete numbers: "the improved occupancy bound forced H < 0.41z, while the excessive coefficient required H > 0.496z". This rules out the "excessive coefficient" case through a contradiction between exponents: the two inequalities cannot both hold.
- The model found that the time window it was using to count direction changes was too long, and shortened it by a factor of ~M² + A·log P.
- The last sentence is quite candid: "That assertion rests on the occupation bound, direction-count estimate, and cutoff cancellations needed to close the signed momentum bootstrap; the cited continuation theorem alone does not establish those estimates."

---

## 9. How well has it been verified

### 9.1 The Lean statement: much longer than the ζ chapter's, and the definitions are homemade

The Lean statement in Explainer 01 is one line, and the `riemannZeta` it uses is Mathlib's standard definition. **Here it's different**: Mathlib has no Vlasov–Maxwell equations, so the challenge file `lean/ComparatorChallenges/VlasovMaxwell.lean` (about 140 lines) **defines everything from scratch**: momentum, velocity, cross product, curl, divergence, charge density, current, the equations themselves, and what a "classical solution" is.

The main theorem:

```lean
theorem global_classical_solution (d : Datum) (hd : Admissible d) :
    ∃ s : Solution, Classical d s ∧ SmoothOnFiniteHorizons s ∧
      ∀ s' : Solution, Classical d s' → SameNonnegativeTime s s'
```

Word-by-word translation:
- `d : Datum`: the initial data, a triple (f₀, E₀, B₀).
- `hd : Admissible d`: the initial data satisfy `Admissible`, which unfolds to: f₀ is smooth (`ContDiff ℝ ∞`), compactly supported (`HasCompactSupport`), and non-negative; E₀, B₀ are smooth with all derivatives uniformly bounded (`BoundedSmooth`); E₀, B₀ are square-integrable (`MemLp … 2`); ∇·E₀ = ρ(f₀), ∇·B₀ = 0.
- `∃ s : Solution`: there exists a solution (f, E, B).
- `Classical d s`: it is a classical solution: f, E, B are C¹ on t ≥ 0; f ≥ 0; E, B are continuous in time as L²-valued functions; on every finite time interval the support of f lies in a compact set; the equations hold pointwise; and at t = 0 it equals the initial data.
- `SmoothOnFiniteHorizons s`: on every [0, T], f, E, B are infinitely differentiable.
- `∀ s', Classical d s' → SameNonnegativeTime s s'`: any other classical solution is identical to it on t ≥ 0 (uniqueness).

This matches Theorem 1.1 of the paper, and the problem statement OpenAI gave the model (the prompt at the start of the reasoning summary).

**I checked by hand the places in the definitions most likely to be written wrong**:
- `velocity v = (q v)⁻¹ • v`, `q v = √(1 + ‖v‖²)`: exactly v̂ = p/√(1+|p|²). ✓
- `cross`: (a₁b₂ − a₂b₁, a₂b₀ − a₀b₂, a₀b₁ − a₁b₀), the standard cross product. ✓
- `curl`: first component ∂₁F₂ − ∂₂F₁, and so on; the standard curl. ✓
- `Equations`: ∂ₜf + v̂·∇ₓf + (E + v̂×B)·∇ᵥf = 0; ∂ₜE − ∇×B = −j; ∂ₜB + ∇×E = 0; ∇·E = ρ; ∇·B = 0. Matches the paper's (1.1) term by term, with the right signs. ✓

A trap specific to Lean: in Lean/Mathlib, the derivative of a non-differentiable function returns 0, and the integral of a non-integrable function also returns 0. If the statement didn't require smoothness, "the equations hold" could be satisfied by exploiting these default values. Here `Classical` requires C¹ and compact support, which closes that loophole (my judgment; no formal audit done ⚠).

### 9.2 The proof itself (local grep, snapshot fd4aeeb, 2026-10-07)

- Solution module `OAI/Analysis/VlasovMaxwell`: **207 .lean files, 89,993 lines** (computed by script). The largest subdirectories are `Population` (56 files, about 32,000 lines, corresponding to the paper's occupation and bin estimates) and `Retarded` (53 files, about 24,000 lines, corresponding to the retarded fields).
- grep finds no `sorry`, `admit`, `native_decide`, or custom `axiom`.
- **It imports only Mathlib** and doesn't depend on any patched external library. This is cleaner than Explainer 01 (which has a dependency patch of about 40,000 lines).
- In other words, the Glassey–Strauss continuation criterion **was not assumed as an axiom**; it was re-proved inside these 90,000 lines (`Continuation/GlobalContinuation.lean` contains theorems such as `bounded_momentum_uniform_restart`; I only looked at the theorem names and did not read the proofs ⚠).
- Comparator config `VlasovMaxwell.json`: only the three standard axioms are allowed (`propext`, `Quot.sound`, `Classical.choice`), and `enable_nanoda: false`, meaning **no re-check with a second, independent kernel**.

### 9.3 Independent checks and human experts

- **I found no public report of anyone successfully running Comparator on 362** (the Goldblatt re-check in Explainer 01 was for ζ). ⚠
- **As of 2026-10-08, I found no named public comment from any kinetic-theory / plasma PDE expert** (searched general media and the GitHub ecosystem around the release). ⚠ Media coverage just restates the abstract.
- A coincidence of timing worth noting: Wang's large-data cylindrical-symmetry paper had just been updated and accepted by Annals in 2026-07, and OpenAI's symmetry-free version appeared two months later. Experts in the field (Wang, Luk, Strain, Pallard, Bigorgne, and others) are the people best qualified to read these 49 pages.

### 9.4 Remaining risks

1. **Faithfulness of the statement**: 140 lines of homemade definitions; any subtle mistake could make the theorem "prove something else." I checked the equations and the key definitions and found no problems, but this is not a formal audit.
2. **Scope**: single species only. Real plasmas have at least two species, electrons and ions, with opposite charges, so particles both repel and attract each other. Whether the proof generalizes directly is **unknown** ⚠. A caution: in the related relativistic Vlasov–Poisson system, the "repulsive" (plasma) and "attractive" (gravitational) cases can have completely different conclusions (Glassey–Schaeffer 1985, paper [8], proved global existence for the spherically symmetric repulsive case; the attractive case is known to be able to blow up ⚠ the latter point is from my memory, not rechecked against the original).
3. **No human has understood it**: the 49-page bootstrap and bin decomposition have so far only been checked by a machine.

---

## 10. What it would mean if true (and what it would not mean)

### 10.1 For mathematics

1. **A roughly 40-year-old flagship open problem (single-species case) is solved**: from the Glassey–Strauss 1986 reduction to "momentum really is bounded."
2. **Methodological novelty**: signed impulse estimates + counting direction changes + using cancellation only in the bins that need it. Whether this transfers to other kinetic systems (multi-species Vlasov–Maxwell, Einstein–Vlasov, etc.) is open (speculation).
3. **The conclusion is finer than "no blowup"**: momentum is bounded on every finite time interval, but the bound may grow with time. It does **not** say what happens to particle momenta over long times (for example, whether they approach some stable state). Long-time behavior is a separate question.

### 10.2 For fusion and space physics: almost no direct impact

This deserves to be said clearly, because the media tend to write it up as "AI solves a hard math problem in fusion."

- **Engineering simulations don't depend on this theorem.** The fusion community uses particle-in-cell (PIC) methods, gyrokinetic codes, and fluid/MHD codes. They compute on discrete grids with finite resolution and finite time steps, and never need to assume that the continuum equations are globally smooth.
- **The model itself is far from a real device**: a real tokamak has at least two species of particles, collisions (important on long time scales), metal walls and boundary conditions, and strong magnetic fields from external coils. This theorem is proved for **all of unbounded three-dimensional space, with no external field and only one species of particle**.
- **Runaway electrons are not mathematical blowup**: the runaway electrons engineers worry about have very large but finite energy. The theorem says "nothing shoots to infinity in finite time"; it can't tell you how many MeV runaway electrons can reach at most in a real device.

A more accurate positioning: it is a **certificate of health for the model**. It tells physicists that this system of equations is self-consistent as a mathematical object: starting from reasonable initial data, it will not produce infinite momentum on its own in any finite time. (Note that what is controlled is each particle's **momentum**, not the total energy: the **total energy** is conserved anyway.) This has value for theorists (for example, it guarantees that the premises of certain derivations hold), but it won't change how anyone designs a fusion reactor today.

### 10.3 For AI

- This is **one of the weightiest mathematical-physics results in this batch**: a named open problem with a complete chain of literature, a clear conclusion, and **a Lean proof that depends only on Mathlib**.
- Compared with Explainer 01: the statement in the ζ chapter used community definitions (the risk was in the dependency patch); here the risk is in the **homemade statement**. For machine-proved PDE results, "is the statement faithful" is the new human bottleneck: reading 140 lines of Lean definitions is much easier than reading a 49-page paper, but it still needs someone who knows the field.
- The reasoning summary shows a process that looks fairly like a human researcher's: try known methods first, hit a wall, find a concrete contradiction between exponents, fix the time window, and repeatedly audit the order of dependencies. But what we see is a summary edited by OpenAI, not the raw reasoning.

---

## 11. Self-test

Try to answer these after reading. If you can't, go back and reread the corresponding section.

1. Why can't a plasma be described by the position density ρ(t, x) alone? Give an example. (Section 2.2)
2. The Vlasov equation says "f is constant along particle trajectories." What property of the maximum of f follows from this? (Section 3.2)
3. Why, in the relativistic version, do we look at momentum rather than velocity when discussing "blowup"? (Section 5.2)
4. What did Glassey–Strauss 1986 reduce the whole problem to? (Section 7.1)
5. Why does "the k-th doubling takes at least c/k time" imply no blowup? What if it were c/2ᵏ? (Sections 6.1–6.2)
6. Compared with the Lean statement for ζ in Explainer 01, where is the main extra risk in OpenAI's Lean statement? (Sections 9.1, 9.4)
7. Why is this result said to have almost no direct impact on fusion engineering? Give at least two reasons. (Section 10.2)

---

## Appendix: answers to the checks

- **Check 1**: Let s = x − vt. ∂f/∂t = e^(−s²)·(−2s)·(−v)·g(v) = 2vs·e^(−s²)g(v); ∂f/∂x = e^(−s²)·(−2s)·g(v) = −2s·e^(−s²)g(v). So ∂f/∂t + v·∂f/∂x = 2vs·e^(−s²)g − 2vs·e^(−s²)g = 0.
- **Check 2**: v × B = (0·1 − 0·0, 0·0 − 1·1, 1·0 − 0·0) = (0, −1, 0). Its dot product with v = (1, 0, 0) is 0. The particle is pushed in the −y direction, but its speed doesn't change; it only turns.
- **Check 3**: v̂ = 3/√10 ≈ 3/3.162 ≈ **0.949** (script: 0.9487).
- **Check 4**: No. 1/1² + 1/2² + 1/3² + … converges (to π²/6 ≈ 1.645, the ζ(2) of Explainer 01). The total time is finite, so momentum can double infinitely many times in finite time, and blowup can't be ruled out. You need a lower bound like 1/k whose "sum diverges."
- **Check 5**: ∫_R^∞ (1/r²)²·r² dr = ∫_R^∞ r⁻² dr = 1/R, which is finite. With the constants included, ½∫_{|x|>R}|E|²dx = Q²/(8πR); for Q = 1, the script computes ∫_R^∞ (1/(4πr²))²·4πr² dr = 1/(4πR), which is ≈ 0.0796 at R = 1 and ≈ 0.0080 at R = 10. In three dimensions a 1/r² field is square-integrable (far away); the part near the origin doesn't diverge either, because the charge is smoothly distributed.

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| Plasma | An ionized gas, made of ions and electrons |
| Collisionless | Particles travel far between collisions, so collisions don't have time to smooth out the velocity distribution |
| Phase space | The space of position + velocity (or momentum); 6-dimensional in 3D |
| Distribution function f(t, x, v) | Number of particles per unit volume of phase space; in the paper v means momentum |
| Vlasov equation | f is constant along particle trajectories; the "collisionless Boltzmann equation" |
| Lorentz force | E + v̂ × B; the magnetic field only changes direction and does no work |
| Maxwell's equations | How charges and currents produce electric and magnetic fields; fields propagate at the speed of light |
| Self-consistent coupling | The loop in which particles produce fields and fields push particles; the source of nonlinearity |
| Backward light cone / retarded field | The past spacetime points that can send a signal to the current point at the speed of light; the field coming from there |
| Vlasov–Poisson | Simplified version that ignores the magnetic field, with an instantly responding electric field; solved in 3D in 1991–92 |
| Finite-time blowup | Some quantity of the solution goes to infinity at a finite time |
| Global classical solution / global regularity | A smooth solution exists for all t ≥ 0 |
| Weak solution | A solution that satisfies the equation only in an averaged sense, possibly non-smooth and non-unique |
| Continuation criterion | A theorem of the type "as long as some quantity is bounded, the solution can be continued" |
| Compact support | The function is nonzero only in a bounded region |
| Bootstrap | Assume an estimate holds, derive a stronger estimate, then use continuity to remove the assumption |
| Harmonic series | 1 + 1/2 + 1/3 + …, which diverges |

## Appendix: Further reading

- **The original paper**: https://github.com/openai/math/blob/main/preprints/Global-classical-solutions-of-the-three-dimensional-relativistic-Vlasov-Maxwell-system-September-23-2026/paper.pdf (I suggest reading §1–2 first, 7 pages in total; the "Proof of Theorem 1.1" in Section 2 is the full version of Section 8.3 of this chapter)
- **The reasoning summary**: https://github.com/openai/math/blob/main/reasoning_traces/relativistic-vlasov-maxwell.pdf (6 pages)
- **The Lean statement**: https://github.com/openai/math/blob/main/lean/ComparatorChallenges/VlasovMaxwell.lean ; scope notes: https://github.com/openai/math/blob/main/lean/docs/362.md
- **Glassey & Strauss 1986**, ARMA 92:59–90, https://doi.org/10.1007/BF00250732 (the reduction of the problem)
- **Luk & Strain 2014**, *A new continuation criterion for the relativistic Vlasov–Maxwell system*, CMP 331:1005–1027, arXiv:1406.0165 (a modern, more readable proof of the continuation criterion; the OpenAI paper uses its formulation)
- **Wang**, cylindrically symmetric large data: arXiv:2203.01199, arXiv:2607.14685 (the closest result before OpenAI)
- **Robert Glassey**, *The Cauchy Problem in Kinetic Theory* (SIAM, 1996): the standard textbook of the field; the first few chapters cover the basic theory of Vlasov–Poisson and Vlasov–Maxwell.
- **Introductory physics**: Francis F. Chen, *Introduction to Plasma Physics and Controlled Fusion* (its chapter on "kinetic theory" covers the Vlasov equation, ⚠ chapter number not checked); good for filling in plasma background.
