"""Control-plane client shared by the CLI and (later) the MCP server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ..fs_layout import Workspace
from ..ops.health import pid_alive
from ..ops.scheduler import worker_env


class DaemonUnavailable(RuntimeError):
    pass


class DaemonClient:
    def __init__(self, project: str | Path) -> None:
        self.ws = Workspace(project)

    # ---- discovery ----
    def info(self) -> dict[str, Any] | None:
        path = self.ws.daemon_info_path
        if not path.exists():
            return None
        try:
            info = json.loads(path.read_text())
        except json.JSONDecodeError:
            return None
        if not pid_alive(info.get("pid")):
            return None
        return info

    @property
    def running(self) -> bool:
        return self.info() is not None

    # ---- rpc ----
    def call(self, method: str, **args: Any) -> Any:
        info = self.info()
        if info is None:
            raise DaemonUnavailable(
                f"no daemon for {self.ws.root} (start it with `sci serve --project <dir>`)"
            )
        url = f"http://{info['host']}:{info['port']}/rpc"
        body = json.dumps({"method": method, "args": args}).encode()
        request = urllib.request.Request(  # noqa: S310 - fixed localhost scheme
            url,
            data=body,
            headers={"Content-Type": "application/json", "X-Sci-Token": info["token"]},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                return json.loads(response.read())["result"]
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            try:
                detail = json.loads(detail).get("error", detail)
            except json.JSONDecodeError:
                pass
            raise DaemonUnavailable(f"control call {method} failed: {detail}") from exc
        except urllib.error.URLError as exc:
            raise DaemonUnavailable(f"control plane unreachable: {exc}") from exc

    # ---- lifecycle ----
    def ensure(self, *, timeout_s: float = 20.0) -> dict[str, Any]:
        """Start a detached daemon if one is not already serving this project."""
        info = self.info()
        if info is not None:
            return info
        log_path = self.ws.state_dir / "daemon.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(log_path, "ab", buffering=0)  # noqa: SIM115 - owned by the child
        subprocess.Popen(
            [sys.executable, "-m", "ai_scientist.daemon", "--project", str(self.ws.root)],
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=worker_env(),
            cwd=str(self.ws.root),
            start_new_session=True,
        )
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            info = self.info()
            if info is not None:
                return info
            time.sleep(0.2)
        raise DaemonUnavailable(f"daemon did not come up; see {log_path}")

    def stop(self, *, timeout_s: float = 10.0) -> bool:
        info = self.info()
        if info is None:
            return False
        try:
            self.call("shutdown")
        except DaemonUnavailable:
            pass
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.info() is None:
                return True
            time.sleep(0.2)
        pid = info.get("pid")
        if pid:
            os.kill(int(pid), 15)
        return self.info() is None
