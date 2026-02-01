"""MCP Server for Call for Papers retrieval."""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .tools.search import search_journal_cfp, get_cfp_details, list_supported_publishers
from .models.cfp import CFPList, CallForPaper
from .utils.config import Config

# Initialize FastMCP server
mcp = FastMCP("call4paper")


@mcp.tool()
async def search_cfp(journal_name: str, count: int = 5) -> str:
    """Search for Call for Papers (Special Issues) for an academic journal.

    This tool searches for open Call for Papers from academic journal publishers.
    It returns information about special issues including topics, deadlines,
    and submission details.

    Args:
        journal_name: Name of the journal to search (e.g., "Energy and Buildings",
                     "Information Sciences", "Applied Energy")
        count: Maximum number of CFP entries to return (default: 5)

    Returns:
        JSON string containing CFP information including:
        - title: Special issue topic/title
        - deadline: Submission deadline
        - url: Link to the CFP page
        - description: Brief description
        - accessibility: Whether submission is open or invite-only
    """
    try:
        cfp_list = await search_journal_cfp(journal_name, count=count)
        return cfp_list.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "journal_name": journal_name,
            "message": "Failed to retrieve CFP information. Please try again or check the journal name."
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
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "url": cfp_url,
            "message": "Failed to retrieve CFP details."
        }, indent=2)


@mcp.tool()
def list_publishers() -> str:
    """List all supported academic publishers.

    Returns information about which publishers are supported and their
    associated domains.

    Returns:
        JSON string containing list of supported publishers with their domains
    """
    publishers = list_supported_publishers()
    return json.dumps({
        "supported_publishers": publishers,
        "total": len(publishers),
        "note": "Journals from unsupported publishers will use generic parsing."
    }, indent=2)


@mcp.tool()
async def get_publisher(journal_name: str) -> str:
    """Identify the publisher of a journal using OpenAlex API.
    
    This tool helps identify which publisher owns a specific journal,
    which is useful for determining how to retrieve CFP information.
    
    Args:
        journal_name: Name of the journal to identify (e.g., "Nature", 
                     "IEEE Access", "Information Sciences")
    
    Returns:
        JSON string containing publisher information including:
        - journal_name: Official name of the journal
        - publisher_raw: Raw publisher name from OpenAlex
        - publisher: Normalized publisher identifier (elsevier/springer/wiley/ieee)
        - issn: ISSN identifier
        - works_count: Number of published works
        - cited_by_count: Total citations
    """
    try:
        info = await Config.get_publisher_from_openalex(journal_name)
        if info:
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


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
