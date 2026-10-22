import pytest

from app import create_app
from app.db import init_db
from app.document import Document
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
    # "договоры" / "договора" are both lemmatized to "договор"
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
    # Only the IT document is relevant for "сеть"; one relevant document is never retrieved
    save_judgments("сеть", "and", {ids["Локальная сеть"]: True, ids["Рыбалка"]: False, ids["Договор аренды"]: True})

    metrics = compute_metrics("сеть", "and")

    assert metrics.retrieved == 3 and metrics.relevant_total == 2 and metrics.relevant_retrieved == 1
    assert metrics.precision == pytest.approx(1 / 3)
    assert metrics.recall == pytest.approx(1 / 2)
    assert metrics.f_measure == pytest.approx(0.4)


def test_pages_render(app):
    client = app.test_client()
    for url in ["/", "/documents", "/search?q=договор", "/search?q=договор+И+НЕ+аренда&mode=or", "/help", "/metrics"]:
        assert client.get(url).status_code == 200, url
