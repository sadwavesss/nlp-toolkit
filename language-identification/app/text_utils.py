import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

RU_ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
EN_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
LETTERS = RU_ALPHABET + EN_ALPHABET
ALPHABETS = {"ru": RU_ALPHABET, "en": EN_ALPHABET}

WORD_RE = re.compile(r"[a-zа-яё]+")
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")
HYPHENATION_RE = re.compile(r"(\w)-\s*\n\s*(\w)")
SPACES_RE = re.compile(r"[ \t\u00a0]+")


def extract_pdf_text(path: str | Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return preprocess("\n".join(pages)), len(pages)


def preprocess(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\r", "")
    text = HYPHENATION_RE.sub(r"\1\2", text)
    lines = (SPACES_RE.sub(" ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def split_sentences(text: str) -> list[str]:
    return [s for s in SENTENCE_RE.split(text.replace("\n", " ")) if WORD_RE.search(s.lower())]


def letter_counts(text: str) -> Counter:
    return Counter(c for c in text.lower() if c.isalpha())
