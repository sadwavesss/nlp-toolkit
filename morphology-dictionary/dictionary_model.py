from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from nlp_tools import lemmatize_word


@dataclass
class DictionaryEntry:
    wordform: str
    lexeme: str
    freq: int
    morph: str = ""


def build_dictionary(words: Iterable[str], existing_morph: Optional[Dict[str, str]] = None) -> Dict[str, DictionaryEntry]:
    existing_morph = existing_morph or {}
    freq: Dict[str, int] = {}

    for w in words:
        wf = w.lower()
        freq[wf] = freq.get(wf, 0) + 1

    result: Dict[str, DictionaryEntry] = {}
    for wf, c in freq.items():
        lex = lemmatize_word(wf)
        result[wf] = DictionaryEntry(wordform=wf, lexeme=lex, freq=c, morph=existing_morph.get(wf, ""))

    return result
