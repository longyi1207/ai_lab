"""A hard spending cap for every billed API call.

Each call's token usage is converted to dollars with the price table in the config and appended
to ``spend.jsonl``. On start-up the ledger is read back, so the cap covers the whole run across
restarts, not just the current process. When the total reaches ``max_usd``, ``check()`` raises
``BudgetExceeded`` and the calling stage stops cleanly; finished work is already on disk.

Prices are estimates you set in the config (USD per 1M tokens). If a model has no entry, the most
expensive configured price is used, so a missing price can only make the cap trigger early.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0


class Budget:
    def __init__(self, max_usd: float, prices: dict[str, dict[str, float]], ledger: Path):
        self.max_usd = float(max_usd)
        self.prices = prices
        self.ledger = Path(ledger)
        self._lock = threading.Lock()
        self._spent = 0.0
        if self.ledger.is_file():
            for line in self.ledger.read_text().splitlines():
                if line.strip():
                    self._spent += float(json.loads(line).get("usd", 0.0))

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def remaining(self) -> float:
        return max(0.0, self.max_usd - self._spent)

    def price_for(self, model: str) -> dict[str, float]:
        matches = [k for k in self.prices if model.startswith(k)]
        if matches:
            return self.prices[max(matches, key=len)]
        if not self.prices:
            raise BudgetExceeded("no prices configured; refusing to make billed calls")
        # Unknown model: charge the most expensive configured rate (fails safe).
        return max(self.prices.values(), key=lambda p: p.get("output", 0) + p.get("input", 0))

    def cost(self, model: str, usage: Usage) -> float:
        p = self.price_for(model)
        uncached = max(0, usage.input_tokens - usage.cached_input_tokens)
        return (uncached * p.get("input", 0.0)
                + usage.cached_input_tokens * p.get("cached_input", p.get("input", 0.0))
                + usage.output_tokens * p.get("output", 0.0)) / 1e6

    def check(self) -> None:
        if self._spent >= self.max_usd:
            raise BudgetExceeded(f"budget reached: ${self._spent:.2f} of ${self.max_usd:.2f}")

    def record(self, model: str, usage: Usage, *, purpose: str, usd: float | None = None) -> float:
        usd = self.cost(model, usage) if usd is None else usd
        rec = {"t": round(time.time(), 3), "model": model, "purpose": purpose, "usd": round(usd, 6),
               "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
               "cached_input_tokens": usage.cached_input_tokens}
        with self._lock:
            self._spent += usd
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger.open("a") as f:
                f.write(json.dumps(rec) + "\n")
        return usd

    def summary(self) -> dict[str, float]:
        by_purpose: dict[str, float] = {}
        if self.ledger.is_file():
            for line in self.ledger.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    by_purpose[r["purpose"]] = by_purpose.get(r["purpose"], 0.0) + r["usd"]
        return {"total_usd": round(self._spent, 4), "max_usd": self.max_usd,
                **{f"usd_{k}": round(v, 4) for k, v in sorted(by_purpose.items())}}
