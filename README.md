# NLP Toolkit for Russian

A collection of natural language processing applications for Russian text, built step by step from
morphology to dialogue systems: lemmatization and corpora, syntactic and semantic parsing, information
retrieval, language identification and a task-oriented chatbot.

| Project | What it does | Key techniques |
|---|---|---|
| [information-retrieval](information-retrieval) | Search engine over a document base with quality evaluation | lemmatization, Boolean query parser (AND/OR/NOT, brackets), inverted index, TF-IDF cosine ranking, Precision/Recall/F1/AP, precision-recall curves |
| [language-identification](language-identification) | Detects the language (Russian / English) of PDF documents with three methods | short-word language model, letter-frequency profiles, **MLP implemented from scratch in NumPy** (backprop, Adam) |
| [dialogue-system](dialogue-system) | Chatbot answering questions about animals | intent classification, entity extraction (spaCy + dictionary), dialogue state, knowledge base, template NLG, REST API |
| [semantic-analysis](semantic-analysis) | Semantic analysis of sentences | NER (spaCy + Natasha), semantic roles, relation extraction from dependency trees, lexicon-based sentiment |
| [syntax-analysis](syntax-analysis) | Dependency parsing with manual correction | spaCy dependency parser, morphological features, editable parse results, statistics |
| [corpus-manager](corpus-manager) | Builds annotated text corpora from documents | PDF/DOCX/RTF/TXT extraction, morphological annotation, concordance (KWIC), frequency statistics |
| [morphology-dictionary](morphology-dictionary) | Desktop app that builds a frequency dictionary of a text | tokenization, lemmatization (pymorphy3 / Mystem), editable morphology, JSON/CSV export |

All projects are web applications on Flask (except the Tkinter desktop dictionary) with SQLite storage.

## Results

- **Language identification:** all three methods correctly classified **20 / 20** held-out Wikipedia articles
  (10 Russian, 10 English, one page each) that were not used for training. The task is easy for two languages with
  different alphabets; the interesting part is the comparison of the methods and the from-scratch neural network.
- **Information retrieval:** the system computes Precision, Recall, F-measure and Average Precision against relevance
  judgments entered by the user and plots interpolated precision-recall curves.

## Tech stack

Python, Flask, SQLite, pymorphy3, spaCy (`ru_core_news_sm`), Natasha, NLTK, NumPy, matplotlib, pypdf, python-docx,
JavaScript (dialogue UI), PlantUML (design documents), pytest.

## Running a project

Each folder is self-contained:

```bash
cd information-retrieval
python -m venv .venv
# Windows: .\.venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Projects that use spaCy also need the Russian model: `python -m spacy download ru_core_news_sm`.
See the README in each folder for details.

## Tests

```bash
cd information-retrieval && pytest
cd language-identification && pytest
```
