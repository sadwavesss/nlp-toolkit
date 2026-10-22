"""SQLite storage for semantic analysis results."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict


class DatabaseManager:

    def __init__(self, db_path: str = "semantic_analysis.db"):
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
                format TEXT DEFAULT '',
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
                morph_ru TEXT DEFAULT '',
                head_index INTEGER DEFAULT -1,
                deprel TEXT DEFAULT '',
                deprel_ru TEXT DEFAULT '',
                position INTEGER NOT NULL,
                FOREIGN KEY (sentence_id) REFERENCES sentences(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS named_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                label TEXT DEFAULT '',
                label_ru TEXT DEFAULT '',
                start_token INTEGER DEFAULT 0,
                end_token INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                FOREIGN KEY (sentence_id) REFERENCES sentences(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS semantic_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                role TEXT DEFAULT '',
                role_ru TEXT DEFAULT '',
                predicate_token_id INTEGER DEFAULT NULL,
                FOREIGN KEY (token_id) REFERENCES tokens(id) ON DELETE CASCADE,
                FOREIGN KEY (predicate_token_id) REFERENCES tokens(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS word_senses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                sense TEXT DEFAULT '',
                sense_ru TEXT DEFAULT '',
                synset TEXT DEFAULT '',
                hypernym TEXT DEFAULT '',
                hypernym_ru TEXT DEFAULT '',
                FOREIGN KEY (token_id) REFERENCES tokens(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS semantic_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                subject_entity TEXT DEFAULT '',
                subject_type TEXT DEFAULT '',
                relation TEXT DEFAULT '',
                relation_ru TEXT DEFAULT '',
                object_entity TEXT DEFAULT '',
                object_type TEXT DEFAULT '',
                confidence REAL DEFAULT 1.0,
                FOREIGN KEY (sentence_id) REFERENCES sentences(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sentiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_id INTEGER NOT NULL,
                label TEXT DEFAULT '',
                label_ru TEXT DEFAULT '',
                score REAL DEFAULT 0.0,
                FOREIGN KEY (sentence_id) REFERENCES sentences(id) ON DELETE CASCADE
            );
        """)

        conn.commit()
        conn.close()

    # --- Documents ---

    def add_document(self, filename: str, title: str, fmt: str, raw_text: str) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, title, format, upload_date, raw_text) VALUES (?, ?, ?, ?, ?)",
            (filename, title, fmt, datetime.now().isoformat(), raw_text)
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
        cursor.execute("SELECT id, filename, title, format, upload_date FROM documents ORDER BY id DESC")
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

    def add_tokens_batch(self, sentence_id: int, tokens: List[Dict]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO tokens (sentence_id, text, lemma, pos, pos_ru, morph, morph_ru, "
            "head_index, deprel, deprel_ru, position) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(sentence_id, t["text"], t["lemma"], t["pos"], t.get("pos_ru", ""),
              t.get("morph", ""), t.get("morph_ru", ""),
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
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [token_id]
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tokens SET {sets} WHERE id = ?", values)
        conn.commit()
        conn.close()

    # --- Named entities ---

    def add_named_entities_batch(self, sentence_id: int, entities: List[Dict]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO named_entities (sentence_id, text, label, label_ru, start_token, end_token, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(sentence_id, e["text"], e["label"], e.get("label_ru", ""),
              e.get("start_token", 0), e.get("end_token", 0), e.get("description", ""))
             for e in entities]
        )
        conn.commit()
        conn.close()

    def get_named_entities(self, sentence_id: int) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM named_entities WHERE sentence_id = ? ORDER BY start_token",
            (sentence_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- Semantic roles ---

    def add_semantic_roles_batch(self, roles: List[Dict]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO semantic_roles (token_id, role, role_ru, predicate_token_id) VALUES (?, ?, ?, ?)",
            [(r["token_id"], r["role"], r.get("role_ru", ""), r.get("predicate_token_id"))
             for r in roles]
        )
        conn.commit()
        conn.close()

    def get_semantic_roles_for_sentence(self, sentence_id: int) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sr.*, t.text as token_text, t.position as token_position, "
            "pt.text as predicate_text, pt.position as predicate_position "
            "FROM semantic_roles sr "
            "JOIN tokens t ON sr.token_id = t.id "
            "LEFT JOIN tokens pt ON sr.predicate_token_id = pt.id "
            "WHERE t.sentence_id = ? ORDER BY t.position",
            (sentence_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- Word meanings ---

    def add_word_senses_batch(self, senses: List[Dict]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO word_senses (token_id, sense, sense_ru, synset, hypernym, hypernym_ru) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(s["token_id"], s.get("sense", ""), s.get("sense_ru", ""),
              s.get("synset", ""), s.get("hypernym", ""), s.get("hypernym_ru", ""))
             for s in senses]
        )
        conn.commit()
        conn.close()

    def get_word_senses_for_sentence(self, sentence_id: int) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ws.*, t.text as token_text, t.position as token_position "
            "FROM word_senses ws "
            "JOIN tokens t ON ws.token_id = t.id "
            "WHERE t.sentence_id = ? ORDER BY t.position",
            (sentence_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- Semantic relations ---

    def add_relations_batch(self, sentence_id: int, relations: List[Dict]):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO semantic_relations (sentence_id, subject_entity, subject_type, "
            "relation, relation_ru, object_entity, object_type, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(sentence_id, r["subject"], r.get("subject_type", ""), r["relation"],
              r.get("relation_ru", ""), r["object"], r.get("object_type", ""), r.get("confidence", 1.0))
             for r in relations]
        )
        conn.commit()
        conn.close()

    def get_relations(self, sentence_id: int) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM semantic_relations WHERE sentence_id = ? ORDER BY confidence DESC",
            (sentence_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --- Sentiment ---

    def add_sentiment(self, sentence_id: int, label: str, label_ru: str, score: float):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sentiment (sentence_id, label, label_ru, score) VALUES (?, ?, ?, ?)",
            (sentence_id, label, label_ru, score)
        )
        conn.commit()
        conn.close()

    def get_sentiment(self, sentence_id: int) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM sentiment WHERE sentence_id = ?",
            (sentence_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # --- Analytics queries ---

    def get_document_analysis(self, doc_id: int) -> List[Dict]:
        sentences = self.get_sentences(doc_id)
        result = []
        for sent in sentences:
            tokens = self.get_tokens(sent["id"])
            entities = self.get_named_entities(sent["id"])
            roles = self.get_semantic_roles_for_sentence(sent["id"])
            senses = self.get_word_senses_for_sentence(sent["id"])
            relations = self.get_relations(sent["id"])
            sentiment = self.get_sentiment(sent["id"])
            result.append({
                "sentence": sent,
                "tokens": tokens,
                "entities": entities,
                "roles": roles,
                "senses": senses,
                "relations": relations,
                "sentiment": sentiment,
            })
        return result

    def get_entity_stats(self, doc_id: int) -> Dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ne.label_ru, COUNT(*) as cnt FROM named_entities ne "
            "JOIN sentences s ON ne.sentence_id = s.id "
            "WHERE s.document_id = ? GROUP BY ne.label_ru ORDER BY cnt DESC",
            (doc_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return {r["label_ru"]: r["cnt"] for r in rows}

    def get_role_stats(self, doc_id: int) -> Dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sr.role_ru, COUNT(*) as cnt FROM semantic_roles sr "
            "JOIN tokens t ON sr.token_id = t.id "
            "JOIN sentences s ON t.sentence_id = s.id "
            "WHERE s.document_id = ? GROUP BY sr.role_ru ORDER BY cnt DESC",
            (doc_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return {r["role_ru"]: r["cnt"] for r in rows}

    def get_pos_stats(self, doc_id: int) -> Dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT t.pos_ru, COUNT(*) as cnt FROM tokens t "
            "JOIN sentences s ON t.sentence_id = s.id "
            "WHERE s.document_id = ? GROUP BY t.pos_ru ORDER BY cnt DESC",
            (doc_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return {r["pos_ru"]: r["cnt"] for r in rows}

    def get_deprel_stats(self, doc_id: int) -> Dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT t.deprel_ru, COUNT(*) as cnt FROM tokens t "
            "JOIN sentences s ON t.sentence_id = s.id "
            "WHERE s.document_id = ? GROUP BY t.deprel_ru ORDER BY cnt DESC",
            (doc_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return {r["deprel_ru"]: r["cnt"] for r in rows}
