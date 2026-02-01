# call4paper MCP Server - Implementation Plan

## Project Overview

Build an MCP server to retrieve Special Issue Call for Papers information from academic journals. Users input a journal name, and the system locates the official CFP page and extracts key information.

---

## 1. Project File Structure

```
call4paper/
├── pyproject.toml              # Project configuration and dependencies
├── README.md                   # Project documentation
├── src/
│   └── call4paper/
│       ├── __init__.py
│       ├── server.py           # MCP server main entry
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── search.py       # Journal search and location tool
│       │   └── scraper.py      # CFP page scraping tool
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py         # Parser base class
│       │   ├── elsevier.py     # Elsevier journal parser
│       │   ├── springer.py     # Springer journal parser
│       │   ├── ieee.py         # IEEE journal parser
│       │   ├── wiley.py        # Wiley journal parser
│       │   └── generic.py      # Generic parser (fallback)
│       ├── models/
│       │   ├── __init__.py
│       │   └── cfp.py          # CFP data model
│       └── utils/
│           ├── __init__.py
│           ├── cache.py        # Cache management
│           └── config.py       # Configuration management
├── data/
│   └── journal_registry.json   # Pre-configured journal URL mappings
└── tests/
    └── ...
```

---

## 2. Core Functional Modules

### 2.1 MCP Tools (Exposed to AI)

| Tool Name | Description | Input Parameters |
|-----------|-------------|------------------|
| `search_journal_cfp` | Main entry: Search journal CFP page and return list | journal_name, count (optional, default 5) |
| `get_cfp_details` | Get detailed information of a single CFP | cfp_url |
| `list_supported_publishers` | List supported publishers | None |

### 2.2 Data Model (CFP Info)

```python
class CallForPaper:
    title: str              # Special Issue title/Topic
    journal_name: str       # Journal name
    publisher: str          # Publisher
    deadline: str           # Submission deadline
    guest_editors: list     # List of guest editors
    topics: list            # List of call topics
    accessibility: str      # "open" | "invite_only" | "unknown"
    url: str                # Original CFP link
    description: str        # Brief description
    submission_url: str     # Submission link (if available)
```

---

## 3. Overall Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                   User calls search_journal_cfp                  │
│                      (Input: journal name)                       │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Journal Location                                         │
│ ├─ Check if local journal_registry.json has pre-configured URL   │
│ └─ If not, use search engine to locate official CFP page         │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Publisher Identification                                 │
│ ├─ Identify publisher by URL domain (elsevier/springer/ieee/etc) │
│ └─ Select corresponding specialized parser                       │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Page Retrieval                                           │
│ ├─ Static pages: Use httpx + BeautifulSoup                       │
│ └─ Dynamic pages: Use Playwright (JavaScript rendering)          │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Content Parsing                                          │
│ ├─ Use specialized parser to extract CFP list                    │
│ ├─ Extract: topic, deadline, accessibility, guest_editors, etc.  │
│ └─ If specialized parser fails, fallback to generic parser       │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Result Return                                            │
│ ├─ Sort by deadline (nearest first)                              │
│ ├─ Return top N results                                          │
│ └─ Format as structured JSON                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Technology Selection

### 4.1 MCP Framework
- **Choice**: Python + FastMCP
- **Reason**: High development efficiency, concise decorator syntax, suitable for rapid prototyping

### 4.2 Web Retrieval Tools

| Tool | Purpose | Scenario |
|------|---------|----------|
| `httpx` | HTTP client | Static page retrieval |
| `playwright` | Browser automation | JavaScript dynamic rendering pages |

### 4.3 Page Parsing Tools

| Tool | Purpose |
|------|---------|
| `beautifulsoup4` | HTML parsing |
| `lxml` | High-performance XML/HTML parsing |

### 4.4 Journal Location Strategy

| Strategy | Implementation | Priority |
|----------|----------------|----------|
| Pre-configured mapping | Maintain journal_registry.json | 1 (Optimal) |
| Search location | DuckDuckGo/Google Search API | 2 (Fallback) |

### 4.5 Dependency List

```toml
[project]
dependencies = [
    "mcp[cli]",           # MCP SDK
    "httpx",              # HTTP client
    "beautifulsoup4",     # HTML parsing
    "lxml",               # HTML parsing acceleration
    "playwright",         # Dynamic pages
    "pydantic",           # Data validation
]
```

---

## 5. Major Publisher CFP Page Patterns

| Publisher | CFP Page URL Pattern | Page Type | Example
|-----------|---------------------|-----------| -----------|
| Elsevier | `https://www.sciencedirect.com/journal/{journal_name}/about/call-for-papers` | Static | `https://www.sciencedirect.com/journal/building-and-environment/about/call-for-papers` (alternative: through hub search https://www.sciencedirect.com/browse/calls-for-papers)
| Springer | `springer.com/journal/{id}/updates` | Partially dynamic |
| IEEE | `ieee.org/publications/special-issues` | Dynamic |
| Wiley | `onlinelibrary.wiley.com/journal/{id}` | Mixed |
| Taylor & Francis | `tandfonline.com/journals/{id}` | Static |

---

## 6. Design Decisions (Confirmed)

| Decision Item | Choice |
|---------------|--------|
| Publisher scope | Support 4 major publishers first: Elsevier, Springer, IEEE, Wiley |
| Parse failure handling | Return original URL, let user view manually |
| Caching strategy | Local cache with 24-hour validity |

---

## 7. Implementation Priority

### Phase 1 - MVP (Core Functionality)
- [ ] Project initialization (pyproject.toml, directory structure)
- [ ] MCP server basic framework (FastMCP)
- [ ] CFP data model (Pydantic)
- [ ] `search_journal_cfp` tool interface
- [ ] Elsevier parser
- [ ] Basic journal_registry.json (10-20 common journals)
- [ ] 24-hour local caching mechanism

### Phase 2 - Major Publisher Support
- [ ] Springer parser
- [ ] IEEE parser
- [ ] Wiley parser
- [ ] Generic parser (fallback, returns URL)

### Phase 3 - Enhancement (Optional)
- [ ] Search engine fallback location (DuckDuckGo)
- [ ] More publisher support
- [ ] `list_supported_publishers` tool

---

## 8. Verification Methods

1. **Unit Tests**: Test cases for each publisher parser
2. **Integration Tests**: Connect MCP server with Claude Desktop, verify tool invocation
3. **Manual Verification**:
   - Call `search_journal_cfp("Information Sciences")`
   - Verify returned CFP information matches official website
