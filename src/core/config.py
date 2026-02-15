
from core.env import BASE_DIR, ENV

TG_BOT_NAME = ENV.get("TG_BOT_NAME", "your_bot_Name_here")
TG_BOT_USERNAME = ENV.get("TG_BOT_USERNAME", "your_bot_username_here")
TG_BOT_TOKEN = ENV.get("TG_BOT_TOKEN", "your_bot_token_here")
TG_BOT_OWNER_ID = ENV.get("TG_BOT_OWNER_ID", 123456789)
TG_BOT_DP_URL = ENV.get("TG_BOT_DP_URL", "profile_picture_url")

# Admin user IDs (comma-separated list)
_admin_ids_str = ENV.get("ADMIN_USER_IDS", 6732766579)  
ADMIN_USER_IDS = [int(uid.strip()) for uid in _admin_ids_str.split(",") if uid.strip()]

# OpenRouter Configuration (optional global defaults)
# Optional global API key
OPENROUTER_API_KEY = ENV.get("OPENROUTER_API_KEY", None)
# Default model for all users (using free model by default)
OPENROUTER_MODEL = ENV.get(
    "OPENROUTER_MODEL", "google/gemini-flash-1.5:free"
)

# PostgreSQL connection URL
# Format: postgresql://username:password@host:port/database
POSTGRES_URL = ENV.get("POSTGRES_URL", "postgresql://user:password@localhost:5432/database")

# Data directory for persistent storage
# Default: ./data in project root for local dev, /app/data for Docker
_default_data_dir = str(BASE_DIR.parent / "data")
DATA_DIR = ENV.get("DATA_DIR", _default_data_dir)
