"""Configuration management."""

import json
from pathlib import Path
from typing import Optional
import httpx


class Config:
    """Configuration manager for the CFP server."""

    # Publisher domain mappings
    PUBLISHER_DOMAINS = {
        "sciencedirect.com": "elsevier",
        "elsevier.com": "elsevier",
        "springer.com": "springer",
        "springerlink.com": "springer",
        "link.springer.com": "springer",
        "nature.com": "springer",
        "ieee.org": "ieee",
        "ieeexplore.ieee.org": "ieee",
        "wiley.com": "wiley",
        "onlinelibrary.wiley.com": "wiley",
        "tandfonline.com": "taylor_francis",
    }

    # CFP URL templates for each publisher
    CFP_URL_TEMPLATES = {
        "elsevier": "https://www.sciencedirect.com/journal/{journal_slug}/about/call-for-papers",
        "springer": "https://www.springer.com/journal/{journal_id}/updates",
        "ieee": "https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber={journal_id}",
        "wiley": "https://onlinelibrary.wiley.com/journal/{journal_id}",
    }

    # Publisher name normalization mapping
    PUBLISHER_NORMALIZATION = {
        "elsevier": ["elsevier", "elsevier bv"],
        "springer": ["springer", "springer nature", "springer science and business media"],
        "wiley": ["wiley", "john wiley", "wiley-blackwell"],
        "ieee": ["ieee", "institute of electrical and electronics engineers"],
    }

    # Cache settings
    CACHE_TTL_HOURS = 24
    CACHE_DIR = Path.home() / ".cache" / "call4paper"

    # HTTP settings
    HTTP_TIMEOUT = 30
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    # OpenAlex API settings
    OPENALEX_API_BASE = "https://api.openalex.org"
    OPENALEX_TIMEOUT = 10

    @classmethod
    def get_publisher_from_url(cls, url: str) -> Optional[str]:
        """Identify publisher from URL domain."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]

        for known_domain, publisher in cls.PUBLISHER_DOMAINS.items():
            if known_domain in domain:
                return publisher
        return None

    @classmethod
    def load_journal_registry(cls) -> dict:
        """Load journal registry from JSON file."""
        registry_path = Path(__file__).parent.parent.parent.parent / "data" / "journal_registry.json"
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @classmethod
    def get_cfp_url_for_journal(cls, journal_name: str) -> Optional[dict]:
        """Get CFP URL for a journal from registry."""
        registry = cls.load_journal_registry()
        # Normalize journal name for lookup
        normalized = journal_name.lower().strip()

        for entry in registry.get("journals", []):
            if entry.get("name", "").lower() == normalized:
                return entry
            # Also check aliases
            for alias in entry.get("aliases", []):
                if alias.lower() == normalized:
                    return entry
        return None

    @classmethod
    def normalize_publisher_name(cls, publisher_raw: str) -> str:
        """Normalize publisher name to standard identifier.
        
        Args:
            publisher_raw: Raw publisher name from external sources
            
        Returns:
            Normalized publisher identifier (e.g., 'elsevier', 'springer')
        """
        if not publisher_raw:
            return "unknown"
        
        publisher_lower = publisher_raw.lower()
        
        for standard_name, patterns in cls.PUBLISHER_NORMALIZATION.items():
            for pattern in patterns:
                if pattern in publisher_lower:
                    return standard_name
        
        return "unknown"

    @classmethod
    async def get_publisher_from_openalex(cls, journal_name: str) -> Optional[dict]:
        """Get publisher information from OpenAlex API.

        Args:
            journal_name: Name of the journal to search

        Returns:
            Dictionary with journal and publisher information, or None if not found
        """
        url = f"{cls.OPENALEX_API_BASE}/autocomplete/sources"
        params = {"q": journal_name}

        try:
            async with httpx.AsyncClient(timeout=cls.OPENALEX_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data.get("results"):
                    return None

                # Get the best match (first result)
                result = data["results"][0]
                publisher_raw = result.get("hint", "")
                openalex_id = result.get("id")

                # Fetch full source details to get homepage_url
                homepage_url = None
                springer_journal_id = None
                nature_short_name = None

                if openalex_id:
                    source_id = openalex_id.split('/')[-1]
                    detail_url = f"{cls.OPENALEX_API_BASE}/sources/{source_id}"

                    try:
                        detail_response = await client.get(detail_url)
                        detail_response.raise_for_status()
                        detail_data = detail_response.json()
                        homepage_url = detail_data.get("homepage_url", "")

                        # Extract Springer journal ID from homepage URL
                        # Handle both formats:
                        # - https://www.springer.com/journal/12273
                        # - http://www.springer.com/computer/programming/journal/11227
                        # - https://link.springer.com/journal/12053
                        if homepage_url and "/journal/" in homepage_url and "springer" in homepage_url.lower():
                            parts = homepage_url.split('/journal/')
                            if len(parts) > 1:
                                # Extract journal ID (numeric part after /journal/)
                                journal_id_part = parts[1].split('/')[0].split('?')[0]
                                # Ensure it's numeric
                                if journal_id_part.isdigit():
                                    springer_journal_id = journal_id_part
                        # Extract Nature short name from homepage URL
                        if homepage_url and "nature.com" in homepage_url.lower():
                            try:
                                from urllib.parse import urlparse

                                parsed = urlparse(homepage_url)
                                path_parts = [p for p in parsed.path.split("/") if p]
                                if path_parts:
                                    if path_parts[0] == "journals" and len(path_parts) > 1:
                                        nature_short_name = path_parts[1]
                                    else:
                                        nature_short_name = path_parts[0]
                            except Exception:
                                pass
                    except Exception:
                        pass  # Continue with autocomplete data

                return {
                    "journal_name": result.get("display_name"),
                    "publisher_raw": publisher_raw,
                    "publisher": cls.normalize_publisher_name(publisher_raw),
                    "issn": result.get("external_id"),
                    "openalex_id": openalex_id,
                    "works_count": result.get("works_count"),
                    "cited_by_count": result.get("cited_by_count"),
                    "homepage_url": homepage_url,
                    "springer_journal_id": springer_journal_id,
                    "nature_short_name": nature_short_name,
                }

        except Exception:
            # Silently fail - this is a fallback mechanism
            return None

    @classmethod
    async def search_journals_by_keyword(
        cls, 
        keyword: str, 
        max_results: int = 20,
        min_works: int = 500,
        mode: str = "topic"
    ) -> list[dict]:
        """Search for journals by keyword using OpenAlex API.
        
        This enables cross-journal CFP discovery by topic/keyword.
        
        Args:
            keyword: Search keyword or phrase (e.g., "machine learning", "renewable energy")
            max_results: Maximum number of journals to return (default: 20)
            min_works: Minimum number of published works to filter quality journals (default: 500)
            mode: "topic" (search by research topic, default) or "name" (search journal names)
            
        Returns:
            List of dictionaries containing journal information:
            - journal_name: Display name of the journal
            - publisher: Normalized publisher name
            - publisher_raw: Original publisher name from OpenAlex
            - works_count: Number of published works
            - cited_by_count: Total citation count
            - citation_rate: Citations per paper (quality indicator, similar to IF)
            - homepage_url: Journal homepage URL (if available)
            - issn_l: Linking ISSN
            - topic_papers_count: (topic mode only) Papers on this specific topic
        """
        # Known non-journal sources to exclude
        EXCLUDE_SOURCES = {
            'arxiv', 'zenodo', 'ssrn', 'biorxiv', 'medrxiv', 'preprints',
            'research square', 'figshare', 'dryad', 'hal', 'pubmed central'
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if mode == "topic":
                    # Search papers by topic, group by journal
                    url = f"{cls.OPENALEX_API_BASE}/works"
                    params = {
                        "search": keyword,
                        "group_by": "primary_location.source.id",
                        "per_page": max_results * 3  # Fetch more to filter
                    }
                    
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    results = []
                    for group in data.get("group_by", []):
                        source_id = group.get('key')
                        topic_papers = group.get('count', 0)
                        
                        if not source_id or not source_id.startswith('https://openalex.org/S'):
                            continue
                        
                        # Fetch journal details
                        source_api_id = source_id.split('/')[-1]
                        api_url = f"{cls.OPENALEX_API_BASE}/sources/{source_api_id}"
                        
                        try:
                            journal_resp = await client.get(api_url)
                            journal_resp.raise_for_status()
                            journal_data = journal_resp.json()
                            
                            # Must be a journal (not repository, conference, etc.)
                            if journal_data.get('type') != 'journal':
                                continue
                            
                            journal_name = journal_data.get('display_name', '')
                            
                            # Exclude preprint servers and repositories
                            if any(excl in journal_name.lower() for excl in EXCLUDE_SOURCES):
                                continue
                            
                            works_count = journal_data.get('works_count', 0)
                            cited_by_count = journal_data.get('cited_by_count', 0)
                            
                            # Filter by minimum works
                            if works_count < min_works:
                                continue
                            
                            # Calculate citation rate (proxy for impact factor)
                            citation_rate = cited_by_count / works_count if works_count > 0 else 0
                            
                            publisher_raw = journal_data.get('host_organization_name') or 'Unknown'
                            
                            results.append({
                                "journal_name": journal_name,
                                "publisher": cls.normalize_publisher_name(publisher_raw),
                                "publisher_raw": publisher_raw,
                                "works_count": works_count,
                                "cited_by_count": cited_by_count,
                                "citation_rate": round(citation_rate, 2),
                                "homepage_url": journal_data.get('homepage_url'),
                                "issn_l": journal_data.get('issn_l'),
                                "topic_papers_count": topic_papers,
                            })
                            
                        except Exception:
                            continue
                    
                    # Sort by citation rate (impact), then by topic relevance
                    results.sort(key=lambda x: (x.get('citation_rate', 0), x.get('topic_papers_count', 0)), reverse=True)
                    
                else:  # mode == "name"
                    # Search journals by name
                    url = f"{cls.OPENALEX_API_BASE}/sources"
                    params = {
                        "search": keyword,
                        "per_page": max_results * 2,
                        "filter": "type:journal",
                    }
                    
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    results = []
                    for result in data.get("results", []):
                        journal_name = result.get("display_name", "")
                        
                        # Exclude preprint servers
                        if any(excl in journal_name.lower() for excl in EXCLUDE_SOURCES):
                            continue
                        
                        works_count = result.get("works_count", 0)
                        cited_by_count = result.get("cited_by_count", 0)
                        
                        if works_count < min_works:
                            continue
                        
                        citation_rate = cited_by_count / works_count if works_count > 0 else 0
                        publisher_raw = result.get("host_organization_name") or "Unknown"
                        
                        results.append({
                            "journal_name": journal_name,
                            "publisher": cls.normalize_publisher_name(publisher_raw),
                            "publisher_raw": publisher_raw,
                            "works_count": works_count,
                            "cited_by_count": cited_by_count,
                            "citation_rate": round(citation_rate, 2),
                            "homepage_url": result.get("homepage_url"),
                            "issn_l": result.get("issn_l"),
                        })
                    
                    # Sort by citation rate (quality indicator)
                    results.sort(key=lambda x: x["citation_rate"], reverse=True)
                
                # Return top results
                return results[:max_results]
                
        except Exception as e:
            return []
