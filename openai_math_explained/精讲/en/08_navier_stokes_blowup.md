# Explainer 08: Finite-time blowup for the Navier–Stokes equations (with external force)

> This is the "explained from zero" version of §11 of the `notes/openai_math_explained/` deck. All you need: how to take derivatives, what a partial derivative ∂/∂x means, and vectors and dot products. You don't need to have studied partial differential equations (PDEs); PDEs are explained from the start.
> Every number here is either computed by script or sourced. **[Check]** items are small exercises you can work out yourself; answers are at the end of the chapter. Tags: **[P]** = primary material I read myself (paper PDF, Lean file, official Clay text); **[R]** = secondhand reporting; **⚠** = unverified or disputed. As of 2026-10-08.
> Estimated reading time: 60–90 minutes. You can split it into three sittings: Sections 1–3 (PDEs, the fluid equations, what blowup means), Sections 4–6 (why it's hard, history, the Clay problem statement), Sections 7–9 (OpenAI's result, its verification, what it means).

---

## 0. The bottom line: the one thing this chapter explains

The Navier–Stokes (NS) equations describe how water and air flow, and engineers use them every day. But the most basic question about them has no answer: **starting from a smooth, gentle initial state, can the flow velocity become infinite in finite time?**

This chapter explains one causal chain:

> The equations contain a nonlinear term where "the fluid pushes itself", and it keeps making the velocity steeper ⟸ viscosity is smoothing it out ⟸ which of the two wins depends on scale ⟸ in 3 dimensions, the only "global ledger" we have (energy) controls less and less at smaller and smaller scales ⟸ so nobody can prove that viscosity always wins, and nobody can build an example where it loses.

In 2000 Clay listed this as a Millennium Prize Problem, with **four alternative statements (A)–(D)**; proving any one counts as a solution. (A) and (B) say "with no external force, solutions stay smooth forever"; (C) and (D) say "**there exists** some smooth external force that makes the solution break down in finite time".

**On 2026-09-08 OpenAI claimed proofs of (C) and (D)**: a smooth external force, acting only within a bounded region of space and time, makes a fluid that starts at rest develop infinite velocity at one point at t = 1, while total energy stays bounded throughout. It comes with about 640,000 lines of Lean. The same day they also released what may be the more important result: **unforced 3D Euler (inviscid fluid) blowup from smooth initial data**.

After this chapter, you should be able to explain in your own words:
- what a PDE is, and what "smooth solutions exist forever" and "finite-time blowup" each mean;
- why energy conservation cannot stop blowup in 3 dimensions (supercritical scaling, with numbers);
- what each of Clay's (A)–(D) says, and what role the external force f plays in (C)/(D);
- whether OpenAI's result **formally** counts as a solution under Clay's official text, which hurdles remain before "collecting the prize", and why many analysts think the real problem is still (A)/(B).

---

## 1. What is a PDE: starting with the heat equation

### 1.1 ODEs and PDEs

The differential equations you know, like y'(t) = −y(t), have as their unknown **a single** number y(t) that changes over time. These are called ordinary differential equations (ODEs).

In a partial differential equation (PDE), the unknown is **a whole field**: a value u(x, t) at every position x and every time t. The equation involves both the time derivative ∂u/∂t and spatial derivatives ∂u/∂x.

Cut space into small cells, one unknown per cell, with neighboring cells influencing each other: a PDE is "**infinitely many coupled ODEs**", like a distributed system in which each node only talks to its neighbors.

### 1.2 The simplest PDE: the heat equation

Take a thin iron rod, and let u(x, t) be the temperature at position x at time t. The heat equation is:

```
∂u/∂t = k · ∂²u/∂x²
```

The term ∂²u/∂x² on the right is the "curvature": if a point is hotter than both neighbors (like a peak), it is negative and the temperature drops; if it is colder than both neighbors (like a valley), it is positive and the temperature rises. So **the heat equation says "each point moves toward the average of its neighbors"**.

It's easier to see on a grid. With grid spacing Δx and time step Δt, write r = kΔt/Δx²; one update step is:

```
newᵢ = oldᵢ + r · (oldᵢ₋₁ − 2·oldᵢ + oldᵢ₊₁)
```

**One step by hand** (r = 0.25, checked by script): 7 cells `[0, 0, 0, 1, 0, 0, 0]`, with a hot spot in the middle.
- Middle: 1 + 0.25·(0 − 2 + 0) = 0.5
- The two neighbors: 0 + 0.25·(0 − 0 + 1) = 0.25
- Result: `[0, 0, 0.25, 0.5, 0.25, 0, 0]`, and the sum is still 1.

The hot spot has spread out, but the total heat is unchanged.

**[Check 1]** Take one more step (r = 0.25) from `[0, 0, 0.25, 0.5, 0.25, 0, 0]`. What is the result? What is the sum?

### 1.3 Numerical simulation: the heat equation smooths everything out

Computed by script: k = 1, initial temperature 1 where |x| < 0.5 and 0 elsewhere (a "box" whose edges are infinitely steep steps), advanced with the scheme above on 1001 grid points.

| t | Center temperature (numerical) | Center temperature (exact) | Total heat | Steepest slope |
|---|---|---|---|---|
| 0 | 1.0000 | 1.0000 | 0.990 | 100 (the steepest step the grid allows) |
| 0.01 | 0.9996 | 0.9996 | 0.990 | 2.82 |
| 0.1 | 0.7316 | 0.7364 | 0.990 | 0.83 |
| 0.5 | 0.3794 | 0.3829 | 0.990 | 0.22 |

(The total heat is 0.990 rather than 1 because the box on the grid is 0.99 wide.)

Remember: **the heat equation only makes things smoother.** An infinitely steep step instantly becomes a smooth curve, and the slope keeps falling. It is linear and cannot "blow up" on its own. The **viscosity term** in NS is mathematically "the heat equation applied to the velocity", and it is on the side of "smooth".

---

## 2. Fluids: the velocity field, and the NS equations term by term

### 2.1 The velocity field

The unknowns for a fluid are the **velocity field** u(x, t) (a 3D vector at every point and every moment) and the **pressure** p(x, t) (a number).

A 2D example: u(x, y) = (−y, x). At the point (1, 0) the velocity is (0, 1), pointing up; at (0, 1) it is (−1, 0), pointing left. Drawn out, it is a rigid rotation **counterclockwise around the origin**, faster the farther from the center (speed = radius r).

### 2.2 Incompressibility: zero divergence

Water is nearly incompressible. Mathematically this is written as **zero divergence**:

```
∇·u = ∂u₁/∂x + ∂u₂/∂y + ∂u₃/∂z = 0
```

Divergence measures "how much flows out of a small region, net". Zero divergence = as much flows in as flows out, so volume is preserved.

**[Check 2]** Compute the divergence of u = (−y, x) and of w = (x, y). Which one is incompressible? What does w look like when drawn?

### 2.3 The NS equations: Newton's second law, written for a small parcel of fluid

The official Clay problem statement (written by Fefferman) says: "Equation (1) is just Newton's law f = ma for a fluid element" [P]. The equations are:

```
∂u/∂t + (u·∇)u  =  ν Δu  −  ∇p  +  f          ∇·u = 0
└─ accel. a ─┘    └visc┘   └pres┘ └force┘
```

Term by term:

**Left side: the acceleration of a small parcel of fluid.** It has two parts:
- ∂u/∂t: the change of velocity over time, as seen from a fixed point.
- (u·∇)u: the change caused by the parcel **moving to a place where the velocity is different**. Even if the flow field doesn't change in time (steady flow), fluid moving along a streamline can still be turning and speeding up.

(u·∇)u is u times the derivative of u, so it is **quadratic in u**. This is where the **nonlinearity** of NS comes from, and it is the source of all the difficulty. Intuitively: the fluid "pushes itself along".

**Computing this term by hand for the rotating flow.** For u = (−y, x), the first component of (u·∇)u is u₁·∂u₁/∂x + u₂·∂u₁/∂y = (−y)·0 + x·(−1) = −x; the second component is (−y)·1 + x·0 = −y. So (u·∇)u = (−x, −y), **pointing toward the center, with magnitude r**. This is exactly the centripetal acceleration from high-school physics, v²/r = r²/r = r.

**First term on the right: viscosity νΔu.** Δ = ∂²/∂x² + ∂²/∂y² + ∂²/∂z², the same thing as on the right side of the heat equation. When neighboring layers of fluid move at different speeds (shear), they drag on each other and smooth out the velocity difference.

**Second term on the right: pressure −∇p.** It pushes from high pressure toward low pressure. In incompressible flow, pressure is "the force that adjusts itself automatically so that ∇·u = 0 holds at every moment", i.e. the Lagrange multiplier for the incompressibility constraint.

**Third term on the right: external force f.** For example gravity, a stirrer, or an electromagnetic force. **This term is the key to understanding OpenAI's result**; Section 6 is devoted to it.

**[Check 3]** For the rotating flow u = (−y, x), take ν > 0 and f = 0. (a) Compute Δu. (b) This flow is steady (∂u/∂t = 0), so the equation requires (u·∇)u = −∇p. Find the pressure p. Is the pressure higher at the center or at the edge?

### 2.4 Reynolds number: nonlinearity versus viscosity

Consider a flow with length scale L and speed U:
- the time for the nonlinear term to carry velocity across one length scale is about L/U;
- the time for viscosity to smooth out differences at this scale is about L²/ν.

Their ratio is the **Reynolds number** Re = UL/ν. Large Re: nonlinearity dominates (turbulence). Small Re: viscosity dominates (smooth, like honey).

Computed by script (water ν ≈ 1.0×10⁻⁶ m²/s, air ≈ 1.5×10⁻⁵ m²/s): water flowing at 1 m/s through a 0.1 m pipe has Re = 10⁵; air flowing at 30 m/s past a 4 m car has Re = 8×10⁶.

Keep this quantity in mind; Section 4 uses it: **the blowup question is whether, at smaller and smaller scales, the Reynolds number can go up instead of down.**

---

## 3. "Smooth solutions exist forever" versus "finite-time blowup"

### 3.1 First, an ODE toy: the equation is perfect, but the solution breaks

Compare two equations that look very similar, both with initial value y(0) = 1:

| t | Solution of y' = y: eᵗ | Solution of y' = y²: 1/(1−t) |
|---|---|---|
| 0.5 | 1.649 | 2 |
| 0.9 | 2.460 | 10 |
| 0.99 | 2.691 | 100 |

(Computed by script; integrating y' = y² numerically with RK4 up to t = 0.99 gives 100.0000000001, matching the exact solution.)

eᵗ is finite at every finite time; 1/(1−t) **becomes infinite at t = 1**. This is called **finite-time blowup**. The right-hand side y² could not be smoother; what breaks is the solution: "the bigger it is, the faster it grows", so the growth rate itself is growing.

### 3.2 Adding damping: who wins depends on the initial value

Now add a "viscosity-like" damping term: y' = y² − y. The substitution z = 1/y solves it exactly: z(t) = 1 + (z₀ − 1)eᵗ, and y blows up if and only if z hits 0.

| Initial value y₀ | Outcome (computed by script) |
|---|---|
| 0.5 | Decays, y(3) ≈ 0.047 |
| 1.0 | Stays put, = 1 forever (equilibrium) |
| 1.1 | Blows up, t* = ln 11 ≈ 2.398 |
| 2.0 | Blows up, t* = ln 2 ≈ 0.693 |

**For small initial values damping wins; for large ones nonlinearity wins.** The known theory of 3D NS has exactly this shape: Fefferman's statement says that in 3D "(A) and (B) hold provided the initial velocity u° satisfies a smallness condition", and that for large initial data, smooth solutions exist at least for a short time [0, T) [P]. Whether large initial data stays smooth forever is the Millennium Problem.

### 3.3 A PDE toy: the Burgers equation

Cut NS down to 1 dimension and drop the pressure: u_t + u·u_x = ν·u_xx. Initial value u = −sin x. **Without viscosity**, the slope at x = 0 satisfies (u_x)' = −(u_x)², which has the same form as y' = y², giving u_x(0, t) = −1/(1−t): at t = 1 the slope is infinite (a shock). **With viscosity**, the script simulates it with a spectral method, and the steepest slope is capped at about 1/(2ν): 3.7 for ν = 0.1 (1/(2ν) = 5), 48.4 for ν = 0.01 (50), 164.9 for ν = 0.003 (166.7). The smaller ν, the higher the cap, but it is always finite (1D viscous Burgers can be turned into the heat equation by the Cole–Hopf transformation, and it is rigorously proven not to blow up).

**The question for 3D NS is: can viscosity still cap things like this?** 3D has one extra mechanism: **vortex stretching**. A vortex tube that gets stretched longer and thinner spins faster, like a figure skater pulling in their arms (angular momentum r·u_θ is conserved: shrink the radius 10×, and the spin speed goes up 10×). This positive feedback does not exist in 1D or 2D.

### 3.4 Saying "blowup" precisely

"Smooth" means derivatives of all orders exist and are continuous (C^∞). **Global smooth solution**: smooth for all t ≥ 0 with bounded energy. **Finite-time blowup**: the solution is smooth on [0, T), but as t → T, the velocity or one of its derivatives → ∞ somewhere. Fefferman's statement records that for NS (ν > 0), at blowup **the velocity itself** must be unbounded [P], which is why OpenAI's theorem is stated as "lim sup ‖u(t)‖_∞ = ∞". Real water never has infinite velocity; the continuum model breaks down at molecular scales first. Blowup is a statement **about this mathematical model**.

---

## 4. Why 3D is so hard: energy and supercritical scaling

### 4.1 Energy: the only global ledger

With no external force, NS has a beautiful identity: the total kinetic energy E(t) = ½∫|u|² dx **can only decrease, never increase** (viscosity turns kinetic energy into heat). The nonlinear term (u·∇)u contributes exactly 0 to the total energy; it only **moves** energy between scales and never creates it.

So we have an upper bound valid for all time: E(t) ≤ E(0). The question is: **is this upper bound enough to prevent blowup?**

### 4.2 Scaling symmetry

NS has a symmetry: if u(x, t) is a solution, then for any λ > 0,

```
u_λ(x, t) = λ · u(λx, λ²t)
```

is also a solution (with pressure and external force transformed accordingly). λ > 1 means "shrink the same flow to 1/λ of its size, play it λ² times faster, and the flow speed becomes λ times larger".

| λ | Size | Time | Flow speed | 3D energy | 2D energy |
|---|---|---|---|---|---|
| 1 | 1 | 1 | ×1 | ×1 | ×1 |
| 10 | 1/10 | 1/100 | ×10 | ×0.1 | ×1 |
| 100 | 1/100 | 1/10⁴ | ×100 | ×0.01 | ×1 |
| 1000 | 1/1000 | 1/10⁶ | ×1000 | ×0.001 | ×1 |

Where the energy column comes from: take ∫|λu(λx)|² dx and set y = λx; in 3D, dx = dy/λ³, so the energy is multiplied by λ²/λ³ = 1/λ.

**[Check 4]** Compute the 2D energy factor the same way, and verify that it is 1.

**The 3D column is the key**: shrink a "blowup structure" 1000×, speed its flow up 1000×, and the energy it needs is only one thousandth of the original. The energy bound places almost no constraint on small scales. This is called **supercritical**. In 2D the energy does not change under scaling, which is called **critical**; that is why 2D NS was proven long ago to be globally smooth (Ladyzhenskaya; see Fefferman's statement [P]).

### 4.3 Saying it again with the Reynolds number

Fix the total energy E = 1 and the viscosity ν = 1. For a blob of flow of size L, how large can its speed be?

- 3D: energy ≈ U²L³ ≤ 1, so U ≤ L^(−3/2), and the Reynolds number Re = UL/ν ≤ L^(−1/2).
- 2D: energy ≈ U²L² ≤ 1, so U ≤ 1/L, and Re ≤ 1.

| Size L | Max Re allowed in 3D | Max Re allowed in 2D |
|---|---|---|
| 1 | 1 | 1 |
| 10⁻² | 10 | 1 |
| 10⁻⁶ | 1,000 | 1 |
| 10⁻⁸ | 10,000 | 1 |

(Computed by script.)

2D: energy holds the Reynolds number at every scale below 1, so viscosity always has what it takes to win. 3D: the smaller the scale, the larger the Reynolds number the energy allows, so **viscosity might lose at small scales**. Energy neither rules out blowup nor proves it; it is simply "not enough". This is the core of the 3D NS problem.

### 4.4 Tao's "supercriticality barrier" (2016)

Tao (JAMS 29, 2016; arXiv:1402.0290) constructed an "averaged NS": it keeps the energy identity and the scaling, replaces only the nonlinear term with an averaged version, and he proved that it **does** blow up. Consequence: an argument that uses only "energy + generic harmonic-analysis estimates" cannot prove (A)/(B); it must use the fine structure of the real nonlinear term. He also proposed a **program**: build "logic gates" out of a real fluid, so that the fluid, like a self-replicating machine, passes its energy again and again to smaller, faster copies of itself, producing blowup in **unforced** NS. This program has not been carried out to this day.

---

## 5. 90 years of partial results

| Year | Result | Significance |
|---|---|---|
| 1934 | **Leray** (Acta Math. 63): every finite-energy initial value has a global **weak solution** | Weak solutions satisfy the equation only "in an integral-average sense" and allow singularities; smoothness and uniqueness are unknown |
| 1982 | **Caffarelli–Kohn–Nirenberg** (CPAM 35): the singular set has parabolic 1-dimensional Hausdorff measure 0 | Singularities "cannot form a curve in space-time" (Fefferman's wording [P]), but isolated points are not ruled out |
| 2003 | **Escauriaza–Seregin–Šverák**: if the L³ norm stays bounded, there is no blowup | Blowup must make the L³ norm diverge |
| 2016 | **Tao**: averaged NS blows up | See Section 4.4 |
| 2019 | **Buckmaster–Vicol** (Annals 189): a class of weak solutions is non-unique | Weak solutions are too "soft" |
| 2014 / 2022 | **Luo–Hou** numerics (PNAS); **Chen–Hou** computer-assisted proof (arXiv:2210.07191): 3D axisymmetric Euler **with a boundary** blows up from smooth initial data | Needs a solid wall; not in all of space ℝ³ |
| 2021 | **Elgindi** (Annals 194): Euler on ℝ³ blows up for C^{1,α} initial data | The initial data is not C^∞ |
| 2023 on | **Córdoba–Martínez-Zoroa** (arXiv:2309.08495 and others): forced 3D Euler blows up, with a force of limited smoothness | Pioneers of the "forcing route": finer and finer vortex layers amplified stage by stage |
| 2025 | **DeepMind et al.** (arXiv:2509.14185): neural networks find **unstable** self-similar singularities for the Boussinesq, IPM and other equations, with accuracy close to machine precision | Paves the way for computer-assisted proofs in the boundaryless case |
| 2026-08 | **Buckmaster–Alpöge**: IPM, Boussinesq and 3D Euler blow up under **smooth forcing**, verified in Lean; made public September 7 | Pushes the route in the previous row to smooth forcing [P, Buckmaster statement] |

The pattern that keeps appearing in this table: **Euler (no viscosity) blows up more easily than NS; having a boundary, lower smoothness, or forcing is each easier than "all of space, C^∞, no forcing".** Every time one condition is relaxed, someone manages to produce blowup. Millennium Problem (A)/(B) is the version with no condition relaxed.

---

## 6. The Clay problem statement: four branches, and the role of the force f

### 6.1 The official text [P]

Fefferman's statement (https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf) first sets out "physically reasonable" conditions: all derivatives of the initial data and the external force decay rapidly (conditions 4, 5), the solution is C^∞ on ℝ³ × [0, ∞) (6), and the energy is uniformly bounded (7); the periodic case uses conditions 8–11. Then:

> "To give reasonable leeway to solvers while retaining the heart of the problem, we ask for a proof of one of the following four statements."

| Branch | Domain | External force | What must be proven |
|---|---|---|---|
| **(A)** | ℝ³ | f ≡ 0 | For **every** smooth decaying initial value → there is a global smooth solution with bounded energy |
| **(B)** | Periodic torus ℝ³/ℤ³ | f ≡ 0 | Same, periodic version |
| **(C)** | ℝ³ | **There exists** a smooth decaying f | **There exist** some initial value and force for which no smooth, bounded-energy global solution **exists** |
| **(D)** | ℝ³/ℤ³ | **There exists** a smooth periodic f | Same, periodic version |

Two points. (A)/(B) say "good for all initial values", while (C)/(D) say "there is one bad example": **opposite directions**. (A)/(B) require f ≡ 0, while (C)/(D) let you **choose the force yourself**, as long as it is smooth and decaying. Fefferman also writes that the corresponding problem for the Euler equations (ν = 0) is "also open and very important", but it is not on the prize list [P].

### 6.2 Why "you can choose the force" changes the shape of the problem

Section 2 of the OpenAI paper says this itself [P]:

> "For any incompressible flow u and pressure p, we can always define the external force f to be the residual in (1.1). The Navier–Stokes equations then hold by construction. The challenge is to choose a flow that blows up while this residual remains smooth."

In plain words: draw any incompressible flow that blows up, plug it into NS, subtract the right side from the left, and let f make up whatever the difference is. The equation then holds **automatically**. There is only one difficulty: **the force making up the difference must stay smooth**, and cannot break even at the blowup time.

An ODE toy makes the difficulty clear:

- **Linear equation y' = −y + g(t)**: to make y = 1/(1−t) blow up, the needed force is g = y' + y = 1/(1−t)² + 1/(1−t), which itself blows up and is not smooth. In fact, a linear equation with a smooth force **never** blows up.
- **Nonlinear equation y' = y² + g(t)**: for the same y = 1/(1−t), g = y' − y² = 1/(1−t)² − 1/(1−t)² = **0**. The force is 0, perfectly smooth.

So blowup must rely on the nonlinear term to cancel the singular part **by itself**, with the force only making up a smooth remainder. In NS, all divergent parts must cancel, to derivatives of every order; this is what those 166 pages are doing.

**[Check 5]** For y' = −y + g(t), if g is smooth and bounded on [0, 2] (say |g| ≤ 1) and y(0) = 0, can y(t) blow up at t = 1? Hint: compare with y' ≤ −y + 1.

### 6.3 So is (C) easier than (A)?

In 2000 Clay put (C) side by side with (A), considering all four branches to be "retaining the heart of the problem". But the "forcing route" opened by Córdoba–Martínez-Zoroa from 2023 on showed that **the force can do a great deal of "engineering" work**: inject energy where and when it is needed, and "plant" perturbations. In his statement Buckmaster says this route "is the route Luis and Diego opened", and calls the next goal "a path to unforced Euler" [P]. Even the people pushing this route see "unforced" as the deeper problem.

A secondhand summary: the forcing route is "a route the written problem permits but that most working mathematicians exclude from the question they care about" [R, Implicator]. ⚠ This is a journalist's summary, not a systematic survey of analysts.

---

## 7. What OpenAI claims

### 7.1 The main theorem [P]

The paper is *Finite time blowup for Navier–Stokes*, authored by "OpenAI", 166 pages, PDF generated 2026-09-08 12:06 PDT (https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf). Abstract:

> "For every positive viscosity, we construct a solution of the three-dimensional incompressible Navier–Stokes equations that starts from rest and develops unbounded velocity in finite time while maintaining uniformly bounded kinetic energy."

What Theorem 1.1 says: for every ν > 0, there exist
- an external force f ∈ C_c^∞(ℝ³ × (0, ∞)): smooth, and **nonzero only within a bounded region in both space and time** ("compactly supported");
- velocity and pressure u, p, smooth on ℝ³ × [0, 1), with **initial value u(·, 0) = 0** (starting from rest), and confined at all times to a fixed bounded region K;
- with energy sup‖u(t)‖_{L²} < ∞ and velocity lim sup_{t↑1} ‖u(t)‖_{L∞} = ∞.

The paper's own words: "This establishes alternative (C) in the Millennium problem statement … Compact support also yields the corresponding construction on T³ … establishing alternative (D)" (Corollary 10.6).

**Arbitrary viscosity, by hand.** The paper first builds the construction at ν = 1, then extends to any ν by the scaling u_ν(x, t) = √ν · u(x/√ν, t). The blowup time does not change.

**[Check 6]** Verify: substituting u_ν = √ν · u(x/√ν, t), each of the three terms ∂u_ν/∂t, (u_ν·∇)u_ν and νΔu_ν equals √ν times the corresponding original term.

### 7.2 Intuition for the mechanism (from reading Section 2 of the paper; a simplified version)

1. **A vortex column that gets thinner and faster.** In the vortex core near the origin, fluid spirals inward and flows out up and down along the axis. Conservation of angular momentum makes the inflowing fluid spin faster; incompressibility makes the incoming fluid leave along the axis, so the inward flow can keep going.
2. **Self-similar contraction.** Write τ = 1 − t. The core radius ℓ_r ~ τ^(1/2), the height ℓ_z ~ τ^(1/2−h), where h is a fixed small number, 0 < h < 1/100. The vortex column gets thinner and relatively longer.
3. **The problem**: the transition annulus outside the core leaves a "residual", and the force needed to make it up diverges as t → 1.
4. **The fix: add oscillating pulses in the annulus.** The pulses have zero average velocity, but their **quadratic products** (momentum flux) do not average to zero. Two families of pulses are carefully arranged so that the nonlinear flux **exactly cancels** the divergent part of the residual. Each pulse is "planted" by an exponentially small force, and then grows by feeding on the background shear.
5. **Outside**: a purely rotating flow that satisfies the heat equation and needs no force; then smoothly cut off to a bounded region.

This is exactly Section 6.2's "the nonlinear term cancels the singular part by itself", except that it must be done in 3D for derivatives of every order.

### 7.3 A feel for the numbers: how the vortex core shrinks

Take h = 0.005 (the paper only requires 0 < h < 1/100; I chose this value for illustration), and compute with the scaling laws the paper gives (computed by script, ν = 1, constant factors set to 1):

| τ = 1 − t | Core radius ℓ_r | Core height ℓ_z | Speed ~ τ^(−1/2−h) | Core energy ~ τ^(1/2−3h) | Swirl Reynolds number τ^(−h) |
|---|---|---|---|---|---|
| 10⁻² | 0.1 | 0.102 | 10.2 | 0.107 | 1.023 |
| 10⁻⁴ | 0.01 | 0.0105 | 104.7 | 0.0115 | 1.047 |
| 10⁻⁸ | 10⁻⁴ | 1.10×10⁻⁴ | 1.10×10⁴ | 1.3×10⁻⁴ | 1.096 |
| 10⁻¹² | 10⁻⁶ | 1.15×10⁻⁶ | 1.15×10⁶ | 1.5×10⁻⁶ | 1.148 |

- **Speed → ∞, core energy → 0**: this is exactly the supercriticality from Section 4, reaching ever larger speeds at small scales with ever less energy.
- The speed carries an extra factor τ^(−h) beyond pure scaling τ^(−1/2); this is the **swirl Reynolds number**. It goes to infinity, but extremely slowly: as τ goes from 10⁻² to 10⁻¹², it only rises from 1.02 to 1.15. The blowup is achieved right at the edge, "just barely beyond critical".
- Consistent with known theorems: the singularity is **a single point** (the origin, t = 1), which does not violate CKN; the cube of the L³ norm ~ τ^(−4h), about 1.74 at τ = 10⁻¹², and it is diverging, which fits the necessary condition from ESS (⚠ ESS is about the unforced case; here it serves only as an intuition check).

### 7.4 The Euler result released at the same time

The same Lean repository also formalizes a second paper, *Finite time blowup for the Euler equation* (57 pages, https://cdn.openai.com/pdf/315b36cd-ec98-4023-8342-93345194ece1/euler.pdf) [P]:

> "We exhibit finite-time blowup for the three-dimensional incompressible, unforced Euler equations from smooth, compactly supported, divergence-free initial data."

Compare with Section 5: Chen–Hou need a boundary, Elgindi's initial data is only C^{1,α}, and Córdoba–Martínez-Zoroa and Buckmaster–Alpöge need a force. This result removes all of those relaxations; the only remaining difference from the Millennium Problem is "no viscosity". Fefferman says the corresponding problem for Euler is "also open and very important" [P]. My judgment (speculation): in terms of how close it is to the question people actually care about, it may carry more weight than the forced NS result. ⚠ I found no named expert's technical assessment of this paper.

**Scale** [R]: about 10,000 concurrent agents, 88 hours; Wikipedia cites 2.7 million messages and 130 billion output tokens, while other reports say "nearly 5 million" ⚠. `formalization.yaml` records the model as "GPT-6 Astra" and the framework as Codex [P].

---

## 8. How far it has been verified

### 8.1 The Lean statement: OpenAI did not write it

The statement file `ComparatorChallenges/NavierStokes.lean` says at the top that it is copied from **Google DeepMind's Formal Conjectures project** (commit `8bf45ed`), with only the imports, namespace and notation changed [P]. If the solver writes the statement itself, it can quietly loosen conditions; here it comes from a third party. ⚠ I did not diff it line by line against upstream.

The statement of branch (C):

```lean
theorem navier_stokes_breakdown_R3 (nu : ℝ) (hnu : nu > 0) :
    ∃ (u₀ : ℝ³ → ℝ³) (f : ℝ³ → ℝ → ℝ³),
    InitialVelocityConditionDecay u₀ ∧ ForceConditionDecay f ∧
    ¬ (∃ v p, NavierStokesExistenceAndSmoothnessRn nu u₀ f v p)
```

Word-by-word translation:
- `(nu : ℝ) (hnu : nu > 0)`: for any positive viscosity ν,
- `∃ (u₀ …) (f …)`: there exist an initial value u₀ and a force f,
- `InitialVelocityConditionDecay u₀`: u₀ is smooth, divergence-free, and all its derivatives decay rapidly (Clay condition 4),
- `ForceConditionDecay f`: f is smooth, and all its space-time derivatives are ≤ C/(1 + |x| + t)^K (condition 5),
- `¬ (∃ v p, …)`: such that there **do not exist** v, p satisfying all of NS (1), zero divergence (2), the initial value (3), C^∞ (6), and uniformly bounded energy (7).

I checked it item by item against the Clay text: (4)–(7) are all there; the periodic version (D) includes (8)–(11), and, as Clay's erratum requires, the pressure is also periodic [P]. **The structure of the statement matches Clay's (C)/(D).** Note that (C) asks that "**no** global smooth solution exists at all", not just "the solution I built blows up"; this requires uniqueness of smooth solutions (the "Consequently…" sentence in Theorem 1.1), and that is proven in Lean too.

### 8.2 The proof itself

- Repository `openai/NavierStokesAndEuler` (snapshot `f9e8bc5`, 2026-09-10): **2,659 `.lean` files** (NS 816, Euler 1,839) [P], about 640,000 lines (a count from the author's research notes).
- `formalization.yaml`: sorry count 0; uses only the three standard axioms `propext`, `Classical.choice`, `Quot.sound`; Comparator has `enable_nanoda` turned on, i.e. a second, independently implemented kernel also checks it [P]. The review status reads **"self-assessed"**.
- ⚠ I did not run `lake build` or Comparator, and found no public report of a third party running the NS Comparator successfully (the quasi-Riemann hypothesis had Goldblatt's independent recheck).

### 8.3 Human experts and institutions

- **Clay** (09-11) [R]: reportedly said "the Navier–Stokes problem has apparently been settled", and also "The process is deliberately unhurried, but we will provide updates". The problem page on Clay's website is still marked "Active" as of today (I checked on 10-08).
- **Gómez-Serrano** (NPR, 09-22) [R]: "The paper is not written for humans … as of today, the paper doesn't teach us much."
- **Fefferman** [R]: "The heroes of the story … are Córdoba and Martínez-Zoroa." ⚠ Original source not found.
- ⚠ **As of 2026-10-08, no human expert has publicly said they have read and verified the 166-page paper**, and there are no reports of journal submission.

### 8.4 The priority dispute (in brief)

- **Buckmaster's statement** (https://cims.nyu.edu/~tristanb/statement.pdf) [P]: he and Alpöge obtained Boussinesq and 3D Euler blowup under smooth forcing on August 15, verified it in Lean on August 22, and made it public on September 7 (dates per Wikipedia [R]). They also used LLMs heavily (Claude, Codex). He credits the route to Córdoba and Martínez-Zoroa. About OpenAI, he recounts that in a call on September 6, "Eventually it was agreed that [the first prompt] had been sent in the past few days, after information about our work had reached OpenAI", and also writes "I am not accusing anyone of anything."
- **OpenAI's response** [R]: "it is impossible for Dr. Buckmaster's Codex prompts over the last two months to have influenced the system in any way".
- **Citations** [P]: the PDF I read (generated 09-08 12:06 PDT) **already cites** three works by Córdoba–Martínez-Zoroa [6–8]; it **does not cite** Buckmaster–Alpöge.

### 8.5 Remaining risks

1. **Mathlib definitions**: the Laplacian, gradient, etc. come from Mathlib, and "junk value conventions" could make the statement drift from its intended meaning; but the statement requires C^∞ everywhere, so the effect is small.
2. **Toolchain**: Lean 4.34.0-rc2 is a pre-release version [P]; the nanoda dual-kernel check lowers the risk.
3. **Human understanding**: nobody can say whether this method extends to the unforced case.

---

## 9. What it means if true (and what it doesn't)

### 9.1 By Clay's text, does this count as "solving the Millennium Problem"?

The answer has three layers.

**Layer one: the problem statement. Yes.** The official text says "we ask for a proof of one of the following four statements", and (C) is one of them [P]. Rule 5(b) of the prize rules also states: "In the case of the P versus NP Problem and the Navier-Stokes Problem, a resolution in either direction will be evaluated by the standard evaluation procedure" [P, https://www.claymath.org/wp-content/uploads/2022/03/millennium_prize_rules_0.pdf]. Both directions are equally valid.

**Layer two: the prize procedure. Still a long way off.** Rule 4 requires all of the following [P]:
- (a) publication in a "qualifying outlet" (no reports of submission so far ⚠);
- (b) at least **2 years** have passed since publication;
- (c) "general acceptance" in the global mathematics community, as judged by CMI;
- (d) a satisfactory answer to the question posed in the official problem statement.

After that, CMI must also form a committee of at least 3 people to review it (Rule 7). Rule 8(b): CMI will "pay special attention to the question of whether a Prize solution depends crucially on insights published prior to the solution", and may add earlier contributors to the list of prizewinners; this is directly relevant to Córdoba–Martínez-Zoroa and Buckmaster–Alpöge. Rule 8(c): if no conclusion can be reached on correctness or **attribution**, the prize may not be awarded. Separately, OpenAI has reportedly said it will not claim the prize [R]. Speculation: even if it is published next year, with "2 years after publication", a conclusion would come around 2029 at the earliest.

**Layer three: the question mathematicians care about. Most would say no.** "Does a fluid blow up on its own?" is still completely open. OpenAI's result does not answer the unforced case, and does not carry out Tao's program.

**Be careful with the "specification gaming" framing.** §11.1 of the deck compares this to specification gaming in AI. But Fefferman included (C) **on purpose** in 2000, considering that it retains the heart of the problem. A more accurate way to put it: **the problem setters thought at the time that (C) was as hard as (A); progress since 2023 shows that the forcing route is easier than expected.** The gap between the text and the intent became visible in hindsight; it is not a case of the solver exploiting a loophole the setters never thought of.

### 9.2 For mathematics, physics and AI

1. **Mathematics**: if it holds, this is the first NS blowup in the setting of smooth forcing, all of space, and C^∞: viscosity is not all-powerful. The unforced Euler blowup released at the same time (Section 7.4), if it holds, may be the bigger news. Methodologically, "synthesizing" the needed stress from the quadratic flux of oscillating pulses is related to convex integration for Euler (Daneri–Székelyhidi), as the paper itself says [P].
2. **Physics and engineering**: almost no direct impact. NS solvers never rely on global regularity theorems; in real fluids, molecular scales make the continuum model fail before a singularity is reached. The conclusion is "**the model itself** breaks under an artificially designed force", not "real water can reach infinite velocity".
3. **AI**: three independent gates: passing formalization ≠ a faithful statement ≠ acceptance by mathematicians. Here the second gate is fairly reliable because a third-party statement was used; the third gate is far from passed. Buckmaster says LLMs mean one mathematician plus a model "can now do all this work in a month", and calls it "a Deep Blue-Kasparov moment" [P]. When an AI lab can quickly pour large amounts of compute into a direction after hearing it is making progress, how norms of priority and attribution should adapt is a real question.

---

## 10. Self-test

1. In one sentence: why does y' = y² blow up in finite time while y' = y does not? (Section 3.1)
2. Which term in the NS equations is nonlinear? What is its physical meaning? (Section 2.3)
3. Why is energy for 3D NS called "supercritical"? Explain using the numbers for scaling λ = 1000. (Sections 4.2–4.3)
4. How do Clay's (A) and (C) differ in "external force" and in "quantifier (for all / there exists)"? (Section 6.1)
5. Why does "you can choose the force yourself" not make the problem trivial? What is the key difficulty? (Section 6.2)
6. Who wrote OpenAI's Lean problem statement? Why does that matter? (Section 8.1)
7. Under Clay's rules, what steps at minimum remain between now and a possible award? (Section 9.1)

---

## Appendix: answers to the checks

- **Check 1**: `[0, 0.0625, 0.25, 0.375, 0.25, 0.0625, 0]`, sum 1 (checked by script). For example, the middle: 0.5 + 0.25·(0.25 − 1 + 0.25) = 0.375.
- **Check 2**: ∇·(−y, x) = ∂(−y)/∂x + ∂x/∂y = 0 + 0 = 0, incompressible. ∇·(x, y) = 1 + 1 = 2 ≠ 0: w is a flow "spraying" outward from the origin; every small region has net outflow, and volume is expanding.
- **Check 3**: (a) Each component of u = (−y, x) is a linear function, so all second derivatives are 0 and Δu = 0: rigid rotation has no shear, so viscosity does nothing. (b) From Section 2.3, (u·∇)u = (−x, −y), so ∇p = (x, y) and p = (x² + y²)/2 + constant. **Higher at the edge, lower at the center**: the pressure difference pushes inward from outside, supplying the centripetal force. When the OpenAI paper describes the vortex core as "Pressure decreases toward the axis, supplying the leading centripetal force", this is what it means.
- **Check 4**: In 2D, dx = dy/λ², so the energy factor is λ²/λ² = 1.
- **Check 5**: No. From y' ≤ −y + 1 and y(0) = 0 you can derive y ≤ 1 − e^(−t) < 1; likewise y ≥ −1. A linear equation with a bounded force has a solution that stays bounded.
- **Check 6**: ∂u_ν/∂t = √ν·∂u/∂t. (u_ν·∇)u_ν: the velocity factors give √ν × √ν, and the derivative ∇ acting on x/√ν brings 1/√ν, for √ν in total. νΔu_ν: ν × √ν × (1/√ν)² = √ν. All three terms agree.

## Appendix: Glossary

| Term | One-line explanation |
|---|---|
| ODE / PDE | The unknown is a single number changing over time / a whole field |
| Heat equation | ∂u/∂t = kΔu; each point moves toward the average of its neighbors, which only makes things smoother |
| Divergence ∇·u | Net outflow from a small region; = 0 means incompressible |
| Material derivative | ∂u/∂t + (u·∇)u, the acceleration of a small parcel of fluid itself |
| Viscosity νΔu | Neighboring fluid layers drag on each other; mathematically, the heat equation for the velocity |
| Reynolds number Re | UL/ν, the ratio of the strength of nonlinearity to viscosity |
| Weak solution | A solution that satisfies the equation only in an integral-average sense, allowing singularities (Leray 1934) |
| Scaling symmetry | u_λ = λu(λx, λ²t) is still a solution |
| Supercritical | The conserved quantity (energy) controls less and less at small scales |
| Vortex stretching | A vortex tube stretched longer and thinner spins faster; only in 3D |
| Euler equations | NS with ν = 0, an inviscid fluid |
| Clay (A)–(D) | The four alternative statements of the Millennium Problem; proving any one is enough |

## Appendix: Further reading

- **The official Clay problem statement** (Fefferman, 5 pages, strongly recommended to read in full): https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf
- **Clay prize rules**: https://www.claymath.org/wp-content/uploads/2022/03/millennium_prize_rules_0.pdf
- **OpenAI NS paper**: https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf (read Sections 1–2 first, about 6 pages, needing almost no PDE background)
- **OpenAI Euler paper**: https://cdn.openai.com/pdf/315b36cd-ec98-4023-8342-93345194ece1/euler.pdf
- **Lean repository**: https://github.com/openai/NavierStokesAndEuler ; upstream problem statement: https://github.com/google-deepmind/formal-conjectures/blob/main/FormalConjectures/Millenium/NavierStokes.lean
- **Buckmaster's statement**: https://cims.nyu.edu/~tristanb/statement.pdf
- **Terence Tao**, arXiv:1402.0290 (JAMS 2016): the introduction lays out the "supercriticality barrier" clearly; more accessible is his blog post *Why global regularity for Navier-Stokes is hard* (2007).
- **DeepMind et al.**, *Discovery of Unstable Singularities*, arXiv:2509.14185
- **Chen & Hou**, *Stable nearly self-similar blowup of the 2D Boussinesq and 3D Euler equations with smooth data I: Analysis*, arXiv:2210.07191
- **Córdoba & Martínez-Zoroa**, *Blow-up for the incompressible 3D-Euler equations with uniform C^{1,1/2−ε} ∩ L² force*, arXiv:2309.08495
- **Bertozzi & Majda**, *Vorticity and Incompressible Flow* (Cambridge, 2002): the textbook recommended in Fefferman's problem statement.
- Secondhand reporting (not checked word for word): Quanta 2026-09-08 https://www.quantamagazine.org/ai-has-solved-one-of-maths-1-million-millennium-prize-problems-20260908/ ; Wikipedia "Navier–Stokes priority controversy" https://en.wikipedia.org/wiki/Navier%E2%80%93Stokes_priority_controversy ; paraphrase of Clay's 09-11 statement https://the-decoder.com/clay-mathematics-institute-says-the-navier-stokes-millennium-prize-problem-has-apparently-been-settled/ ; Implicator https://www.implicator.ai/clay-institute-navier-stokes-openai-proof-claim/
