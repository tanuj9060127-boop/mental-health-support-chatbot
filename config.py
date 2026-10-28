"""Central application configuration.

Secrets and deployment settings are read from environment variables. The
insecure development secret is deliberately local-only and is rejected in
production mode.
"""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=False)
except ImportError:
    # Environment variables can still be set directly by the shell/server.
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


APP_ENV = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development")).lower()
IS_PRODUCTION = APP_ENV == "production"
DEBUG = _env_bool("FLASK_DEBUG", False) and not IS_PRODUCTION
HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))

SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY is required in production. Generate one with: "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    # Rotate on each local process start instead of shipping a fixed signing key.
    SECRET_KEY = secrets.token_hex(32)

# Database. The root/empty-password defaults are for local development only.
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "mh_chatbot")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))

# Model and data paths.
MODEL_PATH = os.environ.get("MODEL_PATH", str(BASE_DIR / "emotion" / "model.joblib"))
DATASET_PATH = os.environ.get("DATASET_PATH", str(BASE_DIR / "emotion" / "dataset.csv"))
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.40"))

# Adaptive dialogue.
MAX_FOLLOW_UP_QUESTIONS = int(os.environ.get("MAX_FOLLOW_UP_QUESTIONS", "2"))

# Curated and generated resources.
RESOURCE_FILE = os.environ.get("RESOURCE_FILE", str(BASE_DIR / "resources" / "resources.json"))
VIDEO_RESOURCE_FILE = os.environ.get("VIDEO_RESOURCE_FILE", str(BASE_DIR / "resources" / "videos.json"))
VIDEO_MATCH_THRESHOLD = float(os.environ.get("VIDEO_MATCH_THRESHOLD", "0.55"))
_video_generation_dir = Path(
    os.environ.get("VIDEO_GENERATION_DIR", str(BASE_DIR / "static" / "generated_videos"))
).expanduser()
if not _video_generation_dir.is_absolute():
    _video_generation_dir = BASE_DIR / _video_generation_dir
VIDEO_GENERATION_DIR = str(_video_generation_dir.resolve())
VIDEO_MAX_SECONDS = int(os.environ.get("VIDEO_MAX_SECONDS", "90"))
HINDI_FONT_PATH = os.environ.get("HINDI_FONT_PATH", "").strip()

# Input limits.
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", "1000"))
MIN_PASSWORD_LENGTH = int(os.environ.get("MIN_PASSWORD_LENGTH", "8"))
MAX_PASSWORD_LENGTH = int(os.environ.get("MAX_PASSWORD_LENGTH", "1024"))
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 40
KNOWN_EMOTIONS = {"joy", "sadness", "anger", "fear", "stress", "confusion", "neutral"}
ALLOWED_GUIDED_EMOTIONS = {"neutral", "fear", "sadness", "anger", "stress", None}
ALLOWED_VIDEO_LANGUAGES = {"en", "hi"}

# Logging.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
