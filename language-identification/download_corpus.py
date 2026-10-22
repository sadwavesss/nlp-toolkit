import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "corpus"
TEST_DIR = ROOT / "test_docs"
TRAIN_LIMIT_BYTES = 100_000
TEST_PAGE_CHARS = 2600
USER_AGENT = "LangIdLab/1.0 (educational project)"
REQUEST_DELAY = 1.5
MAX_ATTEMPTS = 6
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
]

ARTICLES = {
    "ru": {
        "train": ["Русский язык", "Москва", "Байкал", "Волга", "Кошка", "Чай", "Хлеб", "Шахматы"],
        "test": ["Солнце", "Луна", "Футбол", "Яблоко", "Кофе", "Эрмитаж", "Сибирь", "Интернет", "Музыка", "Лошадь"],
    },
    "en": {
        "train": ["English language", "London", "Mississippi River", "Cat", "Tea", "Bread", "Chess", "William Shakespeare"],
        "test": ["Sun", "Moon", "Association football", "Apple", "Coffee", "Louvre", "Canada", "Internet", "Music", "Horse"],
    },
}

STOP_SECTIONS = {
    "см. также", "примечания", "литература", "ссылки", "источники",
    "see also", "references", "notes", "further reading", "external links", "bibliography", "sources",
}
UNSUPPORTED_RE = re.compile(r"[^\u0020-\u007e\u00a0-\u024f\u0400-\u04ff\u2010-\u2027\u2116]")
EMPTY_BRACKETS_RE = re.compile(r"\(\s*[;,]?\s*\)")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
FILENAME_RE = re.compile(r'[\\/:*?"<>|]')


def fetch_extract(lang: str, title: str) -> str:
    params = urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "explaintext": 1, "redirects": 1,
        "titles": title, "format": "json", "formatversion": 2,
    })
    request = urllib.request.Request(
        f"https://{lang}.wikipedia.org/w/api.php?{params}", headers={"User-Agent": USER_AGENT}
    )
    for attempt in range(1, MAX_ATTEMPTS + 1):
        time.sleep(REQUEST_DELAY)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)["query"]["pages"][0].get("extract", "")
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == MAX_ATTEMPTS:
                raise
            wait = int(exc.headers.get("Retry-After") or 0) or 5 * attempt
            print(f"  … слишком много запросов, ожидание {wait} с")
            time.sleep(wait)
    return ""


def clean(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip().replace("\u2011", "-")
        if line.startswith("=="):
            if line.strip("= ").lower() in STOP_SECTIONS:
                break
            continue
        if not line or "displaystyle" in line:
            continue
        line = EMPTY_BRACKETS_RE.sub("", UNSUPPORTED_RE.sub("", line))
        line = re.sub(r"\s{2,}", " ", line).strip()
        if len(line) > 40:
            lines.append(line)
    return "\n".join(lines)


def take(text: str, limit: int, size=len) -> str:
    paragraphs, used = [], 0
    for paragraph in text.split("\n"):
        kept = []
        for sentence in SENTENCE_RE.split(paragraph):
            cost = size(sentence) + 1
            if used + cost > limit:
                if kept:
                    paragraphs.append(" ".join(kept))
                return "\n".join(paragraphs)
            kept.append(sentence)
            used += cost
        paragraphs.append(" ".join(kept))
    return "\n".join(paragraphs)


def utf8_size(text: str) -> int:
    return len(text.encode("utf-8"))


def find_font() -> Path:
    for font in FONT_CANDIDATES:
        if font.exists():
            return font
    sys.exit("Не найден TTF-шрифт с кириллицей (Arial / DejaVu Sans). Укажите путь в FONT_CANDIDATES.")


def write_pdf(path: Path, title: str, text: str, font: Path) -> None:
    pdf = FPDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, 20)
    pdf.add_font("Main", fname=str(font))
    pdf.set_title(title)
    pdf.add_page()
    pdf.set_font("Main", size=15)
    pdf.multi_cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Main", size=11)
    for paragraph in text.split("\n"):
        pdf.multi_cell(0, 5.5, paragraph, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)
    pdf.output(str(path))


def build_corpus(lang: str, titles: list[str]) -> None:
    target = CORPUS_DIR / lang
    target.mkdir(parents=True, exist_ok=True)
    per_article = TRAIN_LIMIT_BYTES // len(titles)
    total = 0
    for i, title in enumerate(titles, 1):
        try:
            text = take(clean(fetch_extract(lang, title)), per_article, utf8_size)
        except Exception as exc:
            print(f"  [!] {title}: {exc}")
            continue
        if not text:
            print(f"  [!] {title}: пустая статья")
            continue
        path = target / f"{i:02d}_{FILENAME_RE.sub('_', title)}.txt"
        path.write_text(text, encoding="utf-8")
        total += path.stat().st_size
        print(f"  {path.name}: {path.stat().st_size / 1024:.1f} КБ")
    print(f"  Итого корпус {lang}: {total / 1024:.1f} КБ")


def build_tests(lang: str, titles: list[str], font: Path) -> None:
    target = TEST_DIR / lang
    target.mkdir(parents=True, exist_ok=True)
    for i, title in enumerate(titles, 1):
        try:
            text = take(clean(fetch_extract(lang, title)), TEST_PAGE_CHARS)
        except Exception as exc:
            print(f"  [!] {title}: {exc}")
            continue
        if not text:
            print(f"  [!] {title}: пустая статья")
            continue
        path = target / f"{lang}_{i:02d}.pdf"
        write_pdf(path, title, text, font)
        print(f"  {path.name}: «{title}», {len(text)} символов")


def main() -> None:
    font = find_font()
    for lang, sets in ARTICLES.items():
        print(f"Обучающий корпус [{lang}]")
        build_corpus(lang, sets["train"])
        print(f"Тестовая коллекция [{lang}]")
        build_tests(lang, sets["test"], font)
    model = ROOT / "instance" / "models.json"
    if model.exists():
        model.unlink()
        print("Старые профили удалены — они будут построены заново при запуске приложения.")


if __name__ == "__main__":
    main()
