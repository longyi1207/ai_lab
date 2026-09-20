"""LLM access. Azure-first per repo policy; deterministic fake for offline work.

Secrets are read from the environment only (never from workspace artifacts, which store
credential *names*).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@lru_cache(maxsize=1)
def load_env(start: str | None = None) -> str | None:
    """Load the nearest `.env` walking upwards, without overriding real environment vars.

    Secrets live in the repo-root `.env` per project policy. Without this, a correctly
    configured machine would silently fall back to the fake model.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dotenv is a declared dependency
        return None
    here = Path(start or os.getcwd()).resolve()
    for directory in [here, *here.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return str(candidate)
    return None


@dataclass
class LLMResponse:
    text: str
    usage: dict[str, float] = field(default_factory=dict)
    model: str = "unknown"
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def json(self) -> Any:
        """Parse a JSON object out of the response, tolerating code fences."""
        text = self.text.strip()
        if text.startswith("```"):
            body = text.split("```")
            for chunk in body:
                chunk = chunk.strip()
                if chunk.startswith("json"):
                    chunk = chunk[4:].strip()
                if chunk.startswith("{") or chunk.startswith("["):
                    return json.loads(chunk)
        start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
        if start == -1:
            raise ValueError("no JSON payload in response")
        return json.loads(text[start:])


@runtime_checkable
class LLMClient(Protocol):
    name: str

    def complete(
        self, system: str, user: str, *, temperature: float = 0.7, json_mode: bool = False
    ) -> LLMResponse: ...


class FakeLLM:
    """Deterministic pseudo-model: same prompt → same output, no network.

    Handlers let tests/skills inject structured replies keyed by a marker in the prompt.
    A handler may return:
      - str / dict → final assistant text (dict is json-dumped)
      - {"tool_calls":[{"name":..., "arguments":{...}}], "content": "..."} → tool round
    """

    name = "fake"

    def __init__(self, handlers: dict[str, Any] | None = None) -> None:
        self.handlers = handlers or {}
        self.calls: list[dict[str, Any]] = []
        self._handler_hits: dict[str, int] = {}

    def complete(
        self, system: str, user: str, *, temperature: float = 0.7, json_mode: bool = False
    ) -> LLMResponse:
        self.calls.append({"system": system, "user": user, "json_mode": json_mode})
        blob = system + "\x00" + user
        chosen_marker = self._select_handler_marker(blob)
        if chosen_marker is not None:
            payload = self.handlers[chosen_marker]
            hit = self._handler_hits.get(chosen_marker, 0)
            self._handler_hits[chosen_marker] = hit + 1
            if isinstance(payload, list):
                chosen = payload[min(hit, len(payload) - 1)]
            else:
                chosen = payload
            if isinstance(chosen, dict) and "tool_calls" in chosen:
                return LLMResponse(
                    text=str(chosen.get("content") or ""),
                    usage={"usd": 0.0, "tokens": 0.0},
                    model=self.name,
                    tool_calls=list(chosen.get("tool_calls") or []),
                )
            text = chosen if isinstance(chosen, str) else json.dumps(chosen)
            return LLMResponse(text=text, usage={"usd": 0.0, "tokens": 0.0}, model=self.name)
        digest = hashlib.sha256(blob.encode()).hexdigest()
        if json_mode:
            return LLMResponse(
                text=json.dumps({"fake": True, "digest": digest[:16]}),
                usage={"usd": 0.0, "tokens": 0.0},
                model=self.name,
            )
        return LLMResponse(
            text=f"[fake:{digest[:16]}]", usage={"usd": 0.0, "tokens": 0.0}, model=self.name
        )

    def _select_handler_marker(self, blob: str) -> str | None:
        """Pick the handler meant for this call — not a skill id merely listed in the catalog."""
        matches = [m for m in self.handlers if m in blob]
        if not matches:
            return None
        # Prefer explicit active-skill / legacy Skill: forms over catalog mentions.
        ranked: list[tuple[int, int, str]] = []
        for marker in matches:
            score = 0
            if f"skill `{marker}`" in blob or f"Active skill hint: {marker}" in blob:
                score += 100
            if f"Skill: {marker}" in blob:
                score += 80
            if f'"id": "{marker}"' in blob:
                score -= 20  # catalog noise
            ranked.append((score, len(marker), marker))
        ranked.sort(reverse=True)
        best = ranked[0]
        if best[0] < 0 and len(ranked) > 1:
            # All catalog-only; fall back to longest marker.
            return max(matches, key=len)
        return best[2]

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        # Flatten for handler matching; include tool results so scripts can branch.
        parts: list[str] = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                continue
            if role == "tool":
                parts.append(f"tool:{m.get('content', '')}")
            else:
                parts.append(str(m.get("content") or ""))
        return self.complete(system, "\n".join(parts), temperature=temperature, json_mode=False)


class MissingLLMDependency(RuntimeError):
    pass


class OpenAICompatibleClient:
    """Thin wrapper over the OpenAI SDK, pointed at Azure or api.openai.com.

    Credentials are read from the environment *inside* this class on purpose: an API key
    passed as an argument shows up verbatim in any traceback frame that renders locals.
    """

    def __init__(self, *, provider: str, model: str, base_url: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # optional dependency
            raise MissingLLMDependency(
                "the OpenAI SDK is not installed; run: pip install -e '.[llm]'"
            ) from exc

        key_var = "AZURE_OPENAI_API_KEY" if provider == "azure" else "OPENAI_API_KEY"
        api_key = os.environ.get(key_var)
        if not api_key:
            raise RuntimeError(f"{key_var} is not set")
        self._client = (
            OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        )
        self.model = model
        self.name = provider

    def complete(
        self, system: str, user: str, *, temperature: float = 0.7, json_mode: bool = False
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        completion = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            **kwargs,
        )
        return self._to_response(completion)

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        completion = self._client.chat.completions.create(**kwargs)
        return self._to_response(completion)

    def _to_response(self, completion: Any) -> LLMResponse:
        usage: dict[str, float] = {}
        if completion.usage is not None:
            usage = {
                "tokens": float(completion.usage.total_tokens or 0),
                "tokens_in": float(completion.usage.prompt_tokens or 0),
                "tokens_out": float(completion.usage.completion_tokens or 0),
            }
        message = completion.choices[0].message
        tool_calls: list[dict[str, Any]] = []
        for tc in getattr(message, "tool_calls", None) or []:
            args_raw = tc.function.arguments or "{}"
            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {"raw": args_raw}
            tool_calls.append(
                {"id": tc.id, "name": tc.function.name, "arguments": args}
            )
        return LLMResponse(
            text=message.content or "",
            usage=usage,
            model=self.model,
            tool_calls=tool_calls,
        )


def get_llm(*, allow_network: bool = True) -> LLMClient:
    """Azure → direct OpenAI → fake, honoring `AI_SCIENTIST_FAKE_LLM` and availability."""
    if os.getenv("AI_SCIENTIST_FAKE_LLM", "0") not in {"0", "", "false", "False"}:
        return FakeLLM()
    if not allow_network:
        return FakeLLM()
    load_env()

    prefer_azure = os.getenv("OPENAI_PREFER_AZURE", "true").lower() not in {"0", "false"}
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if prefer_azure and endpoint and os.getenv("AZURE_OPENAI_API_KEY") and deployment:
        # Azure wants the *deployment* name as the model id, on the /openai/v1/ path.
        return OpenAICompatibleClient(
            provider="azure",
            model=deployment,
            base_url=endpoint.rstrip("/") + "/openai/v1/",
        )
    if os.getenv("OPENAI_API_KEY"):
        return OpenAICompatibleClient(
            provider="openai", model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        )
    return FakeLLM()


__all__ = [
    "FakeLLM",
    "LLMClient",
    "LLMResponse",
    "MissingLLMDependency",
    "OpenAICompatibleClient",
    "get_llm",
    "load_env",
]
