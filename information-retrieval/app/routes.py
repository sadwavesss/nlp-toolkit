from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from . import metrics as metrics_module
from . import suggest
from .db import get_db
from .document import Document
from .docx_reader import DocxError, read_docx
from .search import Search

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    db = get_db()
    stats = {
        "documents": db.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"],
        "lemmas": db.execute("SELECT COUNT(*) AS c FROM lemmas").fetchone()["c"],
    }
    return render_template("index.html", stats=stats)


@bp.route("/documents")
def documents():
    docs = Document.get_all_documents()
    return render_template("documents.html", documents=docs)


@bp.route("/documents/add", methods=["GET", "POST"])
def add_document():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        text = request.form.get("text", "").strip()
        if not title or not text:
            flash("Заполните заголовок и текст документа.", "error")
            return render_template("add_document.html", title=title, text=text)

        doc = Document(title=title, text=text)
        if doc.add_document_to_base():
            flash(f"Документ «{title}» добавлен в базу (ID {doc.document_id}).", "success")
            return redirect(url_for("main.documents"))
        flash("Не удалось добавить документ.", "error")

    return render_template("add_document.html", title="", text="")


@bp.route("/documents/upload", methods=["POST"])
def upload_documents():
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        flash("Выберите хотя бы один файл .docx.", "error")
        return redirect(url_for("main.add_document"))

    added = []
    for file in files:
        if not file.filename.lower().endswith(".docx"):
            flash(f"«{file.filename}»: поддерживаются только файлы .docx.", "error")
            continue
        try:
            title, text = read_docx(file.stream, file.filename)
        except DocxError as exc:
            flash(f"«{file.filename}»: {exc}", "error")
            continue
        doc = Document(title=title, text=text)
        if doc.add_document_to_base():
            added.append(title)
        else:
            flash(f"«{file.filename}»: документ не содержит текста.", "error")

    if added:
        flash(f"Добавлено документов из DOCX: {len(added)} ({', '.join(added)}).", "success")
        return redirect(url_for("main.documents"))
    return redirect(url_for("main.add_document"))


@bp.route("/documents/<int:document_id>")
def view_document(document_id: int):
    doc = Document.get_by_id(document_id)
    if doc is None:
        flash("Документ не найден.", "error")
        return redirect(url_for("main.documents"))
    return render_template("document_view.html", doc=doc)


@bp.route("/documents/<int:document_id>/delete", methods=["POST"])
def delete_document(document_id: int):
    if Document.delete_document_from_base(document_id):
        flash("Документ удалён.", "success")
    else:
        flash("Не удалось удалить документ.", "error")
    return redirect(url_for("main.documents"))


@bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    all_words_together = request.args.get("mode", "and") == "and"
    date_start = request.args.get("date_start", "").strip()
    date_end = request.args.get("date_end", "").strip()

    results = None
    search_obj = None
    if query:
        search_obj = Search(
            search_query=query,
            all_words_together=all_words_together,
            date_start_string=date_start,
            date_end_string=date_end,
        )
        results = search_obj.get_search_result()

    return render_template(
        "search.html",
        query=query,
        mode="and" if all_words_together else "or",
        date_start=date_start,
        date_end=date_end,
        results=results,
        search_obj=search_obj,
    )


@bp.route("/api/suggest")
def api_suggest():
    return jsonify(suggest.complete(request.args.get("q", "")))


@bp.route("/help")
def help_page():
    return render_template("help.html")


@bp.route("/metrics")
def metrics_overview():
    all_metrics = metrics_module.compute_all_metrics()
    chart = metrics_module.summary_bar_chart_image(all_metrics)

    mean = None
    if all_metrics:
        n = len(all_metrics)
        mean = {
            "precision": sum(m.precision for m in all_metrics) / n,
            "recall": sum(m.recall for m in all_metrics) / n,
            "f_measure": sum(m.f_measure for m in all_metrics) / n,
            "average_precision": sum(m.average_precision for m in all_metrics) / n,
        }

    return render_template(
        "metrics.html",
        all_metrics=all_metrics,
        chart=chart,
        mean=mean,
    )


@bp.route("/metrics/evaluate", methods=["GET", "POST"])
def metrics_evaluate():
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        mode = request.form.get("mode", "and")
        shown_ids = [int(v) for v in request.form.getlist("shown_document_id")]
        judgments = {
            doc_id: request.form.get(f"relevant_{doc_id}") is not None
            for doc_id in shown_ids
        }
        metrics_module.save_judgments(query, mode, judgments)
        flash("Оценки релевантности сохранены, метрики пересчитаны.", "success")
        return redirect(url_for("main.metrics_evaluate", q=query, mode=mode))

    query = request.args.get("q", "").strip()
    mode = request.args.get("mode", "and")

    results = None
    judgments = {}
    computed = None
    chart = None

    if query:
        all_words_together = mode == "and"
        search_obj = Search(search_query=query, all_words_together=all_words_together)
        results = search_obj.get_search_result()
        judgments = metrics_module.get_judgments(query, mode)
        computed = metrics_module.compute_metrics(query, mode)
        chart = metrics_module.precision_recall_curve_image(computed)

    return render_template(
        "metrics_evaluate.html",
        query=query,
        mode=mode,
        results=results,
        judgments=judgments,
        computed=computed,
        chart=chart,
    )
