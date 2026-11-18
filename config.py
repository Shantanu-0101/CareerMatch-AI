"""Application configuration. All secrets come from environment variables (.env)."""
import os
import secrets

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _secret_key():
    key = os.environ.get("SECRET_KEY", "").strip()
    if not key:
        # Random key per run: safe, but users are logged out when the server restarts.
        print("[config] SECRET_KEY not set in .env - using a temporary random key.")
        key = secrets.token_hex(32)
    return key


class Config:
    SECRET_KEY = _secret_key()

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "career_match.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads are stored outside /static so they are never publicly reachable.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 5)) * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf", "docx"}

    # AI settings. Provider "gemini" (default) or "openai" (any OpenAI-compatible API).
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").strip().lower()
    AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
    AI_MODEL = os.environ.get("AI_MODEL", "").strip()
    AI_BASE_URL = os.environ.get("AI_BASE_URL", "").strip()
    AI_TIMEOUT = int(os.environ.get("AI_TIMEOUT", 40))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    AI_API_KEY = ""
