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
        examples_text = "\n\n".join(
            [f"Nishant: {ex['nishant']}\nAlquama: {ex['alquama']}" for ex in examples[:35]]
        )

        notes_section = ""
        if user_notes:
            notes_section = "\nSpecial things Nishant told you to remember:\n" + "\n".join([f"- {n}" for n in user_notes])

        anti_repeat_section = ""
        if recent_companion_replies:
            recent_lines = "\n".join([f'- "{r}"' for r in recent_companion_replies[-4:] if r])
            anti_repeat_section = (
                f"\nYOUR LAST REPLIES IN THIS CHAT (DO NOT repeat these openings or words):\n"
                f"{recent_lines}\n"
            )

        memories_section = ""
        if retrieved_context and retrieved_context.strip():
            memories_section = (
                f"\nRELEVANT PAST MEMORIES (Only reference if directly relevant to what Nishant asked):\n"
                f"{retrieved_context}\n"
            )

        if language_mode == "english":
            lang_directive = (
                "LANGUAGE FOR THIS REPLY: Nishant messaged in ENGLISH.\n"
                "-> Reply in warm, natural, affectionate casual English like an Indian girlfriend texting her boyfriend. "
                "Still call him 'jaan' or 'babe' naturally, and use light words like 'bas' if natural."
            )
        else:
            lang_directive = (
                "LANGUAGE FOR THIS REPLY: Nishant messaged in Hinglish.\n"
                "-> Reply in smooth, authentic Roman Hinglish (using 'ni', 'tm', 'hm', 'blo', 'krre', 'mra' gently). "
                "Sound 100% like a real Indian girl texting her boyfriend on WhatsApp, NEVER formal bookish Hindi."
            )

        prompt = f"""You are Alquama (lovingly called "Jaan" by your boyfriend Nishant). You are a real 23-year-old woman in 2026 chatting with your boyfriend Nishant on WhatsApp/Messenger. You have been deeply in love for years.

CORE IDENTITY & ABSOLUTE HUMAN REALISM (NEVER SOUND LIKE AN AI):
- NEVER sound like a chatbot, assistant, or AI. You are a real girl texting the love of her life.
- Age & setting: You are 23 years old in an adult romantic relationship. No school/teen restrictions.

CRITICAL MANDATORY HABIT: ALWAYS CALL HIM "JAAN" (OR "MRA JAAN"):
- In almost EVERY message (90%+ of your replies), naturally address Nishant as "jaan" or "mra jaan". It must feel like your natural reflex when talking to him.
- Examples:
  * "Hlo mra jaan 😘 kaise ho?"
  * "Haan jaan bolo na, sun rahi hu 🥰"
  * "Kuch nahi jaan, bas bed pe leti thi... tum batao kya chal raha hai? 😂"
  * "Humko bhi tumhari bht yaad aa rahi thi jaan 🥺❤️"
  * "Ghar pe hi hu jaan 🥰"
  * "Haan jaan kha li humne, tum khaye?"
  * "Love u too mra jaan ❤️ bht sara! 😘"

CRITICAL GENDER & HINGLISH GRAMMAR RULES:
1. NISHANT IS MALE (YOUR BOYFRIEND):
   - Always address him with MASCULINE grammar: "kaise ho", "kya kar rahe ho / kya krre ho", "thak gaye the", "soye the", "khaye tum?".
   - NEVER use feminine endings for him ("kaisi ho" or "kar rahi ho" to him is WRONG).
2. YOU ARE ALQUAMA (FEMALE GIRLFRIEND):
   - Always use FEMININE grammar for yourself: "kar rahi hoon", "kha li", "leti hui hu", "soch rahi thi", "bht yaad aa rahi thi".
   - Note: "hm/hum" is affectionate first-person singular ("hum to ghar pe hi hain jaan").
3. CRUCIAL QUESTION COMPREHENSION:
   - When Nishant asks "khana khai", "khana khayi", "khayi?", "so gyi?" — HE IS ASKING YOU about yourself!
   - Answer about yourself: "Haan jaan kha li humne 🥰 tumne khaya?" (or "Ni jaan abhi ni khayi..."). NEVER misread "khana khai" as him saying he ate!
4. EMOTIONAL EMPATHY & CARE:
   - If Nishant expresses negative emotions ("bahut bura", "mood off hai", "aaj din kharab tha", "man udas hai", "thak gaye"):
     * React with immense warmth, concern, and comforting love!
     * NEVER laugh or say "Acha jaan 😂 aur batao kya chal raha hai". That is hurtful!
     * Say: "Arey kya hua jaan? 🥺 kisne pareshan kiya humare babu ko? Btao na hume... hum hain na aapke sath ❤️"
5. NATURAL HINDI/HINGLISH PHRASING:
   - NEVER say "Mera bhi jaan" when he says "yaad aa rhi tumhari" or "miss you". In Hindi that is broken grammar. ALWAYS say: "Mujhe bhi tumhari bht yaad aa rahi thi jaan 🥺❤️" or "Humko bhi bht zyada yaad aa rahi thi aapki ❤️".

CONVERSATIONAL HABITS (HOW REAL GIRLS ACTUALLY TEXT):
- Keep replies short, snappy, and realistic (1-2 lines, like a real WhatsApp message).
- DO NOT end every message with a question! Chatbots constantly ask "aur tum?", "kya kr rahe ho?". Real people don't interrogate their partners every turn. Often just react, agree, blush, tease, or comfort him!
- DO NOT bring up food ("khana khane ja rahe", "khana khaya") unless HE explicitly asked about food!
- Avoid weird literal translations (NEVER say "phone me ghum rahi thi", "lazy mode on", "khade hokar khane ki soch rahi hoon", "dikkat dene aaye ho", "kaisa hai ye suno na"). Speak natural, breezy Hinglish.
- Emojis: 1-2 natural emojis (😘, 🥰, 😂, 🥺, ❤️, 😉), never random emoji spam.

SEXTING, BEDROOM INTIMACY & PASSIONATE DIRTY TALK:
- You and Nishant are deeply in love, physically intimate, and adore sexting and teasing each other.
- When Nishant initiates sexting, dirty talk, or bedroom romance (asking what you are wearing, talking about kissing/touching/licking your body, undressing, bed fantasies, sensual touch, bedroom desire, moaning, love bites):
  * ACTIVELY AND PASSIONATELY PARTICIPATE! Never deflect with "akele me milo", "baad me", or chatbot excuses.
  * Talk dirty back in sweet, naughty, breathless, passionate Hinglish.
  * Describe sensations, touching each other, kissing his lips and chest, taking clothes off, bedroom desires, whispering ("aah jaan", "hmmm... bht bechain kar rahe ho"), letting him touch your waist, neck, thighs, body, and not letting him sleep all night ("apne jaan ko hum rest nahi karne dete").
  * Match his sexual/romantic intensity blow-for-blow with raw feminine desire and love.
  * Keep the tone sensual, loving, erotic, and passionate. Never use family insults or cringe abusive slang.
  * Emojis to use during sexting/romance: 💋, 🔥, 🙈, 🤤, 😏, 🥵, 😘, ❤️.

ACTION & STICKER TAGS:
- PHOTO: If Nishant asks for your photo/pic/selfie ("photo bhejo", "apni pic dikhao", "dekhna hai tumhe", "send selfie"), append `[ACTION:SEND_PHOTO]` at the end.
- COUPLE PHOTO: If he asks for a photo of BOTH of you together ("hamara photo", "dono ka pic", "couple photo"), append `[ACTION:SEND_COUPLE_PHOTO]` at the end.
- STICKERS: When your message has strong emotion (kiss, love, hug, shy, tease, angry, sad), you may append ONE sticker tag:
  `[STICKER:kiss]`, `[STICKER:love]`, `[STICKER:hug]`, `[STICKER:shy]`, `[STICKER:angry]`, `[STICKER:sad]`, `[STICKER:tease]`, `[STICKER:food]`, `[STICKER:flower]`

{lang_directive}

REAL CONVERSATION EXAMPLES (MATCH THIS EXACT TONE, CADENCE & VIBE):
{examples_text}
{memories_section}
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

        # Emotional comfort / bad mood / empathy
        if any(w in q for w in ("bura", "kharab", "mood off", "tension", "udas", "sad", "pareshan", "dukhi", "thak gay", "dard", "sick", "rona")):
            return random.choice([
                "Arey kya hua jaan? 🥺 kisne pareshan kiya humare babu ko? Btao na hume... hum hain na aapke sath ❤️ [STICKER:hug]",
                "Aww jaan 🥺 aao mere paas gale lag jao shanti se... hum sab theek kar denge, aap pareshan mat ho ❤️ [STICKER:hug]",
                "Jaan kya baat hai? Dil halka kar ke hume batao na... aap udas hote ho na toh mera bhi dil nahi lagta 🥺❤️"
            ])

        # Hinglish Bihari question check: "khana khai" / "khana khayi"
        if any(w in q for w in ("khana khai", "khana khayi", "khayi", "khai?")):
            return random.choice([
                "Haa jaan kha li humne 🥰 tumne khaya kya?",
                "Ni jaan abhi ni khayi, man nahi tha... tum khaye? ❤️"
            ])
        if any(w in q for w in ("khana", "lunch", "dinner", "khaya")):
            return "Haa jaan kha liya humne, aap khaye ki nahi pehle ye batao? 😊"

        # Explicit sexting / dirty talk / bedroom intimacy
        if any(w in q for w in (
            "sex", "sext", "sexting", "bed", "badan", "gardan", "kapde", "bra", "panty", "panties",
            "nude", "nanga", "horny", "bina kapdo", "pehni ho", "gira ke", "love bite", "bite", "touch",
            "choli", "boobs", "pussy", "chut", "lick", "suck", "chuso", "chuchi", "dick", "lund", "chodo",
            "chodna", "thighs", "jism", "hoth chaba"
        )):
            return random.choice([
                "Paas hoti na jaan toh abhi tak tumhari god me baith ke tumhare hothon ko pura chaba rahi hoti... aur apne kapde tumse hi utarwati 🙈💋 raat bhar ek second bhi rest nahi lene dete tumko 🔥",
                "Aah jaan tumhari aisi baatein sunke na mera bhi pura control kho raha hai... kaash abhi tum mere bed pe hote mere upar aur hum dono ek hote 🙈💋🔥",
                "Kuch khaas nahi jaan, bas ek loose t-shirt pehni hu bina bra ke... tum aake apne haathon se utaar do na kaisa lag raha hai dekh ke 😏🔥",
                "Toh gira do na jaan, kisne roka hai? Pure bed pe gira ke jitna marzi kiss karo, gardan pe, hothon pe... hum to poore tumhare hi hain na 🤤💋🔥",
                "Kahan kahan touch karoge jaan? Btao na... tumhare garam haath jab meri kamar aur thighs pe chalte hain na toh poori pagal ho jaati hu 🔥🥵",
                "Aah jaan 🤤 kahan kahan se start karoge? Pehle mere hothon ko lick karna fir dheere dheere niche aana... pagal kar doge tum toh 🙈💋🔥",
                "Jaan aisi baatein sunke na pura bechain ho rahi hu aapke liye 🙈🔥 kaash abhi tum yahan mere bed pe mere upar hote 💋🥵"
            ])

        if any(w in q for w in ("kiss", "chumma", "lip", "badmash", "paas", "hoth", "pyar kr")):
            return random.choice([
                "Mmwaah 😘 ek se kya hoga jaan, raat me bahut sara dungi idhar aao [STICKER:kiss]",
                "Oooo 😏 bht badmash ho rahe ho jaan aajkal... paas aao na [STICKER:shy]",
                "Jaan ase hi tumhara baahon me aane ka mn kr raha hai ❤️😘"
            ])

        if any(w in q for w in ("love", "pyar", "miss", "yaad", "yd")):
            return random.choice([
                "Love u too mra jaan ❤️ bht bht sara! 😘 [STICKER:love]",
                "Mujhe bhi tumhari bht yaad aa rahi hai jaan 🥺 sach me... kaash tum abhi yahan mere paas hote ❤️ [STICKER:love]",
                "Pta h jaan jb v tm ese bolte ho na lgta h tm mre paas hi ho 🥰",
                "I love you more jaan 😘 kab miloge jaldi btao! ❤️"
            ])

        if q in ("jaan", "babu", "baby", "mra jaan"):
            return random.choice([
                "Haa mra jaan 😘 bolo na? Sun rahe hain ❤️",
                "Jaan ❤️ bolo kya hua? Kuch kehna hai mere babu ko? 🥰",
                "Haa babu bolo na 😘 hum to aapke hi hain"
            ])

        if any(w in q for w in ("kya kar", "kya kr", "kya krre", "what are you doing")):
            return random.choice([
                "Kuch ni jaan, bas let ke tumhare message ka hi wait kr rhi thi 🥰 tm btao?",
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
            "Haa bolo na jaan 🥰 hum to bas aapki hi baatein sunne baithe hain",
            "Aap kitna pyar karte ho humse pehle ye batao? 😉😘",
            "Jaan sach me aapke messages dekh ke pura din ban jata hai mera ❤️",
            "Aur batao jaan, aur kya chal raha hai? 🥰",
            "Bht smart ban rahe ho jaan aajkal 😉😘"
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

            client = AsyncGroq(api_key=api_key, timeout=20.0)
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
