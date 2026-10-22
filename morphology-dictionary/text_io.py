import os
import re
from typing import List


def _decode_text_bytes(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("cp1251")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")


def extract_text_from_txt(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    text = _decode_text_bytes(raw)
    return text.replace("\r\n", "\n").replace("\r", "\n")


_RTF_IGNORED_DESTS = {
    "fonttbl",
    "colortbl",
    "stylesheet",
    "info",
    "pict",
    "object",
    "datastore",
    "themedata",
    "xmlnstbl",
    "revtbl",
    "filetbl",
    "listtable",
    "listoverridetable",
}


def extract_text_from_rtf(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()

    s = raw.decode("latin-1", errors="ignore")
    out: List[str] = []
    i = 0
    stack: List[bool] = []
    skip = False

    def push_skip(value: bool) -> None:
        nonlocal skip
        stack.append(skip)
        skip = skip or value

    def pop_skip() -> None:
        nonlocal skip
        if stack:
            skip = stack.pop()
        else:
            skip = False

    while i < len(s):
        ch = s[i]
        if ch == "{":
            push_skip(False)
            i += 1
            continue
        if ch == "}":
            pop_skip()
            i += 1
            continue
        if ch == "\\":
            i += 1
            if i >= len(s):
                break
            nxt = s[i]
            if nxt in ("\\", "{", "}"):
                if not skip:
                    out.append(nxt)
                i += 1
                continue
            if nxt == "'":
                if i + 2 < len(s):
                    hex_part = s[i + 1 : i + 3]
                    try:
                        b = bytes([int(hex_part, 16)])
                        if not skip:
                            out.append(b.decode("cp1251", errors="replace"))
                    except ValueError:
                        pass
                i += 3
                continue

            j = i
            while j < len(s) and s[j].isalpha():
                j += 1
            word = s[i:j]

            k = j
            if k < len(s) and (s[k] == "-" or s[k].isdigit()):
                k += 1
                while k < len(s) and s[k].isdigit():
                    k += 1

            if k < len(s) and s[k] == " ":
                k += 1

            if word == "par":
                if not skip:
                    out.append("\n")
            elif word == "line":
                if not skip:
                    out.append("\n")
            elif word == "tab":
                if not skip:
                    out.append("\t")
            elif word == "u":
                num_part = s[j:k].strip()
                m = re.match(r"-?\d+", num_part)
                if m and not skip:
                    code = int(m.group(0))
                    if code < 0:
                        code += 65536
                    try:
                        out.append(chr(code))
                    except ValueError:
                        pass
            else:
                if word in _RTF_IGNORED_DESTS or word == "*":
                    skip = True

            i = k
            continue

        if not skip:
            if ch not in ("\n", "\r"):
                out.append(ch)
        i += 1

    text = "".join(out)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v]+", " ", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text


def load_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        return extract_text_from_txt(path)
    if ext == ".rtf":
        return extract_text_from_rtf(path)
    raise ValueError("Неподдерживаемый формат")
