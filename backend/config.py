import os
from pydantic import BaseModel

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORKSPACE_DIR, "data")
MESSAGES_DIR = os.path.join(WORKSPACE_DIR, "messages")
DB_PATH = os.path.join(WORKSPACE_DIR, "data", "jaan_app.db")

class Settings(BaseModel):
    app_name: str = "Jaan AI Backend"
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    temperature: float = 0.7
    max_tokens: int = 500
    host: str = "0.0.0.0"
    port: int = 8000

settings = Settings()
