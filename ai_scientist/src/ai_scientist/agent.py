"""Host-style agent loop: skills as files + tools as callables.

This matches how Cursor / Claude Code use skills — not “stuff SKILL.md into
complete(system='Skill: id')”.

- **Skills** are local markdown playbooks the agent can *read* (`read_skill`).
- **Tools** are registered functions with JSON schemas (same idea as MCP tools).
- **System prompt** describes the agent role + skill catalog + tool list.
- **User message** is the human utterance (optionally: “use skill X”).

Headless workers and `sci ask` share this runtime. The IDE path does not need it:
Cursor already is the agent; it discovers `.cursor/skills/` and calls MCP tools.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .llm import LLMClient, LLMResponse, get_llm
from .skills_loader import Skill, SkillRegistry

ToolHandler = Callable[..., Any]


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AgentTurn:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None


@dataclass
class AgentResult:
    text: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    model_used: str = "unavailable"
    parsed: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "tool_trace": self.tool_trace,
            "model_used": self.model_used,
            "parsed": self.parsed,
        }


def _parse_json_loose(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
    if start >= 0:
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            return None
    return None


class Agent:
    """Minimal tool-calling agent with optional skill access."""

    def __init__(
        self,
        *,
        role: str,
        llm: LLMClient | None = None,
        skills: SkillRegistry | None = None,
        tools: list[ToolSpec] | None = None,
        max_rounds: int = 8,
        temperature: float = 0.2,
        expect_json: bool = False,
    ) -> None:
        self.role = role.strip()
        self.llm = llm or get_llm()
        self.skills = skills or SkillRegistry().load()
        self.tools = {t.name: t for t in (tools or [])}
        # Always offer read_skill so the model can load playbooks like an IDE agent.
        if "read_skill" not in self.tools:
            self.tools["read_skill"] = ToolSpec(
                name="read_skill",
                description=(
                    "Read a local skill playbook by id (e.g. outer_route, ops_triage). "
                    "Call this before following a skill's procedure."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": f"One of: {', '.join(self.skills.ids())}",
                        }
                    },
                    "required": ["skill_id"],
                },
                handler=self._tool_read_skill,
            )
        self.max_rounds = max_rounds
        self.temperature = temperature
        self.expect_json = expect_json

    def _tool_read_skill(self, skill_id: str) -> dict[str, Any]:
        skill = self.skills.get(skill_id)
        return {
            "id": skill.id,
            "role": skill.role,
            "description": skill.description,
            "tools_declared": skill.tools,
            "path": str(skill.path),
            "body": skill.body,
        }

    def _system_prompt(self, *, hint_skill: str | None = None) -> str:
        catalog = [
            {"id": s.id, "description": s.description, "role": s.role}
            for s in self.skills.all()
        ]
        tool_lines = [
            f"- {name}: {spec.description}" for name, spec in sorted(self.tools.items())
        ]
        parts = [
            self.role,
            "",
            "You are a tool-using agent. Skills are local files — read them with "
            "`read_skill` when you need a playbook. Do not invent tool results.",
            "",
            "Accessible skills:",
            json.dumps(catalog, indent=2),
            "",
            "Available tools:",
            *tool_lines,
        ]
        if hint_skill:
            parts += [
                "",
                f"Active skill hint: {hint_skill}",
                f"Call read_skill(skill_id={hint_skill!r}) before acting unless the skill "
                "body was already provided in the conversation.",
            ]
        if self.expect_json:
            parts += ["", "When finished, reply with a single JSON object only (no markdown)."]
        return "\n".join(parts)

    def run(
        self,
        user_message: str,
        *,
        hint_skill: str | None = None,
        preload_skill: bool = False,
    ) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt(hint_skill=hint_skill)},
            {"role": "user", "content": user_message.strip()},
        ]
        if preload_skill and hint_skill:
            # Headless convenience: attach skill body once so FakeLLM / cheap models
            # need not issue read_skill. IDE agents should still call read_skill.
            skill = self.skills.get(hint_skill)
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"[preloaded skill `{skill.id}` from {skill.path}]\n\n{skill.body}"
                    ),
                }
            )

        trace: list[dict[str, Any]] = []
        final_text = ""
        for _ in range(self.max_rounds):
            turn = self._chat(messages)
            if turn.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": turn.text or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in turn.tool_calls
                        ],
                    }
                )
                for tc in turn.tool_calls:
                    result = self._dispatch(tc)
                    trace.append(
                        {"tool": tc.name, "arguments": tc.arguments, "result": result}
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, default=str),
                        }
                    )
                continue
            final_text = (turn.text or "").strip()
            break

        parsed = _parse_json_loose(final_text) if self.expect_json else None
        return AgentResult(
            text=final_text,
            messages=messages,
            tool_trace=trace,
            model_used=getattr(self.llm, "name", "model"),
            parsed=parsed,
        )

    def _dispatch(self, call: ToolCall) -> Any:
        spec = self.tools.get(call.name)
        if spec is None:
            return {"error": f"unknown tool {call.name!r}"}
        try:
            return spec.handler(**call.arguments)
        except TypeError:
            # tolerate models stuffing a single "input" blob
            return spec.handler(call.arguments)  # type: ignore[misc]
        except Exception as exc:  # noqa: BLE001
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _chat(self, messages: list[dict[str, Any]]) -> AgentTurn:
        schemas = [t.openai_schema() for t in self.tools.values()]
        chat = getattr(self.llm, "chat", None)
        if callable(chat):
            raw = chat(messages, tools=schemas, temperature=self.temperature)
            if isinstance(raw, AgentTurn):
                return raw
            if isinstance(raw, LLMResponse):
                if raw.tool_calls:
                    return _turn_from_dict(
                        {"content": raw.text, "tool_calls": raw.tool_calls}
                    )
                # FakeLLM may put a tool-call script in text JSON.
                try:
                    payload = raw.json()
                    if isinstance(payload, dict) and payload.get("tool_calls"):
                        return _turn_from_dict(payload)
                except Exception:  # noqa: BLE001
                    pass
                return AgentTurn(text=raw.text)
            if isinstance(raw, dict):
                return _turn_from_dict(raw)
        # Fallback: legacy complete(system, user)
        system = next((m["content"] for m in messages if m.get("role") == "system"), "")
        user_parts = [
            m.get("content", "")
            for m in messages
            if m.get("role") in {"user", "tool"} and m.get("content")
        ]
        reply = self.llm.complete(
            system,
            "\n\n".join(str(p) for p in user_parts),
            temperature=self.temperature,
            json_mode=self.expect_json,
        )
        if reply.tool_calls:
            return _turn_from_dict({"content": reply.text, "tool_calls": reply.tool_calls})
        try:
            payload = reply.json()
        except Exception:  # noqa: BLE001
            return AgentTurn(text=reply.text)
        if isinstance(payload, dict) and "tool_calls" in payload:
            return _turn_from_dict(payload)
        return AgentTurn(text=reply.text)


def _turn_from_dict(payload: dict[str, Any]) -> AgentTurn:
    calls: list[ToolCall] = []
    for i, item in enumerate(payload.get("tool_calls") or []):
        if not isinstance(item, dict):
            continue
        args = item.get("arguments") or item.get("args") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"raw": args}
        calls.append(
            ToolCall(
                id=str(item.get("id") or f"call_{i}"),
                name=str(item.get("name") or item.get("function", {}).get("name") or ""),
                arguments=args if isinstance(args, dict) else {},
            )
        )
    return AgentTurn(text=payload.get("content") or payload.get("text"), tool_calls=calls)


def skill_catalog_tool(skills: SkillRegistry) -> ToolSpec:
    """Optional extra tool: list skills without reading bodies."""

    def handler() -> list[dict[str, str]]:
        return [{"id": s.id, "description": s.description, "role": s.role} for s in skills.all()]

    return ToolSpec(
        name="list_skills",
        description="List accessible skill ids and descriptions.",
        parameters={"type": "object", "properties": {}},
        handler=handler,
    )


def run_skilled(
    skill_id: str,
    user_message: str,
    *,
    role: str,
    llm: LLMClient | None = None,
    skills: SkillRegistry | None = None,
    tools: list[ToolSpec] | None = None,
    expect_json: bool = True,
    temperature: float = 0.2,
    max_rounds: int = 6,
    preload_skill: bool = True,
) -> AgentResult:
    """Run a focused headless agent that follows one skill playbook.

    Context belongs in ``user_message`` (and/or tools) — not stuffed into the skill file.
    The skill body is a procedure the agent reads; tools are the hands.
    """
    agent = Agent(
        role=role.strip(),
        llm=llm,
        skills=skills,
        tools=tools,
        max_rounds=max_rounds,
        temperature=temperature,
        expect_json=expect_json,
    )
    return agent.run(
        user_message,
        hint_skill=skill_id,
        preload_skill=preload_skill,
    )


def context_block(tag: str, payload: Any) -> str:
    """Wrap runtime context for the user message (skill files stay placeholder-free)."""
    if isinstance(payload, (dict, list)):
        body = json.dumps(payload, indent=2, default=str)
    else:
        body = str(payload)
    return f"<{tag}>\n{body}\n</{tag}>"


__all__ = [
    "Agent",
    "AgentResult",
    "AgentTurn",
    "ToolCall",
    "ToolSpec",
    "context_block",
    "run_skilled",
    "skill_catalog_tool",
]
