DROP TABLE IF EXISTS relevance_judgments;
DROP TABLE IF EXISTS document_lemmas;
DROP TABLE IF EXISTS lemmas;
DROP TABLE IF EXISTS documents;

CREATE TABLE documents (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    text  TEXT NOT NULL,
    date  TEXT NOT NULL,
    time  TEXT NOT NULL
);

CREATE TABLE lemmas (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    lemma TEXT NOT NULL UNIQUE
);

CREATE TABLE document_lemmas (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    lemma_id    INTEGER NOT NULL REFERENCES lemmas(id) ON DELETE CASCADE,
    tf          INTEGER NOT NULL,
    PRIMARY KEY (document_id, lemma_id)
);

CREATE INDEX idx_document_lemmas_lemma ON document_lemmas (lemma_id);
CREATE INDEX idx_document_lemmas_document ON document_lemmas (document_id);

CREATE TABLE relevance_judgments (
    query       TEXT    NOT NULL,
    mode        TEXT    NOT NULL,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    relevant    INTEGER NOT NULL,
    PRIMARY KEY (query, mode, document_id)
);
