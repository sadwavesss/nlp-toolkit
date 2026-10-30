from __future__ import annotations

import zipfile
from pathlib import PurePath
from typing import IO
from xml.etree import ElementTree

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_DC_TITLE = "{http://purl.org/dc/elements/1.1/}title"
_MAX_XML_SIZE = 50 * 1024 * 1024


class DocxError(ValueError):
    pass


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    parts = []
    for node in paragraph.iter():
        if node.tag == f"{_W}t":
            parts.append(node.text or "")
        elif node.tag == f"{_W}tab":
            parts.append("\t")
        elif node.tag in (f"{_W}br", f"{_W}cr"):
            parts.append("\n")
    return "".join(parts).strip()


def _read_xml(archive: zipfile.ZipFile, name: str) -> ElementTree.Element | None:
    try:
        info = archive.getinfo(name)
    except KeyError:
        return None
    if info.file_size > _MAX_XML_SIZE:
        raise DocxError("Документ слишком большой.")
    return ElementTree.fromstring(archive.read(info))


def read_docx(stream: IO[bytes], filename: str = "") -> tuple[str, str]:
    try:
        with zipfile.ZipFile(stream) as archive:
            body = _read_xml(archive, "word/document.xml")
            if body is None:
                raise DocxError("В файле нет содержимого Word (word/document.xml).")
            core = _read_xml(archive, "docProps/core.xml")
    except zipfile.BadZipFile as exc:
        raise DocxError("Файл повреждён или не является документом .docx.") from exc
    except ElementTree.ParseError as exc:
        raise DocxError("Не удалось разобрать XML документа.") from exc

    paragraphs = [text for p in body.iter(f"{_W}p") if (text := _paragraph_text(p))]
    title_node = core.find(_DC_TITLE) if core is not None else None
    title = (title_node.text or "").strip() if title_node is not None else ""
    return title or PurePath(filename).stem or "Документ без названия", "\n".join(paragraphs)
