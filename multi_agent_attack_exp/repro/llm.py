"""Model clients, retries and the cost ledger.

Every call is appended to <runs>/ledger.jsonl with its token usage and estimated cost.
`Budget` stops new calls once estimated spend crosses --max-usd. Calls already in flight
finish, so the overshoot is bounded by the concurrency.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

log = logging.getLogger(__name__)
PROJECT = Path(__file__).resolve().parents[1]


class BudgetExceeded(RuntimeError):
    pass


class ContentFiltered(RuntimeError):
    """The provider's content filter blocked the request. Recorded as its own failure type, never as a model choice."""


@dataclass
class ModelSpec:
    key: str
    model: str            # provider model id, or Azure deployment name
    base_url: str
    api_key_env: str
    params: dict
    price: dict


class Ledger:
    def __init__(self, path: Path, max_usd: float | None):
        self.path = path
        self.max_usd = max_usd
        self._lock = threading.Lock()
        self.spent = 0.0
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    self.spent += json.loads(line)["usd"]
                except (ValueError, KeyError):
                    pass

    def check(self) -> None:
        if self.max_usd is not None and self.spent >= self.max_usd:
            raise BudgetExceeded(f"estimated spend ${self.spent:.2f} reached --max-usd ${self.max_usd:.2f}")

    def record(self, entry: dict) -> None:
        with self._lock:
            self.spent += entry["usd"]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(entry) + "\n")


def config_path() -> Path:
    """MINILAB_MODELS picks the model config (default configs/models.yaml), relative to the project or absolute."""
    p = Path(os.environ.get("MINILAB_MODELS", "configs/models.yaml"))
    return p if p.is_absolute() else PROJECT / p


def load_models() -> dict[str, ModelSpec]:
    load_dotenv(PROJECT / ".env")
    load_dotenv()   # also a .env in the current directory, if any; never overrides what is already set
    for var in ("AZURE_OPENAI_ENDPOINT", "AZURE_FOUNDRY_ENDPOINT"):
        if os.environ.get(var):
            os.environ[var] = os.environ[var].rstrip("/")
    cfg = yaml.safe_load(config_path().read_text())
    provs = cfg["providers"]
    out = {}
    for k, m in cfg["models"].items():
        prov = provs[m["provider"]]
        out[k] = ModelSpec(k, m["model"], os.path.expandvars(prov["base_url"]), prov["api_key_env"],
                           m.get("params", {}), m["price"])
    return out


def usage_cost(spec: ModelSpec, usage) -> dict:
    if usage is None:
        return {"prompt": 0, "cached": 0, "completion": 0, "reasoning": 0, "usd": 0.0}
    prompt = usage.prompt_tokens or 0
    details = getattr(usage, "prompt_tokens_details", None)
    cached = (getattr(details, "cached_tokens", 0) or 0) if details else 0
    completion = usage.completion_tokens or 0
    cdet = getattr(usage, "completion_tokens_details", None)
    reasoning = (getattr(cdet, "reasoning_tokens", 0) or 0) if cdet else 0
    p = spec.price
    usd = ((prompt - cached) * p["input"] + cached * p["cached_input"] + completion * p["output"]) / 1e6
    return {"prompt": prompt, "cached": cached, "completion": completion, "reasoning": reasoning, "usd": usd}


class LLM:
    """Shared async client pool. One instance per process."""

    def __init__(self, ledger: Ledger, concurrency: dict[str, int] | None = None):
        self.models = load_models()
        self.ledger = ledger
        self._clients: dict[tuple[str, str], AsyncOpenAI] = {}
        conc = concurrency or {}
        self._sems = {k: asyncio.Semaphore(conc.get(k, 8)) for k in self.models}

    def _client(self, spec: ModelSpec) -> AsyncOpenAI:
        """Clients are created on first use, so a missing key only matters for the models you actually call."""
        if "$" in spec.base_url:
            raise RuntimeError(f"model {spec.key}: endpoint {spec.base_url!r} has an unset variable; set it in .env")
        key = os.environ.get(spec.api_key_env)
        if not key:
            raise RuntimeError(f"model {spec.key}: {spec.api_key_env} is not set (in .env or the environment)")
        ck = (spec.base_url, spec.api_key_env)
        if ck not in self._clients:
            self._clients[ck] = AsyncOpenAI(api_key=key, base_url=spec.base_url, timeout=300, max_retries=0)
        return self._clients[ck]

    async def chat(self, model_key: str, messages: list[dict], purpose: str, tools: list | None = None,
                   max_attempts: int = 6, **overrides):
        spec = self.models[model_key]
        params = {**spec.params, **overrides}
        client = self._client(spec)
        last = None
        for attempt in range(1, max_attempts + 1):
            self.ledger.check()
            t0 = time.time()
            try:
                async with self._sems[model_key]:
                    kw = dict(model=spec.model, messages=messages, **params)
                    if tools:
                        kw.update(tools=tools, tool_choice="auto")
                    resp = await client.chat.completions.create(**kw)
            except (RateLimitError, APITimeoutError, APIConnectionError) as e:
                last = e
            except APIStatusError as e:
                body = str(getattr(e, "body", "") or e)
                if "content_filter" in body or "ResponsibleAIPolicyViolation" in body or "jailbreak" in body.lower():
                    raise ContentFiltered(body[:500]) from e
                if e.status_code < 500 and e.status_code != 429:
                    raise
                last = e
            else:
                choice = resp.choices[0]
                if choice.finish_reason == "content_filter":
                    raise ContentFiltered(f"{model_key}: completion filtered")
                cost = usage_cost(spec, resp.usage)
                self.ledger.record({"ts": time.time(), "model": model_key, "purpose": purpose,
                                    "latency_s": round(time.time() - t0, 2), **cost})
                return resp
            wait = min(60, 2 ** attempt) * (0.5 + random.random())
            log.warning("%s call failed (%s: %s); retry %d/%d in %.0fs", model_key, type(last).__name__,
                        str(last)[:160], attempt, max_attempts, wait)
            await asyncio.sleep(wait)
        raise RuntimeError(f"{model_key}: giving up after {max_attempts} attempts: {last}")
