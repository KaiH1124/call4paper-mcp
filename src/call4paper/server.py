"""MCP Server for Call for Papers retrieval."""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .tools.search import search_journal_cfp, get_cfp_details, list_supported_publishers, BotProtectionError
from .models.cfp import CFPList, CallForPaper
from .utils.config import Config

# Initialize FastMCP server
mcp = FastMCP("call4paper")


@mcp.tool()
async def search_cfp(journal_name: str, count: int = 5, enrich_details: bool = False) -> str:
    """Search for Call for Papers (Special Issues) for an academic journal.

    IMPORTANT: Use get_publisher() first to verify journal name and publisher support!
    Only Elsevier and Springer journals are supported.
    
    Recommended workflow:
    1. Call get_publisher(journal_name) to get accurate name and publisher
    2. Check if publisher is "Elsevier" or "Springer" 
    3. If supported, use the accurate journal name from get_publisher() result
    4. Call this tool with the verified journal name

    Args:
        journal_name: Exact name of the journal (e.g., "Energy and Buildings",
                     "Information Sciences", "Applied Energy")
        count: Maximum number of CFP entries to return (default: 5)
        enrich_details: Fetch each detail page to fill accurate deadlines (default: False)

    Returns:
        JSON string containing CFP information including:
        - title: Special issue topic/title
        - deadline: Submission deadline
        - url: Link to the CFP page
        - description: Brief description
        - accessibility: Whether submission is open or invite-only
    """
    try:
        # Check publisher support first
        publisher_info = await Config.get_publisher_from_openalex(journal_name)
        if publisher_info:
            normalized_publisher = publisher_info.get("publisher", "unknown")
            if normalized_publisher not in ["elsevier", "springer"]:
                return json.dumps({
                    "error": "Publisher not supported",
                    "journal_name": publisher_info.get("journal_name", journal_name),
                    "publisher": publisher_info.get("publisher_raw", "Unknown"),
                    "supported_publishers": ["Elsevier", "Springer"],
                    "message": f"This journal is published by {publisher_info.get('publisher_raw', 'an unsupported publisher')}. Only Elsevier and Springer journals are currently supported due to anti-scraping measures on other publishers."
                }, indent=2)
        
        cfp_list = await search_journal_cfp(
            journal_name,
            count=count,
            enrich_details=enrich_details,
        )
        return cfp_list.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "journal_name": journal_name,
            "message": "Failed to retrieve CFP information. Use get_publisher() first to verify the journal name and publisher."
        }, indent=2)


@mcp.tool()
async def get_cfp_detail(cfp_url: str, journal_name: str = "") -> str:
    """Get detailed information about a specific Call for Papers.

    Use this tool to retrieve comprehensive details about a specific CFP
    after getting the URL from search_cfp.

    Args:
        cfp_url: URL of the CFP detail page
        journal_name: Optional journal name for better parsing

    Returns:
        JSON string containing detailed CFP information including:
        - title: Full title of the special issue
        - deadline: Submission deadline
        - guest_editors: List of guest editors
        - topics: List of topics covered
        - description: Full description
        - submission_url: Direct submission link
    """
    try:
        cfp = await get_cfp_details(cfp_url, journal_name)
        if cfp:
            return cfp.model_dump_json(indent=2)
        return json.dumps({
            "error": "Could not parse CFP details",
            "url": cfp_url,
            "message": "Please visit the URL directly for more information."
        }, indent=2)
    except BotProtectionError:
        return json.dumps({
            "error": "bot_protection",
            "url": cfp_url,
            "message": "Automated access was blocked by the publisher. Please visit the URL directly for full details."
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "url": cfp_url,
            "message": "Failed to retrieve CFP details."
        }, indent=2)


@mcp.tool()
def list_publishers() -> str:
    """List all supported academic publishers.

    Currently Elsevier, Springer, and Nature Collections are supported due to
    anti-scraping measures on IEEE and Wiley websites that lack centralized search hubs.

    Returns:
        JSON string containing list of supported publishers with their domains:
        - Elsevier: sciencedirect.com (unified browse page with ~2700 CFPs)
        - Springer: link.springer.com (journal-specific collection pages)
    """
    publishers = list_supported_publishers()
    return json.dumps({
        "supported_publishers": publishers,
        "total": len(publishers),
        "note": "Only Elsevier, Springer, and Nature Collections are supported. IEEE and Wiley have anti-scraping measures without centralized CFP hubs.",
        "workflow": "Use get_publisher() to check if a journal is supported before calling search_cfp()."
    }, indent=2)


@mcp.tool()
async def get_publisher(journal_name: str) -> str:
    """Identify the publisher of a journal using OpenAlex API.
    
    IMPORTANT: Always use this tool FIRST before calling search_cfp()!
    
    This tool:
    1. Verifies the exact journal name from OpenAlex's 249,000+ journal database
    2. Identifies the publisher
    3. Checks if the publisher is supported (only Elsevier and Springer)
    
    Workflow:
    - For journal name query: get_publisher() → check if supported → search_cfp()
    - For keyword query: search_journals_by_keyword() → get_publisher() → search_cfp()
    
    Args:
        journal_name: Name of the journal to identify (e.g., "Nature", 
                     "IEEE Access", "Information Sciences")
    
    Returns:
        JSON string containing publisher information including:
        - journal_name: Official name of the journal (use this for search_cfp)
        - publisher_raw: Raw publisher name from OpenAlex
        - publisher: Normalized identifier (elsevier/springer/wiley/ieee/other)
        - issn: ISSN identifier
        - works_count: Number of published works
        - cited_by_count: Total citations
        
    Note: Only "elsevier" and "springer" publishers are currently supported.
    """
    try:
        info = await Config.get_publisher_from_openalex(journal_name)
        if info:
            normalized_publisher = info.get("publisher", "unknown")
            is_supported = normalized_publisher in ["elsevier", "springer"]
            info["is_supported"] = is_supported
            info["supported_publishers"] = ["Elsevier", "Springer"]
            if not is_supported:
                info["note"] = f"This journal's publisher ({info.get('publisher_raw', 'Unknown')}) is not supported. Only Elsevier and Springer journals can be searched for CFPs."
            return json.dumps(info, indent=2)
        return json.dumps({
            "error": "Journal not found",
            "journal_name": journal_name,
            "message": "Could not find this journal in OpenAlex database. Try a different spelling or full journal name."
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "journal_name": journal_name,
            "message": "Failed to retrieve publisher information."
        }, indent=2)


@mcp.tool()
async def search_journals_by_keyword(
    keyword: str,
    max_results: int = 15,
    min_works: int = 500,
    mode: str = "topic",
    supported_only: bool = True
) -> str:
    """Search for academic journals by keyword or research topic.
    
    This tool enables cross-journal CFP discovery by searching for journals
    that publish papers on specific topics. Results are sorted by quality
    (citation rate, similar to Impact Factor).
    
    Args:
        keyword: Research topic or keyword (e.g., "machine learning", "renewable energy",
                "blockchain", "computer vision")
        max_results: Maximum journals to return (default: 15, max: 50)
        min_works: Minimum published papers to filter quality journals (default: 500)
        mode: "topic" (search by research topic, default) or "name" (search journal names)
        supported_only: Only return Elsevier/Springer journals (default: True)
    
    Returns:
        JSON string with journal list sorted by citation rate (quality indicator):
        - journal_name: Official name (use with search_cfp tool)
        - publisher: Publisher name
        - publisher_normalized: Standardized publisher identifier (elsevier/springer/wiley/ieee/other)
        - is_supported: Whether CFPs can be automatically retrieved
        - citation_rate: Citations per paper (quality metric, like Impact Factor)
        - works_count: Total published papers
        - cited_by_count: Total citations
        - topic_papers_count: (topic mode) Papers on this specific topic
        
    Recommended workflow:
        1. search_journals_by_keyword("deep learning") → Get supported journals only
        2. Pick high-citation-rate journals (e.g., "Neural Networks")
        3. search_cfp("Neural Networks") → Get CFPs directly
    
    Note: Results exclude preprint servers (arXiv, bioRxiv) and only include
          peer-reviewed journals. By default, only Elsevier and Springer journals
          are returned (supported_only=True). Set to False to see all journals.
    """
    try:
        # Validate parameters
        max_results = min(max(1, max_results), 50)
        min_works = max(100, min_works)  # Minimum 100 to ensure quality
        mode = mode.lower() if mode in ["topic", "name"] else "topic"
        
        results = await Config.search_journals_by_keyword(
            keyword=keyword,
            max_results=max_results * 3 if supported_only else max_results,  # Fetch more to filter
            min_works=min_works,
            mode=mode
        )
        
        if not results:
            return json.dumps({
                "keyword": keyword,
                "search_mode": mode,
                "filter": "supported_only" if supported_only else "all",
                "total_found": 0,
                "journals": [],
                "message": "No journals found. Try different keywords or lower min_works threshold."
            }, indent=2)
        
        # Filter by supported publishers if requested
        if supported_only:
            # Add publisher normalization to each result
            filtered_results = []
            for journal in results:
                publisher_raw = journal.get("publisher_raw", "")
                normalized = Config.normalize_publisher_name(publisher_raw)
                journal["publisher_normalized"] = normalized
                journal["is_supported"] = normalized in ["elsevier", "springer"]
                
                if journal["is_supported"]:
                    filtered_results.append(journal)
                    if len(filtered_results) >= max_results:
                        break
            
            results = filtered_results
        else:
            # Add metadata even when not filtering
            for journal in results:
                publisher_raw = journal.get("publisher_raw", "")
                normalized = Config.normalize_publisher_name(publisher_raw)
                journal["publisher_normalized"] = normalized
                journal["is_supported"] = normalized in ["elsevier", "springer"]
        
        return json.dumps({
            "keyword": keyword,
            "search_mode": mode,
            "filter": "supported_only" if supported_only else "all",
            "total_found": len(results),
            "journals": results,
            "note": "Results sorted by citation rate (quality). Only Elsevier and Springer journals shown." if supported_only else "Results include all publishers. Only Elsevier and Springer can be automatically searched."
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "keyword": keyword,
            "message": "Failed to search journals by keyword."
        }, indent=2)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
