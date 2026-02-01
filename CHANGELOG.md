# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-02-02

### Added
- **Publisher filtering for keyword search**: Added `supported_only` parameter (default: True) to `search_journals_by_keyword`
  - Automatically filters results to only show Elsevier and Springer journals
  - Adds `publisher_normalized` and `is_supported` fields to all journal results
  - Users can set `supported_only=False` to see all publishers with support status indicators
- **Publisher support verification**: Added `is_supported` field to `get_publisher()` results
  - Clearly indicates whether a journal can be automatically searched for CFPs
  - Provides user-friendly error messages for unsupported publishers
- **Automatic publisher validation in search_cfp**: Now checks publisher support before attempting to scrape
  - Returns informative error message if publisher is not Elsevier or Springer
  - Suggests using `get_publisher()` first for verification
- **Springer journal ID extraction**: Automatically extracts Springer journal IDs from OpenAlex homepage URLs
  - Enables direct construction of journal-specific CFP collection pages
  - Improves reliability of Springer journal searches
- Test scripts: `test_keyword_filter.py`, `test_wiley_id.py`, `test_wiley_url_validity.py`
- Added BMC Biology and Cellular and Molecular Life Sciences to journal registry

### Changed
- **Clarified supported publishers**: Officially limited support to Elsevier and Springer only
  - Updated all documentation to reflect IEEE and Wiley are not supported
  - Reason: Anti-scraping measures and lack of centralized CFP hubs
- **Updated `list_supported_publishers()`**: Now only returns Elsevier and Springer
  - Added clear documentation about publisher limitations
  - Updated return message to explain workflow requirements
- **Enhanced MCP tool descriptions**: Added workflow guidance and support status to all tools
  - `search_cfp()`: Emphasizes using `get_publisher()` first
  - `get_publisher()`: Marked as FIRST step in workflow
  - `search_journals_by_keyword()`: Updated to reflect default filtering behavior
- **Improved Springer parser**: Enhanced heading detection to support both `<h2>` and `<h3>` elements
- **Updated search flow**: For Springer journals, now attempts to construct journal-specific URLs using IDs from OpenAlex
- **Documentation overhaul**:
  - README.md: Updated features, workflows, and examples to reflect supported publishers only
  - CLAUDE.md: Added recommended workflows and clarified publisher support status
  - All tools now include explicit workflow guidance

### Fixed
- **Publisher support transparency**: Users now receive clear feedback about which journals can be searched
- **Workflow consistency**: Standardized the recommended workflow across all documentation and tool descriptions
- **Error messaging**: Improved error messages to guide users toward correct usage patterns

### Removed
- **Wiley CFP link construction**: Removed experimental Wiley URL construction due to 403 Forbidden responses
  - Wiley has strong anti-scraping measures that prevent programmatic access
  - Cannot reliably verify or construct CFP URLs for Wiley journals

## [0.1.0] - 2026-02-01

### Added
- **Cross-journal keyword search**: `search_journals_by_keyword` MCP tool for topic-based journal discovery
- **Topic-based search mode**: Search journals by research topic (not just journal name) using OpenAlex Works API
- **Quality ranking system**: Results sorted by citation rate (citations per paper, similar to Impact Factor)
- **Smart filtering**: Automatically excludes preprint servers (arXiv, bioRxiv, Zenodo) and non-journal sources
- **Citation metrics**: Added `citation_rate` field as quality indicator for journal ranking
- **Topic relevance tracking**: Shows number of papers each journal published on the search topic
- Initial MCP server implementation for Call for Papers retrieval
- Support for Springer Nature journal CFP scraping
- Support for Elsevier/ScienceDirect with JSON extraction
- Automatic caching system with 24-hour TTL
- Generic fallback parser for unsupported publishers
- Journal registry system for publisher mapping
- Playwright integration for dynamic page handling
- Search tool for finding CFPs by journal name
- Scraper tool for direct URL parsing
- OpenAlex API integration for automatic journal publisher identification
- `get_publisher` MCP tool for identifying journal publishers
- Publisher name normalization system supporting Elsevier, Springer, Wiley, IEEE
- Smart fallback mechanism: registry → OpenAlex API → default
- Test suite for OpenAlex API integration (test_openalex_api.py)

### Changed
- Enhanced `search_journal_cfp` to automatically detect publisher for journals not in registry
- Updated Config class with OpenAlex API methods and publisher normalization
- **Improved `search_journals_by_keyword`**: Now uses Works API for true topic-based search instead of name matching
- **Increased default `min_works` threshold**: From 100 to 500 to focus on established journals
- **Updated sorting algorithm**: Primary sort by citation rate, secondary by topic relevance
- Extended OpenAlex timeout to 30 seconds for complex queries

### Fixed
- **Filtered out non-journal sources**: Removed arXiv, Zenodo, SSRN from journal search results
- **Improved journal type detection**: Added strict `type='journal'` filter to exclude conferences and repositories
- Parser framework (base, Springer, Elsevier, generic)
- Configuration and cache utilities
- Test suite for parsers and tools
- Documentation (README, IMPLEMENTATION_PLAN)

### Changed

### Fixed

### Removed
