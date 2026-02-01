# Test Scripts for call4paper

This directory contains test scripts and sample data for validating the CFP scraping functionality.

## Test Files

### Interactive Testing

#### `test_search_local.py`
Interactive testing tool for searching CFPs by journal name.

**Features:**
- Displays journal registry information
- Shows supported publishers
- Allows selection of journal by number or name input
- Displays CFP results with full details

**Usage:**
```bash
python test_search_local.py
# Enter journal number or name when prompted
```

### Automated Tests

#### `test_filter.py`
Tests the journal filtering logic for Elsevier browse page.

**What it tests:**
- Fetches and parses the Elsevier browse page
- Filters CFPs by journal name ("Energy and Buildings" by default)
- Displays filtered results

**Usage:**
```bash
python test_filter.py
```

**Expected output:**
```
期刊: Energy and Buildings
总数: 10
返回数量: 10
```

#### `test_parser_output.py`
Analyzes the parser's output to check journal name extraction.

**What it tests:**
- Parses the browse page HTML
- Counts CFPs per journal
- Identifies journals with "Test" fallback names
- Lists energy/building related journals

**Usage:**
```bash
python test_parser_output.py
```

### JSON Extraction Tests

#### `test_initial_state.py`
Validates extraction of `window.INITIAL_STATE` JSON from the browse page.

**What it tests:**
- Locates the script tag containing JSON data
- Extracts and parses the JSON structure
- Navigates to callsForPapers.cfpList
- Displays sample CFPs and counts Energy and Buildings entries

**Usage:**
```bash
python test_initial_state.py
```

#### `test_json_parse.py`
Tests JSON parsing from saved HTML (outdated - superseded by test_initial_state.py).

#### `check_scripts.py`
Inspects all script tags in the HTML to find JSON data.

**What it tests:**
- Lists all script tags and their properties
- Identifies scripts containing journal data
- Shows script sizes and content previews

### Proxy and Anti-Scraping Tests

#### `test_proxy_url.py`
Tests access to Elsevier through HKU proxy vs. direct access.

**What it tests:**
- Direct access to browse page
- HKU proxy access (eproxy.lib.hku.hk)
- Compares status codes and content length

**Usage:**
```bash
python test_proxy_url.py
```

#### `test_proxy_detail.py`
Examines proxy response details.

### Debug Scripts

#### `debug_browse_page.py`
Saves and analyzes the browse page HTML structure.

**What it does:**
- Fetches the browse page
- Saves to `browse_page.html`
- Counts special-issue links
- Displays sample link structure

#### `debug_filter.py`
Debugs the filtering mechanism to check journal name extraction.

**What it tests:**
- Parses all CFPs from browse page
- Displays first 20 with journal names
- Searches for specific journal terms

## Sample Data

### `browse_page.html`
Sample Elsevier browse page HTML (1.4MB) containing:
- ~2700 CFPs from all Elsevier journals
- Embedded JSON data in `window.INITIAL_STATE`
- Used for offline testing without hitting the server

## Test Results Summary

### Working Features ✅
- JSON extraction from `window.INITIAL_STATE` (2725 CFPs)
- Journal name extraction from JSON (displayName field)
- Filtering by journal name with aliases
- Deadline parsing (ISO format)
- Impact factor and CiteScore extraction
- Guest editor extraction from summary field

### Known Issues
- ~188 CFPs fallback to "Test" journal name when JSON extraction fails
- HTML parsing fallback less reliable than JSON method

## Running All Tests

```bash
# Interactive test
python test_search_local.py

# Automated filtering test
python test_filter.py

# Parser analysis
python test_parser_output.py

# JSON extraction test
python test_initial_state.py

# Proxy test (requires network)
python test_proxy_url.py
```

## Development Notes

### Key Findings

1. **JSON is the Best Source**
   - `window.INITIAL_STATE` contains all CFP data
   - Structure: `data.callsForPapers.cfpList`
   - Each item has complete metadata including journal info

2. **Browse Page Structure**
   - Single unified page for all Elsevier journals
   - ~1.4MB HTML with embedded JSON
   - Direct fetch works (no Cloudflare blocking observed)

3. **Filtering Strategy**
   - Extract all 2700+ CFPs first
   - Filter client-side by journal name
   - Use exact matching + aliases for accuracy

4. **Cloudflare Not an Issue**
   - Previous concern about blocking was resolved
   - Server-side rendered JSON is accessible
   - No JavaScript execution needed

### Test-Driven Development

These tests were created during the development process to:
1. Understand the page structure
2. Validate JSON extraction
3. Test filtering accuracy
4. Debug journal name extraction
5. Compare proxy vs. direct access

The iterative testing approach helped identify and fix:
- Incorrect JSON path (initially looked for `browsePageData`)
- Date type mismatch (Date object vs. string)
- Over-broad filtering logic
- Journal name overwriting in filtered results
