from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import nlp
from .db import get_db

_AND_WORDS = {"и", "and", "плюс"}
_OR_WORDS = {"или", "or", "либо"}
_NOT_WORDS = {"не", "not", "кроме", "без", "исключая"}
_OPERATOR_SYMBOLS = {"&", "&&", "|", "||", "!", "(", ")"}
_OPERATOR_PHRASES = {
    ("за", "исключением"): "не",
    ("но", "не"): "не",
    ("а", "также"): "и",
    ("вместе", "с"): "и",
}

_TOKEN_RE = re.compile(r"\(|\)|&&|\|\||[&|!]|[а-яёa-z]+")


@dataclass
class SelectionResult:
    document_ids: set[int]
    positive_lemmas: dict[str, str] = field(default_factory=dict)
    missing_words: list[str] = field(default_factory=list)
    used_explicit_operators: bool = False
    expression: str = ""


class DocumentSelector:
    def __init__(self, all_words_together: bool = True):
        self.all_words_together = all_words_together

    def select(self, query: str) -> SelectionResult:
        tokens = _normalize_tokens(_TOKEN_RE.findall(query.strip().lower()))
        has_operators = any(_is_operator(t) for t in tokens)

        positive_lemmas: dict[str, str] = {}
        missing_words: list[str] = []

        if has_operators:
            ast = _Parser(tokens).parse_expr()
        else:
            leaves = [("WORD", nlp.lemmatize_word(w), w) for w in tokens]
            if not leaves:
                return SelectionResult(document_ids=set(), used_explicit_operators=False)
            op = "AND" if self.all_words_together else "OR"
            ast = leaves[0]
            for leaf in leaves[1:]:
                ast = (op, ast, leaf)

        all_ids = _all_document_ids()
        doc_ids = self._eval(ast, all_ids, positive_lemmas, missing_words, negated=False)

        return SelectionResult(
            document_ids=doc_ids,
            positive_lemmas=positive_lemmas,
            missing_words=sorted(set(missing_words)),
            used_explicit_operators=has_operators,
            expression=_describe(ast),
        )

    def _eval(self, node, all_ids, positive_lemmas, missing_words, negated) -> set[int]:
        kind = node[0]
        if kind == "WORD":
            _, lemma, surface = node
            if not surface:
                return set()
            ids = _document_ids_for_lemma(lemma)
            if not ids:
                missing_words.append(surface)
            if not negated:
                positive_lemmas[lemma] = surface
            return ids
        if kind == "AND":
            return self._eval(node[1], all_ids, positive_lemmas, missing_words, negated) & \
                self._eval(node[2], all_ids, positive_lemmas, missing_words, negated)
        if kind == "OR":
            return self._eval(node[1], all_ids, positive_lemmas, missing_words, negated) | \
                self._eval(node[2], all_ids, positive_lemmas, missing_words, negated)
        if kind == "NOT":
            inner = self._eval(node[1], all_ids, positive_lemmas, missing_words, not negated)
            return all_ids - inner
        raise ValueError(f"Неизвестный узел AST: {kind}")


class _Parser:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self) -> str | None:
        tok = self._peek()
        self.pos += 1
        return tok

    def parse_expr(self):
        node = self.parse_term()
        while self._peek() in _OR_WORDS or self._peek() in ("|", "||"):
            self._advance()
            node = ("OR", node, self.parse_term())
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self._peek() is not None and (
            self._peek() in _AND_WORDS or self._peek() in ("&", "&&")
            or self._is_implicit_and_start()
        ):
            if self._peek() in _AND_WORDS or self._peek() in ("&", "&&"):
                self._advance()
            node = ("AND", node, self.parse_factor())
        return node

    def _is_implicit_and_start(self) -> bool:
        tok = self._peek()
        if tok is None:
            return False
        if tok in _OR_WORDS or tok in ("|", "||", ")"):
            return False
        if tok in _AND_WORDS or tok in ("&", "&&"):
            return False
        return True

    def parse_factor(self):
        tok = self._peek()
        if tok in _NOT_WORDS or tok == "!":
            self._advance()
            return ("NOT", self.parse_factor())
        if tok == "(":
            self._advance()
            node = self.parse_expr()
            if self._peek() == ")":
                self._advance()
            return node
        if tok is None or tok == ")" or tok in _BINARY_OPERATORS:
            return ("WORD", "", "")
        word = self._advance()
        return ("WORD", nlp.lemmatize_word(word), word)


_BINARY_OPERATORS = _AND_WORDS | _OR_WORDS | {"&", "&&", "|", "||"}


def _is_operator(token: str) -> bool:
    return token in _BINARY_OPERATORS or token in _NOT_WORDS or token in _OPERATOR_SYMBOLS


def _normalize_tokens(tokens: list[str]) -> list[str]:
    merged, i = [], 0
    while i < len(tokens):
        pair = tuple(tokens[i:i + 2])
        if pair in _OPERATOR_PHRASES:
            merged.append(_OPERATOR_PHRASES[pair])
            i += 2
            continue
        merged.append(tokens[i])
        i += 1

    result: list[str] = []
    for token in merged:
        if not _is_operator(token):
            if token in nlp.STOPWORDS or nlp.lemmatize_word(token) in nlp.STOPWORDS:
                continue
        elif token in _BINARY_OPERATORS and (not result or result[-1] in _BINARY_OPERATORS
                                             or result[-1] in _NOT_WORDS or result[-1] in ("!", "(")):
            continue
        elif token == ")" and result and result[-1] in _BINARY_OPERATORS:
            result.pop()
        result.append(token)

    while result and (result[-1] in _BINARY_OPERATORS or result[-1] in _NOT_WORDS or result[-1] in ("!", "(")):
        result.pop()
    return result


_OPERATOR_NAMES = {"AND": "И", "OR": "ИЛИ"}
_PRECEDENCE = {"OR": 1, "AND": 2, "NOT": 3, "WORD": 4}


def _describe(node, parent: int = 0) -> str:
    kind = node[0]
    if kind == "WORD":
        return node[1]
    precedence = _PRECEDENCE[kind]
    if kind == "NOT":
        text = "НЕ " + _describe(node[1], precedence)
    else:
        text = f"{_describe(node[1], precedence)} {_OPERATOR_NAMES[kind]} {_describe(node[2], precedence)}"
    return f"({text})" if precedence < parent else text


def _all_document_ids() -> set[int]:
    db = get_db()
    rows = db.execute("SELECT id FROM documents").fetchall()
    return {r["id"] for r in rows}


def _document_ids_for_lemma(lemma: str) -> set[int]:
    db = get_db()
    row = db.execute("SELECT id FROM lemmas WHERE lemma = ?", (lemma,)).fetchone()
    if row is None:
        return set()
    rows = db.execute(
        "SELECT document_id FROM document_lemmas WHERE lemma_id = ?", (row["id"],)
    ).fetchall()
    return {r["document_id"] for r in rows}
