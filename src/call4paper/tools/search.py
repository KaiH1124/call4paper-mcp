"""Search and retrieval tools for CFP information."""

from typing import Optional

from ..models.cfp import CallForPaper, CFPList
from ..parsers import (
    BaseParser,
    ElsevierParser,
    SpringerParser,
    IEEEParser,
    WileyParser,
    GenericParser,
)
from ..utils.cache import CacheManager
from ..utils.config import Config
from .scraper import fetch_page, fetch_page_with_curl, fetch_page_dynamic, is_playwright_available, get_playwright_install_hint


# Parser registry in order of priority
PARSER_CLASSES: list[type[BaseParser]] = [
    ElsevierParser,
    SpringerParser,
    IEEEParser,
    WileyParser,
]

# Cache instance
_cache = CacheManager()


def get_parser_for_url(url: str, journal_name: str) -> BaseParser:
    """Get appropriate parser for a given URL.

    Args:
        url: The CFP page URL
        journal_name: Name of the journal

    Returns:
        Parser instance suitable for the URL
    """
    for parser_class in PARSER_CLASSES:
        if parser_class.can_handle(url):
            return parser_class(journal_name)

    # Fallback to generic parser
    return GenericParser(journal_name, url)


async def search_journal_cfp(
    journal_name: str,
    count: int = 5,
    use_cache: bool = True,
) -> CFPList:
    """Search for Call for Papers for a given journal.

    This is the main entry point for CFP searches.
    Uses ScienceDirect's browse page and filters by journal name.

    Args:
        journal_name: Name of the journal to search
        count: Maximum number of CFP entries to return
        use_cache: Whether to use cached results

    Returns:
        CFPList containing found CFP entries
    """
    # Check cache first
    cache_key = f"cfp_list:{journal_name.lower()}"
    if use_cache:
        cached = _cache.get(cache_key)
        if cached:
            cfp_list = CFPList(**cached)
            cfp_list.items = cfp_list.items[:count]
            return cfp_list

    # Use ScienceDirect's unified browse page for Elsevier journals
    # This approach avoids 404s and allows filtering by journal name
    cfp_url = "https://www.sciencedirect.com/browse/calls-for-papers"
    publisher = "Elsevier"

    # Try to find journal in registry for better metadata
    journal_info = Config.get_cfp_url_for_journal(journal_name)
    if journal_info:
        publisher = journal_info.get("publisher", "Elsevier")
        # Still use browse page even if journal is in registry
        # Only use specific journal URL if explicitly configured
        if journal_info.get("use_specific_url", False):
            cfp_url = journal_info.get("cfp_url", cfp_url)
    else:
        # If not in registry, try OpenAlex API to identify publisher
        openalex_info = await Config.get_publisher_from_openalex(journal_name)
        if openalex_info:
            detected_publisher = openalex_info.get("publisher", "unknown")
            
            # Update publisher and CFP URL based on detected publisher
            if detected_publisher == "springer":
                publisher = "Springer"
                # Use generic Springer collections page
                cfp_url = "https://link.springer.com/search?facet-content-type=%22Collection%22&facet-discipline=%22Computer+Science%22"
            elif detected_publisher == "wiley":
                publisher = "Wiley"
                # Use generic Wiley special issues page if available
                cfp_url = "https://onlinelibrary.wiley.com/"
            elif detected_publisher == "ieee":
                publisher = "IEEE"
                cfp_url = "https://ieee.org/publications/special-issues"
            elif detected_publisher == "elsevier":
                publisher = "Elsevier"
                # Keep default ScienceDirect browse page
            else:
                # Unknown publisher, keep default Elsevier browse page
                # It will likely return no results, but that's expected
                pass

    # Fetch the page - try multiple methods
    html, error = await fetch_page(cfp_url)

    # If httpx fails (often due to TLS fingerprint detection), try curl
    if html is None and error == "blocked":
        html, curl_error = await fetch_page_with_curl(cfp_url)
        if html is None:
            error = curl_error  # Update error for logging

    # If still no content, try Playwright as last resort
    if html is None:
        if error in ("blocked", "curl_error", "curl_not_available"):
            html, pw_error = await fetch_page_dynamic(cfp_url)
            if html is None:
                # Provide helpful error message based on error type
                if pw_error == "playwright_not_installed":
                    hint = get_playwright_install_hint()
                    description = f"The website blocked automated access. {hint}"
                elif pw_error == "playwright_browser_not_installed":
                    description = "Run 'playwright install chromium' to enable browser access."
                elif pw_error == "bot_protection":
                    description = (
                        "This website uses CAPTCHA/bot protection that requires manual access. "
                        "Please visit the URL directly in your browser."
                    )
                else:
                    description = f"Could not access page: {pw_error}. Please visit the URL directly."

                return CFPList(
                    journal_name=journal_name,
                    publisher=publisher,
                    cfp_page_url=cfp_url,
                    items=[
                        CallForPaper(
                            title=f"CFP page for {journal_name} (manual access required)",
                            journal_name=journal_name,
                            publisher=publisher,
                            url=cfp_url,
                            description=description,
                            accessibility="unknown",
                        )
                    ],
                    total_count=0,
                )
        else:
            # Other errors - return URL for manual access
            return CFPList(
                journal_name=journal_name,
                publisher=publisher,
                cfp_page_url=cfp_url,
                items=[
                    CallForPaper(
                        title=f"CFP page for {journal_name}",
                        journal_name=journal_name,
                        publisher=publisher,
                        url=cfp_url,
                        description=f"Could not fetch automatically ({error}). Please visit the URL directly.",
                        accessibility="unknown",
                    )
                ],
                total_count=0,
            )

    # Parse the page
    parser = get_parser_for_url(cfp_url, journal_name)
    cfp_list = parser.parse_cfp_list(html, cfp_url)

    # Filter by journal name if using browse page
    if "browse/calls-for-papers" in cfp_url:
        cfp_list = _filter_by_journal(cfp_list, journal_name)

    # Sort by deadline
    cfp_list.sort_by_deadline()

    # Cache the results
    if use_cache and cfp_list.items:
        _cache.set(cache_key, cfp_list.model_dump())

    # Return limited results
    cfp_list.items = cfp_list.items[:count]

    return cfp_list


async def get_cfp_details(cfp_url: str, journal_name: str = "") -> Optional[CallForPaper]:
    """Get detailed information for a specific CFP.

    Args:
        cfp_url: URL of the CFP detail page
        journal_name: Optional journal name for context

    Returns:
        CallForPaper with detailed information, or None if fetch/parse fails
    """
    # Check cache
    cache_key = f"cfp_detail:{cfp_url}"
    cached = _cache.get(cache_key)
    if cached:
        return CallForPaper(**cached)

    # Fetch page
    html, error = await fetch_page(cfp_url)
    if html is None:
        if error == "blocked":
            html, _ = await fetch_page_dynamic(cfp_url)

    if html is None:
        return None

    # Parse with appropriate parser
    parser = get_parser_for_url(cfp_url, journal_name or "Unknown Journal")
    cfp = parser.parse_cfp_detail(html, cfp_url)

    # Cache result
    if cfp:
        _cache.set(cache_key, cfp.model_dump())

    return cfp


def _construct_cfp_url(journal_name: str) -> Optional[str]:
    """Try to construct a CFP URL from journal name.

    This is a fallback when journal is not in registry.
    Now returns the unified browse page instead of journal-specific URL.
    """
    # Use ScienceDirect's unified browse page
    # This avoids 404 errors from incorrect journal slugs
    return "https://www.sciencedirect.com/browse/calls-for-papers"


def _filter_by_journal(cfp_list: CFPList, journal_name: str) -> CFPList:
    """Filter CFP list by journal name.

    Args:
        cfp_list: Complete CFP list from browse page
        journal_name: Target journal name to filter for

    Returns:
        Filtered CFP list containing only items matching the journal
    """
    # Normalize journal name for matching
    normalized_target = journal_name.lower().strip()
    
    # Also get aliases from registry
    aliases = [normalized_target]
    journal_info = Config.get_cfp_url_for_journal(journal_name)
    if journal_info:
        aliases.extend([alias.lower() for alias in journal_info.get("aliases", [])])
    
    # Create variations of journal names (with and without common words)
    search_terms = set()
    for alias in aliases:
        search_terms.add(alias)
        # Also add without "journal", "the", etc.
        cleaned = alias.replace("journal of", "").replace("the", "").strip()
        if cleaned and cleaned != alias:
            search_terms.add(cleaned)
    
    filtered_items = []
    for item in cfp_list.items:
        # Check if item's journal name matches target (exact or partial)
        item_journal_lower = item.journal_name.lower() if item.journal_name else ""
        
        # Try exact or partial match in journal name field
        matched = False
        for term in search_terms:
            # Require a more precise match
            # Either exact match or the search term is a substantial part
            if term == item_journal_lower:
                # Exact match (ignoring case)
                matched = True
                break
            elif len(term) > 10 and term in item_journal_lower:
                # Substring match for longer terms (>10 chars)
                matched = True
                break
        
        if matched:
            # IMPORTANT: Do NOT overwrite journal_name - keep original for debugging
            # item.journal_name stays as-is from parser
            filtered_items.append(item)
    
    # Return filtered list
    return CFPList(
        journal_name=journal_name,
        publisher=cfp_list.publisher,
        cfp_page_url=cfp_list.cfp_page_url,
        items=filtered_items,
        total_count=len(filtered_items),
    )


def list_supported_publishers() -> list[dict]:
    """List all supported publishers and their domains.

    Returns:
        List of publisher information dicts
    """
    publishers = []

    for parser_class in PARSER_CLASSES:
        publishers.append({
            "name": parser_class.publisher_name,
            "domains": parser_class.supported_domains,
        })

    return publishers
