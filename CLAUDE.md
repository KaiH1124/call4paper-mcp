# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**call4paper** is an MCP (Model Context Protocol) server that retrieves academic journal Call for Papers (CFP) information. Users provide a journal name, and the server locates official CFP pages and extracts submission details (title, deadline, guest editors, topics, accessibility).

## Commands

```bash
# Install dependencies
uv sync

# Install with Playwright for dynamic pages (optional)
uv sync --extra browser
uv run playwright install chromium

# Run MCP server
uv run call4paper

# Run tests
uv run pytest
uv run pytest tests/test_elsevier.py -v

# Interactive testing
python tests/test_search_local.py
```

## Architecture

### MCP Server Entry Point
`src/call4paper/server.py` - FastMCP server exposing three tools:
- `search_cfp(journal_name, count)` - Search CFPs for a journal
- `get_cfp_detail(cfp_url, journal_name)` - Get detailed CFP info
- `list_publishers()` - List supported publishers

### Parser System
All parsers inherit from `BaseParser` (`parsers/base.py`):
```
parsers/
├── base.py       # Abstract class with parse_cfp_list(), parse_cfp_detail()
├── elsevier.py   # JSON extraction from window.INITIAL_STATE (~2700 CFPs)
├── springer.py   # Article element parsing (fully working)
├── ieee.py       # Planned
├── wiley.py      # Planned
└── generic.py    # Fallback for unknown publishers
```

Parser selection in `tools/search.py` uses URL domain matching via `can_handle()`.

### Search Flow (`tools/search.py`)
1. Check 24-hour cache
2. Lookup journal in `data/journal_registry.json`
3. Fetch page (httpx → Playwright fallback if blocked)
4. Route to appropriate parser
5. Filter by journal name, sort by deadline
6. Cache and return results

### Data Models (`models/cfp.py`)
- `CallForPaper` - Single CFP entry with title, deadline, URL, guest_editors, topics
- `CFPList` - Collection with sorting methods

### Scraper (`tools/scraper.py`)
- `fetch_page()` - httpx async client
- `fetch_page_dynamic()` - Playwright for JS-rendered pages
- Bot protection detection (Cloudflare, CAPTCHA) with fallback to manual URL

## Key Implementation Details

**Elsevier Parser**: Extracts `window.INITIAL_STATE` JSON from browse page containing all CFPs, then filters client-side by journal name. Single request serves all Elsevier journals.

**Springer Parser**: Parses `<article>` elements with `<h2>` titles. Extracts deadlines via regex patterns like "31 May 2026".

**Cache**: 24-hour TTL, stored in `~/.cache/call4paper/` with MD5-hashed filenames.

**Journal Registry** (`data/journal_registry.json`): Pre-configured journal URLs with aliases. Currently 15 Elsevier + 5 Springer journals.

## Adding New Journals

Edit `data/journal_registry.json`:
```json
{
  "name": "Journal Name",
  "aliases": ["short name"],
  "publisher": "elsevier|springer",
  "cfp_url": "https://...",
  "journal_slug": "..."
}
```

## Adding New Publishers

1. Create parser in `parsers/{name}.py` inheriting `BaseParser`
2. Implement `parse_cfp_list()` and `parse_cfp_detail()`
3. Add to `PARSER_CLASSES` list in `tools/search.py`
4. Update `PUBLISHER_DOMAINS` in `utils/config.py`

## Known Limitations

- Elsevier/ScienceDirect may be blocked by Cloudflare; returns URL for manual access
- Playwright is optional but needed for some dynamic pages
- Date parsing limited to ISO and English month formats
- Guest editor extraction may have false positives (regex-based)
