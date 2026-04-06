# Greenhouse MCP Server

MCP server providing access to the public Greenhouse Job Board API via FastMCP.

## Structure

```text
src/mcp_greenhouse/
├── api_client.py
├── api_models.py
├── server.py
└── SKILL.md
```

## Notes

- Package name: `@JoeCardoso13/greenhouse`
- Runtime entry point: `python -m mcp_greenhouse.server`
- No API key is required for the read-only endpoints used by this server
- Integration tests use `GREENHOUSE_BOARD_TOKEN`
