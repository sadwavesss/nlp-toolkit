#!/usr/bin/env python3
from __future__ import annotations

import random
from typing import Dict, List, Optional

from database_manager import DatabaseManager
from nlp_processor import ANIMAL_FORMS



GREETINGS = [
    "Здравствуйте! 🦁 Я — диалоговая система по тематике «Животные мира». Чем могу помочь?",
    "Привет! 🐾 Готов рассказать всё о животных. О ком хотите узнать?",
    "Добрый день! 🐅 Спросите меня про любое известное мне животное.",
    "Приветствую! 🐬 Расскажу про среду обитания, питание, интересные факты или сравню двух животных.",
]

GOODBYES = [
    "До свидания! 👋 Возвращайтесь, в мире животных столько всего интересного!",
    "Всего доброго! 🌿 Берегите природу и её обитателей.",
    "Пока! 🐘 Спасибо за интерес к миру животных.",
    "До встречи! 🦒 Было приятно пообщаться.",
]

UNKNOWN = [
    "Извините, я не совсем понял вопрос. Можете перефразировать?",
    "Не уверен, что правильно понял. Моя специализация — животные. Попробуйте: «Расскажи про тигра» или «Где живут пингвины?»",
    "Кажется, в вашем вопросе нет названия животного. Подскажите, кто вас интересует?",
    "Я отвечаю только на вопросы о животных. Спросите, например: «Что едят волки?»",
]

FOLLOW_UPS = [
    "💬 Хотите узнать что-то ещё?",
    "💡 Может быть, интересно сравнить с другим животным?",
    "🌍 Спросите про среду обитания или питание!",
    "📚 Есть и другие интересные виды в моей базе.",
    "❓ Что ещё рассказать?",
]


def _emoji(animal: str) -> str:
    table = {
        "тигр": "🐅", "лев": "🦁", "гепард": "🐆", "волк": "🐺",
        "медведь": "🐻", "лиса": "🦊", "пингвин": "🐧", "дельфин": "🐬",
        "слон": "🐘", "жираф": "🦒", "зебра": "🦓", "акула": "🦈",
        "кит": "🐋", "обезьяна": "🐒", "кролик": "🐇", "лошадь": "🐎",
        "корова": "🐄", "собака": "🐕", "кошка": "🐈", "крокодил": "🐊",
        "носорог": "🦏", "бегемот": "🦛", "мышь": "🐁", "заяц": "🐇",
    }
    return table.get(animal.lower(), "🐾")


def _capitalize(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s



class ResponseGenerator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def generate_response(self, nlp_result: Dict,
                          dialogue_context: Optional[List] = None) -> str:
        intent = nlp_result.get("intent", "unknown")
        entities = nlp_result.get("entities", [])
        animals = nlp_result.get("animals") or [
            e["text"] for e in entities if e.get("type") == "ANIMAL"
        ]

        if not animals and dialogue_context:
            for prev in reversed(dialogue_context):
                if prev.get("animal"):
                    animals = [prev["animal"]]
                    break

        animals = [self._normalize(a) for a in animals]

        handlers = {
            "greeting": self._greeting,
            "goodbye": self._goodbye,
            "animal_info": self._animal_info,
            "compare_animals": self._compare,
            "habitat_query": self._habitat,
            "diet_query": self._diet,
            "facts_query": self._facts,
            "unknown": self._unknown,
        }
        handler = handlers.get(intent, self._unknown)
        return handler(animals)


    def _greeting(self, animals: List[str]) -> str:
        msg = random.choice(GREETINGS)
        return f"{msg}\n\nПопробуйте: «Расскажи про льва», «Где живут пингвины?», «Сравни тигра и гепарда»."

    def _goodbye(self, animals: List[str]) -> str:
        return random.choice(GOODBYES)

    def _unknown(self, animals: List[str]) -> str:
        suggestions = [
            "💡 Например: «Расскажи про тигров»",
            "💡 Или: «Где обитают пингвины?»",
            "💡 Можно сравнить: «Кто быстрее — лев или гепард?»",
            "💡 Спросить факты: «Интересные факты про дельфинов»",
        ]
        return f"{random.choice(UNKNOWN)}\n\n{random.choice(suggestions)}"

    def _animal_info(self, animals: List[str]) -> str:
        if not animals:
            return ("О каком животном вы хотите узнать? "
                    "Например: «Расскажи про слона».")

        animal = animals[0]
        info = self.db.get_animal_info(animal)
        if not info:
            return self._not_found(animal)

        intros = [
            f"{_emoji(animal)} **{_capitalize(animal)}** — это {info['category']}.",
            f"{_emoji(animal)} Поговорим о таком животном, как **{_capitalize(animal)}**. Это {info['category']}.",
            f"{_emoji(animal)} **{_capitalize(animal)}** относится к категории «{info['category']}».",
        ]

        response = random.choice(intros) + "\n\n"
        response += f"🌍 **Среда обитания:** {info['habitat']}\n"
        response += f"🍖 **Питание:** {info['diet']}\n"
        response += f"📏 **Размер:** {info['size']}\n"
        response += f"⏳ **Продолжительность жизни:** {info['lifespan']}\n\n"
        response += f"💡 **Интересный факт:** {info['interesting_facts']}\n\n"
        response += random.choice(FOLLOW_UPS)
        return response

    def _compare(self, animals: List[str]) -> str:
        if len(animals) < 2:
            if len(animals) == 1:
                return (f"Для сравнения мне нужно ещё одно животное. "
                        f"С кем сравнить {_emoji(animals[0])} {animals[0]}? "
                        f"Например: «Сравни {animals[0]} и медведя».")
            return ("Для сравнения укажите двух животных. Например: "
                    "«Кто быстрее — лев или гепард?» или «Сравни тигра и волка».")

        a1, a2 = animals[0], animals[1]
        info1 = self.db.get_animal_info(a1)
        info2 = self.db.get_animal_info(a2)

        missing = [a for a, i in [(a1, info1), (a2, info2)] if not i]
        if missing:
            return self._not_found_multi(missing)

        intros = [
            f"⚡ Сравниваем {_emoji(a1)} **{a1}** и {_emoji(a2)} **{a2}**:",
            f"🔍 Давайте посмотрим на различия между {_emoji(a1)} {a1} и {_emoji(a2)} {a2}:",
            f"⚖️ Параллельное сравнение {_emoji(a1)} {a1} vs {_emoji(a2)} {a2}:",
        ]
        response = random.choice(intros) + "\n\n"

        response += f"**{_capitalize(a1)}** {_emoji(a1)}\n"
        response += f"  • Категория: {info1['category']}\n"
        response += f"  • Среда: {info1['habitat']}\n"
        response += f"  • Питание: {info1['diet']}\n"
        response += f"  • Размер: {info1['size']}\n"
        response += f"  • Жизнь: {info1['lifespan']}\n\n"

        response += f"**{_capitalize(a2)}** {_emoji(a2)}\n"
        response += f"  • Категория: {info2['category']}\n"
        response += f"  • Среда: {info2['habitat']}\n"
        response += f"  • Питание: {info2['diet']}\n"
        response += f"  • Размер: {info2['size']}\n"
        response += f"  • Жизнь: {info2['lifespan']}\n\n"

        conclusions = []
        if info1["category"] == info2["category"]:
            conclusions.append(
                f"🟰 Оба относятся к категории «{info1['category']}»."
            )
        else:
            conclusions.append(
                f"🆚 Они относятся к разным категориям: "
                f"**{a1}** — {info1['category']}, **{a2}** — {info2['category']}."
            )

        if info1["habitat"] != info2["habitat"]:
            conclusions.append(
                f"🌍 Обитают в разных местах: **{a1}** — {info1['habitat']}; "
                f"**{a2}** — {info2['habitat']}."
            )

        if info1["diet"] != info2["diet"]:
            conclusions.append(
                f"🍽 Питаются по-разному: **{a1}** — {info1['diet']}; "
                f"**{a2}** — {info2['diet']}."
            )

        response += "**Выводы:**\n" + "\n".join(conclusions) + "\n\n"
        response += random.choice(FOLLOW_UPS)
        return response

    def _habitat(self, animals: List[str]) -> str:
        if not animals:
            return "О каком животном вы хотите узнать среду обитания? Назовите его."

        animal = animals[0]
        info = self.db.get_animal_info(animal)
        if not info:
            return self._not_found(animal)

        templates = [
            f"🌍 {_emoji(animal)} **{_capitalize(animal)}** обитает в: **{info['habitat']}**.",
            f"🌍 Среда обитания {_emoji(animal)} {animal}а — **{info['habitat']}**.",
            f"📍 {_capitalize(animal)} ({_emoji(animal)}) можно встретить в: **{info['habitat']}**.",
        ]
        response = random.choice(templates) + "\n\n"
        response += f"Это {info['category']}, размером {info['size']}.\n"
        response += f"Питается {info['diet']}.\n\n"
        response += random.choice(FOLLOW_UPS)
        return response

    def _diet(self, animals: List[str]) -> str:
        if not animals:
            return "О каком животном вы хотите узнать питание? Назовите его."

        animal = animals[0]
        info = self.db.get_animal_info(animal)
        if not info:
            return self._not_found(animal)

        templates = [
            f"🍖 {_emoji(animal)} **{_capitalize(animal)}** питается: **{info['diet']}**.",
            f"🍽 Рацион {_emoji(animal)} {animal}а состоит из: **{info['diet']}**.",
            f"🥩 Основная пища {_capitalize(animal)} ({_emoji(animal)}) — **{info['diet']}**.",
        ]
        response = random.choice(templates) + "\n\n"
        response += f"Это {info['category']}, обитает в {info['habitat']}.\n\n"
        response += f"💡 Интересно: {info['interesting_facts']}\n\n"
        response += random.choice(FOLLOW_UPS)
        return response

    def _facts(self, animals: List[str]) -> str:
        if not animals:
            all_animals = self.db.get_all_animals()
            if not all_animals:
                return "В базе пока нет животных."
            chosen = random.choice(all_animals)
            response = f"🎲 Случайный факт о {_emoji(chosen['name'])} **{_capitalize(chosen['name'])}**:\n\n"
            response += f"💡 {chosen['interesting_facts']}\n\n"
            response += "О каком конкретно животном хотите узнать факты?"
            return response

        animal = animals[0]
        info = self.db.get_animal_info(animal)
        if not info:
            return self._not_found(animal)

        intros = [
            f"💡 Интересные факты о {_emoji(animal)} **{_capitalize(animal)}**:",
            f"🎯 Удивительное про {_emoji(animal)} {animal}а:",
            f"📚 Что нужно знать о {_emoji(animal)} {_capitalize(animal)}:",
        ]
        response = random.choice(intros) + "\n\n"
        response += f"📍 {info['interesting_facts']}\n\n"
        response += f"📋 **Дополнительно:**\n"
        response += f"  • Это {info['category']}\n"
        response += f"  • Обитает: {info['habitat']}\n"
        response += f"  • Размер: {info['size']}\n"
        response += f"  • Живёт: {info['lifespan']}\n\n"
        response += random.choice(FOLLOW_UPS)
        return response


    def _normalize(self, word: str) -> str:
        return ANIMAL_FORMS.get(word.lower(), word.lower())

    def _not_found(self, name: str) -> str:
        available = [a["name"] for a in self.db.get_all_animals()]
        return (f"😕 Извините, у меня нет информации о «{name}».\n\n"
                f"📚 Я знаю про: {', '.join(available)}.\n\n"
                f"О ком расскажу?")

    def _not_found_multi(self, missing: List[str]) -> str:
        available = [a["name"] for a in self.db.get_all_animals()]
        return (f"😕 У меня нет информации о: {', '.join(missing)}.\n\n"
                f"📚 Я знаю про: {', '.join(available)}.\n\n"
                f"Попробуйте сравнить кого-то из них.")
