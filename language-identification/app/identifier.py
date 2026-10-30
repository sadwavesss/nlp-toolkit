import json
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from .languages import LANGUAGES
from .methods import METHOD_CLASSES
from .text_utils import extract_pdf_text, preprocess, split_sentences, tokenize

FRAGMENT_MIN_WORDS = 6
MIXED_THRESHOLD = 0.1


class CorpusError(RuntimeError):
    pass


def weighted_vote(results: dict[str, dict]) -> tuple[str | None, float]:
    support = Counter()
    for r in results.values():
        if r["language"]:
            support[r["language"]] += r.get("confidence", 1.0)
    ranked = support.most_common()
    if not ranked or (len(ranked) > 1 and abs(ranked[0][1] - ranked[1][1]) < 1e-9):
        return None, 0.0
    return ranked[0][0], ranked[0][1] / len(results)


def split_fragments(text: str, min_words: int = FRAGMENT_MIN_WORDS) -> list[str]:
    fragments, buffer = [], []
    for sentence in split_sentences(text):
        buffer.append(sentence)
        if len(tokenize(" ".join(buffer))) >= min_words:
            fragments.append(" ".join(buffer))
            buffer = []
    if buffer:
        if fragments:
            fragments[-1] += " " + " ".join(buffer)
        else:
            fragments.append(" ".join(buffer))
    return fragments


class LanguageIdentifier:
    def __init__(self, corpus_dir: str | Path, model_path: str | Path):
        self.corpus_dir = Path(corpus_dir)
        self.model_path = Path(model_path)
        self.methods = {cls.key: cls() for cls in METHOD_CLASSES}
        self.corpus_info: dict = {}
        self.training_time: dict = {}
        self.trained_at: str | None = None
        self.ready = False
        self._lock = threading.Lock()

    def load_corpus(self) -> tuple[dict[str, str], dict]:
        texts, info = {}, {}
        for lang in LANGUAGES:
            parts, files = [], []
            for path in sorted((self.corpus_dir / lang).glob("*")):
                suffix = path.suffix.lower()
                if suffix == ".txt":
                    parts.append(preprocess(path.read_text(encoding="utf-8")))
                elif suffix == ".pdf":
                    parts.append(extract_pdf_text(path)[0])
                else:
                    continue
                files.append({"name": path.name, "bytes": path.stat().st_size})
            if not parts:
                raise CorpusError(
                    f"Нет обучающих текстов в папке {self.corpus_dir / lang}. "
                    "Запустите download_corpus.py или положите туда .txt/.pdf файлы."
                )
            texts[lang] = "\n".join(parts)
            info[lang] = {
                "files": files,
                "bytes": sum(f["bytes"] for f in files),
                "chars": len(texts[lang]),
            }
        return texts, info

    def train(self) -> None:
        with self._lock:
            texts, self.corpus_info = self.load_corpus()
            self.training_time = {}
            for key, method in self.methods.items():
                started = time.perf_counter()
                method.fit(texts)
                self.training_time[key] = round((time.perf_counter() - started) * 1000, 1)
            self.trained_at = datetime.now().isoformat(sep=" ", timespec="seconds")
            self.ready = True
            self._save()

    def _save(self) -> None:
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "trained_at": self.trained_at,
            "corpus_info": self.corpus_info,
            "training_time": self.training_time,
            "methods": {key: method.to_dict() for key, method in self.methods.items()},
        }
        self.model_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        data = json.loads(self.model_path.read_text(encoding="utf-8"))
        self.trained_at = data["trained_at"]
        self.corpus_info = data["corpus_info"]
        self.training_time = data["training_time"]
        for key, method in self.methods.items():
            method.load(data["methods"][key])
        self.ready = True

    def ensure_ready(self) -> None:
        if self.ready:
            return
        if self.model_path.exists():
            with self._lock:
                self._load()
        else:
            self.train()

    def identify(self, text: str, method_keys: list[str]) -> dict[str, dict]:
        self.ensure_ready()
        results = {}
        for key in method_keys:
            started = time.perf_counter()
            prediction = self.methods[key].predict(text)
            results[key] = {
                "language": prediction.language,
                "scores": prediction.scores,
                "details": prediction.details,
                "confidence": round(prediction.confidence, 6),
                "time_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        return results

    def segment(self, text: str, method_keys: list[str]) -> dict:
        self.ensure_ready()
        segments: list[dict] = []
        for fragment in split_fragments(text):
            results = {}
            for key in method_keys:
                prediction = self.methods[key].predict(fragment)
                results[key] = {"language": prediction.language, "confidence": prediction.confidence}
            language, confidence = weighted_vote(results)
            if segments and segments[-1]["language"] == language:
                last = segments[-1]
                total = last["chars"] + len(fragment)
                last["confidence"] = (last["confidence"] * last["chars"] + confidence * len(fragment)) / total
                last["chars"] = total
                last["fragments"] += 1
                last["text"] += " " + fragment
            else:
                segments.append({"language": language, "confidence": confidence, "chars": len(fragment), "fragments": 1, "text": fragment})

        determined = sum(s["chars"] for s in segments if s["language"])
        shares = {
            lang: sum(s["chars"] for s in segments if s["language"] == lang) / determined if determined else 0.0
            for lang in LANGUAGES
        }
        for s in segments:
            if len(s["text"]) > 400:
                s["text"] = s["text"][:400].rstrip() + "…"
        return {
            "segments": segments,
            "shares": shares,
            "mixed": sum(1 for share in shares.values() if share >= MIXED_THRESHOLD) > 1,
        }
