# Syntax Analysis

Web application for dependency parsing of Russian documents with manual correction of the results.

- Upload a DOCX document; it is split into sentences and parsed with spaCy (`ru_core_news_sm`).
- Table of tokens with lemma, part of speech, morphological features (case, gender, number, tense, aspect, ...),
  head and dependency relation, plus a dependency tree view.
- Any token can be corrected (lemma, POS, relation); corrections are stored in SQLite.
- Statistics of parts of speech and relation types, JSON export, built-in help.

Design documents (PlantUML) are in [docs](docs).

## Run

```bash
pip install -r requirements.txt
python -m spacy download ru_core_news_sm
python run.py            # http://127.0.0.1:5001
```
