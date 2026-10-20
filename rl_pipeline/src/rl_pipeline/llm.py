"""Chat calls to Azure OpenAI with tools, retries, and a spending cap.

One client serves every model the pipeline talks to (the policy we sample from, the fine-tuned
policy, and the intent judge); the deployment name is passed per call.

Failure handling:
* Rate limits, timeouts and 5xx errors are retried with exponential backoff and jitter.
* Request errors that will not succeed on retry (content filter, invalid request) raise
  ``ProviderError``. A rollout that hits one is recorded with that status and excluded from
  training data, instead of being mistaken for the model's behaviour.
* Every successful call is charged to the ``Budget`` before the result is returned.
"""
from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any

import openai
from openai import OpenAI

from .budget import Budget, Usage

log = logging.getLogger(__name__)

_RETRYABLE = (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError,
              openai.InternalServerError)


class ProviderError(RuntimeError):
    """A provider-side refusal or invalid request that retrying will not fix."""

    def __init__(self, kind: str, message: str):
        super().__init__(f"{kind}: {message}")
        self.kind = kind


@dataclass
class ChatResult:
    message: dict[str, Any]          # {"role": "assistant", "content": ..., "tool_calls": [...]}
    usage: Usage
    finish_reason: str | None
    usd: float


def azure_base_url() -> str:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
    resource = os.environ.get("AZURE_AI_RESOURCE", "").strip()
    if endpoint:
        root = endpoint.rstrip("/")
        return root if root.endswith("/openai/v1") else root + "/openai/v1"
    if resource:
        return f"https://{resource}.openai.azure.com/openai/v1"
    raise RuntimeError("set AZURE_OPENAI_ENDPOINT or AZURE_AI_RESOURCE (see .env.example)")


def make_openai_client(timeout: float = 180.0, max_retries: int = 0) -> OpenAI:
    """OpenAI SDK client for the Azure v1 endpoint.

    Chat calls go through ``AzureChat``, which retries itself (and charges the budget), so the SDK's
    own retries are off by default. File and fine-tuning calls pass ``max_retries`` > 0 instead.
    """
    key = os.environ.get("AZURE_OPENAI_API_KEY")
    if not key:
        raise RuntimeError("AZURE_OPENAI_API_KEY is not set (see .env.example)")
    return OpenAI(base_url=azure_base_url() + "/", api_key=key, timeout=timeout, max_retries=max_retries)


def _uses_completion_tokens(model: str) -> bool:
    """Reasoning-model deployments take max_completion_tokens and a fixed temperature."""
    return model.startswith(("gpt-5", "o1", "o3", "o4"))


def message_to_dict(msg: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"role": "assistant", "content": msg.content}
    calls = getattr(msg, "tool_calls", None) or []
    if calls:
        out["tool_calls"] = [{"id": c.id, "type": "function",
                              "function": {"name": c.function.name, "arguments": c.function.arguments}}
                             for c in calls]
    return out


class AzureChat:
    def __init__(self, budget: Budget, *, client: OpenAI | None = None, max_retries: int = 10):
        self.budget = budget
        self.client = client or make_openai_client()
        self.max_retries = max_retries

    def chat(self, model: str, messages: list[dict[str, Any]], *, tools: list[dict] | None = None,
             temperature: float | None = None, max_tokens: int = 2048, purpose: str = "rollout",
             json_mode: bool = False) -> ChatResult:
        self.budget.check()
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if _uses_completion_tokens(model):
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                kwargs["temperature"] = temperature
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(self.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                break
            except _RETRYABLE as e:
                if attempt == self.max_retries:
                    raise ProviderError("retries_exhausted", str(e)[:300]) from e
                delay = min(60.0, 2.0 ** attempt) * (0.5 + random.random())
                log.warning("%s on %s (attempt %d); retrying in %.1fs", type(e).__name__, model,
                            attempt + 1, delay)
                time.sleep(delay)
            except openai.BadRequestError as e:
                body = str(e)
                kind = "content_filter" if "content_filter" in body or "ResponsibleAIPolicy" in body else "bad_request"
                raise ProviderError(kind, body[:300]) from e

        choice = resp.choices[0]
        u = resp.usage
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        usage = Usage(input_tokens=u.prompt_tokens or 0, output_tokens=u.completion_tokens or 0,
                      cached_input_tokens=cached)
        usd = self.budget.record(model, usage, purpose=purpose)
        if choice.finish_reason == "content_filter":
            raise ProviderError("content_filter", "completion was filtered")
        return ChatResult(message=message_to_dict(choice.message), usage=usage,
                          finish_reason=choice.finish_reason, usd=usd)
