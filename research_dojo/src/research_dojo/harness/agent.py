"""Minimal agent harness: a bounded bash-tool loop in a scratch temp workspace.

Demo-grade — no container sandbox, no network policy (the natural next
hardening step: run each rollout in a rootless Docker container with a
default-deny network policy). Exists so the harness interface has a real
second implementation in v1, even though the shipped tom_smoke spec only
exercises BatchChatHarness (spec.harness.kind: batch_chat).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path

from research_dojo.config.settings import azure_openai_client_and_model
from research_dojo.config.spec import ExperimentSpec
from research_dojo.harness.base import HarnessResult, TransientHarnessError, is_transient_error
from research_dojo.harness.batch_chat import DEFAULT_COST_PER_1K_IN, DEFAULT_COST_PER_1K_OUT

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command in the scratch workspace; returns stdout+stderr.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
}

SUBMIT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit",
        "description": "Submit your final answer and stop the loop.",
        "parameters": {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        },
    },
}

SYSTEM_PROMPT = (
    "You may use the `bash` tool in a scratch workspace to investigate, then call "
    "`submit` with your final answer. Call `submit` as soon as you have an answer."
)


class AgentHarness:
    def __init__(self, spec: ExperimentSpec):
        self.spec = spec
        self._client = None
        self._model = None

    def _get_client(self):
        if self._client is None:
            self._client, self._model = azure_openai_client_and_model()
        return self._client, self._model

    def _run_bash(self, workspace: Path, command: str, timeout: int) -> str:
        try:
            proc = subprocess.run(
                command, shell=True, cwd=str(workspace), timeout=timeout,
                capture_output=True, text=True,
            )
            return (proc.stdout + proc.stderr)[-4000:]
        except subprocess.TimeoutExpired:
            return f"[bash timed out after {timeout}s]"
        except Exception as e:  # noqa: BLE001 — a bad command must not crash the rollout
            return f"[bash error: {e}]"

    def _call_model(self, client, model: str, messages: list[dict]):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                tools=[BASH_TOOL, SUBMIT_TOOL],
                temperature=self.spec.model.temperature,
                max_completion_tokens=self.spec.model.max_tokens,
            )
        except Exception as e:  # noqa: BLE001
            if is_transient_error(e):
                raise TransientHarnessError(str(e)) from e
            raise

    def run(self, prompt: str, *, sample_id: str, arm: str) -> HarnessResult:
        client, model = self._get_client()
        max_steps = self.spec.harness.max_steps
        timeout = self.spec.harness.timeout_seconds

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        transcript: list[dict] = [dict(m) for m in messages]
        tokens_in_total = tokens_out_total = 0
        final_answer = ""
        t0 = time.monotonic()

        with tempfile.TemporaryDirectory(prefix="dojo-agent-") as workspace_str:
            workspace = Path(workspace_str)
            for _step in range(max_steps):
                resp = self._call_model(client, model, messages)
                usage = getattr(resp, "usage", None)
                tokens_in_total += getattr(usage, "prompt_tokens", 0) or 0
                tokens_out_total += getattr(usage, "completion_tokens", 0) or 0

                msg = resp.choices[0].message
                tool_calls = list(getattr(msg, "tool_calls", None) or [])
                transcript.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [{"name": tc.function.name, "arguments": tc.function.arguments} for tc in tool_calls],
                })

                if not tool_calls:
                    final_answer = msg.content or ""
                    break

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in tool_calls
                    ],
                })

                submitted = False
                for tc in tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    if tc.function.name == "submit":
                        final_answer = args.get("answer", "")
                        submitted = True
                        tool_result = "submitted"
                    elif tc.function.name == "bash":
                        tool_result = self._run_bash(workspace, args.get("command", ""), timeout)
                    else:
                        tool_result = f"unknown tool {tc.function.name}"
                    transcript.append({"role": "tool", "name": tc.function.name, "content": tool_result})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})
                if submitted:
                    break
            else:
                final_answer = final_answer or "[max_steps reached without submit]"

        latency_ms = (time.monotonic() - t0) * 1000
        cost = (tokens_in_total / 1000) * DEFAULT_COST_PER_1K_IN + (tokens_out_total / 1000) * DEFAULT_COST_PER_1K_OUT
        return HarnessResult(
            completion=final_answer,
            transcript=transcript,
            tokens_in=tokens_in_total,
            tokens_out=tokens_out_total,
            latency_ms=latency_ms,
            cost_usd_est=cost,
        )
