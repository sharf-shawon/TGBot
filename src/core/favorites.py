"""Manage user's favorite stock tickers."""

import json

from core.config import BASE_DIR

DATA_DIR = BASE_DIR / "data"
FAVORITES_FILE = DATA_DIR / "favorites.json"


def _ensure_data_dir() -> None:
    """Ensure data directory exists."""
    DATA_DIR.mkdir(exist_ok=True)


def _load_favorites() -> dict:
    """Load all favorites from file."""
    _ensure_data_dir()
    if FAVORITES_FILE.exists():
        try:
            with open(FAVORITES_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_favorites(favorites: dict) -> None:
    """Save favorites to file."""
    _ensure_data_dir()
    with open(FAVORITES_FILE, "w") as f:
        json.dump(favorites, f, indent=2)


def add_favorite(user_id: int, ticker: str) -> bool:
    """
    Add a ticker to user's favorites.

    Args:
        user_id: Telegram user ID
        ticker: Stock ticker symbol

    Returns:
        True if added, False if already exists
    """
    favorites = _load_favorites()
    user_key = str(user_id)

    if user_key not in favorites:
        favorites[user_key] = []

    ticker_upper = ticker.upper()
    if ticker_upper not in favorites[user_key]:
        favorites[user_key].append(ticker_upper)
        _save_favorites(favorites)
        return True
    return False


def remove_favorite(user_id: int, ticker: str) -> bool:
    """
    Remove a ticker from user's favorites.

    Args:
        user_id: Telegram user ID
        ticker: Stock ticker symbol

    Returns:
        True if removed, False if not found
    """
    favorites = _load_favorites()
    user_key = str(user_id)

    if user_key not in favorites:
        return False

    ticker_upper = ticker.upper()
    if ticker_upper in favorites[user_key]:
        favorites[user_key].remove(ticker_upper)
        _save_favorites(favorites)
        return True
    return False


def get_favorites(user_id: int) -> list:
    """
    Get user's favorite tickers.

    Args:
        user_id: Telegram user ID

    Returns:
        List of ticker symbols
    """
    favorites = _load_favorites()
    user_key = str(user_id)
    return favorites.get(user_key, [])


def clear_favorites(user_id: int) -> None:
    """
    Clear all favorites for a user.

    Args:
        user_id: Telegram user ID
    """
    favorites = _load_favorites()
    user_key = str(user_id)
    if user_key in favorites:
        del favorites[user_key]
        _save_favorites(favorites)
