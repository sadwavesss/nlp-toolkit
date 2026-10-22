DROP TABLE IF EXISTS relevance_judgments;
DROP TABLE IF EXISTS document_lemmas;
DROP TABLE IF EXISTS lemmas;
DROP TABLE IF EXISTS documents;

CREATE TABLE documents (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    text  TEXT NOT NULL,
    date  TEXT NOT NULL,   -- YYYY-MM-DD
    time  TEXT NOT NULL    -- HH:MM:SS
);

CREATE TABLE lemmas (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    lemma TEXT NOT NULL UNIQUE
);

-- обратный (инвертированный) индекс: лемма -> документы, в которых она встречается
CREATE TABLE document_lemmas (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    lemma_id    INTEGER NOT NULL REFERENCES lemmas(id) ON DELETE CASCADE,
    tf          INTEGER NOT NULL,  -- частота леммы в документе (term frequency)
    PRIMARY KEY (document_id, lemma_id)
);

CREATE INDEX idx_document_lemmas_lemma ON document_lemmas (lemma_id);
CREATE INDEX idx_document_lemmas_document ON document_lemmas (document_id);

-- Эталонные оценки релевантности (проставляются экспертом/пользователем
-- вручную) — используются модулем оценки качества (app/metrics.py) для
-- расчёта точности, полноты, F-меры и средней точности (AP).
CREATE TABLE relevance_judgments (
    query       TEXT    NOT NULL,  -- нормализованный текст запроса
    mode        TEXT    NOT NULL,  -- 'and' | 'or' — режим, в котором оценивался запрос
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    relevant    INTEGER NOT NULL,  -- 1 — релевантен, 0 — нерелевантен
    PRIMARY KEY (query, mode, document_id)
);
