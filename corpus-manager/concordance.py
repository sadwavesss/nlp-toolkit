from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ConcordanceLine:
    left_context: str
    keyword: str
    right_context: str
    document_id: int
    document_title: str
    position: int

class ConcordanceBuilder:
    
    def __init__(self, context_size: int = 50):
        self.context_size = context_size
    
    def build_concordance(self, documents: List[Dict], search_results: List[Dict]) -> List[ConcordanceLine]:
        concordance = []

        doc_dict = {doc['id']: doc for doc in documents}
        
        for result in search_results:
            doc_id = result['document_id']
            word_position = result['position']
            keyword = result['word']
            
            if doc_id not in doc_dict:
                continue
                
            document = doc_dict[doc_id]
            text = document['raw_text']

            words = text.split()
            if word_position >= len(words):
                continue

            left_start = max(0, word_position - self.context_size)
            right_end = min(len(words), word_position + self.context_size + 1)

            left_context = ' '.join(words[left_start:word_position])
            right_context = ' '.join(words[word_position + 1:right_end])
            
            concordance_line = ConcordanceLine(
                left_context=left_context,
                keyword=keyword,
                right_context=right_context,
                document_id=doc_id,
                document_title=document.get('title', 'Без названия'),
                position=word_position
            )
            
            concordance.append(concordance_line)
        
        return concordance
    
    def format_concordance_line(self, line: ConcordanceLine) -> str:
        left = line.left_context[-30:] if len(line.left_context) > 30 else line.left_context
        right = line.right_context[:30] if len(line.right_context) > 30 else line.right_context
        
        left_part = f"...{left}" if len(line.left_context) > 30 else left
        right_part = f"{right}..." if len(line.right_context) > 30 else right
        
        return f"{left_part} [{line.keyword}] {right_part}"
    
    def format_concordance_html(self, line: ConcordanceLine) -> str:
        left = line.left_context[-50:] if len(line.left_context) > 50 else line.left_context
        right = line.right_context[:50] if len(line.right_context) > 50 else line.right_context
        
        left_part = f"...{left}" if len(line.left_context) > 50 else left
        right_part = f"{right}..." if len(line.right_context) > 50 else right
        
        return f"""
        <div class="concordance-line">
            <span class="left-context">{left_part}</span>
            <span class="keyword">{line.keyword}</span>
            <span class="right-context">{right_part}</span>
            <span class="source">({line.document_title}, позиция {line.position})</span>
        </div>
        """
