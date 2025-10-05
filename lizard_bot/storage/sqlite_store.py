from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from .base import BaseGuildConfigStore
from .json_store import DEFAULT_USER_TEMPLATE, STAT_ALIASES, JsonGuildConfigStore
from ..settings import logger


USER_DEFAULTS = dict(DEFAULT_USER_TEMPLATE)
PREFERENCE_KEYS = {"kidnap_opt_out"}
ID_FIELDS = {"default_text_channel_id", "temp_channel_id", "afk_channel_id"}
BOOL_FIELDS = {"auto_move_enabled"}


def _utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


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


def _stat_column(stat_type: str) -> Optional[str]:
    normalized = stat_type.lower()
    if normalized in USER_DEFAULTS:
        return normalized
    return STAT_ALIASES.get(normalized)


def _bool_to_int(value: Any) -> int:
    return 1 if bool(value) else 0


def _normalize_id(value: Any) -> Any:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _stringify_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


class SqliteGuildConfigStore(BaseGuildConfigStore):
    """SQLite-backed guild configuration store."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id TEXT PRIMARY KEY,
                    default_text_channel_id TEXT,
                    temp_channel_id TEXT,
                    afk_channel_id TEXT,
                    prefix TEXT DEFAULT '*',
                    auto_move_enabled INTEGER NOT NULL DEFAULT 1,
                    timer_min_minutes INTEGER NOT NULL DEFAULT 2,
                    timer_max_minutes INTEGER NOT NULL DEFAULT 30,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS guild_timers (
                    guild_id TEXT PRIMARY KEY REFERENCES guilds(guild_id) ON DELETE CASCADE,
                    next_visit_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_stats (
                    guild_id TEXT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    display_name TEXT,
                    visits INTEGER NOT NULL DEFAULT 0,
                    kidnapped INTEGER NOT NULL DEFAULT 0,
                    kidnap_attempts INTEGER NOT NULL DEFAULT 0,
                    kidnap_successes INTEGER NOT NULL DEFAULT 0,
                    kidnap_failures INTEGER NOT NULL DEFAULT 0,
                    kidnap_opt_out INTEGER NOT NULL DEFAULT 0,
                    kidnap_immunity_until TEXT,
                    PRIMARY KEY (guild_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS pending_kidnaps (
                    guild_id TEXT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    initiator_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    due_at TEXT,
                    PRIMARY KEY (guild_id, user_id)
                );
                """
            )
            
            # Add display_name column if it doesn't exist (for existing databases)
            try:
                connection.execute("ALTER TABLE user_stats ADD COLUMN display_name TEXT")
            except sqlite3.OperationalError:
                # Column already exists, ignore the error
                pass
            
            connection.commit()

    def _ensure_guild_row(self, connection: sqlite3.Connection, guild_id: int) -> None:
        now_iso = _to_iso(_utcnow())
        connection.execute(
            """
            INSERT INTO guilds (guild_id, created_at, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO NOTHING
            """,
            (str(guild_id), now_iso, now_iso),
        )

    def _has_data(self) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("SELECT 1 FROM guilds LIMIT 1")
            return cursor.fetchone() is not None

    def bootstrap_from_json(self, json_path: Path) -> None:
        json_path = Path(json_path)
        if not json_path.exists():
            return
        if self._has_data():
            return

        legacy_store = JsonGuildConfigStore(json_path)
        data = legacy_store.load_all()
        if not data:
            return

        logger.info("Importing %d legacy guilds from JSON into SQLite", len(data))
        self.save_all(data)

    # Base interface implementations -------------------------------------------------

    def load_all(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        with self._connect() as connection:
            guild_rows = connection.execute(
                "SELECT guild_id, default_text_channel_id, temp_channel_id, afk_channel_id, prefix, auto_move_enabled, timer_min_minutes, timer_max_minutes FROM guilds"
            ).fetchall()
            for row in guild_rows:
                payload[row["guild_id"]] = {
                    "default_text_channel_id": row["default_text_channel_id"],
                    "temp_channel_id": row["temp_channel_id"],
                    "afk_channel_id": row["afk_channel_id"],
                    "prefix": row["prefix"],
                    "auto_move_enabled": row["auto_move_enabled"],
                    "timer_min_minutes": row["timer_min_minutes"],
                    "timer_max_minutes": row["timer_max_minutes"],
                    "stats": {},
                    "pending_kidnaps": {},
                }

            stats_rows = connection.execute(
                "SELECT guild_id, user_id, visits, kidnapped, kidnap_attempts, kidnap_successes, kidnap_failures, kidnap_opt_out FROM user_stats"
            ).fetchall()
            for row in stats_rows:
                guild_payload = payload.setdefault(row["guild_id"], {"stats": {}, "pending_kidnaps": {}})
                stats = guild_payload.setdefault("stats", {})
                stats[row["user_id"]] = {
                    "visits": row["visits"],
                    "kidnapped": row["kidnapped"],
                    "kidnap_attempts": row["kidnap_attempts"],
                    "kidnap_successes": row["kidnap_successes"],
                    "kidnap_failures": row["kidnap_failures"],
                    "kidnap_opt_out": bool(row["kidnap_opt_out"]),
                }

            pending_rows = connection.execute(
                "SELECT guild_id, user_id, initiator_id, created_at, due_at FROM pending_kidnaps"
            ).fetchall()
            for row in pending_rows:
                guild_payload = payload.setdefault(row["guild_id"], {"stats": {}, "pending_kidnaps": {}})
                pending = guild_payload.setdefault("pending_kidnaps", {})
                pending[row["user_id"]] = {
                    "initiator_id": row["initiator_id"],
                    "created_at": row["created_at"],
                    "due_at": row["due_at"],
                }

            timer_rows = connection.execute(
                "SELECT guild_id, next_visit_at FROM guild_timers"
            ).fetchall()
            for row in timer_rows:
                guild_payload = payload.setdefault(row["guild_id"], {"stats": {}, "pending_kidnaps": {}})
                guild_payload.setdefault("timer", {})["next_visit_at"] = row["next_visit_at"]

        return payload

    def save_all(self, data: Mapping[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM pending_kidnaps")
            connection.execute("DELETE FROM user_stats")
            connection.execute("DELETE FROM guild_timers")
            connection.execute("DELETE FROM guilds")

            now_iso = _to_iso(_utcnow())
            for guild_key, payload in data.items():
                guild_id = str(guild_key)
                config = {
                    "default_text_channel_id": _stringify_id(payload.get("default_text_channel_id")),
                    "temp_channel_id": _stringify_id(payload.get("temp_channel_id")),
                    "afk_channel_id": _stringify_id(payload.get("afk_channel_id")),
                    "prefix": payload.get("prefix", "*"),
                    "auto_move_enabled": _bool_to_int(payload.get("auto_move_enabled", 1)),
                    "timer_min_minutes": int(payload.get("timer_min_minutes", 2)),
                    "timer_max_minutes": int(payload.get("timer_max_minutes", 30)),
                }

                connection.execute(
                    """
                    INSERT INTO guilds (
                        guild_id,
                        default_text_channel_id,
                        temp_channel_id,
                        afk_channel_id,
                        prefix,
                        auto_move_enabled,
                        timer_min_minutes,
                        timer_max_minutes,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        config["default_text_channel_id"],
                        config["temp_channel_id"],
                        config["afk_channel_id"],
                        config["prefix"],
                        config["auto_move_enabled"],
                        config["timer_min_minutes"],
                        config["timer_max_minutes"],
                        now_iso,
                        now_iso,
                    ),
                )

                stats = payload.get("stats", {})
                for user_key, stats_payload in stats.items():
                    stats_data = dict(USER_DEFAULTS)
                    stats_data.update(stats_payload)
                    kidnapped_value = stats_data.get("kidnapped", stats_data.get("kidnaps", 0))
                    connection.execute(
                        """
                        INSERT INTO user_stats (
                            guild_id,
                            user_id,
                            visits,
                            kidnapped,
                            kidnap_attempts,
                            kidnap_successes,
                            kidnap_failures,
                            kidnap_opt_out
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            guild_id,
                            _stringify_id(user_key),
                            int(stats_data.get("visits", 0)),
                            int(kidnapped_value),
                            int(stats_data.get("kidnap_attempts", 0)),
                            int(stats_data.get("kidnap_successes", 0)),
                            int(stats_data.get("kidnap_failures", 0)),
                            _bool_to_int(stats_data.get("kidnap_opt_out", False)),
                        ),
                    )

                pending = payload.get("pending_kidnaps", {})
                for user_key, entry in pending.items():
                    connection.execute(
                        """
                        INSERT INTO pending_kidnaps (
                            guild_id,
                            user_id,
                            initiator_id,
                            created_at,
                            due_at
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            guild_id,
                            _stringify_id(user_key),
                            _stringify_id(entry.get("initiator_id")),
                            _to_iso(entry.get("created_at")),
                            _to_iso(entry.get("due_at")),
                        ),
                    )

                timer_info = payload.get("timer", {})
                next_visit = timer_info.get("next_visit_at") or payload.get("next_visit_at")
                if next_visit:
                    connection.execute(
                        """
                        INSERT INTO guild_timers (guild_id, next_visit_at, updated_at)
                        VALUES (?, ?, ?)
                        """,
                        (
                            guild_id,
                            _stringify_id(next_visit),
                            now_iso,
                        ),
                    )

            connection.commit()

    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT default_text_channel_id,
                       temp_channel_id,
                       afk_channel_id,
                       prefix,
                       auto_move_enabled,
                       timer_min_minutes,
                       timer_max_minutes
                FROM guilds
                WHERE guild_id = ?
                """,
                (str(guild_id),),
            ).fetchone()

            config: Dict[str, Any] = {}
            if row:
                config = {
                    "default_text_channel_id": _normalize_id(row["default_text_channel_id"]),
                    "temp_channel_id": _normalize_id(row["temp_channel_id"]),
                    "afk_channel_id": _normalize_id(row["afk_channel_id"]),
                    "prefix": row["prefix"],
                    "auto_move_enabled": bool(row["auto_move_enabled"]),
                    "timer_min_minutes": row["timer_min_minutes"],
                    "timer_max_minutes": row["timer_max_minutes"],
                }

            timer_row = connection.execute(
                "SELECT next_visit_at FROM guild_timers WHERE guild_id = ?",
                (str(guild_id),),
            ).fetchone()
            if timer_row:
                config["next_visit_at"] = timer_row["next_visit_at"]

            return config

    def set_guild_config(self, guild_id: int, **kwargs: Any) -> None:
        allowed = {
            "default_text_channel_id",
            "temp_channel_id",
            "afk_channel_id",
            "prefix",
            "auto_move_enabled",
            "timer_min_minutes",
            "timer_max_minutes",
        }
        updates = {key: kwargs[key] for key in kwargs if key in allowed}
        if not updates:
            return

        for key in ID_FIELDS & updates.keys():
            updates[key] = _stringify_id(updates[key])
        for key in BOOL_FIELDS & updates.keys():
            updates[key] = _bool_to_int(updates[key])
        for key in {"timer_min_minutes", "timer_max_minutes"} & updates.keys():
            updates[key] = int(updates[key])

        now_iso = _to_iso(_utcnow())
        with self._connect() as connection:
            self._ensure_guild_row(connection, guild_id)
            set_clause_parts = [f"{column} = ?" for column in updates]
            params = [updates[column] for column in updates]
            params.extend([now_iso, str(guild_id)])
            connection.execute(
                f"UPDATE guilds SET {', '.join(set_clause_parts)}, updated_at = ? WHERE guild_id = ?",
                params,
            )

    def increment_user_stat(
        self,
        guild_id: int,
        user_id: int,
        stat_type: str = "visits",
        amount: int = 1,
        display_name: str = None,
    ) -> None:
        column = _stat_column(stat_type)
        if not column:
            logger.warning("Unknown stat type '%s' ignored", stat_type)
            return
        if amount == 0 and not display_name:
            return

        with self._connect() as connection:
            self._ensure_guild_row(connection, guild_id)
            if display_name and amount != 0:
                connection.execute(
                    f"""
                    INSERT INTO user_stats (guild_id, user_id, display_name, {column})
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        display_name = excluded.display_name,
                        {column} = CASE
                            WHEN user_stats.{column} + excluded.{column} < 0 THEN 0
                            ELSE user_stats.{column} + excluded.{column}
                        END
                    """,
                    (str(guild_id), str(user_id), display_name, int(amount)),
                )
            elif display_name and amount == 0:
                # Only update display name, don't change stats
                connection.execute(
                    """
                    INSERT INTO user_stats (guild_id, user_id, display_name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        display_name = excluded.display_name
                    """,
                    (str(guild_id), str(user_id), display_name),
                )
            else:
                connection.execute(
                    f"""
                    INSERT INTO user_stats (guild_id, user_id, {column})
                    VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        {column} = CASE
                            WHEN user_stats.{column} + excluded.{column} < 0 THEN 0
                            ELSE user_stats.{column} + excluded.{column}
                        END
                    """,
                    (str(guild_id), str(user_id), int(amount)),
                )

    def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT user_id,
                       display_name,
                       visits,
                       kidnapped,
                       kidnap_attempts,
                       kidnap_successes,
                       kidnap_failures,
                       kidnap_opt_out
                FROM user_stats
                WHERE guild_id = ?
                """,
                (str(guild_id),),
            ).fetchall()

        return {
            row["user_id"]: {
                "display_name": row["display_name"],
                "visits": row["visits"],
                "kidnapped": row["kidnapped"],
                "kidnap_attempts": row["kidnap_attempts"],
                "kidnap_successes": row["kidnap_successes"],
                "kidnap_failures": row["kidnap_failures"],
                "kidnap_opt_out": bool(row["kidnap_opt_out"]),
            }
            for row in rows
        }

    def set_user_preferences(self, guild_id: int, user_id: int, **prefs: Any) -> None:
        filtered = {key: prefs[key] for key in prefs if key in PREFERENCE_KEYS}
        if not filtered:
            return

        with self._connect() as connection:
            self._ensure_guild_row(connection, guild_id)
            connection.execute(
                """
                INSERT INTO user_stats (guild_id, user_id, kidnap_opt_out)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    kidnap_opt_out = excluded.kidnap_opt_out
                """,
                (str(guild_id), str(user_id), _bool_to_int(filtered.get("kidnap_opt_out", False))),
            )

    def get_user_preferences(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT kidnap_opt_out FROM user_stats WHERE guild_id = ? AND user_id = ?",
                (str(guild_id), str(user_id)),
            ).fetchone()
        opt_out = bool(row["kidnap_opt_out"]) if row else False
        return {"kidnap_opt_out": opt_out}

    def set_pending_kidnap(
        self,
        guild_id: int,
        target_user_id: int,
        initiator_user_id: int,
        due_at: Optional[datetime] = None,
    ) -> None:
        now_iso = _to_iso(_utcnow())
        with self._connect() as connection:
            self._ensure_guild_row(connection, guild_id)
            connection.execute(
                """
                INSERT INTO pending_kidnaps (guild_id, user_id, initiator_id, created_at, due_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    initiator_id = excluded.initiator_id,
                    created_at = excluded.created_at,
                    due_at = excluded.due_at
                """,
                (
                    str(guild_id),
                    str(target_user_id),
                    str(initiator_user_id),
                    now_iso,
                    _to_iso(due_at),
                ),
            )

    def clear_pending_kidnap(self, guild_id: int, target_user_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM pending_kidnaps WHERE guild_id = ? AND user_id = ?",
                (str(guild_id), str(target_user_id)),
            )

    def get_pending_kidnap(
        self, guild_id: int, target_user_id: int
    ) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT initiator_id, created_at, due_at
                FROM pending_kidnaps
                WHERE guild_id = ? AND user_id = ?
                """,
                (str(guild_id), str(target_user_id)),
            ).fetchone()
        if not row:
            return None
        initiator = row["initiator_id"]
        try:
            initiator = int(initiator)
        except (TypeError, ValueError):
            pass
        return {
            "initiator_id": initiator,
            "created_at": _from_iso(row["created_at"]),
            "due_at": _from_iso(row["due_at"]),
        }

    def load_pending_kidnaps(self) -> Dict[Tuple[int, int], Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT guild_id, user_id, initiator_id, created_at, due_at FROM pending_kidnaps"
            ).fetchall()
        pending: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for row in rows:
            try:
                guild_id = int(row["guild_id"])
                user_id = int(row["user_id"])
            except ValueError:
                continue
            initiator = row["initiator_id"]
            try:
                initiator = int(initiator)
            except (TypeError, ValueError):
                pass
            pending[(guild_id, user_id)] = {
                "initiator_id": initiator,
                "created_at": _from_iso(row["created_at"]),
                "due_at": _from_iso(row["due_at"]),
            }
        return pending

    def set_guild_timer(
        self, guild_id: int, next_visit_at: Optional[datetime]
    ) -> None:
        now_iso = _to_iso(_utcnow())
        with self._connect() as connection:
            self._ensure_guild_row(connection, guild_id)
            connection.execute(
                """
                INSERT INTO guild_timers (guild_id, next_visit_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    next_visit_at = excluded.next_visit_at,
                    updated_at = excluded.updated_at
                """,
                (str(guild_id), _to_iso(next_visit_at), now_iso),
            )

    def get_guild_timer(self, guild_id: int) -> Optional[datetime]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT next_visit_at FROM guild_timers WHERE guild_id = ?",
                (str(guild_id),),
            ).fetchone()
        if not row:
            return None
        return _from_iso(row["next_visit_at"])

    def load_guild_timers(self) -> Dict[int, Optional[datetime]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT g.guild_id, t.next_visit_at
                FROM guilds g
                LEFT JOIN guild_timers t ON g.guild_id = t.guild_id
                """
            ).fetchall()
        timers: Dict[int, Optional[datetime]] = {}
        for row in rows:
            try:
                guild_id = int(row["guild_id"])
            except ValueError:
                continue
            timers[guild_id] = _from_iso(row["next_visit_at"])
        return timers


__all__ = ["SqliteGuildConfigStore"]
