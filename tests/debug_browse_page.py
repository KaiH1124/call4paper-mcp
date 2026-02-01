"""Debug script to examine browse page structure."""

import asyncio
import httpx
from bs4 import BeautifulSoup


async def debug_browse_page():
    """Fetch and examine the browse page structure."""
    
    url = "https://www.sciencedirect.com/browse/calls-for-papers"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    
    print(f"Fetching: {url}\n")
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        response = await client.get(url)
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)} bytes\n")
    
    # Save full HTML for inspection
    with open("browse_page.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("✓ Saved full HTML to browse_page.html\n")
    
    # Look for special issue/CFP containers
    print("=" * 80)
    print("Looking for CFP containers...")
    print("=" * 80)
    
    # Try different selectors
    selectors = [
        ("a[href*='special-issue']", "Links with 'special-issue' in href"),
        ("a[href*='call-for-paper']", "Links with 'call-for-paper' in href"),
        ("article", "Article elements"),
        ("div.result-item", "Divs with class 'result-item'"),
        ("div.search-result", "Divs with class 'search-result'"),
        ("li.result", "List items with class 'result'"),
    ]
    
    for selector, description in selectors:
        elements = soup.select(selector)
        print(f"\n{description}: Found {len(elements)} elements")
        
        if elements and len(elements) <= 5:
            for i, elem in enumerate(elements[:3], 1):
                print(f"  [{i}] {elem.name}: {elem.get_text()[:100]}")
    
    # Look for all links
    print("\n" + "=" * 80)
    print("All links containing 'special-issue':")
    print("=" * 80)
    
    special_links = soup.find_all("a", href=lambda x: x and "special-issue" in x)
    print(f"Found {len(special_links)} links")
    
    for i, link in enumerate(special_links[:10], 1):
        text = link.get_text().strip()[:80]
        href = link['href'][:80]
        print(f"{i}. {text}")
        print(f"   -> {href}\n")
    
    # Look for journal names
    print("=" * 80)
    print("Elements that might contain journal names:")
    print("=" * 80)
    
    journal_indicators = soup.find_all(class_=lambda x: x and ('journal' in x.lower() or 'publication' in x.lower()))
    print(f"Found {len(journal_indicators)} elements with journal/publication in class")
    for elem in journal_indicators[:5]:
        print(f"  - {elem.name}.{elem.get('class')}: {elem.get_text()[:100]}")


if __name__ == "__main__":
    asyncio.run(debug_browse_page())
