from __future__ import annotations

import configparser
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages loading and validation of configuration from INI files."""

    def __init__(self, config_path: Path) -> None:
        """Initialize the config manager with a path to the INI file."""
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from the INI file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            self._create_default_config()
            return

        try:
            self.config.read(self.config_path, encoding='utf-8')
            logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create a default configuration if none exists."""
        self.config.clear()
        
        # Bot settings
        self.config['bot'] = {
            'command_prefix': '*',
            'activity_name': 'Lizard'
        }
        
        # URLs
        self.config['urls'] = {
            'readme_url': 'https://github.com/yourname/Lizard#readme',
            'kofi_url': 'https://ko-fi.com/yourname'
        }
        
        # File paths
        self.config['files'] = {
            'config_file': 'guild_configs.json',
            'audio_file': 'lizzard-1.mp3',
            'ffmpeg_path': 'ffmpeg.exe',
            'dice_gif': 'Diceroll.gif',
            'frames_directory': 'Frames'
        }
        
        # Text files
        self.config['text_files'] = {
            'facts_file': 'lizard_facts.txt',
            'responses_file': 'lizard_bot_responses.txt'
        }
        
        # Timer settings
        self.config['timer'] = {
            'min_visit_delay': '2',
            'max_visit_delay': '30',
            'timer_check_interval': '10'
        }
        
        # Cooldowns
        self.config['cooldowns'] = {
            'lizard_cooldown': '30',
            'kidnap_cooldown': '45'
        }
        
        # Kidnap settings
        self.config['kidnap'] = {
            'immunity_duration_minutes': '30',
            'dice_roll_success_threshold': '14',
            'dice_roll_failure_threshold': '7',
            'pending_kidnap_delay_seconds': '2'
        }
        
        # Voice settings
        self.config['voice'] = {
            'connection_timeout': '30.0',
            'playback_delay_seconds': '1',
            'disconnect_delay_seconds': '1'
        }
        
        # Reactions
        self.config['reactions'] = {
            'lizard_reaction_probability': '0.03'
        }
        
        # Messages
        self.config['messages'] = {
            'startup_message': 'lizard is lerking',
            'kidnap_success_message': '?? **FORCE KIDNAP!** {member} has been taken!',
            'kidnap_failure_message': '*lizard crawls away*',
            'kidnap_pending_message': "it'll happen, eventually",
            'kidnap_opt_out_message': '{member} has opted out of kidnaps.',
            'kidnap_opt_in_message': '{member} welcomes the kidnaps again!',
            'kidnap_channel_not_set_message': 'Kidnap channel not configured! Use `{prefix}setup kidnap #channel`.',
            'dice_roll_message': '?? Rolled: {roll}',
            'kidnap_immunity_message': '{member} has kidnap immunity for {minutes} more minutes!',
            'no_afk_channel_message': 'AFK channel not configured! Use `{prefix}setup` to configure channels.',
            'no_user_mentioned_message': 'You need to mention a user to kidnap! Example: `{prefix}kidnap @user` or `{prefix}kidnap @user !force` (admin)',
            'cant_kidnap_bot_message': "Can't kidnap bots!",
            'user_not_in_voice_message': '{member} is not in a voice channel!',
            'afk_channel_not_found_message': 'AFK channel not found!',
            'force_admin_only_message': 'Only administrators can use `!force`!',
            'no_users_voice_message': 'No users in any voice channels!',
            'lizard_visiting_all_message': '?? Lizard is visiting ALL channels with users...',
            'lizard_joining_message': '?? Joining {channel}...',
            'lizard_visited_message': '?? Lizard has visited {channel}!',
            'lizard_visited_all_message': '?? Lizard has visited: {channels}!',
            'error_joining_message': 'Failed to join channel: {error}',
            'error_tour_message': 'Error during lizard tour: {error}',
            'left_voice_message': 'Left the voice channel',
            'not_in_voice_message': "I'm not in a voice channel!",
            'stopped_playback_message': 'Stopped playback',
            'nothing_playing_message': 'Nothing is playing!'
        }

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Get a configuration value with optional fallback."""
        try:
            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            logger.warning(f"Config key {section}.{key} not found, using fallback: {fallback}")
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Get an integer configuration value."""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            logger.warning(f"Config key {section}.{key} not found or invalid, using fallback: {fallback}")
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Get a float configuration value."""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            logger.warning(f"Config key {section}.{key} not found or invalid, using fallback: {fallback}")
            return fallback

    def get_boolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get a boolean configuration value."""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            logger.warning(f"Config key {section}.{key} not found or invalid, using fallback: {fallback}")
            return fallback

    def get_section(self, section: str) -> Dict[str, str]:
        """Get all key-value pairs from a section."""
        try:
            return dict(self.config[section])
        except KeyError:
            logger.warning(f"Config section {section} not found")
            return {}

    def save_config(self) -> None:
        """Save the current configuration to the INI file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config file: {e}")

    def reload_config(self) -> None:
        """Reload configuration from the INI file."""
        self._load_config()


__all__ = ["ConfigManager"]
