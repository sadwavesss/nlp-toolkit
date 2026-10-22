#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "dialog_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dialogues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP NULL,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dialogue_id INTEGER,
                    sender TEXT CHECK(sender IN ('user', 'system')),
                    message_text TEXT,
                    intent TEXT NULL,
                    entities TEXT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dialogue_id) REFERENCES dialogues(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS animals_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    category TEXT,
                    habitat TEXT,
                    diet TEXT,
                    size TEXT,
                    lifespan TEXT,
                    interesting_facts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            self.populate_sample_data()
    
    def populate_sample_data(self):
        sample_animals = [
            {
                "name": "тигр",
                "category": "хищник",
                "habitat": "Азия, леса и саванны",
                "diet": "мясо",
                "size": "до 300 кг",
                "lifespan": "10-15 лет в дикой природе",
                "interesting_facts": "Самые большие кошачьи в мире. Могут прыгать до 10 метров в длину."
            },
            {
                "name": "лев",
                "category": "хищник",
                "habitat": "Африка, саванны",
                "diet": "мясо",
                "size": "до 250 кг",
                "lifespan": "10-14 лет в дикой природе",
                "interesting_facts": "Единственные социальные кошачьи. Живут в прайдах."
            },
            {
                "name": "пингвин",
                "category": "птица",
                "habitat": "Антарктида, Южное полушарие",
                "diet": "рыба, криль",
                "size": "40-120 см в зависимости от вида",
                "lifespan": "15-20 лет",
                "interesting_facts": "Могут задерживать дыхание до 22 минут. Плавают со скоростью до 35 км/ч."
            },
            {
                "name": "дельфин",
                "category": "млекопитающее",
                "habitat": "Мировой океан",
                "diet": "рыба, кальмары",
                "size": "2-4 метра",
                "lifespan": "20-45 лет",
                "interesting_facts": "Используют эхолокацию для охоты. Спят только одним полушарием мозга."
            },
            {
                "name": "слон",
                "category": "травоядное",
                "habitat": "Африка, Азия, саванны и леса",
                "diet": "трава, листья, фрукты",
                "size": "до 6000 кг",
                "lifespan": "60-70 лет",
                "interesting_facts": "Обладают превосходной памятью. Могут общаться инфразвуком."
            },
            {
                "name": "медведь",
                "category": "всеядное",
                "habitat": "леса Северного полушария",
                "diet": "рыба, ягоды, мёд, мясо",
                "size": "до 800 кг",
                "lifespan": "20-30 лет",
                "interesting_facts": "Впадают в зимнюю спячку до 7 месяцев."
            },
            {
                "name": "гепард",
                "category": "хищник",
                "habitat": "Африка, саванны",
                "diet": "мясо",
                "size": "до 65 кг",
                "lifespan": "10-12 лет",
                "interesting_facts": "Самое быстрое наземное животное — развивает скорость до 120 км/ч."
            },
            {
                "name": "волк",
                "category": "хищник",
                "habitat": "леса и тундра Евразии и Северной Америки",
                "diet": "мясо",
                "size": "до 80 кг",
                "lifespan": "6-8 лет в дикой природе",
                "interesting_facts": "Живут стаями со строгой иерархией. Могут пробегать до 70 км в день."
            },
            {
                "name": "жираф",
                "category": "травоядное",
                "habitat": "Африка, саванны",
                "diet": "листья акации",
                "size": "до 5.5 метров в высоту",
                "lifespan": "20-25 лет",
                "interesting_facts": "Самое высокое наземное животное. Язык до 50 см."
            },
            {
                "name": "акула",
                "category": "хищник",
                "habitat": "Мировой океан",
                "diet": "рыба, морские млекопитающие",
                "size": "до 12 метров (большая белая)",
                "lifespan": "20-30 лет",
                "interesting_facts": "Существуют более 400 миллионов лет — древнее динозавров."
            }
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for animal in sample_animals:
                cursor.execute("""
                    INSERT OR IGNORE INTO animals_knowledge 
                    (name, category, habitat, diet, size, lifespan, interesting_facts)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    animal["name"], animal["category"], animal["habitat"],
                    animal["diet"], animal["size"], animal["lifespan"],
                    animal["interesting_facts"]
                ))
            conn.commit()
    
    def create_dialogue(self, session_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM dialogues WHERE session_id = ?",
                (session_id,)
            )
            existing = cursor.fetchone()

            if existing:
                dialogue_id = existing[0]
                cursor.execute(
                    "UPDATE dialogues SET status = 'active', ended_at = NULL WHERE id = ?",
                    (dialogue_id,)
                )
                conn.commit()
                return dialogue_id
            else:
                cursor.execute(
                    "INSERT INTO dialogues (session_id) VALUES (?)",
                    (session_id,)
                )
                conn.commit()
                return cursor.lastrowid
    
    def add_message(self, dialogue_id: int, sender: str, message: str, 
                   intent: Optional[str] = None, entities: Optional[List] = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (dialogue_id, sender, message_text, intent, entities)
                VALUES (?, ?, ?, ?, ?)
            """, (dialogue_id, sender, message, intent, json.dumps(entities) if entities else None))
            conn.commit()
    
    def get_dialogue_messages(self, dialogue_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sender, message_text, intent, entities, timestamp
                FROM messages 
                WHERE dialogue_id = ? 
                ORDER BY timestamp ASC
            """, (dialogue_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "sender": row["sender"],
                    "message": row["message_text"],
                    "intent": row["intent"],
                    "entities": json.loads(row["entities"]) if row["entities"] else None,
                    "timestamp": row["timestamp"]
                })
            return messages
    
    def get_animal_info(self, animal_name: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM animals_knowledge 
                WHERE LOWER(name) = LOWER(?)
            """, (animal_name,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def search_animals(self, query: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM animals_knowledge 
                WHERE LOWER(name) LIKE LOWER(?) 
                   OR LOWER(category) LIKE LOWER(?)
                   OR LOWER(habitat) LIKE LOWER(?)
                   OR LOWER(diet) LIKE LOWER(?)
            """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))

            return [dict(row) for row in cursor.fetchall()]

    def get_all_animals(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM animals_knowledge ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_dialogues(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    d.id,
                    d.session_id,
                    d.created_at,
                    d.ended_at,
                    d.status,
                    COUNT(m.id) as message_count,
                    (SELECT message_text FROM messages
                     WHERE dialogue_id = d.id AND sender = 'user'
                     ORDER BY timestamp ASC LIMIT 1) as first_user_message,
                    (SELECT message_text FROM messages
                     WHERE dialogue_id = d.id AND sender = 'system'
                     ORDER BY timestamp ASC LIMIT 1) as first_system_message,
                    (SELECT intent FROM messages
                     WHERE dialogue_id = d.id AND intent IS NOT NULL
                     ORDER BY timestamp ASC LIMIT 1) as first_intent,
                    (SELECT entities FROM messages
                     WHERE dialogue_id = d.id AND entities IS NOT NULL
                     ORDER BY timestamp ASC LIMIT 1) as first_entities
                FROM dialogues d
                LEFT JOIN messages m ON m.dialogue_id = d.id
                GROUP BY d.id
                HAVING message_count > 0
                ORDER BY d.created_at DESC
            """)
            result = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("first_entities"):
                    try:
                        item["first_entities"] = json.loads(item["first_entities"])
                    except (json.JSONDecodeError, TypeError):
                        item["first_entities"] = None
                result.append(item)
            return result

    def get_statistics(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM dialogues")
            total_dialogues = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM dialogues
                WHERE id IN (SELECT DISTINCT dialogue_id FROM messages)
            """)
            non_empty_dialogues = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]

            cursor.execute("""
                SELECT entities FROM messages
                WHERE entities IS NOT NULL
            """)
            unique_animals = set()
            for (entities_json,) in cursor.fetchall():
                try:
                    ents = json.loads(entities_json)
                    for e in ents or []:
                        if e.get("type") == "ANIMAL":
                            unique_animals.add(e.get("text", "").lower())
                except (json.JSONDecodeError, TypeError):
                    continue

            cursor.execute("""
                SELECT intent, COUNT(*) as cnt
                FROM messages
                WHERE intent IS NOT NULL
                GROUP BY intent
                ORDER BY cnt DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            top_intent = row[0] if row else "—"

            cursor.execute("""
                SELECT intent, COUNT(*) as cnt
                FROM messages
                WHERE intent IS NOT NULL
                GROUP BY intent
                ORDER BY cnt DESC
            """)
            intent_distribution = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "total_dialogues": non_empty_dialogues,
                "total_dialogues_all": total_dialogues,
                "total_messages": total_messages,
                "unique_animals": len(unique_animals),
                "top_intent": top_intent,
                "intent_distribution": intent_distribution,
            }
