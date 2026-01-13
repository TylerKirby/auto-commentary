"""
Integration tests for Greek lexicon pipeline.

Tests the full lookup, normalization, and gloss creation pipeline
for various Greek word types.
"""

import pytest

from autocom.core.lexical import Gender, Language, PartOfSpeech
from autocom.core.models import Gloss, Token, Analysis
from autocom.languages.greek.lexicon import GreekLexicon


@pytest.fixture
def lexicon():
    """Create a GreekLexicon with caching disabled for isolated tests."""
    return GreekLexicon(enable_cache=False)


class TestGreekLexiconBasicVocabulary:
    """Test basic vocabulary lookups."""

    def test_lookup_thea_goddess(self, lexicon):
        """Looks up θεά (goddess)."""
        entry = lexicon.lookup_normalized("θεά")
        assert entry is not None
        assert entry.pos == PartOfSpeech.NOUN
        assert entry.gender == Gender.FEMININE
        assert "goddess" in entry.senses

    def test_lookup_logos_word(self, lexicon):
        """Looks up λόγος (word)."""
        entry = lexicon.lookup_normalized("λόγος")
        assert entry is not None
        assert entry.pos == PartOfSpeech.NOUN
        assert entry.gender == Gender.MASCULINE

    def test_lookup_tithemi_verb(self, lexicon):
        """Looks up τίθημι (to put)."""
        entry = lexicon.lookup_normalized("τίθημι")
        assert entry is not None
        assert entry.pos == PartOfSpeech.VERB
        assert entry.greek_principal_parts is not None

    def test_lookup_aeido_verb(self, lexicon):
        """Looks up ἀείδω (to sing)."""
        entry = lexicon.lookup_normalized("ἀείδω")
        assert entry is not None
        assert entry.pos == PartOfSpeech.VERB


class TestGreekLexiconArticles:
    """Test article assignment in glosses."""

    def test_masculine_noun_gets_ho(self, lexicon):
        """Masculine noun gets ὁ article."""
        gloss = lexicon.get_gloss("λόγος")
        assert gloss is not None
        assert gloss.article == "ὁ"

    def test_feminine_noun_gets_he(self, lexicon):
        """Feminine noun gets ἡ article."""
        gloss = lexicon.get_gloss("θεά")
        assert gloss is not None
        assert gloss.article == "ἡ"

    def test_neuter_noun_gets_to(self, lexicon):
        """Neuter noun gets τό article."""
        gloss = lexicon.get_gloss("ἄλγος")
        assert gloss is not None
        assert gloss.article == "τό"

    def test_verb_no_article(self, lexicon):
        """Verbs do not get articles."""
        gloss = lexicon.get_gloss("τίθημι")
        assert gloss is not None
        assert gloss.article is None


class TestGreekLexiconGlossCreation:
    """Test Gloss creation from normalized entries."""

    def test_creates_gloss_with_senses(self, lexicon):
        """Creates Gloss with definition senses."""
        gloss = lexicon.get_gloss("μῆνις")
        assert gloss is not None
        assert len(gloss.senses) > 0
        assert gloss.best is not None

    def test_creates_gloss_with_genitive(self, lexicon):
        """Creates Gloss with genitive ending."""
        gloss = lexicon.get_gloss("λόγος")
        assert gloss is not None
        assert gloss.genitive is not None
        assert gloss.genitive.startswith("-")

    def test_creates_gloss_with_principal_parts(self, lexicon):
        """Creates Gloss with principal parts for verbs."""
        gloss = lexicon.get_gloss("τίθημι")
        assert gloss is not None
        assert gloss.principal_parts is not None


class TestGreekLexiconTokenEnrichment:
    """Test token enrichment with Greek glosses."""

    def test_enriches_noun_token(self, lexicon):
        """Enriches a noun token with gloss."""
        token = Token(
            text="θεά",
            analysis=Analysis(lemma="θεά", pos="noun"),
        )
        enriched = lexicon.enrich_token(token)
        assert enriched.gloss is not None
        assert enriched.gloss.article == "ἡ"

    def test_enriches_verb_token(self, lexicon):
        """Enriches a verb token with gloss."""
        token = Token(
            text="τίθησι",
            analysis=Analysis(lemma="τίθημι", pos="verb"),
        )
        enriched = lexicon.enrich_token(token)
        assert enriched.gloss is not None
        assert enriched.gloss.pos_abbrev == "v."

    def test_enriches_with_frequency(self, lexicon):
        """Enriches token with frequency count."""
        token = Token(
            text="καί",
            analysis=Analysis(lemma="καί", pos="conj"),
        )
        enriched = lexicon.enrich_token(token, frequency=42)
        assert enriched.gloss is not None
        assert enriched.gloss.frequency == 42


class TestGreekLexiconAccentNormalization:
    """Test lookup with accent variations."""

    def test_lookup_with_accents(self, lexicon):
        """Looks up word with accents."""
        entry = lexicon.lookup_normalized("θεά")
        assert entry is not None

    def test_lookup_without_accents(self, lexicon):
        """Looks up word without accents."""
        entry = lexicon.lookup_normalized("θεα")
        assert entry is not None

    def test_lookup_with_breathing(self, lexicon):
        """Looks up word with breathing marks."""
        entry = lexicon.lookup_normalized("ἀείδω")
        assert entry is not None


class TestGreekLexiconFallback:
    """Test fallback behavior for unknown words."""

    def test_unknown_word_returns_none(self, lexicon):
        """Returns None for completely unknown word."""
        entry = lexicon.lookup_normalized("xyzabc123")
        assert entry is None

    def test_creates_empty_gloss_for_unknown(self, lexicon):
        """Creates empty gloss for unknown word."""
        token = Token(
            text="xyzabc",
            analysis=Analysis(lemma="xyzabc", pos="unknown"),
        )
        enriched = lexicon.enrich_token(token)
        assert enriched.gloss is not None
        assert enriched.gloss.senses == []


class TestGreekLexiconProperNouns:
    """Test proper noun handling."""

    def test_lookup_achilles(self, lexicon):
        """Looks up Ἀχιλλεύς (Achilles)."""
        entry = lexicon.lookup_normalized("Ἀχιλλεύς")
        assert entry is not None
        assert entry.gender == Gender.MASCULINE

    def test_lookup_hades(self, lexicon):
        """Looks up Ἅιδης (Hades)."""
        entry = lexicon.lookup_normalized("Ἅιδης")
        assert entry is not None


class TestGreekLexiconSourceTracking:
    """Test source tracking in normalized entries."""

    def test_basic_vocab_source_tracked(self, lexicon):
        """Basic vocabulary entries track source."""
        entry = lexicon.lookup_normalized("θεά")
        assert entry is not None
        # Source should be tracked (basic_vocabulary or morpheus)
        assert entry.source is not None
