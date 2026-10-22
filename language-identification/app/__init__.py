import os
from pathlib import Path

from flask import Flask

from .analysis import RunStorage
from .identifier import LanguageIdentifier
from .languages import LANGUAGES, language_name
from .methods import METHOD_CLASSES, METHOD_TITLES


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    root = Path(app.root_path).parent
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        CORPUS_DIR=str(root / "corpus"),
        TEST_DIR=str(root / "test_docs"),
        MODEL_PATH=os.path.join(app.instance_path, "models.json"),
        RUNS_DIR=os.path.join(app.instance_path, "runs"),
        MAX_CONTENT_LENGTH=100 * 1024 * 1024,
    )
    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    app.extensions["identifier"] = LanguageIdentifier(app.config["CORPUS_DIR"], app.config["MODEL_PATH"])
    app.extensions["runs"] = RunStorage(app.config["RUNS_DIR"])

    app.add_template_filter(language_name, "lang_name")
    app.jinja_env.globals.update(
        LANGUAGES=LANGUAGES,
        METHOD_TITLES=METHOD_TITLES,
        METHODS={cls.key: cls for cls in METHOD_CLASSES},
    )

    from . import routes
    app.register_blueprint(routes.bp)

    return app
