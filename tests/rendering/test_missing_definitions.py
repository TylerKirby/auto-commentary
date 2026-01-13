"""Tests for missing definition filtering and collection."""

import pytest

from autocom.core.models import Analysis, Document, Gloss, Line, Page, Token
from autocom.rendering.latex import (
    _sorted_glossary_tokens_with_exclusions,
    collect_missing_definitions,
)


def make_token(text: str, lemma: str, definition: str = None) -> Token:
    """Helper to create a token with optional definition."""
    token = Token(text=text)
    token.analysis = Analysis(lemma=lemma, pos="noun")
    token.gloss = Gloss(
        lemma=lemma,
        senses=[definition] if definition else [],
        headword=lemma,
    )
    return token


def make_line(tokens: list, text: str = "", number: int = None) -> Line:
    """Helper to create a line with tokens."""
    line = Line(tokens=tokens, text=text)
    line.number = number
    return line


class TestGlossaryFiltering:
    """Test that glossary entries without definitions are filtered out."""

    def test_filters_out_tokens_without_definitions(self):
        """Tokens without definitions should not appear in glossary."""
        token_with_def = make_token("amor", "amor", "love")
        token_without_def = make_token("unknown", "unknown", None)

        line = make_line([token_with_def, token_without_def], "amor unknown")

        result = _sorted_glossary_tokens_with_exclusions([line])

        assert len(result) == 1
        assert result[0].text == "amor"

    def test_includes_all_tokens_with_definitions(self):
        """All tokens with definitions should appear in glossary."""
        tokens = [
            make_token("amor", "amor", "love"),
            make_token("rex", "rex", "king"),
            make_token("bellum", "bellum", "war"),
        ]

        line = make_line(tokens, "amor rex bellum")

        result = _sorted_glossary_tokens_with_exclusions([line])

        assert len(result) == 3
        lemmas = [t.analysis.lemma for t in result]
        assert "amor" in lemmas
        assert "rex" in lemmas
        assert "bellum" in lemmas

    def test_empty_senses_treated_as_no_definition(self):
        """Empty senses list should be treated as no definition."""
        token = Token(text="unknown")
        token.analysis = Analysis(lemma="unknown", pos="noun")
        token.gloss = Gloss(lemma="unknown", senses=[], headword="unknown")

        line = make_line([token], "unknown")

        result = _sorted_glossary_tokens_with_exclusions([line])

        assert len(result) == 0

    def test_sorted_alphabetically(self):
        """Results should be sorted alphabetically by headword."""
        tokens = [
            make_token("rex", "rex", "king"),
            make_token("amor", "amor", "love"),
            make_token("bellum", "bellum", "war"),
        ]

        line = make_line(tokens, "rex amor bellum")

        result = _sorted_glossary_tokens_with_exclusions([line])

        assert [t.analysis.lemma for t in result] == ["amor", "bellum", "rex"]

    def test_respects_exclusion_set(self):
        """Excluded lemmas should not appear even with definitions."""
        tokens = [
            make_token("amor", "amor", "love"),
            make_token("rex", "rex", "king"),
        ]

        line = make_line(tokens, "amor rex")
        exclude = {"rex"}

        result = _sorted_glossary_tokens_with_exclusions([line], exclude_lemmas=exclude)

        assert len(result) == 1
        assert result[0].analysis.lemma == "amor"

    def test_respects_max_entries(self):
        """Should limit results to max_entries."""
        tokens = [make_token(f"word{i}", f"word{i}", f"def{i}") for i in range(10)]

        line = make_line(tokens, "text")

        result = _sorted_glossary_tokens_with_exclusions([line], max_entries=5)

        assert len(result) == 5


class TestCollectMissingDefinitions:
    """Test collection of missing definitions for error reporting."""

    def test_collects_missing_from_pages(self):
        """Should collect tokens without definitions from all pages."""
        token_with_def = make_token("amor", "amor", "love")
        token_without_def = make_token("unknown", "unknown", None)

        line = make_line([token_with_def, token_without_def], "amor unknown", number=1)
        page = Page(lines=[line])
        doc = Document(pages=[page], text="amor unknown", language="latin")

        missing = collect_missing_definitions(doc)

        assert len(missing) == 1
        assert missing[0]["word"] == "unknown"
        assert missing[0]["lemma"] == "unknown"
        assert missing[0]["page"] == 1

    def test_includes_line_number_and_context(self):
        """Should include line number and context in missing entries."""
        token_without_def = make_token("mysterium", "mysterium", None)

        line = make_line([token_without_def], "mysterium magnum est", number=42)
        page = Page(lines=[line])
        doc = Document(pages=[page], text="mysterium magnum est", language="latin")

        missing = collect_missing_definitions(doc)

        assert len(missing) == 1
        assert missing[0]["line_number"] == 42
        assert "mysterium" in missing[0]["context"]

    def test_deduplicates_by_lemma(self):
        """Should only report each missing lemma once."""
        token1 = make_token("unknown", "unknown", None)
        token2 = make_token("unknowns", "unknown", None)  # Same lemma

        line = make_line([token1, token2], "unknown unknowns")
        page = Page(lines=[line])
        doc = Document(pages=[page], text="unknown unknowns", language="latin")

        missing = collect_missing_definitions(doc)

        assert len(missing) == 1
        assert missing[0]["lemma"] == "unknown"

    def test_collects_from_core_vocabulary(self):
        """Should check core vocabulary for missing definitions."""
        token_without_def = make_token("frequency_word", "frequency_word", None)

        page = Page(lines=[])
        doc = Document(pages=[page], text="frequency_word", language="latin")
        doc.core_vocabulary = [token_without_def]

        missing = collect_missing_definitions(doc)

        assert len(missing) == 1
        assert missing[0]["context"] == "core_vocabulary"

    def test_sorted_by_lemma(self):
        """Missing entries should be sorted by lemma."""
        tokens = [
            make_token("zebra", "zebra", None),
            make_token("alpha", "alpha", None),
            make_token("middle", "middle", None),
        ]

        line = make_line(tokens, "zebra alpha middle")
        page = Page(lines=[line])
        doc = Document(pages=[page], text="zebra alpha middle", language="latin")

        missing = collect_missing_definitions(doc)

        lemmas = [m["lemma"] for m in missing]
        assert lemmas == ["alpha", "middle", "zebra"]

    def test_skips_punctuation(self):
        """Should not report punctuation as missing definitions."""
        punct = Token(text=".", is_punct=True)

        line = make_line([punct], ".")
        page = Page(lines=[line])
        doc = Document(pages=[page], text=".", language="latin")

        missing = collect_missing_definitions(doc)

        assert len(missing) == 0

    def test_skips_numbers(self):
        """Should not report numbers as missing definitions."""
        number = Token(text="42")

        line = make_line([number], "42")
        page = Page(lines=[line])
        doc = Document(pages=[page], text="42", language="latin")

        missing = collect_missing_definitions(doc)

        assert len(missing) == 0

    def test_empty_document_returns_empty_list(self):
        """Empty document should return empty list."""
        doc = Document(pages=[], text="", language="latin")

        missing = collect_missing_definitions(doc)

        assert missing == []

    def test_all_defined_returns_empty_list(self):
        """Document with all definitions should return empty list."""
        token = make_token("amor", "amor", "love")

        line = make_line([token], "amor")
        page = Page(lines=[line])
        doc = Document(pages=[page], text="amor", language="latin")

        missing = collect_missing_definitions(doc)

        assert missing == []
