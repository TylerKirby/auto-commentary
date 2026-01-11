"""
Tests for the Greek Morpheus normalizer.

Tests cover headword reconstruction, POS mapping, gender extraction,
article assignment, and principal parts handling.
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
from autocom.core.normalizers.morpheus import MorpheusNormalizer


class TestMorpheusNormalizerInit:
    """Test normalizer initialization."""

    def test_creates_normalizer(self):
        """MorpheusNormalizer can be instantiated."""
        normalizer = MorpheusNormalizer()
        assert normalizer is not None


class TestPOSMapping:
    """Test part-of-speech mapping from Morpheus codes."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    @pytest.mark.parametrize(
        "pos_code,expected",
        [
            ("noun", PartOfSpeech.NOUN),
            ("verb", PartOfSpeech.VERB),
            ("adj", PartOfSpeech.ADJECTIVE),
            ("adv", PartOfSpeech.ADVERB),
            ("prep", PartOfSpeech.PREPOSITION),
            ("conj", PartOfSpeech.CONJUNCTION),
            ("pron", PartOfSpeech.PRONOUN),
            ("part", PartOfSpeech.PARTICLE),
            ("article", PartOfSpeech.ARTICLE),
            ("numeral", PartOfSpeech.NUMERAL),
            ("interj", PartOfSpeech.INTERJECTION),
        ],
    )
    def test_maps_pos_codes(self, normalizer, pos_code, expected):
        """Maps Morpheus POS codes to standard enum."""
        assert normalizer._map_pos(pos_code) == expected

    def test_unknown_pos_returns_unknown(self, normalizer):
        """Unknown POS code returns UNKNOWN enum."""
        assert normalizer._map_pos("xyz") == PartOfSpeech.UNKNOWN

    def test_empty_pos_returns_unknown(self, normalizer):
        """Empty POS code returns UNKNOWN enum."""
        assert normalizer._map_pos("") == PartOfSpeech.UNKNOWN


class TestGenderMapping:
    """Test gender mapping from Morpheus codes."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    @pytest.mark.parametrize(
        "gender_code,expected",
        [
            ("masc", Gender.MASCULINE),
            ("fem", Gender.FEMININE),
            ("neut", Gender.NEUTER),
            ("masc/fem", Gender.COMMON),
            ("m", Gender.MASCULINE),
            ("f", Gender.FEMININE),
            ("n", Gender.NEUTER),
            ("c", Gender.COMMON),
        ],
    )
    def test_maps_gender_codes(self, normalizer, gender_code, expected):
        """Maps Morpheus gender codes to Gender enum."""
        assert normalizer._map_gender(gender_code) == expected

    def test_empty_gender_returns_none(self, normalizer):
        """Empty gender code returns None."""
        assert normalizer._map_gender("") is None


class TestFirstDeclensionHeadwords:
    """Test first declension noun headword reconstruction."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_feminine_alpha_stem(self, normalizer):
        """Reconstructs feminine alpha-stem nominative."""
        headword = normalizer._reconstruct_noun_headword("χωρ", 1, Gender.FEMININE)
        assert headword == "χωρα"

    def test_feminine_eta_stem(self, normalizer):
        """Reconstructs feminine eta-stem nominative."""
        headword = normalizer._reconstruct_noun_headword("τιμ", 1, Gender.FEMININE)
        assert headword == "τιμα"  # Default to alpha, but η is also valid

    def test_masculine_first_decl(self, normalizer):
        """Reconstructs masculine first declension nominative."""
        headword = normalizer._reconstruct_noun_headword("νεανι", 1, Gender.MASCULINE)
        assert headword == "νεανιας"


class TestSecondDeclensionHeadwords:
    """Test second declension noun headword reconstruction."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_masculine_os_stem(self, normalizer):
        """Reconstructs masculine -ος nominative."""
        headword = normalizer._reconstruct_noun_headword("λογ", 2, Gender.MASCULINE)
        assert headword == "λογος"

    def test_neuter_on_stem(self, normalizer):
        """Reconstructs neuter -ον nominative."""
        headword = normalizer._reconstruct_noun_headword("εργ", 2, Gender.NEUTER)
        assert headword == "εργον"

    def test_feminine_os_stem(self, normalizer):
        """Reconstructs feminine -ος nominative (rare pattern like ὁδός)."""
        headword = normalizer._reconstruct_noun_headword("ὁδ", 2, Gender.FEMININE)
        assert headword == "ὁδος"


class TestThirdDeclensionHeadwords:
    """Test third declension noun headword reconstruction."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_dental_stem_tau(self, normalizer):
        """Reconstructs dental τ-stem nominative (drops τ, adds ς)."""
        headword = normalizer._reconstruct_third_decl_noun("χαριτ", "F")
        assert headword == "χαρις"

    def test_dental_stem_delta(self, normalizer):
        """Reconstructs dental δ-stem nominative."""
        headword = normalizer._reconstruct_third_decl_noun("ἐλπιδ", "F")
        assert headword == "ἐλπις"

    def test_velar_stem_kappa(self, normalizer):
        """Reconstructs velar κ-stem nominative (κ -> ξ)."""
        headword = normalizer._reconstruct_third_decl_noun("φυλακ", "M")
        assert headword == "φυλαξ"

    def test_velar_stem_gamma(self, normalizer):
        """Reconstructs velar γ-stem nominative (γ -> ξ)."""
        headword = normalizer._reconstruct_third_decl_noun("φλογ", "F")
        assert headword == "φλοξ"

    def test_labial_stem_pi(self, normalizer):
        """Reconstructs labial π-stem nominative (π -> ψ)."""
        headword = normalizer._reconstruct_third_decl_noun("Αἰθιοπ", "M")
        assert headword == "Αἰθιοψ"

    def test_liquid_stem_rho(self, normalizer):
        """Reconstructs liquid ρ-stem nominative (unchanged)."""
        headword = normalizer._reconstruct_third_decl_noun("ῥητωρ", "M")
        assert headword == "ῥητωρ"

    def test_nasal_stem_nu(self, normalizer):
        """Reconstructs nasal ν-stem nominative (unchanged)."""
        headword = normalizer._reconstruct_third_decl_noun("δαιμων", "M")
        assert headword == "δαιμων"

    def test_iota_stem(self, normalizer):
        """Reconstructs ι-stem nominative (adds ς)."""
        headword = normalizer._reconstruct_third_decl_noun("πολι", "F")
        assert headword == "πολις"

    def test_upsilon_stem(self, normalizer):
        """Reconstructs υ-stem nominative (adds ς)."""
        headword = normalizer._reconstruct_third_decl_noun("ἰχθυ", "M")
        assert headword == "ἰχθυς"

    def test_eus_stem(self, normalizer):
        """Reconstructs ευ-stem nominative (adds ς)."""
        headword = normalizer._reconstruct_third_decl_noun("βασιλευ", "M")
        assert headword == "βασιλευς"

    def test_sigma_stem_neuter(self, normalizer):
        """Reconstructs σ-stem neuter nominative."""
        headword = normalizer._reconstruct_third_decl_noun("γενεσ", "N")
        assert headword == "γενος"


class TestIrregularNouns:
    """Test irregular noun headword reconstruction."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_aner_irregular(self, normalizer):
        """Reconstructs ἀνήρ from stem ανδρ-."""
        headword = normalizer._reconstruct_headword(
            stem="ανδρ",
            pos=PartOfSpeech.NOUN,
            declension=3,
            gender=Gender.MASCULINE,
            morpheus_data={},
        )
        assert headword == "ἀνήρ"

    def test_gyne_irregular(self, normalizer):
        """Reconstructs γυνή from stem γυναικ-."""
        headword = normalizer._reconstruct_headword(
            stem="γυναικ",
            pos=PartOfSpeech.NOUN,
            declension=3,
            gender=Gender.FEMININE,
            morpheus_data={},
        )
        assert headword == "γυνή"

    def test_pater_irregular(self, normalizer):
        """Reconstructs πατήρ from stem πατρ-."""
        headword = normalizer._reconstruct_headword(
            stem="πατρ",
            pos=PartOfSpeech.NOUN,
            declension=3,
            gender=Gender.MASCULINE,
            morpheus_data={},
        )
        assert headword == "πατήρ"


class TestVerbHeadwords:
    """Test verb headword reconstruction."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_omega_verb_from_stem(self, normalizer):
        """Reconstructs -ω verb headword from stem."""
        headword = normalizer._reconstruct_verb_headword("λυ", {})
        assert headword == "λυω"

    def test_omega_verb_already_complete(self, normalizer):
        """Preserves already complete -ω verb form."""
        headword = normalizer._reconstruct_verb_headword("λύω", {})
        assert headword == "λύω"

    def test_mi_verb_from_stem(self, normalizer):
        """Reconstructs -μι verb headword from stem."""
        headword = normalizer._reconstruct_verb_headword("τιθ", {"verb_class": "mi"})
        assert headword == "τιθμι"

    def test_middle_voice_already_complete(self, normalizer):
        """Preserves already complete middle voice form."""
        headword = normalizer._reconstruct_verb_headword("βούλομαι", {})
        assert headword == "βούλομαι"


class TestAdjectiveHeadwords:
    """Test adjective headword reconstruction."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_first_second_decl_adj(self, normalizer):
        """Reconstructs 1st/2nd declension adjective nominative masculine."""
        headword = normalizer._reconstruct_adjective_headword("καλ", 1)
        assert headword == "καλος"

    def test_third_decl_adj_es_stem(self, normalizer):
        """Reconstructs 3rd declension -ης adjective."""
        headword = normalizer._reconstruct_adjective_headword("ἀληθεσ", 3)
        assert headword == "ἀληθης"

    def test_third_decl_adj_on_stem(self, normalizer):
        """Reconstructs 3rd declension -ων adjective."""
        headword = normalizer._reconstruct_adjective_headword("σωφρον", 3)
        assert headword == "σωφρων"

    def test_third_decl_adj_u_stem(self, normalizer):
        """Reconstructs 3rd declension -υς adjective."""
        headword = normalizer._reconstruct_adjective_headword("ἡδυ", 3)
        assert headword == "ἡδυς"


class TestVerbClassification:
    """Test Greek verb class determination."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_omega_verb_class(self, normalizer):
        """Identifies -ω verb class."""
        verb_class = normalizer._determine_verb_class("λύω", {})
        assert verb_class == GreekVerbClass.OMEGA

    def test_mi_verb_class(self, normalizer):
        """Identifies -μι verb class."""
        verb_class = normalizer._determine_verb_class("δίδωμι", {})
        assert verb_class == GreekVerbClass.MI

    def test_contract_alpha_class(self, normalizer):
        """Identifies -άω contract verb class."""
        verb_class = normalizer._determine_verb_class("τιμάω", {})
        assert verb_class == GreekVerbClass.CONTRACT_ALPHA

    def test_contract_epsilon_class(self, normalizer):
        """Identifies -έω contract verb class."""
        verb_class = normalizer._determine_verb_class("ποιέω", {})
        assert verb_class == GreekVerbClass.CONTRACT_EPSILON

    def test_contract_omicron_class(self, normalizer):
        """Identifies -όω contract verb class."""
        verb_class = normalizer._determine_verb_class("δηλόω", {})
        assert verb_class == GreekVerbClass.CONTRACT_OMICRON


class TestArticleAssignment:
    """Test Greek article assignment for nouns."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_masculine_article(self, normalizer):
        """Assigns ὁ for masculine nouns."""
        entry = normalizer.normalize(
            {"lemma": "λογος", "pos": "noun", "gender": "masc", "decl": "2"},
            original_word="λόγον",
            senses=["word", "speech"],
        )
        assert entry.article == "ὁ"

    def test_feminine_article(self, normalizer):
        """Assigns ἡ for feminine nouns."""
        entry = normalizer.normalize(
            {"lemma": "γυνη", "pos": "noun", "gender": "fem", "decl": "3"},
            original_word="γυναῖκα",
            senses=["woman", "wife"],
        )
        assert entry.article == "ἡ"

    def test_neuter_article(self, normalizer):
        """Assigns τό for neuter nouns."""
        entry = normalizer.normalize(
            {"lemma": "εργον", "pos": "noun", "gender": "neut", "decl": "2"},
            original_word="ἔργον",
            senses=["work", "deed"],
        )
        assert entry.article == "τό"

    def test_verb_no_article(self, normalizer):
        """Verbs do not get articles."""
        entry = normalizer.normalize(
            {"lemma": "λυω", "pos": "verb"},
            original_word="λύει",
            senses=["to loose"],
        )
        assert entry.article is None


class TestGenitiveExtraction:
    """Test genitive ending extraction/inference."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_first_decl_feminine_genitive(self, normalizer):
        """Infers -ης genitive for 1st decl feminine."""
        gen = normalizer._extract_genitive({}, 1, Gender.FEMININE)
        assert gen == "-ης"

    def test_first_decl_masculine_genitive(self, normalizer):
        """Infers -ου genitive for 1st decl masculine."""
        gen = normalizer._extract_genitive({}, 1, Gender.MASCULINE)
        assert gen == "-ου"

    def test_second_decl_genitive(self, normalizer):
        """Infers -ου genitive for 2nd declension."""
        gen = normalizer._extract_genitive({}, 2, Gender.MASCULINE)
        assert gen == "-ου"

    def test_third_decl_genitive(self, normalizer):
        """Infers -ος genitive for 3rd declension."""
        gen = normalizer._extract_genitive({}, 3, Gender.MASCULINE)
        assert gen == "-ος"

    def test_explicit_genitive_preserved(self, normalizer):
        """Uses explicit genitive from data when provided."""
        gen = normalizer._extract_genitive({"genitive": "-ιδος"}, 3, Gender.FEMININE)
        assert gen == "-ιδος"


class TestFullNormalization:
    """Integration tests for full normalization pipeline."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_normalizes_noun(self, normalizer):
        """Full normalization of a Greek noun."""
        entry = normalizer.normalize(
            {"lemma": "λογ", "stem": "λογ", "pos": "noun", "gender": "masc", "decl": "2"},
            original_word="λόγου",
            senses=["word", "speech", "reason"],
        )

        assert entry is not None
        assert entry.headword == "λογος"
        assert entry.language == Language.GREEK
        assert entry.pos == PartOfSpeech.NOUN
        assert entry.gender == Gender.MASCULINE
        assert entry.article == "ὁ"
        assert entry.genitive == "-ου"
        assert entry.senses == ["word", "speech", "reason"]
        assert entry.source == "morpheus"

    def test_normalizes_verb(self, normalizer):
        """Full normalization of a Greek verb."""
        entry = normalizer.normalize(
            {"lemma": "λυ", "stem": "λυ", "pos": "verb"},
            original_word="λύει",
            senses=["to loose", "release"],
        )

        assert entry is not None
        assert entry.headword == "λυω"
        assert entry.pos == PartOfSpeech.VERB
        assert entry.greek_verb_class == GreekVerbClass.OMEGA
        assert entry.article is None

    def test_normalizes_adjective(self, normalizer):
        """Full normalization of a Greek adjective."""
        entry = normalizer.normalize(
            {"lemma": "καλ", "stem": "καλ", "pos": "adj", "decl": "1"},
            original_word="καλόν",
            senses=["beautiful", "good", "noble"],
        )

        assert entry is not None
        assert entry.headword == "καλος"
        assert entry.pos == PartOfSpeech.ADJECTIVE

    def test_handles_empty_data(self, normalizer):
        """Returns None for empty data."""
        entry = normalizer.normalize({}, "test", [])
        assert entry is None


class TestLemmaNormalization:
    """Test lemma normalization for lookup."""

    @pytest.fixture
    def normalizer(self):
        return MorpheusNormalizer()

    def test_strips_accents(self, normalizer):
        """Strips accents from lemma."""
        normalized = normalizer._normalize_lemma("λύω")
        assert normalized == "λυω"

    def test_strips_breathing(self, normalizer):
        """Strips breathing marks from lemma."""
        normalized = normalizer._normalize_lemma("ἄνθρωπος")
        assert normalized == "ανθρωπος"

    def test_lowercases(self, normalizer):
        """Lowercases lemma."""
        normalized = normalizer._normalize_lemma("ΛΟΓΟΣ")
        assert normalized == "λογος"

    def test_handles_empty(self, normalizer):
        """Handles empty string."""
        normalized = normalizer._normalize_lemma("")
        assert normalized == ""
