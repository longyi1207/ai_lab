"""Resource accounting: turn a job's resource request into concrete lock names.

Named locks (`gpu:0`, `api:3`) are primary keys in the state db, so acquisition is
atomic and a crashed daemon leaves visible, releasable rows rather than lost capacity.
"""

from __future__ import annotations

from ..schema import ResourcePool, ResourceRequest


class InsufficientResources(RuntimeError):
    pass


class ResourceBroker:
    def __init__(self, pool: ResourcePool) -> None:
        self.pool = pool

    @property
    def gpu_names(self) -> list[str]:
        return [f"gpu:{i}" for i in self.pool.gpus]

    @property
    def api_names(self) -> list[str]:
        return [f"api:{i}" for i in range(self.pool.api_slots)]

    def capacity(self) -> dict[str, int]:
        return {"gpu": len(self.pool.gpus), "api": self.pool.api_slots}

    def satisfiable(self, request: ResourceRequest) -> bool:
        """Could this ever run on this machine's declared pool?"""
        cap = self.capacity()
        return request.gpu <= cap["gpu"] and request.api_slots <= cap["api"]

    def plan_locks(self, request: ResourceRequest, held: set[str]) -> list[str] | None:
        """Pick free lock names for the request, or None if capacity is busy right now."""
        if not self.satisfiable(request):
            raise InsufficientResources(
                f"request gpu={request.gpu} api={request.api_slots} exceeds pool {self.capacity()}"
            )
        chosen: list[str] = []
        for names, count in ((self.gpu_names, request.gpu), (self.api_names, request.api_slots)):
            free = [n for n in names if n not in held]
            if len(free) < count:
                return None
            chosen.extend(free[:count])
        return chosen
