"""Tokenization and lemmatization of Russian text with pymorphy3.

Both documents and queries are reduced to lemmas, so a query matches any inflected form of a word.
"""
import re
import threading

import pymorphy3

_WORD_RE = re.compile(r"[а-яёА-ЯЁa-zA-Z]+")

_analyzer_lock = threading.Lock()
_analyzer: pymorphy3.MorphAnalyzer | None = None

# Russian stop words: they carry no meaning for full-text search
# and are excluded from both the index and the query.
STOPWORDS = frozenset("""
и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по
только ее мне было вот от меня еще ещё нет о из ему теперь когда даже ну вдруг
ли если или ни быть был него до вас нибудь опять уж вам ведь там потом себя
ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без
будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой
совсем ним здесь этом один почти мой тем чтобы нее ней сейчас были куда зачем
всех никогда можно при наконец два об другой хоть после над больше тот через
эти нас про всего них какая много разве три эту моя впрочем хорошо свою этой
перед иногда лучше чуть том нельзя такой им более всегда конечно всю между
это этому такие также которые который которая которое об для является являются
""".split())


def get_analyzer() -> pymorphy3.MorphAnalyzer:
    global _analyzer
    if _analyzer is None:
        with _analyzer_lock:
            if _analyzer is None:
                _analyzer = pymorphy3.MorphAnalyzer()
    return _analyzer


def tokenize(text: str) -> list[str]:
    """Split text into words (no punctuation or digits)."""
    return _WORD_RE.findall(text.lower())


def lemmatize_word(word: str) -> str:
    """Return the normal form (lemma) of a word."""
    morph = get_analyzer()
    return morph.parse(word)[0].normal_form


def lemmatize_text(text: str, drop_stopwords: bool = True) -> list[str]:
    """Tokenize and lemmatize text, optionally dropping stop words."""
    morph = get_analyzer()
    lemmas = []
    for word in tokenize(text):
        if drop_stopwords and word in STOPWORDS:
            continue
        lemma = morph.parse(word)[0].normal_form
        if drop_stopwords and lemma in STOPWORDS:
            continue
        lemmas.append(lemma)
    return lemmas
