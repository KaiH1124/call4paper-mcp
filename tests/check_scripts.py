#!/usr/bin/env python3
"""检查HTML中的script标签和JSON数据"""

import re
from bs4 import BeautifulSoup

with open("browse_page.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("所有script标签：")
print("="*80)

for i, script in enumerate(soup.find_all('script')):
    script_text = script.string or ''
    print(f"\nScript #{i+1}:")
    print(f"  Type: {script.get('type', 'N/A')}")
    print(f"  Src: {script.get('src', 'N/A')}")
    print(f"  Content length: {len(script_text)} chars")
    
    # Check for JSON patterns
    has_json = False
    if '"displayName"' in script_text:
        print("  ✓ Contains 'displayName'")
        has_json = True
    if '"journal"' in script_text:
        print("  ✓ Contains 'journal'")
        has_json = True
    if 'callForPapers' in script_text:
        print("  ✓ Contains 'callForPapers'")
        has_json = True
    
    if has_json:
        print(f"  First 500 chars:")
        print(f"  {script_text[:500]}")

print(f"\n总共 {len(soup.find_all('script'))} 个script标签")
