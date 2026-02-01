"""Debug filtering process."""

import asyncio
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from call4paper.tools.search import search_journal_cfp
from call4paper.tools.scraper import fetch_page
from call4paper.parsers.elsevier import ElsevierParser


async def debug_filter():
    """Debug the filtering."""
    
    url = "https://www.sciencedirect.com/browse/calls-for-papers"
    
    # Fetch page
    html, error = await fetch_page(url)
    
    # Parse
    parser = ElsevierParser("Test")
    cfp_list = parser.parse_cfp_list(html, url)
    
    print(f"Total CFPs found: {len(cfp_list.items)}\n")
    
    # Show first 20 CFPs with their journal names
    print("First 20 CFPs and their journal names:")
    print("=" * 80)
    for i, item in enumerate(cfp_list.items[:20], 1):
        print(f"{i}. Journal: [{item.journal_name}]")
        print(f"   Title: {item.title[:70]}")
        print()
    
    # Search for Energy and Buildings
    print("\n" + "=" * 80)
    print("Searching for 'Energy and Buildings':")
    print("=" * 80)
    matches = []
    for item in cfp_list.items:
        if "energy" in item.journal_name.lower() and "building" in item.journal_name.lower():
            matches.append(item)
    
    print(f"Found {len(matches)} matches")
    for i, item in enumerate(matches[:5], 1):
        print(f"\n{i}. Journal: [{item.journal_name}]")
        print(f"   Title: {item.title}")


if __name__ == "__main__":
    asyncio.run(debug_filter())
