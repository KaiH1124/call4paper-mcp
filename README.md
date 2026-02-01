# call4paper MCP Server

An MCP (Model Context Protocol) server for retrieving academic journal Call for Papers (CFP) information.

## Features

- Search for Special Issue Call for Papers by journal name
- Support for major academic publishers:
  - **Springer Nature** ✅ (fully working)
  - **Elsevier/ScienceDirect** ✅ (fully working - unified browse page with JSON extraction)
  - IEEE (planned)
  - Wiley (planned)
- Automatic caching with 24-hour TTL
- Fallback generic parser for unsupported publishers
- Smart JSON extraction from dynamically loaded pages

## Installation

```bash
# Using uv (recommended)
cd call4paper
uv sync

# Optional: Install Playwright for dynamic pages
uv sync --extra browser
uv run playwright install chromium
```

## Usage

### As MCP Server

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "call4paper": {
      "command": "uv",
      "args": ["--directory", "/path/to/call4paper", "run", "call4paper"]
    }
  }
}
```

### Available Tools

#### `search_cfp`
Search for Call for Papers for a journal.

```
Input:
- journal_name: Name of the journal (e.g., "Building Simulation")
- count: Maximum results to return (default: 5)

Output: JSON with CFP entries including title, deadline, URL, description
```

#### `get_cfp_detail`
Get detailed information about a specific CFP.

```
Input:
- cfp_url: URL of the CFP page
- journal_name: Optional journal name

Output: JSON with detailed CFP info including guest editors, topics, submission URL
```

#### `list_publishers`
List supported publishers.

```
Output: JSON with supported publishers and their domains
```

## Supported Journals

### Springer Nature
| Journal | CFP URL |
|---------|---------|
| Building Simulation | https://link.springer.com/journal/12273/collections?filter=Open |
| Energy Efficiency | https://link.springer.com/journal/12053/collections?filter=Open |
| Machine Learning | https://link.springer.com/journal/10994/collections?filter=Open |
| Neural Computing and Applications | https://link.springer.com/journal/521/collections?filter=Open |
| Neural Computing and Applications | https://link.springer.com/journal/521/collections?filter=Open |
| Applied Intelligence | https://link.springer.com/journal/10489/collections?filter=Open |

### Elsevier/ScienceDirect
Elsevier journals are now fully supported through the unified browse page.

| Journal | CFP URL |
|---------|---------|
| Energy and Buildings | https://www.sciencedirect.com/browse/calls-for-papers |
| Building and Environment | https://www.sciencedirect.com/browse/calls-for-papers |
| Applied Energy | https://www.sciencedirect.com/browse/calls-for-papers |
| Information Sciences | https://www.sciencedirect.com/browse/calls-for-papers |

**Note**: All Elsevier journals use the same unified browse page, with automatic filtering by journal name.

## Implementation Details

### Elsevier/ScienceDirect Parser

The Elsevier parser uses a sophisticated two-stage approach:

#### 1. JSON Data Extraction (Primary Method)
- **Target**: Extracts data from `window.INITIAL_STATE` embedded in the page
- **Data Structure**: 
  ```javascript
  window.INITIAL_STATE = {
    callsForPapers: {
      cfpList: [
        {
          title: "CFP Title",
          journal: {
            displayName: "Journal Name",
            impactFactor: "7.1",
            citeScore: "12.6",
            issn: "03787788"
          },
          url: "cfp-url-slug",
          submissionDeadline: "2026-02-15",
          summary: "Guest editors: ..."
        }
        // ... 2700+ CFPs
      ]
    }
  }
  ```
- **Advantages**:
  - Reliable: Data is pre-rendered by server
  - Complete: Includes all metadata (journal name, impact factor, deadlines)
  - Fast: No need to scrape HTML elements
  - ~2700+ CFPs available across all Elsevier journals

#### 2. HTML Parsing (Fallback)
- Triggers if JSON extraction fails
- Scrapes `<li class="publication">` elements
- Less reliable but provides basic CFP information

#### 3. Client-Side Filtering
- After extracting all CFPs from browse page, filters by target journal name
- Uses exact matching and aliases from registry
- Preserves original journal names for debugging

#### Workflow
```
User Query: "Energy and Buildings"
    ↓
1. Fetch browse page (https://www.sciencedirect.com/browse/calls-for-papers)
    ↓
2. Extract window.INITIAL_STATE JSON (~1.4MB)
    ↓
3. Parse cfpList (2700+ CFPs from all journals)
    ↓
4. Filter by journal name: "Energy and Buildings"
    ↓
5. Return matched CFPs (typically 10-20 per journal)
```

#### Why This Approach Works
- **Bypasses Cloudflare**: Direct page fetch works (no JavaScript execution needed)
- **No Bot Detection**: Server-side rendered JSON is accessible
- **Scalable**: Single request serves all Elsevier journals
- **Maintainable**: JSON structure is stable

### Testing

Test scripts are available in `tests/` directory:

- `test_search_local.py`: Interactive testing tool with registry display
- `test_filter.py`: Tests journal filtering logic
- `test_parser_output.py`: Analyzes parser extraction results
- `test_initial_state.py`: Validates JSON extraction from browse page
- `browse_page.html`: Sample page for offline testing (1.4MB)

Run tests:
```bash
cd tests
python test_search_local.py  # Interactive mode
python test_filter.py         # Automated filtering test
```

## Example

```python
import asyncio
from call4paper.tools.search import search_journal_cfp

async def main():
    # Search for CFPs
    result = await search_journal_cfp("Building Simulation", count=3)
    print(f"Found {result.total_count} CFPs")
    for cfp in result.items:
        print(f"- {cfp.title}")
        print(f"  Deadline: {cfp.deadline}")
        print(f"  URL: {cfp.url}")

asyncio.run(main())
```

## Project Structure

```
call4paper/
├── src/call4paper/
│   ├── server.py           # MCP server entry point
│   ├── tools/              # Search and scraping tools
│   ├── parsers/            # Publisher-specific parsers
│   ├── models/             # Data models (Pydantic)
│   └── utils/              # Cache and config utilities
├── data/
│   └── journal_registry.json   # Pre-configured journal URLs
└── tests/
```

## Adding New Journals

Edit `data/journal_registry.json` to add new journal mappings:

```json
{
  "name": "Journal Name",
  "aliases": ["alias1", "alias2"],
  "publisher": "springer",
  "cfp_url": "https://link.springer.com/journal/{id}/collections?filter=Open",
  "journal_id": "12345"
}
```

## Development

```bash
# Install dev dependencies
uv sync --extra browser

# Run tests
uv run pytest

# Run server directly
uv run call4paper
```

## Known Limitations

1. **Elsevier Journal Name Matching**: Some CFPs may have journal names listed as "Test" if not properly extracted from HTML fallback. JSON extraction method resolves this issue.

2. **Guest Editor Extraction**: May include false positives in some cases. Guest editors are extracted from summary field when available.

3. **Deadline Parsing**: Handles ISO format dates (YYYY-MM-DD) from Elsevier JSON. Other formats may require additional parsing logic.

> **Local Execution Only**  
> This MCP server runs **locally on your machine**. There is no centralized API or server.  
> All requests are made directly from your computer to journal websites (Elsevier, Springer, etc.).  
> Your data and search history stay on your local machine.

## License

MIT
