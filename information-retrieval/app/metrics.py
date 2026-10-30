from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .db import get_db
from .search import Search, SearchResult


def normalize_query(query: str) -> str:
    return query.strip().lower()


@dataclass
class RankedJudgment:
    document_id: int
    title: str
    rank: float
    relevant: bool
    precision_at_i: float
    recall_at_i: float


@dataclass
class QualityMetrics:
    query: str
    mode: str
    retrieved: int
    relevant_total: int
    relevant_retrieved: int
    precision: float
    recall: float
    f_measure: float
    average_precision: float
    ranked: list[RankedJudgment] = field(default_factory=list)


def get_judgments(query: str, mode: str) -> dict[int, bool]:
    db = get_db()
    rows = db.execute(
        "SELECT document_id, relevant FROM relevance_judgments WHERE query = ? AND mode = ?",
        (normalize_query(query), mode),
    ).fetchall()
    return {r["document_id"]: bool(r["relevant"]) for r in rows}


def save_judgments(query: str, mode: str, judgments: dict[int, bool]) -> None:
    db = get_db()
    q = normalize_query(query)
    for document_id, relevant in judgments.items():
        db.execute(
            """
            INSERT INTO relevance_judgments (query, mode, document_id, relevant)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(query, mode, document_id)
            DO UPDATE SET relevant = excluded.relevant
            """,
            (q, mode, document_id, int(relevant)),
        )
    db.commit()


def list_evaluated_queries() -> list[tuple[str, str]]:
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT query, mode FROM relevance_judgments ORDER BY query"
    ).fetchall()
    return [(r["query"], r["mode"]) for r in rows]


def compute_metrics(query: str, mode: str) -> QualityMetrics:
    all_words_together = mode == "and"
    search_obj = Search(search_query=query, all_words_together=all_words_together)
    results: list[SearchResult] = search_obj.get_search_result()

    judgments = get_judgments(query, mode)
    relevant_total = sum(1 for v in judgments.values() if v)
    retrieved = len(results)

    relevant_retrieved = 0
    ranked: list[RankedJudgment] = []
    precisions_at_relevant = []

    for i, r in enumerate(results, start=1):
        is_relevant = judgments.get(r.document_id, False)
        if is_relevant:
            relevant_retrieved += 1
            precisions_at_relevant.append(relevant_retrieved / i)
        precision_at_i = relevant_retrieved / i
        recall_at_i = relevant_retrieved / relevant_total if relevant_total else 0.0
        ranked.append(
            RankedJudgment(
                document_id=r.document_id,
                title=r.title,
                rank=r.rank,
                relevant=is_relevant,
                precision_at_i=precision_at_i,
                recall_at_i=recall_at_i,
            )
        )

    precision = relevant_retrieved / retrieved if retrieved else 0.0
    recall = relevant_retrieved / relevant_total if relevant_total else 0.0
    f_measure = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    average_precision = (
        sum(precisions_at_relevant) / relevant_total if relevant_total else 0.0
    )

    return QualityMetrics(
        query=query,
        mode=mode,
        retrieved=retrieved,
        relevant_total=relevant_total,
        relevant_retrieved=relevant_retrieved,
        precision=precision,
        recall=recall,
        f_measure=f_measure,
        average_precision=average_precision,
        ranked=ranked,
    )


def compute_all_metrics() -> list[QualityMetrics]:
    return [compute_metrics(q, m) for q, m in list_evaluated_queries()]


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def precision_recall_curve_image(metrics: QualityMetrics) -> str | None:
    if not metrics.ranked or metrics.relevant_total == 0:
        return None

    points = [(r.recall_at_i, r.precision_at_i) for r in metrics.ranked]

    levels = [i / 10 for i in range(11)]
    interpolated = []
    for level in levels:
        candidates = [p for r, p in points if r >= level]
        interpolated.append(max(candidates) if candidates else 0.0)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(levels, interpolated, marker="o", color="#2454ff")
    ax.set_xlabel("Полнота (Recall)")
    ax.set_ylabel("Точность (Precision)")
    ax.set_title(f"Precision–Recall: «{metrics.query}»")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.grid(True, linestyle="--", alpha=0.5)
    return _fig_to_base64(fig)


def summary_bar_chart_image(all_metrics: list[QualityMetrics]) -> str | None:
    if not all_metrics:
        return None

    labels = [m.query if len(m.query) <= 18 else m.query[:16] + "…" for m in all_metrics]
    precision = [m.precision for m in all_metrics]
    recall = [m.recall for m in all_metrics]
    f_measure = [m.f_measure for m in all_metrics]
    ap = [m.average_precision for m in all_metrics]

    x = range(len(labels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 1.4), 4))
    ax.bar([i - 1.5 * width for i in x], precision, width, label="Precision", color="#2454ff")
    ax.bar([i - 0.5 * width for i in x], recall, width, label="Recall", color="#1a7f37")
    ax.bar([i + 0.5 * width for i in x], f_measure, width, label="F-мера", color="#c62828")
    ax.bar([i + 1.5 * width for i in x], ap, width, label="AP", color="#8a6100")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Значение метрики")
    ax.set_title("Метрики качества по оценённым запросам")
    ax.legend()
    fig.tight_layout()
    return _fig_to_base64(fig)
