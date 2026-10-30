import re
import threading

import pymorphy3

_WORD_RE = re.compile(r"[а-яёА-ЯЁa-zA-Z]+")

_analyzer_lock = threading.Lock()
_analyzer: pymorphy3.MorphAnalyzer | None = None

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
    return _WORD_RE.findall(text.lower())


def lemmatize_word(word: str) -> str:
    morph = get_analyzer()
    return morph.parse(word)[0].normal_form


def lemmatize_text(text: str, drop_stopwords: bool = True) -> list[str]:
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
