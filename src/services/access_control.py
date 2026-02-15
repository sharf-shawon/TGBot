"""Access control service for managing user permissions."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class AccessControl:
    """Manage user access permissions."""

    def __init__(self, data_dir: Path, admin_ids: List[int]):
        """Initialize access control.

        Args:
            data_dir: Directory to store access data
            admin_ids: List of admin user IDs
        """
        self.data_dir = Path(data_dir)
        self.access_file = self.data_dir / "access_control.json"
        self._admins: Set[int] = set(admin_ids)
        self._allowed_users: Set[int] = set()
        self._load_access_data()

    def _load_access_data(self):
        """Load access control data from disk."""
        if not self.access_file.exists():
            logger.info("No existing access control data, starting fresh")
            self._save_access_data()
            return

        try:
            with open(self.access_file, "r") as f:
                data = json.load(f)
                # Admins from config are always included
                saved_admins = set(data.get("admins", []))
                self._admins.update(saved_admins)
                self._allowed_users = set(data.get("allowed_users", []))
                logger.info(
                    f"Loaded access control: {len(self._admins)} admins, "
                    f"{len(self._allowed_users)} allowed users"
                )
        except Exception as e:
            logger.error(f"Failed to load access control data: {e}")
            self._allowed_users = set()

    def _save_access_data(self):
        """Save access control data to disk."""
        try:
            data = {
                "admins": list(self._admins),
                "allowed_users": list(self._allowed_users)
            }
            with open(self.access_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Access control data saved")
        except Exception as e:
            logger.error(f"Failed to save access control data: {e}")

    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user is admin, False otherwise
        """
        return user_id in self._admins

    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user is allowed (admin or in allowed list), False otherwise
        """
        return user_id in self._admins or user_id in self._allowed_users

    def add_user(self, user_id: int) -> bool:
        """Add a user to the allowed list.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user was added, False if already existed
        """
        if user_id in self._allowed_users:
            return False

        self._allowed_users.add(user_id)
        self._save_access_data()
        logger.info(f"Added user {user_id} to allowed list")
        return True

    def remove_user(self, user_id: int) -> bool:
        """Remove a user from the allowed list.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user was removed, False if didn't exist
        """
        if user_id not in self._allowed_users:
            return False

        self._allowed_users.remove(user_id)
        self._save_access_data()
        logger.info(f"Removed user {user_id} from allowed list")
        return True

    def add_admin(self, user_id: int) -> bool:
        """Add a user as admin.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user was added as admin, False if already admin
        """
        if user_id in self._admins:
            return False

        self._admins.add(user_id)
        # Remove from allowed users if present
        self._allowed_users.discard(user_id)
        self._save_access_data()
        logger.info(f"Added user {user_id} as admin")
        return True

    def remove_admin(self, user_id: int) -> bool:
        """Remove admin status from a user.

        Args:
            user_id: Telegram user ID

        Returns:
            True if admin was removed, False if wasn't admin
        """
        if user_id not in self._admins:
            return False

        self._admins.remove(user_id)
        self._save_access_data()
        logger.info(f"Removed admin status from user {user_id}")
        return True

    def get_admins(self) -> List[int]:
        """Get list of all admin user IDs.

        Returns:
            List of admin user IDs
        """
        return sorted(list(self._admins))

    def get_allowed_users(self) -> List[int]:
        """Get list of all allowed user IDs (not including admins).

        Returns:
            List of allowed user IDs
        """
        return sorted(list(self._allowed_users))

    def get_all_allowed_users(self) -> List[int]:
        """Get list of all users who can use the bot (admins + allowed users).

        Returns:
            List of all allowed user IDs
        """
        return sorted(list(self._admins.union(self._allowed_users)))

    def get_stats(self) -> Dict[str, int]:
        """Get access control statistics.

        Returns:
            Dictionary with admin count and allowed user count
        """
        return {
            "admins": len(self._admins),
            "allowed_users": len(self._allowed_users),
            "total": len(self._admins) + len(self._allowed_users)
        }
