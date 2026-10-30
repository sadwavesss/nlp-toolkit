# Language Identification

Web application that detects whether a PDF document is written in Russian or English and compares three methods.

| Method | Language profile | Decision |
|---|---|---|
| Short words | probabilities of words up to 5 letters seen 4+ times in the training text | minimum mean negative log-probability per word (+ per-sentence votes) |
| Alphabet | letter frequency distribution of each alphabet | minimum L1 distance between frequency distributions |
| Neural network | letter frequencies + most frequent letter bigrams (with word boundaries) | MLP `features → 32 (ReLU) → 2 (softmax)` |

The MLP is implemented **from scratch in NumPy**: He initialization, forward pass, cross-entropy with L2,
backpropagation and the Adam optimizer. It is trained on random-length fragments of the training texts
with an 80/20 train/validation split; the training curve is shown in the UI.

Each method also reports a confidence: the relative margin to the second language (alphabet), the Bayesian
posterior with equal priors (short words) and the softmax probability (neural network). The final answer is a
confidence-weighted vote of the methods, labelled as high / medium / low reliability.

Mixed-language documents are split into fragments of at least six words, each fragment is classified separately
and adjacent fragments with the same language are merged, which gives the share of each language in the document.

## Results

Training corpus: ~100 KB of Wikipedia text per language. Test collection: 20 one-page PDF articles on other topics
(10 per language). All three methods classify **20 / 20** documents correctly. Results can be exported to TXT, CSV and JSON.

## Run

```bash
pip install -r requirements.txt
python download_corpus.py   # downloads the corpus and builds test PDFs from Wikipedia
python run.py               # http://127.0.0.1:5000
pytest
```

## Structure

| File | Purpose |
|---|---|
| `app/methods/short_words.py`, `alphabet.py`, `neural.py` | the three methods |
| `app/identifier.py` | training on the corpus, model persistence (`instance/models.json`) |
| `app/analysis.py` | batch processing, statistics, export |
| `app/text_utils.py` | PDF text extraction and preprocessing |
| `download_corpus.py` | Wikipedia API client, corpus and test PDF generation |
