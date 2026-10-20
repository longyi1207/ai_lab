"""Task registry. Add a task by writing a ``Task`` subclass and listing it here."""
from __future__ import annotations

from pathlib import Path

from .base import Cell, Task
from .internal_exfil import InternalExfil
from .protocol_re import ProtocolRE

TASKS: dict[str, type[Task]] = {
    ProtocolRE.name: ProtocolRE,
    InternalExfil.name: InternalExfil,
}

# Filename prefixes the original runners used, for runs that do not record their task.
FILENAME_PREFIXES: dict[str, str] = {
    "protocol_": "protocol_re",
    "kimi_protocol_": "protocol_re",
    "exfil_": "internal_exfil",
}


def get_task(name: str, sse_root: Path) -> Task:
    if name not in TASKS:
        raise KeyError(f"unknown task {name!r}; known: {sorted(TASKS)}")
    return TASKS[name](sse_root)


__all__ = ["Cell", "Task", "TASKS", "FILENAME_PREFIXES", "get_task"]
