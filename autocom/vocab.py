import json
import re
from collections import Counter
from dataclasses import dataclass
from itertools import chain
from typing import Dict, List, Tuple, Union

from cltk.alphabet.lat import dehyphenate, drop_latin_punctuation, normalize_lat
from cltk.lemmatize.lat import LatinBackoffLemmatizer
from cltk.ner.ner import tag_ner
from cltk.sentence.lat import LatinPunktSentenceTokenizer
from tqdm import tqdm


@dataclass
class ProcessedText:
    title: str
    raw_text: str
    clean_text: str
    lemmata: List[Tuple[str, str]]
    lemmata_frequencies: Dict[str, int]


class CorpusAnalytics:
    def __init__(self, lang, lemmatizer_type):
        self.lang = lang
        self.lemmatizer_type = lemmatizer_type
        if lang == "lat":
            self.sent_tokenizer = LatinPunktSentenceTokenizer()
            if lemmatizer_type == "cltk":
                self.lemmatizer = LatinBackoffLemmatizer()
                with open("autocom/exceptions.json") as f:
                    self.lemma_exceptions = json.loads(f.read())
                self.exclude_list = ["aeeumlre", "aeumlre", "ltcibusgt"]
            else:
                raise NotImplementedError()
        else:
            raise NotImplementedError()

    @staticmethod
    def clean_text(text: str, lower: bool = False) -> str:
        """
        Remove extra punctuation and white space.
        Optionally lower case text
        :param text: raw text
        :param lower: whether to lower case text
        :return: clean text
        """
        # Normalize orthography
        text = normalize_lat(
            text,
            drop_accents=True,
            drop_macrons=True,
            jv_replacement=True,
            ligature_replacement=True,
        )
        # Remove non end of sentence punctuation
        punc_pattern = re.compile("[^a-zA-Z.?!\s]")
        clean_text = punc_pattern.sub("", text)
        # Remove duplicate white space
        duplicate_white_space_pattern = re.compile("\s\s+")
        clean_text = duplicate_white_space_pattern.sub(" ", clean_text).strip()
        # Replace non period end of sentence punc with period
        eos_pattern = re.compile("[!?]")
        clean_text = eos_pattern.sub(".", clean_text)
        if lower:
            return clean_text.lower()
        return clean_text

    @staticmethod
    def is_numeral(token: str) -> bool:
        pattern = r"^(?![vV]im|[dD][īi]c[īi])*[IīVXLCDMiīvxlcdm]*(?<!vix)$"  # matches all numerals except vix
        match = re.search(pattern, token)
        return bool(match)

    def clean_lemma(self, token) -> Union[str, None]:
        if token in self.exclude_list or self.is_numeral(token):
            return None
        if self.lemmatizer_type == "cltk":
            # Return None if should exclude token
            if "lr" in token:
                return None
            # Remove enclitic -que from lemma
            que_include = [
                "usque",
                "denique",
                "itaque",
                "uterque",
                "ubique",
                "undique",
                "utique",
                "utrimque",
                "plerique",
            ]
            if token[-3:] == "que" and token not in que_include:
                token = token[:-3]
            # Remove enclitic -ve
            vowels = ["a", "e", "i", "o", "u", "y"]
            if (
                len(token) > 2
                and token[-3:] != "que"
                and (
                    token[-2:] == "ve"
                    or (token[-2:] == "ue" and token[-3] not in vowels)
                )
            ):
                token = token[:-2]
        # Normalize and return token
        token = normalize_lat(
            token,
            drop_accents=True,
            drop_macrons=True,
            jv_replacement=True,
            ligature_replacement=True,
        )
        token = dehyphenate(token)
        token = drop_latin_punctuation(token)
        if token in self.lemma_exceptions:
            return self.lemma_exceptions[token]
        return token.strip().lower()

    def lemmata_freq(self, lemmata: List[Tuple[str, str]]) -> Dict[str, int]:
        """
        Collate lemmata for vocab frequency.
        Reduces secondary definitions to single lemma. E.g., all "cum2" counts are under "cum".
        :param lemmata: list of lemmata tuples
        :return: dict of lemmata frequency
        """
        lemmata = [
            l[1] for l in lemmata if len(l[1]) > 0
        ]  # TODO: pull out and put in process_text
        clean_lemmata = [self.clean_lemma(l) for l in lemmata]
        freq_dict_temp = dict(Counter(clean_lemmata))
        freq_dict = {}
        only_alphabetic_pattern = re.compile("[^a-z]")
        for k, v in freq_dict_temp.items():
            if k is None:
                continue
            # Check if lemma has any punctuation and reduce, e.g. con-vero -> convero
            elif (
                only_alphabetic_pattern.sub("", k) != k
                and only_alphabetic_pattern.sub("", k) is not None
            ):
                try:
                    freq_dict[only_alphabetic_pattern.sub("", k)] += v
                except KeyError:
                    freq_dict[only_alphabetic_pattern.sub("", k)] = v
            else:
                try:
                    freq_dict[k] += v
                except KeyError:
                    freq_dict[k] = v
        return freq_dict

    def ner_tagger(self, text: str, use_spacy=True) -> List[Tuple[str, bool]]:
        """
        Tag named entities in text.
        :param text: text
        :param use_spacy: flag to use Spacy NER tagger. Note that it runs slowly.
        :return: list of booleans - true indicates named entity
        """
        sentences = self.sent_tokenizer.tokenize(text)
        tagged_sentences = []
        for sentence in sentences:
            tokens = sentence.split(" ")
            if use_spacy:
                cltk_ner_tags = tag_ner(iso_code="lat", input_tokens=tokens)
            else:
                cltk_ner_tags = tokens
            ner_tags = []
            for i in range(len(cltk_ner_tags)):
                if i == 0:
                    ner_tags.append((tokens[i], cltk_ner_tags[i] == True))
                elif tokens[i][0].isupper():
                    ner_tags.append((tokens[i], True))
                else:
                    ner_tags.append((tokens[i], cltk_ner_tags[i] == True))
            tagged_sentences.append(ner_tags)
        tagged_text = list(chain.from_iterable(tagged_sentences))
        return tagged_text

    def process_text(self, text: str, filter_ner=True) -> ProcessedText:
        """
        Collates text, clean text, lemmata, and lemmata frequencies for text.
        :param text: raw Latin Library text
        :param filter_ner: filter proper nouns from text
        :return: processed Latin Library text
        """
        clean_text = self.clean_text(text, lower=True)
        text_title = text.split("\n")[0]
        only_alphabetic_pattern = re.compile("[^a-z]")
        clean_tokens = [
            only_alphabetic_pattern.sub("", t) for t in clean_text.split(" ")
        ]  # Remove punc from tokens
        if self.lemmatizer_type == "cltk":
            lemmata = self.lemmatizer.lemmatize(clean_tokens)
        if filter_ner:
            clean_text_ner = self.clean_text(text, lower=False)
            ner_tags = self.ner_tagger(clean_text_ner, use_spacy=False)
            filter_lemmata = [
                t[0] for t in zip(lemmata, ner_tags) if t[1][1] is not True
            ]
            lemmata_frequencies = self.lemmata_freq(filter_lemmata)
        else:
            lemmata_frequencies = self.lemmata_freq(lemmata)
        processed_text = ProcessedText(
            title=text_title,
            raw_text=text,
            clean_text=clean_text,
            lemmata=lemmata,
            lemmata_frequencies=lemmata_frequencies,
        )
        return processed_text


lemmata_analyzer = CorpusAnalytics("lat", lemmatizer_type="cltk")


def get_lemmata_frequencies(text: str) -> Dict[str, int]:
    """
    Get lemmata frequencies for Latin text.
    :param text: Latin text
    :return: lemmata frequencies
    """
    processed_text = lemmata_analyzer.process_text(text)
    return processed_text.lemmata_frequencies


if __name__ == "__main__":
    analyzer = CorpusAnalytics("lat", lemmatizer_type="cltk")
    with open("sample_latin_text.txt", "r") as f:
        text = f.read()
    frequency_dict = get_lemmata_frequencies(text)
    # Save dictionary as pretty JSON
    with open("frequency_dict.json", "w") as f:
        json.dump(frequency_dict, f, indent=4)
