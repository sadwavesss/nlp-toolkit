"""Flask web app for dependency parsing of Russian documents."""

import os
import json
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from db_manager import DatabaseManager
from syntax_analyzer import SyntaxAnalyzer, POS_RU, DEPREL_RU
from document_reader import DocumentReader
from help_system import get_help, get_all_topics, search_help

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

db = DatabaseManager()
analyzer = SyntaxAnalyzer()
reader = DocumentReader()


# --- Pages ---

@app.route('/')
def index():
    documents = db.get_all_documents()
    return render_template('index.html', documents=documents,
                           analyzer_available=analyzer.is_available())


@app.route('/analysis/<int:doc_id>')
def analysis_page(doc_id):
    document = db.get_document(doc_id)
    if not document:
        return render_template('index.html', documents=db.get_all_documents(),
                               analyzer_available=analyzer.is_available(),
                               error="Документ не найден"), 404

    analysis = db.get_document_analysis(doc_id)
    deprel_stats = db.get_deprel_stats(doc_id)
    pos_stats = db.get_pos_stats(doc_id)

    # Statistics keys are shown with Russian labels
    deprel_stats_ru = {DEPREL_RU.get(k, k): v for k, v in deprel_stats.items()}
    pos_stats_ru = {POS_RU.get(k, k): v for k, v in pos_stats.items()}

    return render_template('analysis.html', document=document,
                           analysis=analysis,
                           deprel_stats=deprel_stats_ru,
                           pos_stats=pos_stats_ru)


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
        return jsonify({'success': False, 'error': 'Файл не выбран'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'Файл не выбран'}), 400

    if not reader.is_supported(file.filename):
        return jsonify({'success': False, 'error': 'Поддерживается только формат DOCX'}), 400

    if not analyzer.is_available():
        return jsonify({'success': False, 'error': 'Анализатор недоступен. Установите модель: python -m spacy download ru_core_news_sm'}), 400

    try:
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)

        text = reader.read_docx(temp_path)
        os.remove(temp_path)

        if not text.strip():
            return jsonify({'success': False, 'error': 'Документ пуст'}), 400

        title = request.form.get('title', filename)
        doc_id = db.add_document(filename, title, text)

        _analyze_and_store(doc_id, text)

        return jsonify({'success': True, 'doc_id': doc_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze/<int:doc_id>', methods=['POST'])
def reanalyze(doc_id):
    document = db.get_document(doc_id)
    if not document:
        return jsonify({'success': False, 'error': 'Документ не найден'}), 404

    if not analyzer.is_available():
        return jsonify({'success': False, 'error': 'Анализатор недоступен'}), 400

    try:
        _clear_analysis(doc_id)
        _analyze_and_store(doc_id, document['raw_text'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/token/<int:token_id>', methods=['PUT'])
def update_token(token_id):
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Нет данных'}), 400

    allowed_fields = {'lemma', 'pos', 'pos_ru', 'morph', 'head_index', 'deprel', 'deprel_ru'}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({'success': False, 'error': 'Нет полей для обновления'}), 400

    try:
        db.update_token(token_id, **updates)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/document/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    try:
        if db.delete_document(doc_id):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Документ не найден'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/<int:doc_id>')
def export_analysis(doc_id):
    document = db.get_document(doc_id)
    if not document:
        return jsonify({'success': False, 'error': 'Документ не найден'}), 404

    analysis = db.get_document_analysis(doc_id)
    export_data = {
        "document": {
            "filename": document['filename'],
            "title": document['title'],
        },
        "sentences": []
    }

    for item in analysis:
        sent_data = {
            "text": item["sentence"]["text"],
            "tokens": item["tokens"]
        }
        export_data["sentences"].append(sent_data)

    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False,
                                       encoding='utf-8')
    json.dump(export_data, tmp, ensure_ascii=False, indent=2)
    tmp.close()

    return send_file(tmp.name, as_attachment=True,
                     download_name=f"analysis_{doc_id}.json",
                     mimetype='application/json')


@app.route('/api/help/search')
def help_search():
    query = request.args.get('q', '')
    results = search_help(query)
    return jsonify({'success': True, 'results': results})


# --- Helpers ---

def _analyze_and_store(doc_id: int, text: str):
    sentences = analyzer.analyze_text(text)

    for i, sent in enumerate(sentences):
        sent_id = db.add_sentence(doc_id, sent["text"], i)
        db.add_tokens_batch(sent_id, sent["tokens"])


def _clear_analysis(doc_id: int):
    sentences = db.get_sentences(doc_id)
    for sent in sentences:
        pass
    # Tokens are removed by ON DELETE CASCADE
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sentences WHERE document_id = ?", (doc_id,))
    conn.commit()
    conn.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
