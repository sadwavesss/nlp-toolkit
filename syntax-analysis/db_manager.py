"""SQLite storage for documents, sentences and tokens."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict


class DatabaseManager:

    def __init__(self, db_path: str = "syntax_analysis.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                title TEXT DEFAULT '',
                upload_date TEXT NOT NULL,
                raw_text TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sentences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                lemma TEXT DEFAULT '',
                pos TEXT DEFAULT '',
                pos_ru TEXT DEFAULT '',
                morph TEXT DEFAULT '',
                head_index INTEGER DEFAULT -1,
                deprel TEXT DEFAULT '',
                deprel_ru TEXT DEFAULT '',
                position INTEGER NOT NULL,
                FOREIGN KEY (sentence_id) REFERENCES sentences(id) ON DELETE CASCADE
            );
        """)

        conn.commit()
        conn.close()

    # --- Documents ---

    def add_document(self, filename: str, title: str, raw_text: str) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, title, upload_date, raw_text) VALUES (?, ?, ?, ?)",
            (filename, title, datetime.now().isoformat(), raw_text)
        )
        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return doc_id

    def get_document(self, doc_id: int) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_documents(self) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, title, upload_date FROM documents ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def update_document_title(self, doc_id: int, title: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE documents SET title = ? WHERE id = ?", (title, doc_id))
        conn.commit()
        conn.close()

    # --- Sentences ---

    def add_sentence(self, document_id: int, text: str, position: int) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sentences (document_id, text, position) VALUES (?, ?, ?)",
            (document_id, text, position)
        )
        sent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return sent_id

    def get_sentences(self, document_id: int) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM sentences WHERE document_id = ? ORDER BY position",
            (document_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- Tokens ---

    def add_token(self, sentence_id: int, text: str, lemma: str, pos: str,
                  pos_ru: str, morph: str, head_index: int, deprel: str,
                  deprel_ru: str, position: int) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tokens (sentence_id, text, lemma, pos, pos_ru, morph, head_index, deprel, deprel_ru, position) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sentence_id, text, lemma, pos, pos_ru, morph, head_index, deprel, deprel_ru, position)
        )
        token_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return token_id

    def add_tokens_batch(self, sentence_id: int, tokens: List[Dict]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO tokens (sentence_id, text, lemma, pos, pos_ru, morph, head_index, deprel, deprel_ru, position) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(sentence_id, t["text"], t["lemma"], t["pos"], t.get("pos_ru", ""), t["morph"],
              t["head_index"], t["deprel"], t.get("deprel_ru", ""), t["position"]) for t in tokens]
        )
        conn.commit()
        conn.close()

    def get_tokens(self, sentence_id: int) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tokens WHERE sentence_id = ? ORDER BY position",
            (sentence_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_token(self, token_id: int, **kwargs):
        """Update token fields edited by the user."""
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [token_id]
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tokens SET {sets} WHERE id = ?", values)
        conn.commit()
        conn.close()

    # --- Analytics queries ---

    def get_sentence_with_tokens(self, sentence_id: int) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sentences WHERE id = ?", (sentence_id,))
        sent = cursor.fetchone()
        if not sent:
            conn.close()
            return None
        cursor.execute(
            "SELECT * FROM tokens WHERE sentence_id = ? ORDER BY position",
            (sentence_id,)
        )
        tokens = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return {"sentence": dict(sent), "tokens": tokens}

    def get_document_analysis(self, document_id: int) -> List[Dict]:
        sentences = self.get_sentences(document_id)
        result = []
        for sent in sentences:
            tokens = self.get_tokens(sent["id"])
            result.append({"sentence": sent, "tokens": tokens})
        return result

    def get_deprel_stats(self, document_id: int) -> Dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT t.deprel, COUNT(*) as cnt FROM tokens t "
            "JOIN sentences s ON t.sentence_id = s.id "
            "WHERE s.document_id = ? AND t.deprel != '' "
            "GROUP BY t.deprel ORDER BY cnt DESC",
            (document_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return {r["deprel"]: r["cnt"] for r in rows}

    def get_pos_stats(self, document_id: int) -> Dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT t.pos, COUNT(*) as cnt FROM tokens t "
            "JOIN sentences s ON t.sentence_id = s.id "
            "WHERE s.document_id = ? AND t.pos != '' "
            "GROUP BY t.pos ORDER BY cnt DESC",
            (document_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return {r["pos"]: r["cnt"] for r in rows}
