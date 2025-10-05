from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

import discord
from discord.ext import tasks

from .state import BotState
from .settings import Settings, logger
from .storage.base import BaseGuildConfigStore
from .voice import (
    execute_kidnap,
    get_users_in_voice_channels_per_guild,
    join_play_leave,
)


def create_lizard_timer(
    bot: discord.Client,
    state: BotState,
    settings: Settings,
    config_store: BaseGuildConfigStore,
) -> tasks.Loop:
    @tasks.loop(seconds=10)
    async def lizard_timer() -> None:
        guild_voice_info = get_users_in_voice_channels_per_guild(bot)
        now = datetime.now()

        for guild in bot.guilds:
            guild_id = guild.id
            has_users = guild_id in guild_voice_info

            if not has_users:
                if guild_id in state.guild_timers and state.guild_timers[guild_id] is not None:
                    logger.info("[%s] No users in voice channels. Timer paused.", guild.name)
                state.guild_timers[guild_id] = None
                continue

            if guild_id not in state.guild_timers or state.guild_timers[guild_id] is None:
                minutes = random.randint(2, 30)
                state.guild_timers[guild_id] = now + timedelta(minutes=minutes)
                logger.info("[%s] Timer set for %d minutes.", guild.name, minutes)
                continue

            if now >= state.guild_timers[guild_id]:
                logger.info("[%s] Time to play! Visiting all channels...", guild.name)

                guild_info = guild_voice_info.get(guild_id)
                if guild_info:
                    for channel_info in guild_info["channels"]:
                        channel = channel_info["channel"]
                        members = channel_info["members"]

                        if members:
                            logger.info(
                                "[%s] Joining %s (%d users)",
                                guild.name,
                                channel.name,
                                len(members),
                            )
                            await join_play_leave(channel, settings)

                            for member in members:
                                config_store.increment_user_stat(guild.id, member.id, "visits")

                            guild_config = config_store.get_guild_config(guild.id)
                            afk_channel_id = guild_config.get("afk_channel_id")
                            if afk_channel_id:
                                afk_channel = bot.get_channel(afk_channel_id)
                                if isinstance(afk_channel, discord.VoiceChannel):
                                    for member in members:
                                        pending_key = (guild.id, member.id)
                                        if pending_key in state.pending_kidnaps:
                                            logger.info(
                                                "Executing pending kidnap for %s",
                                                member.display_name,
                                            )
                                            success = await execute_kidnap(
                                                settings, guild, member, afk_channel
                                            )
                                            if success:
                                                del state.pending_kidnaps[pending_key]
                                                await asyncio.sleep(2)

                            await asyncio.sleep(2)

                    logger.info("[%s] Finished visiting all channels!", guild.name)

                state.guild_timers[guild_id] = None

    @lizard_timer.before_loop
    async def before_lizard_timer() -> None:
        await bot.wait_until_ready()

    return lizard_timer


__all__ = ["create_lizard_timer"]
