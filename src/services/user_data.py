"""User data management service for storing API keys, models, and chat history."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class UserDataManager:
    """Manages user data persistence in JSON files."""

    def __init__(self, data_dir: str = "data"):
        """Initialize the user data manager.

        Args:
            data_dir: Directory to store user data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.users_dir = self.data_dir / "users"
        self.chats_dir = self.data_dir / "chats"
        self.users_dir.mkdir(exist_ok=True)
        self.chats_dir.mkdir(exist_ok=True)

    def _get_user_file(self, user_id: int) -> Path:
        """Get the path to a user's data file."""
        return self.users_dir / f"{user_id}.json"

    def _get_chat_file(self, user_id: int) -> Path:
        """Get the path to a user's chat history file."""
        return self.chats_dir / f"{user_id}.json"

    def save_api_key(self, user_id: int, api_key: str) -> None:
        """Save a user's OpenRouter API key.

        Args:
            user_id: Telegram user ID
            api_key: OpenRouter API key
        """
        user_data = self.get_user_data(user_id)
        user_data["api_key"] = api_key
        user_data["updated_at"] = datetime.now().isoformat()
        
        user_file = self._get_user_file(user_id)
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=2)

    def get_api_key(self, user_id: int) -> Optional[str]:
        """Get a user's OpenRouter API key.

        Args:
            user_id: Telegram user ID

        Returns:
            API key if exists, None otherwise
        """
        user_data = self.get_user_data(user_id)
        return user_data.get("api_key")

    def delete_api_key(self, user_id: int) -> bool:
        """Delete a user's API key.

        Args:
            user_id: Telegram user ID

        Returns:
            True if key was deleted, False if no key existed
        """
        user_data = self.get_user_data(user_id)
        if "api_key" in user_data:
            del user_data["api_key"]
            user_data["updated_at"] = datetime.now().isoformat()
            
            user_file = self._get_user_file(user_id)
            with open(user_file, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=2)
            return True
        return False

    def save_selected_model(self, user_id: int, model_id: str) -> None:
        """Save a user's selected model.

        Args:
            user_id: Telegram user ID
            model_id: OpenRouter model ID
        """
        user_data = self.get_user_data(user_id)
        user_data["selected_model"] = model_id
        user_data["updated_at"] = datetime.now().isoformat()
        
        user_file = self._get_user_file(user_id)
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=2)

    def get_selected_model(self, user_id: int) -> Optional[str]:
        """Get a user's selected model.

        Args:
            user_id: Telegram user ID

        Returns:
            Model ID if exists, None otherwise
        """
        user_data = self.get_user_data(user_id)
        return user_data.get("selected_model")

    def get_user_data(self, user_id: int) -> dict:
        """Get all user data.

        Args:
            user_id: Telegram user ID

        Returns:
            User data dictionary
        """
        user_file = self._get_user_file(user_id)
        if user_file.exists():
            with open(user_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"user_id": user_id, "created_at": datetime.now().isoformat()}

    def save_chat_message(
        self,
        user_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
    ) -> None:
        """Save a chat message to history.

        Args:
            user_id: Telegram user ID
            role: Message role (user/assistant)
            content: Message content
            model: Model used for assistant messages
        """
        chat_file = self._get_chat_file(user_id)
        
        # Load existing chat history
        if chat_file.exists():
            with open(chat_file, "r", encoding="utf-8") as f:
                chat_history = json.load(f)
        else:
            chat_history = {"user_id": user_id, "messages": []}
        
        # Add new message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if model:
            message["model"] = model
        
        chat_history["messages"].append(message)
        
        # Save updated history
        with open(chat_file, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, indent=2, ensure_ascii=False)

    def get_chat_history(self, user_id: int, limit: Optional[int] = None) -> list:
        """Get chat history for a user.

        Args:
            user_id: Telegram user ID
            limit: Optional limit on number of recent messages to return

        Returns:
            List of messages
        """
        chat_file = self._get_chat_file(user_id)
        
        if not chat_file.exists():
            return []
        
        with open(chat_file, "r", encoding="utf-8") as f:
            chat_history = json.load(f)
        
        messages = chat_history.get("messages", [])
        if limit:
            return messages[-limit:]
        return messages

    def clear_chat_history(self, user_id: int) -> None:
        """Clear chat history for a user.

        Args:
            user_id: Telegram user ID
        """
        chat_file = self._get_chat_file(user_id)
        if chat_file.exists():
            chat_file.unlink()
