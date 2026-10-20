"""One MiniLab-lite world = one Docker container. All agents of a team share it.

Agents' bash commands run as their own Linux account via `docker exec -u`. The
container has no network. Standing processes run inside it via lab-ticker, started as labsvc.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

log = logging.getLogger(__name__)

IMAGE = "minilab-lite:0.2"   # 0.1 = pilot v1 (no runner latency, schema-2 docs without job_can_read_records)
MAX_OUTPUT = 6000


def truncate(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n[... {len(text) - limit} characters omitted ...]\n{text[-half:]}"


async def _run(*argv: str, timeout: float = 120, stdin: bytes | None = None) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *argv, stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(stdin), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, f"[harness timeout after {timeout}s]"
    return proc.returncode, out.decode("utf-8", errors="replace")


class Sandbox:
    def __init__(self, image: str = IMAGE, tick_seconds: float = 2.0, label: str = "run",
                 env: dict[str, str] | None = None):
        self.image = image
        self.tick_seconds = tick_seconds
        self.env = {"MINILAB_TICK_SECONDS": str(tick_seconds), **(env or {})}
        self._env_args = [x for k, v in self.env.items() for x in ("-e", f"{k}={v}")]
        self.name = f"minilab-{label}-{uuid.uuid4().hex[:8]}"
        self.started = False

    async def start(self) -> None:
        rc, out = await _run("docker", "run", "-d", "--rm", "--network", "none", "--hostname", "minilab",
                             "--memory", "768m", "--cpus", "1", "--pids-limit", "256",
                             *self._env_args, "--name", self.name, self.image)
        if rc != 0:
            raise RuntimeError(f"docker run failed: {out.strip()}")
        self.started = True
        await self._checked("docker", "exec", "-u", "root", self.name, "sh", "-c",
                            "echo '127.0.0.1 minilab' >> /etc/hosts")
        await self._checked("docker", "exec", "-d", "-u", "labsvc", *self._env_args, self.name,
                            "/usr/local/bin/lab-ticker")
        log.debug("sandbox %s started", self.name)

    async def _checked(self, *argv: str) -> str:
        rc, out = await _run(*argv)
        if rc != 0:
            raise RuntimeError(f"{' '.join(argv[:4])}... failed ({rc}): {out.strip()}")
        return out

    async def bash(self, user: str, command: str, timeout: int = 60) -> tuple[int, str]:
        """Run an agent's command as its account. The timeout is enforced inside the container too."""
        rc, out = await _run("docker", "exec", "-u", user, "-w", f"/home/{user}", self.name,
                             "timeout", "-k", "5", str(timeout), "bash", "-lc", command, timeout=timeout + 15)
        if rc == 124:
            out += f"\n[command timed out after {timeout}s]"
        return rc, truncate(out)

    async def admin(self, *args: str) -> str:
        return await self._checked("docker", "exec", "-u", "labsvc", *self._env_args, self.name,
                                   "/usr/local/bin/lab-core", *args)

    async def finalize(self, ticks: int = 3) -> None:
        """Stop the standing-process loop, then let the world settle: in-flight builds and jobs finish, standing processes run."""
        await _run("docker", "exec", "-u", "root", self.name, "pkill", "-f", "lab-ticker")
        await self.admin("tick", "-n", str(ticks), "--flush")

    async def grade(self, tasks: list[str]) -> list[dict]:
        out = await self.admin("grade", *tasks)
        return [json.loads(line) for line in out.splitlines() if line.startswith("{")]

    async def statelog(self) -> list[dict]:
        out = await self.admin("statelog")
        return [json.loads(line) for line in out.splitlines() if line.startswith("{")]

    async def ticker_errors(self) -> str:
        _, out = await _run("docker", "exec", "-u", "root", self.name, "cat", "/srv/minilab/ticker.err")
        return out if "No such file" not in out else ""

    async def close(self) -> None:
        if self.started:
            await _run("docker", "rm", "-f", self.name)
            self.started = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *exc):
        await self.close()
