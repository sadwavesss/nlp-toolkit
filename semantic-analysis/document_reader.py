"""Text extraction from DOCX, TXT, PDF, HTML and RTF."""

from typing import Optional

# Optional dependencies: the app still starts without them
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    DocxDocument = None

try:
    from pdfminer.high_level import extract_text as pdf_extract_text
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False


SUPPORTED_FORMATS = {
    ".txt": "Текстовый файл",
    ".docx": "Документ Word",
    ".pdf": "PDF документ",
    ".html": "HTML страница",
    ".htm": "HTML страница",
    ".rtf": "RTF документ",
}


class DocumentReader:

    def read(self, filepath: str) -> str:
        ext = self._get_extension(filepath)
        if ext == ".txt":
            return self._read_txt(filepath)
        elif ext == ".docx":
            return self._read_docx(filepath)
        elif ext == ".pdf":
            return self._read_pdf(filepath)
        elif ext in (".html", ".htm"):
            return self._read_html(filepath)
        elif ext == ".rtf":
            return self._read_rtf(filepath)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")

    def is_supported(self, filename: str) -> bool:
        return self._get_extension(filename) in SUPPORTED_FORMATS

    def get_format_name(self, filename: str) -> str:
        ext = self._get_extension(filename)
        return SUPPORTED_FORMATS.get(ext, "Неизвестный формат")

    def _get_extension(self, filename: str) -> str:
        if "." not in filename:
            return ""
        return "." + filename.lower().rsplit(".", 1)[-1]

    def _read_txt(self, filepath: str) -> str:
        for enc in ("utf-8", "windows-1251", "cp866", "latin-1"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _read_docx(self, filepath: str) -> str:
        if not DOCX_AVAILABLE:
            raise RuntimeError("Библиотека python-docx не установлена")
        doc = DocxDocument(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def _read_pdf(self, filepath: str) -> str:
        if not PDF_AVAILABLE:
            raise RuntimeError("Библиотека pdfminer не установлена. Установите: pip install pdfminer.six")
        return pdf_extract_text(filepath)

    def _read_html(self, filepath: str) -> str:
        if not HTML_AVAILABLE:
            raise RuntimeError("Библиотека beautifulsoup4 не установлена. Установите: pip install beautifulsoup4")
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            return soup.get_text(separator="\n", strip=True)

    def _read_rtf(self, filepath: str) -> str:
        """Simplified RTF reader: strips control words."""
        with open(filepath, "rb") as f:
            raw = f.read()
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = raw.decode("windows-1251", errors="replace")
        # Strip RTF markup
        import re
        text = re.sub(r'\{[^}]*\}', '', text)
        text = re.sub(r'\\[a-z]+\d*\s?', ' ', text)
        text = re.sub(r'[{}]', '', text)
        return text.strip()
