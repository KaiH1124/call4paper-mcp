"""Test if HKU proxy URL bypasses Elsevier anti-scraping."""

import asyncio
import httpx
from bs4 import BeautifulSoup


async def test_proxy_access():
    """Test accessing Elsevier through HKU proxy."""
    
    # Original URL and proxy URL
    original_url = "https://www.sciencedirect.com/browse/calls-for-papers"
    proxy_url = "https://www-sciencedirect-com.eproxy.lib.hku.hk/browse/calls-for-papers"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    print("=" * 80)
    print("测试1: 直接访问原始URL")
    print(f"URL: {original_url}")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers=headers,
        ) as client:
            response = await client.get(original_url)
            print(f"状态码: {response.status_code}")
            print(f"响应长度: {len(response.text)} 字符")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                print(f"页面标题: {soup.title.string if soup.title else 'N/A'}")
                
                # Check for anti-bot indicators
                if "captcha" in response.text.lower():
                    print("⚠️  检测到 CAPTCHA")
                elif "access denied" in response.text.lower():
                    print("⚠️  检测到访问被拒绝")
                else:
                    print("✓ 似乎没有明显的反爬虫阻拦")
                    
                # Try to find CFP content
                cfp_links = soup.find_all('a', href=lambda x: x and 'call-for-papers' in x.lower())
                print(f"找到的CFP相关链接数量: {len(cfp_links)}")
                
            print()
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP错误: {e.response.status_code}")
        if e.response.status_code == 403:
            print("   这是典型的反爬虫阻拦响应")
    except Exception as e:
        print(f"❌ 请求失败: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 80)
    print("测试2: 通过HKU代理访问")
    print(f"URL: {proxy_url}")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers=headers,
        ) as client:
            response = await client.get(proxy_url)
            print(f"状态码: {response.status_code}")
            print(f"响应长度: {len(response.text)} 字符")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                print(f"页面标题: {soup.title.string if soup.title else 'N/A'}")
                
                # Check for authentication requirements
                if "login" in response.text.lower() and "authentication" in response.text.lower():
                    print("⚠️  代理需要身份验证/登录")
                elif "captcha" in response.text.lower():
                    print("⚠️  检测到 CAPTCHA")
                elif "access denied" in response.text.lower():
                    print("⚠️  检测到访问被拒绝")
                else:
                    print("✓ 似乎没有明显的反爬虫阻拦")
                
                # Try to find CFP content
                cfp_links = soup.find_all('a', href=lambda x: x and 'call-for-papers' in x.lower())
                print(f"找到的CFP相关链接数量: {len(cfp_links)}")
                
                # Check for special issues
                special_issue_content = soup.find_all(string=lambda x: x and 'special issue' in x.lower())
                print(f"找到的'special issue'文本数量: {len(special_issue_content)}")
                
            print()
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP错误: {e.response.status_code}")
        if e.response.status_code == 403:
            print("   这是典型的反爬虫阻拦响应")
        elif e.response.status_code == 401 or e.response.status_code == 407:
            print("   代理需要身份验证")
    except Exception as e:
        print(f"❌ 请求失败: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 80)
    print("结论:")
    print("=" * 80)
    print("如果代理URL返回200且没有CAPTCHA/登录要求，说明可以绕过反爬虫机制")
    print("如果需要登录，则需要配置代理认证凭据")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_proxy_access())
