import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime


class CorpusDatabase:
    
    def __init__(self, db_path: str = "corpus.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS corpora (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    corpus_id INTEGER,
                    filename TEXT NOT NULL,
                    title TEXT,
                    author TEXT,
                    source TEXT,
                    genre TEXT,
                    raw_text TEXT NOT NULL,
                    wordforms TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (corpus_id) REFERENCES corpora (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS concordance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    word TEXT NOT NULL,
                    lemma TEXT,
                    left_context TEXT,
                    right_context TEXT,
                    position INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            """)
            
            conn.commit()
    
    def create_corpus(self, name: str, description: str = "") -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO corpora (name, description) VALUES (?, ?)",
                (name, description)
            )
            corpus_id = cursor.lastrowid
            conn.commit()
            return corpus_id
    
    def get_corpora(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, created_at 
                FROM corpora 
                ORDER BY created_at DESC
            """)
            
            corpora = []
            for row in cursor.fetchall():
                corpora.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'created_at': row[3]
                })
            return corpora
    
    def get_corpus(self, corpus_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, description, created_at FROM corpora WHERE id = ?",
                (corpus_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'created_at': row[3]
                }
            return None
    
    def delete_corpus(self, corpus_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM concordance 
                WHERE document_id IN (
                    SELECT id FROM documents WHERE corpus_id = ?
                )
            """, (corpus_id,))

            cursor.execute("DELETE FROM documents WHERE corpus_id = ?", (corpus_id,))

            cursor.execute("DELETE FROM corpora WHERE id = ?", (corpus_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_corpus_basic_stats(self, corpus_id: int) -> Dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT COUNT(*) FROM documents WHERE corpus_id = ?",
                    (corpus_id,)
                )
                doc_count = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT wordforms FROM documents WHERE corpus_id = ?",
                    (corpus_id,)
                )
                documents = cursor.fetchall()
                
                total_wordforms = 0
                for wordforms_json, in documents:
                    if wordforms_json and wordforms_json.strip():
                        try:
                            wordforms = json.loads(wordforms_json)
                            if isinstance(wordforms, list):
                                total_wordforms += len(wordforms)
                        except:
                            pass
                
                return {
                    'documents_count': doc_count,
                    'wordforms_count': total_wordforms
                }
        except Exception as e:
            print(f"Ошибка при получении базовой статистики корпуса {corpus_id}: {e}")
            return {
                'documents_count': 0,
                'wordforms_count': 0
            }
    
    def add_document(self, corpus_id: int, filename: str, title: str,
                   author: str, source: str, genre: str, raw_text: str,
                   wordforms: List[Dict] = None) -> int:
        wordforms_json = json.dumps(wordforms) if wordforms else "[]"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents 
                (corpus_id, filename, title, author, source, genre, raw_text, wordforms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (corpus_id, filename, title, author, source, genre, raw_text, wordforms_json))
            
            doc_id = cursor.lastrowid
            conn.commit()
            return doc_id
    
    def get_documents(self, corpus_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, title, author, source, genre, created_at
                FROM documents 
                WHERE corpus_id = ?
                ORDER BY created_at DESC
            """, (corpus_id,))
            
            documents = []
            for row in cursor.fetchall():
                documents.append({
                    'id': row[0],
                    'filename': row[1],
                    'title': row[2],
                    'author': row[3],
                    'source': row[4],
                    'genre': row[5],
                    'created_at': row[6]
                })
            return documents
    
    def get_document(self, doc_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, title, author, source, genre, raw_text, wordforms
                FROM documents 
                WHERE id = ?
            """, (doc_id,))
            
            row = cursor.fetchone()
            if row:
                wordforms = json.loads(row[7]) if row[7] else []
                return {
                    'id': row[0],
                    'filename': row[1],
                    'title': row[2],
                    'author': row[3],
                    'source': row[4],
                    'genre': row[5],
                    'raw_text': row[6],
                    'wordforms': wordforms
                }
            return None
    
    def update_document_wordforms(self, doc_id: int, wordforms_dicts: List[Dict]):
        wordforms_json = json.dumps(wordforms_dicts)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE documents SET wordforms = ? WHERE id = ?",
                (wordforms_json, doc_id)
            )
            conn.commit()
    
    def search_wordforms(self, corpus_id: int, query: str, search_type: str = "wordform") -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, title, wordforms
                FROM documents 
                WHERE corpus_id = ?
            """, (corpus_id,))
            
            results = []
            for row in cursor.fetchall():
                doc_id, filename, title, wordforms_json = row
                wordforms = json.loads(wordforms_json) if wordforms_json else []
                
                for wf in wordforms:
                    match = False
                    if search_type == "wordform" and query.lower() in wf.get('text', '').lower():
                        match = True
                    elif search_type == "lemma" and query.lower() in wf.get('lemma', '').lower():
                        match = True
                    
                    if match:
                        results.append({
                            'document_id': doc_id,
                            'document_title': title,
                            'wordform': wf,
                            'word': wf.get('text', ''),
                            'position': wf.get('position_in_text', 0)
                        })
            
            return results
    
    def save_concordance(self, document_id: int, wordforms: List[Dict], raw_text: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM concordance WHERE document_id = ?", (document_id,))

            words = raw_text.split()
            
            for index, wf in enumerate(wordforms):
                word = wf.get('text', '')
                lemma = wf.get('lemma', '')
                position = index

                context_size = 5
                left_start = max(0, position - context_size)
                right_end = min(len(wordforms), position + context_size + 1)

                left_words = [wordforms[i].get('text', '') for i in range(left_start, position)]
                right_words = [wordforms[i].get('text', '') for i in range(position + 1, right_end)]
                
                left_context = ' '.join(left_words)
                right_context = ' '.join(right_words)
                
                cursor.execute("""
                    INSERT INTO concordance 
                    (document_id, word, lemma, left_context, right_context, position)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (document_id, word, lemma, left_context, right_context, position))
            
            conn.commit()
    
    def get_concordance(self, corpus_id: int, query: str = None, limit: int = 100) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if query:
                cursor.execute("""
                    SELECT c.word, c.lemma, c.left_context, c.right_context, c.position, 
                           d.title, d.filename, d.author, d.source, d.genre, d.wordforms
                    FROM concordance c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.corpus_id = ? AND (c.word LIKE ? OR c.lemma LIKE ?)
                    ORDER BY c.word, c.position
                    LIMIT ?
                """, (corpus_id, f"%{query}%", f"%{query}%", limit))
            else:
                cursor.execute("""
                    SELECT c.word, c.lemma, c.left_context, c.right_context, c.position,
                           d.title, d.filename, d.author, d.source, d.genre, d.wordforms
                    FROM concordance c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.corpus_id = ?
                    ORDER BY c.word, c.position
                    LIMIT ?
                """, (corpus_id, limit))
            
            results = []
            for row in cursor.fetchall():
                word, lemma, left_context, right_context, position = row[0:5]
                title, filename, author, source, genre, wordforms_json = row[5:11]

                morph_info = {}
                if wordforms_json:
                    try:
                        wordforms = json.loads(wordforms_json)
                        if position < len(wordforms):
                            wf = wordforms[position]
                            if isinstance(wf, dict) and 'morph_tag' in wf:
                                morph_tag = wf['morph_tag']
                                if isinstance(morph_tag, dict):
                                    morph_info = {
                                        'pos': morph_tag.get('pos', ''),
                                        'case': morph_tag.get('case', ''),
                                        'number': morph_tag.get('number', ''),
                                        'gender': morph_tag.get('gender', ''),
                                        'tense': morph_tag.get('tense', ''),
                                        'aspect': morph_tag.get('aspect', ''),
                                        'voice': morph_tag.get('voice', ''),
                                        'mood': morph_tag.get('mood', ''),
                                        'person': morph_tag.get('person', '')
                                    }
                    except:
                        pass
                
                results.append({
                    'word': word,
                    'lemma': lemma,
                    'left_context': left_context,
                    'right_context': right_context,
                    'position': position,
                    'document_title': title or filename,
                    'document_filename': filename,
                    'document_author': author or 'Не указан',
                    'document_source': source or 'Не указан',
                    'document_genre': genre or 'Не указан',
                    'morphological_info': morph_info
                })
            
            return results
    
    def get_corpus_statistics(self, corpus_id: int) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, filename, title, author, source, genre, raw_text, wordforms FROM documents WHERE corpus_id = ?",
                (corpus_id,)
            )
            documents = cursor.fetchall()

            total_wordforms = 0
            total_characters = 0
            wordform_counts = {}
            lemma_counts = {}
            pos_counts = {}
            case_counts = {}
            number_counts = {}
            gender_counts = {}
            tense_counts = {}
            aspect_counts = {}
            voice_counts = {}
            mood_counts = {}

            documents_metadata = []
            
            for doc_id, filename, title, author, source, genre, raw_text, wordforms_json in documents:
                doc_metadata = {
                    'id': doc_id,
                    'filename': filename,
                    'title': title or filename,
                    'author': author or 'Не указан',
                    'source': source or 'Не указан',
                    'genre': genre or 'Не указан',
                    'characters': len(raw_text) if raw_text else 0
                }
                documents_metadata.append(doc_metadata)

                if raw_text:
                    total_characters += len(raw_text)

                if wordforms_json:
                    try:
                        wordforms = json.loads(wordforms_json)
                        total_wordforms += len(wordforms)
                        
                        for wf in wordforms:
                            if isinstance(wf, dict):
                                word = wf.get('text', '')
                                if word:
                                    wordform_counts[word] = wordform_counts.get(word, 0) + 1

                                lemma = wf.get('lemma', '')
                                if lemma:
                                    lemma_counts[lemma] = lemma_counts.get(lemma, 0) + 1

                                morph_tag = wf.get('morph_tag', {})
                                if isinstance(morph_tag, dict):
                                    pos = morph_tag.get('pos', '')
                                    if pos:
                                        pos_counts[pos] = pos_counts.get(pos, 0) + 1

                                    case = morph_tag.get('case', '')
                                    if case:
                                        case_counts[case] = case_counts.get(case, 0) + 1

                                    number = morph_tag.get('number', '')
                                    if number:
                                        number_counts[number] = number_counts.get(number, 0) + 1

                                    gender = morph_tag.get('gender', '')
                                    if gender:
                                        gender_counts[gender] = gender_counts.get(gender, 0) + 1

                                    tense = morph_tag.get('tense', '')
                                    if tense:
                                        tense_counts[tense] = tense_counts.get(tense, 0) + 1

                                    aspect = morph_tag.get('aspect', '')
                                    if aspect:
                                        aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1

                                    voice = morph_tag.get('voice', '')
                                    if voice:
                                        voice_counts[voice] = voice_counts.get(voice, 0) + 1

                                    mood = morph_tag.get('mood', '')
                                    if mood:
                                        mood_counts[mood] = mood_counts.get(mood, 0) + 1
                    except:
                        pass

            words_statistics = {}
            
            for doc_id, filename, title, author, source, genre, raw_text, wordforms_json in documents:
                if wordforms_json and wordforms_json.strip():
                    try:
                        wordforms = json.loads(wordforms_json)
                        if not isinstance(wordforms, list):
                            continue
                            
                        for wf in wordforms:
                            if isinstance(wf, dict):
                                word = wf.get('text', '')
                                lemma = wf.get('lemma', '')
                                
                                if word and word.strip():
                                    word = word.strip()
                                    if word not in words_statistics:
                                        words_statistics[word] = {
                                            'word': word,
                                            'lemma': lemma or '',
                                            'pos': set(),
                                            'case': set(),
                                            'number': set(),
                                            'gender': set(),
                                            'tense': set(),
                                            'count': 0
                                        }
                                    
                                    words_statistics[word]['count'] += 1

                                    morph_tag = wf.get('morph_tag', {})
                                    if isinstance(morph_tag, dict):
                                        pos = morph_tag.get('pos', '')
                                        if pos and pos.strip():
                                            words_statistics[word]['pos'].add(pos.strip())
                                        
                                        case = morph_tag.get('case', '')
                                        if case and case.strip():
                                            words_statistics[word]['case'].add(case.strip())
                                        
                                        number = morph_tag.get('number', '')
                                        if number and number.strip():
                                            words_statistics[word]['number'].add(number.strip())
                                        
                                        gender = morph_tag.get('gender', '')
                                        if gender and gender.strip():
                                            words_statistics[word]['gender'].add(gender.strip())
                                        
                                        tense = morph_tag.get('tense', '')
                                        if tense and tense.strip():
                                            words_statistics[word]['tense'].add(tense.strip())
                    except Exception as e:
                        print(f"Ошибка при обработке словоформ: {e}")
                        continue

            words_table = []
            for word_data in words_statistics.values():
                words_table.append({
                    'word': word_data['word'],
                    'lemma': word_data['lemma'],
                    'pos': ', '.join(sorted(word_data['pos'])) if word_data['pos'] else '-',
                    'case': ', '.join(sorted(word_data['case'])) if word_data['case'] else '-',
                    'number': ', '.join(sorted(word_data['number'])) if word_data['number'] else '-',
                    'gender': ', '.join(sorted(word_data['gender'])) if word_data['gender'] else '-',
                    'tense': ', '.join(sorted(word_data['tense'])) if word_data['tense'] else '-',
                    'count': word_data['count'],
                    'percentage': round((word_data['count'] / total_wordforms) * 100, 2) if total_wordforms > 0 else 0
                })
            
            words_table.sort(key=lambda x: x['count'], reverse=True)

            if not words_table:
                words_table = []
            
            return {
                'documents_count': len(documents),
                'wordforms_count': total_wordforms,
                'characters_count': total_characters,
                'unique_wordforms_count': len(wordform_counts),
                'unique_lemmas_count': len(lemma_counts),
                'words_table': words_table,
                'documents_metadata': documents_metadata
            }
