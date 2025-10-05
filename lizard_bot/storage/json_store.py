from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from .base import BaseGuildConfigStore
from ..settings import logger


class JsonGuildConfigStore(BaseGuildConfigStore):
    """Current JSON-backed guild configuration store."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load_all(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
            except Exception as error:  # pragma: no cover - logging branch
                logger.error("Error loading guild configs: %s", error)
                return {}
        return {}

    def save_all(self, data: Mapping[str, Any]) -> None:
        try:
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            logger.info("Guild configurations saved")
        except Exception as error:  # pragma: no cover - logging branch
            logger.error("Error saving guild configs: %s", error)

    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        configs = self.load_all()
        return configs.get(str(guild_id), {})

    def set_guild_config(self, guild_id: int, **kwargs: Any) -> None:
        configs = self.load_all()
        guild_key = str(guild_id)
        guild_config = configs.setdefault(guild_key, {"stats": {}})
        guild_config.update(kwargs)
        self.save_all(configs)

    def increment_user_stat(
        self, guild_id: int, user_id: int, stat_type: str = "visits"
    ) -> None:
        configs = self.load_all()
        guild_key = str(guild_id)
        user_key = str(user_id)

        guild_config = configs.setdefault(guild_key, {"stats": {}})
        stats = guild_config.setdefault("stats", {})
        user_stats = stats.setdefault(user_key, {"visits": 0, "kidnaps": 0})
        user_stats[stat_type] = user_stats.get(stat_type, 0) + 1

        self.save_all(configs)

    def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        configs = self.load_all()
        guild_key = str(guild_id)
        guild_config = configs.get(guild_key, {})
        return guild_config.get("stats", {})


__all__ = ["JsonGuildConfigStore"]
