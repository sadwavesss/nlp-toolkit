# Corpus Manager

Web application for building and exploring morphologically annotated corpora of Russian texts.

- Create corpora and add documents in TXT, RTF, PDF and DOCX (DOC through MS Word on Windows).
- Every word form is annotated with lemma, part of speech and grammatical features (pymorphy3, Mystem as a fallback).
- Search by word form or lemma; concordance (keyword in context).
- Frequency statistics of word forms, lemmas and parts of speech.

## Run

```bash
pip install -r requirements.txt
python start.py          # http://127.0.0.1:5000
```

`test_animals.txt` is a small sample text.
