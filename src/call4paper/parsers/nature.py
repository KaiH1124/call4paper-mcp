"""Nature CFP parser."""

import re
from typing import Optional
from urllib.parse import urljoin

from .base import BaseParser
from ..models.cfp import CallForPaper, CFPList


class NatureParser(BaseParser):
    """Parser for Nature journal collection pages.

    Listing page format:
    - https://www.nature.com/{short}/collections

    Detail page format:
    - https://www.nature.com/collections/{collection_id}
    """

    publisher_name = "Nature"
    supported_domains = ["nature.com"]

    def parse_cfp_list(self, html: str, url: str) -> CFPList:
        """Parse Nature collections listing page."""
        soup = self._create_soup(html)
        cfp_items: list[CallForPaper] = []

        links = soup.find_all("a", href=re.compile(r"^/collections/"))
        seen_urls: set[str] = set()

        for link in links:
            cfp_url = urljoin(url, link.get("href", ""))
            if not cfp_url or cfp_url in seen_urls:
                continue

            title = self._extract_link_title(link)
            if not title or len(title) < 4:
                continue

            container = link.find_parent(["article", "section", "div"])
            description = None
            deadline = None
            accessibility = "unknown"
            if container:
                description = self._extract_description(container)
                deadline = self._extract_deadline(container.get_text(" ", strip=True))
                accessibility = self._infer_accessibility(container.get_text(" ", strip=True))

            cfp_items.append(
                CallForPaper(
                    title=title,
                    journal_name=self.journal_name,
                    publisher=self.publisher_name,
                    deadline=deadline,
                    url=cfp_url,
                    description=description,
                    accessibility=accessibility,
                )
            )
            seen_urls.add(cfp_url)

        return CFPList(
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            cfp_page_url=url,
            items=cfp_items,
            total_count=len(cfp_items),
        )

    def parse_cfp_detail(self, html: str, url: str) -> Optional[CallForPaper]:
        """Parse Nature collection detail page."""
        soup = self._create_soup(html)

        title = self._extract_meta_title(soup)
        if not title:
            title_elem = soup.find("h1") or soup.find("title")
            title = self._clean_text(title_elem.get_text()) if title_elem else "Unknown"

        if "|" in title:
            title = title.split("|")[0].strip()

        page_text = soup.get_text(" ", strip=True)
        deadline = self._extract_deadline(page_text)

        guest_editors = self._extract_guest_editors(soup)
        topics = self._extract_topics(soup)

        description = self._extract_meta_description(soup)
        if not description:
            h1 = soup.find("h1")
            if h1:
                p = h1.find_next("p")
                if p:
                    description = self._clean_text(p.get_text())[:500]

        submission_url = self._extract_submission_url(soup)

        return CallForPaper(
            title=title,
            journal_name=self.journal_name or title,
            publisher=self.publisher_name,
            deadline=deadline,
            guest_editors=guest_editors,
            topics=topics,
            url=url,
            description=description,
            accessibility="unknown",
            submission_url=submission_url,
        )

    def _extract_link_title(self, link) -> str:
        title = self._clean_text(link.get_text())
        if title:
            return title
        for attr in ("aria-label", "title"):
            value = link.get(attr)
            if value:
                return self._clean_text(value)
        heading = link.find_parent(["h2", "h3", "h4"])
        if heading:
            return self._clean_text(heading.get_text())
        return ""

    def _extract_description(self, container) -> Optional[str]:
        p = container.find("p")
        if p:
            text = self._clean_text(p.get_text())
            return text[:500] if text else None
        return None

    def _extract_deadline(self, text: str) -> Optional[str]:
        if not text:
            return None
        patterns = [
            r"(?:submission\\s+)?deadline[:\\s]*(\\d{1,2}\\s+\\w+\\s+\\d{4})",
            r"submit\\s+by[:\\s]*(\\d{1,2}\\s+\\w+\\s+\\d{4})",
            r"deadline[:\\s]*(\\d{4}-\\d{2}-\\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1)
        return self._extract_date(text)

    def _infer_accessibility(self, text: str) -> str:
        text_lower = text.lower()
        if "open" in text_lower or "accepting submissions" in text_lower:
            return "open"
        if "closed" in text_lower or "no longer accepting" in text_lower:
            return "closed"
        return "unknown"

    def _extract_meta_title(self, soup) -> str:
        meta = soup.find("meta", {"property": "og:title"}) or soup.find(
            "meta", {"name": "dc.title"}
        )
        if meta and meta.get("content"):
            return self._clean_text(meta.get("content"))
        return ""

    def _extract_meta_description(self, soup) -> Optional[str]:
        meta = soup.find("meta", {"name": "description"}) or soup.find(
            "meta", {"property": "og:description"}
        )
        if meta and meta.get("content"):
            return self._clean_text(meta.get("content"))
        return None

    def _extract_guest_editors(self, soup) -> list[str]:
        guest_editors: list[str] = []

        def extract_names(text: str) -> list[str]:
            cleaned = self._clean_text(text)
            if not cleaned:
                return []
            cleaned = re.sub(r"guest\\s+editors?:?", "", cleaned, flags=re.I).strip()
            cleaned = re.sub(r"editors?:?", "", cleaned, flags=re.I).strip()
            parts = re.split(r"[;,]|\\band\\b", cleaned)
            results = []
            blacklist = re.compile(
                r"(submission|deadline|collection|topic|nature|springer|editorial|submit)",
                re.I,
            )
            name_pattern = re.compile(
                r"^(?:Dr\.|Prof\.|Mr\.|Ms\.)?\s*[A-Z][A-Za-z'-]+"
                r"(?:\s+[A-Z][A-Za-z'-]+){1,3}$"
            )
            for part in parts:
                part = self._clean_text(part)
                if not part:
                    continue
                if blacklist.search(part):
                    continue
                if name_pattern.match(part):
                    results.append(part)
            return results

        # Prefer heading-based section scan (more reliable)
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
            if "guest editor" in self._clean_text(heading.get_text()).lower():
                scope = heading.find_parent(["section", "div", "article"]) or heading.parent
                items = scope.find_all("li") if scope else []
                if items:
                    for li in items:
                        guest_editors.extend(extract_names(li.get_text()))
                break

        if not guest_editors:
            header = soup.find(string=re.compile(r"guest\\s+editor|guest\\s+editors|editors?", re.I))
            if header:
                header_tag = header.find_parent(["h1", "h2", "h3", "h4", "h5"])
                scope = None
                if header_tag:
                    scope = header_tag.find_parent(["section", "div", "article"]) or header_tag.parent
                else:
                    scope = header.find_parent()

                if scope:
                    items = scope.find_all("li")
                    if items:
                        for li in items:
                            guest_editors.extend(extract_names(li.get_text()))
                    else:
                        for sib in scope.find_all_next(["p", "div", "span"], limit=2):
                            guest_editors.extend(extract_names(sib.get_text()))

        # De-duplicate while preserving order
        seen = set()
        guest_editors = [e for e in guest_editors if not (e in seen or seen.add(e))]
        return guest_editors

    def _extract_topics(self, soup) -> list[str]:
        topics: list[str] = []
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
            if "topic" in self._clean_text(heading.get_text()).lower():
                scope = heading.find_parent(["section", "div", "article"]) or heading.parent
                items = scope.find_all("li") if scope else []
                topics = [self._clean_text(li.get_text()) for li in items[:20] if li.get_text()]
                break

        if not topics:
            section = soup.find(string=re.compile(r"topics?|scope|subject\s+areas?", re.I))
            if section:
                parent = section.find_parent(["section", "div", "article"]) or section.find_parent()
                if parent:
                    items = parent.find_all("li")
                    topics = [self._clean_text(li.get_text()) for li in items[:20] if li.get_text()]
        return topics

    def _extract_submission_url(self, soup) -> Optional[str]:
        for link in soup.find_all("a", href=True):
            text = self._clean_text(link.get_text()).lower()
            href = link.get("href")
            if not href:
                continue
            if "submit" in text or "submission" in text:
                return urljoin("https://www.nature.com", href)
            if re.search(r"editorialmanager|manuscriptcentral|mts-", href, re.I):
                return href
        return None
