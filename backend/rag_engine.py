import json
import os
import re
import math
from typing import List, Dict, Any

from backend.config import DATA_DIR

# Normalize common Hinglish / Messenger shortcuts to canonical stems for better BM25 retrieval
HINGLISH_ALIASES = {
    "khai": "khana", "khayi": "khana", "khaya": "khana", "khaye": "khana", "khay": "khana", "khao": "khana", "khane": "khana",
    "phto": "photo", "pic": "photo", "pics": "photo", "selfie": "photo", "tasveer": "photo", "dp": "photo",
    "yd": "yaad", "yaad": "yaad", "miss": "yaad", "missing": "yaad",
    "pyar": "love", "pyaar": "love", "ishq": "love", "mohabbat": "love",
    "chumma": "kiss", "lip": "kiss", "kisses": "kiss", "kissing": "kiss",
    "gsa": "gussa", "gussa": "gussa", "naraz": "gussa", "angry": "gussa",
    "krre": "kar", "krri": "kar", "kr": "kar", "kro": "kar", "krna": "kar", "karo": "kar",
    "tm": "tum", "tmko": "tum", "tumko": "tum", "tmhra": "tumhara", "tumhari": "tumhara",
    "hm": "hum", "hmko": "hum", "mra": "mera", "mre": "mera", "mjhe": "mujhe",
    "ni": "nahi", "nii": "nahi", "nhi": "nahi", "naa": "nahi",
    "blo": "bolo", "bolna": "bolo", "btao": "batao",
    "dkho": "dekho", "dkhna": "dekho", "dekhna": "dekho", "dikhao": "dekho",
    "rt": "raat", "rat": "raat", "night": "raat",
    "thk": "theek", "thik": "theek", "tabiyat": "theek",
    "ksm": "kasam", "plz": "please", "plzz": "please", "plzzz": "please",
    "bht": "bahut", "bhut": "bahut",
}

NOISE_PATTERNS = (
    "video call ended",
    "missed a video",
    "missed a call",
    "changed the theme",
    "set the nickname",
    "set your nickname",
    "quick reaction",
    "http://",
    "https://",
    "10 th",
    "class 10",
)


GENERIC_CHITCHAT_PATTERNS = {
    "hlo", "hello", "hi", "hey", "suno", "suno na", "kya kar rahi ho", "kya kr rhi ho",
    "kya kar rahe ho", "kaha ho", "kha ho", "kuch nahi", "kuch ni", "acha", "accha",
    "theek hai", "thik hai", "ok", "hmm", "hmmm", "love u", "love you", "miss you",
    "miss u", "yaad aa rahi", "khana khai", "khana khayi", "khana khaya", "photo bhejo",
    "pic bhejo", "kiss do", "good night", "gn", "so jao", "good morning", "gm",
    "kuch bolo", "aur batao", "or btao", "kya chal raha", "kaise ho", "kse ho"
}

class RAGEngine:
    def __init__(self):
        self.chunks_file = os.path.join(DATA_DIR, "conversation_chunks.json")
        self.messages_file = os.path.join(DATA_DIR, "processed_conversations.json")
        self.chunks: List[Dict[str, Any]] = []
        self.messages: List[Dict[str, Any]] = []
        self.index: Dict[str, List[int]] = {}
        self.chunk_tokens: List[List[str]] = []
        self.chunk_lengths: List[int] = []
        self.avg_chunk_length: float = 0.0
        self.doc_count: int = 0
        self.load_data()

    def _is_noisy_message(self, text: str) -> bool:
        if not text:
            return True
        lower = text.lower().strip()
        return any(pat in lower for pat in NOISE_PATTERNS)

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        text = text.lower()
        words = re.findall(r'\b[a-z0-9_]{2,}\b', text)
        return [HINGLISH_ALIASES.get(w, w) for w in words]

    def load_data(self):
        if os.path.exists(self.chunks_file):
            with open(self.chunks_file, 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)
        if os.path.exists(self.messages_file):
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                self.messages = json.load(f)

        self.doc_count = len(self.chunks)
        self.index = {}
        self.chunk_tokens = []
        self.chunk_lengths = []

        total_length = 0
        for idx, chunk in enumerate(self.chunks):
            clean_texts = [
                m.get('content', '')
                for m in chunk.get('messages', [])
                if not self._is_noisy_message(m.get('content', ''))
            ]
            tokens = self._tokenize(" ".join(clean_texts))
            self.chunk_tokens.append(tokens)
            self.chunk_lengths.append(len(tokens))
            total_length += len(tokens)

            for w in set(tokens):
                self.index.setdefault(w, []).append(idx)

        self.avg_chunk_length = (total_length / self.doc_count) if self.doc_count > 0 else 1.0
        print(f"[RAGEngine] Loaded {self.doc_count} chunks and {len(self.messages)} messages. Vocabulary size: {len(self.index)}")

    def search_chunks(self, query: str, top_k: int = 3, min_score: float = 2.8) -> List[Dict[str, Any]]:
        clean_q = re.sub(r'[^a-zA-Z0-9\s]', '', (query or '').lower()).strip()
        # Generic daily chitchat should never pull random historical family/school drama chunks
        if clean_q in GENERIC_CHITCHAT_PATTERNS or len(clean_q.split()) <= 2:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens or self.doc_count == 0:
            return []

        k1 = 1.5
        b = 0.75
        scores = [0.0] * self.doc_count

        for token in query_tokens:
            if token in self.index:
                doc_list = self.index[token]
                df = len(doc_list)
                idf = math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))
                for chunk_idx in doc_list:
                    tokens_in_doc = self.chunk_tokens[chunk_idx]
                    tf = tokens_in_doc.count(token)
                    doc_len = max(1, self.chunk_lengths[chunk_idx])
                    tf_norm = (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (doc_len / self.avg_chunk_length)))
                    scores[chunk_idx] += idf * tf_norm

        scored_chunks = [(score, self.chunks[idx]) for idx, score in enumerate(scores) if score >= min_score]
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        return [chunk for _, chunk in scored_chunks[:top_k]]

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
            lines = []
            # Merge adjacent same-sender short fragments cleanly, ignore call logs & links
            prev_role = None
            for m in c.get('messages', []):
                text = (m.get('content') or '').strip()
                if not text or self._is_noisy_message(text):
                    continue
                role_label = "Nishant" if m['role'] == 'user' else "Alquama"
                if lines and prev_role == role_label:
                    lines[-1] += f" | {text}"
                else:
                    lines.append(f"{role_label}: {text}")
                    prev_role = role_label
                if len(lines) >= 8:
                    break
            if lines:
                formatted.append("--- Past Chat Style Sample ---")
                formatted.extend(lines)
        return "\n".join(formatted)


rag_engine = RAGEngine()
