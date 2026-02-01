#!/usr/bin/env python3
"""测试从browse页面的JSON数据中提取期刊信息"""

import json
import re

# 读取HTML文件
with open("browse_page.html", "r", encoding="utf-8") as f:
    html_content = f.read()

# 从页面中提取JSON数据
# 查找 __NEXT_DATA__ script标签
pattern = r'<script[^>]*>window\.__NEXT_DATA__\s*=\s*({.*?});</script>'
match = re.search(pattern, html_content, re.DOTALL)

if match:
    json_str = match.group(1)
    data = json.loads(json_str)
    
    # 导航到CFP数据
    cfps = data['props']['pageProps']['browsePageData']['callForPapers']
    
    print(f"找到 {len(cfps)} 个CFP")
    print("\n前20个CFP的期刊信息：")
    print("="*80)
    
    for i, cfp in enumerate(cfps[:20]):
        journal = cfp.get('journal', {})
        journal_name = journal.get('displayName', 'Unknown')
        title = cfp.get('title', 'No title')
        url = cfp.get('url', '')
        
        print(f"{i+1}. [{journal_name}]")
        print(f"   标题: {title}")
        print(f"   URL: {url}")
        print()
    
    # 统计Energy and Buildings的CFP
    energy_building_cfps = []
    for cfp in cfps:
        journal = cfp.get('journal', {})
        journal_name = journal.get('displayName', '').lower()
        if 'energy' in journal_name and 'building' in journal_name:
            energy_building_cfps.append(cfp)
    
    print("="*80)
    print(f"\n找到 {len(energy_building_cfps)} 个 Energy and Buildings 的CFP：")
    for cfp in energy_building_cfps:
        journal = cfp.get('journal', {})
        print(f"  - {cfp.get('title')}")
        print(f"    期刊: {journal.get('displayName')}")
        print(f"    Impact Factor: {journal.get('impactFactor', 'N/A')}")
        print()
else:
    print("未找到JSON数据")
