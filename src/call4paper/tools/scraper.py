"""Web scraping utilities for CFP pages."""

import asyncio
import shutil
from typing import Optional, Tuple

import httpx

from ..utils.config import Config

# Check if Playwright is available
PLAYWRIGHT_AVAILABLE = False
try:
    import playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

# Check if curl is available
CURL_AVAILABLE = shutil.which("curl") is not None


async def fetch_page_with_curl(url: str, timeout: int = 30) -> Tuple[Optional[str], Optional[str]]:
    """Fetch a web page using curl command.

    curl has a different TLS fingerprint than httpx, which can help
    bypass some anti-bot protections that block Python HTTP libraries.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Tuple of (HTML content, error message). One will be None.
    """
    if not CURL_AVAILABLE:
        return None, "curl_not_available"

    try:
        proc = await asyncio.create_subprocess_exec(
            "curl", "-s", "-L",  # silent, follow redirects
            "--max-time", str(timeout),
            "-A", Config.USER_AGENT,
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.5",
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            return None, f"curl_error: {error_msg or 'exit code ' + str(proc.returncode)}"

        html = stdout.decode("utf-8", errors="replace")

        # Check if we got a valid response
        if len(html) < 1000:
            return None, "curl_empty_response"

        return html, None

    except Exception as e:
        return None, f"curl_exception: {str(e)}"


async def fetch_page(url: str, timeout: int = Config.HTTP_TIMEOUT) -> Tuple[Optional[str], Optional[str]]:
    """Fetch a static web page using httpx.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Tuple of (HTML content, error message). One will be None.
    """
    headers = {
        "User-Agent": Config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text, None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return None, "blocked"  # Likely anti-bot protection
        return None, f"HTTP {e.response.status_code}"
    except httpx.HTTPError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


async def fetch_page_dynamic(url: str, timeout: int = 60000) -> Tuple[Optional[str], Optional[str]]:
    """Fetch a dynamic web page using Playwright.

    Use this for pages that require JavaScript rendering.

    Args:
        url: URL to fetch
        timeout: Page load timeout in milliseconds

    Returns:
        Tuple of (HTML content, error message). One will be None.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None, "playwright_not_installed"

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )

            page = await context.new_page()

            try:
                # Navigate and wait for load
                await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

                # Wait for network to be idle
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass

                # Wait for content to render
                await asyncio.sleep(3)

                # Check for bot protection pages
                title = await page.title()
                content = await page.content()

                # Detect common bot protection patterns
                bot_protection_indicators = [
                    "just a moment",
                    "are you a robot",
                    "captcha",
                    "access denied",
                    "please verify",
                    "checking your browser",
                    "problem providing the content",
                    "cloudflare",
                    "blocked",
                    "security check",
                    "verify you are human",
                ]

                title_lower = title.lower() if title else ""
                # Check both beginning and end of content for bot protection indicators
                # Error messages often appear at the end (after fonts/styles in head)
                content_lower = content.lower()
                content_to_check = content_lower[:5000] + content_lower[-10000:]

                for indicator in bot_protection_indicators:
                    if indicator in title_lower or indicator in content_lower:
                        return None, "bot_protection"

                return content, None
            except Exception as e:
                return None, f"Page load error: {e}"
            finally:
                await browser.close()

    except Exception as e:
        if "Executable doesn't exist" in str(e):
            return None, "playwright_browser_not_installed"
        return None, str(e)


def is_playwright_available() -> bool:
    """Check if Playwright is installed and ready."""
    return PLAYWRIGHT_AVAILABLE


def get_playwright_install_hint() -> str:
    """Get installation hint for Playwright."""
    return (
        "To access sites with anti-bot protection, install Playwright:\n"
        "  pip install playwright\n"
        "  playwright install chromium"
    )
