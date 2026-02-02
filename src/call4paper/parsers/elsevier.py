"""Elsevier/ScienceDirect CFP parser."""

import re
from typing import Optional
from urllib.parse import urljoin

from .base import BaseParser
from ..models.cfp import CallForPaper, CFPList


class ElsevierParser(BaseParser):
    """Parser for Elsevier/ScienceDirect CFP pages."""

    publisher_name = "Elsevier"
    supported_domains = ["sciencedirect.com", "elsevier.com"]

    def parse_cfp_list(self, html: str, url: str) -> CFPList:
        """Parse ScienceDirect special issues listing page.

        Expected URL formats:
        - https://www.sciencedirect.com/browse/calls-for-papers (unified browse page)
        - https://www.sciencedirect.com/journal/{journal}/special-issues (journal specific)
        """
        soup = self._create_soup(html)
        cfp_items = []

        # Check if this is the unified browse page
        if "browse/calls-for-papers" in url:
            # Parse browse page structure (has different layout)
            cfp_items = self._parse_browse_page(soup, url)
        else:
            # Parse journal-specific page
            cfp_items = self._parse_journal_page(soup, url)

        return CFPList(
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            cfp_page_url=url,
            items=cfp_items,
            total_count=len(cfp_items),
        )

    def _parse_browse_page(self, soup, base_url: str) -> list[CallForPaper]:
        """Parse the unified browse/calls-for-papers page.
        
        This page lists all CFPs across all journals with a specific structure.
        First try to extract from JSON data, then fallback to HTML parsing.
        """
        import json
        
        cfp_items = []
        
        # Method 1: Try to extract from embedded JSON data (window.INITIAL_STATE)
        for script in soup.find_all('script'):
            script_text = script.string or ''
            # Look for window.INITIAL_STATE with callsForPapers data
            if 'window.INITIAL_STATE' in script_text and len(script_text) > 100000:
                try:
                    # Extract JSON from window.INITIAL_STATE = {...}
                    match = re.search(r'window\.INITIAL_STATE\s*=\s*(\{.*)', script_text, re.DOTALL)
                    if match:
                        json_str = match.group(1).rstrip().rstrip(';')
                        json_data = json.loads(json_str)
                        cfp_items = self._extract_cfps_from_json(json_data, base_url)
                        if cfp_items:
                            return cfp_items
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    # Log and continue to fallback
                    pass
        
        # Method 2: Fallback to HTML parsing if JSON extraction fails
        # Find publication entries (li elements with class 'publication')
        publication_items = soup.find_all("li", class_="publication")
        
        for item in publication_items:
            # Extract title from the main link
            title_link = item.find("a", class_="js-publication-title")
            if not title_link:
                continue
                
            title = self._clean_text(title_link.get_text())
            if not title:
                continue
            
            # Get CFP URL
            cfp_url = ""
            if title_link.get("href"):
                cfp_url = urljoin(base_url, title_link["href"])
            
            # Extract journal name from publication-text
            journal_name = self.journal_name  # default
            pub_text_elem = item.find("p", class_="publication-text")
            if pub_text_elem:
                pub_text = self._clean_text(pub_text_elem.get_text())
                # Format: "Journal Name • Impact Factor X.X • CiteScore X.X"
                if pub_text and "•" in pub_text:
                    journal_name = pub_text.split("•")[0].strip()
            
            # Extract deadline
            deadline = None
            deadline_text = item.find(string=lambda x: x and "deadline" in x.lower())
            if deadline_text:
                deadline = self._extract_date(str(deadline_text))
            
            # Extract guest editors
            guest_editors = []
            editors_text = item.find(string=lambda x: x and "guest editor" in x.lower())
            if editors_text:
                parent = editors_text.find_parent() if hasattr(editors_text, 'find_parent') else None
                if parent:
                    editor_names = self._clean_text(parent.get_text())
                    # Simple extraction
                    if ":" in editor_names:
                        editors_part = editor_names.split(":", 1)[1]
                        guest_editors = [name.strip() for name in editors_part.split(";") if name.strip()]
            
            cfp_items.append(
                CallForPaper(
                    title=title,
                    journal_name=journal_name,
                    publisher=self.publisher_name,
                    deadline=deadline,
                    url=cfp_url,
                    guest_editors=guest_editors[:10],
                    accessibility="unknown",
                )
            )
        
        return cfp_items

    def _parse_journal_page(self, soup, base_url: str) -> list[CallForPaper]:
        """Parse journal-specific CFP page."""
        cfp_items = []

        # Find all special issue entries
        # ScienceDirect uses various containers for special issues
        issue_containers = soup.find_all("div", class_=re.compile(r"special-issue|issue-item|call-for-paper", re.I))

        if not issue_containers:
            # Try alternative selectors
            issue_containers = soup.find_all("li", class_=re.compile(r"issue|special", re.I))

        if not issue_containers:
            # Try to find article/section elements
            issue_containers = soup.find_all("article")

        if not issue_containers:
            # Fallback: look for links containing "special issue" or "call for papers"
            issue_containers = soup.find_all("a", href=re.compile(r"special-issue|call-for-paper", re.I))

        for container in issue_containers:
            cfp = self._parse_issue_entry(container, base_url)
            if cfp:
                cfp_items.append(cfp)

        # Also try to find from structured data or specific section headings
        if not cfp_items:
            cfp_items = self._parse_from_sections(soup, base_url)

        return cfp_items

    def _parse_issue_entry(self, container, base_url: str) -> Optional[CallForPaper]:
        """Parse a single issue entry from container element."""
        # Try to find title
        title_elem = (
            container.find("h2")
            or container.find("h3")
            or container.find("h4")
            or container.find("a")
            or container.find(class_=re.compile(r"title", re.I))
        )

        if not title_elem:
            return None

        title = self._clean_text(title_elem.get_text())
        if not title:
            return None

        # Get URL
        link_elem = container.find("a", href=True) if container.name != "a" else container
        cfp_url = ""
        if link_elem and link_elem.get("href"):
            cfp_url = urljoin(base_url, link_elem["href"])

        # Try to extract journal name from container
        # Browse page includes journal name with each CFP
        extracted_journal = self._extract_journal_name(container)
        journal_name = extracted_journal or self.journal_name

        # Try to find deadline
        deadline = None
        deadline_elem = container.find(string=re.compile(r"deadline|submission|due", re.I))
        if deadline_elem:
            parent = deadline_elem.find_parent()
            if parent:
                deadline = self._extract_date(parent.get_text())

        # Try to find description
        desc_elem = container.find("p") or container.find(class_=re.compile(r"desc|summary|abstract", re.I))
        description = self._clean_text(desc_elem.get_text()) if desc_elem else None

        # Try to determine accessibility
        accessibility = "unknown"
        text_content = container.get_text().lower()
        if "invite only" in text_content or "invitation" in text_content:
            accessibility = "invite_only"
        elif "open" in text_content or "submit" in text_content:
            accessibility = "open"

        return CallForPaper(
            title=title,
            journal_name=journal_name,
            publisher=self.publisher_name,
            deadline=deadline,
            url=cfp_url or base_url,
            description=description,
            accessibility=accessibility,
        )

    def _parse_from_sections(self, soup, base_url: str) -> list[CallForPaper]:
        """Alternative parsing method using section headings."""
        cfp_items = []

        # Look for heading elements that might indicate CFP entries
        headings = soup.find_all(["h2", "h3", "h4"])

        for heading in headings:
            text = self._clean_text(heading.get_text())
            # Skip navigation/common headings
            if text.lower() in ["special issues", "call for papers", "about", "contact"]:
                continue

            # Try to find associated content
            next_elem = heading.find_next_sibling()
            description = None
            deadline = None

            if next_elem:
                description = self._clean_text(next_elem.get_text())
                deadline = self._extract_date(next_elem.get_text())

            # Get link
            link = heading.find("a", href=True)
            cfp_url = urljoin(base_url, link["href"]) if link else base_url

            if text:
                cfp_items.append(
                    CallForPaper(
                        title=text,
                        journal_name=self.journal_name,
                        publisher=self.publisher_name,
                        deadline=deadline,
                        url=cfp_url,
                        description=description[:500] if description else None,
                        accessibility="unknown",
                    )
                )

        return cfp_items

    def parse_cfp_detail(self, html: str, url: str) -> Optional[CallForPaper]:
        """Parse a single CFP detail page."""
        import json

        soup = self._create_soup(html)

        # Find title
        title_elem = soup.find("h1")
        if not title_elem:
            og_title = soup.find("meta", {"property": "og:title"})
            if og_title and og_title.get("content"):
                title_elem = og_title
        if not title_elem:
            title_elem = soup.find("title")
        title = self._clean_text(title_elem.get_text()) if title_elem else "Unknown"
        if title_elem and title_elem.name == "meta":
            title = self._clean_text(title_elem.get("content", "")) or title

        # Find deadline
        deadline = None
        deadline_section = soup.find(string=re.compile(r"deadline|submission date|due date", re.I))
        if deadline_section:
            parent = deadline_section.find_parent()
            if parent:
                deadline = self._extract_date(parent.get_text())

        # Find guest editors
        guest_editors = []
        editor_section = soup.find(string=re.compile(r"guest editor|editor", re.I))
        if editor_section:
            parent = editor_section.find_parent()
            if parent:
                # Try to extract names
                names_text = parent.get_text()
                # Simple extraction - names are often comma or newline separated
                potential_names = re.split(r"[,\n]", names_text)
                for name in potential_names:
                    name = self._clean_text(name)
                    if name and len(name) > 3 and len(name) < 100:
                        guest_editors.append(name)

        # Find topics
        topics = []
        topics_section = soup.find(string=re.compile(r"topics|scope|areas", re.I))
        if topics_section:
            parent = topics_section.find_parent()
            if parent:
                list_items = parent.find_all("li")
                topics = [self._clean_text(li.get_text()) for li in list_items if li.get_text().strip()]

        # Find description
        description = None
        desc_elem = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
        if desc_elem:
            description = desc_elem.get("content")
        if not description:
            # Try first paragraph
            p = soup.find("p")
            if p:
                description = self._clean_text(p.get_text())[:500]

        # Find submission URL
        submission_url = None
        submit_link = soup.find("a", string=re.compile(r"submit|submission", re.I))
        if submit_link and submit_link.get("href"):
            submission_url = urljoin(url, submit_link["href"])

        # Special-issue pages often embed structured data
        def _find_json_block(predicate):
            def _walk(obj):
                if isinstance(obj, dict):
                    if predicate(obj):
                        return obj
                    for value in obj.values():
                        hit = _walk(value)
                        if hit:
                            return hit
                elif isinstance(obj, list):
                    for item in obj:
                        hit = _walk(item)
                        if hit:
                            return hit
                return None
            return _walk

        # Try JSON-LD for title/description
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(data, list):
                candidates = data
            else:
                candidates = [data]
            for item in candidates:
                if isinstance(item, dict):
                    if title == "Unknown" and item.get("name"):
                        title = self._clean_text(item.get("name"))
                    if not description and item.get("description"):
                        description = self._clean_text(item.get("description"))[:500]

        # Try window.INITIAL_STATE for deadline and editors
        init_script = soup.find(string=re.compile(r"window\\.INITIAL_STATE", re.I))
        if init_script:
            match = re.search(r"window\\.INITIAL_STATE\\s*=\\s*(\\{.*\\});", init_script, re.S)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    data = None
                if data:
                    finder = _find_json_block(lambda o: "submissionDeadline" in o or "expiryDate" in o)
                    block = finder(data)
                    if block:
                        if not deadline:
                            deadline = self._extract_date(
                                str(block.get("submissionDeadline") or block.get("expiryDate") or "")
                            )
                        if title == "Unknown" and block.get("title"):
                            title = self._clean_text(block.get("title"))
                        summary = block.get("summary") or ""
                        if summary and not guest_editors:
                            if "Guest editor" in summary:
                                editor_text = summary.split("Guest editor")[-1].split(":")[-1].strip()
                                guest_editors = [e.strip() for e in editor_text.split(",") if e.strip()]

        return CallForPaper(
            title=title,
            journal_name=self.journal_name,
            publisher=self.publisher_name,
            deadline=deadline,
            guest_editors=guest_editors[:10],  # Limit to 10 editors
            topics=topics[:20],  # Limit to 20 topics
            url=url,
            description=description,
            submission_url=submission_url,
            accessibility="unknown",
        )

    def _extract_journal_name(self, container) -> Optional[str]:
        """Extract journal name from a container element.
        
        Used when parsing browse pages where journal name is included with each CFP.
        """
        # Look for journal name in specific elements
        # ScienceDirect browse page often includes journal name in separate element
        journal_elem = container.find(class_=re.compile(r"journal|publication", re.I))
        if journal_elem:
            journal_text = self._clean_text(journal_elem.get_text())
            if journal_text and len(journal_text) < 100:  # Reasonable journal name length
                return journal_text
        
        # Try to find link to journal page
        journal_link = container.find("a", href=re.compile(r"/journal/[^/]+$"))
        if journal_link:
            journal_text = self._clean_text(journal_link.get_text())
            if journal_text:
                return journal_text
        
        return None

    def _extract_cfps_from_json(self, data: dict, base_url: str) -> list[CallForPaper]:
        """Extract CFP information from JSON data structure.
        
        This handles the case where CFP data is embedded as JSON in the page.
        Specifically handles window.INITIAL_STATE structure from ScienceDirect.
        """
        import json
        from datetime import datetime
        
        cfp_items = []
        
        # First check for the specific window.INITIAL_STATE structure
        if 'callsForPapers' in data:
            cfp_data = data['callsForPapers']
            if isinstance(cfp_data, dict) and 'cfpList' in cfp_data:
                cfp_list = cfp_data['cfpList']
                if isinstance(cfp_list, list):
                    # Found the data!
                    for item in cfp_list:
                        cfp = self._parse_cfp_json_item(item, base_url)
                        if cfp:
                            cfp_items.append(cfp)
                    return cfp_items
        
        # Fallback: recursive search for CFP list in nested structure
        def find_cfp_list(obj, path=""):
            """Recursively search for CFP list in nested JSON structure."""
            if isinstance(obj, dict):
                # Look for keys that might contain CFP data
                for key in ['callForPapers', 'calls-for-papers', 'cfps', 'items', 'cfpList']:
                    if key in obj:
                        candidate = obj[key]
                        if isinstance(candidate, list) and len(candidate) > 0:
                            # Check if first item looks like a CFP
                            first = candidate[0] if candidate else {}
                            if isinstance(first, dict) and ('title' in first or 'displayName' in first.get('journal', {})):
                                return candidate
                        elif isinstance(candidate, dict):
                            result = find_cfp_list(candidate, f"{path}/{key}")
                            if result:
                                return result
                
                # Recursively search in nested dicts
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        result = find_cfp_list(value, f"{path}/{key}")
                        if result:
                            return result
            
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        result = find_cfp_list(item, path)
                        if result:
                            return result
            
            return None
        
        # Try to find the CFP list using recursive search
        cfp_list = find_cfp_list(data)
        
        if cfp_list:
            for item in cfp_list:
                if isinstance(item, dict):
                    cfp = self._parse_cfp_json_item(item, base_url)
                    if cfp:
                        cfp_items.append(cfp)
        
        return cfp_items
    
    def _parse_cfp_json_item(self, item: dict, base_url: str) -> Optional[CallForPaper]:
        """Parse a single CFP item from JSON data."""
        from datetime import datetime
        
        # Extract journal information
        journal = item.get('journal', {})
        journal_name = journal.get('displayName', journal.get('title', 'Unknown'))
        
        # Extract CFP details
        title = item.get('title', '')
        if not title:
            return None
        
        # Build URL (ScienceDirect special issue pages use contentId + slug)
        url_path = item.get('url', '')
        content_id = item.get('contentId')
        if content_id and url_path and not url_path.startswith('http'):
            url = urljoin(base_url, f"/special-issue/{content_id}/{url_path}")
        else:
            url = url_path or base_url
        
        # Extract dates
        deadline = None
        deadline_str = item.get('submissionDeadline', '') or item.get('expiryDate', '')
        if deadline_str:
            try:
                # Parse ISO date format and keep as string in ISO format (YYYY-MM-DD)
                date_obj = datetime.fromisoformat(deadline_str.replace('Z', '+00:00')).date()
                deadline = date_obj.isoformat()  # Convert back to string
            except (ValueError, AttributeError):
                pass
        
        # Extract other fields
        summary = item.get('summary', '')
        guest_editors = []
        if summary:
            # Try to extract guest editors from summary
            if 'Guest editor' in summary:
                editor_text = summary.split('Guest editor')[1].split(':')[-1].strip()
                guest_editors = [e.strip() for e in editor_text.split(',') if e.strip()]
        
        # Extract metrics if available
        description_parts = []
        if journal.get('impactFactor'):
            description_parts.append(f"Impact Factor: {journal['impactFactor']}")
        if journal.get('citeScore'):
            description_parts.append(f"CiteScore: {journal['citeScore']}")
        if journal.get('issn'):
            description_parts.append(f"ISSN: {journal['issn']}")
        
        if summary:
            description_parts.append(f"Summary: {summary}")
        
        description = " • ".join(description_parts) if description_parts else None
        
        return CallForPaper(
            title=title,
            journal_name=journal_name,
            publisher=self.publisher_name,
            deadline=deadline,
            guest_editors=guest_editors,
            topics=[],
            url=url,
            description=description,
            submission_url=None,
            accessibility="open" if item.get('type') == 'call-for-papers' else "unknown",
        )
