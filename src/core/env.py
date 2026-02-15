from os import environ
from pathlib import Path

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
# Load src/.env and overlay with real environment variables (env wins).
ENV = {**dotenv_values(BASE_DIR / ".env"), **environ}
