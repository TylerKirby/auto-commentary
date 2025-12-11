"""Test the LatinParsingTools class."""

import pytest
from autocom.processing.analyze import LatinParsingTools


@pytest.mark.parametrize(
    "word,lemma",
    [
        ("puellae", "puella"),  # noun
        ("amantis", "amor"),  # spaCy interprets as genitive of amor (noun), not participle of amo
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


def test_get_lemma_error_handling(monkeypatch):
    """Test that get_lemma handles malformed lemmatizer output gracefully."""
    tools = LatinParsingTools()

    # Test case 1: empty list returned by lemmatizer
    monkeypatch.setattr(tools.lemmatizer, "lemmatize", lambda x: [])
    with pytest.raises(IndexError):
        tools.get_lemma("test_word")

    # Test case 2: malformed data (missing second element)
    def mock_malformed(x):
        return [["single_element"]]

    monkeypatch.setattr(tools.lemmatizer, "lemmatize", mock_malformed)
    with pytest.raises(IndexError):
        tools.get_lemma("test_word")

    # Test case 3: None returned by lemmatizer
    monkeypatch.setattr(tools.lemmatizer, "lemmatize", lambda x: None)
    with pytest.raises(TypeError):
        tools.get_lemma("test_word")
