import pytest

from app.identifier import LanguageIdentifier
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


def test_identifier_trains_from_corpus_folder_and_caches_model(tmp_path):
    for lang, text in TEXTS.items():
        (tmp_path / "corpus" / lang).mkdir(parents=True)
        (tmp_path / "corpus" / lang / "train.txt").write_text(text, encoding="utf-8")
    model_path = tmp_path / "models.json"

    identifier = LanguageIdentifier(tmp_path / "corpus", model_path)
    identifier.methods["neural"] = NeuralMethod(epochs=50, samples_per_language=100)
    results = identifier.identify(UNSEEN[2][0], ["short_words", "alphabet"])

    assert model_path.exists()
    assert {r["language"] for r in results.values()} == {"en"}

    reloaded = LanguageIdentifier(tmp_path / "corpus", model_path)
    assert reloaded.identify(UNSEEN[0][0], ["alphabet"])["alphabet"]["language"] == "ru"
