# Information Retrieval System

Search engine for a base of Russian documents with Boolean query processing, TF-IDF ranking and
search quality evaluation.

## How it works

1. **Indexing.** Each document is tokenized and lemmatized with pymorphy3; stop words are dropped and an
   inverted index `lemma -> (document, term frequency)` is stored in SQLite.
2. **Selection.** The query is lemmatized as well, so it matches any inflected form ("договоры" finds "договора").
   A recursive-descent parser supports `И / AND / &`, `ИЛИ / OR / |`, `НЕ / NOT / !` and brackets, as well as
   natural-language operators (`кроме`, `без`, `за исключением`, `либо`, `вместе с`); the parsed expression is
   shown above the results. Without operators, words are joined with AND or OR depending on the selected mode.
   Words that do not occur in any document are reported, and a corrected query is suggested
   (Levenshtein distance to the index vocabulary).
3. **Ranking.** Selected documents are sorted by cosine similarity between the query vector (IDF) and the
   document vector (TF-IDF: `Aij = tf_ij * log10(N / n_i)`).
4. **Evaluation.** On the Metrics page the user marks relevant documents for a query; the system computes
   Precision, Recall, F-measure and Average Precision, plots an interpolated 11-point precision-recall curve
   and a summary chart for all judged queries.

Other features: query autocompletion from the index vocabulary, bulk import of `.docx` files (parsed with the
standard library, no extra dependencies), date filter, snippets with matched words, document management, built-in help.

## Run

```bash
pip install -r requirements.txt
python seed_data.py      # demo documents (recreates the database)
python run.py            # http://127.0.0.1:5000
pytest
```

Query examples: `договор аренда`, `договор ИЛИ соглашение`, `договор И НЕ расторжение`, `(договор OR соглашение) AND аренда`.

## Structure

| File | Purpose |
|---|---|
| `app/nlp.py` | tokenization, lemmatization, stop words |
| `app/document.py` | documents, inverted index, IDF and TF-IDF weights |
| `app/selection.py` | Boolean query parser and document selection |
| `app/search.py` | ranking and search results |
| `app/suggest.py`, `app/static/suggest.js` | autocompletion and typo correction |
| `app/docx_reader.py` | text extraction from `.docx` |
| `app/metrics.py` | relevance judgments, quality metrics, charts |
| `app/routes.py`, `app/templates/` | web interface |
