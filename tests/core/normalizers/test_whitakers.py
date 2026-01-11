"""Tests for Whitaker's Words normalizer."""

from unittest.mock import MagicMock

import pytest

from autocom.core.lexical import (
    Gender,
    Language,
    LatinPrincipalParts,
    LatinStemType,
    Number,
    PartOfSpeech,
    VerbVoice,
)
from autocom.core.normalizers.whitakers import WhitakersNormalizer


class TestPOSMapping:
    """Test part of speech mapping."""

    def test_all_whitaker_codes_mapped(self):
        """All known Whitaker's POS codes have mappings."""
        normalizer = WhitakersNormalizer()

        known_codes = ["N", "V", "ADJ", "ADV", "PREP", "CONJ", "PRON", "INTERJ", "NUM", "VPAR", "SUPINE", "PACK"]

        for code in known_codes:
            assert code in normalizer.POS_MAP

    def test_noun_maps_correctly(self):
        """N maps to NOUN."""
        assert WhitakersNormalizer.POS_MAP["N"] == PartOfSpeech.NOUN

    def test_verb_maps_correctly(self):
        """V maps to VERB."""
        assert WhitakersNormalizer.POS_MAP["V"] == PartOfSpeech.VERB

    def test_adjective_maps_correctly(self):
        """ADJ maps to ADJECTIVE."""
        assert WhitakersNormalizer.POS_MAP["ADJ"] == PartOfSpeech.ADJECTIVE

    def test_vpar_maps_to_verb(self):
        """VPAR (verbal participle) maps to VERB."""
        assert WhitakersNormalizer.POS_MAP["VPAR"] == PartOfSpeech.VERB


class TestGenderMapping:
    """Test gender mapping."""

    def test_all_gender_codes_mapped(self):
        """All Whitaker's gender codes have mappings."""
        normalizer = WhitakersNormalizer()

        known_codes = ["M", "F", "N", "C", "X"]

        for code in known_codes:
            assert code in normalizer.GENDER_MAP

    def test_masculine_maps_correctly(self):
        """M maps to MASCULINE."""
        assert WhitakersNormalizer.GENDER_MAP["M"] == Gender.MASCULINE

    def test_feminine_maps_correctly(self):
        """F maps to FEMININE."""
        assert WhitakersNormalizer.GENDER_MAP["F"] == Gender.FEMININE

    def test_neuter_maps_correctly(self):
        """N maps to NEUTER."""
        assert WhitakersNormalizer.GENDER_MAP["N"] == Gender.NEUTER

    def test_common_maps_correctly(self):
        """C maps to COMMON."""
        assert WhitakersNormalizer.GENDER_MAP["C"] == Gender.COMMON


class TestHeadwordReconstruction:
    """Test headword reconstruction for different word types."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    # Verb tests
    def test_verb_first_conjugation(self, normalizer):
        """First conjugation verb: stem + o."""
        result = normalizer._reconstruct_headword(
            stem="am",
            word_type="V",
            declension=1,
            gender_code=None,
            roots=["am"],
        )
        assert result == "amo"

    def test_verb_second_conjugation(self, normalizer):
        """Second conjugation verb: stem + eo."""
        result = normalizer._reconstruct_headword(
            stem="mon",
            word_type="V",
            declension=2,
            gender_code=None,
            roots=["mon"],
        )
        assert result == "moneo"

    def test_verb_third_conjugation(self, normalizer):
        """Third conjugation verb: stem + o."""
        result = normalizer._reconstruct_headword(
            stem="ag",
            word_type="V",
            declension=3,
            gender_code=None,
            roots=["ag"],
        )
        assert result == "ago"

    def test_verb_fourth_conjugation(self, normalizer):
        """Fourth conjugation verb: stem + io."""
        result = normalizer._reconstruct_headword(
            stem="aud",
            word_type="V",
            declension=4,
            gender_code=None,
            roots=["aud"],
        )
        assert result == "audio"

    # Noun tests
    def test_noun_first_declension_feminine(self, normalizer):
        """First declension feminine: stem + a."""
        result = normalizer._reconstruct_headword(
            stem="terr",
            word_type="N",
            declension=1,
            gender_code="F",
            roots=["terr"],
        )
        assert result == "terra"

    def test_noun_first_declension_masculine(self, normalizer):
        """First declension masculine (agricola): stem + a."""
        result = normalizer._reconstruct_headword(
            stem="agricol",
            word_type="N",
            declension=1,
            gender_code="M",
            roots=["agricol"],
        )
        assert result == "agricola"

    def test_noun_second_declension_masculine(self, normalizer):
        """Second declension masculine: stem + us."""
        result = normalizer._reconstruct_headword(
            stem="domin",
            word_type="N",
            declension=2,
            gender_code="M",
            roots=["domin"],
        )
        assert result == "dominus"

    def test_noun_second_declension_neuter(self, normalizer):
        """Second declension neuter: stem + um."""
        result = normalizer._reconstruct_headword(
            stem="bell",
            word_type="N",
            declension=2,
            gender_code="N",
            roots=["bell"],
        )
        assert result == "bellum"

    def test_noun_fourth_declension_masculine(self, normalizer):
        """Fourth declension masculine: stem + us."""
        result = normalizer._reconstruct_headword(
            stem="man",
            word_type="N",
            declension=4,
            gender_code="M",
            roots=["man"],
        )
        assert result == "manus"

    def test_noun_fourth_declension_neuter(self, normalizer):
        """Fourth declension neuter: stem + u."""
        result = normalizer._reconstruct_headword(
            stem="corn",
            word_type="N",
            declension=4,
            gender_code="N",
            roots=["corn"],
        )
        assert result == "cornu"

    def test_noun_fifth_declension(self, normalizer):
        """Fifth declension: stem + es."""
        result = normalizer._reconstruct_headword(
            stem="r",
            word_type="N",
            declension=5,
            gender_code="F",
            roots=["r"],
        )
        assert result == "res"

    # Third declension tests (complex)
    def test_noun_third_declension_velar_stem(self, normalizer):
        """Third declension with velar stem: stem ending in c/g -> x."""
        result = normalizer._reconstruct_third_decl_noun("reg", "M")
        assert result == "rex"

    def test_noun_third_declension_dental_stem(self, normalizer):
        """Third declension with dental stem: stem ending in t/d -> s."""
        # Using ped -> pes (regular pattern). Note: milit -> miles involves
        # irregular ablaut (i->e) that can't be predicted from stem alone.
        result = normalizer._reconstruct_third_decl_noun("ped", "M")
        assert result == "pes"

    def test_noun_third_declension_or_stem(self, normalizer):
        """Third declension with -or stem: unchanged."""
        result = normalizer._reconstruct_third_decl_noun("orator", "M")
        assert result == "orator"

    # Adjective tests
    def test_adjective_first_second_declension(self, normalizer):
        """1st/2nd declension adjective: stem + us."""
        result = normalizer._reconstruct_headword(
            stem="bon",
            word_type="ADJ",
            declension=1,
            gender_code="M",
            roots=["bon"],
        )
        assert result == "bonus"

    def test_adjective_third_declension(self, normalizer):
        """3rd declension adjective: stem + is."""
        result = normalizer._reconstruct_headword(
            stem="fort",
            word_type="ADJ",
            declension=3,
            gender_code="M",
            roots=["fort"],
        )
        assert result == "fortis"

    # Pronoun tests
    def test_pronoun_ille(self, normalizer):
        """Pronoun ille from stem ill."""
        result = normalizer._reconstruct_headword(
            stem="ill",
            word_type="PRON",
            declension=None,
            gender_code="M",
            roots=["ill"],
        )
        assert result == "ille"

    def test_pronoun_hic(self, normalizer):
        """Pronoun hic from stem hic."""
        result = normalizer._reconstruct_headword(
            stem="hic",
            word_type="PRON",
            declension=None,
            gender_code="M",
            roots=["hic"],
        )
        assert result == "hic"

    def test_pronoun_ipse(self, normalizer):
        """Pronoun ipse from stem ips."""
        result = normalizer._reconstruct_headword(
            stem="ips",
            word_type="PRON",
            declension=None,
            gender_code="M",
            roots=["ips"],
        )
        assert result == "ipse"

    def test_pronoun_qui(self, normalizer):
        """Pronoun qui from stem qu."""
        result = normalizer._reconstruct_headword(
            stem="qu",
            word_type="PRON",
            declension=None,
            gender_code="M",
            roots=["qu"],
        )
        assert result == "qui"


class TestSenseCleaning:
    """Test sense cleaning."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    def test_removes_editorial_brackets(self, normalizer):
        """Editorial brackets are removed."""
        result = normalizer._clean_sense("boy, (male) child [a puere => from boyhood]")
        assert "[" not in result
        assert "puere" not in result
        assert "boy" in result

    def test_removes_citation_parentheses(self, normalizer):
        """Citation parentheses are removed."""
        result = normalizer._clean_sense("love, affection (Cic. Off. 1.2)")
        assert "Cic." not in result
        assert "love" in result

    def test_normalizes_whitespace(self, normalizer):
        """Excessive whitespace is normalized."""
        result = normalizer._clean_sense("love,   affection,    desire")
        assert "  " not in result

    def test_strips_trailing_punctuation(self, normalizer):
        """Trailing punctuation is stripped."""
        result = normalizer._clean_sense("love, affection;")
        assert not result.endswith(";")

    def test_handles_empty_input(self, normalizer):
        """Empty input returns empty string."""
        result = normalizer._clean_sense("")
        assert result == ""

    def test_preserves_valid_content(self, normalizer):
        """Valid content is preserved."""
        result = normalizer._clean_sense("love, affection")
        assert result == "love, affection"


class TestPrincipalPartsExtraction:
    """Test verb principal parts extraction."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    def test_builds_principal_parts_from_roots(self, normalizer):
        """Principal parts are built from Whitaker's roots."""
        # Whitaker's returns: [present_stem, inf_stem, perfect_stem, supine_stem]
        roots = ["am", "am", "amav", "amat"]

        pp = normalizer._build_principal_parts(roots, conjugation=1, headword="amo")

        assert pp is not None
        assert pp.present == "amo"
        assert "āre" in pp.infinitive  # amāre
        assert pp.perfect == "amavī"
        assert pp.supine == "amatum"

    def test_handles_missing_perfect(self, normalizer):
        """Handles verbs without perfect stem."""
        roots = ["am", "am"]

        pp = normalizer._build_principal_parts(roots, conjugation=1, headword="amo")

        assert pp is not None
        assert pp.perfect is None

    def test_builds_correct_infinitive_by_conjugation(self, normalizer):
        """Infinitive ending matches conjugation."""
        # 1st conjugation: -āre
        pp1 = normalizer._build_principal_parts(["am", "am", "amav", "amat"], 1, "amo")
        assert "āre" in pp1.infinitive

        # 2nd conjugation: -ēre
        pp2 = normalizer._build_principal_parts(["mon", "mon", "monu", "monit"], 2, "moneo")
        assert "ēre" in pp2.infinitive

        # 3rd conjugation: -ere
        pp3 = normalizer._build_principal_parts(["ag", "ag", "eg", "act"], 3, "ago")
        assert "ere" in pp3.infinitive

        # 4th conjugation: -īre
        pp4 = normalizer._build_principal_parts(["aud", "aud", "audiv", "audit"], 4, "audio")
        assert "īre" in pp4.infinitive


class TestNormalizeLexeme:
    """Test normalizing from Whitaker's lexeme objects."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    def test_normalizes_noun_lexeme(self, normalizer):
        """Normalizes a noun lexeme correctly."""
        # Mock a Whitaker's lexeme object
        lexeme = MagicMock()
        lexeme.wordType = MagicMock(name="N")
        lexeme.wordType.name = "N"
        lexeme.senses = ["girl", "maiden"]
        lexeme.roots = ["puell"]
        lexeme.category = [1]  # 1st declension
        lexeme.form = ["F"]  # Feminine

        entry = normalizer.normalize_lexeme(lexeme, original_word="puella")

        assert entry is not None
        assert entry.headword == "puella"
        assert entry.pos == PartOfSpeech.NOUN
        assert entry.gender == Gender.FEMININE
        assert entry.declension == 1
        assert entry.genitive == "-ae"
        assert "girl" in entry.senses

    def test_normalizes_verb_lexeme(self, normalizer):
        """Normalizes a verb lexeme correctly."""
        lexeme = MagicMock()
        lexeme.wordType = MagicMock(name="V")
        lexeme.wordType.name = "V"
        lexeme.senses = ["to love", "to be fond of"]
        lexeme.roots = ["am", "am", "amav", "amat"]
        lexeme.category = [1]  # 1st conjugation
        lexeme.form = []

        entry = normalizer.normalize_lexeme(lexeme, original_word="amat")

        assert entry is not None
        assert entry.headword == "amo"
        assert entry.pos == PartOfSpeech.VERB
        assert entry.conjugation == 1
        assert entry.latin_principal_parts is not None
        assert entry.latin_principal_parts.present == "amo"

    def test_normalizes_adjective_lexeme(self, normalizer):
        """Normalizes an adjective lexeme correctly."""
        lexeme = MagicMock()
        lexeme.wordType = MagicMock(name="ADJ")
        lexeme.wordType.name = "ADJ"
        lexeme.senses = ["much", "many", "great"]
        lexeme.roots = ["mult"]
        lexeme.category = [1]  # 1st/2nd declension
        lexeme.form = ["M"]  # Masculine

        entry = normalizer.normalize_lexeme(lexeme, original_word="multum")

        assert entry is not None
        assert entry.headword == "multus"
        assert entry.pos == PartOfSpeech.ADJECTIVE

    def test_normalizes_pronoun_lexeme(self, normalizer):
        """Normalizes a pronoun lexeme correctly."""
        lexeme = MagicMock()
        lexeme.wordType = MagicMock(name="PRON")
        lexeme.wordType.name = "PRON"
        lexeme.senses = ["that", "he", "she"]
        lexeme.roots = ["ill"]
        lexeme.category = []
        lexeme.form = ["M"]

        entry = normalizer.normalize_lexeme(lexeme, original_word="ille")

        assert entry is not None
        assert entry.headword == "ille"
        assert entry.pos == PartOfSpeech.PRONOUN

    def test_returns_none_for_none_lexeme(self, normalizer):
        """Returns None for None input."""
        entry = normalizer.normalize_lexeme(None)
        assert entry is None

    def test_returns_none_for_empty_senses(self, normalizer):
        """Returns None when lexeme has no senses."""
        lexeme = MagicMock()
        lexeme.wordType = MagicMock(name="N")
        lexeme.wordType.name = "N"
        lexeme.senses = []
        lexeme.roots = ["puell"]
        lexeme.category = [1]
        lexeme.form = ["F"]

        entry = normalizer.normalize_lexeme(lexeme)
        assert entry is None


class TestNormalizeFromMetadata:
    """Test normalizing from pre-extracted metadata dict."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    def test_normalizes_noun_metadata(self, normalizer):
        """Normalizes noun metadata correctly."""
        metadata = {
            "senses": ["girl", "maiden"],
            "headword": "puella",
            "gender": "f.",
            "genitive": "-ae",
        }

        entry = normalizer.normalize_from_metadata(metadata, original_word="puella")

        assert entry is not None
        assert entry.headword == "puella"
        assert entry.pos == PartOfSpeech.NOUN
        assert entry.gender == Gender.FEMININE
        assert entry.declension == 1
        assert entry.genitive == "-ae"

    def test_normalizes_verb_metadata(self, normalizer):
        """Normalizes verb metadata correctly."""
        metadata = {
            "senses": ["to love"],
            "headword": "amo",
            "pos_abbrev": "v.",
            "principal_parts": "amāvī, amātum (1)",
        }

        entry = normalizer.normalize_from_metadata(metadata, original_word="amat")

        assert entry is not None
        assert entry.headword == "amo"
        assert entry.pos == PartOfSpeech.VERB
        assert entry.latin_principal_parts is not None

    def test_returns_none_for_empty_metadata(self, normalizer):
        """Returns None for empty metadata."""
        entry = normalizer.normalize_from_metadata({})
        assert entry is None

    def test_returns_none_for_no_senses(self, normalizer):
        """Returns None when no senses in metadata."""
        metadata = {"headword": "test", "gender": "m."}
        entry = normalizer.normalize_from_metadata(metadata)
        assert entry is None


class TestVoiceDetermination:
    """Test verb voice determination."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    def test_detects_deponent_from_senses(self, normalizer):
        """Detects deponent verbs from sense text."""
        senses = ["to follow, pursue (dep.)"]
        voice = normalizer._determine_voice([], senses)
        assert voice == VerbVoice.DEPONENT

    def test_detects_semideponent_from_senses(self, normalizer):
        """Detects semi-deponent verbs from sense text."""
        senses = ["to dare (semi-dep.)"]
        voice = normalizer._determine_voice([], senses)
        assert voice == VerbVoice.SEMI_DEPONENT

    def test_defaults_to_active(self, normalizer):
        """Defaults to active voice when no indicators."""
        senses = ["to love", "to be fond of"]
        voice = normalizer._determine_voice([], senses)
        assert voice == VerbVoice.ACTIVE


class TestPluralTantumDetection:
    """Test detection of pluralia tantum nouns."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    def test_detects_arma(self, normalizer):
        """Detects arma as plural tantum."""
        assert normalizer._is_plural_tantum("arm", 2, "N") is True

    def test_detects_castra(self, normalizer):
        """Detects castra as plural tantum."""
        assert normalizer._is_plural_tantum("castr", 2, "N") is True

    def test_regular_noun_not_plural_tantum(self, normalizer):
        """Regular nouns are not plural tantum."""
        assert normalizer._is_plural_tantum("puell", 1, "F") is False


class TestLemmaNormalization:
    """Test lemma normalization."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    def test_lowercases_lemma(self, normalizer):
        """Lemma is lowercased."""
        result = normalizer._normalize_lemma("PUELLA")
        assert result == "puella"

    def test_removes_macrons(self, normalizer):
        """Macrons are removed from lemma."""
        result = normalizer._normalize_lemma("amō")
        assert result == "amo"

    def test_handles_empty_input(self, normalizer):
        """Empty input returns empty string."""
        result = normalizer._normalize_lemma("")
        assert result == ""


class TestEntryIntegration:
    """Integration tests for complete entry creation."""

    @pytest.fixture
    def normalizer(self):
        return WhitakersNormalizer()

    def test_creates_valid_entry_with_all_fields(self, normalizer):
        """Creates a complete valid NormalizedLexicalEntry."""
        lexeme = MagicMock()
        lexeme.wordType = MagicMock(name="N")
        lexeme.wordType.name = "N"
        lexeme.senses = ["girl", "maiden", "young woman"]
        lexeme.roots = ["puell"]
        lexeme.category = [1]
        lexeme.form = ["F"]

        entry = normalizer.normalize_lexeme(lexeme, original_word="puella")

        # Verify all expected fields
        assert entry.headword == "puella"
        assert entry.lemma == "puella"
        assert entry.language == Language.LATIN
        assert entry.pos == PartOfSpeech.NOUN
        assert entry.gender == Gender.FEMININE
        assert entry.declension == 1
        assert entry.genitive == "-ae"
        assert entry.source == "whitakers"
        assert entry.confidence == 1.0
        assert len(entry.senses) == 3

    def test_entry_serializes_to_json(self, normalizer):
        """Entry can be serialized to JSON."""
        lexeme = MagicMock()
        lexeme.wordType = MagicMock(name="N")
        lexeme.wordType.name = "N"
        lexeme.senses = ["girl"]
        lexeme.roots = ["puell"]
        lexeme.category = [1]
        lexeme.form = ["F"]

        entry = normalizer.normalize_lexeme(lexeme)

        # Should not raise
        json_str = entry.model_dump_json()
        assert "puella" in json_str
        assert "latin" in json_str
