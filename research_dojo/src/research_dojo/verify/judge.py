"""LLM-judge verification. Rubric text comes from a versioned file
(prompts/judge_rubric.md); the version string is required in the spec
(config.spec.JudgeSpec.version) so judgments stay traceable to a rubric.

Structured JSON output with one reformat retry before giving up — mirrors
code/tom_empathy/src/judge.py's fence-stripping + regex-extract fallback.
"""

from __future__ import annotations

import json
import re

from research_dojo.config.settings import azure_openai_client_and_model

JUDGE_SYSTEM = "You are a careful evaluator. Reply with ONLY valid JSON matching the given schema."

JUDGE_USER_TEMPLATE = """\
Rubric:
{rubric}

Prompt given to the model:
{prompt}

Model's completion:
{completion}

JSON schema: {{"score": <float 0-1>, "label": "<short label>", "rationale": "<one sentence>"}}
"""


def _parse_json(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError(f"judge returned non-JSON: {raw[:200]!r}") from None
        return json.loads(m.group())


def judge_rollout(rubric: str, prompt: str, completion: str, judge_version: str) -> dict:
    client, model = azure_openai_client_and_model()
    user = JUDGE_USER_TEMPLATE.format(rubric=rubric, prompt=prompt, completion=completion)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        max_completion_tokens=300,
        messages=[{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}],
    )
    raw = resp.choices[0].message.content or ""
    try:
        parsed = _parse_json(raw)
    except ValueError:
        retry_resp = client.chat.completions.create(
            model=model,
            temperature=0.0,
            max_completion_tokens=300,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user},
                {"role": "assistant", "content": raw},
                {"role": "user", "content": "That was not valid JSON. Reply with ONLY the JSON object, nothing else."},
            ],
        )
        raw = retry_resp.choices[0].message.content or ""
        parsed = _parse_json(raw)  # let this raise if it still fails — caller marks rollout FAILED
    return {
        "score": float(parsed.get("score", 0.0)),
        "label": parsed.get("label"),
        "rationale": parsed.get("rationale"),
        "raw_response": raw,
        "judge_version": judge_version,
    }
