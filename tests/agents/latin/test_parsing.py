import pytest

from src.agents.latin.parsing import LatinParsingTools


@pytest.mark.parametrize(
    "word,lemma",
    [
        ("puellae", "puella"),  # noun
        ("amantis", "amo"),  # adjective
        ("omnis", "omnis"),  # adjective
        ("Ciceronis", "Cicero"),  # proper noun
        ("not_a_word", "not_a_word"),  # not a word
    ],
)
def test_get_lemma(word, lemma):
    """Test the get_lemma method."""
    tools = LatinParsingTools()
    output = tools.get_lemma(word)
    assert output == lemma
