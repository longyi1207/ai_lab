"""Batch chat harness: one Azure/OpenAI chat completion per rollout.

Cost is an *estimate* for budget gating (spec.budget.max_usd), not a billing
reconciliation — actual spend should be checked against the Azure portal.
"""

from __future__ import annotations

import time

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from research_dojo.config.settings import azure_openai_client_and_model
from research_dojo.config.spec import ExperimentSpec
from research_dojo.harness.base import HarnessResult, TransientHarnessError, is_transient_error

# Rough $/1K-token estimate, gpt-4o-mini class deployment. Override the whole
# harness (a different ModelSpec) rather than this constant for other models.
DEFAULT_COST_PER_1K_IN = 0.00015
DEFAULT_COST_PER_1K_OUT = 0.0006


class BatchChatHarness:
    def __init__(self, spec: ExperimentSpec):
        self.spec = spec
        self._client = None
        self._model = None

    def _get_client(self):
        if self._client is None:
            self._client, self._model = azure_openai_client_and_model()
        return self._client, self._model

    @retry(
        retry=retry_if_exception_type(TransientHarnessError),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _call(self, client, model: str, messages: list[dict]):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.spec.model.temperature,
                max_completion_tokens=self.spec.model.max_tokens,
            )
        except Exception as e:  # noqa: BLE001 — route known-transient classes to retry
            if is_transient_error(e):
                raise TransientHarnessError(str(e)) from e
            # newer Azure reasoning-model deployments reject temperature/max_tokens;
            # retry once with the minimal, widely-compatible kwarg set before giving
            # up (see docs/AZURE.md, mirrors tom_empathy/vendor/llm_client.py:chat).
            if "unsupported_parameter" in str(e) or "Unsupported parameter" in str(e):
                return client.chat.completions.create(
                    model=model, messages=messages, max_completion_tokens=self.spec.model.max_tokens,
                )
            raise

    def run(self, prompt: str, *, sample_id: str, arm: str) -> HarnessResult:
        client, model = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        t0 = time.monotonic()
        resp = self._call(client, model, messages)
        latency_ms = (time.monotonic() - t0) * 1000
        completion = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", 0) or 0
        tokens_out = getattr(usage, "completion_tokens", 0) or 0
        cost = (tokens_in / 1000) * DEFAULT_COST_PER_1K_IN + (tokens_out / 1000) * DEFAULT_COST_PER_1K_OUT
        transcript = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": completion},
        ]
        return HarnessResult(
            completion=completion,
            transcript=transcript,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_usd_est=cost,
        )
