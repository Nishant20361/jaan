import json
import os
import re
import math
from collections import Counter
from typing import List, Dict, Any, Optional

from backend.config import DATA_DIR

class RAGEngine:
    def __init__(self):
        self.chunks_file = os.path.join(DATA_DIR, "conversation_chunks.json")
        self.messages_file = os.path.join(DATA_DIR, "processed_conversations.json")
        self.chunks: List[Dict[str, Any]] = []
        self.messages: List[Dict[str, Any]] = []
        self.index: Dict[str, List[int]] = {}  # word -> list of chunk indices
        self.chunk_lengths: List[int] = []
        self.avg_chunk_length: float = 0.0
        self.doc_count: int = 0
        self.load_data()

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        text = text.lower()
        # Remove punctuation, keep alphanumerics
        words = re.findall(r'\b[a-z0-9_]{2,}\b', text)
        return words

    def load_data(self):
        if os.path.exists(self.chunks_file):
            with open(self.chunks_file, 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)
        if os.path.exists(self.messages_file):
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                self.messages = json.load(f)

        self.doc_count = len(self.chunks)
        self.index = {}
        self.chunk_lengths = []

        total_length = 0
        for idx, chunk in enumerate(self.chunks):
            chunk_text = " ".join([m.get('content', '') for m in chunk.get('messages', [])])
            tokens = self._tokenize(chunk_text)
            self.chunk_lengths.append(len(tokens))
            total_length += len(tokens)
            
            unique_words = set(tokens)
            for w in unique_words:
                if w not in self.index:
                    self.index[w] = []
                self.index[w].append(idx)

        self.avg_chunk_length = (total_length / self.doc_count) if self.doc_count > 0 else 1.0
        print(f"[RAGEngine] Loaded {self.doc_count} chunks and {len(self.messages)} messages. Vocabulary size: {len(self.index)}")

    def search_chunks(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            # Fallback to returning a few representative playful/caring chunks
            return self.chunks[:top_k]

        k1 = 1.5
        b = 0.75
        scores = [0.0] * self.doc_count

        for token in query_tokens:
            if token in self.index:
                doc_list = self.index[token]
                df = len(doc_list)
                # BM25 IDF
                idf = math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))
                for chunk_idx in doc_list:
                    chunk = self.chunks[chunk_idx]
                    chunk_text = " ".join([m.get('content', '') for m in chunk.get('messages', [])]).lower()
                    tf = chunk_text.count(token)
                    doc_len = self.chunk_lengths[chunk_idx]
                    
                    # BM25 TF formula
                    tf_norm = (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (doc_len / self.avg_chunk_length)))
                    scores[chunk_idx] += idf * tf_norm

        # Rank by score
        scored_chunks = [(score, self.chunks[idx]) for idx, score in enumerate(scores) if score > 0]
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        if not scored_chunks:
            # If no direct keyword match, choose chunks with rich exchanges
            return self.chunks[10:10 + top_k]

        return [chunk for score, chunk in scored_chunks[:top_k]]

    def search_messages(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        query_lower = query.lower().strip()
        if not query_lower:
            return self.messages[-limit:]
            
        results = []
        for msg in self.messages:
            content = (msg.get('content') or '').lower()
            if query_lower in content:
                results.append(msg)
            elif any(query_lower in (r.get('actor', '').lower()) for r in msg.get('reactions', [])):
                results.append(msg)
                
        return results[:limit]

    def format_chunks_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        formatted = []
        for c in chunks:
            formatted.append(f"--- Historical Conversation Memory ({c.get('date', 'Past')}) ---")
            for m in c.get('messages', [])[:12]:
                role_label = "Nishant (User)" if m['role'] == 'user' else "Alquama/Jaan"
                text = m.get('content', '')
                if text:
                    formatted.append(f"{role_label}: {text}")
                elif m.get('sticker'):
                    formatted.append(f"{role_label}: [Sent Sticker]")
                elif m.get('photos'):
                    formatted.append(f"{role_label}: [Sent Photo]")
                elif m.get('gifs'):
                    formatted.append(f"{role_label}: [Sent GIF]")
        return "\n".join(formatted)

rag_engine = RAGEngine()

