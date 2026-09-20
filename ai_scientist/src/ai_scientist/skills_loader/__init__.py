"""Skill loading (SPEC §6).

Skills are the portable half of the system: markdown playbooks with YAML frontmatter
that work in an IDE host (Cursor / Claude Code) *and* inside daemon workers. The loader
is deliberately dumb — it discovers, validates, and renders; it never executes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)

REQUIRED_KEYS = ("description",)  # id/name + role filled with fallbacks


class SkillError(ValueError):
    pass


@dataclass
class Skill:
    id: str
    role: str
    description: str
    tools: list[str]
    outputs: list[str]
    body: str
    path: Path
    name: str = ""  # Cursor-facing name (may equal id)

    def render(self, **variables: object) -> str:
        """Substitute `{{var}}` placeholders; unknown placeholders are an error.

        Prefer the Agent + `read_skill` path for new code. `render` remains for
        headless prompt-pack call sites that have not migrated yet.
        """
        text = self.body
        for key, value in variables.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        leftover = re.findall(r"\{\{(\w+)\}\}", text)
        if leftover:
            raise SkillError(f"{self.id}: unfilled placeholders {sorted(set(leftover))}")
        return text.strip()

    @property
    def placeholders(self) -> list[str]:
        return sorted(set(re.findall(r"\{\{(\w+)\}\}", self.body)))


def parse_skill(path: Path) -> Skill:
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(raw)
    if not match:
        raise SkillError(f"{path}: missing YAML frontmatter")
    meta = yaml.safe_load(match.group(1)) or {}
    if not meta.get("description"):
        raise SkillError(f"{path}: frontmatter missing description")
    # Cursor uses `name`; our registry uses `id`. Accept either.
    skill_id = str(meta.get("id") or meta.get("name") or path.parent.name).replace("-", "_")
    name = str(meta.get("name") or skill_id)
    role = str(meta.get("role") or "general")
    tools = [str(t) for t in meta.get("tools", [])]
    # MCP tool names declared for IDE hosts (informational; Agent registers real tools in code).
    tools += [str(t) for t in meta.get("mcp_tools", []) if str(t) not in tools]
    return Skill(
        id=skill_id,
        name=name,
        role=role,
        description=str(meta["description"]).strip(),
        tools=tools,
        outputs=[str(o) for o in meta.get("outputs", [])],
        body=match.group(2),
        path=path,
    )


def default_skills_dir() -> Path:
    # repo layout: <pkg>/src/ai_scientist/skills_loader/__init__.py → <pkg>/skills
    return Path(__file__).resolve().parents[3] / "skills"


class SkillRegistry:
    def __init__(self, directory: str | Path | None = None) -> None:
        self.directory = Path(directory) if directory else default_skills_dir()
        self._skills: dict[str, Skill] = {}

    def load(self) -> SkillRegistry:
        self._skills.clear()
        if not self.directory.exists():
            raise SkillError(f"skills directory not found: {self.directory}")
        for path in sorted(self.directory.glob("*/SKILL.md")):
            skill = parse_skill(path)
            if skill.id in self._skills:
                raise SkillError(f"duplicate skill id {skill.id!r}")
            self._skills[skill.id] = skill
        return self

    def __len__(self) -> int:
        return len(self._skills)

    def ids(self) -> list[str]:
        return sorted(self._skills)

    def get(self, skill_id: str) -> Skill:
        if not self._skills:
            self.load()
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise SkillError(f"unknown skill {skill_id!r}; have {self.ids()}") from exc

    def all(self) -> list[Skill]:
        if not self._skills:
            self.load()
        return [self._skills[i] for i in self.ids()]


__all__ = ["Skill", "SkillError", "SkillRegistry", "default_skills_dir", "parse_skill"]
