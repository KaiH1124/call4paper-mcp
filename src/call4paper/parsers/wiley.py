"""Wiley CFP parser."""

import re
from typing import Optional
from urllib.parse import urljoin

from .base import BaseParser
from ..models.cfp import CallForPaper, CFPList


class WileyParser(BaseParser):
    """Parser for Wiley Online Library CFP pages."""

    publisher_name = "Wiley"
    supported_domains = ["wiley.com", "onlinelibrary.wiley.com"]

    def parse_cfp_list(self, html: str, url: str) -> CFPList:
        """Parse Wiley CFP listing page."""
        soup = self._create_soup(html)
        cfp_items = []

        # Wiley uses various containers
        containers = soup.find_all("div", class_=re.compile(r"special|issue|cfp", re.I))
        if not containers:
            containers = soup.find_all("article")
        if not containers:
            containers = soup.find_all("li", class_=re.compile(r"item", re.I))

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
        """Parse Wiley CFP entry."""
        title_elem = (
            container.find("h2")
            or container.find("h3")
            or container.find(class_=re.compile(r"title", re.I))
        )

        if not title_elem:
            return None

        title = self._clean_text(title_elem.get_text())
        if not title or len(title) < 5:
            return None

        link = container.find("a", href=True)
        cfp_url = urljoin(base_url, link["href"]) if link else base_url

        deadline = self._extract_date(container.get_text())

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
        """Parse Wiley CFP detail page."""
        soup = self._create_soup(html)

        title_elem = soup.find("h1") or soup.find("title")
        title = self._clean_text(title_elem.get_text()) if title_elem else "Unknown"

        deadline = None
        for elem in soup.find_all(string=re.compile(r"deadline|submission", re.I)):
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
