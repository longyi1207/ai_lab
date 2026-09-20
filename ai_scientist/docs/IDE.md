# IDE setup (Cursor / Claude Code) — the real Outer

`ai_scientist` is **IDE-primary**. The Outer harness agent is **not** `system="Skill: outer_route"`.
It is the host agent (Cursor / Claude Code) with:

1. **Skills** — local `SKILL.md` files the host can discover and read  
2. **Tools** — MCP `sci_*` control-plane tools (and the host’s built-ins)

```text
Human chat
   │
   ▼
Cursor / Claude Code agent
   ├── reads .cursor/skills/ai-scientist-*   (playbooks)
   └── calls MCP sci_status / sci_pause / …  (hands)
          │
          ▼
   ai_scientist daemon (deterministic substrate)
```

## Install (this repo)

Skills are symlinked into the repo’s project skill dir:

```text
.ai_notes/.cursor/skills/ai-scientist-outer-route → code/ai_scientist/skills/outer_route
… (one link per skill)
```

Open the **ai_notes** workspace in Cursor so project skills load. Skill `description`
fields are what the host uses for discovery — edit those when triggers feel wrong.

## MCP

Add a server that runs the package stdio MCP (adjust path / venv):

```json
{
  "mcpServers": {
    "ai-scientist": {
      "command": "/Users/apple/Desktop/ai_notes/code/ai_scientist/.venv/bin/python",
      "args": ["-m", "ai_scientist.mcp", "--project", "/path/to/runs/demo"]
    }
  }
}
```

Cursor: Settings → MCP, or project `.cursor/mcp.json` if your Cursor build supports it.

Tools you should see: `sci_init`, `sci_status`, `sci_start_run`, `sci_run_sync`,
`sci_pause`, `sci_resume`, `sci_set_concurrency`, `sci_elites`, `sci_map`, `sci_pin`,
`sci_ban`, `sci_restart_worker`, `sci_tail`, `sci_events`, `sci_report`, `sci_stop`,
`sci_skills`, `sci_domains`, `sci_ask` (headless Outer fallback).

## Day in the life

1. Chat: “study whether debate beats solo under a weak judge” → host loads
   `phase1_intake` / `design_debate` skills, may call `sci_init` / write specs via CLI.  
2. `sci_start_run` / `sci serve` — daemon runs the fleet.  
3. Anytime: “pause” / “why is job X stuck?” → host uses `outer-route` skill + MCP tools.  
4. `sci_report` when done.

## Headless fallback (`sci ask`)

When there is **no** IDE agent (CI, scripts), `sci ask` runs a small tool-calling
`Agent` with the same skill files + the same control methods. That is a twin of the
IDE Outer, not the primary UX. Prefer Cursor + MCP when you are at the keyboard.

## Skill authoring notes (how we write them)

Drawn from Cursor skill docs + Anthropic/OpenAI agent prompting guidance:

- **description** carries discovery: third person, WHAT + WHEN + trigger phrases.
- **Body = procedure**, not a string template. No `{{placeholders}}`. Runtime context
  arrives in the Agent user message as XML blocks (`<claim>`, `<metrics>`, …) or via tools.
- Sections: when to use / inputs / procedure / hard rules / output schema (+ one example).
- Prefer structured JSON outputs the harness parses; markdown only for writeups/reports/debate.
- Tool guidance lives in the skill and in real MCP/Agent tool schemas — never a fake
  `tools: [control_api]` with no registration.

See also: [Cursor Agent Skills](https://cursor.com/docs/skills.md),
[Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents),
[OpenAI function calling](https://platform.openai.com/docs/guides/function-calling).

## What we deliberately do *not* do

- Stuff `SKILL.md` into `llm.complete(system="Skill: id", …)` as if that were an agent  
- Put only the skill id in the system prompt instead of role + catalog + tools  
- Declare `tools: [control_api]` in frontmatter without registering real MCP/Agent tools  
