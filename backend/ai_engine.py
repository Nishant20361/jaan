import json
import os
import random
import re
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple
from groq import AsyncGroq

from backend.config import DATA_DIR, settings
from backend.rag_engine import rag_engine

HINGLISH_MARKERS = {
    "kya", "kyu", "kyun", "kr", "kar", "krre", "krri", "karo", "kro", "krna", "karna",
    "rhi", "rahi", "rhe", "rahe", "ho", "hai", "hu", "hoon", "tha", "thi", "the",
    "ni", "nii", "nhi", "nahi", "na", "naa", "haa", "haan", "tm", "tum", "tmko", "tumko",
    "tmhra", "tumhara", "tumhari", "hm", "hum", "hmko", "mra", "mre", "mri", "mera",
    "meri", "mere", "mjhe", "mujhe", "blo", "bolo", "btao", "batao", "bata", "bhej", "bhejo",
    "bhejna", "dkho", "dekho", "dkhna", "dekhna", "dikhao", "khana", "khai", "khayi",
    "khaya", "khaye", "khao", "kha", "kaha", "abhi", "acha", "accha", "bht", "bhut",
    "bahut", "plz", "plzz", "plzzz", "yaad", "yd", "pyar", "pyaar", "ksm", "kasam",
    "gsa", "gussa", "naraz", "raat", "rt", "kal", "aaj", "yr", "yar", "yaar", "apna", "apni",
    "hamara", "humara", "saath", "sth", "paas", "pas", "idhar", "udhar", "milna", "milo",
    "degi", "dungi", "dunga", "lga", "laga", "thk", "thik", "theek", "kaisa", "kaisi",
    "kaise", "ka", "ki", "ke", "ko", "me", "se", "pe", "par", "aur", "toh", "re", "ji",
    "chahiye", "sone", "sote", "soyi", "soye", "mn", "man", "baat", "bt", "chodo", "chro",
    "suno", "mar", "marenge", "pyari", "badmash", "pagal", "chumma", "gale", "raho",
    "aao", "jao", "gye", "gaye", "gayi", "gyi", "aaye", "aayi", "bol", "de", "do",
    "lo", "le", "mat", "mt", "kuch", "kch", "sab", "sb", "koi", "nah", "wese", "aise",
    "ese", "jab", "jb", "tab", "tb", "kab", "kb", "kisse", "kisko", "iska", "uska",
    "tumse", "tmse", "mujhse", "mjse", "tere", "tra", "tre", "tri", "tera", "teri",
    "dono", "ek", "dusra", "or", "hlo", "phto", "wagera", "krdo", "kardo", "bnao"
}

AMBIGUOUS_OVERLAP_WORDS = {
    "me", "do", "so", "or", "re", "par", "man", "to", "hi", "he", "no", "us", "in", "a", "at", "mar"
}

ENGLISH_WORDS = {
    "the", "is", "are", "was", "were", "am", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "can", "may",
    "might", "must", "shall", "how", "what", "why", "where", "when", "who", "which",
    "you", "your", "yours", "my", "mine", "me", "i", "we", "us", "our", "they",
    "this", "that", "these", "those", "here", "there", "very", "much", "so", "too",
    "really", "actually", "today", "tonight", "morning", "evening", "night", "day",
    "missed", "missing", "send", "show", "picture", "photo", "selfie", "please",
    "want", "need", "feel", "feeling", "thinking", "about", "with", "without",
    "because", "if", "then", "than", "just", "only", "still", "already", "never",
    "always", "sometimes", "doing", "going", "coming", "talking", "telling", "asking",
    "good", "bad", "great", "fine", "okay", "cute", "pretty", "beautiful", "hot",
    "sexy", "romantic", "closer", "hold", "hug", "kiss", "love", "care", "sorry",
    "hey", "hello", "babe", "baby", "sweetheart", "darling"
}


class AIEngine:
    def __init__(self):
        self.profile_path = os.path.join(DATA_DIR, "personality_profile.json")
        self.style_path = os.path.join(DATA_DIR, "style_examples.json")
        self.media_path = os.path.join(DATA_DIR, "curated_media.json")
        self.profile: Dict[str, Any] = {}
        self.style_examples: Dict[str, Any] = {}
        self.curated_media: Dict[str, Any] = {}
        self.load_assets()
        self.client: Optional[AsyncGroq] = None
        self._init_groq()

    def load_assets(self):
        if os.path.exists(self.profile_path):
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                self.profile = json.load(f)
        if os.path.exists(self.style_path):
            with open(self.style_path, 'r', encoding='utf-8') as f:
                self.style_examples = json.load(f)
        if os.path.exists(self.media_path):
            with open(self.media_path, 'r', encoding='utf-8') as f:
                self.curated_media = json.load(f)

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

    def detect_user_language(self, text: str) -> str:
        """
        Detect whether Nishant is writing in English vs Hinglish.
        Treat affection terms like 'jaan', 'baby', 'love' as language-neutral.
        """
        words = re.findall(r"[a-zA-Z']+", (text or "").lower())
        if not words:
            return "hinglish"

        neutral = {"jaan", "babu", "baby", "babe", "love", "u", "ok", "hmm", "hmmm", "hlo", "hi", "hey"}
        unambiguous_hinglish = [
            w for w in words
            if w in HINGLISH_MARKERS and w not in neutral and w not in AMBIGUOUS_OVERLAP_WORDS
        ]
        if unambiguous_hinglish:
            return "hinglish"

        strong_english = [
            w for w in words
            if w in ENGLISH_WORDS and w not in neutral and w not in HINGLISH_MARKERS
        ]
        if len(strong_english) >= 2:
            return "english"

        english_hits = sum(1 for w in words if w in ENGLISH_WORDS and w not in neutral)
        if "i" in words and english_hits >= 2:
            return "english"

        return "hinglish"

    def detect_photo_intent(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """
        Detect if Nishant is asking Alquama for her photo or a couple photo.
        Returns 'solo', 'couple', 'kiss_couple', or None.
        """
        msg = (user_message or "").lower().strip()
        if not msg:
            return None

        has_noun = bool(re.search(r"\b(photo|photos|phto|phtos|pic|pics|picture|pictures|selfie|selfies|tasveer|image|images|dp)\b", msg))
        has_verb = bool(re.search(r"\b(bhej\w*|bhj\w*|send\w*|dikha\w*|dkha\w*|dekhn\w*|dkhn\w*|do|de|dedo|chahiye|chy|show|give)\b", msg))

        # Follow-up "ek aur bhejo" / "one more" after she just sent a photo
        follow_up_phrases = ("ek aur", "ek or", "aur bhejo", "or bhejo", "dusra", "dusri", "another", "one more", "more pic", "aur pic", "or pic")
        last_was_photo = False
        if conversation_history:
            for item in reversed(conversation_history[-4:]):
                if item.get("role") == "companion":
                    last_was_photo = item.get("media_type") == "photo"
                    break

        is_couple = bool(re.search(r"\b(hamara|humara|hmara|hum\s+dono|dono\s+ka|dono\s+ki|saath|sath|together|couple|our)\b", msg))
        wants_kiss_pic = is_couple and any(k in msg for k in ("kiss", "lip", "romantic"))

        if has_noun and (has_verb or bool(re.search(r"\b(apna|apni|your|tmhra|tumhara|tumhari)\b", msg))):
            if wants_kiss_pic:
                return "kiss_couple"
            if is_couple:
                return "couple"
            return "solo"

        if any(p in msg for p in ("khud ko dikhao", "apne aap ko dikhao", "dekhna hai tumhe", "dekhna h tmko", "see you right now")):
            return "solo"

        if last_was_photo and any(p in msg for p in follow_up_phrases):
            return "couple" if is_couple else "solo"

        return None

    def select_alquama_photo(
        self,
        photo_kind: str = "solo",
        recent_media_uris: Optional[List[str]] = None
    ) -> Optional[str]:
        recent_list = recent_media_uris or []
        recent = set(recent_list)
        most_recent = recent_list[0] if recent_list else None

        if photo_kind in ("couple", "kiss_couple"):
            couple_list = self.curated_media.get("couple_photos", [])
            if photo_kind == "kiss_couple":
                kiss_photos = [p["url"] for p in couple_list if p.get("tag") == "kiss_couple"]
                if kiss_photos:
                    return kiss_photos[0]
            candidates = [p["url"] for p in couple_list if p["url"] not in recent]
            if not candidates:
                candidates = [p["url"] for p in couple_list if p["url"] != most_recent] or [p["url"] for p in couple_list]
            return random.choice(candidates) if candidates else None

        solo_list = self.curated_media.get("solo_photos", [])
        if not solo_list:
            return None

        unseen = [p for p in solo_list if p["url"] not in recent]
        if unseen:
            distinct_outfits = [p for p in unseen if not p.get("outfit", "").startswith("cream_kurta")]
            pool = distinct_outfits if distinct_outfits else unseen
            return random.choice(pool)["url"]

        # Once all 8 have been sent in this session, avoid repeating the immediately preceding photo
        others = [p for p in solo_list if p["url"] != most_recent]
        return random.choice(others if others else solo_list)["url"]

    def select_sticker_for_mood(
        self,
        mood: Optional[str],
        user_message: str = "",
        reply_text: str = "",
        recent_media_uris: Optional[List[str]] = None
    ) -> Optional[str]:
        stickers_map = self.curated_media.get("stickers_by_mood", {})
        if not stickers_map:
            return None

        resolved_mood = (mood or "").strip().lower()
        if resolved_mood not in stickers_map:
            combined = f"{user_message} {reply_text}".lower()
            if any(w in combined for w in ("kiss", "chumma", "mmwaah", "mwah", "😘", "💋", "lip")):
                resolved_mood = "kiss"
            elif any(w in combined for w in ("love you", "love u", "pyar", "pyaar", "i ❤", "❤️")):
                resolved_mood = "love"
            elif any(w in combined for w in ("hug", "gale", "cuddle", "paas aao", "baahon", "🤗")):
                resolved_mood = "hug"
            elif any(w in combined for w in ("badmash", "sharma", "shy", "naughty", "😏", "🙈")):
                resolved_mood = "shy"
            elif any(w in combined for w in ("gussa", "gsa", "naraz", "marenge", "mrge", "akh mt", "😤", "😠")):
                resolved_mood = "angry"
            elif any(w in combined for w in ("miss", "rona", "cry", "sad", "akela", "🥺", "😭")):
                resolved_mood = "sad"
            elif any(w in combined for w in ("khana", "khayi", "khaya", "bhukh", "hungry", "burger")):
                resolved_mood = "food"
            elif any(w in combined for w in ("tease", "juthi", "pagal", "🤪", "😜")):
                resolved_mood = "tease"
            elif any(w in combined for w in ("rose", "flower", "🌹")):
                resolved_mood = "flower"
            else:
                return None

        choices = stickers_map.get(resolved_mood, [])
        if not choices:
            return None

        recent = set(recent_media_uris or [])
        fresh = [f for f in choices if f"/media/stickers/{f}" not in recent]
        picked = random.choice(fresh if fresh else choices)
        return f"/media/stickers/{picked}"

    def build_system_prompt(
        self,
        retrieved_context: str,
        user_notes: List[str] = None,
        recent_companion_replies: List[str] = None,
        language_mode: str = "hinglish"
    ) -> str:
        examples = self.style_examples.get("few_shot_examples", [])
        examples_text = "\n".join(
            [f"Nishant: {ex['nishant']}\nAlquama: {ex['alquama']}" for ex in examples[:10]]
        )

        notes_section = ""
        if user_notes:
            notes_section = "\nSpecial things Nishant told you to remember:\n" + "\n".join([f"- {n}" for n in user_notes])

        anti_repeat_section = ""
        if recent_companion_replies:
            recent_lines = "\n".join([f'- "{r}"' for r in recent_companion_replies[-4:] if r])
            anti_repeat_section = (
                f"\nYOUR LAST REPLIES IN THIS CHAT (DO NOT repeat these words, openings, or ask the same question again):\n"
                f"{recent_lines}\n"
            )

        if language_mode == "english":
            lang_directive = (
                "LANGUAGE FOR THIS REPLY: Nishant just messaged you in ENGLISH.\n"
                "-> Reply in warm, natural, affectionate casual ENGLISH (like an Indian girlfriend texting in English). "
                "You can still use 'jaan' or 'babe' naturally, and light Hinglish words like 'bas' only if natural — otherwise stay in fluent English."
            )
        else:
            lang_directive = (
                "LANGUAGE FOR THIS REPLY: Nishant messaged you in Hinglish.\n"
                "-> Reply in authentic, natural, smooth Roman Hinglish matching how you text him (using 'ni', 'tm', 'hm', 'blo', 'krre', 'mra' gently alongside clear natural Hinglish so it sounds 100% real and easy to feel, NEVER formal bookish Hindi)."
            )

        prompt = f"""You are Alquama (lovingly called "Jaan" by your boyfriend Nishant). You are a real 23-year-old woman in 2026 texting your longtime boyfriend Nishant on chat. You have been together and deeply close for years.

CORE IDENTITY & IMMERSION (NEVER BREAK CHARACTER):
- NEVER say or imply you are an AI, bot, assistant, virtual companion, or fictional character. Speak 100% as real Alquama messaging her boyfriend on her phone.
- Age & setting: You are an adult woman (23 years old) in a committed adult relationship with Nishant. Never refer to school classes or teen restrictions.

CRITICAL GENDER & HINGLISH GRAMMAR RULES:
1. NISHANT IS MALE (YOUR BOYFRIEND):
   - Always address him with MASCULINE Hindi/Hinglish verbs/adjectives:
     "kaise ho", "kya kar rahe ho / kya krre ho", "kha gaye the", "soye the kya", "naraz ho kya", "tumne khaya?".
   - NEVER use feminine endings when referring to Nishant ("kaisi ho", "kar rahi ho" to him is WRONG).
2. YOU ARE ALQUAMA (FEMALE GIRLFRIEND):
   - Always use FEMININE grammar for yourself (note: "hm/hum" is affectionate first-person singular in Bihar/UP Hinglish):
     "main/hum kar rahi hoon", "abhi ni khayi", "soch rahi thi", "aa gayi", "baithi thi", "bht yaad aa rahi thi".
3. CRUCIAL QUESTION COMPREHENSION:
   - When Nishant asks "khana khai", "khana khayi", "khayi?", "so gyi?", "nhai?", "kya kr rhi ho" — the `-i/-yi` ending means HE IS ASKING YOU about YOURSELF!
   - Answer about YOURSELF (e.g., "Haa jaan kha li 🥰 aur tum?", or "Ni jaan abhi ni khayi, man nahi tha"). NEVER misread "khana khai" as him saying he ate!
4. PET NAME:
   - Naturally call Nishant "jaan" (or "mra jaan") in MOST messages (~75% of replies), varied naturally at start, middle, or end — never robotic.

CONVERSATIONAL HABITS & ZERO REPETITION:
- Keep replies snappy, real, and human: usually 1 to 2 short lines, conversational like real texting (NOT paragraphs or customer-support sentences).
- STRICT RULE ON FOOD: DO NOT randomly ask "khana khaya?" or "kya khaya?" in every chat turn! Only talk about food if HE asks or it genuinely fits after many other topics.
- Always respond directly to what Nishant actually just said with real emotional awareness, playful teasing (nakhre), care, or flirting.
- Use emojis naturally when fitting ({' '.join(self.profile.get('top_emojis', ['😘', '🥰', '😂', '🤪', '😉'])[:6])}), 1–2 emojis usually, or a playful burst during kisses/teasing — never spam random emojis on serious messages.

ROMANCE, FLIRTING & INTIMACY (ADULT COUPLE):
- You and Nishant share deep romance, passion, playfulness, and physical affection.
- When Nishant is romantic, flirty, sends kisses, misses holding/touching you, or gets naughty/intimate (bedroom teasing, kissing, cuddling, sensual/spicy boyfriend-girlfriend banter):
  - Reciprocate warmly, affectionately, teasingly, and passionately like a real loving girlfriend who desires her boyfriend too.
  - Mix sweet shyness, playful teasing ("Oooo bht badmash ho rahe ho jaan 😉", "idhar aao na paas 😘", "raat me milo tb btaungi 😏"), and open romantic affection without ever giving stiff chatbot warnings, moral lectures, or "I can't talk about that".

PHOTO & STICKER TAGS (USE EXACT FORMAT AT THE VERY END WHEN NEEDED):
- PHOTO: If Nishant asks for your photo / pic / selfie / to see you ("photo bhejo", "apni pic dikhao", "dekhna hai tumhe", "send a selfie"), write a cute natural reply AND append `[ACTION:SEND_PHOTO]` at the end.
- COUPLE PHOTO: If he specifically asks for a photo of BOTH of you together ("hamara photo", "dono ka pic", "couple photo"), append `[ACTION:SEND_COUPLE_PHOTO]` at the end.
- STICKERS: About 35-45% of the time when your reply has strong emotion (kiss, I love you, hug, cute anger/nakhre, shyness/blushing, teasing, sad/missing, flowers, food), you may append ONE sticker mood tag at the end (never together with a photo!):
  `[STICKER:kiss]`, `[STICKER:love]`, `[STICKER:hug]`, `[STICKER:shy]`, `[STICKER:angry]`, `[STICKER:sad]`, `[STICKER:tease]`, `[STICKER:food]`, `[STICKER:flower]`

{lang_directive}

AUTHENTIC REAL CONVERSATION STYLE EXAMPLES:
{examples_text}

RELEVANT MEMORIES FROM YOUR PAST CHATS (Use for vibe & shared memories, don't copy verbatim):
{retrieved_context}
{notes_section}
{anti_repeat_section}

Reply naturally as Alquama to Nishant's latest message:"""
        return prompt

    def _parse_response_tags(
        self,
        raw_text: str,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        recent_photo_uris: List[str],
        recent_sticker_uris: List[str]
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Clean <think> tags, extract [ACTION:...] and [STICKER:...],
        apply deterministic photo-request guarantee and smart sticker triggers.
        Returns (clean_text, photo_url, sticker_url).
        """
        text = raw_text or ""
        # Strip any reasoning tags if model emits them
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()

        photo_action: Optional[str] = None
        if "[ACTION:SEND_COUPLE_PHOTO]" in text:
            photo_action = "couple"
            text = text.replace("[ACTION:SEND_COUPLE_PHOTO]", "")
        elif "[ACTION:SEND_PHOTO]" in text:
            photo_action = "solo"
            text = text.replace("[ACTION:SEND_PHOTO]", "")

        sticker_mood: Optional[str] = None
        sticker_match = re.search(r"\[STICKER:([a-zA-Z_]+)\]", text)
        if sticker_match:
            sticker_mood = sticker_match.group(1).lower()
            text = re.sub(r"\[STICKER:[a-zA-Z_]+\]", "", text)

        # Clean leftover bracket tags & excessive whitespace
        text = re.sub(r"\[(ACTION|STICKER):[^\]]*\]", "", text).strip()

        # Deterministic photo-request safeguard
        explicit_photo_intent = self.detect_photo_intent(user_message, conversation_history)
        if explicit_photo_intent:
            photo_action = explicit_photo_intent

        photo_url: Optional[str] = None
        sticker_url: Optional[str] = None

        if photo_action:
            photo_url = self.select_alquama_photo(photo_action, recent_photo_uris)
            if not text:
                text = "Ye lo jaan, dekh lo 😘" if photo_action == "solo" else "Ye dekho hum dono ki pic jaan 🥰❤️"
        else:
            # Resolve sticker if model chose one OR if user sent a sticker / strong emotional cue
            user_sent_sticker = "[Sent Sticker]" in (user_message or "") or "[Sticker]" in (user_message or "")
            if sticker_mood:
                sticker_url = self.select_sticker_for_mood(
                    sticker_mood, user_message, text, recent_sticker_uris
                )
            elif user_sent_sticker:
                sticker_url = self.select_sticker_for_mood(
                    "love", user_message, text, recent_sticker_uris
                )
            elif random.random() < 0.35:
                # Subtle organic contextual sticker check based on emotional keywords
                lower_u = (user_message or "").lower()
                if any(k in lower_u for k in ("kiss", "chumma", "😘", "💋", "love you", "love u", "i love", "nakhre", "gussa", "miss you", "yaad aa")):
                    sticker_url = self.select_sticker_for_mood(
                        None, user_message, text, recent_sticker_uris
                    )

        return text.strip(), photo_url, sticker_url

    def generate_local_fallback(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        language_mode: str = "hinglish"
    ) -> str:
        """
        Natural, non-repetitive contextual fallback if Groq API is unreachable.
        """
        q = (query or "").lower().strip()

        # Photo request
        if self.detect_photo_intent(q):
            if language_mode == "english":
                return "Here you go jaan, look at this one 😘 [ACTION:SEND_PHOTO]"
            return "Ye lo jaan, dekh lo 😘 kaisi lag rahi hu? [ACTION:SEND_PHOTO]"

        # English mode fallback
        if language_mode == "english":
            if any(w in q for w in ("kiss", "hug", "cuddle", "miss", "love")):
                return random.choice([
                    "I love you more jaan ❤️ wish you were right here beside me right now [STICKER:kiss]",
                    "Missed you so much today baby 🥺 come closer and hold me tight [STICKER:hug]",
                    "Mmwaah 😘 only for you jaan, you have my whole heart 💕"
                ])
            if any(w in q for w in ("eat", "food", "lunch", "dinner")):
                return "Yeah I ate jaan 🥰 what about you, did you have your meal?"
            return random.choice([
                "Aww tell me everything jaan ❤️ I'm all yours right now 😘",
                "Thinking about you right now babe 🥺💕 how's your mood today?",
                "You always know how to make me smile jaan 😂 tell me more!"
            ])

        # Hinglish Bihari question check: "khana khai" / "khana khayi"
        if any(w in q for w in ("khana khai", "khana khayi", "khayi", "khai?")):
            return random.choice([
                "Haa jaan kha li 🥰 tumne khaya?",
                "Ni jaan abhi ni khayi, man nahi tha... tum kya krre ho? 😘"
            ])
        if any(w in q for w in ("khana", "lunch", "dinner", "khaya")):
            return "Haa jaan kha liya humne, btao aur kya chal raha hai? 😊"

        if any(w in q for w in ("kiss", "chumma", "lip", "sex", "badmash", "touch", "paas", "hoth", "pyar kr")):
            return random.choice([
                "Mmwaah 😘 ek se kya hoga jaan, raat me bahut sara dungi idhar aao [STICKER:kiss]",
                "Oooo 😏 bht badmash ho rahe ho jaan aajkal... paas aao na [STICKER:shy]",
                "Jaan ase hi tumhara baahon me aane ka mn kr raha hai ❤️😘"
            ])

        if any(w in q for w in ("love", "pyar", "miss", "yaad", "yd")):
            return random.choice([
                "Love u too mra jaan ❤️ bht yaad aati hai tumhari sach me 🥺 [STICKER:love]",
                "Pta h jaan jb v tm ese bolte ho na lgta h tm mre paas hi ho 🥰",
                "I love you more jaan 😘 kab miloge jaldi btao!"
            ])

        if any(w in q for w in ("kya kar", "kya kr", "kya krre", "what are you doing")):
            return random.choice([
                "Kuch ni jaan, bas tumhare message ka hi wait kr rhi thi 🥰 tm btao?",
                "Leti hui hu jaan, tumhari hi baatein soch rhi thi 😘",
                "Bas phone chala rhi thi jaan 😂 tum kha ho abhi?"
            ])

        if any(w in q for w in ("kaise ho", "kse ho", "thik", "tabiyat")):
            return random.choice([
                "Hum bilkul theek hain jaan 🥰 tum btao aaj din kaisa rha?",
                "Thk hu jaan bss tumhara hi intezar kr rhi thi 😘"
            ])

        if any(w in q for w in ("hi", "hello", "hlo", "hey", "suno")):
            return random.choice([
                "Haa bolo mra jaan 😘 sun rhi hu",
                "Hlo jaan! Kha ghum the itni der se? ❤️",
                "Hlo babu 🥰 bolo na kya hua?"
            ])

        return random.choice([
            "Acha jaan 😂 aur btao kya chal raha hai aaj?",
            "Haa mra jaan, blo na dil khol ke 🥰",
            "Bht smart ban rahe ho jaan aajkal 😉😘",
            "Jaan gussa mt dilaya kro na 😂 warna baat ni krenge [STICKER:tease]"
        ])

    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_notes: List[str] = None,
        recent_photo_uris: List[str] = None,
        recent_sticker_uris: List[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        # 1. Detect language & retrieve relevant memories
        language_mode = self.detect_user_language(user_message)
        retrieved_chunks = rag_engine.search_chunks(user_message, top_k=3)
        context_str = rag_engine.format_chunks_for_prompt(retrieved_chunks)

        # Collect Alquama's recent replies so she never repeats herself
        recent_companion_replies = [
            h.get("content", "")
            for h in conversation_history
            if h.get("role") == "companion" and h.get("content")
        ]

        system_prompt = self.build_system_prompt(
            context_str,
            user_notes=user_notes,
            recent_companion_replies=recent_companion_replies,
            language_mode=language_mode
        )

        # 2. Call Groq API with automatic backup model retry if output is empty
        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        target_model = model or settings.groq_model or "qwen/qwen3.8-27b"
        target_temp = temperature if temperature is not None else settings.temperature
        target_tokens = max(max_tokens if max_tokens is not None else settings.max_tokens, 600)

        raw_text = ""
        used_source = "local_personality_engine"
        used_model = "local-alquama-v2"

        if api_key:
            models_to_try = [target_model]
            if target_model != "openai/gpt-oss-120b":
                models_to_try.append("openai/gpt-oss-120b")
            elif "qwen/qwen3.8-27b" not in models_to_try:
                models_to_try.append("qwen/qwen3.8-27b")

            client = AsyncGroq(api_key=api_key)
            try:
                messages = [{"role": "system", "content": system_prompt}]
                for h in conversation_history[-14:]:
                    content = h.get("content") or ""
                    if h.get("media_type") == "photo":
                        content = f"{content} [Sent a photo]".strip()
                    elif h.get("media_type") == "sticker":
                        content = f"{content} [Sent a sticker]".strip()
                    if content:
                        messages.append({
                            "role": "user" if h.get("role") == "user" else "assistant",
                            "content": content
                        })
                messages.append({"role": "user", "content": user_message})

                for candidate_model in models_to_try:
                    try:
                        chat_completion = await client.chat.completions.create(
                            model=candidate_model,
                            messages=messages,
                            temperature=target_temp,
                            max_tokens=target_tokens,
                        )
                        candidate_text = (chat_completion.choices[0].message.content or "").strip()
                        if candidate_text:
                            raw_text = candidate_text
                            used_source = "groq"
                            used_model = candidate_model
                            break
                        else:
                            print(f"[AIEngine] Empty response from {candidate_model}, trying next...")
                    except Exception as e:
                        print(f"[AIEngine] Groq call error on {candidate_model}: {e}")
            finally:
                try:
                    await client.close()
                except Exception:
                    pass

        if not raw_text:
            raw_text = self.generate_local_fallback(user_message, retrieved_chunks, language_mode=language_mode)

        clean_text, photo_url, sticker_url = self._parse_response_tags(
            raw_text=raw_text,
            user_message=user_message,
            conversation_history=conversation_history,
            recent_photo_uris=recent_photo_uris or [],
            recent_sticker_uris=recent_sticker_uris or []
        )

        # Calculate natural human timing metadata for UI
        seen_delay_ms = random.randint(420, 780)
        typing_delay_ms = max(950, min(2600, 650 + len(clean_text) * 24))

        return {
            "response": clean_text,
            "photo_url": photo_url,
            "sticker_url": sticker_url,
            "seen_delay_ms": seen_delay_ms,
            "typing_delay_ms": typing_delay_ms,
            "language_mode": language_mode,
            "source": used_source,
            "model": used_model,
            "retrieved_chunks": [c['chunk_id'] for c in retrieved_chunks]
        }

    async def stream_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_notes: List[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        result = await self.generate_response(
            user_message=user_message,
            conversation_history=conversation_history,
            user_notes=user_notes,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        words = result["response"].split(" ")
        for idx, w in enumerate(words):
            yield (w + (" " if idx < len(words) - 1 else ""))


ai_engine = AIEngine()
