"""Check proxy response details."""

import asyncio
import httpx


async def check_proxy_response():
    """Check what the proxy returns."""
    
    proxy_url = "https://www-sciencedirect-com.eproxy.lib.hku.hk/browse/calls-for-papers"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers=headers,
        ) as client:
            response = await client.get(proxy_url)
            
            print("HTTP Headers:")
            print("=" * 80)
            for key, value in response.headers.items():
                print(f"{key}: {value}")
            
            print("\n\nResponse Content (前1000字符):")
            print("=" * 80)
            print(response.text[:1000])
            
            print("\n\n关键词检查:")
            print("=" * 80)
            content_lower = response.text.lower()
            keywords = [
                "shibboleth",
                "authentication",
                "login",
                "sign in",
                "credentials",
                "username",
                "password",
                "institution",
            ]
            
            for keyword in keywords:
                if keyword in content_lower:
                    print(f"✓ 找到关键词: '{keyword}'")
                    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_proxy_response())
