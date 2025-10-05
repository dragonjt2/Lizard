from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from .base import BaseGuildConfigStore
from ..settings import logger


DEFAULT_USER_TEMPLATE: Dict[str, Any] = {
    "visits": 0,
    "kidnapped": 0,
    "kidnap_attempts": 0,
    "kidnap_successes": 0,
    "kidnap_failures": 0,
    "kidnap_opt_out": False,
}

STAT_ALIASES: Dict[str, str] = {
    "kidnaps": "kidnapped",
    "kidnap": "kidnapped",
    "kidnap_success": "kidnap_successes",
    "kidnap_successes": "kidnap_successes",
    "kidnap_failure": "kidnap_failures",
    "kidnap_failures": "kidnap_failures",
}

PREFERENCE_KEYS = {"kidnap_opt_out"}

DEFAULT_GUILD_VALUES: Dict[str, Any] = {
    "auto_move_enabled": True,
    "timer_min_minutes": 2,
    "timer_max_minutes": 30,
    "kidnap_immunity_minutes": 30,
    "kidnap_channel_id": None,
}


def _to_user_key(user_id: int) -> str:
    return str(user_id)


def _to_guild_key(guild_id: int) -> str:
    return str(guild_id)


def _copy_user_template() -> Dict[str, Any]:
    return dict(DEFAULT_USER_TEMPLATE)


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def _from_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            if value.endswith("Z"):
                value = value[:-1]
            return datetime.fromisoformat(value)
        except ValueError:
            logger.warning("Unable to parse datetime value: %s", value)
    return None


class JsonGuildConfigStore(BaseGuildConfigStore):
    """JSON-backed guild storage used as a compatibility fallback."""

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

    def _ensure_guild(self, configs: Dict[str, Any], guild_key: str) -> Dict[str, Any]:
        guild_config = configs.setdefault(guild_key, {})
        guild_config.setdefault("stats", {})
        guild_config.setdefault("pending_kidnaps", {})
        guild_config.setdefault("timer", {})
        for key, value in DEFAULT_GUILD_VALUES.items():
            guild_config.setdefault(key, value)
        return guild_config

    def _normalize_stat_name(self, stat_type: str) -> Optional[str]:
        normalized = stat_type.lower()
        if normalized in DEFAULT_USER_TEMPLATE:
            return normalized
        return STAT_ALIASES.get(normalized)

    def _compose_user(self, stats: Mapping[str, Any]) -> Dict[str, Any]:
        user_data = _copy_user_template()
        for key, value in stats.items():
            if key in user_data:
                user_data[key] = value
        user_data["visits"] = int(user_data.get("visits", 0))
        user_data["kidnapped"] = int(user_data.get("kidnapped", 0))
        user_data["kidnap_attempts"] = int(user_data.get("kidnap_attempts", 0))
        user_data["kidnap_successes"] = int(user_data.get("kidnap_successes", 0))
        user_data["kidnap_failures"] = int(user_data.get("kidnap_failures", 0))
        user_data["kidnap_opt_out"] = bool(user_data.get("kidnap_opt_out", False))
        return user_data

    def _coerce_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        coerced = dict(config)
        if "auto_move_enabled" in coerced:
            coerced["auto_move_enabled"] = bool(coerced["auto_move_enabled"])
        for key in ("timer_min_minutes", "timer_max_minutes", "kidnap_immunity_minutes"):
            if key in coerced and coerced[key] is not None:
                coerced[key] = int(coerced[key])
        if "kidnap_channel_id" in coerced and coerced["kidnap_channel_id"] is not None:
            coerced["kidnap_channel_id"] = int(coerced["kidnap_channel_id"])
        return coerced

    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        guild_config = self._ensure_guild(configs, guild_key)
        config = {
            key: value
            for key, value in guild_config.items()
            if key not in {"stats", "pending_kidnaps", "timer"}
        }
        timer_info = guild_config.get("timer", {})
        if "next_visit_at" in timer_info:
            config["next_visit_at"] = timer_info.get("next_visit_at")
        return self._coerce_config(config)

    def set_guild_config(self, guild_id: int, **kwargs: Any) -> None:
        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        guild_config = self._ensure_guild(configs, guild_key)
        updates = self._coerce_config(kwargs)
        guild_config.update(updates)
        self.save_all(configs)

    def increment_user_stat(
        self,
        guild_id: int,
        user_id: int,
        stat_type: str = "visits",
        amount: int = 1,
    ) -> None:
        stat_name = self._normalize_stat_name(stat_type)
        if not stat_name:
            logger.warning("Unknown stat type '%s' ignored", stat_type)
            return

        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        guild_config = self._ensure_guild(configs, guild_key)
        stats = guild_config.setdefault("stats", {})
        user_key = _to_user_key(user_id)
        user_stats = stats.setdefault(user_key, _copy_user_template())
        current_value = int(user_stats.get(stat_name, 0))
        user_stats[stat_name] = max(0, current_value + amount)
        self.save_all(configs)

    def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        guild_config = self._ensure_guild(configs, guild_key)
        stats = guild_config.get("stats", {})
        return {
            user_id: self._compose_user(user_stats)
            for user_id, user_stats in stats.items()
        }

    def set_user_preferences(self, guild_id: int, user_id: int, **prefs: Any) -> None:
        filtered = {key: value for key, value in prefs.items() if key in PREFERENCE_KEYS}
        if not filtered:
            return

        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        guild_config = self._ensure_guild(configs, guild_key)
        stats = guild_config.setdefault("stats", {})
        user_key = _to_user_key(user_id)
        user_stats = stats.setdefault(user_key, _copy_user_template())
        user_stats.update(filtered)
        self.save_all(configs)

    def get_user_preferences(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        stats = self.get_guild_stats(guild_id)
        user_key = _to_user_key(user_id)
        user_stats = stats.get(user_key, _copy_user_template())
        return {key: user_stats.get(key, DEFAULT_USER_TEMPLATE[key]) for key in PREFERENCE_KEYS}

    def set_pending_kidnap(
        self,
        guild_id: int,
        target_user_id: int,
        initiator_user_id: int,
        due_at: Optional[datetime] = None,
    ) -> None:
        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        guild_config = self._ensure_guild(configs, guild_key)
        pending = guild_config.setdefault("pending_kidnaps", {})
        target_key = _to_user_key(target_user_id)
        pending[target_key] = {
            "initiator_id": initiator_user_id,
            "created_at": _to_iso(datetime.utcnow()),
            "due_at": _to_iso(due_at),
        }
        self.save_all(configs)

    def clear_pending_kidnap(self, guild_id: int, target_user_id: int) -> None:
        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        guild_config = self._ensure_guild(configs, guild_key)
        pending = guild_config.setdefault("pending_kidnaps", {})
        target_key = _to_user_key(target_user_id)
        if target_key in pending:
            pending.pop(target_key, None)
            self.save_all(configs)

    def get_pending_kidnap(
        self, guild_id: int, target_user_id: int
    ) -> Optional[Dict[str, Any]]:
        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        pending = self._ensure_guild(configs, guild_key).get("pending_kidnaps", {})
        entry = pending.get(_to_user_key(target_user_id))
        if not entry:
            return None
        return {
            "initiator_id": entry.get("initiator_id"),
            "created_at": _from_iso(entry.get("created_at")),
            "due_at": _from_iso(entry.get("due_at")),
        }

    def load_pending_kidnaps(self) -> Dict[Tuple[int, int], Dict[str, Any]]:
        configs = self.load_all()
        pending_map: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for guild_key, payload in configs.items():
            pending = payload.get("pending_kidnaps", {})
            for user_key, entry in pending.items():
                try:
                    g_id = int(guild_key)
                    u_id = int(user_key)
                except ValueError:
                    continue
                pending_map[(g_id, u_id)] = {
                    "initiator_id": entry.get("initiator_id"),
                    "created_at": _from_iso(entry.get("created_at")),
                    "due_at": _from_iso(entry.get("due_at")),
                }
        return pending_map

    def set_guild_timer(
        self, guild_id: int, next_visit_at: Optional[datetime]
    ) -> None:
        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        guild_config = self._ensure_guild(configs, guild_key)
        timer = guild_config.setdefault("timer", {})
        timer["next_visit_at"] = _to_iso(next_visit_at)
        timer["updated_at"] = _to_iso(datetime.utcnow())
        self.save_all(configs)

    def get_guild_timer(self, guild_id: int) -> Optional[datetime]:
        configs = self.load_all()
        guild_key = _to_guild_key(guild_id)
        timer = self._ensure_guild(configs, guild_key).get("timer", {})
        return _from_iso(timer.get("next_visit_at"))

    def load_guild_timers(self) -> Dict[int, Optional[datetime]]:
        configs = self.load_all()
        timers: Dict[int, Optional[datetime]] = {}
        for guild_key, payload in configs.items():
            try:
                g_id = int(guild_key)
            except ValueError:
                continue
            timer = payload.get("timer", {})
            timers[g_id] = _from_iso(timer.get("next_visit_at"))
        return timers


__all__ = ["JsonGuildConfigStore"]
