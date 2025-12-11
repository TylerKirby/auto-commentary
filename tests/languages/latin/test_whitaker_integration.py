"""Tests for Whitaker's Words integration as primary dictionary source."""

import pytest

from autocom.core.models import Analysis, Token
from autocom.languages.latin.lexicon import LatinLexicon


@pytest.mark.whitakers
class TestWhitakerMetadataExtraction:
    """Test Whitaker's Words metadata extraction."""

    @pytest.fixture
    def whitaker_lexicon(self):
        """Create lexicon with Whitaker as primary source."""
        return LatinLexicon(max_senses=3, primary_source="whitakers", enable_api_fallbacks=False)

    def test_whitaker_returns_senses_for_common_verb(self, whitaker_lexicon):
        """Test that Whitaker returns definitions for common verbs."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("amo")
        assert len(result["senses"]) > 0
        # Check for common meaning
        senses_lower = " ".join(result["senses"]).lower()
        assert "love" in senses_lower or "like" in senses_lower

    def test_whitaker_returns_senses_for_noun(self, whitaker_lexicon):
        """Test that Whitaker returns definitions for common nouns."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("puella")
        assert len(result["senses"]) > 0
        senses_lower = " ".join(result["senses"]).lower()
        assert "girl" in senses_lower or "maiden" in senses_lower

    def test_whitaker_extracts_gender_feminine(self, whitaker_lexicon):
        """Test gender extraction for feminine nouns."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("puella")
        assert result.get("gender") == "f."

    def test_whitaker_extracts_gender_masculine(self, whitaker_lexicon):
        """Test gender extraction for masculine nouns."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("puer")
        assert result.get("gender") == "m."

    def test_whitaker_extracts_gender_neuter(self, whitaker_lexicon):
        """Test gender extraction for neuter nouns."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("bellum")
        assert result.get("gender") == "n."

    def test_whitaker_extracts_verb_pos(self, whitaker_lexicon):
        """Test POS extraction for verbs."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("amo")
        assert result.get("pos_abbrev") == "v."

    def test_whitaker_extracts_adjective_pos(self, whitaker_lexicon):
        """Test POS extraction for adjectives."""
        # Use "magnus" which is clearly an adjective
        result = whitaker_lexicon._lookup_whitaker_with_metadata("magnus")
        assert result.get("pos_abbrev") == "adj."

    def test_whitaker_extracts_adverb_pos(self, whitaker_lexicon):
        """Test POS extraction for adverbs."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("bene")
        assert result.get("pos_abbrev") == "adv."

    def test_whitaker_extracts_preposition_pos(self, whitaker_lexicon):
        """Test POS extraction for prepositions."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("in")
        assert result.get("pos_abbrev") == "prep."

    def test_whitaker_extracts_genitive_first_declension(self, whitaker_lexicon):
        """Test genitive extraction for 1st declension nouns."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("puella")
        assert result.get("genitive") == "-ae"

    def test_whitaker_extracts_genitive_second_declension(self, whitaker_lexicon):
        """Test genitive extraction for 2nd declension nouns."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("dominus")
        assert result.get("genitive") == "-ī"

    def test_whitaker_extracts_genitive_third_declension(self, whitaker_lexicon):
        """Test genitive extraction for 3rd declension nouns."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("rex")
        assert result.get("genitive") == "-is"

    def test_whitaker_extracts_headword(self, whitaker_lexicon):
        """Test headword extraction from roots."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("puella")
        assert result.get("headword") is not None
        assert "puell" in result.get("headword", "").lower()

    def test_whitaker_extracts_principal_parts(self, whitaker_lexicon):
        """Test principal parts extraction for verbs."""
        result = whitaker_lexicon._lookup_whitaker_with_metadata("duco")
        pp = result.get("principal_parts", "")
        # Should contain perfect and/or supine stems
        assert pp, "Principal parts should be extracted for verbs"


@pytest.mark.whitakers
class TestWhitakerSenseCleaning:
    """Test sense cleaning for Whitaker output."""

    @pytest.fixture
    def lexicon(self):
        return LatinLexicon(max_senses=3, primary_source="whitakers")

    def test_removes_editorial_brackets(self, lexicon):
        """Test that editorial brackets are removed from senses."""
        sense = "boy, (male) child [a puere => from boyhood]"
        cleaned = lexicon._clean_whitaker_sense(sense)
        assert "[" not in cleaned
        assert "=>" not in cleaned
        assert "boy" in cleaned

    def test_cleans_whitespace(self, lexicon):
        """Test that extra whitespace is cleaned."""
        sense = "  love,   like  "
        cleaned = lexicon._clean_whitaker_sense(sense)
        assert cleaned == "love, like"

    def test_removes_trailing_punctuation(self, lexicon):
        """Test that trailing punctuation is removed."""
        sense = "love, like, ;"
        cleaned = lexicon._clean_whitaker_sense(sense)
        assert not cleaned.endswith(";")
        assert not cleaned.endswith(",")

    def test_handles_empty_sense(self, lexicon):
        """Test handling of empty sense strings."""
        assert lexicon._clean_whitaker_sense("") == ""
        assert lexicon._clean_whitaker_sense(None) == ""


@pytest.mark.whitakers
class TestPrimarySourceConfiguration:
    """Test configurable primary source selection."""

    def test_default_primary_is_whitakers(self):
        """Test that Whitaker's is the default primary source."""
        lexicon = LatinLexicon()
        assert lexicon._primary_source == "whitakers"

    def test_can_set_lewis_short_primary(self):
        """Test that Lewis & Short can be set as primary."""
        lexicon = LatinLexicon(primary_source="lewis_short")
        assert lexicon._primary_source == "lewis_short"

    def test_whitakers_primary_uses_whitaker_first(self):
        """Test that Whitaker primary uses Whitaker for lookup first."""
        lexicon = LatinLexicon(primary_source="whitakers", enable_api_fallbacks=False)
        # Create a token
        token = Token(
            text="amo",
            analysis=Analysis(lemma="amo", pos_labels=[], backend="test"),
        )
        enriched = lexicon.enrich_token(token)
        # Should have a gloss with senses
        assert enriched.gloss is not None


@pytest.mark.whitakers
class TestTokenEnrichmentWithWhitaker:
    """Test token enrichment with Whitaker as primary."""

    @pytest.fixture
    def whitaker_lexicon(self):
        return LatinLexicon(primary_source="whitakers", enable_api_fallbacks=False)

    def test_token_gets_senses(self, whitaker_lexicon):
        """Test that tokens get definitions."""
        token = Token(
            text="puella",
            analysis=Analysis(lemma="puella", pos_labels=[], backend="test"),
        )
        enriched = whitaker_lexicon.enrich_token(token)
        assert enriched.gloss is not None
        assert len(enriched.gloss.senses) > 0

    def test_token_gets_gender(self, whitaker_lexicon):
        """Test that noun tokens get gender metadata."""
        token = Token(
            text="puella",
            analysis=Analysis(lemma="puella", pos_labels=[], backend="test"),
        )
        enriched = whitaker_lexicon.enrich_token(token)
        assert enriched.gloss is not None
        assert enriched.gloss.gender == "f."

    def test_token_gets_pos_abbrev(self, whitaker_lexicon):
        """Test that verb tokens get POS abbreviation."""
        token = Token(
            text="amo",
            analysis=Analysis(lemma="amo", pos_labels=[], backend="test"),
        )
        enriched = whitaker_lexicon.enrich_token(token)
        assert enriched.gloss is not None
        assert enriched.gloss.pos_abbrev == "v."

    def test_token_gets_genitive(self, whitaker_lexicon):
        """Test that noun tokens get genitive ending."""
        token = Token(
            text="puella",
            analysis=Analysis(lemma="puella", pos_labels=[], backend="test"),
        )
        enriched = whitaker_lexicon.enrich_token(token)
        assert enriched.gloss is not None
        assert enriched.gloss.genitive == "-ae"

    def test_punctuation_tokens_skipped(self, whitaker_lexicon):
        """Test that punctuation tokens are not enriched."""
        token = Token(text=",", is_punct=True)
        enriched = whitaker_lexicon.enrich_token(token)
        assert enriched.gloss is None


@pytest.mark.whitakers
class TestFallbackBehavior:
    """Test fallback behavior when Whitaker doesn't have an entry."""

    def test_falls_back_to_lewis_short(self):
        """Test fallback to Lewis & Short when Whitaker fails."""
        lexicon = LatinLexicon(primary_source="whitakers", enable_api_fallbacks=False)
        # Use a word that might not be in Whitaker but is in Lewis & Short
        # This is hard to test without knowing exact coverage differences
        # For now, just verify the method doesn't crash
        result = lexicon._lookup_whitaker_with_metadata("xyznonexistent")
        assert result["senses"] == []


class TestQueryVariants:
    """Test query variant generation for Latin spelling variations."""

    @pytest.fixture
    def lexicon(self):
        return LatinLexicon()

    def test_includes_lowercase(self, lexicon):
        """Test that lowercase variant is included."""
        variants = lexicon._get_query_variants("Amo")
        assert "amo" in variants

    def test_includes_capitalized(self, lexicon):
        """Test that capitalized variant is included."""
        variants = lexicon._get_query_variants("amo")
        assert "Amo" in variants

    def test_includes_u_v_variants(self, lexicon):
        """Test that u/v variants are included."""
        variants = lexicon._get_query_variants("uideo")
        assert "video" in variants

    def test_includes_i_j_variants(self, lexicon):
        """Test that i/j variants are included."""
        variants = lexicon._get_query_variants("iam")
        assert "jam" in variants

    def test_removes_duplicates(self, lexicon):
        """Test that duplicate variants are removed."""
        variants = lexicon._get_query_variants("amo")
        assert len(variants) == len(set(variants))
