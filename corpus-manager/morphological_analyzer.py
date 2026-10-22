import re
from typing import List, Optional, Dict, Any

try:
    import pymorphy3
    PYMORPHY_AVAILABLE = True
except ImportError:
    PYMORPHY_AVAILABLE = False

try:
    import pymystem3
    PYMYSTEM3_AVAILABLE = True
except ImportError:
    PYMYSTEM3_AVAILABLE = False

from corpus_model import Wordform, MorphologicalTag


class MorphologicalAnalyzer:
    
    def __init__(self):
        self.morph = None
        self.mystem = None
        self.analyzer_type = None

        if PYMORPHY_AVAILABLE:
            try:
                self.morph = pymorphy3.MorphAnalyzer()
                self.analyzer_type = "pymorphy3"
                print("Используется pymorphy3 для морфологического анализа")
            except Exception:
                self.morph = None

        if self.morph is None and PYMYSTEM3_AVAILABLE:
            try:
                self.mystem = pymystem3.Mystem()
                self.analyzer_type = "pymystem3"
                print("Используется pymystem3 для морфологического анализа")
            except Exception:
                self.mystem = None

        if self.morph is None and self.mystem is None:
            print("Морфологический анализатор недоступен")
            self.analyzer_type = None

        self.pos_mapping = {
            'NOUN': 'существительное',
            'ADJF': 'прилагательное',
            'ADJS': 'прилагательное',
            'COMP': 'прилагательное',
            'VERB': 'глагол',
            'INFN': 'глагол',
            'PRTF': 'причастие',
            'PRTS': 'причастие',
            'GRND': 'деепричастие',
            'NUMR': 'числительное',
            'ADVB': 'наречие',
            'NPRO': 'местоимение',
            'PRED': 'предикатив',
            'PREP': 'предлог',
            'CONJ': 'союз',
            'PRCL': 'частица',
            'INTJ': 'междометие'
        }
        
        self.case_mapping = {
            'nomn': 'именительный',
            'gent': 'родительный',
            'datv': 'дательный',
            'accs': 'винительный',
            'ablt': 'творительный',
            'loct': 'предложный',
            'voct': 'звательный',
            'gen2': 'родительный (частичный)',
            'acc2': 'винительный (при подсчете)',
            'loc2': 'предложный (о месте)'
        }
        
        self.number_mapping = {
            'sing': 'единственное',
            'plur': 'множественное'
        }
        
        self.gender_mapping = {
            'masc': 'мужской',
            'femn': 'женский',
            'neut': 'средний'
        }

        self.animacy_mapping = {
            'anim': 'одушевлённое',
            'inan': 'неодушевлённое'
        }

        self.tense_mapping = {
            'past': 'прошедшее',
            'pres': 'настоящее',
            'futr': 'будущее'
        }
        
        self.person_mapping = {
            '1per': 'первое',
            '2per': 'второе',
            '3per': 'третье'
        }
        
        self.aspect_mapping = {
            'impf': 'несовершенный',
            'perf': 'совершенный'
        }
        
        self.voice_mapping = {
            'actv': 'действительный',
            'pssv': 'страдательный'
        }
        
        self.mood_mapping = {
            'indc': 'изъявительное',
            'impr': 'повелительное'
        }
    
    def analyze_text(self, text: str) -> List[Wordform]:
        if not self.morph and not self.mystem:
            raise RuntimeError("Морфологический анализатор недоступен")

        words = self._tokenize_russian(text)
        wordforms = []
        
        for position, word in enumerate(words):
            wordform = self.analyze_word(word, position)
            if wordform:
                wordforms.append(wordform)
        
        return wordforms
    
    def analyze_word(self, word: str, position: int = 0) -> Optional[Wordform]:
        if not self.morph and not self.mystem:
            return None
        
        if len(word.strip()) < 1:
            return None
        
        if self.morph:
            parses = self.morph.parse(word)
            if not parses:
                return Wordform(
                    text=word,
                    lemma=word.lower(),
                    morph_tag=MorphologicalTag(),
                    position_in_text=position
                )
            
            parse = parses[0]
            lemma = parse.normal_form
            
            morph_tag = self._extract_morphological_tag(parse)
            
            return Wordform(
                text=word,
                lemma=lemma,
                morph_tag=morph_tag,
                position_in_text=position
            )
        
        elif self.mystem:
            try:
                analysis = self.mystem.analyze(word)
                if not analysis or not analysis[0].get('analysis'):
                    return Wordform(
                        text=word,
                        lemma=word.lower(),
                        morph_tag=MorphologicalTag(),
                        position_in_text=position
                    )
                
                parse_info = analysis[0]['analysis'][0]
                lemma = parse_info.get('lex', word.lower())
                
                morph_tag = self._extract_morphological_tag_mystem(parse_info)
                
                return Wordform(
                    text=word,
                    lemma=lemma,
                    morph_tag=morph_tag,
                    position_in_text=position
                )
            except Exception:
                return Wordform(
                    text=word,
                    lemma=word.lower(),
                    morph_tag=MorphologicalTag(),
                    position_in_text=position
                )
        
        return None
    
    def _tokenize_russian(self, text: str) -> List[str]:
        russian_word_pattern = r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*"
        return re.findall(russian_word_pattern, text)
    
    def _extract_morphological_tag(self, parse) -> MorphologicalTag:
        tag = MorphologicalTag()

        if not hasattr(parse, 'tag') or not parse.tag:
            return tag

        opencorpora_tag = parse.tag

        if opencorpora_tag.POS:
            tag.pos = self.pos_mapping.get(opencorpora_tag.POS, '')

        if opencorpora_tag.case:
            tag.case = self.case_mapping.get(opencorpora_tag.case, '')

        if opencorpora_tag.number:
            tag.number = self.number_mapping.get(opencorpora_tag.number, '')

        if opencorpora_tag.gender:
            tag.gender = self.gender_mapping.get(opencorpora_tag.gender, '')

        if opencorpora_tag.animacy:
            tag.animacy = self.animacy_mapping.get(opencorpora_tag.animacy, '')

        if opencorpora_tag.tense:
            tag.tense = self.tense_mapping.get(opencorpora_tag.tense, '')

        if opencorpora_tag.person:
            tag.person = self.person_mapping.get(opencorpora_tag.person, '')

        if opencorpora_tag.aspect:
            tag.aspect = self.aspect_mapping.get(opencorpora_tag.aspect, '')

        if opencorpora_tag.voice:
            tag.voice = self.voice_mapping.get(opencorpora_tag.voice, '')

        if opencorpora_tag.mood:
            tag.mood = self.mood_mapping.get(opencorpora_tag.mood, '')

        return tag
    
    def get_lemma(self, word: str) -> str:
        if not self.morph:
            return word.lower()
        
        try:
            parse = self.morph.parse(word)
            if parse:
                return parse[0].normal_form
        except Exception:
            pass
        
        return word.lower()
    
    def get_pos(self, word: str) -> str:
        if not self.morph:
            return ""
        
        try:
            parse = self.morph.parse(word)
            if parse and hasattr(parse[0], 'tag') and parse[0].tag:
                pos_tag = parse[0].tag.POS
                if pos_tag in self.pos_mapping:
                    return self.pos_mapping[pos_tag]
        except Exception:
            pass
        
        return ""
    
    def is_available(self) -> bool:
        return self.morph is not None or self.mystem is not None
    
    def get_word_info(self, word: str) -> Dict[str, Any]:
        if not self.morph and not self.mystem:
            return {
                'word': word,
                'lemma': word.lower(),
                'pos': '',
                'morphological_info': 'Анализатор недоступен'
            }
        
        try:
            parses = self.morph.parse(word)
            if not parses:
                return {
                    'word': word,
                    'lemma': word.lower(),
                    'pos': '',
                    'morphological_info': 'Не удалось разобрать'
                }
            
            parse = parses[0]
            morph_tag = self._extract_morphological_tag(parse)
            
            return {
                'word': word,
                'lemma': parse.normal_form,
                'pos': morph_tag.pos,
                'morphological_tag': morph_tag,
                'score': getattr(parse, 'score', 0),
                'methods': [str(method) for method in getattr(parse, 'methods', [])],
                'all_variants': [
                    {
                        'lemma': p.normal_form,
                        'pos': self.pos_mapping.get(p.tag.POS, '') if p.tag.POS else '',
                        'tag': str(p.tag) if p.tag else '',
                        'score': getattr(p, 'score', 0)
                    }
                    for p in parses
                ]
            }
        except Exception as e:
            return {
                'word': word,
                'lemma': word.lower(),
                'pos': '',
                'morphological_info': f'Ошибка: {str(e)}'
            }
    
    def _extract_morphological_tag_mystem(self, parse_info: Dict) -> MorphologicalTag:
        tag = MorphologicalTag()
        
        try:
            grammemes = parse_info.get('gr', '')

            pos_mapping_mystem = {
                'S': 'существительное',
                'A': 'прилагательное',
                'V': 'глагол',
                'ADV': 'наречие',
                'PR': 'предлог',
                'CONJ': 'союз',
                'PART': 'частица',
                'INTJ': 'междометие',
                'NUM': 'числительное',
                'PRO': 'местоимение',
                'APRO': 'местоимение-прилагательное',
                'SPRO': 'местоимение-существительное',
                'ADVPRO': 'местоимение-наречие',
                'PRAEDIC': 'предикатив'
            }
            
            case_mapping_mystem = {
                'им': 'именительный',
                'род': 'родительный',
                'дат': 'дательный',
                'вин': 'винительный',
                'твор': 'творительный',
                'пр': 'предложный',
                'парт': 'партитив',
                'зват': 'звательный',
                'loc': 'местный'
            }
            
            number_mapping_mystem = {
                'ед': 'единственное',
                'мн': 'множественное'
            }
            
            gender_mapping_mystem = {
                'муж': 'мужской',
                'жен': 'женский',
                'сред': 'средний'
            }
            
            tense_mapping_mystem = {
                'наст': 'настоящее',
                'прош': 'прошедшее',
                'буд': 'будущее'
            }
            
            tags = grammemes.split(',')
            for t in tags:
                t = t.strip()
                
                if '=' in t:
                    pos, rest = t.split('=', 1)
                    if pos in pos_mapping_mystem:
                        tag.pos = pos_mapping_mystem[pos]
                    
                    rest_tags = rest.split('|')
                    for rt in rest_tags:
                        rt = rt.strip()
                        if rt in case_mapping_mystem:
                            tag.case = case_mapping_mystem[rt]
                        elif rt in number_mapping_mystem:
                            tag.number = number_mapping_mystem[rt]
                        elif rt in gender_mapping_mystem:
                            tag.gender = gender_mapping_mystem[rt]
                        elif rt in tense_mapping_mystem:
                            tag.tense = tense_mapping_mystem[rt]
                        elif rt in ['несов', 'сов']:
                            tag.aspect = 'несовершенный' if rt == 'несов' else 'совершенный'
                        elif rt in ['действ', 'страд']:
                            tag.voice = 'действительный' if rt == 'действ' else 'страдательный'
                        elif rt in ['изъяв', 'повел', 'сослаг']:
                            mood_map = {'изъяв': 'изъявительное', 'повел': 'повелительное', 'сослаг': 'сослагательное'}
                            tag.mood = mood_map.get(rt, '')
                elif t in pos_mapping_mystem:
                    tag.pos = pos_mapping_mystem[t]
                    
        except Exception as e:
            print(f"Ошибка извлечения тегов pymystem3: {e}")
        
        return tag


_analyzer_instance = None


def get_analyzer() -> MorphologicalAnalyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = MorphologicalAnalyzer()
    return _analyzer_instance
