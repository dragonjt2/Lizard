from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Tuple


class BaseGuildConfigStore(ABC):
    """Abstract interface for guild configuration, stats, and state persistence."""

    @abstractmethod
    def load_all(self) -> Dict[str, Any]:
        """Return a raw representation of every guild payload (for diagnostics)."""
        raise NotImplementedError

    @abstractmethod
    def save_all(self, data: Mapping[str, Any]) -> None:
        """Persist the provided raw payload (used primarily by JSON fallback)."""
        raise NotImplementedError

    @abstractmethod
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Fetch configuration values for a guild (channel ids, prefix, etc)."""
        raise NotImplementedError

    @abstractmethod
    def set_guild_config(self, guild_id: int, **kwargs: Any) -> None:
        """Upsert configuration values for a guild."""
        raise NotImplementedError

    @abstractmethod
    def increment_user_stat(
        self,
        guild_id: int,
        user_id: int,
        stat_type: str = "visits",
        amount: int = 1,
    ) -> None:
        """Increment a numeric stat (visits, kidnapped, attempts, successes, failures)."""
        raise NotImplementedError

    @abstractmethod
    def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        """Return all tracked stats (and preferences) for users within the guild."""
        raise NotImplementedError

    @abstractmethod
    def set_user_preferences(self, guild_id: int, user_id: int, **prefs: Any) -> None:
        """Persist preference flags (e.g. kidnap opt-out) for a user."""
        raise NotImplementedError

    @abstractmethod
    def get_user_preferences(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Retrieve preference flags for a specific user."""
        raise NotImplementedError

    @abstractmethod
    def set_pending_kidnap(
        self,
        guild_id: int,
        target_user_id: int,
        initiator_user_id: int,
        due_at: Optional[datetime] = None,
    ) -> None:
        """Store a pending kidnap record so it survives restarts."""
        raise NotImplementedError

    @abstractmethod
    def clear_pending_kidnap(self, guild_id: int, target_user_id: int) -> None:
        """Remove any pending kidnap entry for a given target."""
        raise NotImplementedError

    @abstractmethod
    def get_pending_kidnap(
        self, guild_id: int, target_user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch pending kidnap metadata for the given target (if any)."""
        raise NotImplementedError

    @abstractmethod
    def load_pending_kidnaps(self) -> Dict[Tuple[int, int], Dict[str, Any]]:
        """Load all pending kidnap entries keyed by (guild_id, user_id)."""
        raise NotImplementedError

    @abstractmethod
    def set_guild_timer(
        self, guild_id: int, next_visit_at: Optional[datetime]
    ) -> None:
        """Persist the next scheduled automatic visit time for a guild."""
        raise NotImplementedError

    @abstractmethod
    def get_guild_timer(self, guild_id: int) -> Optional[datetime]:
        """Return the next scheduled automatic visit, if recorded."""
        raise NotImplementedError

    @abstractmethod
    def load_guild_timers(self) -> Dict[int, Optional[datetime]]:
        """Return next scheduled visits for all guilds."""
        raise NotImplementedError


__all__ = ["BaseGuildConfigStore"]
