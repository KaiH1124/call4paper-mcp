"""Generic fallback CFP parser."""

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from .base import BaseParser
from ..models.cfp import CallForPaper, CFPList


class GenericParser(BaseParser):
    """Generic fallback parser for unsupported publishers.

    This parser attempts to extract CFP information using common patterns
    and returns partial results or just the URL if extraction fails.
    """

    publisher_name = "Unknown"
    supported_domains = []  # Accepts any domain

    def __init__(self, journal_name: str, url: str = ""):
        super().__init__(journal_name)
        # Try to identify publisher from URL
        if url:
            parsed = urlparse(url)
            self.publisher_name = parsed.netloc.replace("www.", "")

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Generic parser can handle any URL as fallback."""
        return True

    def parse_cfp_list(self, html: str, url: str) -> CFPList:
        """Attempt to parse CFP list using generic patterns."""
        soup = self._create_soup(html)
        cfp_items = []

        # Try various common patterns
        # Pattern 1: Links containing CFP-related keywords
        cfp_links = soup.find_all("a", href=re.compile(r"call|cfp|special.*issue", re.I))
        for link in cfp_links[:20]:  # Limit to 20 results
            title = self._clean_text(link.get_text())
            if title and len(title) > 5:
                cfp_url = urljoin(url, link["href"])
                cfp_items.append(
                    CallForPaper(
                        title=title,
                        journal_name=self.journal_name,
                        publisher=self.publisher_name,
                        url=cfp_url,
                        accessibility="unknown",
                    )
                )

        # Pattern 2: Headings with nearby content
        if not cfp_items:
            for heading in soup.find_all(["h2", "h3", "h4"])[:30]:
                title = self._clean_text(heading.get_text())
                if not title or len(title) < 5:
                    continue

                # Skip common navigation headings
                if title.lower() in ["menu", "navigation", "contact", "about", "home"]:
                    continue

                link = heading.find("a", href=True)
                cfp_url = urljoin(url, link["href"]) if link else url

                # Try to find deadline nearby
                deadline = None
                next_elem = heading.find_next_sibling()
                if next_elem:
                    deadline = self._extract_date(next_elem.get_text())

                cfp_items.append(
                    CallForPaper(
                        title=title,
                        journal_name=self.journal_name,
                        publisher=self.publisher_name,
                        deadline=deadline,
                        url=cfp_url,
                        accessibility="unknown",
                    )
                )

        # If still no results, return a single entry pointing to the URL
        if not cfp_items:
            cfp_items.append(
                CallForPaper(
                    title=f"Call for Papers - {self.journal_name}",
                    journal_name=self.journal_name,
                    publisher=self.publisher_name,
                    url=url,
                    description="Could not parse CFP details. Please visit the URL directly.",
                    accessibility="unknown",
                )
            )

        return CFPList(
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            cfp_page_url=url,
            items=cfp_items,
            total_count=len(cfp_items),
        )

    def parse_cfp_detail(self, html: str, url: str) -> Optional[CallForPaper]:
        """Attempt to parse CFP detail page using generic patterns."""
        soup = self._create_soup(html)

        # Get title
        title_elem = soup.find("h1")
        if not title_elem:
            title_elem = soup.find("title")
        title = self._clean_text(title_elem.get_text()) if title_elem else f"CFP - {self.journal_name}"

        # Get description from meta or first paragraph
        description = None
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc:
            description = meta_desc.get("content")
        if not description:
            first_p = soup.find("p")
            if first_p:
                description = self._clean_text(first_p.get_text())[:500]

        # Try to find deadline anywhere
        deadline = None
        page_text = soup.get_text()
        deadline = self._extract_date(page_text)

        # Try to find guest editors
        guest_editors = []
        editor_pattern = re.compile(r"guest.*editor|editor.*in.*chief", re.I)
        editor_section = soup.find(string=editor_pattern)
        if editor_section:
            parent = editor_section.find_parent()
            if parent:
                # Simple name extraction
                text = parent.get_text()
                names = re.findall(r"(?:Dr\.|Prof\.|Mr\.|Ms\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)", text)
                guest_editors = list(set(names))[:10]

        # Try to find topics
        topics = []
        topics_section = soup.find(string=re.compile(r"topics|scope|interest", re.I))
        if topics_section:
            parent = topics_section.find_parent()
            if parent:
                list_items = parent.find_all("li")
                topics = [self._clean_text(li.get_text()) for li in list_items][:20]

        return CallForPaper(
            title=title,
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            deadline=deadline,
            guest_editors=guest_editors,
            topics=topics,
            url=url,
            description=description,
            accessibility="unknown",
        )
