from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

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
    def resolve_kidnap_channel(
        guild: discord.Guild, guild_config: Dict[str, any]
    ) -> Optional[discord.VoiceChannel]:
        channel_id = guild_config.get("kidnap_channel_id") or guild_config.get("afk_channel_id")
        if not channel_id:
            return None
        channel = bot.get_channel(channel_id)
        if isinstance(channel, discord.VoiceChannel):
            return channel
        return None

    @tasks.loop(seconds=10)
    async def lizard_timer() -> None:
        guild_voice_info = get_users_in_voice_channels_per_guild(bot)
        now = datetime.now()

        for guild in bot.guilds:
            guild_id = guild.id
            has_users = guild_id in guild_voice_info
            guild_config = config_store.get_guild_config(guild_id)

            if not has_users:
                if guild_id in state.guild_timers and state.guild_timers[guild_id] is not None:
                    logger.info("[%s] No users in voice channels. Timer paused.", guild.name)
                state.guild_timers[guild_id] = None
                config_store.set_guild_timer(guild_id, None)
                continue

            if guild_id not in state.guild_timers or state.guild_timers[guild_id] is None:
                min_minutes = max(1, int(guild_config.get("timer_min_minutes", settings.timer_min_minutes)))
                max_minutes = max(min_minutes, int(guild_config.get("timer_max_minutes", settings.timer_max_minutes)))
                minutes = random.randint(min_minutes, max_minutes)
                next_visit = now + timedelta(minutes=minutes)
                state.guild_timers[guild_id] = next_visit
                config_store.set_guild_timer(guild_id, next_visit)
                logger.info(
                    "[%s] Timer set for %d minutes (range %d-%d).",
                    guild.name,
                    minutes,
                    min_minutes,
                    max_minutes,
                )
                continue

            scheduled_time = state.guild_timers[guild_id]
            if not scheduled_time:
                continue

            if now >= scheduled_time:
                logger.info("[%s] Time to play! Visiting all channels...", guild.name)

                guild_info = guild_voice_info.get(guild_id)
                kidnap_channel = resolve_kidnap_channel(guild, guild_config)
                if guild_info:
                    # Check if there are any pending kidnaps for this guild
                    has_any_pending_kidnaps = False
                    if kidnap_channel:
                        for channel_info in guild_info["channels"]:
                            members = channel_info["members"]
                            for member in members:
                                pending_key = (guild.id, member.id)
                                if pending_key in state.pending_kidnaps:
                                    has_any_pending_kidnaps = True
                                    break
                            if has_any_pending_kidnaps:
                                break

                    if has_any_pending_kidnaps:
                        # Skip normal visits entirely, go straight to kidnap execution
                        logger.info(
                            "[%s] Skipping normal visits (pending kidnaps detected)",
                            guild.name,
                        )
                    else:
                        # Normal visits - play sound for all channels
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
                                await asyncio.sleep(2)

                    # Always increment visit stats for all members
                    for channel_info in guild_info["channels"]:
                        members = channel_info["members"]
                        for member in members:
                            config_store.increment_user_stat(guild.id, member.id, "visits")

                    # Execute pending kidnaps if any
                    if kidnap_channel:
                        for channel_info in guild_info["channels"]:
                            channel = channel_info["channel"]
                            members = channel_info["members"]
                            
                            for member in members:
                                pending_key = (guild.id, member.id)
                                pending = state.pending_kidnaps.get(pending_key)
                                if pending:
                                    logger.info(
                                        "Executing pending kidnap for %s",
                                        member.display_name,
                                    )
                                    success = await execute_kidnap(
                                        settings, guild, member, kidnap_channel
                                    )
                                    if success:
                                        config_store.increment_user_stat(
                                            guild.id, member.id, "kidnapped"
                                        )
                                        if pending.initiator_id:
                                            config_store.increment_user_stat(
                                                guild.id,
                                                pending.initiator_id,
                                                "kidnap_successes",
                                            )
                                        del state.pending_kidnaps[pending_key]
                                        config_store.clear_pending_kidnap(
                                            guild.id, member.id
                                        )
                                        await asyncio.sleep(settings.pending_kidnap_delay_seconds)

                    logger.info("[%s] Finished visiting all channels!", guild.name)

                state.guild_timers[guild_id] = None
                config_store.set_guild_timer(guild_id, None)

    @lizard_timer.before_loop
    async def before_lizard_timer() -> None:
        await bot.wait_until_ready()

    return lizard_timer


__all__ = ["create_lizard_timer"]
