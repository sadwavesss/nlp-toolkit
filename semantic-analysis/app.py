"""Flask web app for semantic analysis of Russian documents."""

import os
import json
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from db_manager import DatabaseManager
from semantic_analyzer import SemanticAnalyzer, POS_RU, DEPREL_RU
from document_reader import DocumentReader, SUPPORTED_FORMATS
from help_system import get_help, get_all_topics, search_help

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

db = DatabaseManager()
analyzer = SemanticAnalyzer()
reader = DocumentReader()


# --- Pages ---

@app.route('/')
def index():
    documents = db.get_all_documents()
    return render_template('index.html', documents=documents,
                           analyzer_available=analyzer.is_available(),
                           ner_available=analyzer.ner_available(),
                           supported_formats=SUPPORTED_FORMATS)


@app.route('/analysis/<int:doc_id>')
def analysis_page(doc_id):
    document = db.get_document(doc_id)
    if not document:
        return render_template('index.html', documents=db.get_all_documents(),
                               analyzer_available=analyzer.is_available(),
                               error="Документ не найден"), 404

    analysis = db.get_document_analysis(doc_id)
    pos_stats = db.get_pos_stats(doc_id)
    deprel_stats = db.get_deprel_stats(doc_id)
    entity_stats = db.get_entity_stats(doc_id)
    role_stats = db.get_role_stats(doc_id)

    sentiment_stats = {}
    for item in analysis:
        if item["sentiment"]:
            label = item["sentiment"]["label_ru"]
            sentiment_stats[label] = sentiment_stats.get(label, 0) + 1

    return render_template('analysis.html', document=document,
                           analysis=analysis,
                           pos_stats=pos_stats,
                           deprel_stats=deprel_stats,
                           entity_stats=entity_stats,
                           role_stats=role_stats,
                           sentiment_stats=sentiment_stats)


@app.route('/help')
def help_page():
    topic_key = request.args.get('topic', 'general')
    topic = get_help(topic_key)
    topics = get_all_topics()
    return render_template('help.html', topic=topic, topics=topics,
                           current_topic=topic_key)


# --- API ---

@app.route('/api/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "Файл не выбран"}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({"success": False, "error": "Имя файла пустое"}), 400

    filename = secure_filename(file.filename)
    if not reader.is_supported(filename):
        return jsonify({"success": False, "error": f"Неподдерживаемый формат. Допустимые: {', '.join(SUPPORTED_FORMATS.keys())}"}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        text = reader.read(filepath)
        if not text or not text.strip():
            return jsonify({"success": False, "error": "Не удалось извлечь текст из файла"}), 400

        fmt = reader.get_format_name(filename)
        title = request.form.get('title', filename)
        doc_id = db.add_document(filename, title, fmt, text)

        if analyzer.is_available():
            _perform_analysis(doc_id, text)

        return jsonify({"success": True, "doc_id": doc_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        try:
            os.remove(filepath)
        except OSError:
            pass


@app.route('/api/analyze/<int:doc_id>', methods=['POST'])
def reanalyze(doc_id):
    document = db.get_document(doc_id)
    if not document:
        return jsonify({"success": False, "error": "Документ не найден"}), 404

    if not analyzer.is_available():
        return jsonify({"success": False, "error": "Анализатор недоступен"}), 503

    try:
        _perform_analysis(doc_id, document['raw_text'])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/token/<int:token_id>', methods=['PUT'])
def edit_token(token_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Нет данных"}), 400

    allowed_fields = {'lemma', 'pos', 'pos_ru', 'deprel', 'deprel_ru', 'morph', 'morph_ru'}
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    if not updates:
        return jsonify({"success": False, "error": "Нет допустимых полей"}), 400

    db.update_token(token_id, **updates)
    return jsonify({"success": True})


@app.route('/api/delete/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    if db.delete_document(doc_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Документ не найден"}), 404


@app.route('/api/export/<int:doc_id>')
def export_analysis(doc_id):
    document = db.get_document(doc_id)
    if not document:
        return jsonify({"error": "Документ не найден"}), 404

    analysis = db.get_document_analysis(doc_id)
    export_data = {
        "document": {
            "filename": document["filename"],
            "title": document["title"],
            "format": document["format"],
        },
        "sentences": [],
    }
    for item in analysis:
        sent_data = {
            "text": item["sentence"]["text"],
            "tokens": item["tokens"],
            "entities": item["entities"],
            "semantic_roles": item["roles"],
            "word_senses": item["senses"],
            "semantic_relations": item["relations"],
            "sentiment": item["sentiment"],
        }
        export_data["sentences"].append(sent_data)

    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    tmp.write(json_str)
    tmp.close()

    return send_file(tmp.name, as_attachment=True,
                     download_name=f"analysis_{doc_id}.json",
                     mimetype='application/json')


@app.route('/api/help/search')
def help_search():
    q = request.args.get('q', '')
    if not q:
        return jsonify([])
    results = search_help(q)
    return jsonify(results)


# --- Internal helpers ---

def _perform_analysis(doc_id: int, text: str):
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sentences WHERE document_id = ?", (doc_id,))
    conn.commit()
    conn.close()

    results = analyzer.analyze_text(text)

    for i, sent_data in enumerate(results):
        sent_id = db.add_sentence(doc_id, sent_data["text"], i)

        db.add_tokens_batch(sent_id, sent_data["tokens"])

        tokens = db.get_tokens(sent_id)

        if sent_data["entities"]:
            db.add_named_entities_batch(sent_id, sent_data["entities"])

        if sent_data["roles"]:
            role_records = []
            for role in sent_data["roles"]:
                tok_idx = role["token_index"]
                pred_idx = role["predicate_index"]
                if tok_idx < len(tokens):
                    token_id = tokens[tok_idx]["id"]
                    predicate_token_id = tokens[pred_idx]["id"] if pred_idx >= 0 and pred_idx < len(tokens) else None
                    role_records.append({
                        "token_id": token_id,
                        "role": role["role"],
                        "role_ru": role["role_ru"],
                        "predicate_token_id": predicate_token_id,
                    })
            if role_records:
                db.add_semantic_roles_batch(role_records)

        if sent_data["senses"]:
            sense_records = []
            for sense in sent_data["senses"]:
                tok_idx = sense["token_index"]
                if tok_idx < len(tokens):
                    sense_records.append({
                        "token_id": tokens[tok_idx]["id"],
                        "sense": sense["sense"],
                        "sense_ru": sense["sense_ru"],
                        "synset": "",
                        "hypernym": sense["hypernym"],
                        "hypernym_ru": sense["hypernym_ru"],
                    })
            if sense_records:
                db.add_word_senses_batch(sense_records)

        if sent_data["relations"]:
            db.add_relations_batch(sent_id, sent_data["relations"])

        if sent_data["sentiment"]:
            s = sent_data["sentiment"]
            db.add_sentiment(sent_id, s["label"], s["label_ru"], s["score"])


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
