"""Dependency parsing of Russian text with spaCy."""

from typing import List, Dict, Optional

# Optional dependency: the app still starts without spaCy
try:
    import spacy
except ImportError:
    spacy = None


# Universal Dependencies POS tags -> Russian labels for the UI
DEPREL_RU = {
    "nsubj": "подлежащее",
    "nsubj:pass": "подлежащее (страд.)",
    "obj": "дополнение",
    "iobj": "косв. дополнение",
    "obl": "обстоятельство",
    "obl:agent": "агент",
    "root": "корень",
    "aux": "вспом. глагол",
    "cop": "связка",
    "case": "предлог",
    "det": "определитель",
    "amod": "прил. определение",
    "nmod": "сущ. определение",
    "advmod": "нареч. определение",
    "acl": "причастн. оборот",
    "acl:relcl": "придаточн. предл.",
    "advcl": "придаточн. обстоят.",
    "cc": "союз",
    "conj": "однородный",
    "punct": "знак препинания",
    "mark": "маркер",
    "expl": "возвратн. частица",
    "nummod": "числит. определение",
    "compound": "компаунд",
    "flat": "неанализируемое",
    "fixed": "фиксир. оборот",
    "parataxis": "паратаксис",
    "orphan": "орфан",
    "discourse": "дискурс",
    "vocative": "звательный",
    "appos": "приложение",
    "csubj": "подлежащее (предик.)",
    "csubj:pass": "подлежащее (предик. страд.)",
    "xcomp": "открыт. предикатив",
    "ccomp": "закрыт. предикатив",
}

POS_RU = {
    "NOUN": "существительное",
    "VERB": "глагол",
    "ADJ": "прилагательное",
    "ADV": "наречие",
    "PRON": "местоимение",
    "DET": "определит. местоимение",
    "ADP": "предлог",
    "CCONJ": "союз",
    "SCONJ": "подчинит. союз",
    "PART": "частица",
    "PUNCT": "знак препинания",
    "NUM": "числительное",
    "PROPN": "имя собственное",
    "AUX": "вспом. глагол",
    "INTJ": "междометие",
    "SYM": "символ",
    "X": "прочее",
}

# Universal Dependencies morphological features -> Russian labels
MORPH_KEYS_RU = {
    "Animacy": "Одушевлённость",
    "Aspect": "Вид",
    "Case": "Падеж",
    "Degree": "Степень",
    "Foreign": "Иноязычное",
    "Gender": "Род",
    "Mood": "Наклонение",
    "Number": "Число",
    "NumType": "Тип числительного",
    "Person": "Лицо",
    "Polarity": "Полярность",
    "Polite": "Вежливость",
    "Poss": "Притяжательность",
    "PronType": "Тип местоимения",
    "Reflex": "Возвратность",
    "Tense": "Время",
    "VerbForm": "Форма глагола",
    "Voice": "Залог",
    "Abbr": "Аббревиатура",
    "Hyph": "Дефис",
    "NameType": "Тип имени",
}

MORPH_VALUES_RU = {
    # Animacy
    "Anim": "одуш.",
    "Inan": "неодуш.",
    # Aspect
    "Imp": "сов.",
    "Perf": "сов.",
    "Prog": "длит.",
    # Case
    "Nom": "ИМ",
    "Gen": "РД",
    "Dat": "ДТ",
    "Acc": "ВН",
    "Ins": "ТВ",
    "Loc": "ПР",
    "Voc": "ЗВ",
    "Par": "Парт.",
    # Degree
    "Pos": "положит.",
    "Cmp": "сравнит.",
    "Sup": "превосх.",
    # Gender
    "Masc": "муж.",
    "Fem": "жен.",
    "Neut": "ср.",
    # Mood
    "Ind": "изъявит.",
    "Imp": "повелит.",
    "Cnd": "условн.",
    # Number
    "Sing": "ед.",
    "Plur": "мн.",
    # Person
    "First": "1-е",
    "Second": "2-е",
    "Third": "3-е",
    # Tense
    "Past": "прош.",
    "Pres": "наст.",
    "Fut": "буд.",
    # VerbForm
    "Fin": "личная",
    "Inf": "инфинитив",
    "Part": "причастие",
    "Conv": "деепричастие",
    "Ger": "герундий",
    # Voice
    "Act": "действит.",
    "Pass": "страдат.",
    "Mid": "возвратн.",
    # PronType
    "Prs": "личное",
    "Rcp": "взаимное",
    "Art": "артикль",
    "Dem": "указательное",
    "Ind": "неопределённое",
    "Neg": "отрицательное",
    "Int": "вопросительное",
    "Rel": "относительное",
    "Exc": "восклицательное",
    # Poss
    "Yes": "да",
    # Reflex
    # Polarity
    "Neg": "отриц.",
    "Pos": "утвердит.",
}


class SyntaxAnalyzer:

    def __init__(self):
        self.nlp = None
        self._load_model()

    def _load_model(self):
        if spacy is None:
            self.nlp = None
            return
        model_name = "ru_core_news_sm"
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            try:
                spacy.cli.download(model_name)
                self.nlp = spacy.load(model_name)
            except Exception:
                self.nlp = None

    def is_available(self) -> bool:
        return self.nlp is not None

    def analyze_text(self, text: str) -> List[Dict]:
        """
        Синтаксический анализ текста.
        Возвращает список предложений с токенами и синтаксическими связями.
        """
        if not self.is_available():
            raise RuntimeError("Модель spaCy для русского языка не загружена")

        if not text or not text.strip():
            return []

        doc = self.nlp(text)
        result = []

        for sent in doc.sents:
            tokens = []
            for i, token in enumerate(sent):
                tokens.append({
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "pos_ru": POS_RU.get(token.pos_, token.pos_),
                    "morph": self._morph_to_str(token.morph),
                    "head_index": self._relative_head_index(sent, token),
                    "deprel": token.dep_,
                    "deprel_ru": DEPREL_RU.get(token.dep_, token.dep_),
                    "position": i,
                })
            result.append({
                "text": sent.text,
                "tokens": tokens,
            })

        return result

    def _relative_head_index(self, sent, token) -> int:
        """
        Вычислить индекс head относительно начала предложения.
        Возвращает -1 если head — корень (head = сам токен).
        """
        head = token.head
        if head == token:
            return -1
        for i, t in enumerate(sent):
            if t == head:
                return i
        return -1

    def _morph_to_str(self, morph) -> str:
        """Format spaCy MorphAnalysis as a Russian string."""
        if not morph:
            return ""
        morph_dict = morph.to_dict()
        if not morph_dict:
            return ""
        parts = []
        for key, val in morph_dict.items():
            key_ru = MORPH_KEYS_RU.get(key, key)
            if isinstance(val, list):
                vals_ru = [MORPH_VALUES_RU.get(v, v) for v in val]
                val_ru = ",".join(vals_ru)
            else:
                val_ru = MORPH_VALUES_RU.get(val, val)
            parts.append(f"{key_ru}={val_ru}")
        return "|".join(parts)

    def build_dependency_tree(self, tokens: List[Dict]) -> Dict:
        """
        Построить дерево зависимостей из списка токенов.
        Возвращает словарь: {token_index: [child_indices]}
        """
        tree = {i: [] for i in range(len(tokens))}
        root_index = 0

        for i, token in enumerate(tokens):
            head_idx = token["head_index"]
            if head_idx == -1:
                root_index = i
            else:
                if head_idx in tree:
                    tree[head_idx].append(i)

        return {"root": root_index, "children": tree}

    def get_deprel_explanation(self, deprel: str) -> str:
        return DEPREL_RU.get(deprel, deprel)

    def get_pos_explanation(self, pos: str) -> str:
        return POS_RU.get(pos, pos)
