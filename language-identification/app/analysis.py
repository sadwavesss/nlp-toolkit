import csv
import io
import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from .identifier import LanguageIdentifier, weighted_vote
from .languages import LANGUAGES, language_name
from .methods import METHOD_TITLES
from .text_utils import extract_pdf_text, tokenize

RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")
LABEL_RE = re.compile(r"^(ru|en)[_\-\s.]", re.IGNORECASE)
INVALID_CHARS_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

SOURCE_TITLES = {"upload": "Загруженные документы", "collection": "Тестовая коллекция"}
HIGH_CONFIDENCE = 0.9
LOW_CONFIDENCE = 0.6


def label_from_filename(name: str) -> str | None:
    match = LABEL_RE.match(name)
    return match.group(1).lower() if match else None


def safe_filename(name: str, taken: set[str]) -> str:
    cleaned = INVALID_CHARS_RE.sub("_", Path(name).name).strip(" .") or "document.pdf"
    stem, suffix = Path(cleaned).stem, Path(cleaned).suffix
    candidate, n = cleaned, 1
    while candidate.lower() in taken:
        n += 1
        candidate = f"{stem} ({n}){suffix}"
    taken.add(candidate.lower())
    return candidate


class RunStorage:
    def __init__(self, runs_dir: str | Path):
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def create(self) -> tuple[str, Path]:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        files_dir = self.runs_dir / run_id / "files"
        files_dir.mkdir(parents=True)
        return run_id, files_dir

    def files_dir(self, run_id: str) -> Path | None:
        return self.runs_dir / run_id / "files" if RUN_ID_RE.match(run_id) else None

    def save(self, run: dict) -> None:
        path = self.runs_dir / run["id"] / "run.json"
        path.write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")

    def load(self, run_id: str) -> dict | None:
        if not RUN_ID_RE.match(run_id):
            return None
        path = self.runs_dir / run_id / "run.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def list(self) -> list[dict]:
        runs = (self.load(p.name) for p in sorted(self.runs_dir.iterdir(), reverse=True) if p.is_dir())
        return [run for run in runs if run]

    def delete(self, run_id: str) -> bool:
        if not RUN_ID_RE.match(run_id) or not (self.runs_dir / run_id).exists():
            return False
        shutil.rmtree(self.runs_dir / run_id)
        return True


def reliability(confidence: float | None) -> str:
    if confidence is None:
        return ""
    if confidence >= HIGH_CONFIDENCE:
        return "высокая"
    return "средняя" if confidence >= LOW_CONFIDENCE else "низкая"


def analyze_document(identifier: LanguageIdentifier, path: Path, true_language: str | None, method_keys: list[str]) -> dict:
    document = {
        "filename": path.name,
        "true_language": true_language,
        "pages": 0,
        "chars": 0,
        "words": 0,
        "preview": "",
        "error": None,
        "results": {},
        "consensus": None,
        "consensus_confidence": None,
        "segmentation": None,
    }
    try:
        text, document["pages"] = extract_pdf_text(path)
    except Exception as exc:
        document["error"] = f"Не удалось прочитать PDF: {exc}"
        return document

    document.update(chars=len(text), words=len(tokenize(text)), preview=text[:1500])
    if not text.strip():
        document["error"] = "PDF не содержит извлекаемого текста (возможно, это скан)."
        return document

    document["results"] = identifier.identify(text, method_keys)
    document["consensus"], document["consensus_confidence"] = weighted_vote(document["results"])
    document["segmentation"] = identifier.segment(text, method_keys)
    return document


def build_run(run_id: str, source: str, identifier: LanguageIdentifier, files: list[tuple[Path, str | None]], method_keys: list[str]) -> dict:
    return {
        "id": run_id,
        "created": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "source": source,
        "methods": method_keys,
        "documents": [analyze_document(identifier, path, label, method_keys) for path, label in files],
    }


def summarize(run: dict) -> dict:
    documents = run["documents"]
    processed = [d for d in documents if not d["error"]]
    labeled = [d for d in processed if d["true_language"]]
    labels = list(LANGUAGES) + [None]

    methods = {}
    for key in run["methods"]:
        predictions = [d["results"][key]["language"] for d in processed]
        confusion = {
            true: {pred: sum(1 for d in labeled if d["true_language"] == true and d["results"][key]["language"] == pred) for pred in labels}
            for true in LANGUAGES
        }
        correct = sum(1 for d in labeled if d["results"][key]["language"] == d["true_language"])
        times = [d["results"][key]["time_ms"] for d in processed]
        methods[key] = {
            "title": METHOD_TITLES[key],
            "distribution": {lang: predictions.count(lang) for lang in labels},
            "correct": correct,
            "accuracy": correct / len(labeled) if labeled else None,
            "avg_time_ms": sum(times) / len(times) if times else 0.0,
            "confusion": confusion,
        }

    all_agree = sum(1 for d in processed if len({r["language"] for r in d["results"].values()}) == 1)
    consensus_correct = sum(1 for d in labeled if d["consensus"] == d["true_language"])
    pairwise = {}
    keys = run["methods"]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            same = sum(1 for d in processed if d["results"][a]["language"] == d["results"][b]["language"])
            pairwise[f"{a}|{b}"] = {"a": a, "b": b, "share": same / len(processed) if processed else 0.0}

    best = max(
        (k for k in methods if methods[k]["accuracy"] is not None),
        key=lambda k: (methods[k]["accuracy"], -methods[k]["avg_time_ms"]),
        default=None,
    )
    confidences = [d["consensus_confidence"] for d in processed if d.get("consensus_confidence") is not None]
    return {
        "mixed": sum(1 for d in processed if (d.get("segmentation") or {}).get("mixed")),
        "avg_confidence": sum(confidences) / len(confidences) if confidences else None,
        "low_confidence": sum(1 for c in confidences if c < LOW_CONFIDENCE),
        "total": len(documents),
        "processed": len(processed),
        "errors": len(documents) - len(processed),
        "labeled": len(labeled),
        "true_distribution": {lang: sum(1 for d in labeled if d["true_language"] == lang) for lang in LANGUAGES},
        "consensus_distribution": {lang: sum(1 for d in processed if d["consensus"] == lang) for lang in labels},
        "consensus_accuracy": consensus_correct / len(labeled) if labeled else None,
        "all_agree": all_agree,
        "all_agree_share": all_agree / len(processed) if processed else 0.0,
        "pairwise": pairwise,
        "methods": methods,
        "best_method": best,
    }


def _percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f} %"


def export_txt(run: dict, summary: dict) -> str:
    lines = [
        "ОТЧЁТ ОБ АВТОМАТИЧЕСКОМ РАСПОЗНАВАНИИ ЯЗЫКА ТЕКСТА",
        "=" * 60,
        f"Запуск: {run['id']}",
        f"Дата: {run['created']}",
        f"Источник: {SOURCE_TITLES.get(run['source'], run['source'])}",
        f"Методы: {', '.join(METHOD_TITLES[k] for k in run['methods'])}",
        "",
        "РЕЗУЛЬТАТЫ ПО ДОКУМЕНТАМ",
        "-" * 60,
    ]
    for i, d in enumerate(run["documents"], 1):
        lines.append(f"{i}. {d['filename']}")
        if d["true_language"]:
            lines.append(f"   Истинный язык: {language_name(d['true_language'])}")
        if d["error"]:
            lines.append(f"   Ошибка: {d['error']}")
            continue
        lines.append(f"   Страниц: {d['pages']}, символов: {d['chars']}, слов: {d['words']}")
        for key in run["methods"]:
            r = d["results"][key]
            metric = r["scores"].get(r["language"]) if r["language"] else None
            metric_text = f"{metric:.4f}" if metric is not None else "—"
            confidence = f", уверенность {_percent(r['confidence'])}" if "confidence" in r else ""
            lines.append(f"   {METHOD_TITLES[key]}: {language_name(r['language'])} (метрика {metric_text}{confidence}, {r['time_ms']:.2f} мс)")
        confidence = d.get("consensus_confidence")
        suffix = f" — уверенность {_percent(confidence)}, надёжность {reliability(confidence)}" if confidence is not None else ""
        lines.append(f"   Итог (взвешенное голосование методов): {language_name(d['consensus'])}{suffix}")
        if (d.get("segmentation") or {}).get("mixed"):
            lines.append(f"   Смешанный документ: {shares_text(d)}")

    lines += [
        "",
        "СВОДНАЯ СТАТИСТИКА",
        "-" * 60,
        f"Всего документов: {summary['total']}, обработано: {summary['processed']}, ошибок: {summary['errors']}",
        f"С известным языком: {summary['labeled']}",
        f"Все методы согласны: {summary['all_agree']} ({_percent(summary['all_agree_share'])})",
        f"Точность итогового решения: {_percent(summary['consensus_accuracy'])}",
        f"Средняя уверенность итога: {_percent(summary['avg_confidence'])}, решений с низкой уверенностью: {summary['low_confidence']}",
        f"Смешанных (многоязычных) документов: {summary['mixed']}",
        "",
    ]
    for key, m in summary["methods"].items():
        distribution = ", ".join(f"{language_name(lang)}: {n}" for lang, n in m["distribution"].items())
        lines.append(f"{m['title']}:")
        lines.append(f"   Распределение: {distribution}")
        lines.append(f"   Точность: {_percent(m['accuracy'])} ({m['correct']} из {summary['labeled']})")
        lines.append(f"   Среднее время: {m['avg_time_ms']:.2f} мс")
    if summary["best_method"]:
        lines.append("")
        lines.append(f"Лучший метод: {METHOD_TITLES[summary['best_method']]}")
    return "\n".join(lines) + "\n"


def export_csv(run: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    header = ["№", "Файл", "Истинный язык", "Страниц", "Символов", "Слов"]
    for key in run["methods"]:
        header += [f"{METHOD_TITLES[key]}: язык", f"{METHOD_TITLES[key]}: метрика", f"{METHOD_TITLES[key]}: время, мс"]
    writer.writerow(header + ["Итог", "Уверенность итога", "Доли языков", "Ошибка"])
    for i, d in enumerate(run["documents"], 1):
        row = [i, d["filename"], language_name(d["true_language"]) if d["true_language"] else "", d["pages"], d["chars"], d["words"]]
        for key in run["methods"]:
            r = d["results"].get(key)
            if r:
                metric = r["scores"].get(r["language"]) if r["language"] else None
                row += [language_name(r["language"]), f"{metric:.4f}".replace(".", ",") if metric is not None else "", f"{r['time_ms']:.3f}".replace(".", ",")]
            else:
                row += ["", "", ""]
        confidence = d.get("consensus_confidence")
        writer.writerow(row + [
            language_name(d["consensus"]) if not d["error"] else "",
            f"{confidence:.3f}".replace(".", ",") if confidence is not None else "",
            shares_text(d),
            d["error"] or "",
        ])
    return "\ufeff" + buffer.getvalue()


def shares_text(document: dict) -> str:
    shares = (document.get("segmentation") or {}).get("shares") or {}
    return ", ".join(f"{language_name(lang)} {_percent(share)}" for lang, share in shares.items() if share)


def export_json(run: dict, summary: dict) -> str:
    return json.dumps({"run": run, "summary": summary}, ensure_ascii=False, indent=2)
