# Morphology Dictionary

Desktop application (Tkinter) that builds a frequency dictionary of a Russian text.

- Opens TXT (UTF-8 / CP1251) and RTF files.
- Tokenizes the text and lemmatizes every word form (pymorphy3, Yandex Mystem as a fallback).
- Table of word forms with lexemes and frequencies; morphological information can be edited.
- Filtering by substring, saving and loading the dictionary as JSON, export to CSV.

## Run

```bash
pip install -r requirements.txt
python main.py
```

`test.txt` and `test_rus.txt` are sample texts; data model and use cases are in [diagrams](diagrams).
