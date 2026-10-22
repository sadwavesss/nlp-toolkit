from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import json


@dataclass
class MorphologicalTag:
    pos: str = ""
    case: str = ""
    number: str = ""
    gender: str = ""
    animacy: str = ""
    tense: str = ""
    person: str = ""
    aspect: str = ""
    voice: str = ""
    mood: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            'pos': self.pos,
            'case': self.case,
            'number': self.number,
            'gender': self.gender,
            'animacy': self.animacy,
            'tense': self.tense,
            'person': self.person,
            'aspect': self.aspect,
            'voice': self.voice,
            'mood': self.mood
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'MorphologicalTag':
        return cls(**data)
    
    def to_string(self) -> str:
        tags = []
        if self.pos: tags.append(self.pos)
        if self.case: tags.append(self.case)
        if self.number: tags.append(self.number)
        if self.gender: tags.append(self.gender)
        if self.animacy: tags.append(self.animacy)
        if self.tense: tags.append(self.tense)
        if self.person: tags.append(self.person)
        if self.aspect: tags.append(self.aspect)
        if self.voice: tags.append(self.voice)
        if self.mood: tags.append(self.mood)
        return ", ".join(tags) if tags else ""


@dataclass
class Wordform:
    text: str
    lemma: str
    morph_tag: MorphologicalTag
    position_in_text: int
    sentence_id: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'lemma': self.lemma,
            'morph_tag': self.morph_tag.to_dict(),
            'position_in_text': self.position_in_text,
            'sentence_id': self.sentence_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Wordform':
        return cls(
            text=data['text'],
            lemma=data['lemma'],
            morph_tag=MorphologicalTag.from_dict(data['morph_tag']),
            position_in_text=data['position_in_text'],
            sentence_id=data.get('sentence_id', 0)
        )


@dataclass
class DocumentMetadata:
    filename: str
    title: str = ""
    author: str = ""
    source: str = ""
    genre: str = ""
    creation_date: Optional[datetime] = None
    word_count: int = 0
    sentence_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'filename': self.filename,
            'title': self.title,
            'author': self.author,
            'source': self.source,
            'genre': self.genre,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'word_count': self.word_count,
            'sentence_count': self.sentence_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        creation_date = None
        if data.get('creation_date'):
            creation_date = datetime.fromisoformat(data['creation_date'])
        
        return cls(
            filename=data['filename'],
            title=data.get('title', ''),
            author=data.get('author', ''),
            source=data.get('source', ''),
            genre=data.get('genre', ''),
            creation_date=creation_date,
            word_count=data.get('word_count', 0),
            sentence_count=data.get('sentence_count', 0)
        )


@dataclass
class Document:
    id: str
    metadata: DocumentMetadata
    raw_text: str
    wordforms: List[Wordform] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'metadata': self.metadata.to_dict(),
            'raw_text': self.raw_text,
            'wordforms': [wf.to_dict() for wf in self.wordforms]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        return cls(
            id=data['id'],
            metadata=DocumentMetadata.from_dict(data['metadata']),
            raw_text=data['raw_text'],
            wordforms=[Wordform.from_dict(wf) for wf in data.get('wordforms', [])]
        )


@dataclass
class CorpusStatistics:
    total_documents: int = 0
    total_wordforms: int = 0
    total_lemmas: int = 0
    unique_lemmas: int = 0
    total_sentences: int = 0
    average_words_per_document: float = 0.0
    lemma_frequencies: Dict[str, int] = field(default_factory=dict)
    pos_frequencies: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_documents': self.total_documents,
            'total_wordforms': self.total_wordforms,
            'total_lemmas': self.total_lemmas,
            'unique_lemmas': self.unique_lemmas,
            'total_sentences': self.total_sentences,
            'average_words_per_document': self.average_words_per_document,
            'lemma_frequencies': self.lemma_frequencies,
            'pos_frequencies': self.pos_frequencies
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorpusStatistics':
        return cls(
            total_documents=data.get('total_documents', 0),
            total_wordforms=data.get('total_wordforms', 0),
            total_lemmas=data.get('total_lemmas', 0),
            unique_lemmas=data.get('unique_lemmas', 0),
            total_sentences=data.get('total_sentences', 0),
            average_words_per_document=data.get('average_words_per_document', 0.0),
            lemma_frequencies=data.get('lemma_frequencies', {}),
            pos_frequencies=data.get('pos_frequencies', {})
        )


@dataclass
class Corpus:
    name: str
    description: str = ""
    documents: Dict[str, Document] = field(default_factory=dict)
    statistics: CorpusStatistics = field(default_factory=CorpusStatistics)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'documents': {doc_id: doc.to_dict() for doc_id, doc in self.documents.items()},
            'statistics': self.statistics.to_dict(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Corpus':
        created_at = datetime.fromisoformat(data['created_at'])
        updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            documents={doc_id: Document.from_dict(doc) for doc_id, doc in data.get('documents', {}).items()},
            statistics=CorpusStatistics.from_dict(data.get('statistics', {})),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def add_document(self, document: Document) -> None:
        self.documents[document.id] = document
        self.updated_at = datetime.now()
        self._recalculate_statistics()
    
    def remove_document(self, document_id: str) -> bool:
        if document_id in self.documents:
            del self.documents[document_id]
            self.updated_at = datetime.now()
            self._recalculate_statistics()
            return True
        return False
    
    def _recalculate_statistics(self) -> None:
        self.statistics.total_documents = len(self.documents)
        self.statistics.total_wordforms = sum(len(doc.wordforms) for doc in self.documents.values())
        self.statistics.total_sentences = sum(doc.metadata.sentence_count for doc in self.documents.values())
        
        if self.statistics.total_documents > 0:
            self.statistics.average_words_per_document = self.statistics.total_wordforms / self.statistics.total_documents

        lemma_freq = {}
        pos_freq = {}
        lemmas = set()
        
        for doc in self.documents.values():
            for wf in doc.wordforms:
                lemmas.add(wf.lemma)
                lemma_freq[wf.lemma] = lemma_freq.get(wf.lemma, 0) + 1
                if wf.morph_tag.pos:
                    pos_freq[wf.morph_tag.pos] = pos_freq.get(wf.morph_tag.pos, 0) + 1
        
        self.statistics.lemma_frequencies = lemma_freq
        self.statistics.pos_frequencies = pos_freq
        self.statistics.unique_lemmas = len(lemmas)
        self.statistics.total_lemmas = sum(lemma_freq.values())
