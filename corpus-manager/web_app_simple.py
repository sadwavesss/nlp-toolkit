from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from typing import Dict, List

from database import CorpusDatabase
from document_reader import DocumentReader
from morphological_analyzer import get_analyzer
from concordance import ConcordanceBuilder

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev')

db = CorpusDatabase()
doc_reader = DocumentReader()
morph_analyzer = get_analyzer()

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'rtf', 'pdf', 'docx', 'doc'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    try:
        corpora = db.get_corpora()

        for corpus in corpora:
            try:
                stats = db.get_corpus_basic_stats(corpus['id'])
                corpus['documents_count'] = stats['documents_count']
                corpus['wordforms_count'] = stats['wordforms_count']
            except Exception as e:
                print(f"Ошибка при получении статистики для корпуса {corpus['id']}: {e}")
                corpus['documents_count'] = 0
                corpus['wordforms_count'] = 0

        return render_template('index_simple.html', corpora=corpora)
    except Exception as e:
        print(f"Ошибка при загрузке главной страницы: {e}")
        flash('Ошибка при загрузке списка корпусов', 'error')
        return render_template('index_simple.html', corpora=[])


@app.route('/help')
def help_page():
    return render_template('help.html')


@app.route('/create_corpus', methods=['GET', 'POST'])
def create_corpus():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('Название корпуса обязательно', 'error')
            return render_template('create_corpus.html')
        
        corpus_id = db.create_corpus(name, description)
        flash(f'Корпус "{name}" создан', 'success')
        return redirect(url_for('view_corpus', corpus_id=corpus_id))
    
    return render_template('create_corpus.html')


@app.route('/corpus/<int:corpus_id>')
def view_corpus(corpus_id: int):
    corpus = db.get_corpus(corpus_id)
    if not corpus:
        flash('Корпус не найден', 'error')
        return redirect(url_for('index'))
    
    documents = db.get_documents(corpus_id)
    statistics = db.get_corpus_statistics(corpus_id)
    basic_stats = db.get_corpus_basic_stats(corpus_id)
    
    return render_template('corpus_simple.html', 
                         corpus=corpus, 
                         documents=documents, 
                         statistics=statistics,
                         basic_stats=basic_stats)


@app.route('/corpus/<int:corpus_id>/delete', methods=['POST'])
def delete_corpus(corpus_id: int):
    corpus = db.get_corpus(corpus_id)
    if not corpus:
        flash('Корпус не найден', 'error')
        return redirect(url_for('index'))
    
    if db.delete_corpus(corpus_id):
        flash(f'Корпус "{corpus["name"]}" удален', 'success')
    else:
        flash('Ошибка при удалении корпуса', 'error')
    
    return redirect(url_for('index'))


@app.route('/corpus/<int:corpus_id>/upload', methods=['POST'])
def upload_document(corpus_id):
    corpus = db.get_corpus(corpus_id)
    if not corpus:
        flash('Корпус не найден', 'error')
        return redirect(url_for('index'))
    
    if 'file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('view_corpus', corpus_id=corpus_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('view_corpus', corpus_id=corpus_id))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            text = doc_reader.read_document(filepath)

            try:
                doc_id = db.add_document(
                    corpus_id,
                    filename,
                    request.form.get('title', filename),
                    request.form.get('author', ''),
                    request.form.get('source', ''),
                    request.form.get('genre', ''),
                    text,
                    None
                )
                print(f"Документ успешно добавлен с ID: {doc_id}")
            except Exception as db_error:
                print(f"Ошибка при добавлении документа в БД: {db_error}")
                raise db_error

            os.remove(filepath)
            
            flash(f'Документ "{filename}" добавлен', 'success')
            
        except Exception as e:
            flash(f'Ошибка при обработке файла: {str(e)}', 'error')
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        flash('Неподдерживаемый формат файла', 'error')
    
    return redirect(url_for('view_corpus', corpus_id=corpus_id))


@app.route('/corpus/<int:corpus_id>/morphology')
def morphology_analysis(corpus_id):
    corpus = db.get_corpus(corpus_id)
    if not corpus:
        flash('Корпус не найден', 'error')
        return redirect(url_for('index'))
    
    documents = db.get_documents(corpus_id)
    
    return render_template('morphology_simple.html', 
                         corpus=corpus, 
                         documents=documents)


@app.route('/corpus/<int:corpus_id>/run_morphology', methods=['POST'])
def run_morphology(corpus_id):
    corpus = db.get_corpus(corpus_id)
    if not corpus:
        return jsonify({'error': 'Корпус не найден'})
    
    if not morph_analyzer:
        return jsonify({'error': 'Морфологический анализатор недоступен'})
    
    if not morph_analyzer.is_available():
        return jsonify({'error': 'Морфологический анализатор недоступен'})
    
    documents = db.get_documents(corpus_id)
    processed = 0
    
    for doc in documents:
        try:
            full_doc = db.get_document(doc['id'])
            if not full_doc:
                continue

            wordforms = morph_analyzer.analyze_text(full_doc['raw_text'])

            wordforms_dicts = []
            for wf in wordforms:
                wordforms_dicts.append({
                    'text': wf.text,
                    'lemma': wf.lemma,
                    'morph_tag': {
                        'pos': wf.morph_tag.pos,
                        'case': wf.morph_tag.case,
                        'number': wf.morph_tag.number,
                        'gender': wf.morph_tag.gender,
                        'tense': wf.morph_tag.tense,
                        'aspect': wf.morph_tag.aspect,
                        'voice': wf.morph_tag.voice,
                        'mood': wf.morph_tag.mood,
                        'person': wf.morph_tag.person
                    },
                    'position_in_text': wf.position_in_text
                })
            
            db.update_document_wordforms(doc['id'], wordforms_dicts)

            db.save_concordance(doc['id'], wordforms_dicts, full_doc['raw_text'])
            
            processed += 1
            
        except Exception as e:
            print(f"Ошибка при анализе документа {doc['id']}: {e}")
    
    return jsonify({
        'success': True,
        'processed': processed,
        'total': len(documents)
    })


@app.route('/corpus/<int:corpus_id>/statistics')
def statistics_corpus(corpus_id):
    corpus = db.get_corpus(corpus_id)
    if not corpus:
        flash('Корпус не найден', 'error')
        return redirect(url_for('index'))

    query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'wordform')
    
    if query:
        concordance_data = db.get_concordance(corpus_id, query, limit=50)
    else:
        concordance_data = db.get_concordance(corpus_id, limit=100)

    formatted_concordance = []
    for item in concordance_data:
        left = item['left_context'][-30:] if len(item['left_context']) > 30 else item['left_context']
        right = item['right_context'][:30] if len(item['right_context']) > 30 else item['right_context']
        
        left_part = f"...{left}" if len(item['left_context']) > 30 else left
        right_part = f"{right}..." if len(item['right_context']) > 30 else right

        morph_info = item['morphological_info']
        morph_tags = []
        if morph_info.get('pos'): morph_tags.append(morph_info['pos'])
        if morph_info.get('case'): morph_tags.append(morph_info['case'])
        if morph_info.get('number'): morph_tags.append(morph_info['number'])
        if morph_info.get('gender'): morph_tags.append(morph_info['gender'])
        if morph_info.get('tense'): morph_tags.append(morph_info['tense'])
        
        morph_str = f" [{', '.join(morph_tags)}]" if morph_tags else ""

        formatted_line = f"""
        <div class="concordance-line">
            <span class="left-context">{left_part}</span>
            <span class="keyword">{item['word']}</span>
            <span class="lemma">({item['lemma']})</span>
            <span class="morph-info">{morph_str}</span>
            <span class="right-context">{right_part}</span>
            <span class="source">({item['document_title']}, автор: {item['document_author']}, жанр: {item['document_genre']}, позиция {item['position']})</span>
        </div>
        """
        formatted_concordance.append(formatted_line)
    
    return render_template('statistics_simple.html', 
                         corpus=corpus, 
                         query=query,
                         search_type=search_type,
                         results=formatted_concordance,
                         results_count=len(concordance_data))


@app.route('/corpus/<int:corpus_id>/search')
def search_corpus(corpus_id):
    corpus = db.get_corpus(corpus_id)
    if not corpus:
        flash('Корпус не найден', 'error')
        return redirect(url_for('index'))
    
    query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'wordform')
    results = []
    concordance_lines = []
    
    if query:
        search_results = db.search_wordforms(corpus_id, query, search_type)

        if search_results:
            documents = db.get_documents(corpus_id)
            full_documents = []

            for doc in documents:
                full_doc = db.get_document(doc['id'])
                if full_doc:
                    full_documents.append(full_doc)

            concordance_builder = ConcordanceBuilder(context_size=10)
            concordance_lines = concordance_builder.build_concordance(full_documents, search_results)

            results = [concordance_builder.format_concordance_html(line) for line in concordance_lines]
    
    return render_template('search_simple.html', 
                         corpus=corpus, 
                         query=query,
                         search_type=search_type,
                         results=results,
                         results_count=len(concordance_lines))


@app.route('/api/corpus/<int:corpus_id>/statistics')
def api_statistics(corpus_id):
    stats = db.get_corpus_statistics(corpus_id)
    return jsonify(stats)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
