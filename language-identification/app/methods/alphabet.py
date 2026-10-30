from ..text_utils import ALPHABETS, letter_counts
from .base import Method, Prediction


class AlphabetMethod(Method):
    key = "alphabet"
    title = "Алфавитный метод"
    metric_name = "L1-расстояние"
    description = (
        "ПОЯ — алфавит языка (33 буквы кириллицы для русского, 26 букв латиницы для английского) "
        "и распределение частот этих букв, рассчитанное по обучающему тексту. Для документа строится "
        "распределение частот всех его букв; метрика — сумма модулей разностей частот (буквы вне "
        "алфавита языка дают полное несовпадение). Выбирается язык с минимальным расстоянием."
    )
    confidence_name = "относительный отрыв от второго языка: 1 − d₁ / d₂"

    def __init__(self):
        self.profiles: dict[str, dict[str, float]] = {}

    @staticmethod
    def _frequencies(text: str) -> tuple[dict[str, float], int]:
        counts = letter_counts(text)
        total = sum(counts.values())
        return ({c: n / total for c, n in counts.items()} if total else {}), total

    def fit(self, texts: dict[str, str]) -> None:
        self.profiles = {}
        for lang, text in texts.items():
            counts = letter_counts(text)
            kept = {c: counts[c] for c in ALPHABETS[lang]}
            total = sum(kept.values()) or 1
            self.profiles[lang] = {
                c: n / total for c, n in sorted(kept.items(), key=lambda item: -item[1])
            }

    def predict(self, text: str) -> Prediction:
        frequencies, total = self._frequencies(text)
        if not total:
            return Prediction(None, {}, {"reason": "В тексте нет букв."})

        scores = {
            lang: sum(abs(frequencies.get(c, 0) - profile.get(c, 0)) for c in set(frequencies) | set(profile))
            for lang, profile in self.profiles.items()
        }
        outside = {
            lang: sum(f for c, f in frequencies.items() if c not in profile)
            for lang, profile in self.profiles.items()
        }
        top_letters = [
            {"letter": c, "frequency": f, "profiles": {
                lang: profile.get(c, 0.0) for lang, profile in self.profiles.items()
            }}
            for c, f in sorted(frequencies.items(), key=lambda item: -item[1])[:12]
        ]
        ranked = sorted(scores.values())
        confidence = 1.0 - ranked[0] / ranked[1] if len(ranked) > 1 and ranked[1] > 0 else 1.0
        return Prediction(
            min(scores, key=scores.get),
            scores,
            {"letters": total, "outside_alphabet": outside, "top_letters": top_letters},
            confidence,
        )

    def to_dict(self) -> dict:
        return {"profiles": self.profiles}

    def load(self, data: dict) -> None:
        self.profiles = data["profiles"]
