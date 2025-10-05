from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import discord
from dotenv import load_dotenv


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord")


@dataclass(frozen=True)
class Settings:
    """Runtime configuration values for the bot."""

    token: str | None
    readme_url: str
    kofi_url: str
    config_file: Path
    audio_file: Path
    ffmpeg_path: Path


def load_settings() -> Settings:
    """Load strongly-typed settings from environment variables."""
    project_root = Path(__file__).resolve().parent.parent

    token = os.getenv("DISCORD_BOT_TOKEN")
    readme_url = os.getenv(
        "LIZARD_README_URL", "https://github.com/yourname/Lizard#readme"
    )
    kofi_url = os.getenv("LIZARD_KOFI_URL", "https://ko-fi.com/yourname")

    config_file = project_root / "guild_configs.json"
    audio_file = project_root / "lizzard-1.mp3"
    ffmpeg_path = project_root / "ffmpeg.exe"

    return Settings(
        token=token,
        readme_url=readme_url,
        kofi_url=kofi_url,
        config_file=config_file,
        audio_file=audio_file,
        ffmpeg_path=ffmpeg_path,
    )


def create_intents() -> discord.Intents:
    """Create and configure Discord intents for the bot."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True
    return intents


__all__ = ["Settings", "load_settings", "create_intents", "logger"]
