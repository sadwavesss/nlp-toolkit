"""Boolean document selection.

A natural-language query is lemmatized and turned into a Boolean expression over the sets of
documents containing each lemma. Query words that are missing from the index are reported to the
user (`missing_words`) instead of being silently dropped.

Grammar (operators in Russian, English or as symbols):
    expr   := term (OR term)*
    term   := factor (AND factor)*
    factor := NOT factor | '(' expr ')' | WORD
    AND    := И | AND | &
    OR     := ИЛИ | OR | '|'
    NOT    := НЕ | NOT | '!'

Without explicit operators all meaningful words are joined with AND (all_words_together) or OR.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import nlp
from .db import get_db

_AND_WORDS = {"и", "and"}
_OR_WORDS = {"или", "or"}
_NOT_WORDS = {"не", "not"}
_OPERATOR_SYMBOLS = {"&", "&&", "|", "||", "!", "(", ")"}

_TOKEN_RE = re.compile(r"\(|\)|&&|\|\||[&|!]|[^\s()]+")


@dataclass
class SelectionResult:
    document_ids: set[int]
    # positive (not negated) query lemmas -> the word typed by the user
    positive_lemmas: dict[str, str] = field(default_factory=dict)
    # query lemmas missing from the index (not in any document)
    missing_words: list[str] = field(default_factory=list)
    used_explicit_operators: bool = False


class DocumentSelector:
    """Select documents that satisfy a Boolean query."""

    def __init__(self, all_words_together: bool = True):
        self.all_words_together = all_words_together

    def select(self, query: str) -> SelectionResult:
        tokens = _TOKEN_RE.findall(query.strip().lower())
        has_operators = any(
            t in _AND_WORDS | _OR_WORDS | _NOT_WORDS | _OPERATOR_SYMBOLS for t in tokens
        )

        positive_lemmas: dict[str, str] = {}
        missing_words: list[str] = []

        if has_operators:
            ast = _Parser(tokens).parse_expr()
        else:
            words = [t for t in tokens if t not in ("(", ")")]
            leaves = []
            for w in words:
                lemma = nlp.lemmatize_word(w) if w not in nlp.STOPWORDS else None
                if lemma is None or lemma in nlp.STOPWORDS:
                    continue
                leaves.append(("WORD", lemma, w))
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
        )

    def _eval(self, node, all_ids, positive_lemmas, missing_words, negated) -> set[int]:
        kind = node[0]
        if kind == "WORD":
            _, lemma, surface = node
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
    """Recursive-descent parser for Boolean expressions."""

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
        """Two words without an explicit operator are joined with AND."""
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
        word = self._advance()
        lemma = nlp.lemmatize_word(word) if word else ""
        return ("WORD", lemma, word or "")


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
