import shutil
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from . import analysis
from .identifier import CorpusError, LanguageIdentifier
from .languages import LANGUAGES
from .methods import METHOD_TITLES

bp = Blueprint("main", __name__)


def get_identifier() -> LanguageIdentifier:
    return current_app.extensions["identifier"]


def get_runs() -> analysis.RunStorage:
    return current_app.extensions["runs"]


def test_collection() -> list[tuple[Path, str]]:
    root = Path(current_app.config["TEST_DIR"])
    return [(path, lang) for lang in LANGUAGES for path in sorted((root / lang).glob("*.pdf"))]


def selected_methods() -> list[str]:
    keys = [k for k in request.form.getlist("methods") if k in METHOD_TITLES]
    return keys or list(METHOD_TITLES)


def model_status() -> str | None:
    try:
        get_identifier().ensure_ready()
    except CorpusError as exc:
        return str(exc)
    return None


def load_run_or_404(run_id: str) -> dict:
    run = get_runs().load(run_id)
    if run is None:
        abort(404)
    return run


@bp.route("/")
def index():
    return render_template(
        "index.html",
        model_error=model_status(),
        identifier=get_identifier(),
        collection_size=len(test_collection()),
        recent_runs=get_runs().list()[:5],
    )


@bp.route("/analyze", methods=["POST"])
def analyze():
    if error := model_status():
        flash(error, "error")
        return redirect(url_for("main.index"))

    uploads = [f for f in request.files.getlist("files") if f and f.filename]
    pdfs = [f for f in uploads if f.filename.lower().endswith(".pdf")]
    if len(pdfs) < len(uploads):
        flash(f"Пропущено файлов не в формате PDF: {len(uploads) - len(pdfs)}.", "warning")
    if not pdfs:
        flash("Выберите хотя бы один PDF-документ.", "error")
        return redirect(url_for("main.index"))

    run_id, files_dir = get_runs().create()
    taken: set[str] = set()
    files = []
    for upload in pdfs:
        name = analysis.safe_filename(upload.filename, taken)
        path = files_dir / name
        upload.save(path)
        files.append((path, analysis.label_from_filename(name)))

    run = analysis.build_run(run_id, "upload", get_identifier(), files, selected_methods())
    get_runs().save(run)
    flash(f"Обработано документов: {len(files)}.", "success")
    return redirect(url_for("main.view_run", run_id=run_id))


@bp.route("/collection", methods=["POST"])
def analyze_collection():
    if error := model_status():
        flash(error, "error")
        return redirect(url_for("main.index"))

    collection = test_collection()
    if not collection:
        flash("Тестовая коллекция пуста. Запустите download_corpus.py.", "error")
        return redirect(url_for("main.index"))

    run_id, files_dir = get_runs().create()
    taken: set[str] = set()
    files = []
    for source, lang in collection:
        target = files_dir / analysis.safe_filename(source.name, taken)
        shutil.copy2(source, target)
        files.append((target, lang))

    run = analysis.build_run(run_id, "collection", get_identifier(), files, selected_methods())
    get_runs().save(run)
    flash(f"Тестовая коллекция обработана: {len(files)} документов.", "success")
    return redirect(url_for("main.view_run", run_id=run_id))


@bp.route("/runs")
def runs():
    items = [(run, analysis.summarize(run)) for run in get_runs().list()]
    return render_template("runs.html", items=items)


@bp.route("/runs/<run_id>")
def view_run(run_id: str):
    run = load_run_or_404(run_id)
    return render_template("run.html", run=run, summary=analysis.summarize(run), source_titles=analysis.SOURCE_TITLES)


@bp.route("/runs/<run_id>/documents/<int:index>")
def view_document(run_id: str, index: int):
    run = load_run_or_404(run_id)
    if not 0 <= index < len(run["documents"]):
        abort(404)
    return render_template("document.html", run=run, index=index, doc=run["documents"][index])


@bp.route("/runs/<run_id>/files/<path:filename>")
def run_file(run_id: str, filename: str):
    files_dir = get_runs().files_dir(run_id)
    if files_dir is None:
        abort(404)
    return send_from_directory(files_dir, filename, mimetype="application/pdf")


@bp.route("/runs/<run_id>/export/<fmt>")
def export_run(run_id: str, fmt: str):
    run = load_run_or_404(run_id)
    summary = analysis.summarize(run)
    exporters = {
        "txt": (lambda: analysis.export_txt(run, summary), "text/plain"),
        "csv": (lambda: analysis.export_csv(run), "text/csv"),
        "json": (lambda: analysis.export_json(run, summary), "application/json"),
    }
    if fmt not in exporters:
        abort(404)
    build, mimetype = exporters[fmt]
    return Response(
        build().encode("utf-8"),
        mimetype=f"{mimetype}; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=langid-{run_id}.{fmt}"},
    )


@bp.route("/runs/<run_id>/delete", methods=["POST"])
def delete_run(run_id: str):
    if get_runs().delete(run_id):
        flash("Запуск удалён.", "success")
    else:
        flash("Запуск не найден.", "error")
    return redirect(url_for("main.runs"))


def chart_points(values: list[float], width: int, height: int, top: float) -> str:
    if len(values) < 2:
        return ""
    step = width / (len(values) - 1)
    return " ".join(f"{i * step:.1f},{height - min(v, top) / top * height:.1f}" for i, v in enumerate(values))


@bp.route("/profiles")
def profiles():
    error = model_status()
    if error:
        return render_template("profiles.html", model_error=error)

    identifier = get_identifier()
    neural = identifier.methods["neural"]
    history = neural.history
    max_loss = max((h["loss"] for h in history), default=1.0) or 1.0
    chart = {
        "width": 600,
        "height": 200,
        "max_loss": max_loss,
        "epochs": history[-1]["epoch"] if history else 0,
        "loss": chart_points([h["loss"] for h in history], 600, 200, max_loss),
        "val_accuracy": chart_points([h["val_accuracy"] for h in history], 600, 200, 1.0),
    }
    return render_template(
        "profiles.html",
        model_error=None,
        identifier=identifier,
        short_words=identifier.methods["short_words"],
        alphabet=identifier.methods["alphabet"],
        neural=neural,
        chart=chart,
    )


@bp.route("/profiles/retrain", methods=["POST"])
def retrain():
    try:
        get_identifier().train()
        flash("Профили языков перестроены, нейросеть переобучена.", "success")
    except CorpusError as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.profiles"))


@bp.route("/help")
def help_page():
    return render_template("help.html")
