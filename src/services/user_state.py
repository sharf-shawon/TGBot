"""User state management for storing API keys and preferences."""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class UserState:
    """User state data structure."""

    user_id: int
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None  # User's preferred model (optional)
    max_query_results: int = 100
    show_sql: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "UserState":
        """Create UserState from dictionary."""
        return cls(**data)


class UserStateManager:
    """Manager for user states with persistent storage."""

    def __init__(self, data_dir: Path):
        """Initialize user state manager.

        Args:
            data_dir: Directory to store user data
        """
        self.data_dir = Path(data_dir)
        self.users_file = self.data_dir / "users.json"
        self._states: Dict[int, UserState] = {}
        self._ensure_data_dir()
        self._load_states()

    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"User data directory: {self.data_dir}")

    def _load_states(self):
        """Load user states from disk."""
        if not self.users_file.exists():
            logger.info("No existing user data found, starting fresh")
            return

        try:
            with open(self.users_file, "r") as f:
                data = json.load(f)
                self._states = {
                    int(user_id): UserState.from_dict(state_data)
                    for user_id, state_data in data.items()
                }
                logger.info(f"Loaded {len(self._states)} user states")
        except Exception as e:
            logger.error(f"Failed to load user states: {e}")
            self._states = {}

    def _save_states(self):
        """Save user states to disk."""
        try:
            data = {
                str(user_id): state.to_dict()
                for user_id, state in self._states.items()
            }
            with open(self.users_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("User states saved successfully")
        except Exception as e:
            logger.error(f"Failed to save user states: {e}")

    def get_user(self, user_id: int) -> UserState:
        """Get user state, creating if doesn't exist.

        Args:
            user_id: Telegram user ID

        Returns:
            User state
        """
        if user_id not in self._states:
            self._states[user_id] = UserState(user_id=user_id)
            self._save_states()
            logger.info(f"Created new user state for user {user_id}")

        return self._states[user_id]

    def update_user(self, user_id: int, **kwargs):
        """Update user state with new values.

        Args:
            user_id: Telegram user ID
            **kwargs: Fields to update
        """
        user = self.get_user(user_id)

        # Update fields
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
                logger.info(f"Updated user {user_id} field {key}")

        self._save_states()

    def set_api_key(self, user_id: int, api_key: str):
        """Set OpenRouter API key for user.

        Args:
            user_id: Telegram user ID
            api_key: OpenRouter API key
        """
        self.update_user(user_id, openrouter_api_key=api_key)

    def get_api_key(self, user_id: int) -> Optional[str]:
        """Get OpenRouter API key for user.

        Args:
            user_id: Telegram user ID

        Returns:
            API key if set, None otherwise
        """
        user = self.get_user(user_id)
        return user.openrouter_api_key

    def has_api_key(self, user_id: int) -> bool:
        """Check if user has API key set.

        Args:
            user_id: Telegram user ID

        Returns:
            True if API key is set, False otherwise
        """
        return self.get_api_key(user_id) is not None

    def get_effective_api_key(self, user_id: int, global_key: Optional[str] = None) -> Optional[str]:
        """Get the effective API key for a user (personal key takes precedence over global).

        Args:
            user_id: Telegram user ID
            global_key: Global API key to use as fallback

        Returns:
            User's personal API key if set, otherwise global key
        """
        user_key = self.get_api_key(user_id)
        return user_key if user_key is not None else global_key

    def clear_api_key(self, user_id: int):
        """Clear API key for user.

        Args:
            user_id: Telegram user ID
        """
        self.update_user(user_id, openrouter_api_key=None)

    def get_max_results(self, user_id: int) -> int:
        """Get maximum query results limit for user.

        Args:
            user_id: Telegram user ID

        Returns:
            Maximum number of results
        """
        user = self.get_user(user_id)
        return user.max_query_results

    def set_max_results(self, user_id: int, max_results: int):
        """Set maximum query results limit for user.

        Args:
            user_id: Telegram user ID
            max_results: Maximum number of results
        """
        self.update_user(user_id, max_query_results=max_results)

    def get_show_sql(self, user_id: int) -> bool:
        """Get whether to show SQL queries for user.

        Args:
            user_id: Telegram user ID

        Returns:
            True if SQL should be shown, False otherwise
        """
        user = self.get_user(user_id)
        return user.show_sql

    def set_show_sql(self, user_id: int, show_sql: bool):
        """Set whether to show SQL queries for user.

        Args:
            user_id: Telegram user ID
            show_sql: Whether to show SQL queries
        """
        self.update_user(user_id, show_sql=show_sql)

    def get_model(self, user_id: int) -> Optional[str]:
        """Get user's preferred OpenRouter model.

        Args:
            user_id: Telegram user ID

        Returns:
            Model name if set, None otherwise
        """
        user = self.get_user(user_id)
        return user.openrouter_model

    def set_model(self, user_id: int, model: str):
        """Set user's preferred OpenRouter model.

        Args:
            user_id: Telegram user ID
            model: OpenRouter model name
        """
        self.update_user(user_id, openrouter_model=model)

    def get_effective_model(self, user_id: int, default_model: str) -> str:
        """Get the effective model for a user (personal preference takes precedence over global default).

        Args:
            user_id: Telegram user ID
            default_model: Default model to use if user hasn't set a preference

        Returns:
            User's preferred model if set, otherwise default model
        """
        user_model = self.get_model(user_id)
        return user_model if user_model is not None else default_model

    def delete_user(self, user_id: int):
        """Delete user state.

        Args:
            user_id: Telegram user ID
        """
        if user_id in self._states:
            del self._states[user_id]
            self._save_states()
            logger.info(f"Deleted user state for user {user_id}")

    def get_all_users(self) -> Dict[int, UserState]:
        """Get all user states.

        Returns:
            Dictionary of user ID to UserState
        """
        return self._states.copy()
