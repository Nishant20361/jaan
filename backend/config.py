import os
from pydantic import BaseModel

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORKSPACE_DIR, "data")
MESSAGES_DIR = os.path.join(WORKSPACE_DIR, "messages")
DB_PATH = os.path.join(WORKSPACE_DIR, "data", "jaan_app.db")

def load_env_file(filepath: str):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and not os.environ.get(key):
                        os.environ[key] = val

# Load from root .env and backend/.env
load_env_file(os.path.join(WORKSPACE_DIR, ".env"))
load_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

class Settings(BaseModel):
    app_name: str = "Jaan AI Backend"
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    temperature: float = 0.7
    max_tokens: int = 500
    host: str = "0.0.0.0"
    port: int = 8000

settings = Settings()
