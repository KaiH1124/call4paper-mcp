"""Tests for Elsevier parser."""

import pytest
from call4paper.parsers.elsevier import ElsevierParser


class TestElsevierParser:
    """Test suite for ElsevierParser."""

    def test_can_handle_sciencedirect(self):
        """Test that parser recognizes ScienceDirect URLs."""
        parser = ElsevierParser("Test Journal")
        assert parser.can_handle("https://www.sciencedirect.com/journal/test/special-issues")
        assert parser.can_handle("https://sciencedirect.com/journal/test")

    def test_can_handle_elsevier(self):
        """Test that parser recognizes Elsevier URLs."""
        parser = ElsevierParser("Test Journal")
        assert parser.can_handle("https://www.elsevier.com/journals/test")

    def test_cannot_handle_other_domains(self):
        """Test that parser rejects non-Elsevier URLs."""
        parser = ElsevierParser("Test Journal")
        assert not parser.can_handle("https://www.springer.com/journal/test")
        assert not parser.can_handle("https://ieee.org/publications")

    def test_parse_simple_html(self):
        """Test parsing a simple HTML structure."""
        html = """
        <html>
        <body>
            <div class="special-issue">
                <h3><a href="/special-issue/ai-energy">AI in Energy Systems</a></h3>
                <p>Deadline: December 31, 2025</p>
                <p>This special issue focuses on AI applications in energy.</p>
            </div>
        </body>
        </html>
        """
        parser = ElsevierParser("Energy and Buildings")
        result = parser.parse_cfp_list(html, "https://www.sciencedirect.com/journal/energy-and-buildings/special-issues")

        assert result.journal_name == "Energy and Buildings"
        assert result.publisher == "Elsevier"
        assert len(result.items) >= 1

    def test_clean_text(self):
        """Test text cleaning utility."""
        parser = ElsevierParser("Test")
        assert parser._clean_text("  hello   world  ") == "hello world"
        assert parser._clean_text(None) == ""

    def test_extract_date(self):
        """Test date extraction."""
        parser = ElsevierParser("Test")
        assert parser._extract_date("Deadline: December 31, 2025") == "December 31, 2025"
        assert parser._extract_date("Due: 2025-12-31") == "2025-12-31"
        assert parser._extract_date("No date here") is None
