"""Local test script for CFP search functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from call4paper.tools.search import search_journal_cfp, list_supported_publishers
from call4paper.utils.config import Config


async def test_search_by_journal_name(journal_name: str):
    """Test searching for CFP by journal name."""
    print("=" * 80)
    print(f"测试搜索期刊: {journal_name}")
    print("=" * 80)
    
    # Check if journal is in registry
    journal_info = Config.get_cfp_url_for_journal(journal_name)
    if journal_info:
        print(f"✓ 期刊在注册表中找到")
        print(f"  发布商: {journal_info.get('publisher')}")
        print(f"  CFP URL: {journal_info.get('cfp_url')}")
        print(f"  别名: {journal_info.get('aliases', [])}")
    else:
        print(f"⚠️  期刊不在注册表中，将尝试构造URL")
    
    print("\n搜索中...")
    
    try:
        result = await search_journal_cfp(journal_name, count=3, use_cache=False)
        
        print(f"\n搜索结果:")
        print(f"  期刊名: {result.journal_name}")
        print(f"  发布商: {result.publisher}")
        print(f"  CFP页面: {result.cfp_page_url}")
        print(f"  找到的CFP数量: {result.total_count}")
        
        if result.items:
            print(f"\n前 {len(result.items)} 个CFP:")
            for i, cfp in enumerate(result.items, 1):
                print(f"\n  [{i}] {cfp.title}")
                print(f"      截止日期: {cfp.deadline or '未知'}")
                print(f"      URL: {cfp.url}")
                print(f"      开放状态: {cfp.accessibility}")
                if cfp.description:
                    desc = cfp.description[:100] + "..." if len(cfp.description) > 100 else cfp.description
                    print(f"      描述: {desc}")
        else:
            print("\n⚠️  未找到CFP信息")
            
    except Exception as e:
        print(f"\n❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()


async def test_list_publishers():
    """Test listing supported publishers."""
    print("=" * 80)
    print("支持的出版商列表")
    print("=" * 80)
    
    publishers = list_supported_publishers()
    
    for i, pub in enumerate(publishers, 1):
        print(f"\n{i}. {pub['name']}")
        print(f"   支持的域名: {', '.join(pub['domains'])}")


async def test_registry_info():
    """Test reading journal registry."""
    print("=" * 80)
    print("期刊注册表信息")
    print("=" * 80)
    
    registry = Config.load_journal_registry()
    journals = registry.get("journals", [])
    
    print(f"注册表版本: {registry.get('version', 'N/A')}")
    print(f"更新日期: {registry.get('updated_at', 'N/A')}")
    print(f"注册的期刊数量: {len(journals)}")
    
    # Show first 10 journals
    print(f"\n前10个注册的期刊:")
    for i, journal in enumerate(journals[:10], 1):
        print(f"  {i}. {journal.get('name')} [{journal.get('publisher')}]")
        if journal.get('aliases'):
            print(f"     别名: {', '.join(journal.get('aliases', []))}")


async def main():
    """Main test function."""
    print("\n🔍 Call4Paper 本地测试工具\n")
    
    # Test 1: Show registry info
    await test_registry_info()
    print("\n")
    
    # Test 2: List supported publishers
    await test_list_publishers()
    print("\n")
    
    # Test 3: Test search with different journal names
    test_cases = [
        "Energy and Buildings",  # Should be in registry (Elsevier)
        "Information Sciences",   # Should be in registry (Elsevier)
        "Applied Energy",         # Should be in registry (Elsevier)
    ]
    
    for journal_name in test_cases:
        await test_search_by_journal_name(journal_name)
        print("\n")
    
    # Test 4: Interactive search
    print("=" * 80)
    print("交互式搜索测试")
    print("=" * 80)
    print("输入期刊名称进行搜索（输入 'quit' 退出）:")
    print("示例期刊名: Energy and Buildings, Information Sciences")
    print()
    
    while True:
        try:
            journal_name = input("期刊名称> ").strip()
            if not journal_name:
                continue
            if journal_name.lower() in ['quit', 'exit', 'q']:
                break
            
            await test_search_by_journal_name(journal_name)
            print()
            
        except KeyboardInterrupt:
            print("\n\n退出...")
            break
        except EOFError:
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已终止")
