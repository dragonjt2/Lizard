from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping


class BaseGuildConfigStore(ABC):
    """Abstract interface for guild configuration persistence."""

    @abstractmethod
    def load_all(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def save_all(self, data: Mapping[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def set_guild_config(self, guild_id: int, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def increment_user_stat(
        self, guild_id: int, user_id: int, stat_type: str = "visits"
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        raise NotImplementedError


__all__ = ["BaseGuildConfigStore"]
