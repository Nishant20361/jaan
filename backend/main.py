import os
import json
import random
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from backend.config import WORKSPACE_DIR, DATA_DIR, MESSAGES_DIR, settings
from backend.rag_engine import rag_engine
from backend.ai_engine import ai_engine
from backend.memory_manager import memory_manager

app = FastAPI(
    title="Alquama Chat Backend",
    description="Personal romantic companion backend powered by Groq and Messenger conversation memory",
    version="2.0.0"
)

# Enable CORS for Mobile and Web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount media directories safely
photos_dir = os.path.join(MESSAGES_DIR, "e2ee_cutover", "nishantkumar_1105539713135073", "photos")
stickers_dir = os.path.join(MESSAGES_DIR, "stickers_used")
gifs_dir = os.path.join(MESSAGES_DIR, "e2ee_cutover", "nishantkumar_1105539713135073", "gifs")

if os.path.exists(photos_dir):
    app.mount("/media/photos", StaticFiles(directory=photos_dir), name="photos")
if os.path.exists(stickers_dir):
    app.mount("/media/stickers", StaticFiles(directory=stickers_dir), name="stickers")
if os.path.exists(gifs_dir):
    app.mount("/media/gifs", StaticFiles(directory=gifs_dir), name="gifs")
if os.path.exists(MESSAGES_DIR):
    app.mount("/media/all", StaticFiles(directory=MESSAGES_DIR), name="messages_all")

# Mount mobile assets for web UI
mobile_assets_dir = os.path.join(WORKSPACE_DIR, "mobile", "assets")
if os.path.exists(mobile_assets_dir):
    app.mount("/mobile/assets", StaticFiles(directory=mobile_assets_dir), name="mobile_assets")

static_dir = os.path.join(WORKSPACE_DIR, "backend", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def get_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Alquama Chat Running"}


# Request Models
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    media_uri: Optional[str] = None
    media_type: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False


class MemoryNoteCreate(BaseModel):
    title: str
    content: str
    tag: str = "general"


class SettingsUpdate(BaseModel):
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


# Health & Status Endpoint
@app.get("/api/health")
def get_health():
    api_key_configured = bool(settings.groq_api_key or os.getenv("GROQ_API_KEY"))
    return {
        "status": "online",
        "app_name": "Alquama ❤️",
        "groq_configured": api_key_configured,
        "default_model": settings.groq_model,
        "total_historical_messages": len(rag_engine.messages),
        "total_conversation_chunks": len(rag_engine.chunks),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/chat/greeting")
def get_greeting():
    greetings = ai_engine.style_examples.get("greetings") or [
        "Hlo jaan 😘 kya haal hai aaj?",
        "Hlo mra jaan 🥰 kha busy the itni der se?",
        "Aa gye online jaan ❤️ kya chal raha hai?"
    ]
    avatar_photo = ai_engine.curated_media.get("avatar_photo", "2680598922269266.jpg")
    return {
        "greeting": random.choice(greetings),
        "avatar_url": f"/media/photos/{avatar_photo}",
        "name": "Alquama ❤️"
    }


# Chat Completion Endpoint
@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not request.message.strip() and not request.media_uri:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_text = request.message.strip() or "[Sent Sticker]"

    # 1. Fetch prior conversation history BEFORE saving current user message (prevents duplicate turn in prompt)
    history = memory_manager.get_chat_history(session_id=request.session_id, limit=14)
    recent_photos = memory_manager.get_recent_media_uris(session_id=request.session_id, media_type="photo", limit=10)
    recent_stickers = memory_manager.get_recent_media_uris(session_id=request.session_id, media_type="sticker", limit=8)

    # 2. Save user message to chat history
    memory_manager.save_chat_message(
        session_id=request.session_id,
        role="user",
        content=user_text,
        media_uri=request.media_uri,
        media_type=request.media_type
    )

    # 3. Fetch user custom notes if any
    user_memories = memory_manager.get_memories()
    user_notes = [f"{m['title']}: {m['content']}" for m in user_memories]

    # 4. Generate natural response + optional photo or sticker
    result = await ai_engine.generate_response(
        user_message=user_text,
        conversation_history=history,
        user_notes=user_notes,
        recent_photo_uris=recent_photos,
        recent_sticker_uris=recent_stickers,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )

    # 5. Save companion response (text + photo/sticker if attached)
    comp_media_uri = result.get("photo_url") or result.get("sticker_url")
    comp_media_type = "photo" if result.get("photo_url") else ("sticker" if result.get("sticker_url") else None)
    memory_manager.save_chat_message(
        session_id=request.session_id,
        role="companion",
        content=result["response"],
        media_uri=comp_media_uri,
        media_type=comp_media_type
    )

    return {
        "response": result["response"],
        "photo_url": result.get("photo_url"),
        "sticker_url": result.get("sticker_url"),
        "seen_delay_ms": result.get("seen_delay_ms", 550),
        "typing_delay_ms": result.get("typing_delay_ms", 1200),
        "source": result["source"],
        "model": result["model"],
        "retrieved_chunks": result["retrieved_chunks"],
        "timestamp": datetime.utcnow().isoformat()
    }


# Streaming Chat Endpoint
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    history = memory_manager.get_chat_history(session_id=request.session_id, limit=14)
    memory_manager.save_chat_message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    user_memories = memory_manager.get_memories()
    user_notes = [f"{m['title']}: {m['content']}" for m in user_memories]

    async def event_generator():
        collected_response = []
        async for chunk in ai_engine.stream_response(
            user_message=request.message,
            conversation_history=history,
            user_notes=user_notes,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        ):
            collected_response.append(chunk)
            data_payload = json.dumps({"delta": chunk})
            yield f"data: {data_payload}\n\n"

        full_text = "".join(collected_response)
        memory_manager.save_chat_message(
            session_id=request.session_id,
            role="companion",
            content=full_text
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Memories & Stats Endpoints (kept for backend diagnostics/continuity)
@app.get("/api/memories/chunks")
def get_chunks(page: int = 1, page_size: int = 15, query: Optional[str] = None):
    if query:
        chunks = rag_engine.search_chunks(query, top_k=page_size)
        total = len(chunks)
        paged_chunks = chunks
    else:
        total = len(rag_engine.chunks)
        start = (page - 1) * page_size
        end = start + page_size
        paged_chunks = rag_engine.chunks[start:end]

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "chunks": paged_chunks
    }


@app.get("/api/memories/search")
def search_messages(q: str = Query("", description="Search term"), limit: int = 50):
    results = rag_engine.search_messages(q, limit=limit)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }


@app.get("/api/memories/stats")
def get_memory_stats():
    profile_path = os.path.join(DATA_DIR, "personality_profile.json")
    media_path = os.path.join(DATA_DIR, "media_catalog.json")
    profile = {}
    media = {}
    if os.path.exists(profile_path):
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
    if os.path.exists(media_path):
        with open(media_path, 'r', encoding='utf-8') as f:
            media = json.load(f)

    return {
        "total_messages": len(rag_engine.messages),
        "total_chunks": len(rag_engine.chunks),
        "companion_name": profile.get("companion_name", "Alquama"),
        "date_range": profile.get("date_range", {}),
        "top_emojis": profile.get("top_emojis", []),
        "key_phrases": profile.get("key_phrases", []),
        "total_photos": len(ai_engine.curated_media.get("solo_photos", [])),
        "total_stickers": media.get("total_stickers", 0),
        "total_gifs": media.get("total_gifs", 0)
    }


# Verified Clean Alquama Photos Endpoint
@app.get("/api/media/photos")
def get_photos():
    solo = ai_engine.curated_media.get("solo_photos", [])
    return [
        {
            "uri": f"messages/e2ee_cutover/nishantkumar_1105539713135073/photos/{p['filename']}",
            "url": p["url"],
            "filename": p["filename"],
            "description": p.get("description", "")
        }
        for p in solo
    ]


@app.get("/api/media/stickers")
def get_stickers():
    media_path = os.path.join(DATA_DIR, "media_catalog.json")
    if os.path.exists(media_path):
        with open(media_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stickers = []
            for s in data.get("stickers", []):
                filename = os.path.basename(s["uri"])
                stickers.append({
                    "uri": s["uri"],
                    "url": f"/media/stickers/{filename}",
                    "filename": filename
                })
            return stickers
    return []


@app.get("/api/media/gifs")
def get_gifs():
    media_path = os.path.join(DATA_DIR, "media_catalog.json")
    if os.path.exists(media_path):
        with open(media_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            gifs = []
            for g in data.get("gifs", []):
                filename = os.path.basename(g["uri"])
                gifs.append({
                    "uri": g["uri"],
                    "url": f"/media/gifs/{filename}",
                    "filename": filename
                })
            return gifs
    return []


# User-Defined Memories / Notes
@app.get("/api/memories/notes")
def get_notes():
    return memory_manager.get_memories()


@app.post("/api/memories/notes")
def add_note(note: MemoryNoteCreate):
    created = memory_manager.add_memory(
        title=note.title,
        content=note.content,
        tag=note.tag
    )
    return created


@app.delete("/api/memories/notes/{note_id}")
def delete_note(note_id: int):
    success = memory_manager.delete_memory(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory note not found")
    return {"success": True}


# Active Chat History CRUD
@app.get("/api/chat/history")
def get_chat_history(session_id: str = "default", limit: int = 100):
    return memory_manager.get_chat_history(session_id=session_id, limit=limit)


@app.delete("/api/chat/history")
def clear_chat_history(session_id: str = "default"):
    deleted = memory_manager.clear_chat_history(session_id=session_id)
    return {"success": True, "deleted_count": deleted}


# App Settings CRUD
@app.get("/api/settings")
def get_settings():
    return {
        "groq_configured": bool(settings.groq_api_key or os.getenv("GROQ_API_KEY")),
        "groq_model": settings.groq_model,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "available_models": [
            {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B (Natural Hinglish & Expressive)"},
            {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B (Deep Nuance & English/Hinglish)"},
            {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B (Ultra Fast)"}
        ]
    }


@app.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    if payload.groq_api_key is not None:
        settings.groq_api_key = payload.groq_api_key
        os.environ["GROQ_API_KEY"] = payload.groq_api_key
        ai_engine._init_groq()
    if payload.groq_model is not None:
        settings.groq_model = payload.groq_model
    if payload.temperature is not None:
        settings.temperature = payload.temperature
    if payload.max_tokens is not None:
        settings.max_tokens = payload.max_tokens
    return {"success": True, "settings": get_settings()}
