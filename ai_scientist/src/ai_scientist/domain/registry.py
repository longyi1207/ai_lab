"""Domain pack resolution.

Built-in packs are registered by id. External packs can be referenced as
`module:factory` (e.g. `domains.oversight_debate.pack:build`) so a pack can live outside
this package without touching the harness.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable

from .base import DomainPack

_BUILTINS: dict[str, str] = {
    "fake_toy": "ai_scientist.domain.fake_toy:build",
    "oversight_debate": "ai_scientist.domain.oversight_debate.pack:build",
}

_CACHE: dict[str, DomainPack] = {}


class DomainNotFound(KeyError):
    pass


def register(domain_id: str, target: str) -> None:
    _BUILTINS[domain_id] = target
    _CACHE.pop(domain_id, None)


def available() -> list[str]:
    return sorted(_BUILTINS)


def load_domain(domain_id: str, *, use_cache: bool = True) -> DomainPack:
    if use_cache and domain_id in _CACHE:
        return _CACHE[domain_id]
    target = _BUILTINS.get(domain_id, domain_id)
    if ":" not in target:
        raise DomainNotFound(
            f"unknown domain {domain_id!r}; known: {available()} "
            "(or pass 'module:factory' for an external pack)"
        )
    module_name, factory_name = target.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise DomainNotFound(f"cannot import domain module {module_name!r}: {exc}") from exc
    factory: Callable[[], DomainPack] = getattr(module, factory_name)
    pack = factory()
    if not isinstance(pack, DomainPack):
        raise TypeError(f"{target} did not produce a DomainPack")
    _CACHE[domain_id] = pack
    return pack
