"""CFP data models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CallForPaper(BaseModel):
    """Model representing a Call for Papers entry."""

    title: str = Field(..., description="Special Issue title/Topic")
    journal_name: str = Field(..., description="Journal name")
    publisher: str = Field(..., description="Publisher name")
    deadline: Optional[str] = Field(None, description="Submission deadline")
    guest_editors: list[str] = Field(default_factory=list, description="List of guest editors")
    topics: list[str] = Field(default_factory=list, description="List of call topics")
    accessibility: str = Field(
        default="unknown",
        description="Accessibility: 'open', 'invite_only', or 'unknown'",
    )
    url: str = Field(..., description="Original CFP link")
    description: Optional[str] = Field(None, description="Brief description")
    submission_url: Optional[str] = Field(None, description="Submission link if available")

    def deadline_date(self) -> Optional[datetime]:
        """Parse deadline string to datetime if possible."""
        if not self.deadline:
            return None
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%d %B %Y",
            "%B %d, %Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(self.deadline, fmt)
            except ValueError:
                continue
        return None


class CFPList(BaseModel):
    """Model representing a list of CFP entries."""

    journal_name: str = Field(..., description="Journal name searched")
    publisher: str = Field(..., description="Publisher name")
    cfp_page_url: str = Field(..., description="URL of the CFP listing page")
    items: list[CallForPaper] = Field(default_factory=list, description="List of CFP entries")
    total_count: int = Field(0, description="Total number of CFPs found")
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp when data was retrieved",
    )

    def sort_by_deadline(self) -> "CFPList":
        """Sort items by deadline, nearest first. Items without deadline go last."""
        def sort_key(cfp: CallForPaper):
            date = cfp.deadline_date()
            if date is None:
                return datetime.max
            return date

        self.items = sorted(self.items, key=sort_key)
        return self
