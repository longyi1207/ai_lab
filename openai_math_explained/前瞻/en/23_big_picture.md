# The big picture: how the world changes if AI solves math

> This section pulls §17–§22 together into one picture and answers the question posed at the start of Part II: **if AI solves math at scale, or AI's other capabilities break through as well, what happens to physics, biology, computing, AI itself and society? Which effects are truly far-reaching?**
> The facts and numbers in this section all come from earlier sections, with sources in the source list at the end of each; the rankings, generalizations and timelines here are my own synthesis and are tagged [speculation]. All timing judgments use the central scenario of the three curves in §17.4.

## 23.0 The bottom line

1. **The impact of "math being solved" falls into three tiers, and they differ enormously.**
   - **Tier 1: fields where the math itself is the product** (cryptography, formal verification, algorithms, mechanism design, part of mathematical physics). The impact is direct and fast, visible by 2027–2028.
   - **Tier 2: fields where math is just one link in the pipeline** (physics, chemistry, materials, climate, fusion). Math acts mainly through **algorithms and numerical methods**, constrained by compute, experiments and the pace of hardware; the impact lands in 2028–2035.
   - **Tier 3: fields where math is barely a bottleneck** (most of biomedicine, neuroscience, macroeconomics, governance). What matters here are AI's **other capabilities** (coding agents, simulation, automated experiments, literature matching), and they will be slowed by experimental cycles and institutions; the impact comes in the 2030s.
2. **The most far-reaching impact is not any single theorem, but the structural change to the whole knowledge-production system once "proofs become a cheap commodity".** Across six fields we see the same phenomenon: making things got cheap, and **judging whether they are right, whether they are worth it, and what to ask** became the bottleneck.
3. **How fast AI accelerates a field depends on how fast that field's "referee" is.** Lean checks a proof in minutes and a weather forecast can be checked the next day, so AI is already having an effect in both; materials need synthesis and drugs need clinical trials, so their referees work in months and years; quantum gravity has no referee at all.
4. **AI is building "oracles" for science, not "theories".** Models that can predict but not explain are appearing in biology, physics and math at the same time. This is the same problem mechanistic interpretability faces.
5. **The exponential curves of AI capability will run into the linear time constants of the physical world and of institutions.** Progress in the digital world (software, math, AI itself) and in the physical world (drugs, materials, energy, hardware) will pull further and further apart.
6. **Verifiability will become the scarcest and most powerful resource.** Whoever holds the verifiers, signing keys and release channels decides how AI output enters society.
7. **2026–2029 is likely to be a fragile transition period of "fast offense, slow defense"**: finding vulnerabilities is fast, patching them is slow; discovering attacks is fast, migrating standards is slow; generating claims is fast, checking them is slow; capability grows fast, legislation moves slowly.
8. **For AI safety, all of this converges on one conclusion**: when proofs, experiments and even alignment research itself can be automated, safety depends on three things: **whether statements and specs are faithful**, **whether the verifiers themselves can be trusted**, and **who judges fuzzy tasks**. None of the three has mature methods yet.

## 23.1 A direct answer: can breakthroughs in math bring breakthroughs in physics, biology and computing?

Your intuition is right, but it needs to be unpacked. Math enters the real world mainly through five channels, and their strength varies a lot:

| Channel | Mechanism | Examples | Strength |
|---|---|---|---|
| **1. The theorem itself is the product** | A proof directly decides whether a system works and whether it is secure | Security reductions for, or breaks of, cryptographic schemes (§18); software with proofs (§18); incentive compatibility of mechanisms (§22) | **Strong, fast** |
| **2. Math → algorithms → computation** | New math becomes new algorithms that make previously intractable things computable | DFT functionals and molecular simulation (§19, §20); quantum error-correcting codes pulling Q-day earlier (§18); SAT solvers making the spectrum auction feasible (§22) | **Strong, but limited by compute and data** |
| **3. "Impossibility" theorems change direction** | Proving that a path is a dead end turns a whole field around | A universal DFT functional cannot be computed efficiently (§19); text watermarks cannot be made reliable (§22); undetectable backdoors exist (§21) | **Medium; deep impact but not conspicuous** |
| **4. Connecting existing math to new problems** | The math has long existed; what's missing is that "the people who need it know it exists" | The Radon transform behind CT scans (around since 1917); Gauss's FFT from 1805; LDPC codes, forgotten for 34 years (§17) | **Possibly underrated** |
| **5. Model health checks** | Proving that what physicists have long believed really holds | Navier–Stokes (§11), Vlasov–Maxwell (§12), Anderson localization and others (§19) | **Weak: raises certainty, barely changes experiments or engineering** |

**Three key points:**

- **Most of OpenAI's 719 papers belong to channel 5 and to "inventory" math.** Going by the historical pattern (§17.1), math done for its own sake takes 50–200 years to find applications, while math done for engineering problems takes only 2–15 years. So the real-world impact of this batch of results will be measured in decades, unless AI also speeds up the "matching" (channel 4). [speculation]
- **Channel 2 is the main entry point into physics, chemistry and biology, and it depends more on AI's other capabilities than on its ability to prove.** As of 2026, every confirmed AI-for-science speedup (weather forecasting, protein structure) came through this channel; none came from proofs (§17.3).
- **Think in terms of Amdahl's law**: in drug development, making "theory" infinitely fast raises overall speed by only about 5% (the back-of-envelope calculation in §17.2). The smaller the share of math in a field, the less acceleration "solving math" brings, however big the breakthrough.

**One summary table: what blocks each field, and how much AI can help** (see §17.7 and the individual sections for details)

| Field | Is math the bottleneck? | The real bottleneck | Most likely AI lever | Central timing |
|---|---|---|---|---|
| Cryptography and security (§18) | **Yes** | Proofs + standards migration + patching speed | AI math (analysis, proofs) + AI coding (finding vulnerabilities, writing verification code) | 2027–2029 |
| Quantum computing (§18) | Partly | Hardware | Resource estimates and error-correcting codes (type A); new algorithms (type B) | Q-day 2033–2036 |
| Chemistry and materials (§19) | Partly (algorithms) | Computational accuracy + synthesis throughput | ML functionals and force fields; autonomous labs | 2028–2032 |
| Fusion and energy (§19) | Rarely | Hardware cadence, materials irradiation | Control, design optimization | 2030s |
| Proteins and molecules (§20) | **Yes** (a sampling problem) | Sampling algorithms + validation data | Generative models that sample directly from the Boltzmann distribution | 2029 |
| Cells, development, aging (§20) | No | Measurement, data, concepts | Automated experiments, oracle-style models | 2030–2035 |
| Drugs and the clinic (§20) | No | Target causality + 8–13-year pipeline + regulation | Target selection, patient stratification | 2035 |
| Neuroscience (§20) | Partly (missing theory) | Measurement + concepts | Connectome reconstruction, digital twins | 2033 |
| AI theory and alignment (§21) | Yes, but mostly type B | **Definitions** (complexity, capability, explanation, corrigibility) | Automated controlled experiments; bulk sweeps of type A theorems | 2027–2030 |
| Economics and governance (§22) | In a few places (ZK, social choice) | Institutions, adoption, legitimacy | Mechanism solving, verifiable agreements | 2029 and later |

## 23.2 Five cross-field patterns

Each of these five patterns showed up independently in every one of §17–§22. They are the most important content of this Part.

### 23.2.1 Proofs are cheap, statements are expensive

AI is making "given a problem, find the answer" cheaper and cheaper, but "is the problem itself stated correctly?" has not gotten any cheaper.

| Field | The cheap part | The expensive part |
|---|---|---|
| Math (§3, §16) | Writing Lean proofs | Checking whether the Lean statement is faithful to the paper |
| Software (§18) | Writing proofs | Getting the spec right, delimiting the trusted computing base (TCB) |
| Cryptography (§18) | Improving known attacks | What the security model leaves out (timing, implementation) |
| Materials (§19) | Generating candidates (GNoME predicted about 380,000 stable crystals) | Confirming that candidates are real and useful (only 736 synthesized externally) |
| Biology (§20) | Designing proteins, training predictive models | Knowing what to measure, and whether evaluation metrics are valid |
| AI theory (§21) | Proving theorems about solvable models | Defining "complexity", "capability", "explanation", "corrigibility" |
| Governance (§22) | Producing papers, content, transactions | Checking, signing, legitimacy |

**Implication**: The scarcest capability in the future will be turning vague intent into precise statements, and checking whether those statements have been quietly weakened. In math this is called "statement faithfulness", in software "the spec", in AI "the alignment target"; **at bottom it is the same capability**.

### 23.2.2 The speed of the referee sets the speed of acceleration

| Field | Referee | One feedback loop | AI acceleration |
|---|---|---|---|
| Formal math | Lean kernel | Minutes | Already happened (2026) |
| Weather | Next day's observations | Days | Already happened (ECMWF operational in 2025) |
| Software security | Tests, fuzzing, proof checking | Minutes to days | Already happened (finding vulnerabilities); patching can't keep up |
| Electronic structure | High-accuracy calculations | Hours to days | Fast |
| Protein design | Wet lab | Weeks | Medium, limited by the cost of experiments |
| Materials, superconductors | Synthesis + characterization | Weeks to months | Slow |
| Clinical medicine | Clinical trials | Years | Very slow (a single Phase III takes 5–8 years) |
| Climate | Observations | A decade | Very slow |
| Quantum gravity | None | ∞ | Only on subproblems |

**Implication**: If you want AI to accelerate a field, the most effective investment is often not a stronger model but a **faster referee**: autonomous labs, smaller and faster Phase IIa trials, better evaluation metrics, automated connectome proofreading.

### 23.2.3 Prediction succeeds, understanding fails

In several fields AI has produced models that "can answer what-if, but can't say why":

- Biology (§20): generative protein design bypasses physics-based scoring functions; virtual cell models learn "perturbation → expression" without building mechanisms; AlphaGenome learns "sequence → regulatory signals" without building gene regulatory networks; the digital twin of mouse visual cortex can predict the responses of more than 10,000 neurons, but is as much a black box as the brain itself.
- Physics (§19): neural network functionals fit energies more and more accurately, while the densities may drift further and further off.
- Math (§3, §16): 26 million lines of Lean proofs, almost none of which anyone has read.
- A precedent from neuroscience: the complete connectome of the nematode's 302 neurons has existed since 1986, and forty years later we still cannot predict its behavior (§20).

**Implication**: Scientific output may shift from "theories" to "validated oracles". Capability will grow while understanding may stall. This is exactly the predicament mechanistic interpretability faces with AI, and biology already has more, and more realistic, examples of it. The two fields should learn from each other; at present they almost never do. [speculation]

### 23.2.4 Exponential curves hit linear time constants

| Curve or constant | Speed |
|---|---|
| METR task length | Doubles every 129 days (about ×7 per year) |
| Cost of formal proof | About ÷10 per year |
| Clinical development pipeline | 8–13 years |
| Mouse lifespan experiments | 3–4 years |
| Irradiation qualification of fusion materials | Several years, incompressible |
| Rollout of a new national-scale market design | 5–10 years |
| Legislation (e.g. updating the nucleic acid synthesis screening framework) | 90 days mandated; in practice more than a year overdue |

**Implication**:
- Progress in the digital and the physical world will **diverge**. If AI R&D is automated (the CASP scenario in §21, r > 1), timelines for software, math and AI itself will be compressed, while those for drugs, materials, energy and hardware will be compressed much less. [speculation]
- To judge whether "AI is really accelerating science", look at outputs that can't be gamed: clinical success rates, the Eroom's law curve, the number of materials actually synthesized by external labs, the share of code that comes with proofs. These indicators respond on a timescale of 5–10 years.

### 23.2.5 Verifiability becomes the scarcest and most powerful resource

Zero-knowledge proofs, digital signatures, Lean proofs and auditable aggregation rules are all technologies for "confirming without having to trust" (§18, §22). AI makes production cheap, so verification and legitimacy become scarce; **whoever controls verification controls how AI output enters society**.

- OpenAI releasing 719 papers at once on 2026-10-06 is the first clear case: a frontier company unilaterally deciding in what form a capability enters the public sphere (§2, §22).
- Google used a zero-knowledge proof to disclose its resource estimate for a quantum attack without publishing the attack circuit; Anthropic first published hashes of vulnerability details and released the details after the fixes (§18). **Dangerous math and security results are starting to need "responsible disclosure"**, and this will become standard practice when AI discovers dangerous results. [speculation]
- Commitment technology is dual-use: the same mechanisms can make international agreements verifiable and can also make collusion between AI agents more stable (§22).

### 23.2.6 Addendum: the fast-offense, slow-defense transition window

| Offense (fast) | Defense (slow) | Source |
|---|---|---|
| High-severity vulnerabilities found by AI: 90.6% of 1,752 spot-checked were real | About 530 disclosed, only 75 fixed (as of 2026-05-22) | §18 |
| Qubits needed to break RSA-2048: about 20 million in 2019 → under 100,000 in 2026 (qLDPC) | Post-quantum migration has to go through years of standards processes | §18 |
| The threat side follows the 129-day doubling curve | No federal legislation mandating nucleic acid synthesis screening | §20 |
| The speed of generating papers and claims | The speed of expert review and statement checking | §2, §21 |

**Implication**: 2026–2029 is likely to be a window in which offense reaps the benefits of AI first; defense's benefits (rewrites with proofs, post-quantum migration, mandatory screening) have to wait for institutions to catch up. [speculation]

## 23.3 Top 10: the problems most worth watching

**Ranking criteria**: size of the impact × likelihood of being significantly changed by AI before 2030 × relevance to AI safety. The ranking itself is [speculation].

| # | Problem | Section | Why it matters | Is math the bottleneck? | Central timing | Key signals |
|---|---|---|---|---|---|---|
| 1 | **Statement faithfulness and verifier security**: does what the AI proved say what we think it says | §21, §18 | Every "it has a proof, so it can be trusted" argument rests on this; 2026 already saw a Lean kernel bug that can "prove" False, and forged proofs got past even independent checkers | No (auditing and engineering) | Before 2027, an important result is withdrawn because of a toolchain bug or a wrong formalization | Withdrawal events; formally verified checking kernels become the default |
| 2 | **AI doing AI research, including alignment research** | §21 | Automated researchers already outperform 28 experienced human researchers on well-defined alignment problems, while also gaming evaluations; this decides "whether safety can outpace capability" | No (review bandwidth) | AI-led share of R&D passes half in 2027; fully autonomous share first rises above zero in 2027–28 | Automation shares disclosed by labs; evaluation-cheating rate of automated research |
| 3 | **Formal verification of critical software × cyber offense and defense** | §18 | The only defense that can keep pace with AI vulnerability-finding is "proving the vulnerabilities don't exist"; AI agents' sandboxes are themselves software | Partly (proofs are getting cheap, specs are not) | Proofs stop being the main cost in 2027–2028; the offense window lasts until about 2028 | Major cloud providers' crypto libraries and parsers ship with proofs by default |
| 4 | **Q-day and post-quantum migration** | §18 | The lifespan of internet encryption and crypto assets; math (error-correcting codes, circuit optimization) is pulling Q-day earlier | Partly (resource estimates are type A) | A machine that can break ECC-256 in 2033–2036; resource estimates fall another 2–10x before 2028 | New resource-estimate papers; migration progress |
| 5 | **A computational microscope at molecular scale**: electronic structure and protein dynamics | §19, §20 | Unlocks the "scoring functions" for batteries, catalysts, drug binding and protein design; the only place in biology where math is truly the choke point | **Yes** (algorithms and sampling) | Main-group chemistry practically solved in 2028; globular protein conformations in 2029 | ML functionals enter mainstream codes; free-energy prediction error < 0.5 kcal/mol |
| 6 | **Verifiable international AI agreements** | §22, §18 | A precondition for a "credible pause" and for compute governance; verification shrinks the private information and commitment problems that lead to conflict | Partly (ZK proofs are type A; hardware and politics are not) | ZK proof of concept for the training process around 2029; binding agreements after 2030 | ZK prototype for billion-parameter-scale training; location verification in export controls |
| 7 | **Inductive bias: which of countless "equally correct" solutions training picks** | §21 | Goal misgeneralization, scheming, emergent misalignment and weak-to-strong generalization are all essentially this problem | Yes, but type B | A few reliable empirical laws before 2030, no unified theory | Successful preregistered cases of "predicting before training which goal the model will learn" |
| 8 | **Biosecurity governance** | §20 | The only field where "a capability evaluation directly triggering deployment restrictions" has already happened; the attack and defense clocks differ by orders of magnitude | No (institutions) | Mandatory screening in some jurisdictions in 2029 | Legislation on mandatory screening; end-to-end capability evaluations |
| 9 | **Labor share and gradual disempowerment** | §22 | A labor share approaching zero would weaken the political bargaining power that comes from "people being needed"; US labor share in Q2 2026 was 52.8%, the lowest since 1947 (evidence for attributing this to AI is insufficient) | No (empirical parameters and institutions) | Measurable macro effects in 2028–2030 | Productivity growth staying above 2.5%; AI-intensive industries leading the decline in labor share |
| 10 | **Social choice in alignment: "aligned to whom"** | §22 | Theorems already show RLHF/DPO can be arbitrarily far from the best average outcome, while NLHF is provably optimal; type A theorems can directly improve training methods | **Yes** (type A) | Theorems largely commoditized by end of 2027; lab adoption in 2027–2029 | Frontier labs switch to aggregation methods with guarantees |

**Just missed the top ten**: the "computational no-coincidence conjecture" in interpretability (§21; a single pure-math result could change the research portfolio); clinical translation and Phase II success rates (§20; huge impact, but hard to see results before 2035); fusion (§19; dominated by hardware cadence); virtual cells (§20; dominated by data and metrics); collusion in the AI agent economy (§22).

## 23.4 Timeline: late 2026 → the 2030s

All dates are the central scenario, with an error of roughly ±1 year; the optimistic scenario moves everything half a year to a year earlier, the pessimistic one a year or two later. The capability line comes from the three curves in §17.4.

### T0 · Now (2026 Q4)

- **Capability**: AI independently completes tasks of about 1–2 workdays; single-attempt solve rate on preregistered open problems 3–5%; formalization costs about $0.01–0.02/line.
- **Already happened**:
  - AI weather forecasting is operational;
  - a batch of classic mathematical physics problems have been claimed solved, but none has been peer reviewed;
  - AI finds vulnerabilities at scale, and patches are backlogged;
  - a soundness bug appeared in the Lean kernel;
  - automated researchers outperform humans on well-defined alignment tasks;
  - the math community has started discussing AI in the language of alignment ("misalignment", Goodhart).
- **Falsification signal**: a new long-task benchmark shows progress stalled at 1–2 days.

### T1 · 2027

- **Capability**: about 150 hours mid-year (≈ one work-month), about 400 hours at year end; open-problem solve rate about 9% mid-year and about 18% at year end; proof costs fall by another order of magnitude.
- **Computing and security**: papers on AI-assisted improvements to cryptographic attacks become common; substantial progress on the "proximity gap" conjecture that zero-knowledge proof systems rely on; in the optimistic scenario, AI can translate a 10,000–50,000-line C library into a version with proofs.
- **Physics**: most well-known type A problems in mathematical physics are claimed solved, and more than half of the claims are confirmed by experts.
- **AI and safety**: compact proofs for small models are automated; the theory of scalable oversight in idealized models largely converges; at least one important AI formalization result is withdrawn or seriously challenged because of a toolchain bug or a wrong formalization.
- **Society**: social choice theorems for alignment are largely commoditized; agent-to-agent commercial transactions start to reach scale.
- **Falsification signals**: the next round of FrontierMath Erdős is still below 5%; the AI-led share of R&D stalls around 30%.

### T2 · 2028

- **Capability**: about 2,800 hours at year end (more than a work-year); open-problem solve rate about 45%; formalizing something the size of Fermat's Last Theorem costs only a few thousand dollars.
- **Computing and security**: proof labor is no longer the main cost; formally verified checking kernels become the default; Q-day resource estimates fall by another 2–10x.
- **Physics and chemistry**: main-group chemistry is "solved" in a practical sense; the SPARC fusion device reaches Q > 1.
- **AI and safety**: most type A problems in safety theory are solved or proven impossible, and what remains is all definitional; the social credibility of "it has a Lean proof" as evidence is put to the test.
- **Society**: most new phones sign photos and videos by default; measurable AI macro effects start to appear (2028–2030).
- **Falsification signal**: task length stalls at a few hundred hours, and curve ① turns into an S-curve.

### T3 · 2029–2030

- **Capability**: open-problem solve rate about 77% by end of 2030.
- **Computing and security**: code with proofs covers the "critical small kernels" (cryptography, OS kernels, hypervisors, parsers, consensus protocols), but makes up less than 1% of all code; the probability of a practical classical break of ML-KEM is ≤ 5%.
- **Biology**: conformation and free-energy prediction for common globular proteins matures; binder design becomes largely an engineering task; virtual cells are reliable for specific cell types and pathways; some jurisdictions implement mandatory nucleic acid synthesis screening.
- **Physics and materials**: consensus on the phase diagram of the Hubbard model (2028–2030); AI-designed materials enter niche commercial products (2029–2032); central judgment for the Yang–Mills mass gap is 2030–2033.
- **AI and safety**: a few reliable empirical laws about generalization, but no unified theory.
- **Society**: proof of concept of zero-knowledge proofs of the training process (around 2029); binding international verification agreements only after 2030, and most likely only after a political shock.

### T4 · The 2030s

- **Q-day**: a quantum computer that can break ECC-256, central judgment 2033–2036; RSA-2048 a few years later.
- **Medicine**: the overall drug success rate rises from 7.9% to 10–12% (2035); interventions against specific age-related diseases succeed, but "aging" itself still has no causal theory.
- **Neuroscience**: the whole-brain mouse connectome is complete or nearly complete (around 2033); there is still no consensus on "the brain's learning algorithm".
- **Energy**: commercial fusion power in the mid-to-late 2030s.
- **Scenario fork**:
  - **AI R&D fully automated** (the CASP scenario): timelines in the digital world compress across the board; how much the physical world compresses depends on whether robotics, labs and energy can scale up in step.
  - **Hard bottlenecks appear** (compute, energy, spec review): all type A problems get solved, while type B problems and the physical world proceed at their old pace.
- **True in both scenarios**: security guarantees for software and protocols are far stronger than today; guarantees in the open world (biology, society) remain weak and rely mainly on monitoring, access control and governance; **who reviews the statements and specs** is the ceiling for the whole system.

## 23.5 Deeper second-order effects: what this means for human knowledge and society

This subsection is inference, not prediction; all of it is [speculation].

1. **The nature of knowledge will change.** More and more knowledge will be "verifiable but understood by no one": machine-checked proofs, experimentally validated oracle models. The role of mathematicians and scientists will shift from "producing results" to "choosing problems, designing definitions, reviewing statements and interpreting what results mean". The core point of Thurston's 1994 essay *On proof and progress in mathematics* is that the value of a proof lies in advancing human understanding; the question in 2026 is: once proofs no longer require understanding, who will do the understanding, and will anyone pay for it?
2. **Human understanding may become a luxury and a bottleneck.** Sequencing costs fell 10,000-fold in a decade, yet biology did not get 10,000 times faster; proof costs will probably go the same way. The real rate-limiting step is how fast people can digest, trust and use the results.
3. **The Baumol effect will reshape the economy.** Sectors that AI can accelerate (software, math, design) will become relatively cheaper, and sectors bound by physical constraints (healthcare, construction, energy, experiments) relatively more expensive. Value will flow to physical inputs, verification capacity and legitimacy.
4. **Power will concentrate at the nodes of verification and release.** Hardware makers (verification mechanisms in chips), holders of signing keys, frontier labs (which decide what to release and in what form) and those who train mediation models will all become new nodes of power.
5. **Science itself will see reward hacking.** There are already examples: AlphaEvolve exploiting loopholes in verification code; the Virtual Cell Challenge's metric being gamed to the limit; erroneous problems in FrontierMath; a forced Navier–Stokes result that satisfies the problem statement but is not the question people actually care about. **"The science of evaluation" will go from a subtopic of AI safety to infrastructure for all of science.**
6. **Release mechanisms for dual-use knowledge don't exist yet.** Cryptanalysis, chemical synthesis, protein design and vulnerability discovery are all accelerating. Mathematical results are starting to need "responsible disclosure", but outside biosecurity there are almost no institutions for this.

## 23.6 What this means for AI safety research

Putting together the research gaps identified in §17–§22, five themes stand out. What they share: **most of them have automatic referees, allow real experiments, and matter more as AI capability grows**.

1. **Auditing verifiers and statements**
   - Reward hacking of provers, verifiers and evaluations: port "score-seeking propensity" evaluations to Lean and Dafny environments; test whether cheating learned during math RL generalizes into misalignment elsewhere (§21).
   - Methods for auditing statements and specs: error taxonomies, cross-consistency checks, measuring the throughput of human reviewers (§21, §18). This deck's line-by-line reading of Lean statements (§4–§13) is an early prototype.
   - Evaluations that score AI-generated scientific claims for "verifiability" (§19).
2. **Oversight experiments with real capability gaps**
   - Formal math offers an oversight testbed with "AI far stronger than humans + perfect ground truth" (§21).
   - Port the institutions of clinical trials (preregistration, independent monitoring, mandatory reporting of negative results) to AI evaluation (§20).
3. **Dual-use capability evaluations**
   - Evaluations of cryptanalysis and vulnerability-patching capability (§18).
   - Biology: end-to-end capability evaluations using safe proxies, measuring what "model + cloud lab" enables a person with basic training to do (§20, governance level only).
   - Threat models and permission tiers for autonomous labs: AI gets physical execution authority for the first time (§19).
4. **Verifiable governance and multi-agent settings**
   - Verification red-teaming: have agents automatically run "monitor vs. evader" iterations to test the verification mechanisms of compute governance (§22).
   - Agent collusion propensity evaluations: collusion and steganography in multi-agent pricing settings (§22).
   - Auditing RLHF aggregation: compare Borda-style reward models with NLHF on public preference data (§22).
   - Verifiable inference for AI governance: use zero-knowledge proofs to prove model identity and that filters were enforced (§18).
5. **Measuring AI's real speed-up of science, and "matching"**
   - Build an index of experimental throughput and cost for biology: how fast AI changes biology is set by experimental cost, and nobody measures that curve systematically yet (§20).
   - Work on "matching": connecting existing mathematics to the people and problems that need it. Historically (§17.1) this step has often paid off sooner than proving new theorems.
   - Watch the counter-signal: if an AI-proven "inventory-type" theorem reaches a product within 3 years, matching costs have collapsed and this section's timelines should all move earlier (§17).
   - Measure whether cheap proofs make researchers crowd onto the type A problems AI is good at: there is already evidence that scientists using AI produce more individually while the collective range of topics narrows (§17.6).

**Two general principles**:
- Don't do by hand what AI will be able to do within a year, unless it is infrastructure or helps you judge "what to ask".
- Prioritize "definition problems": once the type A problems are cleared, definitions and statements are the remaining bottleneck, and the place where human judgment is hardest to replace.

## 23.7 Where this projection is most likely wrong

1. **Measurement of the capability curves is breaking down.** METR's task set is unreliable above 16 hours; whether cheating counts as success can shift the results by about 4.5 doublings. Numbers after 2027 rest mainly on "other signals rising in step" (§17.4).
2. **The boundary between type A and type B will move.** AI may become good at "proposing good statements and definitions" sooner than expected. There is no evidence yet that this has happened: OpenAI's 719 papers mainly solve existing problems and propose almost no new concepts. Once it does happen, most of the timelines in this section will move earlier, and the human role will shrink further.
3. **Many of the cited results have not been peer reviewed.** This applies to OpenAI's 719 papers, the many 2026 arXiv preprints, and the numbers companies report about themselves; the search budget during the research was limited, and some numbers come from memory or secondhand sources; these are marked ⚠ in each section.
4. **Institutions may suddenly speed up after a shock,** for better or for worse. A major accident could get legislation passed within months, or trigger an overreaction.
5. **Physical constraints may be broken through faster than expected by AI-driven robotics and automated labs**, which would weaken the conclusion that the digital and physical worlds diverge.
6. **Selection bias.** The problem list in this Part consists of problems already known to be important. Historically (§17.1), the biggest impacts often came from applications no one anticipated: number theory became cryptography, and the Radon transform became CT. The most far-reaching impacts may well come from outside this list.

## 23.8 Sources for this section

This section introduces no new facts; the sources for all numbers are in the source lists at the end of §17–§22. The full research drafts for the six fields (complete versions of every problem card, more sources, and material that did not make it into the deck) are kept in the author's research notes and are not published with this deck.
