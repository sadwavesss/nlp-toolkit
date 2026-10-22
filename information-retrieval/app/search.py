"""Search: Boolean selection (DocumentSelector) followed by TF-IDF cosine-similarity ranking."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .db import get_db
from .document import Document
from .selection import DocumentSelector

SNIPPET_LENGTH = 300


@dataclass
class SearchResult:
    document_id: int
    title: str
    snippet: str
    rank: float
    date: str
    matched_words: list[str] = field(default_factory=list)


class Search:
    def __init__(
        self,
        search_query: str,
        all_words_together: bool = True,
        date_start_string: str = "",
        date_end_string: str = "",
    ):
        self.search_query = search_query
        self.all_words_together = all_words_together
        self.date_start_string = date_start_string
        self.date_end_string = date_end_string
        self.missing_words: list[str] = []
        self.used_explicit_operators = False

    # ------------------------------------------------------------------
    # Ranking (applied on top of Boolean selection)
    # ------------------------------------------------------------------
    def _get_search_query_vector(self, positive_lemmas: dict[str, str]) -> dict[int, float]:
        """Query vector {lemma_id: IDF}; term frequency in short queries is assumed to be 1."""
        db = get_db()
        vector: dict[int, float] = {}
        for lemma in positive_lemmas:
            row = db.execute("SELECT id FROM lemmas WHERE lemma = ?", (lemma,)).fetchone()
            if row is None:
                continue
            ok, idf = Document.get_lemm_inverse_frequency(lemm_id=row["id"])
            if ok:
                vector[row["id"]] = idf
        return vector

    @staticmethod
    def _scalar_product(a: dict[int, float], b: dict[int, float]) -> float:
        common = set(a) & set(b)
        return sum(a[k] * b[k] for k in common)

    @staticmethod
    def _euclidean_norm(a: dict[int, float]) -> float:
        return math.sqrt(sum(v * v for v in a.values()))

    def _rank(self, query_vector: dict[int, float], document_id: int) -> float:
        doc_vector = Document.get_document_vector(document_id)
        numerator = self._scalar_product(query_vector, doc_vector)
        denominator = self._euclidean_norm(query_vector) * self._euclidean_norm(doc_vector)
        if denominator == 0:
            return 0.0
        return numerator / denominator

    # ------------------------------------------------------------------
    # Search results page
    # ------------------------------------------------------------------
    def get_search_result(self) -> list[SearchResult]:
        selector = DocumentSelector(all_words_together=self.all_words_together)
        selection = selector.select(self.search_query)

        self.missing_words = selection.missing_words
        self.used_explicit_operators = selection.used_explicit_operators

        if not selection.document_ids:
            return []

        query_vector = self._get_search_query_vector(selection.positive_lemmas)

        db = get_db()
        placeholders = ",".join("?" * len(selection.document_ids))
        rows = db.execute(
            f"SELECT id, title, text, date, time FROM documents WHERE id IN ({placeholders})",
            tuple(selection.document_ids),
        ).fetchall()

        results: list[SearchResult] = []
        for row in rows:
            if self.date_start_string and row["date"] < self.date_start_string:
                continue
            if self.date_end_string and row["date"] > self.date_end_string:
                continue

            matched_words = self._matched_words(row["text"], selection.positive_lemmas)
            snippet_source = row["text"].strip().replace("\n", " ")
            snippet = snippet_source[:SNIPPET_LENGTH]
            if len(snippet_source) > SNIPPET_LENGTH:
                snippet += "…"

            rank = self._rank(query_vector, row["id"])
            results.append(
                SearchResult(
                    document_id=row["id"],
                    title=row["title"],
                    snippet=snippet,
                    rank=rank,
                    date=row["date"],
                    matched_words=matched_words,
                )
            )

        results.sort(key=lambda r: r.rank, reverse=True)
        return results

    @staticmethod
    def _matched_words(text: str, positive_lemmas: dict[str, str]) -> list[str]:
        from . import nlp

        doc_lemmas = set(nlp.lemmatize_text(text, drop_stopwords=False))
        return [surface for lemma, surface in positive_lemmas.items() if lemma in doc_lemmas]
