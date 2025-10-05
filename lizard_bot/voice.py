from __future__ import annotations

import asyncio
from typing import Dict, List

import discord

from .settings import Settings, logger


def get_users_in_voice_channels(bot: discord.Client) -> List[Dict[str, object]]:
    users_info: List[Dict[str, object]] = []
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            members = [member for member in channel.members if not member.bot]
            if members:
                users_info.append({"channel": channel, "members": members, "guild": guild})
    return users_info


def get_users_in_voice_channels_per_guild(bot: discord.Client) -> Dict[int, Dict[str, object]]:
    guild_voice_info: Dict[int, Dict[str, object]] = {}
    for guild in bot.guilds:
        channels_with_users = []
        for channel in guild.voice_channels:
            members = [member for member in channel.members if not member.bot]
            if members:
                channels_with_users.append({"channel": channel, "members": members})
        if channels_with_users:
            guild_voice_info[guild.id] = {"guild": guild, "channels": channels_with_users}
    return guild_voice_info


async def join_play_leave(channel: discord.VoiceChannel, settings: Settings) -> None:
    try:
        if channel.guild.voice_client:
            await channel.guild.voice_client.disconnect(force=True)
            await asyncio.sleep(1)

        voice_client = await channel.connect(
            timeout=settings.connection_timeout, reconnect=False, self_deaf=False, self_mute=False
        )
        logger.info("Joined %s in %s", channel.name, channel.guild.name)

        await channel.guild.me.edit(mute=False, deafen=False)
        await asyncio.sleep(settings.playback_delay_seconds)

        if not settings.audio_file.exists():
            logger.error("Audio file not found: %s", settings.audio_file)
            await voice_client.disconnect(force=True)
            return

        ffmpeg_path = settings.ffmpeg_path
        if not ffmpeg_path.exists():
            logger.warning("FFmpeg executable not found at %s", ffmpeg_path)
            executable = str(ffmpeg_path)
        else:
            executable = str(ffmpeg_path)

        audio_source = discord.FFmpegPCMAudio(
            str(settings.audio_file), executable=executable
        )

        def after_playback(error: Exception | None) -> None:
            if error:
                logger.error("Playback error: %s", error)
            else:
                logger.info("Playback finished successfully")

        voice_client.play(audio_source, after=after_playback)
        logger.info("Playing %s", settings.audio_file.name)

        while voice_client.is_playing():
            await asyncio.sleep(1)

        await asyncio.sleep(settings.disconnect_delay_seconds)
        await voice_client.disconnect(force=True)
        logger.info("Left %s", channel.name)

    except asyncio.TimeoutError:
        logger.error("Voice connection timeout")
    except discord.ClientException as error:
        logger.error("ClientException: %s", error)
    except Exception as error:  # pragma: no cover - logging branch
        logger.error("Error in join_play_leave: %s", error)


async def execute_kidnap(
    settings: Settings,
    guild: discord.Guild,
    member: discord.Member,
    afk_channel: discord.VoiceChannel,
) -> bool:
    try:
        if not member.voice or not member.voice.channel:
            return False

        victim_channel = member.voice.channel

        if guild.voice_client:
            await guild.voice_client.disconnect(force=True)
            await asyncio.sleep(1)

        voice_client = await victim_channel.connect(
            timeout=settings.connection_timeout, reconnect=False, self_deaf=False, self_mute=False
        )
        logger.info("Joined %s to kidnap %s", victim_channel.name, member.display_name)

        await guild.me.edit(mute=False, deafen=False)
        await asyncio.sleep(settings.playback_delay_seconds)

        if settings.audio_file.exists():
            ffmpeg_path = settings.ffmpeg_path
            executable = str(ffmpeg_path)
            if not ffmpeg_path.exists():
                logger.warning("FFmpeg executable not found at %s", ffmpeg_path)
            audio_source = discord.FFmpegPCMAudio(str(settings.audio_file), executable=executable)

            def after_playback(error: Exception | None) -> None:
                if error:
                    logger.error("Kidnap playback error: %s", error)

            voice_client.play(audio_source, after=after_playback)
            logger.info("Playing kidnap sound for %s", member.display_name)

            while voice_client.is_playing():
                await asyncio.sleep(1)

        await member.move_to(afk_channel)
        logger.info("Moved %s to AFK channel", member.display_name)

        await guild.me.move_to(afk_channel)
        await asyncio.sleep(settings.disconnect_delay_seconds)

        await voice_client.disconnect(force=True)
        logger.info("Kidnap complete for %s", member.display_name)

        return True

    except Exception as error:  # pragma: no cover - logging branch
        logger.error("Error during kidnap execution: %s", error)
        if guild.voice_client:
            await guild.voice_client.disconnect(force=True)
        return False


__all__ = [
    "execute_kidnap",
    "get_users_in_voice_channels",
    "get_users_in_voice_channels_per_guild",
    "join_play_leave",
]
