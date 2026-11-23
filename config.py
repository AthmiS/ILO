import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-this-secret-key")
    DATABASE = os.environ.get("DATABASE_PATH", str(ROOT / "instance" / "ilo.db"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
