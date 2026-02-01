#!/usr/bin/env python3
"""调试：检查解析器实际提取了什么期刊名"""

import asyncio
from pathlib import Path

# 添加src目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from call4paper.parsers.elsevier import ElsevierParser

async def main():
    # 读取保存的HTML
    with open("browse_page.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # 创建解析器
    parser = ElsevierParser("Test")
    
    # 解析
    url = "https://www.sciencedirect.com/browse/calls-for-papers"
    cfp_list = parser.parse_cfp_list(html, url)
    
    print(f"总共解析到 {len(cfp_list.items)} 个CFP")
    
    # 统计期刊名分布
    journal_counts = {}
    for cfp in cfp_list.items:
        journal_counts[cfp.journal_name] = journal_counts.get(cfp.journal_name, 0) + 1
    
    print("\n期刊名分布（前30个）：")
    for journal, count in sorted(journal_counts.items(), key=lambda x: -x[1])[:30]:
        print(f"  {count:4d} - {journal}")
    
    # 查找包含 "energy" 和 "building" 的期刊
    print("\n包含 'energy' 或 'building' 的期刊：")
    for journal in sorted(journal_counts.keys()):
        if 'energy' in journal.lower() or 'building' in journal.lower():
            print(f"  [{journal}] ({journal_counts[journal]} CFPs)")

if __name__ == "__main__":
    asyncio.run(main())
