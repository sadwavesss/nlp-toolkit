from __future__ import annotations

import re

from . import nlp
from .db import get_db


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def max_typos(word: str) -> int:
    return 1 if len(word) <= 4 else 2 if len(word) <= 8 else 3


def _vocabulary() -> list[tuple[str, int]]:
    rows = get_db().execute(
        "SELECT l.lemma AS lemma, COUNT(dl.document_id) AS df "
        "FROM lemmas l JOIN document_lemmas dl ON dl.lemma_id = l.id GROUP BY l.id"
    ).fetchall()
    return [(r["lemma"], r["df"]) for r in rows]


def complete(prefix: str, limit: int = 8) -> list[dict]:
    words = nlp.tokenize(prefix)
    if not words or len(words[-1]) < 2:
        return []
    prefix = words[-1]
    vocabulary = _vocabulary()

    exact = sorted(((w, df) for w, df in vocabulary if w.startswith(prefix)), key=lambda x: (-x[1], x[0]))
    result = [{"word": w, "documents": df, "fuzzy": False} for w, df in exact[:limit]]

    if len(result) < 3 and len(prefix) >= 5:
        taken = {r["word"] for r in result}
        allowed = 1 if len(prefix) <= 6 else 2
        fuzzy = []
        for w, df in vocabulary:
            if w in taken or w[0] != prefix[0]:
                continue
            distance = min(levenshtein(prefix, w[:n]) for n in (len(prefix) - 1, len(prefix), len(prefix) + 1) if n > 0)
            if distance <= allowed:
                fuzzy.append((distance, -df, w))
        result += [{"word": w, "documents": -df, "fuzzy": True} for _, df, w in sorted(fuzzy)[:limit - len(result)]]
    return result


def correct_word(word: str) -> str | None:
    word = word.lower()
    lemma = nlp.lemmatize_word(word)
    allowed = max_typos(word)
    best = None
    for candidate, df in _vocabulary():
        if abs(len(candidate) - len(lemma)) > allowed and abs(len(candidate) - len(word)) > allowed:
            continue
        distance = min(levenshtein(word, candidate), levenshtein(lemma, candidate))
        if distance <= allowed and (best is None or (distance, -df) < best[:2]):
            best = (distance, -df, candidate)
    return best[2] if best else None


def correct_query(query: str, missing_words: list[str]) -> str | None:
    corrected = query
    for word in missing_words:
        replacement = correct_word(word)
        if replacement:
            corrected = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", replacement, corrected, flags=re.IGNORECASE)
    return corrected if corrected.lower() != query.lower() else None
