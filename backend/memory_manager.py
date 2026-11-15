import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.config import DB_PATH

class MemoryManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # User defined memories and notes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tag TEXT DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Active chat history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    media_uri TEXT,
                    media_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # App settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_memory(self, title: str, content: str, tag: str = "general") -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_memories (title, content, tag) VALUES (?, ?, ?)",
                (title, content, tag)
            )
            conn.commit()
            memory_id = cursor.lastrowid
            return {
                "id": memory_id,
                "title": title,
                "content": content,
                "tag": tag,
                "created_at": datetime.utcnow().isoformat()
            }

    def get_memories(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, content, tag, created_at FROM user_memories ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_memory(self, memory_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def save_chat_message(self, session_id: str, role: str, content: str, media_uri: Optional[str] = None, media_type: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (session_id, role, content, media_uri, media_type) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, media_uri, media_type)
            )
            conn.commit()

    def get_chat_history(self, session_id: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, role, content, media_uri, media_type, created_at
                FROM (
                    SELECT id, role, content, media_uri, media_type, created_at
                    FROM chat_history
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                ) recent
                ORDER BY id ASC
                """,
                (session_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_recent_media_uris(self, session_id: str = "default", media_type: Optional[str] = None, limit: int = 10) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if media_type:
                cursor.execute(
                    "SELECT media_uri FROM chat_history WHERE session_id = ? AND media_type = ? AND media_uri IS NOT NULL ORDER BY id DESC LIMIT ?",
                    (session_id, media_type, limit)
                )
            else:
                cursor.execute(
                    "SELECT media_uri FROM chat_history WHERE session_id = ? AND media_uri IS NOT NULL ORDER BY id DESC LIMIT ?",
                    (session_id, limit)
                )
            rows = cursor.fetchall()
            return [row["media_uri"] for row in rows if row["media_uri"]]

    def clear_chat_history(self, session_id: str = "default") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount

    def search_past_conversations(
        self,
        session_id: str = "default",
        query: str = "",
        exclude_ids: Optional[List[int]] = None,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Search older conversations in chat_history for relevant past messages/topics.
        Excludes recent messages so only past/forgotten context is recalled.
        """
        if not query or not query.strip():
            return []

        exclude_ids = exclude_ids or []
        import re
        stop_words = {
            "kya", "hai", "ho", "hu", "hain", "ko", "ka", "ke", "ki", "se", "me", "mai", "aur", "or",
            "to", "bhi", "tha", "thi", "the", "batao", "bolo", "na", "hlo", "hello", "hi", "hey",
            "jaan", "babu", "accha", "acha", "theek", "thik", "ok", "plz", "please", "suno",
            "aaj", "ab", "abhi", "kar", "kr", "raha", "rahi", "rhe", "rhi", "karoge", "karenge",
            "mujhe", "tumhe", "humko", "aapko", "mera", "meri", "mere", "tumhara", "tumhari", "tumhare"
        }
        words = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', query.lower())
        keywords = [w for w in words if w not in stop_words]

        q_lower = query.lower()
        is_recall_query = any(k in q_lower for k in ["yaad", "remember", "pata", "bola tha", "kaha tha", "pehle", "kal", "pichli"])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            results = []

            if keywords:
                like_clauses = " OR ".join(["content LIKE ?" for _ in keywords])
                params = [session_id]
                exclude_clause = ""
                if exclude_ids:
                    placeholders = ",".join(["?" for _ in exclude_ids])
                    exclude_clause = f"AND id NOT IN ({placeholders})"
                    params.extend(exclude_ids)

                params.extend([f"%{kw}%" for kw in keywords])
                params.append(limit * 2)

                query_sql = f"""
                    SELECT id, role, content, media_uri, media_type, created_at
                    FROM chat_history
                    WHERE session_id = ?
                      {exclude_clause}
                      AND ({like_clauses})
                    ORDER BY id DESC
                    LIMIT ?
                """
                cursor.execute(query_sql, params)
                rows = cursor.fetchall()
                for row in rows:
                    msg_dict = dict(row)
                    if msg_dict["role"] == "user":
                        cursor.execute(
                            "SELECT content FROM chat_history WHERE session_id = ? AND id > ? AND role = 'companion' ORDER BY id ASC LIMIT 1",
                            (session_id, msg_dict["id"])
                        )
                        reply_row = cursor.fetchone()
                        msg_dict["reply_content"] = reply_row["content"] if reply_row else ""
                    results.append(msg_dict)
                    if len(results) >= limit:
                        break

            # If it's an explicit recall question and few/no keyword matches, fetch earlier highlights
            if is_recall_query and len(results) < limit:
                params = [session_id]
                exclude_clause = ""
                if exclude_ids:
                    placeholders = ",".join(["?" for _ in exclude_ids])
                    exclude_clause = f"AND id NOT IN ({placeholders})"
                    params.extend(exclude_ids)

                cursor.execute(f"""
                    SELECT id, role, content, media_uri, media_type, created_at
                    FROM chat_history
                    WHERE session_id = ?
                      {exclude_clause}
                      AND role = 'user'
                      AND length(content) > 6
                    ORDER BY id DESC
                    LIMIT ?
                """, (*params, limit - len(results)))
                for row in cursor.fetchall():
                    r_dict = dict(row)
                    cursor.execute(
                        "SELECT content FROM chat_history WHERE session_id = ? AND id > ? AND role = 'companion' ORDER BY id ASC LIMIT 1",
                        (session_id, r_dict["id"])
                    )
                    reply_row = cursor.fetchone()
                    r_dict["reply_content"] = reply_row["content"] if reply_row else ""
                    if not any(x["id"] == r_dict["id"] for x in results):
                        results.append(r_dict)

            return results

    def auto_extract_facts(self, user_message: str):
        """
        Automatically detect and remember key facts Nishant shares about his life,
        routines, preferences, or events so Alquama remembers them across sessions.
        """
        if not user_message or len(user_message) < 8:
            return

        import re
        q = user_message.strip()
        lower = q.lower()

        patterns = [
            (r"(?:mera|meri|mere)\s+(birthday|bday|janamdin)\s+(?:hai\s+)?([^\.,!\?]+)", "Birthday"),
            (r"(?:mujhe|humko)\s+([^\.,!\?]+)\s+(?:bahut\s+)?(?:pasand|achha lagta|fav|favourite)\s+hai", "Preference"),
            (r"(?:mera|meri|mere)\s+(favourite|fav)\s+([^\.,!\?]+)\s+hai", "Favorite"),
            (r"(?:aaj|kal)\s+(?:mera|meri)\s+(exam|interview|meeting|test|presentation)\s+hai", "Event"),
            (r"(?:meri|humari)\s+(tabiyat|health)\s+(kharab|theek nahi|down)\s+hai", "Health"),
            (r"(?:mai|hum)\s+([a-zA-Z0-9_\s]+)\s+(?:me\s+kaam\s+karta\s+hu|me\s+job\s+karta\s+hu)", "Work/Job"),
        ]

        for pat, tag in patterns:
            match = re.search(pat, lower)
            if match:
                fact_text = q
                existing = self.get_memories()
                if not any(m.get("content") == fact_text for m in existing):
                    self.add_memory(title=f"Nishant's {tag}", content=fact_text, tag="auto_fact")
                break

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

memory_manager = MemoryManager()

