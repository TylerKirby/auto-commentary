"""Tests for core lexical data models."""

import pytest
from pydantic import ValidationError

from autocom.core.lexical import (
    DIALECT_DISPLAY_MAP,
    GENDER_DISPLAY_MAP,
    GREEK_ARTICLES,
    GREEK_VERB_CLASS_DISPLAY_MAP,
    POS_DISPLAY_MAP,
    POS_ORDER_MAP,
    VOICE_DISPLAY_MAP,
    Gender,
    GreekDialect,
    GreekPrincipalParts,
    GreekStemType,
    GreekVerbClass,
    Language,
    LatinPrincipalParts,
    LatinStemType,
    NormalizedLexicalEntry,
    Number,
    PartOfSpeech,
    VerbVoice,
    get_dialect_display,
    get_gender_display,
    get_greek_article,
    get_greek_verb_class_display,
    get_pos_display,
    get_pos_order,
    get_voice_display,
)


class TestEnums:
    """Test enum definitions and values."""

    def test_language_values(self):
        """Language enum has expected values."""
        assert Language.LATIN.value == "latin"
        assert Language.GREEK.value == "greek"

    def test_pos_values(self):
        """PartOfSpeech enum has all expected categories."""
        expected = [
            "noun",
            "verb",
            "adjective",
            "adverb",
            "preposition",
            "conjunction",
            "pronoun",
            "interjection",
            "numeral",
            "particle",
            "article",
            "unknown",
        ]
        actual = [pos.value for pos in PartOfSpeech]
        assert set(expected) == set(actual)

    def test_gender_values(self):
        """Gender enum has expected values."""
        assert Gender.MASCULINE.value == "m"
        assert Gender.FEMININE.value == "f"
        assert Gender.NEUTER.value == "n"
        assert Gender.COMMON.value == "c"
        assert Gender.UNKNOWN.value == "x"

    def test_number_values(self):
        """Number enum includes plural tantum."""
        assert Number.SINGULAR.value == "sg"
        assert Number.PLURAL.value == "pl"
        assert Number.PLURAL_ONLY.value == "pl_tantum"
        assert Number.DUAL.value == "du"

    def test_verb_voice_values(self):
        """VerbVoice enum has all voice categories."""
        assert VerbVoice.ACTIVE.value == "active"
        assert VerbVoice.PASSIVE.value == "passive"
        assert VerbVoice.MIDDLE.value == "middle"
        assert VerbVoice.DEPONENT.value == "deponent"
        assert VerbVoice.SEMI_DEPONENT.value == "semi_deponent"

    def test_greek_verb_class_values(self):
        """GreekVerbClass enum has all verb classifications."""
        assert GreekVerbClass.OMEGA.value == "omega"
        assert GreekVerbClass.MI.value == "mi"
        assert GreekVerbClass.CONTRACT_ALPHA.value == "alpha_contract"
        assert GreekVerbClass.CONTRACT_EPSILON.value == "epsilon_contract"
        assert GreekVerbClass.CONTRACT_OMICRON.value == "omicron_contract"


class TestLatinPrincipalParts:
    """Test LatinPrincipalParts model."""

    def test_minimal_parts(self):
        """Can create with just required fields."""
        parts = LatinPrincipalParts(present="amō", infinitive="amāre")
        assert parts.present == "amō"
        assert parts.infinitive == "amāre"
        assert parts.perfect is None
        assert parts.supine is None

    def test_full_parts(self):
        """Can create with all four principal parts."""
        parts = LatinPrincipalParts(
            present="amō",
            infinitive="amāre",
            perfect="amāvī",
            supine="amātum",
        )
        assert parts.present == "amō"
        assert parts.perfect == "amāvī"
        assert parts.supine == "amātum"

    def test_deponent_parts(self):
        """Can create deponent verb parts (no supine)."""
        parts = LatinPrincipalParts(
            present="sequor",
            infinitive="sequī",
            perfect="secūtus sum",
            supine=None,
        )
        assert parts.present == "sequor"
        assert parts.perfect == "secūtus sum"

    def test_with_participles(self):
        """Can include optional participle forms."""
        parts = LatinPrincipalParts(
            present="amō",
            infinitive="amāre",
            perfect="amāvī",
            supine="amātum",
            future_active_participle="amātūrus",
            perfect_passive_participle="amātus",
        )
        assert parts.future_active_participle == "amātūrus"
        assert parts.perfect_passive_participle == "amātus"


class TestGreekPrincipalParts:
    """Test GreekPrincipalParts model."""

    def test_minimal_parts(self):
        """Can create with just present form."""
        parts = GreekPrincipalParts(present="λύω")
        assert parts.present == "λύω"
        assert parts.future is None

    def test_full_parts(self):
        """Can create with all six principal parts."""
        parts = GreekPrincipalParts(
            present="λύω",
            future="λύσω",
            aorist="ἔλυσα",
            perfect_active="λέλυκα",
            perfect_middle="λέλυμαι",
            aorist_passive="ἐλύθην",
        )
        assert parts.present == "λύω"
        assert parts.future == "λύσω"
        assert parts.aorist == "ἔλυσα"
        assert parts.perfect_active == "λέλυκα"
        assert parts.perfect_middle == "λέλυμαι"
        assert parts.aorist_passive == "ἐλύθην"

    def test_deponent_parts(self):
        """Can create deponent verb parts (no passive)."""
        parts = GreekPrincipalParts(
            present="ἔρχομαι",
            future="εἶμι",
            aorist=None,
            perfect_active="ἐλήλυθα",
            perfect_middle=None,
            aorist_passive=None,
            second_aorist="ἦλθον",
        )
        assert parts.present == "ἔρχομαι"
        assert parts.second_aorist == "ἦλθον"
        assert parts.aorist is None

    def test_with_additional_forms(self):
        """Can include additional irregular forms."""
        parts = GreekPrincipalParts(
            present="βάλλω",
            future="βαλῶ",
            aorist=None,
            perfect_active="βέβληκα",
            perfect_middle="βέβλημαι",
            aorist_passive="ἐβλήθην",
            second_aorist="ἔβαλον",
            future_middle="βαλοῦμαι",
        )
        assert parts.second_aorist == "ἔβαλον"
        assert parts.future_middle == "βαλοῦμαι"


class TestNormalizedLexicalEntry:
    """Test the NormalizedLexicalEntry model."""

    def test_minimal_entry(self):
        """Can create entry with only required fields."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            source="whitakers",
        )
        assert entry.headword == "terra"
        assert entry.lemma == "terra"
        assert entry.language == "latin"
        assert entry.pos == "noun"
        assert entry.source == "whitakers"
        assert entry.confidence == 1.0  # Default
        assert entry.senses == []  # Default empty

    def test_full_latin_noun(self):
        """Can create complete Latin noun entry."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["earth", "land", "ground"],
            gender=Gender.FEMININE,
            declension=1,
            genitive="-ae",
            source="whitakers",
            confidence=1.0,
            frequency=5,
        )
        assert entry.gender == "f"
        assert entry.declension == 1
        assert entry.genitive == "-ae"
        assert entry.frequency == 5
        assert len(entry.senses) == 3

    def test_full_latin_verb_with_structured_parts(self):
        """Can create complete Latin verb entry with structured principal parts."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to love", "to be fond of"],
            verb_voice=VerbVoice.ACTIVE,
            conjugation=1,
            latin_principal_parts=LatinPrincipalParts(
                present="amō",
                infinitive="amāre",
                perfect="amāvī",
                supine="amātum",
            ),
            source="whitakers",
            confidence=1.0,
        )
        assert entry.conjugation == 1
        assert entry.verb_voice == "active"
        assert entry.latin_principal_parts.present == "amō"
        assert entry.latin_principal_parts.perfect == "amāvī"

    def test_latin_deponent_verb(self):
        """Can create Latin deponent verb entry."""
        entry = NormalizedLexicalEntry(
            headword="sequor",
            lemma="sequor",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to follow", "to pursue"],
            verb_voice=VerbVoice.DEPONENT,
            conjugation=3,
            latin_principal_parts=LatinPrincipalParts(
                present="sequor",
                infinitive="sequī",
                perfect="secūtus sum",
            ),
            source="lewis_short",
        )
        assert entry.verb_voice == "deponent"
        assert entry.is_deponent is True

    def test_latin_semi_deponent_verb(self):
        """Can create Latin semi-deponent verb entry."""
        entry = NormalizedLexicalEntry(
            headword="audeō",
            lemma="audeo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to dare", "to venture"],
            verb_voice=VerbVoice.SEMI_DEPONENT,
            conjugation=2,
            source="lewis_short",
        )
        assert entry.verb_voice == "semi_deponent"
        assert entry.is_deponent is True

    def test_full_latin_verb(self):
        """Can create complete Latin verb entry (legacy format)."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to love", "to be fond of"],
            conjugation=1,
            principal_parts=["amāvī", "amātum"],
            source="lewis_short",
            confidence=1.0,
        )
        assert entry.conjugation == 1
        assert entry.principal_parts == ["amāvī", "amātum"]

    def test_full_greek_noun(self):
        """Can create complete Greek noun entry with article."""
        entry = NormalizedLexicalEntry(
            headword="λόγος",
            lemma="λογος",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            senses=["word", "speech", "reason"],
            gender=Gender.MASCULINE,
            declension=2,
            genitive="-ου",
            article="ὁ",
            source="lsj",
            confidence=1.0,
        )
        assert entry.language == "greek"
        assert entry.article == "ὁ"
        assert entry.gender == "m"

    def test_full_greek_verb_with_structured_parts(self):
        """Can create Greek verb with structured 6 principal parts."""
        entry = NormalizedLexicalEntry(
            headword="λύω",
            lemma="λυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to loose", "to release"],
            verb_voice=VerbVoice.ACTIVE,
            greek_verb_class=GreekVerbClass.OMEGA,
            greek_principal_parts=GreekPrincipalParts(
                present="λύω",
                future="λύσω",
                aorist="ἔλυσα",
                perfect_active="λέλυκα",
                perfect_middle="λέλυμαι",
                aorist_passive="ἐλύθην",
            ),
            source="lsj",
        )
        assert entry.greek_verb_class == "omega"
        assert entry.greek_principal_parts.present == "λύω"
        assert entry.greek_principal_parts.aorist_passive == "ἐλύθην"

    def test_greek_mi_verb(self):
        """Can create Greek -μι verb entry."""
        entry = NormalizedLexicalEntry(
            headword="δίδωμι",
            lemma="διδωμι",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to give", "to grant"],
            verb_voice=VerbVoice.ACTIVE,
            greek_verb_class=GreekVerbClass.MI,
            is_irregular=True,
            greek_principal_parts=GreekPrincipalParts(
                present="δίδωμι",
                future="δώσω",
                aorist="ἔδωκα",
                perfect_active="δέδωκα",
                perfect_middle="δέδομαι",
                aorist_passive="ἐδόθην",
            ),
            source="lsj",
        )
        assert entry.greek_verb_class == "mi"
        assert entry.is_irregular is True

    def test_greek_contract_verb(self):
        """Can create Greek contract verb entry."""
        entry = NormalizedLexicalEntry(
            headword="τιμάω",
            lemma="τιμαω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to honor", "to value"],
            verb_voice=VerbVoice.ACTIVE,
            greek_verb_class=GreekVerbClass.CONTRACT_ALPHA,
            source="lsj",
        )
        assert entry.greek_verb_class == "alpha_contract"

    def test_greek_deponent_verb(self):
        """Can create Greek deponent verb entry."""
        entry = NormalizedLexicalEntry(
            headword="ἔρχομαι",
            lemma="ερχομαι",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to come", "to go"],
            verb_voice=VerbVoice.DEPONENT,
            greek_verb_class=GreekVerbClass.OMEGA,
            is_suppletive=True,
            has_second_aorist=True,
            greek_principal_parts=GreekPrincipalParts(
                present="ἔρχομαι",
                future="εἶμι",
                perfect_active="ἐλήλυθα",
                second_aorist="ἦλθον",
            ),
            source="lsj",
        )
        assert entry.verb_voice == "deponent"
        assert entry.is_suppletive is True
        assert entry.has_second_aorist is True
        assert entry.is_deponent is True

    def test_full_greek_verb(self):
        """Can create Greek verb with 5 principal parts (legacy format)."""
        entry = NormalizedLexicalEntry(
            headword="λύω",
            lemma="λυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to loose", "to release"],
            principal_parts=["λύσω", "ἔλυσα", "λέλυκα", "λέλυμαι", "ἐλύθην"],
            source="lsj",
        )
        assert len(entry.principal_parts) == 5

    def test_plural_tantum_noun(self):
        """Can mark pluralia tantum nouns."""
        entry = NormalizedLexicalEntry(
            headword="arma",
            lemma="arma",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["weapons", "arms"],
            gender=Gender.NEUTER,
            number=Number.PLURAL_ONLY,
            declension=2,
            genitive="-ōrum",
            source="whitakers",
        )
        assert entry.number == "pl_tantum"

    def test_proper_noun_flag(self):
        """Can mark proper nouns."""
        entry = NormalizedLexicalEntry(
            headword="Italia",
            lemma="italia",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["Italy"],
            is_proper_noun=True,
            source="whitakers",
        )
        assert entry.is_proper_noun is True

    def test_variant_tracking(self):
        """Can track spelling variants."""
        entry = NormalizedLexicalEntry(
            headword="caelum",
            lemma="caelum",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["sky", "heaven"],
            variant_of="coelum",
            source="lewis_short",
        )
        assert entry.variant_of == "coelum"

    def test_compound_verb_tracking(self):
        """Can track compound verbs."""
        entry = NormalizedLexicalEntry(
            headword="ἀπολύω",
            lemma="απολυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to release", "to set free"],
            is_compound=True,
            simplex_form="λύω",
            prefix="ἀπο-",
            source="lsj",
        )
        assert entry.is_compound is True
        assert entry.simplex_form == "λύω"
        assert entry.prefix == "ἀπο-"

    def test_defective_verb(self):
        """Can mark defective verbs."""
        entry = NormalizedLexicalEntry(
            headword="οἶδα",
            lemma="οιδα",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to know"],
            is_defective=True,
            source="lsj",
        )
        assert entry.is_defective is True

    def test_suppletive_verb(self):
        """Can mark suppletive verbs (different stems)."""
        entry = NormalizedLexicalEntry(
            headword="ferō",
            lemma="fero",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to carry", "to bear"],
            is_suppletive=True,
            latin_principal_parts=LatinPrincipalParts(
                present="ferō",
                infinitive="ferre",
                perfect="tulī",
                supine="lātum",
            ),
            source="lewis_short",
        )
        assert entry.is_suppletive is True


class TestNormalizedLexicalEntryValidation:
    """Test validation constraints on NormalizedLexicalEntry."""

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        # Valid confidence
        entry = NormalizedLexicalEntry(
            headword="test",
            lemma="test",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            source="test",
            confidence=0.5,
        )
        assert entry.confidence == 0.5

        # Invalid: too high
        with pytest.raises(ValidationError):
            NormalizedLexicalEntry(
                headword="test",
                lemma="test",
                language=Language.LATIN,
                pos=PartOfSpeech.NOUN,
                source="test",
                confidence=1.5,
            )

        # Invalid: negative
        with pytest.raises(ValidationError):
            NormalizedLexicalEntry(
                headword="test",
                lemma="test",
                language=Language.LATIN,
                pos=PartOfSpeech.NOUN,
                source="test",
                confidence=-0.1,
            )

    def test_declension_bounds(self):
        """Declension must be 1-5."""
        # Valid
        entry = NormalizedLexicalEntry(
            headword="test",
            lemma="test",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            source="test",
            declension=3,
        )
        assert entry.declension == 3

        # Invalid: 0
        with pytest.raises(ValidationError):
            NormalizedLexicalEntry(
                headword="test",
                lemma="test",
                language=Language.LATIN,
                pos=PartOfSpeech.NOUN,
                source="test",
                declension=0,
            )

        # Invalid: 6
        with pytest.raises(ValidationError):
            NormalizedLexicalEntry(
                headword="test",
                lemma="test",
                language=Language.LATIN,
                pos=PartOfSpeech.NOUN,
                source="test",
                declension=6,
            )

    def test_conjugation_bounds(self):
        """Conjugation must be 1-4."""
        # Valid
        entry = NormalizedLexicalEntry(
            headword="test",
            lemma="test",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            source="test",
            conjugation=4,
        )
        assert entry.conjugation == 4

        # Invalid: 5
        with pytest.raises(ValidationError):
            NormalizedLexicalEntry(
                headword="test",
                lemma="test",
                language=Language.LATIN,
                pos=PartOfSpeech.VERB,
                source="test",
                conjugation=5,
            )

    def test_required_fields(self):
        """Required fields must be provided."""
        with pytest.raises(ValidationError):
            NormalizedLexicalEntry(
                lemma="test",
                language=Language.LATIN,
                pos=PartOfSpeech.NOUN,
                source="test",
            )  # Missing headword


class TestNormalizedLexicalEntryProperties:
    """Test computed properties and methods."""

    def test_has_definition_true(self):
        """has_definition returns True when senses exist."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["earth"],
            source="whitakers",
        )
        assert entry.has_definition is True

    def test_has_definition_false(self):
        """has_definition returns False when no senses."""
        entry = NormalizedLexicalEntry(
            headword="unknown",
            lemma="unknown",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=[],
            source="whitakers",
        )
        assert entry.has_definition is False

    def test_best_sense_exists(self):
        """best_sense returns first sense."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["earth", "land", "ground"],
            source="whitakers",
        )
        assert entry.best_sense == "earth"

    def test_best_sense_none(self):
        """best_sense returns None when no senses."""
        entry = NormalizedLexicalEntry(
            headword="unknown",
            lemma="unknown",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            source="whitakers",
        )
        assert entry.best_sense is None

    def test_is_deponent_true(self):
        """is_deponent returns True for deponent verbs."""
        entry = NormalizedLexicalEntry(
            headword="sequor",
            lemma="sequor",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            verb_voice=VerbVoice.DEPONENT,
            source="whitakers",
        )
        assert entry.is_deponent is True

    def test_is_deponent_semi(self):
        """is_deponent returns True for semi-deponent verbs."""
        entry = NormalizedLexicalEntry(
            headword="audeō",
            lemma="audeo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            verb_voice=VerbVoice.SEMI_DEPONENT,
            source="whitakers",
        )
        assert entry.is_deponent is True

    def test_is_deponent_false(self):
        """is_deponent returns False for active verbs."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            verb_voice=VerbVoice.ACTIVE,
            source="whitakers",
        )
        assert entry.is_deponent is False

    def test_format_principal_parts_latin_structured(self):
        """format_principal_parts works with structured Latin parts."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            conjugation=1,
            latin_principal_parts=LatinPrincipalParts(
                present="amō",
                infinitive="amāre",
                perfect="amāvī",
                supine="amātum",
            ),
            source="whitakers",
        )
        assert entry.format_principal_parts() == "amō, amāre, amāvī, amātum (1)"

    def test_format_principal_parts_latin_no_conjugation(self):
        """format_principal_parts can exclude conjugation."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            conjugation=1,
            latin_principal_parts=LatinPrincipalParts(
                present="amō",
                infinitive="amāre",
                perfect="amāvī",
                supine="amātum",
            ),
            source="whitakers",
        )
        assert entry.format_principal_parts(include_conjugation=False) == "amō, amāre, amāvī, amātum"

    def test_format_principal_parts_greek_structured(self):
        """format_principal_parts works with structured Greek parts."""
        entry = NormalizedLexicalEntry(
            headword="λύω",
            lemma="λυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            greek_principal_parts=GreekPrincipalParts(
                present="λύω",
                future="λύσω",
                aorist="ἔλυσα",
                perfect_active="λέλυκα",
                perfect_middle="λέλυμαι",
                aorist_passive="ἐλύθην",
            ),
            source="lsj",
        )
        assert entry.format_principal_parts() == "λύω, λύσω, ἔλυσα, λέλυκα, λέλυμαι, ἐλύθην"

    def test_format_principal_parts_latin_legacy(self):
        """format_principal_parts includes conjugation for Latin (legacy)."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            conjugation=1,
            principal_parts=["amāvī", "amātum"],
            source="whitakers",
        )
        assert entry.format_principal_parts() == "amāvī, amātum (1)"

    def test_format_principal_parts_without_conjugation(self):
        """format_principal_parts works without conjugation number (legacy)."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            principal_parts=["amāvī", "amātum"],
            source="whitakers",
        )
        assert entry.format_principal_parts(include_conjugation=False) == "amāvī, amātum"

    def test_format_principal_parts_greek_legacy(self):
        """format_principal_parts works for Greek (no conjugation, legacy)."""
        entry = NormalizedLexicalEntry(
            headword="λύω",
            lemma="λυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            principal_parts=["λύσω", "ἔλυσα", "λέλυκα"],
            source="lsj",
        )
        assert entry.format_principal_parts() == "λύσω, ἔλυσα, λέλυκα"

    def test_format_principal_parts_none(self):
        """format_principal_parts returns None when no parts."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            source="whitakers",
        )
        assert entry.format_principal_parts() is None

    def test_get_deponent_note_deponent(self):
        """get_deponent_note returns 'deponent' for deponent verbs."""
        entry = NormalizedLexicalEntry(
            headword="sequor",
            lemma="sequor",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            verb_voice=VerbVoice.DEPONENT,
            source="whitakers",
        )
        assert entry.get_deponent_note() == "deponent"

    def test_get_deponent_note_semi(self):
        """get_deponent_note returns 'semi-deponent' for semi-deponent verbs."""
        entry = NormalizedLexicalEntry(
            headword="audeō",
            lemma="audeo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            verb_voice=VerbVoice.SEMI_DEPONENT,
            source="whitakers",
        )
        assert entry.get_deponent_note() == "semi-deponent"

    def test_get_deponent_note_none(self):
        """get_deponent_note returns None for non-deponent verbs."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            verb_voice=VerbVoice.ACTIVE,
            source="whitakers",
        )
        assert entry.get_deponent_note() is None


class TestDisplayMappings:
    """Test display mapping functions."""

    def test_pos_display_map_complete(self):
        """All POS values have display mappings."""
        for pos in PartOfSpeech:
            assert pos in POS_DISPLAY_MAP

    def test_gender_display_map_complete(self):
        """All Gender values have display mappings."""
        for gender in Gender:
            assert gender in GENDER_DISPLAY_MAP

    def test_voice_display_map_complete(self):
        """All VerbVoice values have display mappings."""
        for voice in VerbVoice:
            assert voice in VOICE_DISPLAY_MAP

    def test_greek_verb_class_display_map_complete(self):
        """All GreekVerbClass values have display mappings."""
        for verb_class in GreekVerbClass:
            assert verb_class in GREEK_VERB_CLASS_DISPLAY_MAP

    def test_get_pos_display(self):
        """get_pos_display returns correct abbreviations."""
        assert get_pos_display(PartOfSpeech.VERB) == "v."
        assert get_pos_display(PartOfSpeech.ADJECTIVE) == "adj."
        assert get_pos_display(PartOfSpeech.NOUN) is None  # Uses gender instead

    def test_get_gender_display(self):
        """get_gender_display returns correct abbreviations."""
        assert get_gender_display(Gender.MASCULINE) == "m."
        assert get_gender_display(Gender.FEMININE) == "f."
        assert get_gender_display(Gender.NEUTER) == "n."

    def test_get_greek_article(self):
        """get_greek_article returns correct articles."""
        assert get_greek_article(Gender.MASCULINE) == "ὁ"
        assert get_greek_article(Gender.FEMININE) == "ἡ"
        assert get_greek_article(Gender.NEUTER) == "τό"
        assert get_greek_article(Gender.COMMON) is None
        assert get_greek_article(Gender.UNKNOWN) is None

    def test_get_voice_display(self):
        """get_voice_display returns correct abbreviations."""
        assert get_voice_display(VerbVoice.ACTIVE) is None  # Default, not shown
        assert get_voice_display(VerbVoice.PASSIVE) == "pass."
        assert get_voice_display(VerbVoice.MIDDLE) == "mid."
        assert get_voice_display(VerbVoice.DEPONENT) == "dep."
        assert get_voice_display(VerbVoice.SEMI_DEPONENT) == "semi-dep."

    def test_get_greek_verb_class_display(self):
        """get_greek_verb_class_display returns correct strings."""
        assert get_greek_verb_class_display(GreekVerbClass.OMEGA) is None  # Default
        assert get_greek_verb_class_display(GreekVerbClass.MI) == "-μι"
        assert get_greek_verb_class_display(GreekVerbClass.CONTRACT_ALPHA) == "contr. (-άω)"
        assert get_greek_verb_class_display(GreekVerbClass.CONTRACT_EPSILON) == "contr. (-έω)"


class TestSerialization:
    """Test model serialization and deserialization."""

    def test_dict_serialization(self):
        """Entry serializes to dict correctly."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["earth"],
            gender=Gender.FEMININE,
            source="whitakers",
        )
        d = entry.model_dump()
        assert d["headword"] == "terra"
        assert d["language"] == "latin"
        assert d["pos"] == "noun"
        assert d["gender"] == "f"

    def test_dict_serialization_with_verb_fields(self):
        """Entry with verb fields serializes correctly."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            verb_voice=VerbVoice.ACTIVE,
            conjugation=1,
            source="whitakers",
        )
        d = entry.model_dump()
        assert d["verb_voice"] == "active"
        assert d["conjugation"] == 1

    def test_json_round_trip(self):
        """Entry survives JSON round-trip."""
        entry = NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to love"],
            conjugation=1,
            principal_parts=["amāvī", "amātum"],
            source="whitakers",
            confidence=0.9,
        )
        json_str = entry.model_dump_json()
        restored = NormalizedLexicalEntry.model_validate_json(json_str)
        assert restored.headword == entry.headword
        assert restored.principal_parts == entry.principal_parts
        assert restored.confidence == entry.confidence

    def test_json_round_trip_with_structured_parts(self):
        """Entry with structured principal parts survives JSON round-trip."""
        entry = NormalizedLexicalEntry(
            headword="λύω",
            lemma="λυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to loose"],
            verb_voice=VerbVoice.ACTIVE,
            greek_verb_class=GreekVerbClass.OMEGA,
            greek_principal_parts=GreekPrincipalParts(
                present="λύω",
                future="λύσω",
                aorist="ἔλυσα",
            ),
            source="lsj",
        )
        json_str = entry.model_dump_json()
        restored = NormalizedLexicalEntry.model_validate_json(json_str)
        assert restored.greek_verb_class == "omega"
        # After JSON round-trip, nested model is restored as dict due to use_enum_values
        assert restored.greek_principal_parts.present == "λύω"
        assert restored.greek_principal_parts.future == "λύσω"


class TestLatinStemType:
    """Test Latin stem type enum (Morpheus stemtype parity)."""

    def test_first_declension_types(self):
        """First declension stem types are defined."""
        assert LatinStemType.A_AE.value == "a_ae"
        assert LatinStemType.A_AE_GREEK.value == "a_ae_greek"

    def test_second_declension_types(self):
        """Second declension stem types are defined."""
        assert LatinStemType.US_I.value == "us_i"
        assert LatinStemType.ER_RI.value == "er_ri"
        assert LatinStemType.ER_I.value == "er_i"
        assert LatinStemType.UM_I.value == "um_i"
        assert LatinStemType.IUS_II.value == "ius_ii"
        assert LatinStemType.OS_OU_GREEK.value == "os_ou_greek"

    def test_third_declension_consonant_types(self):
        """Third declension consonant stem types are defined."""
        assert LatinStemType.CONS_STEM.value == "cons_stem"
        assert LatinStemType.X_CIS.value == "x_cis"
        assert LatinStemType.S_RIS.value == "s_ris"
        assert LatinStemType.S_TIS.value == "s_tis"
        assert LatinStemType.N_NIS.value == "n_nis"

    def test_third_declension_i_stems(self):
        """Third declension i-stem types are defined."""
        assert LatinStemType.I_STEM_PURE.value == "i_stem_pure"
        assert LatinStemType.I_STEM_MIXED.value == "i_stem_mixed"
        assert LatinStemType.I_STEM_NEUTER.value == "i_stem_neut"

    def test_fourth_fifth_declension(self):
        """Fourth and fifth declension stem types are defined."""
        assert LatinStemType.US_US.value == "us_us"
        assert LatinStemType.U_US.value == "u_us"
        assert LatinStemType.ES_EI.value == "es_ei"


class TestGreekStemType:
    """Test Greek stem type enum (Morpheus stemtype parity)."""

    def test_first_declension_types(self):
        """First declension (alpha/eta) stem types are defined."""
        assert GreekStemType.A_AS.value == "a_as"
        assert GreekStemType.A_ES.value == "a_es"
        assert GreekStemType.E_ES.value == "e_es"
        assert GreekStemType.A_MIXED.value == "a_mixed"

    def test_second_declension_types(self):
        """Second declension (omicron) stem types are defined."""
        assert GreekStemType.OS_OU.value == "os_ou"
        assert GreekStemType.ON_OU.value == "on_ou"
        assert GreekStemType.OS_OU_CONTRACT.value == "os_ou_contr"

    def test_third_declension_consonant_types(self):
        """Third declension consonant stem types are defined."""
        assert GreekStemType.CONS_STEM.value == "cons_stem"
        assert GreekStemType.K_KOS.value == "k_kos"
        assert GreekStemType.P_POS.value == "p_pos"
        assert GreekStemType.T_TOS.value == "t_tos"
        assert GreekStemType.N_NOS.value == "n_nos"
        assert GreekStemType.NT_NTOS.value == "nt_ntos"
        assert GreekStemType.R_ROS.value == "r_ros"
        assert GreekStemType.S_EOS.value == "s_eos"

    def test_third_declension_vowel_types(self):
        """Third declension vowel/diphthong stem types are defined."""
        assert GreekStemType.EUS_EOS.value == "eus_eos"
        assert GreekStemType.IS_EOS.value == "is_eos"
        assert GreekStemType.US_EOS.value == "us_eos"
        assert GreekStemType.I_STEM.value == "i_stem"

    def test_irregular_type(self):
        """Irregular stem type is defined."""
        assert GreekStemType.IRREGULAR.value == "irregular"


class TestGreekDialect:
    """Test Greek dialect enum."""

    def test_all_dialect_values(self):
        """All dialect values are defined correctly."""
        assert GreekDialect.ATTIC.value == "attic"
        assert GreekDialect.IONIC.value == "ionic"
        assert GreekDialect.HOMERIC.value == "homeric"
        assert GreekDialect.DORIC.value == "doric"
        assert GreekDialect.AEOLIC.value == "aeolic"
        assert GreekDialect.KOINE.value == "koine"
        assert GreekDialect.EPIC.value == "epic"


class TestMorpheusParityFields:
    """Test Morpheus-parity fields on NormalizedLexicalEntry."""

    def test_stem_suffix_fields(self):
        """Can set stem and suffix for morphological decomposition."""
        entry = NormalizedLexicalEntry(
            headword="λόγος",
            lemma="λογος",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            stem="λογ",
            suffix="ος",
            source="morpheus",
        )
        assert entry.stem == "λογ"
        assert entry.suffix == "ος"

    def test_latin_stem_type_field(self):
        """Can set Latin stem type."""
        entry = NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            gender=Gender.FEMININE,
            declension=1,
            latin_stem_type=LatinStemType.A_AE,
            stem="terr",
            suffix="a",
            source="morpheus",
        )
        assert entry.latin_stem_type == "a_ae"

    def test_greek_stem_type_field(self):
        """Can set Greek stem type."""
        entry = NormalizedLexicalEntry(
            headword="λόγος",
            lemma="λογος",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            gender=Gender.MASCULINE,
            declension=2,
            greek_stem_type=GreekStemType.OS_OU,
            stem="λογ",
            suffix="ος",
            source="morpheus",
        )
        assert entry.greek_stem_type == "os_ou"

    def test_dialect_field(self):
        """Can set Greek dialect."""
        entry = NormalizedLexicalEntry(
            headword="μῆνιν",
            lemma="μηνις",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            dialect=GreekDialect.HOMERIC,
            source="lsj",
        )
        assert entry.dialect == "homeric"

    def test_latin_third_declension_i_stem(self):
        """Can represent Latin third declension i-stem."""
        entry = NormalizedLexicalEntry(
            headword="turris",
            lemma="turris",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            gender=Gender.FEMININE,
            declension=3,
            genitive="-is",
            latin_stem_type=LatinStemType.I_STEM_PURE,
            stem="turr",
            suffix="is",
            source="whitakers",
        )
        assert entry.latin_stem_type == "i_stem_pure"
        assert entry.declension == 3

    def test_greek_third_declension_dental_stem(self):
        """Can represent Greek third declension dental stem."""
        entry = NormalizedLexicalEntry(
            headword="χάρις",
            lemma="χαρις",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            gender=Gender.FEMININE,
            declension=3,
            genitive="-ιτος",
            greek_stem_type=GreekStemType.T_TOS,
            stem="χαριτ",
            suffix="ς",
            source="morpheus",
        )
        assert entry.greek_stem_type == "t_tos"

    def test_json_round_trip_with_morpheus_fields(self):
        """Entry with Morpheus-parity fields survives JSON round-trip."""
        entry = NormalizedLexicalEntry(
            headword="λόγος",
            lemma="λογος",
            language=Language.GREEK,
            pos=PartOfSpeech.NOUN,
            senses=["word", "speech"],
            gender=Gender.MASCULINE,
            declension=2,
            greek_stem_type=GreekStemType.OS_OU,
            stem="λογ",
            suffix="ος",
            dialect=GreekDialect.ATTIC,
            source="morpheus",
        )
        json_str = entry.model_dump_json()
        restored = NormalizedLexicalEntry.model_validate_json(json_str)
        assert restored.greek_stem_type == "os_ou"
        assert restored.stem == "λογ"
        assert restored.suffix == "ος"
        assert restored.dialect == "attic"


class TestPOSOrdering:
    """Test POS ordering for Morpheus parity."""

    def test_pos_order_map_complete(self):
        """All POS values have ordering."""
        for pos in PartOfSpeech:
            assert pos in POS_ORDER_MAP

    def test_pos_order_values(self):
        """POS ordering follows expected hierarchy."""
        assert POS_ORDER_MAP[PartOfSpeech.NOUN] < POS_ORDER_MAP[PartOfSpeech.VERB]
        assert POS_ORDER_MAP[PartOfSpeech.VERB] < POS_ORDER_MAP[PartOfSpeech.ADJECTIVE]
        assert POS_ORDER_MAP[PartOfSpeech.UNKNOWN] == 99

    def test_get_pos_order(self):
        """get_pos_order returns correct values."""
        assert get_pos_order(PartOfSpeech.NOUN) == 1
        assert get_pos_order(PartOfSpeech.VERB) == 2
        assert get_pos_order(PartOfSpeech.ADJECTIVE) == 3
        assert get_pos_order(PartOfSpeech.UNKNOWN) == 99


class TestDialectDisplay:
    """Test dialect display mappings."""

    def test_dialect_display_map_complete(self):
        """All dialect values have display mappings."""
        for dialect in GreekDialect:
            assert dialect in DIALECT_DISPLAY_MAP

    def test_dialect_display_values(self):
        """Dialect display abbreviations are correct."""
        assert DIALECT_DISPLAY_MAP[GreekDialect.ATTIC] is None  # Standard, no marking
        assert DIALECT_DISPLAY_MAP[GreekDialect.IONIC] == "Ion."
        assert DIALECT_DISPLAY_MAP[GreekDialect.HOMERIC] == "Hom."
        assert DIALECT_DISPLAY_MAP[GreekDialect.DORIC] == "Dor."
        assert DIALECT_DISPLAY_MAP[GreekDialect.AEOLIC] == "Aeol."
        assert DIALECT_DISPLAY_MAP[GreekDialect.KOINE] == "Koine"
        assert DIALECT_DISPLAY_MAP[GreekDialect.EPIC] == "epic"

    def test_get_dialect_display(self):
        """get_dialect_display returns correct values."""
        assert get_dialect_display(GreekDialect.ATTIC) is None
        assert get_dialect_display(GreekDialect.HOMERIC) == "Hom."
        assert get_dialect_display(GreekDialect.IONIC) == "Ion."
