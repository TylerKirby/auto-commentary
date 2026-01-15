"""
Golden output tests for regression prevention.

These tests verify that sample texts produce expected glossary entries.
If a change causes a word to lose its definition or get a wrong lemma,
these tests will catch it.

IMPORTANT: When intentionally changing output (e.g., improving a definition),
update the expected values here. These tests are meant to catch UNINTENDED
changes, not block intentional improvements.
"""

import pytest
from autocom.processing import ingest, analyze, enrich
from autocom.processing.analyze import get_analyzer_for_language
from autocom.processing.lexicon import get_lexicon_for_language


@pytest.mark.regression
class TestLatinGoldenOutput:
    """Verify Latin sample produces expected glossary entries."""

    @pytest.fixture(scope="class")
    def latin_glossary(self):
        """Generate glossary for Latin sample (cached for all tests in class)."""
        text = open("examples/sample_latin_short.txt").read()
        _, lines = ingest.normalize_and_segment(text)

        analyzer = get_analyzer_for_language("latin", prefer_spacy=True)
        lines = analyzer.analyze(lines)
        lines = analyze.disambiguate_sequence(lines)

        freq = enrich.compute_frequency(lines)
        lexicon = get_lexicon_for_language("latin", enable_api_fallbacks=False)
        lines = lexicon.enrich(lines, frequency_map=dict(freq))

        # Build glossary dict: lemma -> (token_text, definition)
        glossary = {}
        for line in lines:
            for tok in line.tokens:
                if tok.is_punct:
                    continue
                if tok.gloss and tok.gloss.best:
                    lemma = tok.analysis.lemma if tok.analysis else tok.text
                    glossary[lemma] = {
                        "text": tok.text,
                        "definition": tok.gloss.best,
                        "headword": tok.gloss.headword,
                    }
        return glossary

    def test_arma_present(self, latin_glossary):
        """The word 'arma' (arms/weapons) must be in glossary."""
        # arma is the first word of the Aeneid - may be capitalized as "Arma"
        arma_entries = [k for k in latin_glossary.keys() if k.lower() in ("arma", "armum")]
        assert len(arma_entries) > 0, f"Expected 'arma' or 'armum' in Latin glossary, got: {list(latin_glossary.keys())[:10]}"
        # Check definition mentions arms/weapons
        entry = latin_glossary[arma_entries[0]]
        assert "arm" in entry["definition"].lower(), \
            f"arma definition should mention 'arms', got: {entry['definition']}"

    def test_vir_present(self, latin_glossary):
        """The word 'vir' (man) should be in glossary."""
        # virumque -> vir
        assert "vir" in latin_glossary, "Expected 'vir' (man) in glossary"
        assert "man" in latin_glossary["vir"]["definition"].lower(), \
            f"vir definition should mention 'man', got: {latin_glossary['vir']['definition']}"

    def test_venio_present(self, latin_glossary):
        """The word 'venio' (to come) should be in glossary."""
        # venit -> venio
        assert "venio" in latin_glossary, "Expected 'venio' (to come) in glossary"

    def test_italia_present(self, latin_glossary):
        """Italia (Italy) should be in glossary."""
        assert "Italia" in latin_glossary, "Expected 'Italia' (Italy) in glossary"

    def test_no_empty_definitions(self, latin_glossary):
        """No glossary entry should have an empty definition."""
        for lemma, entry in latin_glossary.items():
            assert entry["definition"], f"Empty definition for {lemma}"
            assert len(entry["definition"]) > 2, f"Definition too short for {lemma}"


@pytest.mark.regression
@pytest.mark.integration  # Uses API fallbacks for Greek definitions
class TestGreekGoldenOutput:
    """Verify Greek sample produces expected glossary entries."""

    @pytest.fixture(scope="class")
    def greek_glossary(self):
        """Generate glossary for Greek sample (cached for all tests in class)."""
        text = open("examples/sample_greek.txt").read()
        _, lines = ingest.normalize_and_segment(text)

        analyzer = get_analyzer_for_language("greek", prefer_cltk=True)
        lines = analyzer.analyze(lines)
        lines = analyze.disambiguate_sequence(lines)

        freq = enrich.compute_frequency(lines)
        lexicon = get_lexicon_for_language("greek", enable_api_fallbacks=True)
        lines = lexicon.enrich(lines, frequency_map=dict(freq))

        # Build glossary dict: lemma -> (token_text, definition)
        glossary = {}
        for line in lines:
            for tok in line.tokens:
                if tok.is_punct:
                    continue
                if tok.gloss and tok.gloss.best:
                    lemma = tok.analysis.lemma if tok.analysis else tok.text
                    glossary[lemma] = {
                        "text": tok.text,
                        "definition": tok.gloss.best,
                        "headword": tok.gloss.headword,
                    }
        return glossary

    def test_menis_present(self, greek_glossary):
        """μῆνις (wrath) must be in glossary - first word of Iliad."""
        assert "μῆνις" in greek_glossary, "Expected μῆνις (wrath) in Greek glossary"
        assert "wrath" in greek_glossary["μῆνις"]["definition"].lower(), \
            "μῆνις definition should mention 'wrath'"

    def test_aeido_present(self, greek_glossary):
        """ἀείδω (to sing) must be in glossary."""
        assert "ἀείδω" in greek_glossary, "Expected ἀείδω (to sing) in glossary"
        assert "sing" in greek_glossary["ἀείδω"]["definition"].lower(), \
            "ἀείδω definition should mention 'sing'"

    def test_thea_present(self, greek_glossary):
        """θεά (goddess) must be in glossary."""
        assert "θεά" in greek_glossary, "Expected θεά (goddess) in glossary"

    def test_achilles_present(self, greek_glossary):
        """Ἀχιλλεύς (Achilles) must be in glossary."""
        assert "Ἀχιλλεύς" in greek_glossary, "Expected Ἀχιλλεύς (Achilles) in glossary"

    def test_relative_pronoun_correct(self, greek_glossary):
        """ὅς (relative pronoun) should be lemmatized correctly."""
        # This was a bug: ἣ was being lemmatized as ἀποστερέω
        assert "ὅς" in greek_glossary, "Expected ὅς (who/which) in glossary"
        # Should NOT be ἀποστερέω (to rob)
        assert "ἀποστερέω" not in greek_glossary, \
            "ἀποστερέω should NOT be in glossary (wrong lemma for ἣ)"

    def test_myrios_not_myro(self, greek_glossary):
        """μυρίος (countless) should be correct, not μύρω (to flow)."""
        # This was a bug: μυρί' was being lemmatized as μυρίς/μύρω
        assert "μυρίος" in greek_glossary, "Expected μυρίος (countless) in glossary"
        assert "countless" in greek_glossary["μυρίος"]["definition"].lower(), \
            "μυρίος should mean 'countless', not 'flow'"

    def test_de_particle_present(self, greek_glossary):
        """δέ (but/and) particle should be in glossary."""
        assert "δέ" in greek_glossary, "Expected δέ (but/and) in glossary"

    def test_no_empty_definitions(self, greek_glossary):
        """No glossary entry should have an empty definition."""
        for lemma, entry in greek_glossary.items():
            assert entry["definition"], f"Empty definition for {lemma}"
            assert len(entry["definition"]) > 1, f"Definition too short for {lemma}"


@pytest.mark.regression
class TestGlossaryCompleteness:
    """Test that samples have reasonable glossary coverage."""

    def test_latin_sample_coverage(self):
        """Latin sample should have >80% of tokens with definitions."""
        text = open("examples/sample_latin_short.txt").read()
        _, lines = ingest.normalize_and_segment(text)

        analyzer = get_analyzer_for_language("latin", prefer_spacy=True)
        lines = analyzer.analyze(lines)
        lines = analyze.disambiguate_sequence(lines)

        freq = enrich.compute_frequency(lines)
        lexicon = get_lexicon_for_language("latin", enable_api_fallbacks=False)
        lines = lexicon.enrich(lines, frequency_map=dict(freq))

        total = 0
        with_def = 0
        for line in lines:
            for tok in line.tokens:
                if tok.is_punct:
                    continue
                total += 1
                if tok.gloss and tok.gloss.best:
                    with_def += 1

        coverage = with_def / total if total > 0 else 0
        assert coverage >= 0.80, f"Latin coverage {coverage:.1%} is below 80% threshold"

    def test_greek_sample_coverage(self):
        """Greek sample should have >80% of tokens with definitions."""
        text = open("examples/sample_greek.txt").read()
        _, lines = ingest.normalize_and_segment(text)

        analyzer = get_analyzer_for_language("greek", prefer_cltk=True)
        lines = analyzer.analyze(lines)
        lines = analyze.disambiguate_sequence(lines)

        freq = enrich.compute_frequency(lines)
        lexicon = get_lexicon_for_language("greek", enable_api_fallbacks=True)
        lines = lexicon.enrich(lines, frequency_map=dict(freq))

        total = 0
        with_def = 0
        for line in lines:
            for tok in line.tokens:
                if tok.is_punct:
                    continue
                total += 1
                if tok.gloss and tok.gloss.best:
                    with_def += 1

        coverage = with_def / total if total > 0 else 0
        assert coverage >= 0.80, f"Greek coverage {coverage:.1%} is below 80% threshold"
