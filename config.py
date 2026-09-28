import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    """Application Configuration Settings for CareerBot."""
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY") or "careerbot_secure_random_key_2026_prod"
    # Database configuration with automatic postgres:// -> postgresql:// normalization for cloud providers
    _raw_db_uri = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI") or f"sqlite:///{BASE_DIR / 'careerbot.db'}"
    if _raw_db_uri.startswith("postgres://"):
        _raw_db_uri = _raw_db_uri.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session & Cookie Security Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
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

    # News API Configuration
    NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "").strip()
    NEWS_CACHE_TTL = 300  # 5 minutes in-memory cache

    # Job Dataset Path
    JOBS_DATASET_PATH = BASE_DIR / "data" / "jobs.csv"

