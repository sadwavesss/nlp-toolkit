import math
from dataclasses import dataclass, field


@dataclass
class Prediction:
    language: str | None
    scores: dict[str, float]
    details: dict = field(default_factory=dict)
    confidence: float = 0.0


def posterior(log_likelihoods: dict[str, float]) -> dict[str, float]:
    top = max(log_likelihoods.values())
    weights = {lang: math.exp(value - top) for lang, value in log_likelihoods.items()}
    total = sum(weights.values())
    return {lang: w / total for lang, w in weights.items()}


class Method:
    key = ""
    title = ""
    metric_name = ""
    description = ""
    confidence_name = ""

    def fit(self, texts: dict[str, str]) -> None:
        raise NotImplementedError

    def predict(self, text: str) -> Prediction:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError

    def load(self, data: dict) -> None:
        raise NotImplementedError
