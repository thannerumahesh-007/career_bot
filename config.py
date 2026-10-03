import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file with override to ensure project .env takes precedence
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

def normalize_database_uri(uri: str) -> str:
    """
    Normalizes database URIs for cloud deployment compatibility.
    Ensures PostgreSQL connections use the installed psycopg2-binary driver
    (e.g., converts postgres://, postgresql://, or postgresql+psycopg:// to postgresql+psycopg2://)
    while preserving sqlite:// and other explicit dialect drivers.
    """
    if not uri:
        return uri
    if uri.startswith("postgres://"):
        return uri.replace("postgres://", "postgresql+psycopg2://", 1)
    if uri.startswith("postgresql+psycopg://"):
        return uri.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    if uri.startswith("postgresql://"):
        return uri.replace("postgresql://", "postgresql+psycopg2://", 1)
    return uri


class Config:
    """Application Configuration Settings for CareerBot."""
    DEBUG = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true")
    
    # Secret Key strictly from environment variable in production
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV") == "production" or os.environ.get("RENDER") == "true":
            raise RuntimeError(
                "CRITICAL DEPLOYMENT ERROR: SECRET_KEY environment variable is not set! "
                "You must configure SECRET_KEY in Render's Environment Variables dashboard."
            )
        SECRET_KEY = "careerbot_dev_secret_key_change_in_production"

    # Database configuration with automatic PostgreSQL normalization for cloud providers (e.g. Render)
    _raw_db_uri = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI") or f"sqlite:///{BASE_DIR / 'careerbot.db'}"
    SQLALCHEMY_DATABASE_URI = normalize_database_uri(_raw_db_uri)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session & Cookie Security Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (os.environ.get("FLASK_ENV") == "production" or os.environ.get("RENDER") == "true")
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # Upload settings
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    
    # Matching Engine Component Weights
    WEIGHT_SKILL = 0.50
    WEIGHT_SEMANTIC = 0.25
    WEIGHT_INTEREST = 0.15
    WEIGHT_EXPERIENCE = 0.10
    
    # Match Recommendation Bands / Thresholds
    STRONG_MATCH_THRESHOLD = 0.75
    MODERATE_MATCH_THRESHOLD = 0.50
    
    # Gemini API Key (strictly from environment variable, never hard-coded)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()

    # Synchronize environment variables for SDK consistency
    if GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
        os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

    # ElevenLabs Voice AI Configuration
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()

    # News API Configuration
    NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "").strip()
    NEWS_CACHE_TTL = 300  # 5 minutes in-memory cache

    # Live Job Search API Configuration
    JOB_SEARCH_API_KEY = os.environ.get("JOB_SEARCH_API_KEY", "").strip()
    ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "").strip()
    ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "").strip()
    LIVE_JOB_CACHE_TTL = 600  # 10 minutes cache

    # Job Dataset Path
    JOBS_DATASET_PATH = BASE_DIR / "data" / "jobs.csv"

    # Gemini Model Router Configuration
    GEMINI_PRIMARY_MODEL = os.environ.get("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash").strip()
    GEMINI_FAST_MODEL = os.environ.get("GEMINI_FAST_MODEL", "gemini-3.5-flash").strip()
    GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-flash-latest").strip()
    GEMINI_LIGHT_MODEL = os.environ.get("GEMINI_LIGHT_MODEL", "gemini-flash-latest").strip()
    GEMINI_INTERVIEW_MODEL = os.environ.get("GEMINI_INTERVIEW_MODEL", "gemini-3.5-flash").strip()
    GEMINI_RESUME_MODEL = os.environ.get("GEMINI_RESUME_MODEL", "gemini-3.5-flash").strip()

