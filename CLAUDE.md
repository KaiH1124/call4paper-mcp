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
`src/call4paper/server.py` - FastMCP server exposing five tools:
- `search_cfp(journal_name, count)` - Search CFPs for a journal (Elsevier/Springer only)
- `get_cfp_detail(cfp_url, journal_name)` - Get detailed CFP info
- `list_publishers()` - List supported publishers (Elsevier, Springer)
- `get_publisher(journal_name)` - Identify journal's publisher via OpenAlex API (use FIRST!)
- **`search_journals_by_keyword(keyword, max_results, min_works, mode)`** - 🆕 Cross-journal keyword search with quality ranking

**Recommended Workflow**:
1. For journal name: `get_publisher()` → check if Elsevier/Springer → `search_cfp()`
2. For keywords: `search_journals_by_keyword()` → `get_publisher()` → `search_cfp()`

### Parser System
All parsers inherit from `BaseParser` (`parsers/base.py`):
```
parsers/
├── base.py       # Abstract class with parse_cfp_list(), parse_cfp_detail()
├── elsevier.py   # JSON extraction from window.INITIAL_STATE (~2700 CFPs)
├── springer.py   # Article element parsing (fully working)
├── ieee.py       # Not supported - anti-scraping measures
├── wiley.py      # Not supported - anti-scraping measures
└── generic.py    # Fallback for unknown publishers
```

Parser selection in `tools/search.py` uses URL domain matching via `can_handle()`.

**Note**: Only Elsevier and Springer parsers are actively used. IEEE and Wiley have
anti-scraping measures and lack centralized CFP hubs.

### Search Flow (`tools/search.py`)
1. Check 24-hour cache
2. Lookup journal in `data/journal_registry.json`
3. **If not found, query OpenAlex API** to identify publisher (NEW)
4. Fetch page (httpx → Playwright fallback if blocked)
5. Route to appropriate parser
6. Filter by journal name, sort by deadline
7. Cache and return results

### Cross-Journal Search Flow (`utils/config.py` - NEW)
**Topic-based search** (`mode="topic"`, default):
1. Query OpenAlex Works API: search papers by keyword
2. Group results by journal (`group_by=primary_location.source.id`)
3. Fetch journal details for each source
4. Filter: type=journal, min_works threshold, exclude preprints (arXiv, bioRxiv, etc.)
5. Calculate citation_rate = cited_by_count / works_count (quality metric)
6. Sort by citation_rate (primary), topic_papers_count (secondary)
7. Return top journals with quality metrics

**Name-based search** (`mode="name"`):
1. Query OpenAlex Sources API: search journal names
2. Filter and sort by citation_rate

**Key Features**:
- Excludes non-journals: arXiv, Zenodo, SSRN, bioRxiv, conference proceedings
- Quality ranking: citation rate (similar to Impact Factor)
- Topic relevance: tracks papers each journal published on the topic
- Default min_works=500 to ensure established journals

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

**OpenAlex API Integration** (`utils/config.py`): 
- **Publisher detection**: Automatic publisher identification for journals not in registry. Queries OpenAlex's 249,000+ journal database to enable dynamic routing to correct parser without manual configuration.
- **Cross-journal keyword search** 🆕: Topic-based journal discovery using Works API. Finds journals that publish papers on specific topics, ranks by quality (citation rate), and filters out preprint servers. Supports both "topic" mode (search papers by subject) and "name" mode (search journal titles).
- **Quality metrics**: Calculates citation rate (citations per paper) as proxy for Impact Factor
- **Smart filtering**: Excludes arXiv, bioRxiv, Zenodo, SSRN, conferences
- Publisher normalization: Elsevier, Springer, Wiley, IEEE

## Adding New Journals

Journals can be added to the registry for faster lookups, but **OpenAlex API will automatically detect publishers** for any journal not in the list.

Manually edit `data/journal_registry.json` (optional):
```json
{
  "name": "Journal Name",
  "aliases": ["short name"],
  "publisher": "elsevier|springer",
  "cfp_url": "https://...",
  "journal_slug": "..."
}
```

To test publisher detection:
```bash
python tests/test_openalex_api.py
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
