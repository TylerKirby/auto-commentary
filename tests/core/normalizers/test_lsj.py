"""
Tests for the Greek LSJ (Liddell-Scott-Jones) normalizer.

Tests cover entry parsing, POS mapping, gender extraction, article assignment,
genitive extraction, principal parts, and sense cleaning.
"""

import pytest

from autocom.core.lexical import (
    Gender,
    GreekPrincipalParts,
    GreekVerbClass,
    Language,
    PartOfSpeech,
    VerbVoice,
)
from autocom.core.normalizers.lsj import LSJNormalizer


class TestLSJNormalizerInit:
    """Test normalizer initialization."""

    def test_creates_normalizer(self):
        """LSJNormalizer can be instantiated."""
        normalizer = LSJNormalizer()
        assert normalizer is not None

    def test_default_max_senses(self):
        """Default max_senses is 3."""
        normalizer = LSJNormalizer()
        assert normalizer.max_senses == 3

    def test_custom_max_senses(self):
        """Can set custom max_senses."""
        normalizer = LSJNormalizer(max_senses=5)
        assert normalizer.max_senses == 5


class TestLSJPOSMapping:
    """Test part-of-speech mapping from LSJ entries."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    @pytest.mark.parametrize(
        "pos_code,expected",
        [
            ("noun", PartOfSpeech.NOUN),
            ("verb", PartOfSpeech.VERB),
            ("adj", PartOfSpeech.ADJECTIVE),
            ("adjective", PartOfSpeech.ADJECTIVE),
            ("adv", PartOfSpeech.ADVERB),
            ("adverb", PartOfSpeech.ADVERB),
            ("prep", PartOfSpeech.PREPOSITION),
            ("conj", PartOfSpeech.CONJUNCTION),
            ("pron", PartOfSpeech.PRONOUN),
            ("part", PartOfSpeech.PARTICLE),
            ("article", PartOfSpeech.ARTICLE),
            ("interj", PartOfSpeech.INTERJECTION),
            ("numeral", PartOfSpeech.NUMERAL),
            ("subst", PartOfSpeech.NOUN),
            ("v", PartOfSpeech.VERB),
            ("vb", PartOfSpeech.VERB),
        ],
    )
    def test_maps_pos_codes(self, normalizer, pos_code, expected):
        """Maps LSJ POS codes to standard enum."""
        entry = {"orth": "test", "pos": pos_code, "senses": ["test"]}
        result = normalizer.normalize(entry, "test")
        assert result.pos == expected

    def test_verb_detected_from_ending_omega(self, normalizer):
        """Detects verb from -ω ending."""
        entry = {"orth": "λύω", "senses": ["loose"]}
        result = normalizer.normalize(entry, "λύω")
        assert result.pos == PartOfSpeech.VERB

    def test_verb_detected_from_ending_mi(self, normalizer):
        """Detects verb from -μι ending."""
        entry = {"orth": "δίδωμι", "senses": ["give"]}
        result = normalizer.normalize(entry, "δίδωμι")
        assert result.pos == PartOfSpeech.VERB

    def test_unknown_pos_returns_unknown(self, normalizer):
        """Unknown POS returns UNKNOWN enum."""
        entry = {"orth": "test", "pos": "xyz", "senses": ["test"]}
        result = normalizer.normalize(entry, "test")
        assert result.pos == PartOfSpeech.UNKNOWN


class TestLSJGenderExtraction:
    """Test gender extraction from LSJ entries."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    @pytest.mark.parametrize(
        "gender_code,expected",
        [
            ("m", Gender.MASCULINE),
            ("f", Gender.FEMININE),
            ("n", Gender.NEUTER),
            ("c", Gender.COMMON),
            ("masc", Gender.MASCULINE),
            ("fem", Gender.FEMININE),
            ("neut", Gender.NEUTER),
            ("m/f", Gender.COMMON),
            ("mf", Gender.COMMON),
        ],
    )
    def test_maps_gender_codes(self, normalizer, gender_code, expected):
        """Maps LSJ gender codes to Gender enum."""
        entry = {"orth": "test", "pos": "noun", "gender": gender_code, "senses": ["test"]}
        result = normalizer.normalize(entry, "test")
        assert result.gender == expected

    def test_extracts_gender_from_gram(self, normalizer):
        """Extracts gender from grammatical info."""
        entry = {"orth": "λόγος", "pos": "noun", "gram": "masc.", "senses": ["word"]}
        result = normalizer.normalize(entry, "λόγος")
        assert result.gender == Gender.MASCULINE

    def test_extracts_feminine_from_gram(self, normalizer):
        """Extracts feminine from grammatical info."""
        entry = {"orth": "γυνή", "pos": "noun", "gram": "fem.", "senses": ["woman"]}
        result = normalizer.normalize(entry, "γυνή")
        assert result.gender == Gender.FEMININE

    def test_extracts_neuter_from_gram(self, normalizer):
        """Extracts neuter from grammatical info."""
        entry = {"orth": "ἔργον", "pos": "noun", "gram": "n.", "senses": ["work"]}
        result = normalizer.normalize(entry, "ἔργον")
        assert result.gender == Gender.NEUTER


class TestLSJArticleAssignment:
    """Test Greek article assignment for nouns."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    def test_masculine_article(self, normalizer):
        """Assigns ὁ for masculine nouns."""
        entry = {"orth": "λόγος", "pos": "noun", "gender": "m", "senses": ["word"]}
        result = normalizer.normalize(entry, "λόγος")
        assert result.article == "ὁ"

    def test_feminine_article(self, normalizer):
        """Assigns ἡ for feminine nouns."""
        entry = {"orth": "γυνή", "pos": "noun", "gender": "f", "senses": ["woman"]}
        result = normalizer.normalize(entry, "γυνή")
        assert result.article == "ἡ"

    def test_neuter_article(self, normalizer):
        """Assigns τό for neuter nouns."""
        entry = {"orth": "ἔργον", "pos": "noun", "gender": "n", "senses": ["work"]}
        result = normalizer.normalize(entry, "ἔργον")
        assert result.article == "τό"

    def test_no_article_for_verbs(self, normalizer):
        """Verbs do not get articles."""
        entry = {"orth": "λύω", "pos": "verb", "senses": ["loose"]}
        result = normalizer.normalize(entry, "λύω")
        assert result.article is None

    def test_no_article_for_adjectives(self, normalizer):
        """Adjectives do not get articles."""
        entry = {"orth": "καλός", "pos": "adj", "senses": ["beautiful"]}
        result = normalizer.normalize(entry, "καλός")
        assert result.article is None


class TestLSJGenitiveExtraction:
    """Test genitive ending extraction from LSJ entries."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    def test_extracts_explicit_genitive(self, normalizer):
        """Extracts genitive from explicit field."""
        entry = {"orth": "λόγος", "pos": "noun", "genitive": "ου", "senses": ["word"]}
        result = normalizer.normalize(entry, "λόγος")
        assert result.genitive == "-ου"

    def test_formats_genitive_with_hyphen(self, normalizer):
        """Adds hyphen to genitive if missing."""
        entry = {"orth": "λόγος", "pos": "noun", "gen_ending": "ου", "senses": ["word"]}
        result = normalizer.normalize(entry, "λόγος")
        assert result.genitive == "-ου"

    def test_preserves_hyphen_in_genitive(self, normalizer):
        """Preserves existing hyphen in genitive."""
        entry = {"orth": "λόγος", "pos": "noun", "genitive": "-ου", "senses": ["word"]}
        result = normalizer.normalize(entry, "λόγος")
        assert result.genitive == "-ου"


class TestLSJVerbClassification:
    """Test Greek verb class determination."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    def test_omega_verb_class(self, normalizer):
        """Identifies -ω verb class."""
        entry = {"orth": "λύω", "pos": "verb", "senses": ["loose"]}
        result = normalizer.normalize(entry, "λύω")
        assert result.greek_verb_class == GreekVerbClass.OMEGA

    def test_mi_verb_class(self, normalizer):
        """Identifies -μι verb class."""
        entry = {"orth": "δίδωμι", "pos": "verb", "senses": ["give"]}
        result = normalizer.normalize(entry, "δίδωμι")
        assert result.greek_verb_class == GreekVerbClass.MI

    def test_contract_alpha_class(self, normalizer):
        """Identifies -άω contract verb class."""
        entry = {"orth": "τιμάω", "pos": "verb", "senses": ["honor"]}
        result = normalizer.normalize(entry, "τιμάω")
        assert result.greek_verb_class == GreekVerbClass.CONTRACT_ALPHA

    def test_contract_epsilon_class(self, normalizer):
        """Identifies -έω contract verb class."""
        entry = {"orth": "ποιέω", "pos": "verb", "senses": ["make"]}
        result = normalizer.normalize(entry, "ποιέω")
        assert result.greek_verb_class == GreekVerbClass.CONTRACT_EPSILON

    def test_contract_omicron_class(self, normalizer):
        """Identifies -όω contract verb class."""
        entry = {"orth": "δηλόω", "pos": "verb", "senses": ["show"]}
        result = normalizer.normalize(entry, "δηλόω")
        assert result.greek_verb_class == GreekVerbClass.CONTRACT_OMICRON


class TestLSJVoiceDetermination:
    """Test verb voice determination."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    def test_active_voice_default(self, normalizer):
        """Active voice is default."""
        entry = {"orth": "λύω", "pos": "verb", "senses": ["loose"]}
        result = normalizer.normalize(entry, "λύω")
        assert result.verb_voice == VerbVoice.ACTIVE

    def test_deponent_from_gram(self, normalizer):
        """Detects deponent from grammatical info."""
        entry = {"orth": "ἔρχομαι", "pos": "verb", "gram": "dep.", "senses": ["come"]}
        result = normalizer.normalize(entry, "ἔρχομαι")
        assert result.verb_voice == VerbVoice.DEPONENT

    def test_middle_voice_from_gram(self, normalizer):
        """Detects middle voice from grammatical info."""
        entry = {"orth": "βούλομαι", "pos": "verb", "gram": "mid.", "senses": ["wish"]}
        result = normalizer.normalize(entry, "βούλομαι")
        assert result.verb_voice == VerbVoice.MIDDLE


class TestLSJPrincipalParts:
    """Test Greek principal parts extraction."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    def test_extracts_explicit_principal_parts(self, normalizer):
        """Extracts principal parts from explicit field."""
        entry = {
            "orth": "λύω",
            "pos": "verb",
            "principal_parts": {
                "present": "λύω",
                "future": "λύσω",
                "aorist": "ἔλυσα",
                "perfect_active": "λέλυκα",
            },
            "senses": ["loose"],
        }
        result = normalizer.normalize(entry, "λύω")
        assert result.greek_principal_parts is not None
        assert result.greek_principal_parts.present == "λύω"
        assert result.greek_principal_parts.future == "λύσω"
        assert result.greek_principal_parts.aorist == "ἔλυσα"
        assert result.greek_principal_parts.perfect_active == "λέλυκα"

    def test_parses_principal_parts_from_gram(self, normalizer):
        """Parses principal parts from grammatical info."""
        entry = {
            "orth": "λύω",
            "pos": "verb",
            "gram": "fut. λύσω, aor. ἔλυσα",
            "senses": ["loose"],
        }
        result = normalizer.normalize(entry, "λύω")
        assert result.greek_principal_parts is not None
        assert result.greek_principal_parts.future == "λύσω"
        assert result.greek_principal_parts.aorist == "ἔλυσα"

    def test_default_present_from_headword(self, normalizer):
        """Sets present form from headword if no parts given."""
        entry = {"orth": "λύω", "pos": "verb", "senses": ["loose"]}
        result = normalizer.normalize(entry, "λύω")
        assert result.greek_principal_parts is not None
        assert result.greek_principal_parts.present == "λύω"


class TestLSJSenseCleaning:
    """Test sense cleaning and formatting."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    def test_removes_citations(self, normalizer):
        """Removes author citations from senses."""
        entry = {
            "orth": "λόγος",
            "pos": "noun",
            "senses": ["word, speech, Hom.Il.1.1, Pl.Rep.327a"],
        }
        result = normalizer.normalize(entry, "λόγος")
        # Citations should be removed
        assert "Hom." not in result.senses[0]
        assert "Pl." not in result.senses[0]

    def test_removes_references(self, normalizer):
        """Removes book/line references from senses."""
        entry = {"orth": "λόγος", "pos": "noun", "senses": ["word 1.2.3, speech ib."]}
        result = normalizer.normalize(entry, "λόγος")
        assert "1.2.3" not in result.senses[0]
        assert "ib." not in result.senses[0]

    def test_removes_cross_references(self, normalizer):
        """Removes cross-references from senses."""
        entry = {"orth": "λόγος", "pos": "noun", "senses": ["word, v. sub λέγω, speech"]}
        result = normalizer.normalize(entry, "λόγος")
        assert "v. sub" not in result.senses[0]

    def test_truncates_long_senses(self, normalizer):
        """Truncates very long senses at natural break points."""
        # Long sense with semicolon delimiter for natural break
        # First part must be > 20 chars for truncation to apply
        long_sense = "word, speech, reason, account; " + "additional meaning " * 15
        entry = {"orth": "λόγος", "pos": "noun", "senses": [long_sense]}
        result = normalizer.normalize(entry, "λόγος")
        # Should truncate at semicolon
        assert len(result.senses[0]) <= 200
        assert "word" in result.senses[0]
        assert "additional meaning" not in result.senses[0]

    def test_limits_number_of_senses(self, normalizer):
        """Limits to max_senses."""
        entry = {
            "orth": "λόγος",
            "pos": "noun",
            "senses": ["word", "speech", "reason", "account", "ratio"],
        }
        result = normalizer.normalize(entry, "λόγος")
        assert len(result.senses) == 3  # Default max_senses

    def test_flattens_nested_senses(self, normalizer):
        """Flattens nested sense lists."""
        entry = {"orth": "λόγος", "pos": "noun", "senses": [["word", "speech"], "reason"]}
        result = normalizer.normalize(entry, "λόγος")
        assert "word" in result.senses
        assert "speech" in result.senses
        assert "reason" in result.senses

    def test_handles_sense_objects(self, normalizer):
        """Handles sense objects with text field."""
        entry = {
            "orth": "λόγος",
            "pos": "noun",
            "senses": [{"text": "word"}, {"definition": "speech"}],
        }
        result = normalizer.normalize(entry, "λόγος")
        assert "word" in result.senses
        assert "speech" in result.senses


class TestLSJLemmaNormalization:
    """Test lemma normalization for lookup."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    def test_strips_accents(self, normalizer):
        """Strips accents from lemma."""
        normalized = normalizer._normalize_lemma("λύω")
        assert normalized == "λυω"

    def test_strips_breathing(self, normalizer):
        """Strips breathing marks from lemma."""
        normalized = normalizer._normalize_lemma("ἄνθρωπος")
        assert normalized == "ανθρωπος"

    def test_strips_iota_subscript(self, normalizer):
        """Strips iota subscript from lemma."""
        normalized = normalizer._normalize_lemma("τῷ")
        assert normalized == "τω"

    def test_lowercases(self, normalizer):
        """Lowercases lemma."""
        normalized = normalizer._normalize_lemma("ΛΟΓΟΣ")
        assert normalized == "λογος"

    def test_handles_empty(self, normalizer):
        """Handles empty string."""
        normalized = normalizer._normalize_lemma("")
        assert normalized == ""


class TestLSJFullNormalization:
    """Integration tests for full normalization pipeline."""

    @pytest.fixture
    def normalizer(self):
        return LSJNormalizer()

    def test_normalizes_complete_noun(self, normalizer):
        """Full normalization of a Greek noun."""
        entry = {
            "orth": "λόγος",
            "pos": "noun",
            "gender": "m",
            "genitive": "-ου",
            "declension": 2,
            "senses": ["word", "speech", "reason"],
        }
        result = normalizer.normalize(entry, "λόγος")

        assert result is not None
        assert result.headword == "λόγος"
        assert result.language == Language.GREEK
        assert result.pos == PartOfSpeech.NOUN
        assert result.gender == Gender.MASCULINE
        assert result.article == "ὁ"
        assert result.genitive == "-ου"
        assert result.declension == 2
        assert result.senses == ["word", "speech", "reason"]
        assert result.source == "lsj"

    def test_normalizes_complete_verb(self, normalizer):
        """Full normalization of a Greek verb."""
        entry = {
            "orth": "λύω",
            "pos": "verb",
            "principal_parts": {
                "present": "λύω",
                "future": "λύσω",
                "aorist": "ἔλυσα",
            },
            "senses": ["loose", "release"],
        }
        result = normalizer.normalize(entry, "λύω")

        assert result is not None
        assert result.headword == "λύω"
        assert result.pos == PartOfSpeech.VERB
        assert result.greek_verb_class == GreekVerbClass.OMEGA
        assert result.verb_voice == VerbVoice.ACTIVE
        assert result.greek_principal_parts is not None
        assert result.article is None

    def test_normalizes_adjective(self, normalizer):
        """Full normalization of a Greek adjective."""
        entry = {
            "orth": "καλός",
            "pos": "adj",
            "senses": ["beautiful", "good", "noble"],
        }
        result = normalizer.normalize(entry, "καλός")

        assert result is not None
        assert result.headword == "καλός"
        assert result.pos == PartOfSpeech.ADJECTIVE
        assert result.article is None

    def test_handles_empty_entry(self, normalizer):
        """Returns None for empty entry."""
        result = normalizer.normalize({}, "test")
        assert result is None

    def test_handles_missing_headword(self, normalizer):
        """Returns None for entry without headword."""
        entry = {"pos": "noun", "senses": ["test"]}
        result = normalizer.normalize(entry, "test")
        assert result is None

    def test_alternative_field_names(self, normalizer):
        """Handles alternative field names."""
        entry = {
            "headword": "λόγος",
            "part_of_speech": "noun",
            "definitions": ["word"],
        }
        result = normalizer.normalize(entry, "λόγος")
        assert result is not None
        assert result.headword == "λόγος"
        assert result.senses == ["word"]
