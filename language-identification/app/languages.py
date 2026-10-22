LANGUAGES = {
    "ru": "Русский",
    "en": "Английский",
}


def language_name(code: str | None) -> str:
    return LANGUAGES.get(code, "не определён") if code else "не определён"
