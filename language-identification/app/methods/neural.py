from collections import Counter

import numpy as np

from ..text_utils import LETTERS, tokenize
from .base import Method, Prediction


class NeuralMethod(Method):
    key = "neural"
    title = "Нейросетевой метод (MLP)"
    metric_name = "1 − P(язык)"
    letters_count = len(LETTERS)
    description = (
        "Многослойный перцептрон, реализованный на NumPy: вход — относительные частоты букв "
        "русского и английского алфавитов и наиболее частых буквенных биграмм (с учётом границ "
        "слов), скрытый слой ReLU, выход softmax по языкам. Обучение — обратное распространение "
        "ошибки (кросс-энтропия, оптимизатор Adam) на фрагментах обучающих текстов случайной длины."
    )

    def __init__(
        self,
        hidden_size: int = 32,
        epochs: int = 300,
        learning_rate: float = 0.01,
        l2: float = 1e-4,
        samples_per_language: int = 800,
        bigrams_per_language: int = 60,
        seed: int = 42,
    ):
        self.hidden_size = hidden_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.l2 = l2
        self.samples_per_language = samples_per_language
        self.bigrams_per_language = bigrams_per_language
        self.seed = seed
        self.languages: list[str] = []
        self.bigrams: list[str] = []
        self.params: dict[str, np.ndarray] = {}
        self.mean = np.zeros(0)
        self.std = np.ones(0)
        self.history: list[dict] = []
        self.metrics: dict = {}

    @staticmethod
    def _word_bigrams(words: list[str]):
        for word in words:
            padded = f"_{word}_"
            for i in range(len(padded) - 1):
                yield padded[i:i + 2]

    def _vector(self, text: str) -> np.ndarray:
        words = tokenize(text)
        letters = Counter("".join(words))
        bigrams = Counter(self._word_bigrams(words))
        letters_total = sum(letters.values()) or 1
        bigrams_total = sum(bigrams.values()) or 1
        return np.array(
            [letters[c] / letters_total for c in LETTERS]
            + [bigrams[b] / bigrams_total for b in self.bigrams]
        )

    def _forward(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        hidden = np.maximum(0.0, x @ self.params["W1"] + self.params["b1"])
        logits = hidden @ self.params["W2"] + self.params["b2"]
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        return hidden, probabilities

    def _accuracy(self, x: np.ndarray, y: np.ndarray) -> float:
        return float((self._forward(x)[1].argmax(axis=1) == y).mean()) if len(y) else 0.0

    def fit(self, texts: dict[str, str]) -> None:
        rng = np.random.default_rng(self.seed)
        self.languages = sorted(texts)

        self.bigrams = []
        for lang in self.languages:
            for bigram, _ in Counter(self._word_bigrams(tokenize(texts[lang]))).most_common(self.bigrams_per_language):
                if bigram not in self.bigrams:
                    self.bigrams.append(bigram)

        samples, labels = [], []
        for index, lang in enumerate(self.languages):
            text = texts[lang]
            for _ in range(self.samples_per_language):
                length = int(rng.integers(20, 2000))
                start = int(rng.integers(0, max(1, len(text) - length)))
                samples.append(self._vector(text[start:start + length]))
                labels.append(index)

        x, y = np.array(samples), np.array(labels)
        order = rng.permutation(len(y))
        x, y = x[order], y[order]
        split = int(len(y) * 0.8)
        self.mean = x[:split].mean(axis=0)
        self.std = x[:split].std(axis=0) + 1e-8
        x = (x - self.mean) / self.std
        self._train(x[:split], y[:split], x[split:], y[split:], rng)

    def _train(self, x_train, y_train, x_val, y_val, rng) -> None:
        n_in, n_out = x_train.shape[1], len(self.languages)
        self.params = {
            "W1": rng.normal(0, np.sqrt(2 / n_in), (n_in, self.hidden_size)),
            "b1": np.zeros(self.hidden_size),
            "W2": rng.normal(0, np.sqrt(2 / self.hidden_size), (self.hidden_size, n_out)),
            "b2": np.zeros(n_out),
        }
        moment1 = {k: np.zeros_like(v) for k, v in self.params.items()}
        moment2 = {k: np.zeros_like(v) for k, v in self.params.items()}
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        targets = np.eye(n_out)[y_train]
        n = len(y_train)
        self.history = []

        for epoch in range(1, self.epochs + 1):
            hidden, probabilities = self._forward(x_train)
            w1, w2 = self.params["W1"], self.params["W2"]
            loss = float(
                -np.mean(np.log(probabilities[np.arange(n), y_train] + 1e-12))
                + self.l2 / 2 * (np.sum(w1 ** 2) + np.sum(w2 ** 2))
            )

            d_logits = (probabilities - targets) / n
            d_hidden = d_logits @ w2.T
            d_hidden[hidden <= 0] = 0
            grads = {
                "W2": hidden.T @ d_logits + self.l2 * w2,
                "b2": d_logits.sum(axis=0),
                "W1": x_train.T @ d_hidden + self.l2 * w1,
                "b1": d_hidden.sum(axis=0),
            }
            for k, g in grads.items():
                moment1[k] = beta1 * moment1[k] + (1 - beta1) * g
                moment2[k] = beta2 * moment2[k] + (1 - beta2) * g ** 2
                m_hat = moment1[k] / (1 - beta1 ** epoch)
                v_hat = moment2[k] / (1 - beta2 ** epoch)
                self.params[k] -= self.learning_rate * m_hat / (np.sqrt(v_hat) + eps)

            if epoch == 1 or epoch % 5 == 0:
                self.history.append({
                    "epoch": epoch,
                    "loss": loss,
                    "train_accuracy": self._accuracy(x_train, y_train),
                    "val_accuracy": self._accuracy(x_val, y_val),
                })

        self.metrics = {
            "train_samples": int(n),
            "val_samples": int(len(y_val)),
            "train_accuracy": self._accuracy(x_train, y_train),
            "val_accuracy": self._accuracy(x_val, y_val),
            "final_loss": self.history[-1]["loss"],
        }

    def predict(self, text: str) -> Prediction:
        if not tokenize(text):
            return Prediction(None, {}, {"reason": "В тексте нет слов на поддерживаемых алфавитах."})
        x = (self._vector(text) - self.mean) / self.std
        probabilities = self._forward(x[None, :])[1][0]
        probs = {lang: float(probabilities[i]) for i, lang in enumerate(self.languages)}
        scores = {lang: 1.0 - p for lang, p in probs.items()}
        return Prediction(min(scores, key=scores.get), scores, {"probabilities": probs})

    @property
    def architecture(self) -> str:
        n_in = len(LETTERS) + len(self.bigrams)
        return f"{n_in} → {self.hidden_size} (ReLU) → {len(self.languages)} (softmax)"

    def to_dict(self) -> dict:
        return {
            "hidden_size": self.hidden_size,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "l2": self.l2,
            "languages": self.languages,
            "bigrams": self.bigrams,
            "params": {k: v.tolist() for k, v in self.params.items()},
            "mean": self.mean.tolist(),
            "std": self.std.tolist(),
            "history": self.history,
            "metrics": self.metrics,
        }

    def load(self, data: dict) -> None:
        self.hidden_size = data["hidden_size"]
        self.epochs = data["epochs"]
        self.learning_rate = data["learning_rate"]
        self.l2 = data["l2"]
        self.languages = data["languages"]
        self.bigrams = data["bigrams"]
        self.params = {k: np.array(v) for k, v in data["params"].items()}
        self.mean = np.array(data["mean"])
        self.std = np.array(data["std"])
        self.history = data["history"]
        self.metrics = data["metrics"]
