"""Semantic analysis of Russian text: NER, semantic roles, relations, word meanings, sentiment."""

from typing import List, Dict, Optional

# Optional dependencies: the app still starts without them
try:
    import spacy
except ImportError:
    spacy = None

try:
    from natasha import Segmenter, NewsNERTagger, NewsEmbeddingModel, Doc as NatashaDoc
    NATASHA_AVAILABLE = True
except ImportError:
    NATASHA_AVAILABLE = False

# --- Universal Dependencies tags -> Russian labels ---

DEPREL_RU = {
    "nsubj": "подлежащее", "nsubj:pass": "подлежащее (страд.)",
    "obj": "дополнение", "iobj": "косв. дополнение",
    "obl": "обстоятельство", "obl:agent": "агент",
    "root": "корень", "ROOT": "корень", "aux": "вспом. глагол",
    "flat:name": "имя+фамилия",
    "cop": "связка", "case": "предлог",
    "det": "определитель", "amod": "прил. определение",
    "nmod": "сущ. определение", "advmod": "нареч. определение",
    "acl": "причастн. оборот", "acl:relcl": "придаточн. предл.",
    "advcl": "придаточн. обстоят.", "cc": "союз",
    "conj": "однородный", "punct": "знак препинания",
    "mark": "маркер", "expl": "возвратн. частица",
    "nummod": "числит. определение", "compound": "компаунд",
    "flat": "неанализируемое", "fixed": "фиксир. оборот",
    "parataxis": "паратаксис", "orphan": "орфан",
    "discourse": "дискурс", "vocative": "звательный",
    "appos": "приложение", "csubj": "подлежащее (предик.)",
    "csubj:pass": "подлежащее (предик. страд.)",
    "xcomp": "открыт. предикатив", "ccomp": "закрыт. предикатив",
}

POS_RU = {
    "NOUN": "существительное", "VERB": "глагол",
    "ADJ": "прилагательное", "ADV": "наречие",
    "PRON": "местоимение", "DET": "определит. местоимение",
    "ADP": "предлог", "CCONJ": "союз",
    "SCONJ": "подчинит. союз", "PART": "частица",
    "PUNCT": "знак препинания", "NUM": "числительное",
    "PROPN": "имя собственное", "AUX": "вспом. глагол",
    "INTJ": "междометие", "SYM": "символ", "X": "прочее",
}

MORPH_KEYS_RU = {
    "Animacy": "Одушевлённость", "Aspect": "Вид",
    "Case": "Падеж", "Degree": "Степень",
    "Foreign": "Иноязычное", "Gender": "Род",
    "Mood": "Наклонение", "Number": "Число",
    "NumType": "Тип числительного", "Person": "Лицо",
    "Polarity": "Полярность", "Polite": "Вежливость",
    "Poss": "Притяжательность", "PronType": "Тип местоимения",
    "Reflex": "Возвратность", "Tense": "Время",
    "VerbForm": "Форма глагола", "Voice": "Залог",
    "Abbr": "Аббревиатура", "Hyph": "Дефис",
    "NameType": "Тип имени",
}

MORPH_VALUES_RU = {
    "Anim": "одуш.", "Inan": "неодуш.",
    "Perf": "сов.", "Imp": "повелит.", "Prog": "длит.",
    "Nom": "ИМ", "Gen": "РД", "Dat": "ДТ", "Acc": "ВН",
    "Ins": "ТВ", "Loc": "ПР", "Voc": "ЗВ", "Par": "Парт.",
    "Pos": "положит.", "Cmp": "сравнит.", "Sup": "превосх.",
    "Masc": "муж.", "Fem": "жен.", "Neut": "ср.",
    "Ind": "изъявит.", "Cnd": "условн.",
    "Sing": "ед.", "Plur": "мн.",
    "First": "1-е", "Second": "2-е", "Third": "3-е",
    "Past": "прош.", "Pres": "наст.", "Fut": "буд.",
    "Fin": "личная", "Inf": "инфинитив",
    "Part": "причастие", "Conv": "деепричастие", "Ger": "герундий",
    "Act": "действит.", "Pass": "страдат.", "Mid": "возвратн.",
    "Prs": "личное", "Rcp": "взаимное", "Art": "артикль",
    "Dem": "указательное", "Neg": "отрицательное",
    "Int": "вопросительное", "Rel": "относительное",
    "Exc": "восклицательное",
    "Yes": "да",
}

# --- NER labels ---

NER_LABELS_RU = {
    "PER": "Персона", "PERSON": "Персона",
    "ORG": "Организация", "ORGANIZATION": "Организация",
    "LOC": "Местоположение", "LOCATION": "Местоположение",
    "GPE": "Геополитическая единица",
    "DATE": "Дата", "TIME": "Время",
    "MONEY": "Деньги", "PERCENT": "Процент",
    "FAC": "Сооружение", "EVENT": "Событие",
    "PRODUCT": "Продукт", "WORK_OF_ART": "Произведение",
    "LAW": "Закон", "LANGUAGE": "Язык",
    "NORP": "Национальность", "QUANTITY": "Количество",
    "ORDINAL": "Порядковый", "CARDINAL": "Количественный",
}

# --- Semantic roles ---

SEMANTIC_ROLE_MAP = {
    # dependency relation -> semantic role
    "nsubj": {"role": "agent", "role_ru": "Агенс"},
    "nsubj:pass": {"role": "patient", "role_ru": "Пациенс"},
    "obj": {"role": "patient", "role_ru": "Пациенс"},
    "iobj": {"role": "recipient", "role_ru": "Реципиент"},
    "obl": {"role": "modifier", "role_ru": "Модификатор"},
    "obl:agent": {"role": "agent", "role_ru": "Агенс"},
    "advmod": {"role": "modifier", "role_ru": "Модификатор"},
    "nmod": {"role": "possessor", "role_ru": "Посессор"},
    "nummod": {"role": "measure", "role_ru": "Мера"},
    "xcomp": {"role": "theme", "role_ru": "Тема"},
    "ccomp": {"role": "theme", "role_ru": "Тема"},
    "csubj": {"role": "experiencer", "role_ru": "Экспериенцер"},
    "expl": {"role": "expletive", "role_ru": "Эксплетив"},
}

# --- Simplified Russian lexicon of word meanings and hypernyms ---

WORD_SENSES = {
    # Nouns
    "кошка": {"sense": "animal_cat", "sense_ru": "животное (кошка)", "hypernym": "млекопитающее", "hypernym_ru": "млекопитающее"},
    "собака": {"sense": "animal_dog", "sense_ru": "животное (собака)", "hypernym": "млекопитающее", "hypernym_ru": "млекопитающее"},
    "дом": {"sense": "building", "sense_ru": "здание (дом)", "hypernym": "сооружение", "hypernym_ru": "сооружение"},
    "город": {"sense": "settlement", "sense_ru": "населённый пункт", "hypernym": "место", "hypernym_ru": "место"},
    "человек": {"sense": "human", "sense_ru": "человек", "hypernym": "живое существо", "hypernym_ru": "живое существо"},
    "книга": {"sense": "book", "sense_ru": "книга", "hypernym": "произведение", "hypernym_ru": "произведение"},
    "вода": {"sense": "water", "sense_ru": "вода", "hypernym": "вещество", "hypernym_ru": "вещество"},
    "стол": {"sense": "table_furniture", "sense_ru": "мебель (стол)", "hypernym": "мебель", "hypernym_ru": "мебель"},
    "машина": {"sense": "vehicle", "sense_ru": "транспорт", "hypernym": "транспортное средство", "hypernym_ru": "транспортное средство"},
    "дерево": {"sense": "tree_plant", "sense_ru": "растение (дерево)", "hypernym": "растение", "hypernym_ru": "растение"},
    "река": {"sense": "river", "sense_ru": "река", "hypernym": "водоём", "hypernym_ru": "водоём"},
    "школа": {"sense": "school", "sense_ru": "учебное заведение", "hypernym": "учреждение", "hypernym_ru": "учреждение"},
    "страна": {"sense": "country", "sense_ru": "страна", "hypernym": "территория", "hypernym_ru": "территория"},
    # Verbs
    "бежать": {"sense": "run", "sense_ru": "бежать (двигаться)", "hypernym": "двигаться", "hypernym_ru": "двигаться"},
    "идти": {"sense": "walk", "sense_ru": "идти (двигаться)", "hypernym": "двигаться", "hypernym_ru": "двигаться"},
    "говорить": {"sense": "speak", "sense_ru": "говорить", "hypernym": "коммуницировать", "hypernym_ru": "коммуницировать"},
    "видеть": {"sense": "see", "sense_ru": "видеть (воспринимать)", "hypernym": "воспринимать", "hypernym_ru": "воспринимать"},
    "знать": {"sense": "know", "sense_ru": "знать", "hypernym": "познавать", "hypernym_ru": "познавать"},
    "работать": {"sense": "work", "sense_ru": "работать", "hypernym": "действовать", "hypernym_ru": "действовать"},
    "читать": {"sense": "read", "sense_ru": "читать", "hypernym": "воспринимать", "hypernym_ru": "воспринимать"},
    "писать": {"sense": "write", "sense_ru": "писать", "hypernym": "создавать", "hypernym_ru": "создавать"},
    "есть": {"sense": "eat", "sense_ru": "есть (употреблять пищу)", "hypernym": "употреблять", "hypernym_ru": "употреблять"},
    "спать": {"sense": "sleep", "sense_ru": "спать", "hypernym": "отдыхать", "hypernym_ru": "отдыхать"},
    # Adjectives
    "большой": {"sense": "big", "sense_ru": "большой (размер)", "hypernym": "размер", "hypernym_ru": "размер"},
    "маленький": {"sense": "small", "sense_ru": "маленький (размер)", "hypernym": "размер", "hypernym_ru": "размер"},
    "хороший": {"sense": "good", "sense_ru": "хороший (качество)", "hypernym": "качество", "hypernym_ru": "качество"},
    "плохой": {"sense": "bad", "sense_ru": "плохой (качество)", "hypernym": "качество", "hypernym_ru": "качество"},
    "красивый": {"sense": "beautiful", "sense_ru": "красивый (эстетика)", "hypernym": "эстетика", "hypernym_ru": "эстетика"},
}


class SemanticAnalyzer:

    def __init__(self):
        self.nlp = None
        self._natasha_segmenter = None
        self._natasha_ner = None
        self._load_models()

    def _load_models(self):
        # spaCy
        if spacy is None:
            self.nlp = None
        else:
            model_name = "ru_core_news_sm"
            try:
                self.nlp = spacy.load(model_name)
            except OSError:
                try:
                    spacy.cli.download(model_name)
                    self.nlp = spacy.load(model_name)
                except Exception:
                    self.nlp = None

        # Natasha NER
        if NATASHA_AVAILABLE:
            try:
                self._natasha_segmenter = Segmenter()
                self._natasha_ner = NewsNERTagger(NewsEmbeddingModel())
            except Exception:
                self._natasha_ner = None

    def is_available(self) -> bool:
        return self.nlp is not None

    def ner_available(self) -> bool:
        return self._natasha_ner is not None

    # --- Main analysis ---

    def analyze_text(self, text: str) -> List[Dict]:
        if not self.is_available():
            raise RuntimeError("Модель spaCy не загружена")
        if not text or not text.strip():
            return []

        doc = self.nlp(text)
        result = []

        for sent in doc.sents:
            tokens = self._analyze_tokens(sent)
            entities = self._extract_entities(sent, tokens)
            roles = self._assign_semantic_roles(sent, tokens)
            senses = self._lookup_senses(tokens)
            relations = self._extract_relations(sent, tokens, entities)
            sentiment = self._analyze_sentiment(sent.text)

            result.append({
                "text": sent.text,
                "tokens": tokens,
                "entities": entities,
                "roles": roles,
                "senses": senses,
                "relations": relations,
                "sentiment": sentiment,
            })

        # Extra named entities from Natasha
        if self._natasha_ner is not None:
            self._enhance_entities_natasha(text, result)

        return result

    def _analyze_tokens(self, sent) -> List[Dict]:
        tokens = []
        for i, token in enumerate(sent):
            morph_ru = self._morph_to_str(token.morph)
            tokens.append({
                "text": token.text,
                "lemma": token.lemma_,
                "pos": token.pos_,
                "pos_ru": POS_RU.get(token.pos_, token.pos_),
                "morph": str(token.morph),
                "morph_ru": morph_ru,
                "head_index": self._relative_head_index(sent, token),
                "deprel": token.dep_,
                "deprel_ru": DEPREL_RU.get(token.dep_, token.dep_),
                "position": i,
            })
        return tokens

    def _extract_entities(self, sent, tokens: List[Dict]) -> List[Dict]:
        entities = []
        seen_spans = set()
        sent_start = sent.start
        for ent in sent.ents:
            span_key = (ent.start_char, ent.end_char)
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)
            start_tok = max(0, ent.start - sent_start)
            end_tok = max(0, ent.end - sent_start - 1)
            label_ru = NER_LABELS_RU.get(ent.label_, ent.label_)
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "label_ru": label_ru,
                "start_token": start_tok,
                "end_token": end_tok,
                "description": f"Именованная сущность: {label_ru}",
            })
        return entities

    def _enhance_entities_natasha(self, text: str, result: List[Dict]):
        try:
            nat_doc = NatashaDoc(text)
            nat_doc.segment(self._natasha_segmenter)
            nat_doc.tag_ner(self._natasha_ner)

            for ner_span in nat_doc.ner.spans:
                ner_text = ner_span.text
                ner_type = ner_span.type
                label_ru = NER_LABELS_RU.get(ner_type, ner_type)

                for item in result:
                    if ner_text in item["text"]:
                        # Skip entities already found by spaCy
                        existing_texts = {e["text"] for e in item["entities"]}
                        if ner_text not in existing_texts:
                            item["entities"].append({
                                "text": ner_text,
                                "label": ner_type,
                                "label_ru": label_ru,
                                "start_token": 0,
                                "end_token": 0,
                                "description": f"Именованная сущность (Natasha): {label_ru}",
                            })
                        break
        except Exception:
            pass

    def _assign_semantic_roles(self, sent, tokens: List[Dict]) -> List[Dict]:
        """Map dependency relations to semantic roles."""
        roles = []
        for i, token in enumerate(sent):
            dep = token.dep_
            role_info = SEMANTIC_ROLE_MAP.get(dep)
            if role_info:
                # id of the predicate (head word)
                predicate_idx = self._relative_head_index(sent, token)
                predicate_text = tokens[predicate_idx]["text"] if predicate_idx >= 0 else ""

                roles.append({
                    "token_index": i,
                    "token_text": token.text,
                    "role": role_info["role"],
                    "role_ru": role_info["role_ru"],
                    "predicate_index": predicate_idx,
                    "predicate_text": predicate_text,
                })
        return roles

    def _lookup_senses(self, tokens: List[Dict]) -> List[Dict]:
        senses = []
        for t in tokens:
            lemma = t["lemma"].lower()
            sense_info = WORD_SENSES.get(lemma)
            if sense_info:
                senses.append({
                    "token_index": t["position"],
                    "token_text": t["text"],
                    "sense": sense_info["sense"],
                    "sense_ru": sense_info["sense_ru"],
                    "hypernym": sense_info["hypernym"],
                    "hypernym_ru": sense_info["hypernym_ru"],
                })
        return senses

    def _extract_relations(self, sent, tokens: List[Dict], entities: List[Dict]) -> List[Dict]:
        """Extract (subject, relation, object) triples from the dependency tree.

        subject = nsubj / nsubj:pass of a verb, object = obj / iobj / obl of the same verb,
        relation = verb lemma + preposition. Conjoined and infinitive clauses inherit the subject;
        time adverbials ("day", "hour") are skipped.
        """
        relations = []
        
        # token position -> NER label
        ner_labels = {}
        for ent in entities:
            for i in range(ent.get("start_token", 0), ent.get("end_token", 0) + 1):
                ner_labels[i] = ent.get("label_ru", "Сущность")
        
        # Time words: excluded from roles (e.g. obl adverbials like 'all day')
        TIME_LEMMAS = {
            "день", "ночь", "время", "час", "минута", "секунда", "год",
            "месяц", "неделя", "утро", "вечер", "сегодня", "завтра", "вчера",
            "зима", "лето", "весна", "осень", "сейчас", "потом", "раньше",
            "когда", "пора", "момент", "период", "эпоха",
        }
        
        def get_entity(token: Dict) -> Dict:
            idx = token["position"]
            label_ru = ner_labels.get(idx, "Сущность")
            return {"text": token["text"], "label_ru": label_ru}
        
        def find_preposition(token_idx: int) -> str:
            """Preposition (case dependent) attached to the token."""
            for t in tokens:
                if t["head_index"] == token_idx and t["deprel"] == "case":
                    return t["lemma"].lower()
            return ""
        
        def is_valid_noun_object(token: Dict) -> bool:
            # Nouns, proper nouns and substantivized adjectives
            if token["pos"] not in ("NOUN", "PROPN", "ADJ"):
                return False
            if token["lemma"].lower() in TIME_LEMMAS:
                return False
            return True
        
        # Step 1: find the subject of every verb
        verb_subjects = {}
        verb_tokens = [t for t in tokens if t["pos"] in ("VERB", "AUX")]
        
        for vtok in verb_tokens:
            verb_idx = vtok["position"]
            for t in tokens:
                if (t["head_index"] == verb_idx 
                    and t["deprel"] in ("nsubj", "nsubj:pass")
                    and t["pos"] in ("NOUN", "PROPN", "ADJ", "PRON")):
                    verb_subjects[verb_idx] = get_entity(t)
                    break
        
        # Step 2: propagate subjects through conj / xcomp / advcl
        for _ in range(3):  # up to 3 levels of nesting
            changed = False
            for vtok in verb_tokens:
                verb_idx = vtok["position"]
                if verb_idx in verb_subjects:
                    continue
                if vtok["deprel"] in ("conj", "xcomp", "advcl", "parataxis", "ccomp"):
                    head_idx = vtok["head_index"]
                    if head_idx in verb_subjects:
                        verb_subjects[verb_idx] = verb_subjects[head_idx]
                        changed = True
            if not changed:
                break
        
        # Step 3: collect objects of every verb that has a subject
        seen = set()
        for vtok in verb_tokens:
            verb_idx = vtok["position"]
            if verb_idx not in verb_subjects:
                continue
            
            subject = verb_subjects[verb_idx]
            verb_lemma = vtok["lemma"].lower()
            
            for t in tokens:
                if t["head_index"] != verb_idx:
                    continue
                if t["deprel"] not in ("obj", "iobj", "obl", "obl:agent"):
                    continue
                if not is_valid_noun_object(t):
                    continue
                
                obj = get_entity(t)
                
                # relation name: verb lemma [+ preposition]
                prep = find_preposition(t["position"])
                if prep:
                    relation_ru = f"{verb_lemma} {prep}"
                    relation_en = f"{verb_lemma}_{prep}"
                else:
                    relation_ru = verb_lemma
                    relation_en = verb_lemma
                
                key = (subject["text"], relation_ru, obj["text"])
                if key in seen:
                    continue
                seen.add(key)
                
                relations.append({
                    "subject": subject["text"],
                    "subject_type": subject["label_ru"],
                    "relation": relation_en,
                    "relation_ru": relation_ru,
                    "object": obj["text"],
                    "object_type": obj["label_ru"],
                    "confidence": 0.85,
                })
        
        return relations

    def _analyze_sentiment(self, text: str) -> Dict:
        """Lexicon-based sentiment with intensifiers and negation."""
        # Simplified Russian sentiment lexicon
        POSITIVE_WORDS = {
            "хороший", "отличный", "прекрасный", "замечательный", "великолепный",
            "радостный", "счастливый", "люблю", "нравится", "любить", "обожать",
            "лучший", "превосходный", "отлично", "хорошо", "красивый", "умный",
            "талантливый", "добрый", "приятный", "весёлый", "смешной",
            "верный", "верные", "друг", "друзья", "независимый", "независимые",
            "грациозный", "грациозные", "медленно", "медленный",
        }
        NEGATIVE_WORDS = {
            "плохой", "ужасный", "отвратительный", "ужасно", "плохо",
            "грустный", "печальный", "злой", "ненавижу", "ненавидеть",
            "скучный", "тупой", "грязный", "мерзкий", "негативный",
            "проблема", "ошибка", "неудача", "катастрофа", "трагедия",
            "ужас", "страх", "вызывать", "вызывают", "бояться", "опасный",
        }
        INTENSIFIERS = {"очень", "крайне", "чрезвычайно", "невероятно", "особенно"}
        NEGATORS = {"не", "нет", "ни", "без"}
        
        words = text.lower().split()
        pos_score = 0
        neg_score = 0
        
        for i, word in enumerate(words):
            clean_word = "".join(c for c in word if c.isalpha())
            
            # intensifiers and negations
            multiplier = 1.0
            if i > 0:
                if words[i-1] in INTENSIFIERS:
                    multiplier = 1.5
                if words[i-1] in NEGATORS:
                    multiplier = -1.0
            
            if clean_word in POSITIVE_WORDS:
                if multiplier < 0:
                    neg_score += abs(multiplier)
                else:
                    pos_score += multiplier
            elif clean_word in NEGATIVE_WORDS:
                if multiplier < 0:
                    pos_score += abs(multiplier)
                else:
                    neg_score += multiplier
        
        total = pos_score + neg_score
        if total == 0:
            return {"label": "neutral", "label_ru": "нейтральная", "score": 0.5}
        
        sentiment_score = pos_score / (pos_score + neg_score) if (pos_score + neg_score) > 0 else 0.5
        
        if pos_score > neg_score:
            return {"label": "positive", "label_ru": "позитивная", "score": sentiment_score}
        elif neg_score > pos_score:
            return {"label": "negative", "label_ru": "негативная", "score": 1 - sentiment_score}
        else:
            return {"label": "neutral", "label_ru": "нейтральная", "score": 0.5}

    # --- Helpers ---

    def _relative_head_index(self, sent, token) -> int:
        head = token.head
        if head == token:
            return -1
        for i, t in enumerate(sent):
            if t == head:
                return i
        return -1

    def _morph_to_str(self, morph) -> str:
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
