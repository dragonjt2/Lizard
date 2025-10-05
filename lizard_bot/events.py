from __future__ import annotations

import random
from typing import Callable

import discord
from discord.ext import commands

from .state import BotState
from .settings import Settings, logger
from .text_cache import TextCache
from .storage.base import BaseGuildConfigStore


def register_events(
    bot: commands.Bot,
    state: BotState,
    settings: Settings,
    text_cache: TextCache,
    config_store: BaseGuildConfigStore,
    start_timer: Callable[[], None],
) -> None:
    @bot.event
    async def on_ready() -> None:  # pragma: no cover - Discord runtime
        print(f"{bot.user} has connected to Discord!")
        print(f"Bot is in {len(bot.guilds)} guild(s)")
        print("Bot is ready to receive commands!")

        activity = discord.CustomActivity(name="Lizard")
        await bot.change_presence(activity=activity)
        print("Bot status set to: Lizard")

        if not discord.opus.is_loaded():
            print("WARNING: Opus library not loaded. Voice may not work properly.")
        else:
            print("Opus library loaded successfully")

        start_timer()
        print("Lizard timer started (per-guild)")

        configs = config_store.load_all()
        if configs:
            print(f"Configured guilds: {len(configs)}")
            for guild_id in configs:
                guild = bot.get_guild(int(guild_id))
                if guild:
                    print(f"  - {guild.name}: Auto-mover enabled")
        else:
            print("No guilds configured yet. Use *setup to configure per-guild settings.")

        for guild in bot.guilds:
            config = config_store.get_guild_config(guild.id)
            default_text_id = config.get("default_text_channel_id")

            if default_text_id:
                channel = bot.get_channel(default_text_id)
                if channel and channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send("lizard is lerking")
                        logger.info(
                            "Sent startup message to %s in %s", channel.name, guild.name
                        )
                        continue
                    except Exception:  # pragma: no cover - Discord runtime
                        pass

            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send("lizard is lerking")
                        logger.info(
                            "Sent startup message to %s in %s (fallback)",
                            channel.name,
                            guild.name,
                        )
                        break
                    except Exception:  # pragma: no cover - Discord runtime
                        continue

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author == bot.user:
            return

        if random.random() < 0.03:
            try:
                await message.add_reaction("🦎")
            except Exception:  # pragma: no cover - Discord runtime
                pass

        if bot.user and bot.user in message.mentions:
            try:
                if "fact" in message.content.lower():
                    facts = text_cache.get_lines("facts")
                    if facts:
                        fact = random.choice(facts)
                        await message.reply(f"🦎 **Lizard Fact:** {fact}")
                        logger.info(
                            "Sent fact to %s: %s", message.author.display_name, fact
                        )
                    else:
                        await message.reply("Fact file not found. Hiss.")
                        logger.warning("lizard_facts.txt not found")
                else:
                    lines = text_cache.get_lines("responses")
                    if lines:
                        response = random.choice(lines)
                        await message.reply(response)
                        logger.info(
                            "Responded to mention from %s: %s",
                            message.author.display_name,
                            response,
                        )
                    else:
                        await message.reply("Hiss. (Response file not found)")
                        logger.warning("lizard_bot_responses.txt not found")
            except Exception as error:
                logger.error("Error handling mention: %s", error)
                await message.reply("Hiss?")

        await bot.process_commands(message)

    @bot.event
    async def on_command_error(ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            retry_after = max(1, int(error.retry_after))
            command_name = ctx.command.qualified_name if ctx.command else "unknown"
            await ctx.send(f"Slow down! Try again in {retry_after} seconds.")
            logger.info(
                "Cooldown triggered for %s by %s", command_name, ctx.author.display_name
            )
            return

        logger.error("Command error: %s", error)
        raise error

    @bot.event
    async def on_voice_state_update(
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member == bot.user and after.channel is None:
            logger.info("Bot was disconnected from voice channel")
            return

        if after.channel and not member.bot:
            guild_config = config_store.get_guild_config(member.guild.id)
            temp_channel_id = guild_config.get("temp_channel_id")
            afk_channel_id = guild_config.get("afk_channel_id")

            if temp_channel_id and afk_channel_id and after.channel.id == temp_channel_id:
                afk_channel = bot.get_channel(afk_channel_id)
                if isinstance(afk_channel, discord.VoiceChannel):
                    try:
                        await member.move_to(afk_channel)
                        logger.info(
                            "Moved %s from TEMP to AFK channel in %s",
                            member.display_name,
                            member.guild.name,
                        )
                    except discord.HTTPException as error:
                        logger.error("Failed to move %s: %s", member.display_name, error)
                    except Exception as error:  # pragma: no cover - Discord runtime
                        logger.error("Error moving user: %s", error)


__all__ = ["register_events"]
