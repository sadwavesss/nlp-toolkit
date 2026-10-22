import re
from functools import lru_cache
from typing import Callable, Dict, List, Optional

RUS_WORD_RE = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*")


def _build_nltk_tokenizer():
    try:
        from nltk.tokenize import RegexpTokenizer

        return RegexpTokenizer(RUS_WORD_RE.pattern)
    except Exception:
        return None


def tokenize_russian_words(text: str) -> List[str]:
    tokenizer = _build_nltk_tokenizer()
    if tokenizer is not None:
        return tokenizer.tokenize(text)
    return [m.group(0) for m in RUS_WORD_RE.finditer(text)]


@lru_cache(maxsize=1)
def _build_lemmatizer() -> Optional[Callable[[str], str]]:
    """pymorphy3 if available, otherwise Yandex Mystem; None means no lemmatization."""
    try:
        import pymorphy3

        morph = pymorphy3.MorphAnalyzer()

        def lemmatize(word: str) -> str:
            parses = morph.parse(word)
            return parses[0].normal_form if parses else word

        return lemmatize
    except Exception:
        pass

    try:
        from pymystem3 import Mystem

        mystem = Mystem()
        cache: Dict[str, str] = {}

        def lemmatize(word: str) -> str:
            if word not in cache:
                result = mystem.analyze(word)
                analysis = result[0].get("analysis") if result else None
                cache[word] = (analysis[0].get("lex") if analysis else None) or word
            return cache[word]

        return lemmatize
    except Exception:
        return None


def lemmatize_word(word: str) -> str:
    lemmatize = _build_lemmatizer()
    return lemmatize(word) if lemmatize else word
