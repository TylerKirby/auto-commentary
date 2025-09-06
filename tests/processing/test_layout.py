"""
Unit tests for smart pagination and layout functionality.
"""

import pytest
from autocom.core.models import Line, Token, Analysis, Gloss
from autocom.processing.layout import paginate, build_document


def create_token_with_gloss(text: str, lemma: str, definition: str) -> Token:
    """Helper to create a token with analysis and gloss."""
    return Token(
        text=text,
        normalized=text.lower(),
        start_char=0,
        end_char=len(text),
        is_punct=False,
        analysis=Analysis(lemma=lemma, pos_labels=["NOUN"]),
        gloss=Gloss(lemma=lemma, senses=[definition])
    )


def create_punct_token(text: str) -> Token:
    """Helper to create punctuation token."""
    return Token(
        text=text,
        normalized=text,
        start_char=0,
        end_char=len(text),
        is_punct=True
    )


class TestSmartPagination:
    """Test smart pagination that considers text and glossary space."""

    def test_single_line_fits_on_page(self):
        """Single line with few words should fit on one page."""
        line = Line(
            text="Arma virumque cano",
            tokens=[
                create_token_with_gloss("Arma", "arma", "arms, weapons"),
                create_token_with_gloss("virumque", "vir", "man"),
                create_token_with_gloss("cano", "cano", "I sing")
            ],
            number=1
        )
        
        pages = paginate([line], max_lines_per_page=30)
        
        assert len(pages) == 1
        assert len(pages[0].lines) == 1
        assert pages[0].number == 1

    def test_many_lines_few_unique_words(self):
        """Many lines with repeated words should fit more lines per page."""
        # Create 20 lines all using the same 3 words
        lines = []
        for i in range(20):
            line = Line(
                text="Arma virumque cano",
                tokens=[
                    create_token_with_gloss("Arma", "arma", "arms, weapons"),
                    create_token_with_gloss("virumque", "vir", "man"),
                    create_token_with_gloss("cano", "cano", "I sing")
                ],
                number=i+1
            )
            lines.append(line)
        
        pages = paginate(lines, max_lines_per_page=30)
        
        # Should fit most/all on one page since only 3 unique words
        assert len(pages) <= 2
        if len(pages) == 1:
            assert len(pages[0].lines) == 20

    def test_few_lines_many_unique_words(self):
        """Few lines with many unique words should trigger earlier page breaks."""
        lines = []
        # Create lines with many unique words
        for i in range(5):
            tokens = []
            # Each line has 10 unique words
            for j in range(10):
                word_num = i * 10 + j
                tokens.append(create_token_with_gloss(
                    f"word{word_num}", 
                    f"lemma{word_num}", 
                    f"definition for word {word_num}"
                ))
            
            line = Line(
                text=f"Line {i} with many unique words",
                tokens=tokens,
                number=i+1
            )
            lines.append(line)
        
        pages = paginate(lines, max_lines_per_page=30)
        
        # With 5 lines * 10 words = 50 unique glossary entries
        # Should definitely split across multiple pages
        assert len(pages) >= 2

    def test_punctuation_ignored_in_glossary(self):
        """Punctuation tokens should not count toward glossary size."""
        line = Line(
            text="Arma, virumque; cano!",
            tokens=[
                create_token_with_gloss("Arma", "arma", "arms, weapons"),
                create_punct_token(","),
                create_token_with_gloss("virumque", "vir", "man"),
                create_punct_token(";"),
                create_token_with_gloss("cano", "cano", "I sing"),
                create_punct_token("!")
            ],
            number=1
        )
        
        pages = paginate([line], max_lines_per_page=30)
        
        # Should still fit easily - only 3 glossary entries, not 6
        assert len(pages) == 1

    def test_duplicate_lemmas_deduplicated(self):
        """Same lemma appearing multiple times should only count once in glossary."""
        line = Line(
            text="arma arma arma",
            tokens=[
                create_token_with_gloss("arma", "arma", "arms, weapons"),
                create_token_with_gloss("arma", "arma", "arms, weapons"),
                create_token_with_gloss("arma", "arma", "arms, weapons")
            ],
            number=1
        )
        
        pages = paginate([line], max_lines_per_page=30)
        
        # Should fit easily since only 1 unique glossary entry
        assert len(pages) == 1

    def test_page_break_calculation(self):
        """Test the space calculation logic."""
        # Create a scenario where we know the exact break point
        lines = []
        
        # First, add lines that should fit
        for i in range(10):
            line = Line(
                text=f"simple line {i}",
                tokens=[create_token_with_gloss(f"word{i}", f"lemma{i}", f"def{i}")],
                number=i+1
            )
            lines.append(line)
        
        # 10 text lines + 10 glossary entries + 1 header + 20% buffer
        # = (10 + 11) * 1.2 = 25.2 -> fits in 30
        
        # Add one more line that should push to next page
        line = Line(
            text="overflow line",
            tokens=[
                create_token_with_gloss("word10", "lemma10", "def10"),
                create_token_with_gloss("word11", "lemma11", "def11"),
                create_token_with_gloss("word12", "lemma12", "def12"),
                create_token_with_gloss("word13", "lemma13", "def13"),
                create_token_with_gloss("word14", "lemma14", "def14")
            ],
            number=11
        )
        lines.append(line)
        
        pages = paginate(lines, max_lines_per_page=30)
        
        # Should split into 2 pages
        assert len(pages) == 2

    def test_empty_lines_handled(self):
        """Empty lines should be handled gracefully."""
        pages = paginate([], max_lines_per_page=30)
        assert len(pages) == 0

    def test_single_large_line_gets_own_page(self):
        """A single line with many unique words should get its own page."""
        # Create one line with 25 unique words
        tokens = []
        for i in range(25):
            tokens.append(create_token_with_gloss(
                f"word{i}", 
                f"lemma{i}", 
                f"very long definition for word {i} that might wrap"
            ))
        
        large_line = Line(
            text="Line with many words",
            tokens=tokens,
            number=1
        )
        
        # Add a simple line after
        simple_line = Line(
            text="Simple line",
            tokens=[create_token_with_gloss("simple", "simple", "easy")],
            number=2
        )
        
        pages = paginate([large_line, simple_line], max_lines_per_page=30)
        
        # Large line should get its own page
        assert len(pages) == 2
        assert len(pages[0].lines) == 1  # Just the large line
        assert len(pages[1].lines) == 1  # Just the simple line


class TestBuildDocument:
    """Test document building with smart pagination."""

    def test_build_document_with_smart_pagination(self):
        """Test that build_document uses smart pagination."""
        lines = [
            Line(
                text="Arma virumque cano",
                tokens=[create_token_with_gloss("Arma", "arma", "arms")],
                number=1
            )
        ]
        
        doc = build_document("Arma virumque cano", "latin", lines)
        
        assert doc.language == "latin"
        assert doc.text == "Arma virumque cano"
        assert len(doc.pages) == 1
        assert len(doc.pages[0].lines) == 1

    def test_build_document_respects_max_lines(self):
        """Test that custom max_lines_per_page is respected."""
        lines = []
        for i in range(10):
            line = Line(
                text=f"line {i}",
                tokens=[create_token_with_gloss(f"word{i}", f"lemma{i}", f"def{i}")],
                number=i+1
            )
            lines.append(line)
        
        # Force very small pages
        doc = build_document("text", "latin", lines, max_lines_per_page=5)
        
        # Should create multiple pages
        assert len(doc.pages) >= 2