import pytest

from app.identifier import LanguageIdentifier, split_fragments, weighted_vote
from app.methods import METHOD_CLASSES
from app.methods.neural import NeuralMethod

RU = (
    "Москва является столицей России и самым большим городом страны. В городе много музеев, театров и парков. "
    "Каждый год сюда приезжают миллионы туристов, чтобы увидеть Красную площадь и Кремль. Река Москва течёт "
    "через центр города, а по её берегам гуляют люди. Зимой в Москве холодно и идёт снег, а летом бывает жарко. "
    "Метро в Москве одно из самых красивых в мире, и на нём каждый день ездят миллионы людей. "
) * 6
EN = (
    "London is the capital of England and the largest city in the United Kingdom. The city has many museums, "
    "theatres and parks. Every year millions of tourists come here to see the Tower and the river. The Thames "
    "flows through the centre of the city, and people walk along its banks. In winter it is cold and wet, and in "
    "summer it can be warm. The underground in London is one of the oldest in the world. "
) * 6
TEXTS = {"ru": RU, "en": EN}

UNSEEN = [
    ("Кошка спит на окне, а собака играет во дворе с детьми.", "ru"),
    ("Я люблю читать книги вечером, когда за окном идёт дождь.", "ru"),
    ("The cat is sleeping on the window and the dog plays in the yard with the children.", "en"),
    ("I like to read books in the evening when it is raining outside.", "en"),
]


@pytest.fixture(scope="module")
def trained():
    methods = {}
    for cls in METHOD_CLASSES:
        method = NeuralMethod(epochs=150, samples_per_language=200) if cls is NeuralMethod else cls()
        method.fit(TEXTS)
        methods[cls.key] = method
    return methods


@pytest.mark.parametrize("text,language", UNSEEN)
@pytest.mark.parametrize("key", [cls.key for cls in METHOD_CLASSES])
def test_methods_identify_unseen_sentences(trained, key, text, language):
    assert trained[key].predict(text).language == language


@pytest.mark.parametrize("key", [cls.key for cls in METHOD_CLASSES])
def test_methods_handle_text_without_letters(trained, key):
    assert trained[key].predict("12345 !!! 678").language is None


def test_neural_training_reduces_loss_and_reaches_high_validation_accuracy(trained):
    history = trained["neural"].history
    assert history[-1]["loss"] < history[0]["loss"]
    assert trained["neural"].metrics["val_accuracy"] >= 0.95


@pytest.mark.parametrize("key", [cls.key for cls in METHOD_CLASSES])
def test_method_state_round_trips_through_dict(trained, key):
    restored = type(trained[key])()
    restored.load(trained[key].to_dict())
    text = UNSEEN[0][0]
    assert restored.predict(text).scores == pytest.approx(trained[key].predict(text).scores)


@pytest.mark.parametrize("key", [cls.key for cls in METHOD_CLASSES])
def test_confidence_is_a_probability(trained, key):
    for text, _ in UNSEEN:
        assert 0.0 <= trained[key].predict(text).confidence <= 1.0
    assert trained[key].predict(RU[:400]).confidence > 0.5


def test_weighted_vote():
    assert weighted_vote({"a": {"language": "ru", "confidence": 0.9}, "b": {"language": "en", "confidence": 0.3}}) == ("ru", 0.45)
    assert weighted_vote({"a": {"language": "ru", "confidence": 0.5}, "b": {"language": "en", "confidence": 0.5}}) == (None, 0.0)
    assert weighted_vote({"a": {"language": None, "confidence": 0.0}}) == (None, 0.0)


def test_split_fragments_merges_short_tail():
    fragments = split_fragments("Один два три четыре пять шесть. Семь восемь девять десять одиннадцать двенадцать. Тринадцать.")
    assert len(fragments) == 2 and fragments[-1].endswith("Тринадцать.")


def make_identifier(tmp_path):
    for lang, text in TEXTS.items():
        (tmp_path / "corpus" / lang).mkdir(parents=True)
        (tmp_path / "corpus" / lang / "train.txt").write_text(text, encoding="utf-8")
    identifier = LanguageIdentifier(tmp_path / "corpus", tmp_path / "models.json")
    identifier.methods["neural"] = NeuralMethod(epochs=50, samples_per_language=100)
    return identifier


def test_segment_detects_mixed_document(tmp_path):
    identifier = make_identifier(tmp_path)
    text = " ".join(t for t, _ in UNSEEN)
    result = identifier.segment(text, ["short_words", "alphabet"])
    assert result["mixed"]
    assert [s["language"] for s in result["segments"]] == ["ru", "en"]
    assert result["shares"]["ru"] + result["shares"]["en"] == pytest.approx(1.0)
    assert not identifier.segment(RU[:600], ["short_words", "alphabet"])["mixed"]


def test_identifier_trains_from_corpus_folder_and_caches_model(tmp_path):
    identifier = make_identifier(tmp_path)
    model_path = tmp_path / "models.json"
    results = identifier.identify(UNSEEN[2][0], ["short_words", "alphabet"])

    assert model_path.exists()
    assert {r["language"] for r in results.values()} == {"en"}

    reloaded = LanguageIdentifier(tmp_path / "corpus", model_path)
    assert reloaded.identify(UNSEEN[0][0], ["alphabet"])["alphabet"]["language"] == "ru"
