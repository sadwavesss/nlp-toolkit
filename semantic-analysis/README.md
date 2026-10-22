# Semantic Analysis

Web application for semantic analysis of Russian sentences.

- **Syntax:** tokens, lemmas, POS, morphological features and dependency relations (spaCy `ru_core_news_sm`).
- **Named entities:** persons, organizations, locations, dates from spaCy, completed with Natasha.
- **Semantic roles:** agent, patient, recipient, experiencer, modifier — mapped from dependency relations.
- **Relation extraction:** `(subject, relation, object)` triples from the dependency tree; the relation is the verb
  lemma plus preposition, conjoined and infinitive clauses inherit the subject, time adverbials are skipped.
- **Sentiment:** lexicon-based with intensifiers and negation.
- **Word meanings:** a small lexicon of senses and hypernyms.

Documents: DOCX, TXT, PDF, HTML, RTF. Results can be edited and exported to JSON.

## Run

```bash
pip install -r requirements.txt
python -m spacy download ru_core_news_sm
python run.py                 # http://127.0.0.1:5002
python demo_relations.py      # relation extraction on sample sentences in the console
```
