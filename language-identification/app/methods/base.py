from dataclasses import dataclass, field


@dataclass
class Prediction:
    language: str | None
    scores: dict[str, float]
    details: dict = field(default_factory=dict)


class Method:
    key = ""
    title = ""
    metric_name = ""
    description = ""

    def fit(self, texts: dict[str, str]) -> None:
        raise NotImplementedError

    def predict(self, text: str) -> Prediction:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError

    def load(self, data: dict) -> None:
        raise NotImplementedError
