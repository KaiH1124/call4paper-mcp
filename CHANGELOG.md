# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Removed

## [0.1.0] - 2026-02-01

### Added
- Project initialization
- Basic MCP server structure
- Parser framework (base, Springer, Elsevier, generic)
- Configuration and cache utilities
- Test suite for parsers and tools
- Documentation (README, IMPLEMENTATION_PLAN)

### Changed

### Fixed

### Removed
