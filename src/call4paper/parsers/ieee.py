"""IEEE CFP parser."""

import re
from typing import Optional
from urllib.parse import urljoin

from .base import BaseParser
from ..models.cfp import CallForPaper, CFPList


class IEEEParser(BaseParser):
    """Parser for IEEE CFP pages."""

    publisher_name = "IEEE"
    supported_domains = ["ieee.org", "ieeexplore.ieee.org"]

    def parse_cfp_list(self, html: str, url: str) -> CFPList:
        """Parse IEEE CFP listing page.

        Note: IEEE pages are often dynamic and may require Playwright.
        """
        soup = self._create_soup(html)
        cfp_items = []

        # IEEE uses various structures
        containers = soup.find_all("div", class_=re.compile(r"special-issue|cfp|call", re.I))
        if not containers:
            containers = soup.find_all("tr")  # Table format
        if not containers:
            containers = soup.find_all("article")

        for container in containers:
            cfp = self._parse_entry(container, url)
            if cfp:
                cfp_items.append(cfp)

        return CFPList(
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            cfp_page_url=url,
            items=cfp_items,
            total_count=len(cfp_items),
        )

    def _parse_entry(self, container, base_url: str) -> Optional[CallForPaper]:
        """Parse IEEE CFP entry."""
        title_elem = (
            container.find("h2")
            or container.find("h3")
            or container.find("td")
            or container.find("a")
        )

        if not title_elem:
            return None

        title = self._clean_text(title_elem.get_text())
        if not title or len(title) < 5:
            return None

        # Get link
        link = container.find("a", href=True)
        cfp_url = urljoin(base_url, link["href"]) if link else base_url

        # Deadline
        deadline = self._extract_date(container.get_text())

        # Description
        desc_elem = container.find("p")
        description = self._clean_text(desc_elem.get_text())[:500] if desc_elem else None

        return CallForPaper(
            title=title,
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            deadline=deadline,
            url=cfp_url,
            description=description,
            accessibility="unknown",
        )

    def parse_cfp_detail(self, html: str, url: str) -> Optional[CallForPaper]:
        """Parse IEEE CFP detail page."""
        soup = self._create_soup(html)

        title_elem = soup.find("h1") or soup.find("title")
        title = self._clean_text(title_elem.get_text()) if title_elem else "Unknown"

        deadline = None
        for elem in soup.find_all(string=re.compile(r"deadline|due", re.I)):
            parent = elem.find_parent()
            if parent:
                deadline = self._extract_date(parent.get_text())
                if deadline:
                    break

        description = None
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc:
            description = meta_desc.get("content")

        return CallForPaper(
            title=title,
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            deadline=deadline,
            url=url,
            description=description,
            accessibility="unknown",
        )
