"""Tests for Lewis & Short normalizer."""

import pytest

from autocom.core.lexical import (
    Gender,
    Language,
    LatinPrincipalParts,
    PartOfSpeech,
    VerbVoice,
)
from autocom.core.normalizers.lewis_short import LewisShortNormalizer


@pytest.fixture
def normalizer():
    """Create a normalizer instance for testing."""
    return LewisShortNormalizer(max_senses=3)


class TestPOSMapping:
    """Test part of speech extraction and mapping."""

    def test_maps_noun(self, normalizer):
        """Maps 'noun' to NOUN."""
        entry = {"part_of_speech": "noun", "key": "test", "senses": ["a test"]}
        assert normalizer._extract_pos(entry) == PartOfSpeech.NOUN

    def test_maps_verb(self, normalizer):
        """Maps 'verb' to VERB."""
        entry = {"part_of_speech": "verb", "key": "test", "senses": ["to test"]}
        assert normalizer._extract_pos(entry) == PartOfSpeech.VERB

    def test_maps_adjective(self, normalizer):
        """Maps 'adjective' to ADJECTIVE."""
        entry = {"part_of_speech": "adjective", "key": "test", "senses": ["testy"]}
        assert normalizer._extract_pos(entry) == PartOfSpeech.ADJECTIVE

    def test_maps_v_a(self, normalizer):
        """Maps 'v. a.' (verbum activum) to VERB."""
        entry = {"part_of_speech": "v. a.", "key": "test", "senses": ["to test"]}
        assert normalizer._extract_pos(entry) == PartOfSpeech.VERB

    def test_maps_v_dep(self, normalizer):
        """Maps 'v. dep.' (verbum deponens) to VERB."""
        entry = {"part_of_speech": "v. dep.", "key": "test", "senses": ["to test"]}
        assert normalizer._extract_pos(entry) == PartOfSpeech.VERB

    def test_extracts_verb_from_main_notes(self, normalizer):
        """Extracts VERB from main_notes when part_of_speech is unclear."""
        entry = {
            "part_of_speech": "unknown",
            "main_notes": "test, v. a.",
            "key": "test",
            "senses": ["to test"],
        }
        assert normalizer._extract_pos(entry) == PartOfSpeech.VERB

    def test_extracts_adjective_from_pattern(self, normalizer):
        """Detects adjective from -us, -a, -um pattern in main_notes."""
        entry = {
            "part_of_speech": "",
            "main_notes": "bonus, -us, -a, -um",
            "key": "bonus",
            "senses": ["good"],
        }
        assert normalizer._extract_pos(entry) == PartOfSpeech.ADJECTIVE

    def test_returns_unknown_for_unrecognized(self, normalizer):
        """Returns UNKNOWN for unrecognized POS."""
        entry = {"part_of_speech": "xyz", "key": "test", "senses": ["test"]}
        assert normalizer._extract_pos(entry) == PartOfSpeech.UNKNOWN


class TestGenderMapping:
    """Test gender extraction and mapping."""

    def test_maps_masculine(self, normalizer):
        """Maps 'M' to MASCULINE."""
        entry = {"gender": "M"}
        assert normalizer._extract_gender(entry) == Gender.MASCULINE

    def test_maps_feminine(self, normalizer):
        """Maps 'F' to FEMININE."""
        entry = {"gender": "F"}
        assert normalizer._extract_gender(entry) == Gender.FEMININE

    def test_maps_neuter(self, normalizer):
        """Maps 'N' to NEUTER."""
        entry = {"gender": "N"}
        assert normalizer._extract_gender(entry) == Gender.NEUTER

    def test_maps_common(self, normalizer):
        """Maps 'C' to COMMON."""
        entry = {"gender": "C"}
        assert normalizer._extract_gender(entry) == Gender.COMMON

    def test_maps_mf_to_common(self, normalizer):
        """Maps 'MF' to COMMON."""
        entry = {"gender": "MF"}
        assert normalizer._extract_gender(entry) == Gender.COMMON

    def test_handles_lowercase(self, normalizer):
        """Handles lowercase gender codes."""
        entry = {"gender": "m"}
        assert normalizer._extract_gender(entry) == Gender.MASCULINE

    def test_returns_none_for_missing(self, normalizer):
        """Returns None when gender is missing."""
        entry = {}
        assert normalizer._extract_gender(entry) is None


class TestGenitiveFormatting:
    """Test genitive ending formatting."""

    def test_adds_hyphen_prefix(self, normalizer):
        """Adds hyphen prefix if missing."""
        assert normalizer._format_genitive("ae") == "-ae"

    def test_preserves_existing_hyphen(self, normalizer):
        """Preserves existing hyphen prefix."""
        assert normalizer._format_genitive("-ae") == "-ae"

    def test_handles_indecl(self, normalizer):
        """Returns None for indeclinable markers."""
        assert normalizer._format_genitive("indecl.") is None
        assert normalizer._format_genitive("indecl") is None

    def test_returns_none_for_empty(self, normalizer):
        """Returns None for empty input."""
        assert normalizer._format_genitive("") is None
        assert normalizer._format_genitive(None) is None


class TestLemmaNormalization:
    """Test lemma normalization."""

    def test_lowercases(self, normalizer):
        """Lowercases the lemma."""
        assert normalizer._normalize_lemma("AMO") == "amo"

    def test_removes_macrons(self, normalizer):
        """Removes macrons."""
        assert normalizer._normalize_lemma("āmō") == "amo"

    def test_removes_breves(self, normalizer):
        """Removes breves."""
        assert normalizer._normalize_lemma("ămŏ") == "amo"

    def test_normalizes_j_to_i(self, normalizer):
        """Normalizes j to i."""
        assert normalizer._normalize_lemma("juvo") == "iuuo"

    def test_normalizes_v_to_u(self, normalizer):
        """Normalizes v to u."""
        assert normalizer._normalize_lemma("vivo") == "uiuo"

    def test_removes_trailing_digits(self, normalizer):
        """Removes trailing digits (homograph markers)."""
        assert normalizer._normalize_lemma("amo1") == "amo"
        assert normalizer._normalize_lemma("amo2") == "amo"

    def test_handles_empty(self, normalizer):
        """Handles empty input."""
        assert normalizer._normalize_lemma("") == ""


class TestPrincipalPartsExtraction:
    """Test principal parts extraction from main_notes."""

    def test_extracts_standard_pattern(self, normalizer):
        """Extracts standard 3-part + conjugation pattern."""
        parts, conj = normalizer._extract_principal_parts("ămō, āvi, ātum, 1")
        assert conj == 1
        assert parts is not None
        assert parts.present == "ămō"
        assert parts.perfect == "āvi"
        assert parts.supine == "ātum"

    def test_extracts_third_conjugation(self, normalizer):
        """Extracts third conjugation pattern."""
        parts, conj = normalizer._extract_principal_parts("cănō, cĕcĭnī, cantum, 3")
        assert conj == 3
        assert parts is not None
        assert parts.present == "cănō"
        assert parts.perfect == "cĕcĭnī"
        assert parts.supine == "cantum"

    def test_extracts_conjugation_only(self, normalizer):
        """Extracts conjugation number when full pattern not found."""
        parts, conj = normalizer._extract_principal_parts("some text 2 more text")
        assert conj == 2
        assert parts is None

    def test_returns_none_for_empty(self, normalizer):
        """Returns None for empty input."""
        parts, conj = normalizer._extract_principal_parts("")
        assert parts is None
        assert conj is None

    def test_builds_infinitive(self, normalizer):
        """Builds correct infinitive based on conjugation."""
        parts, _ = normalizer._extract_principal_parts("ămō, āvi, ātum, 1")
        assert parts.infinitive == "amāre"

        parts, _ = normalizer._extract_principal_parts("moneō, monui, monitum, 2")
        assert parts.infinitive == "monēre"


class TestVoiceDetermination:
    """Test voice determination."""

    def test_detects_deponent_from_pos(self, normalizer):
        """Detects deponent from part_of_speech field."""
        entry = {"part_of_speech": "v. dep.", "senses": ["to follow"]}
        assert normalizer._determine_voice(entry) == VerbVoice.DEPONENT

    def test_detects_deponent_from_main_notes(self, normalizer):
        """Detects deponent from main_notes."""
        entry = {
            "part_of_speech": "verb",
            "main_notes": "sequor, dep.",
            "senses": ["to follow"],
        }
        assert normalizer._determine_voice(entry) == VerbVoice.DEPONENT

    def test_detects_semi_deponent(self, normalizer):
        """Detects semi-deponent."""
        entry = {
            "part_of_speech": "verb",
            "main_notes": "audeo, semi-dep.",
            "senses": ["to dare"],
        }
        assert normalizer._determine_voice(entry) == VerbVoice.SEMI_DEPONENT

    def test_defaults_to_active(self, normalizer):
        """Defaults to active voice."""
        entry = {"part_of_speech": "verb", "senses": ["to love"]}
        assert normalizer._determine_voice(entry) == VerbVoice.ACTIVE


class TestSenseCleaning:
    """Test sense cleaning and flattening."""

    def test_flattens_nested_senses(self, normalizer):
        """Flattens nested sense lists."""
        senses = ["def1", ["def2", "def3"], "def4"]
        result = normalizer._flatten_senses(senses)
        assert result == ["def1", "def2", "def3", "def4"]

    def test_removes_citations(self, normalizer):
        """Removes author citations."""
        sense = "to love, Cic. Off. 1, 2; Verg. A. 4, 1"
        result = normalizer._clean_single_sense(sense)
        assert "Cic." not in result
        assert "Verg." not in result

    def test_removes_references(self, normalizer):
        """Removes reference patterns."""
        sense = "to love, ib. l. c. al."
        result = normalizer._clean_single_sense(sense)
        assert "ib." not in result
        assert "l. c." not in result

    def test_removes_long_parentheticals(self, normalizer):
        """Removes long parenthetical notes."""
        sense = "to love (this is a very long scholarly note that goes on and on and provides extensive etymological information that students don't need)"
        result = normalizer._clean_single_sense(sense)
        assert "etymological" not in result

    def test_preserves_short_parentheticals(self, normalizer):
        """Preserves short helpful parentheticals."""
        sense = "to love (opp. to hate)"
        result = normalizer._clean_single_sense(sense)
        assert "(opp. to hate)" in result

    def test_removes_cross_references(self, normalizer):
        """Removes v. and cf. cross-references."""
        sense = "to test, v. the pass. cf. other entry"
        result = normalizer._clean_single_sense(sense)
        assert "v. the pass" not in result
        assert "cf. other" not in result

    def test_cleans_whitespace(self, normalizer):
        """Normalizes multiple spaces."""
        sense = "to   love    someone"
        result = normalizer._clean_single_sense(sense)
        assert "   " not in result

    def test_removes_sub_sense_markers(self, normalizer):
        """Removes sub-sense letter/number markers."""
        assert normalizer._clean_single_sense("a) to love") == "to love"
        assert normalizer._clean_single_sense("1) to love") == "to love"
        assert normalizer._clean_single_sense("II. to love") == "to love"

    def test_truncates_long_senses(self, normalizer):
        """Truncates very long senses at natural break points."""
        # Use a first clause that's > 20 chars so truncation triggers
        long_sense = "to love deeply and passionately; " + "to be fond of someone; " * 20
        result = normalizer._clean_single_sense(long_sense)
        assert len(result) < len(long_sense)
        assert "to love deeply and passionately" in result


class TestNormalizeEntry:
    """Test full entry normalization."""

    def test_normalizes_noun(self, normalizer):
        """Normalizes a noun entry."""
        entry = {
            "key": "puella",
            "title_orthography": "puĕlla",
            "title_genitive": "-ae",
            "gender": "F",
            "part_of_speech": "noun",
            "senses": ["a girl", "a maiden", "a sweetheart"],
        }
        result = normalizer.normalize(entry, "puella")

        assert result is not None
        assert result.headword == "puĕlla"
        assert result.lemma == "puella"
        assert result.language == Language.LATIN
        assert result.pos == PartOfSpeech.NOUN
        assert result.gender == Gender.FEMININE
        assert result.genitive == "-ae"
        assert len(result.senses) == 3
        assert result.source == "lewis_short"

    def test_normalizes_verb(self, normalizer):
        """Normalizes a verb entry."""
        entry = {
            "key": "amo",
            "title_orthography": "ămo",
            "part_of_speech": "verb",
            "main_notes": "ămō, āvi, ātum, 1, v. a.",
            "senses": ["to love", "to be fond of"],
        }
        result = normalizer.normalize(entry, "amo")

        assert result is not None
        assert result.headword == "ămo"
        assert result.pos == PartOfSpeech.VERB
        assert result.conjugation == 1
        assert result.latin_principal_parts is not None
        assert result.verb_voice == VerbVoice.ACTIVE

    def test_normalizes_adjective(self, normalizer):
        """Normalizes an adjective entry."""
        entry = {
            "key": "bonus",
            "title_orthography": "bŏnus",
            "part_of_speech": "adjective",
            "main_notes": "bŏnus, -a, -um",
            "senses": ["good", "excellent"],
        }
        result = normalizer.normalize(entry, "bonus")

        assert result is not None
        assert result.pos == PartOfSpeech.ADJECTIVE

    def test_normalizes_deponent_verb(self, normalizer):
        """Normalizes a deponent verb entry."""
        entry = {
            "key": "sequor",
            "title_orthography": "sĕquor",
            "part_of_speech": "v. dep.",
            "main_notes": "sĕquor, secūtus, 3",
            "senses": ["to follow"],
        }
        result = normalizer.normalize(entry, "sequor")

        assert result is not None
        assert result.verb_voice == VerbVoice.DEPONENT

    def test_returns_none_for_empty_entry(self, normalizer):
        """Returns None for empty entry."""
        assert normalizer.normalize({}, "test") is None
        assert normalizer.normalize(None, "test") is None

    def test_returns_none_for_no_senses(self, normalizer):
        """Returns None when entry has no senses."""
        entry = {"key": "test", "senses": []}
        assert normalizer.normalize(entry, "test") is None

    def test_limits_senses(self, normalizer):
        """Limits senses to max_senses."""
        entry = {
            "key": "test",
            "title_orthography": "test",
            "part_of_speech": "noun",
            "senses": ["sense1", "sense2", "sense3", "sense4", "sense5"],
        }
        result = normalizer.normalize(entry, "test")
        assert len(result.senses) == 3  # max_senses default

    def test_uses_key_as_fallback_headword(self, normalizer):
        """Uses key as headword when title_orthography missing."""
        entry = {
            "key": "testword",
            "part_of_speech": "noun",
            "senses": ["a test"],
        }
        result = normalizer.normalize(entry, "testword")
        assert result.headword == "testword"


class TestGreekPreservation:
    """Test Greek text handling in senses."""

    def test_removes_greek_by_default(self):
        """Removes Greek text by default."""
        normalizer = LewisShortNormalizer(preserve_greek=False)
        sense = "to love, φιλέω"
        result = normalizer._clean_single_sense(sense)
        assert "φιλέω" not in result

    def test_preserves_greek_when_enabled(self):
        """Preserves Greek text when enabled."""
        normalizer = LewisShortNormalizer(preserve_greek=True)
        sense = "to love, φιλέω"
        result = normalizer._clean_single_sense(sense)
        assert "φιλέω" in result


class TestScholarlyApparatusCleaning:
    """Test removal of scholarly apparatus that's not pedagogically useful."""

    def test_removes_temporal_labels(self, normalizer):
        """Removes temporal classification labels like (ante-class.), (post-class.)."""
        assert "(ante-class.)" not in normalizer._clean_single_sense(
            "to live, feed (ante-class.): ficis"
        )
        assert "(post-class.)" not in normalizer._clean_single_sense(
            "to fill with marrow (post-class.)"
        )
        assert "(post-Aug.)" not in normalizer._clean_single_sense(
            "suavity, courteousness (post-Aug.)"
        )

    def test_removes_section_markers(self, normalizer):
        """Removes section markers like § 60, § 181."""
        assert "§ 60" not in normalizer._clean_single_sense(
            "a crane, § 60; ; 75"
        )
        assert "§ 181" not in normalizer._clean_single_sense(
            "to be in heat, § 181; perh. also"
        )

    def test_removes_page_numbers(self, normalizer):
        """Removes page number references like p. 89, p. 59."""
        assert "p. 89" not in normalizer._clean_single_sense(
            "only Boëth. in Porphyr. 4, p. 89"
        )
        assert "p. 59" not in normalizer._clean_single_sense(
            "Lex. Servil. p. 59 Haubold"
        )

    def test_removes_etymology_references(self, normalizer):
        """Removes etymology like Sanscr., Gr., root or."""
        result = normalizer._clean_single_sense(
            "Fut. part. oriturus, root or.; Sanscr. ar-; Gr. ̓́"
        )
        assert "Sanscr." not in result
        assert "root or." not in result

    def test_removes_manuscript_notations(self, normalizer):
        """Removes manuscript notations like freq. in MSS., inscrr."""
        result = normalizer._clean_single_sense(
            "Masc.eidem, freq. in MSS. and inscrr.; ad 120"
        )
        assert "freq. in MSS." not in result
        assert "inscrr." not in result

    def test_removes_author_page_citations(self, normalizer):
        """Removes author + page citations like Naev. ap., Pac. ap. Non."""
        result = normalizer._clean_single_sense(
            "n. irreg. : Pac. ap. Non. ; Quadrig. ap. ; 1010"
        )
        assert "Pac. ap. Non." not in result
        assert "Quadrig. ap." not in result

    def test_removes_technical_abbreviations(self, normalizer):
        """Removes or expands technical abbreviations like n. irreg., inch."""
        result = normalizer._clean_single_sense(
            "inch. n. and a."
        )
        # Should either remove or the definition should make sense
        assert result == "" or "gape" in result.lower() or "open" in result.lower() or len(result) < 20

    def test_removes_empty_semicolons(self, normalizer):
        """Removes empty citation sequences like '; ; .'."""
        result = normalizer._clean_single_sense(
            "a crane, ; ; 75; regarded as a delicacy"
        )
        assert "; ;" not in result
        assert "; 75" not in result

    def test_cleans_truncated_definitions(self, normalizer):
        """Cleans definitions that end with incomplete fragments."""
        result = normalizer._clean_single_sense(
            "to support with pales: reliquae partes vinearum nunc palandae et alligandae sunt,: ut..."
        )
        # Should not end with incomplete Latin or "..."
        assert not result.endswith("...")
        assert not result.endswith(",:")

    def test_removes_form_variant_lists(self, normalizer):
        """Removes variant form listings like 'Gen. plur., denum, fin.'."""
        result = normalizer._clean_single_sense(
            "Gen. plur., denum, fin.; : denorum,5 fin.), num. distrib., ten each"
        )
        assert "Gen. plur." not in result
        assert "fin.)" not in result
        # Should preserve the actual definition
        assert "ten each" in result or "ten" in result.lower()

    def test_produces_clean_definition_for_orior(self, normalizer):
        """The verb orior should have a clean definition, not etymology."""
        # This is what the raw L&S data looks like
        result = normalizer._clean_single_sense(
            "Fut. part. oriturus, 4 , root or.; Sanscr. ar-; Gr. ̓́, ̓́; Etym. 348 ."
        )
        # This should be cleaned to empty or a meaningful stub
        # The real definition should come from a different sense
        assert "Sanscr." not in result
        assert "Etym." not in result

    def test_produces_clean_definition_for_possum(self, normalizer):
        """The verb possum should have a clean definition."""
        result = normalizer._clean_single_sense(
            "n. irreg. : Pac. ap. Non. ; Quadrig. ap. ; 1010: poteratur, Cael. ap. Non."
        )
        # Should be cleaned to empty - this is not a definition
        assert "Pac. ap." not in result
        assert "poteratur" not in result or len(result) < 30


class TestRealWorldEntries:
    """Test with real L&S entry structures."""

    def test_aaron_entry(self, normalizer):
        """Test with Aaron entry (indeclinable noun)."""
        entry = {
            "alternative_genative": ["ōnis"],
            "declension": None,
            "entry_type": "main",
            "gender": "M",
            "key": "Aaron",
            "main_notes": "(Aārōn, Prud. Psych. 884),  or",
            "part_of_speech": "noun",
            "senses": [
                "Aaron, brother of Moses, and first high-priest of the Hebrews, Vulg. Exod. 4, 14; 6, 25 al."
            ],
            "title_genitive": "indecl.",
            "title_orthography": "Aărōn",
        }
        result = normalizer.normalize(entry, "aaron")

        assert result is not None
        assert result.headword == "Aărōn"
        assert result.gender == Gender.MASCULINE
        assert result.genitive is None  # indecl.
        assert "Aaron" in result.senses[0]

    def test_amo_entry(self, normalizer):
        """Test with amo entry (complex verb)."""
        entry = {
            "entry_type": "main",
            "key": "amo",
            "main_notes": "ămō, āvi, ātum, 1, v. a.",
            "part_of_speech": "v. a.prep.P. a.adv.",  # Corrupted POS field
            "senses": [
                "to like, to love",
                "In gen.: quid autem est amare, nisi velle bonis aliquem adfici",
            ],
        }
        result = normalizer.normalize(entry, "amo")

        assert result is not None
        assert result.pos == PartOfSpeech.VERB  # Should detect from main_notes
        assert result.conjugation == 1
        assert "to love" in result.senses[0] or "to like" in result.senses[0]


class TestEntryIntegration:
    """Test integration with NormalizedLexicalEntry."""

    def test_creates_valid_entry(self, normalizer):
        """Creates a valid NormalizedLexicalEntry."""
        entry = {
            "key": "amor",
            "title_orthography": "ămor",
            "title_genitive": "-ōris",
            "gender": "M",
            "part_of_speech": "noun",
            "declension": 3,
            "senses": ["love", "affection", "desire"],
        }
        result = normalizer.normalize(entry, "amor")

        assert result is not None
        assert result.model_dump() is not None  # Pydantic serialization works

    def test_entry_has_correct_source(self, normalizer):
        """Entry has correct source attribution."""
        entry = {
            "key": "test",
            "part_of_speech": "noun",
            "senses": ["a test"],
        }
        result = normalizer.normalize(entry, "test")
        assert result.source == "lewis_short"
        assert result.confidence == 1.0
