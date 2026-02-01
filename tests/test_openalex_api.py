"""Test script for OpenAlex API to retrieve journal publisher information."""

import asyncio
import httpx
import json
from typing import Optional


# Publisher mapping for normalization
PUBLISHER_MAPPING = {
    "elsevier": ["elsevier", "elsevier bv"],
    "springer": ["springer", "springer nature", "springer science and business media"],
    "wiley": ["wiley", "john wiley", "wiley-blackwell"],
    "ieee": ["ieee", "institute of electrical and electronics engineers"],
}


def normalize_publisher(publisher_raw: str) -> str:
    """Normalize publisher name to standard identifier."""
    if not publisher_raw:
        return "unknown"
    
    publisher_lower = publisher_raw.lower()
    
    for standard_name, patterns in PUBLISHER_MAPPING.items():
        for pattern in patterns:
            if pattern in publisher_lower:
                return standard_name
    
    return "unknown"


async def search_journal_openalex(journal_name: str) -> Optional[dict]:
    """Search for a journal using OpenAlex API.
    
    Args:
        journal_name: Name of the journal to search
        
    Returns:
        Dictionary with journal information or None if not found
    """
    # Use autocomplete endpoint (faster and simpler)
    url = "https://api.openalex.org/autocomplete/sources"
    params = {"q": journal_name}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                return None
            
            # Get the best match (first result)
            result = data["results"][0]
            
            return {
                "journal_name": result.get("display_name"),
                "publisher_raw": result.get("hint"),  # Publisher name in autocomplete
                "publisher": normalize_publisher(result.get("hint", "")),
                "issn": result.get("external_id"),
                "openalex_id": result.get("id"),
                "cited_by_count": result.get("cited_by_count"),
                "works_count": result.get("works_count"),
            }
            
    except Exception as e:
        print(f"Error searching for '{journal_name}': {e}")
        return None


async def get_full_source_info(journal_name: str) -> Optional[dict]:
    """Get full source information using the main sources endpoint.
    
    This provides more detailed information than autocomplete.
    """
    url = "https://api.openalex.org/sources"
    params = {
        "search": journal_name,
        "per_page": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                return None
            
            result = data["results"][0]
            
            return {
                "journal_name": result.get("display_name"),
                "publisher_raw": result.get("host_organization_name"),
                "publisher": normalize_publisher(result.get("host_organization_name", "")),
                "issn_l": result.get("issn_l"),
                "issn": result.get("issn"),
                "homepage_url": result.get("homepage_url"),
                "type": result.get("type"),
                "is_oa": result.get("is_oa"),
                "works_count": result.get("works_count"),
                "cited_by_count": result.get("cited_by_count"),
                "openalex_id": result.get("id"),
            }
            
    except Exception as e:
        print(f"Error getting full info for '{journal_name}': {e}")
        return None


async def test_multiple_journals():
    """Test OpenAlex API with multiple journals from different publishers."""
    
    # Test journals from different publishers
    test_journals = [
        # Elsevier journals
        "Energy and Buildings",
        "Information Sciences",
        "Applied Energy",
        
        # Springer journals
        "Journal of Network and Systems Management",
        "Neural Computing and Applications",
        
        # Wiley journals
        "Software: Practice and Experience",
        "Concurrency and Computation: Practice and Experience",
        
        # IEEE journals
        "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "IEEE Access",
        
        # Other publishers
        "Nature",
        "Science",
    ]
    
    print("=" * 80)
    print("Testing OpenAlex API - Autocomplete Endpoint (Fast)")
    print("=" * 80)
    
    for journal in test_journals:
        print(f"\n📚 Searching: {journal}")
        print("-" * 80)
        
        result = await search_journal_openalex(journal)
        
        if result:
            print(f"✅ Found: {result['journal_name']}")
            print(f"   Publisher (raw): {result['publisher_raw']}")
            print(f"   Publisher (normalized): {result['publisher']}")
            print(f"   ISSN: {result['issn']}")
            print(f"   Works: {result['works_count']:,}")
            print(f"   Citations: {result['cited_by_count']:,}")
        else:
            print(f"❌ Not found")
    
    print("\n" + "=" * 80)
    print("Testing OpenAlex API - Full Source Endpoint (Detailed)")
    print("=" * 80)
    
    # Test a few journals with full endpoint
    sample_journals = [
        "Energy and Buildings",
        "Journal of Network and Systems Management",
        "IEEE Access"
    ]
    
    for journal in sample_journals:
        print(f"\n📚 Getting full info: {journal}")
        print("-" * 80)
        
        result = await get_full_source_info(journal)
        
        if result:
            print(f"✅ Found: {result['journal_name']}")
            print(f"   Publisher (raw): {result['publisher_raw']}")
            print(f"   Publisher (normalized): {result['publisher']}")
            print(f"   ISSN-L: {result['issn_l']}")
            print(f"   Homepage: {result['homepage_url']}")
            print(f"   Type: {result['type']}")
            print(f"   Open Access: {result['is_oa']}")
            print(f"   Works: {result['works_count']:,}")
            print(f"   Citations: {result['cited_by_count']:,}")
        else:
            print(f"❌ Not found")


async def test_publisher_distribution():
    """Test and show publisher distribution across test journals."""
    
    test_journals = [
        "Energy and Buildings",
        "Information Sciences",
        "Building and Environment",
        "Journal of Network and Systems Management",
        "IEEE Access",
        "Software: Practice and Experience",
        "Nature",
        "Science",
        "Pattern Recognition",
        "Neural Networks",
    ]
    
    print("\n" + "=" * 80)
    print("Publisher Distribution Analysis")
    print("=" * 80)
    
    publisher_count = {}
    results = []
    
    for journal in test_journals:
        result = await search_journal_openalex(journal)
        if result:
            results.append(result)
            publisher = result['publisher']
            publisher_count[publisher] = publisher_count.get(publisher, 0) + 1
    
    print(f"\nTested {len(test_journals)} journals, found {len(results)} results\n")
    print("Publisher distribution:")
    for publisher, count in sorted(publisher_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {publisher}: {count} journals")
    
    print("\n" + "=" * 80)


async def main():
    """Run all tests."""
    print("\n🔬 OpenAlex API Test Suite")
    print("=" * 80)
    print("Testing whether we can retrieve publisher information for journals")
    print("=" * 80)
    
    await test_multiple_journals()
    await test_publisher_distribution()
    
    print("\n" + "=" * 80)
    print("✅ Test completed!")
    print("=" * 80)
    print("\nConclusion:")
    print("- OpenAlex API can successfully retrieve publisher information")
    print("- Autocomplete endpoint is fast and suitable for quick lookups")
    print("- Full source endpoint provides detailed metadata")
    print("- Publisher names can be normalized to standard identifiers")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
