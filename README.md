# Greenhouse MCP Server

An MCP server for the public Greenhouse Job Board API. It is designed for polling job boards, normalizing job data, and checking whether postings expose salary, experience-level, and workplace-type signals.

## Features

- Public read-only Greenhouse Job Board integration
- Normalized job output for downstream storage and diffing
- Salary and metadata inspection for individual job postings
- Typed responses with Pydantic models

## Installation

### Using mpak

```bash
mpak run @JoeCardoso13/greenhouse
```

### Manual Installation

```bash
git clone https://github.com/JoeCardoso13/mcp-greenhouse.git
cd mcp-greenhouse
uv sync --dev
uv run python -m mcp_greenhouse.server
```

## Configuration

Runtime configuration is not required for the public GET endpoints used by this server.

For live integration tests, set a board token in `.env` or your shell:

```bash
export GREENHOUSE_BOARD_TOKEN=your_board_token
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "greenhouse": {
      "command": "mpak",
      "args": ["run", "@JoeCardoso13/greenhouse"]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_job_board` | Fetch the board-level name and intro content |
| `list_company_jobs` | List current public Greenhouse jobs |
| `get_job_details` | Fetch a single job with optional question and pay data |
| `list_departments` | List departments and associated jobs |
| `list_offices` | List offices and associated departments/jobs |
| `normalize_job_data` | Convert public jobs into a stable normalized schema |
| `inspect_job_attributes` | Check salary, experience-level, and workplace-type coverage |
| `list_new_or_updated_jobs` | Detect new or changed jobs from a prior snapshot |

## Development

```bash
uv sync --dev
make check
```

Integration tests require `GREENHOUSE_BOARD_TOKEN`. LLM smoke tests require `ANTHROPIC_API_KEY`.

## License

MIT
