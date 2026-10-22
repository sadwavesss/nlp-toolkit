"""Documents and their inverted index (lemma -> term frequency).

Term weights (Aij = Qij * Bi, i.e. TF-IDF) are not used for selection, which is Boolean,
but to rank the selected documents and to evaluate search quality.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from . import nlp
from .db import get_db


@dataclass
class Document:
    title: str
    text: str
    date: str = ""
    time: str = ""
    document_id: int | None = None

    def __post_init__(self):
        now = datetime.now()
        if not self.date:
            self.date = now.strftime("%Y-%m-%d")
        if not self.time:
            self.time = now.strftime("%H:%M:%S")

    # ------------------------------------------------------------------
    # Adding / removing documents
    # ------------------------------------------------------------------
    def add_document_to_base(self) -> bool:
        """Save the document and build its inverted lemma index."""
        if not self.title.strip() or not self.text.strip():
            return False

        db = get_db()
        cur = db.execute(
            "INSERT INTO documents (title, text, date, time) VALUES (?, ?, ?, ?)",
            (self.title, self.text, self.date, self.time),
        )
        self.document_id = cur.lastrowid

        lemmas = nlp.lemmatize_text(self.text)
        frequencies: dict[str, int] = {}
        for lemma in lemmas:
            frequencies[lemma] = frequencies.get(lemma, 0) + 1

        for lemma, tf in frequencies.items():
            lemma_id = _get_or_create_lemma_id(db, lemma)
            db.execute(
                "INSERT INTO document_lemmas (document_id, lemma_id, tf) VALUES (?, ?, ?)",
                (self.document_id, lemma_id, tf),
            )

        db.commit()
        return True

    @staticmethod
    def delete_document_from_base(document_id: int | None) -> bool:
        if document_id is None:
            return False
        db = get_db()
        cur = db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        db.commit()
        return cur.rowcount > 0

    @staticmethod
    def get_all_documents() -> list["Document"]:
        db = get_db()
        rows = db.execute(
            "SELECT id, title, text, date, time FROM documents ORDER BY date DESC, time DESC"
        ).fetchall()
        return [
            Document(title=r["title"], text=r["text"], date=r["date"], time=r["time"], document_id=r["id"])
            for r in rows
        ]

    @staticmethod
    def get_by_id(document_id: int) -> "Document | None":
        db = get_db()
        r = db.execute(
            "SELECT id, title, text, date, time FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if r is None:
            return None
        return Document(title=r["title"], text=r["text"], date=r["date"], time=r["time"], document_id=r["id"])

    # ------------------------------------------------------------------
    # Lemma statistics (IDF, TF-IDF, document vector)
    # ------------------------------------------------------------------
    @staticmethod
    def get_lemm_inverse_frequency(lemm_id: int | None = None, lemm_str: str | None = None) -> tuple[bool, float]:
        """Inverse document frequency of term i: Bi = log10(N / ni)."""
        db = get_db()
        if lemm_id is None:
            if lemm_str is None:
                return False, 0.0
            row = db.execute("SELECT id FROM lemmas WHERE lemma = ?", (lemm_str,)).fetchone()
            if row is None:
                return False, 0.0
            lemm_id = row["id"]

        total_docs = db.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"]
        if total_docs == 0:
            return False, 0.0
        df = db.execute(
            "SELECT COUNT(*) AS c FROM document_lemmas WHERE lemma_id = ?", (lemm_id,)
        ).fetchone()["c"]
        if df == 0:
            return False, 0.0
        b_i = math.log10(total_docs / df)
        return True, b_i

    @staticmethod
    def get_word_weight_in_document(lemm_str: str, document_id: int) -> tuple[bool, float]:
        db = get_db()
        row = db.execute("SELECT id FROM lemmas WHERE lemma = ?", (lemm_str,)).fetchone()
        if row is None:
            return False, 0.0
        return Document.get_lemm_weight_in_document(row["id"], document_id)

    @staticmethod
    def get_lemm_weight_in_document(lemm_id: int, document_id: int) -> tuple[bool, float]:
        """Weight of term i in document j: Aij = Qij * Bi (raw term frequency times IDF)."""
        db = get_db()
        row = db.execute(
            "SELECT tf FROM document_lemmas WHERE lemma_id = ? AND document_id = ?",
            (lemm_id, document_id),
        ).fetchone()
        if row is None:
            return False, 0.0
        q_ij = row["tf"]
        ok, b_i = Document.get_lemm_inverse_frequency(lemm_id=lemm_id)
        if not ok:
            return False, 0.0
        a_ij = q_ij * b_i
        return True, a_ij

    @staticmethod
    def get_document_vector(document_id: int) -> dict[int, float]:
        """Document vector {lemma_id: weight Aij}."""
        db = get_db()
        rows = db.execute(
            "SELECT lemma_id FROM document_lemmas WHERE document_id = ?", (document_id,)
        ).fetchall()
        vector: dict[int, float] = {}
        for r in rows:
            ok, w = Document.get_lemm_weight_in_document(r["lemma_id"], document_id)
            if ok:
                vector[r["lemma_id"]] = w
        return vector


def _get_or_create_lemma_id(db, lemma: str) -> int:
    row = db.execute("SELECT id FROM lemmas WHERE lemma = ?", (lemma,)).fetchone()
    if row is not None:
        return row["id"]
    cur = db.execute("INSERT INTO lemmas (lemma) VALUES (?)", (lemma,))
    return cur.lastrowid
