"""Springer Nature CFP parser."""

import re
from typing import Optional
from urllib.parse import urljoin

from .base import BaseParser
from ..models.cfp import CallForPaper, CFPList


class SpringerParser(BaseParser):
    """Parser for Springer Nature CFP pages.

    Supports URLs like:
    - https://link.springer.com/journal/{id}/collections?filter=Open
    - https://link.springer.com/collections/{collection_id}
    """

    publisher_name = "Springer"
    supported_domains = ["springer.com", "springerlink.com", "link.springer.com", "nature.com"]

    def parse_cfp_list(self, html: str, url: str) -> CFPList:
        """Parse Springer journal collections/CFP listing page."""
        soup = self._create_soup(html)
        cfp_items = []

        # Find article elements - these contain CFP entries
        articles = soup.find_all("article")

        for article in articles:
            cfp = self._parse_article_entry(article, url)
            if cfp:
                cfp_items.append(cfp)

        # If no articles found, try alternative selectors
        if not cfp_items:
            # Try finding by heading structure
            for h2 in soup.find_all("h2"):
                link = h2.find("a", href=re.compile(r"/collections/", re.I))
                if link:
                    cfp = self._parse_heading_entry(h2, link, url)
                    if cfp:
                        cfp_items.append(cfp)

        return CFPList(
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            cfp_page_url=url,
            items=cfp_items,
            total_count=len(cfp_items),
        )

    def _parse_article_entry(self, article, base_url: str) -> Optional[CallForPaper]:
        """Parse a single article element containing CFP info."""
        # Get title from h2
        h2 = article.find("h2")
        if not h2:
            return None

        title = self._clean_text(h2.get_text())
        if not title or len(title) < 5:
            return None

        # Get URL from link in h2
        link = h2.find("a", href=True)
        cfp_url = urljoin(base_url, link["href"]) if link else base_url

        # Get full article text for extraction
        article_text = article.get_text()

        # Extract deadline - look for date patterns
        deadline = None
        # Pattern: "Submission deadline" followed by date
        deadline_match = re.search(
            r"(?:submission\s+)?deadline[:\s]*(\d{1,2}\s+\w+\s+\d{4})",
            article_text,
            re.I
        )
        if deadline_match:
            deadline = deadline_match.group(1)
        else:
            # Try to find any date
            date_match = re.search(
                r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
                article_text,
                re.I
            )
            if date_match:
                deadline = date_match.group(1)

        # Get description from first paragraph
        description = None
        p = article.find("p")
        if p:
            description = self._clean_text(p.get_text())
            if description:
                description = description[:500]

        # Determine accessibility
        accessibility = "unknown"
        text_lower = article_text.lower()
        if "open" in text_lower or "accepting" in text_lower:
            accessibility = "open"
        elif "closed" in text_lower:
            accessibility = "closed"

        return CallForPaper(
            title=title,
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            deadline=deadline,
            url=cfp_url,
            description=description,
            accessibility=accessibility,
        )

    def _parse_heading_entry(self, h2, link, base_url: str) -> Optional[CallForPaper]:
        """Parse CFP from heading and link when no article container."""
        title = self._clean_text(link.get_text())
        if not title or len(title) < 5:
            return None

        cfp_url = urljoin(base_url, link["href"])

        # Try to find nearby text for deadline
        deadline = None
        next_elem = h2.find_next_sibling()
        if next_elem:
            text = next_elem.get_text()
            deadline = self._extract_date(text)

        return CallForPaper(
            title=title,
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            deadline=deadline,
            url=cfp_url,
            accessibility="unknown",
        )

    def parse_cfp_detail(self, html: str, url: str) -> Optional[CallForPaper]:
        """Parse Springer collection/CFP detail page."""
        soup = self._create_soup(html)

        # Get title
        title_elem = soup.find("h1") or soup.find("title")
        title = self._clean_text(title_elem.get_text()) if title_elem else "Unknown"

        # Clean up title (remove site name suffix)
        if "|" in title:
            title = title.split("|")[0].strip()

        # Find deadline
        deadline = None
        page_text = soup.get_text()

        # Look for deadline patterns
        deadline_patterns = [
            r"(?:submission\s+)?deadline[:\s]*(\d{1,2}\s+\w+\s+\d{4})",
            r"submit\s+by[:\s]*(\d{1,2}\s+\w+\s+\d{4})",
            r"closes?[:\s]*(\d{1,2}\s+\w+\s+\d{4})",
        ]

        for pattern in deadline_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                deadline = match.group(1)
                break

        if not deadline:
            deadline = self._extract_date(page_text)

        # Find guest editors
        guest_editors = []
        editor_section = soup.find(string=re.compile(r"guest\s+editor|editor", re.I))
        if editor_section:
            parent = editor_section.find_parent()
            if parent:
                # Look for names in list items or text
                items = parent.find_all("li")
                if items:
                    guest_editors = [self._clean_text(li.get_text()) for li in items[:10]]
                else:
                    # Try to extract from text
                    text = parent.get_text()
                    names = re.findall(r"(?:Dr\.|Prof\.|Mr\.|Ms\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)", text)
                    guest_editors = list(set(names))[:10]

        # Find topics
        topics = []
        topics_section = soup.find(string=re.compile(r"topics?|scope|areas?\s+of\s+interest", re.I))
        if topics_section:
            parent = topics_section.find_parent()
            if parent:
                items = parent.find_all("li")
                topics = [self._clean_text(li.get_text()) for li in items[:20]]

        # Get description
        description = None
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc:
            description = meta_desc.get("content")
        if not description:
            # Try first paragraph after h1
            h1 = soup.find("h1")
            if h1:
                p = h1.find_next("p")
                if p:
                    description = self._clean_text(p.get_text())[:500]

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
