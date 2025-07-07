"""
Agent for parsing Latin text using CLTK tools with LLM fallback.
"""

from cltk import NLP
from cltk.lemmatize.lat import LatinBackoffLemmatizer
from cltk.morphology.lat import CollatinusDecliner
from cltk.phonology.lat.phonology import (
    LatinSyllabifier,
    LatinTranscription,
)

# TODO: test get_lemma
# TODO: implement get_morphology
# TODO: implement get_definition
# TODO: implement get_macronization


class LatinParsingTools:
    """
    Collection of CLTK tools for Latin parsing.
    """

    def __init__(self):
        self.nlp = NLP(language="lat", suppress_banner=True)
        self.lemmatizer = LatinBackoffLemmatizer()
        self.decliner = CollatinusDecliner()
        self.transcriber = LatinTranscription()
        self.syllabifier = LatinSyllabifier()

    def get_lemma(self, word: str) -> str:
        """Get the lemma of a word."""
        try:
            return self.lemmatizer.lemmatize([word])[0][1]
        except Exception as e:
            raise e
