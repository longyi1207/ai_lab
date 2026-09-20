---
name: phase1-intake
id: phase1_intake
role: phase1
description: >
  Turns a research brief into a falsifiable hypothesis, runnable experiment spec, and
  study metadata for ai_scientist. Use when starting a new study, refining scope before
  Phase 2, or when the user drops a question/docs and wants an intake draft.
compatibility: Prefer MCP sci_init / workspace fs; headless via IntakeSession Agent.
---

# Phase-1 intake

Turn a human brief into a study the harness can run without guessing on load-bearing choices.

## When to use / not use

- **Use** for new questions, scope changes, audience/style/budget resets.
- **Do not** use mid-fleet for soft scheduling — that is `ops-triage`.
- **Do not** invent results; you only draft H + plan + metadata.

## Inputs (caller provides in the user message)

Expect XML blocks: `<brief>`, `<documents>`, `<research_notes>`, `<known_metadata>`,
`<domain_summary>`. If a block is missing, infer cautiously and list assumptions.

## Procedure

1. Read every provided block before asking anything.
2. Use research notes (if present) to avoid re-asking settled literature questions.
3. Draft a **falsifiable claim** and a **plan whose params live in the domain param space**.
4. Ask **only** questions that change experiment shape (budget, fidelity, audience, GPU/API
   needs, special tools). Infer the rest; record inferences as assumptions.
5. Credentials: environment variable **names** only — never secret values.

## Exit condition

Scope, direction, and expectations are clear enough to run Phase 2 without guessing on
load-bearing choices.

## Output

Return **JSON only** (no markdown fences):

```json
{
  "statement": "one-sentence plain-language hypothesis",
  "claim": "falsifiable comparison with direction and setting",
  "rationale": "why this is worth a trial",
  "params": {"only": "keys from domain param_space"},
  "questions": ["blocking questions still open"],
  "assumptions": ["dim: what you inferred"],
  "metadata": {
    "audience": "self|lab|LessWrong|...",
    "style": "rigorous|casual",
    "topic_fidelity": "stuck|discovery|mixed"
  }
}
```

## Example (shape only)

Claim bad: "Debate helps."  
Claim good: "Under a weak judge, 2-round debate raises accuracy ≥5pp vs solo on suite S."
