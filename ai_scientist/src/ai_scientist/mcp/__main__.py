"""`python -m ai_scientist.mcp` — stdio MCP server for Cursor / Claude Code."""

from .server import main

if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
