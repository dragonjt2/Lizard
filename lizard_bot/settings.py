from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import discord
from dotenv import load_dotenv

from .config_manager import ConfigManager


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord")


@dataclass(frozen=True)
class Settings:
    """Runtime configuration values for the bot."""

    token: str | None
    command_prefix: str
    activity_name: str
    readme_url: str
    kofi_url: str
    config_file: Path
    database_file: Path
    audio_file: Path
    ffmpeg_path: Path
    dice_gif: Path
    frames_directory: Path
    messages: Dict[str, str]
    lizard_cooldown: int
    kidnap_cooldown: int
    dice_roll_success_threshold: int
    dice_roll_failure_threshold: int
    immunity_duration_minutes: int
    pending_kidnap_delay_seconds: int
    connection_timeout: float
    playback_delay_seconds: float
    disconnect_delay_seconds: float
    lizard_reaction_probability: float
    timer_min_minutes: int
    timer_max_minutes: int


def load_settings() -> Settings:
    """Load strongly-typed settings from configuration and environment."""
    project_root = Path(__file__).resolve().parent.parent
    config_manager = ConfigManager(project_root / "config.ini")

    token = os.getenv("DISCORD_BOT_TOKEN")
    command_prefix = config_manager.get("bot", "command_prefix", "*")
    activity_name = config_manager.get("bot", "activity_name", "Lizard")

    readme_url = config_manager.get(
        "urls", "readme_url", "https://github.com/yourname/Lizard#readme"
    )
    kofi_url = config_manager.get("urls", "kofi_url", "https://ko-fi.com/yourname")

    config_file = project_root / config_manager.get("files", "config_file", "guild_configs.json")
    database_file = project_root / "guild_data.sqlite3"
    audio_file = project_root / config_manager.get("files", "audio_file", "lizzard-1.mp3")
    ffmpeg_path = project_root / config_manager.get("files", "ffmpeg_path", "ffmpeg.exe")
    dice_gif = project_root / config_manager.get("files", "dice_gif", "Diceroll.gif")
    frames_directory = project_root / config_manager.get("files", "frames_directory", "Frames")

    messages = config_manager.get_section("messages")

    lizard_cooldown = config_manager.get_int("cooldowns", "lizard_cooldown", 30)
    kidnap_cooldown = config_manager.get_int("cooldowns", "kidnap_cooldown", 45)

    dice_roll_success_threshold = config_manager.get_int("kidnap", "dice_roll_success_threshold", 14)
    dice_roll_failure_threshold = config_manager.get_int("kidnap", "dice_roll_failure_threshold", 7)
    immunity_duration_minutes = config_manager.get_int("kidnap", "immunity_duration_minutes", 30)
    pending_kidnap_delay_seconds = config_manager.get_int("kidnap", "pending_kidnap_delay_seconds", 2)

    connection_timeout = config_manager.get_float("voice", "connection_timeout", 30.0)
    playback_delay_seconds = config_manager.get_float("voice", "playback_delay_seconds", 1.0)
    disconnect_delay_seconds = config_manager.get_float("voice", "disconnect_delay_seconds", 1.0)

    lizard_reaction_probability = config_manager.get_float(
        "reactions", "lizard_reaction_probability", 0.03
    )

    timer_min_minutes = config_manager.get_int("timer", "min_visit_delay", 2)
    timer_max_minutes = config_manager.get_int("timer", "max_visit_delay", 30)

    return Settings(
        token=token,
        command_prefix=command_prefix,
        activity_name=activity_name,
        readme_url=readme_url,
        kofi_url=kofi_url,
        config_file=config_file,
        database_file=database_file,
        audio_file=audio_file,
        ffmpeg_path=ffmpeg_path,
        dice_gif=dice_gif,
        frames_directory=frames_directory,
        messages=messages,
        lizard_cooldown=lizard_cooldown,
        kidnap_cooldown=kidnap_cooldown,
        dice_roll_success_threshold=dice_roll_success_threshold,
        dice_roll_failure_threshold=dice_roll_failure_threshold,
        immunity_duration_minutes=immunity_duration_minutes,
        pending_kidnap_delay_seconds=pending_kidnap_delay_seconds,
        connection_timeout=connection_timeout,
        playback_delay_seconds=playback_delay_seconds,
        disconnect_delay_seconds=disconnect_delay_seconds,
        lizard_reaction_probability=lizard_reaction_probability,
        timer_min_minutes=timer_min_minutes,
        timer_max_minutes=timer_max_minutes,
    )


def create_intents() -> discord.Intents:
    """Create and configure Discord intents for the bot."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True
    return intents


__all__ = ["Settings", "load_settings", "create_intents", "logger"]
