"""A disposable Docker container for one rollout.

Each rollout gets a fresh container started with ``--network none``, so the agent can reach only
the services inside its own container and nothing on the internet. Commands run through
``docker exec``, exactly as the original task runners ran them, so a replayed command sees the
same environment the recorded agent saw.

Containers are removed when the ``with`` block exits, and again at interpreter exit in case a
run is interrupted.
"""
from __future__ import annotations

import atexit
import logging
import subprocess
import threading
import uuid

log = logging.getLogger(__name__)

_LIVE: set[str] = set()
_LIVE_LOCK = threading.Lock()


def _cleanup_all() -> None:
    with _LIVE_LOCK:
        names = list(_LIVE)
    for name in names:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


atexit.register(_cleanup_all)


class SandboxError(RuntimeError):
    pass


def docker_available() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


class DockerSandbox:
    def __init__(self, image: str, *, workdir: str = "/app", name_prefix: str = "rlp"):
        self.image = image
        self.workdir = workdir
        self.name = f"{name_prefix}_{uuid.uuid4().hex[:10]}"
        self._started = False

    def __enter__(self) -> "DockerSandbox":
        p = subprocess.run(["docker", "run", "-d", "--name", self.name, "--network", "none", self.image],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise SandboxError(f"docker run {self.image} failed: {p.stderr.strip()[:300]}")
        with _LIVE_LOCK:
            _LIVE.add(self.name)
        self._started = True
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        if self._started:
            subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
            with _LIVE_LOCK:
                _LIVE.discard(self.name)
            self._started = False

    def exec(self, cmd: str, *, user: str | None = None, timeout: int = 60) -> str:
        """Run a shell command; return stdout plus stderr in the original runners' format."""
        if "\x00" in cmd:   # cannot be passed to a process; answer the way a shell error would
            return "[stderr]\nbash: command contains a NUL byte and was not run"
        argv = ["docker", "exec", "-w", self.workdir] + (["-u", user] if user else []) + \
               [self.name, "bash", "-lc", cmd]
        try:
            p = subprocess.run(argv, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return f"[timed out after {timeout}s]"
        out = (p.stdout or b"").decode("utf-8", "replace")
        if p.stderr:
            out += "\n[stderr]\n" + p.stderr.decode("utf-8", "replace")
        return out.strip()

    def copy_in(self, src: str, dst: str) -> None:
        p = subprocess.run(["docker", "cp", src, f"{self.name}:{dst}"], capture_output=True, text=True)
        if p.returncode != 0:
            raise SandboxError(f"docker cp failed: {p.stderr.strip()[:300]}")
