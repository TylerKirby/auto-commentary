"""
Tests for core domain models.

Tests cover Gloss creation from NormalizedLexicalEntry, article handling,
and Steadman-style formatting.
"""

from autocom.core.lexical import (
    Gender,
    GreekPrincipalParts,
    Language,
    LatinPrincipalParts,
    NormalizedLexicalEntry,
    PartOfSpeech,
)
from autocom.core.models import Gloss, _extract_infinitive_ending


class TestGlossFromNormalizedEntry:
    """Test Gloss.from_normalized_entry() transformation."""

    def test_creates_gloss_from_latin_noun(self):
        """Creates Gloss from Latin noun entry."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["earth", "land"],
            gender=Gender.FEMININE,
            genitive="-ae",
            source="whitakers",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.headword == "terra"
        assert gloss.lemma == "terra"
        assert gloss.senses == ["earth", "land"]
        assert gloss.gender == "f."
        assert gloss.genitive == "-ae"
        assert gloss.pos_abbrev is None  # Nouns use gender, not POS abbreviation
        assert gloss.article is None  # Latin has no articles

    def test_creates_gloss_from_latin_verb(self):
        """Creates Gloss from Latin verb entry with principal parts."""
        entry = NormalizedLexicalEntry(
            headword="amo",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to love"],
            latin_principal_parts=LatinPrincipalParts(
                present="amo",
                infinitive="amare",
                perfect="amavi",
                supine="amatum",
            ),
            conjugation=1,
            source="whitakers",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.pos_abbrev == "v."
        assert gloss.principal_parts == "amavi, amatum (1)"


class TestGlossArticleHandling:
    """Test Gloss article field for Greek nouns."""

    def test_transfers_masculine_article(self):
        """Transfers ὁ article for masculine nouns."""
        entry = NormalizedLexicalEntry(
            headword="λόγος",
            lemma="λογος",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            senses=["word", "speech"],
            gender=Gender.MASCULINE,
            genitive="-ου",
            article="ὁ",
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.article == "ὁ"
        assert gloss.headword == "λόγος"
        assert gloss.genitive == "-ου"
        assert gloss.gender == "m."

    def test_transfers_feminine_article(self):
        """Transfers ἡ article for feminine nouns."""
        entry = NormalizedLexicalEntry(
            headword="γυνή",
            lemma="γυνη",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            senses=["woman", "wife"],
            gender=Gender.FEMININE,
            genitive="-αικός",
            article="ἡ",
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.article == "ἡ"
        assert gloss.gender == "f."

    def test_transfers_neuter_article(self):
        """Transfers τό article for neuter nouns."""
        entry = NormalizedLexicalEntry(
            headword="ἔργον",
            lemma="εργον",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            senses=["work", "deed"],
            gender=Gender.NEUTER,
            genitive="-ου",
            article="τό",
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.article == "τό"
        assert gloss.gender == "n."

    def test_no_article_for_verbs(self):
        """Verbs do not have articles."""
        entry = NormalizedLexicalEntry(
            headword="λύω",
            lemma="λυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to loose"],
            greek_principal_parts=GreekPrincipalParts(
                present="λύω",
                future="λύσω",
            ),
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.article is None
        assert gloss.pos_abbrev == "v."

    def test_no_article_for_adjectives(self):
        """Adjectives do not have articles."""
        entry = NormalizedLexicalEntry(
            headword="καλός",
            lemma="καλος",
            language=Language.GREEK,
            pos=PartOfSpeech.ADJECTIVE,
            senses=["beautiful", "good"],
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.article is None
        assert gloss.pos_abbrev == "adj."

    def test_no_article_for_latin_nouns(self):
        """Latin nouns do not have articles."""
        entry = NormalizedLexicalEntry(
            headword="puer",
            lemma="puer",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["boy"],
            gender=Gender.MASCULINE,
            genitive="-i",
            source="whitakers",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.article is None


class TestGlossGreekPrincipalParts:
    """Test Greek principal parts formatting in Gloss."""

    def test_formats_all_six_principal_parts(self):
        """Formats all 6 Greek principal parts."""
        entry = NormalizedLexicalEntry(
            headword="λύω",
            lemma="λυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to loose"],
            greek_principal_parts=GreekPrincipalParts(
                present="λύω",
                future="λύσω",
                aorist="ἔλυσα",
                perfect_active="λέλυκα",
                perfect_middle="λέλυμαι",
                aorist_passive="ἐλύθην",
            ),
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.principal_parts == "λύσω, ἔλυσα, λέλυκα, λέλυμαι, ἐλύθην"

    def test_formats_partial_principal_parts(self):
        """Formats partial principal parts (e.g., deponent verbs)."""
        entry = NormalizedLexicalEntry(
            headword="ἔρχομαι",
            lemma="ερχομαι",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to come", "to go"],
            greek_principal_parts=GreekPrincipalParts(
                present="ἔρχομαι",
                future="εἶμι",
            ),
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.principal_parts == "εἶμι"


class TestGlossFrequency:
    """Test frequency handling in Gloss creation."""

    def test_passes_frequency_to_gloss(self):
        """Passes frequency parameter to Gloss."""
        entry = NormalizedLexicalEntry(
            headword="καί",
            lemma="και",
            language=Language.GREEK,
            pos=PartOfSpeech.CONJUNCTION,
            senses=["and", "also"],
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry, frequency=42)

        assert gloss.frequency == 42

    def test_uses_entry_frequency_if_not_provided(self):
        """Uses entry.frequency when parameter not provided."""
        entry = NormalizedLexicalEntry(
            headword="καί",
            lemma="και",
            language=Language.GREEK,
            pos=PartOfSpeech.CONJUNCTION,
            senses=["and"],
            frequency=10,
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.frequency == 10

    def test_parameter_overrides_entry_frequency(self):
        """Parameter frequency overrides entry.frequency."""
        entry = NormalizedLexicalEntry(
            headword="καί",
            lemma="και",
            language=Language.GREEK,
            pos=PartOfSpeech.CONJUNCTION,
            senses=["and"],
            frequency=10,
            source="morpheus",
        )

        gloss = Gloss.from_normalized_entry(entry, frequency=25)

        assert gloss.frequency == 25


class TestGlossBestSense:
    """Test Gloss.best property."""

    def test_returns_first_sense(self):
        """Returns the first sense as best."""
        gloss = Gloss(lemma="test", senses=["first", "second", "third"])
        assert gloss.best == "first"

    def test_returns_none_for_empty_senses(self):
        """Returns None when no senses."""
        gloss = Gloss(lemma="test", senses=[])
        assert gloss.best is None


class TestExtractInfinitiveEnding:
    """Test _extract_infinitive_ending() helper function."""

    def test_first_conjugation_with_macron(self):
        """Extracts -āre for 1st conjugation verbs."""
        assert _extract_infinitive_ending("amō", "amāre") == "-āre"
        assert _extract_infinitive_ending("vocō", "vocāre") == "-āre"

    def test_second_conjugation_with_macron(self):
        """Extracts -ēre for 2nd conjugation verbs."""
        assert _extract_infinitive_ending("moneō", "monēre") == "-ēre"
        assert _extract_infinitive_ending("videō", "vidēre") == "-ēre"

    def test_third_conjugation(self):
        """Extracts -ere for 3rd conjugation verbs."""
        assert _extract_infinitive_ending("dūcō", "dūcere") == "-ere"
        assert _extract_infinitive_ending("capiō", "capere") == "-ere"

    def test_fourth_conjugation_with_macron(self):
        """Extracts -īre for 4th conjugation verbs."""
        assert _extract_infinitive_ending("veniō", "venīre") == "-īre"
        assert _extract_infinitive_ending("audiō", "audīre") == "-īre"

    def test_without_macrons(self):
        """Handles infinitives without macrons."""
        assert _extract_infinitive_ending("amo", "amare") == "-are"
        assert _extract_infinitive_ending("venio", "venire") == "-ire"

    def test_deponent_infinitive(self):
        """Handles deponent infinitives ending in -ī."""
        assert _extract_infinitive_ending("sequor", "sequī") == "-ī"

    def test_none_infinitive_returns_none(self):
        """Returns None when infinitive is None or empty."""
        assert _extract_infinitive_ending("amō", None) is None
        assert _extract_infinitive_ending("amō", "") is None

    def test_none_headword_uses_fallback(self):
        """Uses fallback extraction when headword is None."""
        assert _extract_infinitive_ending(None, "amāre") == "-āre"


class TestGlossVerbInfinitiveEnding:
    """Test that verbs include infinitive ending in Gloss.genitive field."""

    def test_latin_verb_gets_infinitive_ending(self):
        """Latin verbs have infinitive ending in genitive field (Steadman style)."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to love"],
            latin_principal_parts=LatinPrincipalParts(
                present="amō",
                infinitive="amāre",
                perfect="amāvī",
                supine="amātum",
            ),
            conjugation=1,
            source="whitakers",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.genitive == "-āre"
        assert gloss.pos_abbrev == "v."
        assert gloss.principal_parts == "amāvī, amātum (1)"

    def test_fourth_conjugation_verb_ending(self):
        """4th conjugation verbs get -īre ending."""
        entry = NormalizedLexicalEntry(
            headword="veniō",
            lemma="venio",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to come"],
            latin_principal_parts=LatinPrincipalParts(
                present="veniō",
                infinitive="venīre",
                perfect="vēnī",
                supine="ventum",
            ),
            conjugation=4,
            source="whitakers",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.genitive == "-īre"

    def test_nouns_retain_original_genitive(self):
        """Nouns retain their original genitive ending."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["earth"],
            gender=Gender.FEMININE,
            genitive="-ae",
            source="whitakers",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.genitive == "-ae"

    def test_verb_without_infinitive_no_ending(self):
        """Verbs without infinitive don't get an ending."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to love"],
            # No principal parts
            source="whitakers",
        )

        gloss = Gloss.from_normalized_entry(entry)

        assert gloss.genitive is None
