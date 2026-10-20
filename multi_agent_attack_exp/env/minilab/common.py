"""Helpers shared by the service modules."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .store import Refused, Store


@dataclass
class Ctx:
    store: Store
    account: str            # effective account (after --as)
    caller: str             # real Linux account that ran the command
    roles: list[str]
    files: dict[str, str] = field(default_factory=dict)   # --file payload read by the caller-side wrapper

    def require(self, role: str) -> None:
        if role not in self.roles:
            raise Refused(f"account {self.account} does not hold role {role}")


def emit(obj, pretty: bool = False) -> None:
    print(json.dumps(obj, indent=2 if pretty else None, sort_keys=False))


def table(rows: list[dict], cols: list[str]) -> None:
    if not rows:
        print("(none)")
        return
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  ".join(c.upper().ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


__all__ = ["Ctx", "Refused", "emit", "table"]
