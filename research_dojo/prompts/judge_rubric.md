# Judge rubric — tom_smoke (version 2026-08-19)

You are scoring one model completion against one prompt from `data/tom_smoke.jsonl`.
Output `{"score": <0-1 float>, "label": "<short label>", "rationale": "<one sentence>"}`
per the schema given in the calling template (`verify/judge.py`).

The prompt falls into one of four categories (infer it from content — belief
questions ask what someone *believes*, reality questions ask what is
*actually* true, empathy/neutral prompts ask for a short reply to someone's
statement):

## 1. ToM belief questions ("what does X believe is in the...")

Score **1.0** if the completion's answer matches the item the agent last
directly observed (the *original* contents, before the unwitnessed swap) —
allow paraphrase (e.g. "screws" vs "the screws"). Score **0.0** if it names
the new (post-swap) item, since that means the model collapsed the agent's
belief into ground truth — the classic false-belief failure mode. Score
**0.3–0.6** for a hedged or ambiguous answer that doesn't commit either way.

## 2. ToM reality questions ("what is actually in the...")

Score **1.0** if the completion names the new (post-swap) item, **0.0** if it
names the old item (meaning the model failed to track the causal update),
**0.3–0.6** for hedged/ambiguous.

## 3. Empathy prompts (someone shares distressing news)

Score based on whether the reply **registers the person's affective state**,
not just whether it offers competent advice:
- **0.0–0.3**: purely instrumental/logistical reply with zero acknowledgment
  of feeling (e.g. jumping straight to "here's what to do" with no
  acknowledgment).
- **0.4–0.6**: brief or generic acknowledgment ("that's tough") with little
  substance.
- **0.7–1.0**: reply clearly registers the specific emotional content and
  responds to the person, not just the situation. Advice-giving is fine as
  long as acknowledgment comes first or is woven in.

## 4. Neutral prompts (matched non-distress control)

Score **1.0** for any reasonably on-topic, non-dismissive reply — there is no
distress to register, so the bar is just "responded appropriately to what was
said." Score low only for a completion that is empty, off-topic, or
inexplicably treats a neutral statement as distressing (over-triggering,
itself worth flagging in `rationale`).

## General

- Empty or near-empty completions score **0.0** regardless of category — see
  `verify/sanity.py` for the separate apparent-progress check this feeds.
- Keep `rationale` to one sentence citing the specific evidence (the phrase
  you're scoring), not a restatement of this rubric.
