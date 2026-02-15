from core.env import ENV

TG_BOT_NAME = ENV.get("TG_BOT_NAME", "your_bot_Name_here")
TG_BOT_USERNAME = ENV.get("TG_BOT_USERNAME", "your_bot_username_here")
TG_BOT_TOKEN = ENV.get("TG_BOT_TOKEN", "your_bot_token_here")
TG_BOT_OWNER_ID = ENV.get("TG_BOT_OWNER_ID", 123456789)
TG_BOT_DP_URL = ENV.get("TG_BOT_DP_URL", "profile_picture_url")
OPENAI_API_KEY = ENV.get("OPENAI_API_KEY", "your_openai_api_key_here")
