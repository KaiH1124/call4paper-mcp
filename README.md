# call4paper MCP Server

An MCP (Model Context Protocol) server for retrieving academic journal Call for Papers (CFP) information.

## Features

- 🔍 Cross-journal keyword search: find journals by research topic (OpenAlex)
- 📰 Journal CFP search: retrieve special-issue CFPs by journal name
- 🏢 Mainstream publisher coverage: Elsevier, Springer, and Nature (more to be added)
- 🧭 Accurate deadlines: detail-page enrichment (especially Nature collections)
- ⚡ Local MCP server with JSON output

## Install (from GitHub)

```bash
# pip
pip install "git+https://github.com/KaiH1124/call4paper-mcp.git"

# uv tool
uv tool install "git+https://github.com/KaiH1124/call4paper-mcp.git"
```

## MCP Config

Use this MCP server as a local stdio process. Pick the client you use:

Claude Desktop (claude_desktop_config.json):

```json
{
  "mcpServers": {
    "call4paper": {
      "command": "call4paper",
      "args": ["serve"]
    }
  }
}
```

Claude Code (CLI add command):

```bash
claude mcp add --transport stdio call4paper -- call4paper serve
```

Codex (config.toml):

```toml
[mcp_servers.call4paper]
command = "call4paper"
args = ["serve"]
```

Codex (CLI add command):

```bash
codex mcp add call4paper -- call4paper serve
```

Where to place these:

- Claude Desktop: Settings -> Developer -> Edit Config, then add under `mcpServers`.
- Claude Code: the CLI add command writes to your MCP config (use the scope flag to choose user/project/local).
- Codex: edit `~/.codex/config.toml` or project `.codex/config.toml`.

## Usage

Example prompts:

> Search CFPs for "Nature Energy" (this year only). Include deadlines and URLs.

> Find journals related to "battery recycling", then search CFPs for the top 3.

> Use keyword search for "microgrids", then fetch CFPs for any supported journals you find.

## Available Tools

- `search_cfp`: Find CFPs for a specific journal.
- `search_journals_by_keyword`: Discover journals by topic/keyword before searching CFPs.
- `get_publisher`: Identify a journal's publisher and support status.
- `get_cfp_detail`: Fetch full details for a specific CFP URL.
- `list_publishers`: Show supported publishers and domains.

## License

MIT
