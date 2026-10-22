#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import spacy


ANIMALS = [
    "тигр", "лев", "гепард", "пингвин", "дельфин", "слон",
    "медведь", "волк", "лиса", "заяц", "кролик", "лошадь", "корова",
    "собака", "кошка", "мышь", "кит", "акула", "крокодил",
    "обезьяна", "жираф", "зебра", "носорог", "бегемот",
]

ANIMAL_FORMS = {
    "тигр": "тигр", "тигра": "тигр", "тигру": "тигр", "тигром": "тигр",
    "тигре": "тигр", "тигры": "тигр", "тигров": "тигр", "тиграми": "тигр", "тиграх": "тигр",
    "лев": "лев", "льва": "лев", "льву": "лев", "львом": "лев", "льве": "лев",
    "львы": "лев", "львов": "лев", "львами": "лев", "львах": "лев",
    "гепард": "гепард", "гепарда": "гепард", "гепарду": "гепард", "гепардом": "гепард",
    "гепарде": "гепард", "гепарды": "гепард", "гепардов": "гепард", "гепардами": "гепард",
    "пингвин": "пингвин", "пингвина": "пингвин", "пингвину": "пингвин",
    "пингвином": "пингвин", "пингвине": "пингвин", "пингвины": "пингвин",
    "пингвинов": "пингвин", "пингвинами": "пингвин", "пингвинах": "пингвин",
    "дельфин": "дельфин", "дельфина": "дельфин", "дельфину": "дельфин",
    "дельфином": "дельфин", "дельфине": "дельфин", "дельфины": "дельфин",
    "дельфинов": "дельфин", "дельфинами": "дельфин", "дельфинах": "дельфин",
    "слон": "слон", "слона": "слон", "слону": "слон", "слоном": "слон",
    "слоне": "слон", "слоны": "слон", "слонов": "слон", "слонами": "слон",
    "медведь": "медведь", "медведя": "медведь", "медведю": "медведь",
    "медведем": "медведь", "медведе": "медведь", "медведи": "медведь",
    "медведей": "медведь", "медведями": "медведь", "медведях": "медведь",
    "волк": "волк", "волка": "волк", "волку": "волк", "волком": "волк",
    "волке": "волк", "волки": "волк", "волков": "волк", "волками": "волк",
    "жираф": "жираф", "жирафа": "жираф", "жирафу": "жираф", "жирафом": "жираф",
    "жирафе": "жираф", "жирафы": "жираф", "жирафов": "жираф", "жирафами": "жираф",
    "акула": "акула", "акулы": "акула", "акуле": "акула", "акулу": "акула",
    "акулой": "акула", "акулу": "акула", "акул": "акула", "акулами": "акула",
    "лиса": "лиса", "лисы": "лиса", "лисе": "лиса", "лису": "лиса",
    "лисой": "лиса", "лис": "лиса", "лисами": "лиса",
    "обезьяна": "обезьяна", "обезьяны": "обезьяна", "обезьяне": "обезьяна",
    "обезьяну": "обезьяна", "обезьяной": "обезьяна", "обезьян": "обезьяна",
    "кит": "кит", "кита": "кит", "киту": "кит", "китом": "кит",
    "ките": "кит", "киты": "кит", "китов": "кит", "китами": "кит",
}

HABITATS = [
    "лес", "саванна", "пустыня", "тундра", "океан", "море",
    "река", "озеро", "горы", "джунгли", "арктика", "антарктида",
]


class NLPProcessor:
    def __init__(self):
        try:
            self.nlp = spacy.load("ru_core_news_sm")
            self.has_spacy = True
        except OSError:
            print("⚠ Модель ru_core_news_sm не найдена. Установите: "
                  "python -m spacy download ru_core_news_sm")
            print("⚠ NLP работает в режиме fallback (только regex+словари).")
            self.nlp = None
            self.has_spacy = False

        self.animals = ANIMALS
        self.animal_forms = ANIMAL_FORMS
        self.habitats = HABITATS

        forms = sorted(self.animal_forms.keys(), key=len, reverse=True)
        self._animal_re = re.compile(
            r"\b(" + "|".join(map(re.escape, forms)) + r")\b",
            re.IGNORECASE,
        )

        self.intent_patterns = [
            ("greeting", [
                r"^\s*(привет(ствую)?|здравствуй(те)?|добрый\s+(день|вечер|утро)|хай|хеллоу)\b",
                r"^\s*здорово\b",
            ]),
            ("goodbye", [
                r"\b(пока|до\s+свидания|прощай(те)?|увидимся|всего\s+доброго)\b",
                r"^\s*бай\b",
            ]),
            ("compare_animals", [
                r"\bсравни(ть)?\b",
                r"\bкто\s+(быстрее|сильнее|больше|умнее|опаснее|крупнее|меньше)\b",
                r"\b(что|кто)\s+(лучше|круче)\b",
                r"\bразниц[аы]\s+между\b",
                r"\b\S+\s+или\s+\S+",
            ]),
            ("facts_query", [
                r"\b(интересн[ыо]е?\s+)?факт(ы|ов|а)?\b",
                r"\bчто\s+интересного\b",
                r"\bрасскажи\s+интересн",
                r"\bудивительн",
            ]),
            ("habitat_query", [
                r"\bгде\s+(жив[её]т|живут|обита(е|ю)т|водит(ся|ятся))\b",
                r"\bсред[аы]\s+обитани[яе]\b",
                r"\bареал\b",
                r"\bобитани[ея]\b",
                r"\bгде\s+(можно\s+)?(найти|встретить|увидеть)\b",
            ]),
            ("diet_query", [
                r"\bчто\s+(ест|едят|кушает|кушают)\b",
                r"\bчем\s+питает(ся|ются)\b",
                r"\bпитани[ея]\b",
                r"\bрацион\b",
                r"\bчем\s+корм",
                r"\b(основная\s+)?пища\b",
            ]),
            ("animal_info", [
                r"\bрасскажи\s+(про|о|об)\b",
                r"\bчто\s+(ты\s+)?знаешь\s+о[бт]?\b",
                r"\bинформаци[яю]\s+(о|про)\b",
                r"\bкто\s+так(ой|ая|ие)\b",
                r"\bописани[ея]\b",
            ]),
        ]


    def analyze_text(self, text: str) -> Dict:
        clean = text.lower().strip()
        animals_found = self._extract_animals(clean)
        spacy_entities = self._extract_spacy_entities(clean)
        habitats_found = self._extract_habitats(clean)
        entities: List[Dict] = []
        for a in animals_found:
            entities.append({"text": a, "type": "ANIMAL"})
        for h in habitats_found:
            entities.append({"text": h, "type": "HABITAT"})
        for e in spacy_entities:
            if e not in entities:
                entities.append(e)

        intent = self._detect_intent(clean, animals_found)

        return {
            "intent": intent,
            "entities": entities,
            "confidence": self._calculate_confidence(intent, clean, animals_found),
            "clean_text": clean,
            "animals": animals_found,
        }


    def _extract_animals(self, text: str) -> List[str]:
        found: List[str] = []
        seen = set()
        for m in self._animal_re.finditer(text):
            form = m.group(1).lower()
            lemma = self.animal_forms.get(form, form)
            if lemma not in seen:
                seen.add(lemma)
                found.append(lemma)

        if self.has_spacy and not found:
            doc = self.nlp(text)
            for token in doc:
                lemma = token.lemma_.lower()
                if lemma in self.animals and lemma not in seen:
                    seen.add(lemma)
                    found.append(lemma)

        return found

    def _extract_habitats(self, text: str) -> List[str]:
        return [h for h in self.habitats if re.search(rf"\b{h}", text)]

    def _extract_spacy_entities(self, text: str) -> List[Dict]:
        if not self.has_spacy:
            return []
        try:
            doc = self.nlp(text)
        except Exception:
            return []
        out = []
        for ent in doc.ents:
            if ent.label_ in ("PER", "LOC", "ORG"):
                out.append({"text": ent.text.lower(), "type": ent.label_})
        return out

    def _detect_intent(self, text: str, animals: List[str]) -> str:
        for intent_name, patterns in self.intent_patterns:
            for p in patterns:
                if re.search(p, text, re.IGNORECASE):
                    if intent_name == "compare_animals" and len(animals) < 2:
                        continue
                    return intent_name

        if animals:
            return "animal_info"

        return "unknown"

    def _calculate_confidence(self, intent: str, text: str, animals: List[str]) -> float:
        if intent == "unknown":
            return 0.15
        base = 0.65
        if animals:
            base += 0.15
        boosters = {
            "greeting": ["привет", "здравствуй", "добрый"],
            "goodbye": ["пока", "свидания", "прощай"],
            "animal_info": ["расскажи", "знаешь", "информаци", "описани"],
            "compare_animals": ["сравни", "быстрее", "сильнее", "лучше", "или"],
            "habitat_query": ["где", "обита", "ареал", "среда"],
            "diet_query": ["ест", "питает", "рацион"],
            "facts_query": ["факт", "интересн", "удивит"],
        }
        for kw in boosters.get(intent, []):
            if kw in text:
                base += 0.05
        return min(base, 0.99)


    def normalize_animal(self, word: str) -> str:
        return self.animal_forms.get(word.lower(), word.lower())

    def extract_animal_names(self, text: str) -> List[str]:
        return self._extract_animals(text.lower())
