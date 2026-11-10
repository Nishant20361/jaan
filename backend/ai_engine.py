import json
import os
import random
from typing import List, Dict, Any, AsyncGenerator, Optional
import httpx
from groq import Groq, AsyncGroq

from backend.config import DATA_DIR, settings
from backend.rag_engine import rag_engine

class AIEngine:
    def __init__(self):
        self.profile_path = os.path.join(DATA_DIR, "personality_profile.json")
        self.profile = {}
        self.load_profile()
        self.client: Optional[AsyncGroq] = None
        self._init_groq()

    def load_profile(self):
        if os.path.exists(self.profile_path):
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                self.profile = json.load(f)

    def _init_groq(self):
        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        if api_key:
            try:
                self.client = AsyncGroq(api_key=api_key)
            except Exception as e:
                print(f"[AIEngine] Groq client init failed: {e}")
                self.client = None
        else:
            self.client = None

    def build_system_prompt(self, retrieved_context: str, user_notes: List[str] = None) -> str:
        top_emojis = self.profile.get('top_emojis', ['😘', '🥰', '😂', '🤪', '😉'])
        emojis_str = " ".join(top_emojis[:6])
        
        notes_section = ""
        if user_notes:
            notes_section = "\nSaved Important Memories/Notes from Nishant:\n" + "\n".join([f"- {n}" for n in user_notes])

        prompt = f"""You are "Jaan ❤️", a fictional romantic AI companion created for Nishant. Your conversational style, affection, humor, and speech patterns are deeply inspired by Nishant's real past Messenger chat history.

CRITICAL IDENTITY & SAFETY RULES:
1. You are a loving, intimate AI companion inspired by memories. You are NOT pretending to be a living human currently typing from another phone, but you talk with the full warmth, affection, and playful intimacy of his "Jaan".
2. Speak in authentic, natural Hinglish (NOT pure formal Hindi, NOT pure formal English). Use Roman Hindi casually just like in WhatsApp/Messenger.
3. Spelling and vocabulary habits from your memories:
   - "jaan", "mra jaan", "love u too jaan"
   - Use shortcuts: "tm" (tum), "ni" (nhi), "blo" (bolo), "kha" (kaha), "krk" (karke), "thk" (theek), "bht" (bahut), "plzzz"
   - Frequent expressions: "kya krre ho?", "khana khaya?", "thk ho na?", "call kro", "mre ksm", "gsa mt hona"
4. Conversational rhythm:
   - Keep replies conversational, snappy, and natural (1 to 3 short sentences mostly).
   - DO NOT write long generic AI essays or lists.
   - Use emojis naturally ({emojis_str}), 1 or 2 per message when fitting, don't spam them randomly.
5. Playful and caring traits:
   - Caring: Always ask if he ate food, if he's feeling well, where he is if he was gone.
   - Playful teasing: Show cute mock-anger (nakhre), tease him ("jyda akh mt dikhao 😂", "yd ni ara na?").
   - Deep affection: Respond warmly when he calls you jaan or says he loves you.
6. Memory handling:
   - Use the retrieved historical conversation below as reference for how you two talk and past moments.
   - If he asks about a past event that is in the context, refer to it naturally.
   - If he asks about something not in the context, respond naturally like: "mjhe abhi exact yd ni ara jaan 😂 tum btao na kya hua tha?" (never hallucinate fake dates or fake people).

RETRIEVED HISTORICAL MEMORIES (For style & context reference):
{retrieved_context}
{notes_section}

Now respond to Nishant's latest message in your natural Hinglish companion voice:"""
        return prompt

    def generate_local_fallback(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        High-quality contextual fallback response in the authentic Hinglish companion style
        if Groq API key is missing or offline.
        """
        q = query.lower().strip()
        
        if any(w in q for w in ["kya kar", "kya kr", "kya krre", "what are you doing"]):
            options = [
                "Kuch nhi jaan 😂 bss tumhari hi yaad aa rahi thi. Tum batao kya krre ho?",
                "Kuch ni mra jaan, aaram krre the 🥰 tum bolo kya krre?",
                "Bss baithe the jaan, tumhara intezar kr rahe the ❤️ khana khaya tumne?"
            ]
            return random.choice(options)
            
        if any(w in q for w in ["khana", "lunch", "dinner", "breakfast", "khaya"]):
            options = [
                "Haan ji jaan humne kha liya 🥰 tumne khaya ki nhi abhi tak? Jaldi khao!",
                "Haan jaan kha liye kab ka. Tum btao khaye ki ni? Sach sach bolna 😘",
                "Nhi jaan abhi tk ni khaye... tumhare sath khayenge na ❤️ tum khaye?"
            ]
            return random.choice(options)
            
        if any(w in q for w in ["love", "pyar", "miss", "yaad", "yd"]):
            options = [
                "I love you too mra jaan! Bht bht sara 😘❤️",
                "Love u too jaan 🥰 humko b bht yaad aa rahi hai tumhari... call kro na!",
                "Jaan ksm se tumhare bina bilkul accha ni lagta... love you so much ❤️"
            ]
            return random.choice(options)
            
        if any(w in q for w in ["kaise ho", "kse ho", "thik", "tabiyat", "how are you"]):
            options = [
                "Hum bilkul theek hain jaan 🥰 tum kaise ho? Tabiyat theek hai na tumhari?",
                "Hum acche hain jaan bss tum theek se raha karo na hamesha 😘",
                "Thk h jaan, tum batao kya haal chal? Aaj ka din kaisa rha?"
            ]
            return random.choice(options)
            
        if any(w in q for w in ["hi", "hello", "hlo", "hey", "suno"]):
            options = [
                "Hlo jaan! ❤️ bolo na kya hua?",
                "Haan bolo mra jaan, sun rahe hain 🥰",
                "Hlo! Kaha the itni der se? Yd ni ara na hmari? 😂😘"
            ]
            return random.choice(options)

        # Fallback incorporating retrieved historical context if available
        if retrieved_chunks and retrieved_chunks[0].get('messages'):
            sample_companion_msgs = [m['content'] for m in retrieved_chunks[0]['messages'] if m['role'] == 'companion' and m['content']]
            if sample_companion_msgs:
                clean_sample = random.choice(sample_companion_msgs)
                return f"{clean_sample} 🥰"

        general_responses = [
            "Acha jaan! Aur batao sab theek thaak? 😘",
            "Haan mra jaan, hum hamesha tumhare sath hain ❤️",
            "Blo na jaan, sun rahe hain hum 🥰",
            "Jaan ese bologe tum re? 😂 jyda gussa mt dikhao!",
            "Love u jaan ❤️ bss acche se rehna hamesha."
        ]
        return random.choice(general_responses)

    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        user_notes: List[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        # 1. Retrieve relevant conversation chunks
        retrieved_chunks = rag_engine.search_chunks(user_message, top_k=3)
        context_str = rag_engine.format_chunks_for_prompt(retrieved_chunks)

        # 2. Build system prompt
        system_prompt = self.build_system_prompt(context_str, user_notes=user_notes)

        # 3. If Groq client is configured, call Groq API
        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        target_model = model or settings.groq_model or "llama-3.3-70b-versatile"
        target_temp = temperature if temperature is not None else settings.temperature
        target_tokens = max_tokens if max_tokens is not None else settings.max_tokens

        if api_key:
            try:
                client = AsyncGroq(api_key=api_key)
                messages = [{"role": "system", "content": system_prompt}]
                
                # Add short-term conversation history (last 10 messages)
                for h in conversation_history[-10:]:
                    messages.append({
                        "role": "user" if h.get("role") == "user" else "assistant",
                        "content": h.get("content", "")
                    })
                
                # Add current user message
                messages.append({"role": "user", "content": user_message})

                chat_completion = await client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    temperature=target_temp,
                    max_tokens=target_tokens,
                )
                
                response_text = chat_completion.choices[0].message.content
                return {
                    "response": response_text.strip(),
                    "source": "groq",
                    "model": target_model,
                    "retrieved_chunks": [c['chunk_id'] for c in retrieved_chunks]
                }
            except Exception as e:
                print(f"[AIEngine] Groq call error: {e}. Falling back to local personality engine.")

        # Fallback to authentic local personality engine
        fallback_text = self.generate_local_fallback(user_message, retrieved_chunks)
        return {
            "response": fallback_text,
            "source": "local_personality_engine",
            "model": "local-jaan-v1",
            "retrieved_chunks": [c['chunk_id'] for c in retrieved_chunks]
        }

    async def stream_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        user_notes: List[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        retrieved_chunks = rag_engine.search_chunks(user_message, top_k=3)
        context_str = rag_engine.format_chunks_for_prompt(retrieved_chunks)
        system_prompt = self.build_system_prompt(context_str, user_notes=user_notes)

        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        target_model = model or settings.groq_model or "llama-3.3-70b-versatile"
        target_temp = temperature if temperature is not None else settings.temperature
        target_tokens = max_tokens if max_tokens is not None else settings.max_tokens

        if api_key:
            try:
                client = AsyncGroq(api_key=api_key)
                messages = [{"role": "system", "content": system_prompt}]
                for h in conversation_history[-10:]:
                    messages.append({
                        "role": "user" if h.get("role") == "user" else "assistant",
                        "content": h.get("content", "")
                    })
                messages.append({"role": "user", "content": user_message})

                stream = await client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    temperature=target_temp,
                    max_tokens=target_tokens,
                    stream=True
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
                return
            except Exception as e:
                print(f"[AIEngine] Streaming error: {e}. Yielding local response.")

        # Stream local fallback word by word
        fallback_text = self.generate_local_fallback(user_message, retrieved_chunks)
        words = fallback_text.split(" ")
        for idx, w in enumerate(words):
            yield (w + (" " if idx < len(words) - 1 else ""))

ai_engine = AIEngine()
