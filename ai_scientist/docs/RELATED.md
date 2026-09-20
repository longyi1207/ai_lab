# Related work & lineage

Parent: [`../DESIGN.md`](../DESIGN.md).

What we copy, adapt, or deliberately **not** build.

---

## 1. Evolutionary search with LLM variation

| System | Evolves | Fitness | Archive |
|--------|---------|---------|---------|
| FunSearch | Programs | Deterministic scorers | Island EA |
| AlphaEvolve | Code / algorithms | Automated evaluators | Evolutionary + LLM |
| **This project** | **`hypothesis + experiment_plan`** | Domain graders + verification | **MAP-Elites + novelty** |

Steal: LLM as mutation prior + hard-ish evaluators + persistent archive.  
First demo domain may be oversight empirics — not matmul kernels.

---

## 2. Quality–diversity

| Idea | Role |
|------|------|
| MAP-Elites | Best per behavior cell |
| Novelty search | Exploration archive / parents |
| Open-endedness (Clune et al.) | Aspiration; not copied wholesale |

Descriptors from **results/behavior**, not prompt embeddings (DESIGN §8).

---

## 3. Debate & scalable oversight

| Thread | Role here |
|--------|-----------|
| Irving et al. — AI safety via debate | Motivates oversight as an **example domain** |
| Pfau / AISI → Resolution empirics | Taste for weak-judge settings; we don’t claim their scale |
| QuALITY-style asymmetry | Useful pattern inside a domain pack |
| Design-time + run-time debate **inside the harness** | Product mechanisms (Phase 1 debater; Phase 2 truth-seeking) — distinct from “research topic = debate” |

---

## 4. Other “AI Scientist” systems (contrast)

| System | Output | Contrast |
|--------|--------|----------|
| Sakana AI Scientist | Papers + ML experiments | Soft review fitness; different epistemic object |
| Kosmos / agentic research | Long analysis artifacts | Verification burden |
| Darwin Gödel Machine | Self-modifying agent code | Meta-search; defer until outer loop trusted |
| ADAS | Agent scaffolds | Optional later |

LY map: [A map of AI for scientific discovery](../../../website/src/content/writing/ai-for-science-discovery-map.md) (program evolution vs full research artifacts).

---

## 5. Resolution positioning

| Bet | This project |
|-----|----------------|
| Research automation / 10×→50× | **Primary deliverable** (harness) |
| Scalable oversight / debate | **First domain pack** (example), not the whole architecture |
| SLT / personas | Out of core phenotype |
| Apparent vs real progress | Verification gates + held-out / audit in domain + report |

Sibling: [`research_dojo`](../../research_dojo/) — reuse supervisor/eval patterns in V1 daemon; don’t rebuild.

---

## 6. Starter references

- Irving, Christiano, Amodei — AI safety via debate  
- Mouret & Clune — MAP-Elites  
- Lehman & Stanley — Novelty search  
- FunSearch (Nature 2024); AlphaEvolve (arXiv 2506.13131)  
- Sakana AI Scientist; Darwin Gödel Machine  
- Resolution launch / AISI Alignment + Timaeus framing  

---

## 7. Naming honesty

Prefer:

> evolutionary research harness with QD search over hypotheses/experiments  

over:

> an AI that does alignment research  

`ai_scientist` is aspirational product shorthand.
