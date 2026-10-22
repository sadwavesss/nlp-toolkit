import math
from collections import Counter

from ..text_utils import split_sentences, tokenize
from .base import Method, Prediction


class ShortWordsMethod(Method):
    key = "short_words"
    title = "Метод коротких слов"
    metric_name = "−log P / n"
    description = (
        "ПОЯ — лексемы длиной до 5 символов, встретившиеся в обучающем тексте более 3 раз, "
        "с вероятностями p = частота / сумма частот. Вероятность предложения — произведение "
        "вероятностей его лексем (для отсутствующих в ПОЯ — минимальная вероятность). "
        "Метрика — средний отрицательный логарифм вероятности на лексему; выбирается минимум."
    )

    def __init__(self, max_length: int = 5, min_count: int = 4):
        self.max_length = max_length
        self.min_count = min_count
        self.profiles: dict[str, dict[str, float]] = {}
        self.min_probability: dict[str, float] = {}

    def _short_tokens(self, text: str) -> list[str]:
        return [t for t in tokenize(text) if len(t) <= self.max_length]

    def fit(self, texts: dict[str, str]) -> None:
        self.profiles, self.min_probability = {}, {}
        for lang, text in texts.items():
            counts = Counter(self._short_tokens(text))
            selected = {w: c for w, c in counts.items() if c >= self.min_count}
            total = sum(selected.values())
            self.profiles[lang] = {
                w: c / total for w, c in sorted(selected.items(), key=lambda item: -item[1])
            }
            self.min_probability[lang] = min(self.profiles[lang].values()) / 2

    def _log_probability(self, tokens: list[str], lang: str) -> float:
        profile, floor = self.profiles[lang], self.min_probability[lang]
        return sum(math.log(profile.get(t, floor)) for t in tokens)

    def predict(self, text: str) -> Prediction:
        log_prob = {lang: 0.0 for lang in self.profiles}
        votes = Counter()
        all_tokens = []
        sentences = split_sentences(text)
        for sentence in sentences:
            tokens = self._short_tokens(sentence)
            if not tokens:
                continue
            all_tokens.extend(tokens)
            sentence_scores = {lang: self._log_probability(tokens, lang) for lang in self.profiles}
            for lang, value in sentence_scores.items():
                log_prob[lang] += value
            votes[max(sentence_scores, key=sentence_scores.get)] += 1

        if not all_tokens:
            return Prediction(None, {}, {"reason": "В тексте нет коротких слов."})

        n = len(all_tokens)
        scores = {lang: -value / n for lang, value in log_prob.items()}
        coverage = {
            lang: sum(1 for t in all_tokens if t in profile) / n
            for lang, profile in self.profiles.items()
        }
        top_tokens = [
            {"token": token, "count": count, "probabilities": {
                lang: profile.get(token) for lang, profile in self.profiles.items()
            }}
            for token, count in Counter(all_tokens).most_common(15)
        ]
        return Prediction(
            min(scores, key=scores.get),
            scores,
            {
                "tokens": n,
                "sentences": sum(votes.values()),
                "votes": dict(votes),
                "coverage": coverage,
                "top_tokens": top_tokens,
            },
        )

    def to_dict(self) -> dict:
        return {
            "max_length": self.max_length,
            "min_count": self.min_count,
            "profiles": self.profiles,
            "min_probability": self.min_probability,
        }

    def load(self, data: dict) -> None:
        self.max_length = data["max_length"]
        self.min_count = data["min_count"]
        self.profiles = data["profiles"]
        self.min_probability = data["min_probability"]
