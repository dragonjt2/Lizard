from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Mapping

from .base import BaseGuildConfigStore
from ..settings import logger


SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_configs (
    guild_id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
"""


class SqliteGuildConfigStore(BaseGuildConfigStore):
    """SQLite-backed guild configuration store (scaffolding)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(SCHEMA)
            connection.commit()

    # The following methods still delegate to JSON-style semantics.
    # They will be fully implemented in the upcoming migration work.

    def load_all(self) -> Dict[str, Any]:  # pragma: no cover - placeholder
        logger.warning("SQLite store load_all not yet implemented")
        return {}

    def save_all(self, data: Mapping[str, Any]) -> None:  # pragma: no cover
        logger.warning("SQLite store save_all not yet implemented")

    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:  # pragma: no cover
        logger.warning("SQLite store get_guild_config not yet implemented")
        return {}

    def set_guild_config(self, guild_id: int, **kwargs: Any) -> None:  # pragma: no cover
        logger.warning("SQLite store set_guild_config not yet implemented")

    def increment_user_stat(
        self, guild_id: int, user_id: int, stat_type: str = "visits"
    ) -> None:  # pragma: no cover
        logger.warning("SQLite store increment_user_stat not yet implemented")

    def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:  # pragma: no cover
        logger.warning("SQLite store get_guild_stats not yet implemented")
        return {}


__all__ = ["SqliteGuildConfigStore"]
