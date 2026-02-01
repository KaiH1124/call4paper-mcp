"""Test filtering logic."""

import asyncio
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from call4paper.tools.search import search_journal_cfp


async def test_filter():
    """Test the filtering."""
    
    # Test with Energy and Buildings
    result = await search_journal_cfp("Energy and Buildings", count=10, use_cache=False)
    
    print(f"期刊: {result.journal_name}")
    print(f"总数: {result.total_count}")
    print(f"返回数量: {len(result.items)}\n")
    
    print("前10个结果的期刊名:")
    for i, item in enumerate(result.items, 1):
        print(f"{i}. [{item.journal_name}] {item.title[:60]}")


if __name__ == "__main__":
    asyncio.run(test_filter())
