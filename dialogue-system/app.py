#!/usr/bin/env python3
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request, session

from database_manager import DatabaseManager
from nlp_processor import NLPProcessor
from response_generator import ResponseGenerator

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

db_manager = DatabaseManager()
nlp_processor = NLPProcessor()
response_generator = ResponseGenerator(db_manager)

active_dialogues: Dict[str, Dict[str, Any]] = {}



def _get_or_create_dialogue() -> Dict[str, Any]:
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    session_id = session["session_id"]
    if session_id not in active_dialogues:
        dialogue_id = db_manager.create_dialogue(session_id)
        active_dialogues[session_id] = {
            "dialogue_id": dialogue_id,
            "context": [],
            "last_animal": None,
        }
    return active_dialogues[session_id]



@app.route("/")
def index():
    _get_or_create_dialogue()
    return render_template("index.html")



@app.route("/api/send_message", methods=["POST"])
def send_message():
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Сообщение не может быть пустым"}), 400

        dialogue_info = _get_or_create_dialogue()
        dialogue_id = dialogue_info["dialogue_id"]

        nlp_result = nlp_processor.analyze_text(user_message)

        db_manager.add_message(
            dialogue_id,
            "user",
            user_message,
            nlp_result["intent"],
            nlp_result["entities"],
        )

        system_response = response_generator.generate_response(
            nlp_result, dialogue_info["context"]
        )

        db_manager.add_message(dialogue_id, "system", system_response, None, None)

        dialogue_info["context"].append({
            "user": user_message,
            "system": system_response,
            "intent": nlp_result["intent"],
            "timestamp": datetime.now().isoformat(),
        })
        for entity in nlp_result.get("entities", []):
            if entity.get("type") == "ANIMAL":
                dialogue_info["last_animal"] = entity["text"]
                break

        return jsonify({
            "response": system_response,
            "intent": nlp_result["intent"],
            "entities": nlp_result.get("entities", []),
            "confidence": nlp_result.get("confidence", 0.0),
        })
    except Exception as e:  # pragma: no cover
        return jsonify({"error": f"Внутренняя ошибка: {e}"}), 500


@app.route("/api/get_history")
def get_history():
    try:
        session_id = session.get("session_id")
        if not session_id or session_id not in active_dialogues:
            return jsonify({"history": []})

        dialogue_id = active_dialogues[session_id]["dialogue_id"]
        messages = db_manager.get_dialogue_messages(dialogue_id)
        return jsonify({"history": messages})
    except Exception as e:  # pragma: no cover
        return jsonify({"error": f"Ошибка загрузки истории: {e}"}), 500


@app.route("/api/new_dialogue", methods=["POST"])
def new_dialogue():
    try:
        old_session_id = session.get("session_id")
        if old_session_id and old_session_id in active_dialogues:
            old_dialogue_id = active_dialogues[old_session_id]["dialogue_id"]
            import sqlite3
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE dialogues SET status = 'ended', ended_at = ? WHERE id = ?",
                    (datetime.now(), old_dialogue_id),
                )
                conn.commit()
            del active_dialogues[old_session_id]

        session["session_id"] = str(uuid.uuid4())
        info = _get_or_create_dialogue()
        return jsonify({"success": True, "dialogue_id": info["dialogue_id"]})
    except Exception as e:  # pragma: no cover
        return jsonify({"error": f"Ошибка создания диалога: {e}"}), 500


@app.route("/api/end_dialogue", methods=["POST"])
def end_dialogue():
    try:
        session_id = session.get("session_id")
        if session_id and session_id in active_dialogues:
            dialogue_id = active_dialogues[session_id]["dialogue_id"]
            import sqlite3
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE dialogues SET status = 'ended', ended_at = ? WHERE id = ?",
                    (datetime.now(), dialogue_id),
                )
                conn.commit()
            del active_dialogues[session_id]
        return jsonify({"success": True})
    except Exception as e:  # pragma: no cover
        return jsonify({"error": f"Ошибка завершения диалога: {e}"}), 500



@app.route("/api/dialogues")
def list_dialogues():
    try:
        dialogues = db_manager.get_all_dialogues()
        return jsonify({"dialogues": dialogues})
    except Exception as e:  # pragma: no cover
        return jsonify({"error": f"Ошибка: {e}"}), 500


@app.route("/api/dialogue/<int:dialogue_id>")
def get_dialogue(dialogue_id: int):
    try:
        messages = db_manager.get_dialogue_messages(dialogue_id)
        return jsonify({"dialogue_id": dialogue_id, "messages": messages})
    except Exception as e:  # pragma: no cover
        return jsonify({"error": f"Ошибка: {e}"}), 500



@app.route("/api/animals")
def list_animals():
    try:
        animals = db_manager.get_all_animals()
        return jsonify({"animals": animals})
    except Exception as e:  # pragma: no cover
        return jsonify({"error": f"Ошибка: {e}"}), 500


@app.route("/api/statistics")
def get_statistics():
    try:
        return jsonify(db_manager.get_statistics())
    except Exception as e:  # pragma: no cover
        return jsonify({"error": f"Ошибка: {e}"}), 500



if __name__ == "__main__":
    print("=" * 60)
    print("ДИАЛОГОВАЯ СИСТЕМА «ЖИВОТНЫЕ МИРА»")
    print("Лабораторная работа №6 — полнофункциональная реализация")
    print("=" * 60)
    print("Веб-интерфейс:  http://localhost:5003")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5003, debug=True)
