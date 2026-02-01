#!/usr/bin/env python3
"""提取window.INITIAL_STATE中的CFP数据"""

from bs4 import BeautifulSoup
import json
import re

with open('browse_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
scripts = soup.find_all('script')

# Find the large script
for script in scripts:
    text = script.string or ''
    if 'window.INITIAL_STATE' in text and len(text) > 1000000:
        print(f"Found INITIAL_STATE script, length: {len(text)} chars")
        # Extract JSON - match everything after the = until the end
        match = re.search(r'window\.INITIAL_STATE\s*=\s*(\{.*)', text, re.DOTALL)
        if match:
            json_str = match.group(1)
            # Remove trailing semicolon and whitespace
            json_str = json_str.rstrip().rstrip(';')
            
            try:
                data = json.loads(json_str)
                print(f"Successfully parsed JSON")
                print(f"Top level keys: {list(data.keys())}")
                
                # Navigate to CFPs - try multiple possible locations
                cfps = None
                if 'callsForPapers' in data:
                    cfps = data['callsForPapers']
                elif 'browsePageData' in data:
                    browse = data['browsePageData']
                    cfps = browse.get('callForPapers')
                
                if cfps:
                    print(f'Found {len(cfps)} CFPs')
                    
                    if cfps:
                        print('\nFirst 3 CFPs:')
                        for i, cfp in enumerate(cfps[:3]):
                            journal = cfp.get('journal', {})
                            print(f"\n{i+1}. {cfp.get('title', 'No title')}")
                            print(f"   Journal: {journal.get('displayName', 'Unknown')}")
                            print(f"   URL: {cfp.get('url', '')}")
                        
                        # Find Energy and Buildings CFPs
                        energy_building = [c for c in cfps if 'energy' in c.get('journal', {}).get('displayName', '').lower() and 'building' in c.get('journal', {}).get('displayName', '').lower()]
                        print(f"\n\nFound {len(energy_building)} Energy and Buildings CFPs")
                        for cfp in energy_building[:5]:
                            print(f"  - {cfp.get('title')}")
                else:
                    print("No CFPs found in data structure")
                    
                break
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"First 500 chars: {json_str[:500]}")
                print(f"Last 200 chars: {json_str[-200:]}")
