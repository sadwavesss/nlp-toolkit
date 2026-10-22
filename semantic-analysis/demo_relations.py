#!/usr/bin/env python3
from semantic_analyzer import SemanticAnalyzer

a = SemanticAnalyzer()

text = """Собаки — самые верные и добрые друзья человека.
Кошки независимые, но очень красивые животные.
Пауки вызывают ужас и страх у многих людей.
Слоны — грациозные и умные гиганты саванны.
Медузы плавают медленно и выглядят прекрасно в воде.
Коты любят спать на мягком диване целый день."""

res = a.analyze_text(text)
for i, sent in enumerate(res):
    print(f"\n{i+1}. {sent['text']}")
    for r in sent['relations']:
        print(f"   • {r['subject']} → {r['relation_ru']} → {r['object']}")
    if not sent['relations']:
        print("   (нет отношений)")
