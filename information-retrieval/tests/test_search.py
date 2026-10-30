import io
import zipfile

import pytest

from app import create_app, suggest
from app.db import init_db
from app.document import Document
from app.docx_reader import DocxError, read_docx
from app.metrics import compute_metrics, save_judgments
from app.search import Search
from app.selection import DocumentSelector

DOCUMENTS = [
    ("Договор аренды", "Договор аренды квартиры заключён на один год. Арендатор платит каждый месяц."),
    ("Расторжение договора", "Договор аренды расторгнут досрочно по соглашению сторон."),
    ("Локальная сеть", "Настройка локальной сети в офисе: коммутаторы, маршрутизаторы и кабели."),
    ("Рыбалка", "Рыбак поставил сеть на озере и поймал много рыбы."),
    ("Соглашение о сотрудничестве", "Компании подписали соглашение о сотрудничестве в области сетей."),
]


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})
    with app.app_context():
        init_db()
        for title, text in DOCUMENTS:
            Document(title=title, text=text).add_document_to_base()
        yield app


def titles(ids):
    return {Document.get_by_id(i).title for i in ids}


def test_query_matches_inflected_forms(app):
    assert titles(DocumentSelector().select("договоры").document_ids) == {"Договор аренды", "Расторжение договора"}


def test_boolean_operators(app):
    select = lambda q: titles(DocumentSelector().select(q).document_ids)
    assert select("договор И НЕ расторгнуть") == {"Договор аренды"}
    assert select("договор ИЛИ соглашение") == {"Договор аренды", "Расторжение договора", "Соглашение о сотрудничестве"}
    assert select("(договор OR соглашение) AND сторона") == {"Расторжение договора"}
    assert select("сеть") == {"Локальная сеть", "Рыбалка", "Соглашение о сотрудничестве"}


def test_implicit_and_or_modes(app):
    assert titles(DocumentSelector(all_words_together=True).select("договор квартира").document_ids) == {"Договор аренды"}
    assert len(DocumentSelector(all_words_together=False).select("договор квартира").document_ids) == 2


def test_missing_words_are_reported(app):
    result = DocumentSelector().select("договор блокчейн")
    assert result.missing_words == ["блокчейн"]
    assert result.document_ids == set()


def test_results_are_ranked_by_tfidf_similarity(app):
    results = Search("аренда").get_search_result()
    assert [r.title for r in results][0] in {"Договор аренды", "Расторжение договора"}
    assert all(a.rank >= b.rank for a, b in zip(results, results[1:]))
    assert all(0 < r.rank <= 1 for r in results)


def test_metrics_against_relevance_judgments(app):
    ids = {Document.get_by_id(i).title: i for i in range(1, len(DOCUMENTS) + 1)}
    save_judgments("сеть", "and", {ids["Локальная сеть"]: True, ids["Рыбалка"]: False, ids["Договор аренды"]: True})

    metrics = compute_metrics("сеть", "and")

    assert metrics.retrieved == 3 and metrics.relevant_total == 2 and metrics.relevant_retrieved == 1
    assert metrics.precision == pytest.approx(1 / 3)
    assert metrics.recall == pytest.approx(1 / 2)
    assert metrics.f_measure == pytest.approx(0.4)


def test_natural_language_operators(app):
    result = DocumentSelector().select("договор кроме расторгнуть")
    assert titles(result.document_ids) == {"Договор аренды"}
    assert result.expression == "договор И НЕ расторгнуть"
    assert titles(DocumentSelector().select("договор за исключением квартира").document_ids) == {"Расторжение договора"}


def test_autocomplete_and_typo_correction(app):
    assert suggest.complete("дог")[0]["word"] == "договор"
    assert suggest.levenshtein("договор", "догвор") == 1
    search = Search("догвор аренды")
    search.get_search_result()
    assert search.missing_words == ["догвор"]
    assert search.corrected_query == "договор аренды"


def make_docx(paragraphs, title=""):
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>')
        if title:
            archive.writestr("docProps/core.xml", f'<cp:coreProperties xmlns:cp="x" xmlns:dc="http://purl.org/dc/elements/1.1/">'
                                                  f"<dc:title>{title}</dc:title></cp:coreProperties>")
    buffer.seek(0)
    return buffer


def test_docx_reader():
    assert read_docx(make_docx(["Первый абзац.", "Второй абзац."]), "отчёт.docx") == ("отчёт", "Первый абзац.\nВторой абзац.")
    assert read_docx(make_docx(["Текст"], title="Заголовок"))[0] == "Заголовок"
    with pytest.raises(DocxError):
        read_docx(io.BytesIO(b"not a zip"), "broken.docx")


def test_docx_upload(app):
    client = app.test_client()
    response = client.post("/documents/upload", data={"files": (make_docx(["Аренда гаража на месяц."]), "гараж.docx")},
                           content_type="multipart/form-data")
    assert response.status_code == 302
    assert "гараж" in titles(DocumentSelector().select("гараж").document_ids)


def test_pages_render(app):
    client = app.test_client()
    for url in ["/", "/documents", "/search?q=договор", "/search?q=договор+И+НЕ+аренда&mode=or", "/help", "/metrics"]:
        assert client.get(url).status_code == 200, url
