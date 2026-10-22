
from typing import Optional

# Optional dependency: the app still starts without it
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    DocxDocument = None


class DocumentReader:

    def read_docx(self, filepath: str) -> str:
        if not DOCX_AVAILABLE:
            raise RuntimeError("Библиотека python-docx не установлена. Установите: pip install python-docx")
        doc = DocxDocument(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def is_supported(self, filename: str) -> bool:
        return filename.lower().endswith(".docx")
