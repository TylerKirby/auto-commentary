from collections import namedtuple
from typing import List, NamedTuple

from cltk.lemmatize.latin.backoff import BackoffLatinLemmatizer
from cltk.tokenize.word import WordTokenizer


VocabEntry = namedtuple('VocabEntry', ['word', 'definition', 'frequency'])

latin_word_tokenizer = WordTokenizer('latin')
latin_lemmatizer = BackoffLatinLemmatizer()


def generate_vocab_list(text: str) -> List[NamedTuple]:
    """
    Generate vocab list from text.
    :param text:
    :return:
    """
    tokens = latin_word_tokenizer.tokenize(text)
    lemata = latin_lemmatizer.lemmatize(tokens)
    return []
