"""Base parser class for CFP extraction."""

from abc import ABC, abstractmethod
from typing import Optional
from bs4 import BeautifulSoup

from ..models.cfp import CallForPaper, CFPList


class BaseParser(ABC):
    """Abstract base class for publisher-specific parsers."""

    publisher_name: str = "unknown"
    supported_domains: list[str] = []

    def __init__(self, journal_name: str):
        self.journal_name = journal_name

    @abstractmethod
    def parse_cfp_list(self, html: str, url: str) -> CFPList:
        """Parse CFP listing page and extract all CFP entries.

        Args:
            html: Raw HTML content of the CFP listing page
            url: URL of the page

        Returns:
            CFPList containing all found CFP entries
        """
        pass

    @abstractmethod
    def parse_cfp_detail(self, html: str, url: str) -> Optional[CallForPaper]:
        """Parse a single CFP detail page.

        Args:
            html: Raw HTML content of the CFP detail page
            url: URL of the page

        Returns:
            CallForPaper object or None if parsing fails
        """
        pass

    def _create_soup(self, html: str) -> BeautifulSoup:
        """Create BeautifulSoup object from HTML."""
        return BeautifulSoup(html, "lxml")

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        return " ".join(text.split()).strip()

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text. Override in subclasses for custom patterns."""
        import re

        # Common date patterns
        patterns = [
            r"\d{4}-\d{2}-\d{2}",  # 2024-12-31
            r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            r"\d{1,2}/\d{1,2}/\d{4}",  # 12/31/2024
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this parser can handle the given URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        return any(d in domain for d in cls.supported_domains)
