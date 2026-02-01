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
                
                return {
                    "journal_name": result.get("display_name"),
                    "publisher_raw": publisher_raw,
                    "publisher": cls.normalize_publisher_name(publisher_raw),
                    "issn": result.get("external_id"),
                    "openalex_id": result.get("id"),
                    "works_count": result.get("works_count"),
                    "cited_by_count": result.get("cited_by_count"),
                }
                
        except Exception:
            # Silently fail - this is a fallback mechanism
            return None
