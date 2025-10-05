from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from .state import BotState
from .settings import Settings
from .storage.base import BaseGuildConfigStore
from .voice import execute_kidnap, get_users_in_voice_channels, join_play_leave


def register_commands(
    bot: commands.Bot,
    state: BotState,
    settings: Settings,
    config_store: BaseGuildConfigStore,
) -> None:
    @bot.command(name="ping")
    async def ping(ctx: commands.Context) -> None:
        await ctx.send(f"Pong! 🏓 Latency: {round(bot.latency * 1000)}ms")

    @bot.command(name="help")
    async def help_command(ctx: commands.Context) -> None:
        description_lines = [
            "**Core Commands**",
            "`*setup` - Configure default text and AFK channels (admin only)",
            "`*lizard` - Summon the lizard to your channel or all active channels",
            "`*kidnap @user` - Attempt a dice roll kidnap toward the AFK channel",
            "`*stats` - View visit and kidnap statistics",
            "`*timer` - Check time remaining before the next automatic visit",
            "`*leave` - Disconnect the bot from voice",
        ]

        embed = discord.Embed(
            title="Lizard Bot Help",
            description="\n".join(description_lines),
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Resources",
            value=f"[README]({settings.readme_url})\n[Ko-fi Support]({settings.kofi_url})",
            inline=False,
        )
        embed.set_footer(text="Stay warm and bask responsibly.")

        await ctx.send(embed=embed)

    @bot.command(name="leave")
    async def leave(ctx: commands.Context) -> None:
        if ctx.guild.voice_client:
            try:
                await ctx.guild.voice_client.disconnect(force=True)
                await ctx.send("Left the voice channel")
            except Exception as error:
                await ctx.send(f"Error leaving channel: {error}")
        else:
            await ctx.send("I'm not in a voice channel!")

    @bot.command(name="lizard")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def lizard_command(ctx: commands.Context) -> None:
        if ctx.author.voice and ctx.author.voice.channel:
            sender_channel = ctx.author.voice.channel
            await ctx.send(f"🦎 Joining {sender_channel.name}...")

            try:
                await join_play_leave(sender_channel, settings)

                members = [member for member in sender_channel.members if not member.bot]
                for member in members:
                    config_store.increment_user_stat(ctx.guild.id, member.id, "visits")

                guild_config = config_store.get_guild_config(ctx.guild.id)
                afk_channel_id = guild_config.get("afk_channel_id")
                if afk_channel_id:
                    afk_channel = bot.get_channel(afk_channel_id)
                    if isinstance(afk_channel, discord.VoiceChannel):
                        for member in members:
                            pending_key = (ctx.guild.id, member.id)
                            if pending_key in state.pending_kidnaps:
                                success = await execute_kidnap(
                                    settings, ctx.guild, member, afk_channel
                                )
                                if success:
                                    del state.pending_kidnaps[pending_key]
                                    await asyncio.sleep(2)

                await ctx.send(f"🦎 Lizard has visited {sender_channel.name}!")
            except Exception as error:
                await ctx.send(f"Failed to join channel: {error}")
        else:
            await ctx.send("🦎 Lizard is visiting ALL channels with users...")

            voice_info = get_users_in_voice_channels(bot)
            if not voice_info:
                await ctx.send("No users in any voice channels!")
                return

            try:
                visited_channels = []
                for channel_info in voice_info:
                    channel = channel_info["channel"]
                    members = [member for member in channel.members if not member.bot]

                    if members and channel.guild.id == ctx.guild.id:
                        await join_play_leave(channel, settings)

                        for member in members:
                            config_store.increment_user_stat(ctx.guild.id, member.id, "visits")

                        guild_config = config_store.get_guild_config(ctx.guild.id)
                        afk_channel_id = guild_config.get("afk_channel_id")
                        if afk_channel_id:
                            afk_channel = bot.get_channel(afk_channel_id)
                            if isinstance(afk_channel, discord.VoiceChannel):
                                for member in members:
                                    pending_key = (ctx.guild.id, member.id)
                                    if pending_key in state.pending_kidnaps:
                                        success = await execute_kidnap(
                                            settings, ctx.guild, member, afk_channel
                                        )
                                        if success:
                                            del state.pending_kidnaps[pending_key]
                                            await asyncio.sleep(2)

                        visited_channels.append(channel.name)
                        await asyncio.sleep(2)

                if visited_channels:
                    await ctx.send(f"🦎 Lizard has visited: {', '.join(visited_channels)}!")
            except Exception as error:
                await ctx.send(f"Error during lizard tour: {error}")

    @bot.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup(ctx: commands.Context, subcommand: str | None = None, *args: str) -> None:
        guild_id = ctx.guild.id

        if subcommand is None:
            config = config_store.get_guild_config(guild_id)

            info = [
                f"**🦎 Setup Commands for {ctx.guild.name}**",
                "",
                "**Usage:**",
                "`*setup` - Show this help message",
                "`*setup default-text #channel` - Set default text channel",
                "`*setup afk #temp_channel #afk_channel` - Configure auto-mover",
                "",
                "**Current Configuration:**",
            ]

            default_text_id = config.get("default_text_channel_id")
            if default_text_id:
                default_channel = bot.get_channel(default_text_id)
                info.append(
                    "📝 **Default Text:** "
                    + (default_channel.mention if default_channel else "Channel not found")
                )
            else:
                info.append("📝 **Default Text:** Not set")

            temp_channel = bot.get_channel(config.get("temp_channel_id")) if config.get("temp_channel_id") else None
            afk_channel = bot.get_channel(config.get("afk_channel_id")) if config.get("afk_channel_id") else None

            if isinstance(temp_channel, discord.VoiceChannel) and isinstance(afk_channel, discord.VoiceChannel):
                info.append(f"🚪 **Auto-mover:** {temp_channel.mention} → {afk_channel.mention}")
            else:
                info.append("🚪 **Auto-mover:** Not set")

            await ctx.send("\n".join(info))
            return

        if subcommand.lower() in {"default-text", "text", "default"}:
            if len(ctx.message.channel_mentions) != 1:
                await ctx.send(
                    "❌ Please mention exactly one text channel.\n\nUsage: `*setup default-text #channel`"
                )
                return

            text_channel = ctx.message.channel_mentions[0]
            if text_channel.guild.id != guild_id:
                await ctx.send("❌ Channel must be from this server!")
                return

            config_store.set_guild_config(guild_id, default_text_channel_id=text_channel.id)

            await ctx.send(
                "✅ **Default text channel set!**\n\n"
                f"📝 **Channel:** {text_channel.mention}\n\n"
                "Bot startup messages will be sent here."
            )
            return

        if subcommand.lower() == "afk":
            channel_mentions = [ctx.guild.get_channel(mention.id) for mention in ctx.message.mentions]
            voice_channels = [channel for channel in channel_mentions if isinstance(channel, discord.VoiceChannel)]

            if len(voice_channels) != 2:
                await ctx.send(
                    "❌ Please mention exactly two voice channels.\n\nUsage: `*setup afk #temp_channel #afk_channel`"
                )
                return

            temp_channel, afk_channel = voice_channels
            if temp_channel.guild.id != guild_id or afk_channel.guild.id != guild_id:
                await ctx.send("❌ Channels must be from this server!")
                return

            config_store.set_guild_config(
                guild_id, temp_channel_id=temp_channel.id, afk_channel_id=afk_channel.id
            )

            await ctx.send(
                "✅ **Auto-mover configured!**\n\n"
                f"🚪 **TEMP:** {temp_channel.mention}\n"
                f"🚪 **AFK:** {afk_channel.mention}\n\n"
                f"Users joining {temp_channel.mention} will automatically be moved to {afk_channel.mention}"
            )
            return

        await ctx.send(
            f"❌ Unknown subcommand: `{subcommand}`\n\nUse `*setup` to see available commands."
        )

    @bot.command(name="kidnap")
    @commands.cooldown(1, 45, commands.BucketType.user)
    async def kidnap(
        ctx: commands.Context,
        member: discord.Member | None = None,
        force_flag: str | None = None,
    ) -> None:
        guild_config = config_store.get_guild_config(ctx.guild.id)
        afk_channel_id = guild_config.get("afk_channel_id")

        if not afk_channel_id:
            await ctx.send("AFK channel not configured! Use `*setup` to configure channels.")
            return

        if member is None:
            await ctx.send("You need to mention a user to kidnap! Example: `*kidnap @user` or `*kidnap @user !force` (admin)")
            return

        if member.bot:
            await ctx.send("Can't kidnap bots!")
            return

        if not member.voice or not member.voice.channel:
            await ctx.send(f"{member.display_name} is not in a voice channel!")
            return

        afk_channel = bot.get_channel(afk_channel_id)
        if not isinstance(afk_channel, discord.VoiceChannel):
            await ctx.send("AFK channel not found!")
            return

        is_forced = force_flag == "!force"
        if is_forced:
            if not ctx.author.guild_permissions.administrator:
                await ctx.send("Only administrators can use `!force`!")
                return

            success = await execute_kidnap(settings, ctx.guild, member, afk_channel)
            if success:
                await ctx.send(f"🦎 **FORCE KIDNAP!** {member.mention} has been taken!")
                config_store.increment_user_stat(ctx.guild.id, member.id, "kidnaps")
            return

        immunity_key = (ctx.guild.id, member.id)
        now = datetime.now()
        if immunity_key in state.kidnap_immunity and state.kidnap_immunity[immunity_key] > now:
            time_left = state.kidnap_immunity[immunity_key] - now
            minutes = int(time_left.total_seconds() / 60)
            await ctx.send(f"{member.mention} has kidnap immunity for {minutes} more minutes!")
            return

        assets_root = settings.audio_file.parent
        gif_path = assets_root / "Diceroll.gif"
        if not gif_path.exists():
            await ctx.send("Diceroll.gif not found!")
            return

        dice_msg = await ctx.send(file=discord.File(str(gif_path)))
        await asyncio.sleep(2)

        roll = random.randint(1, 20)

        frames_dir = assets_root / "frames"
        if not frames_dir.exists():
            frames_dir = assets_root / "Frames"
        frame_path = frames_dir / f"{roll}.png"
        frame_exists = frame_path.exists()

        if frame_exists:
            await dice_msg.delete()
            await ctx.send(file=discord.File(str(frame_path)))
        else:
            await ctx.send(f"🎲 Rolled: {roll}")

        if roll <= 7:
            await ctx.send("*lizard crawls away*")
            state.kidnap_immunity[immunity_key] = now + timedelta(minutes=30)
        elif roll >= 14:
            success = await execute_kidnap(settings, ctx.guild, member, afk_channel)
            if success:
                config_store.increment_user_stat(ctx.guild.id, member.id, "kidnaps")
        else:
            await ctx.send("it'll happen, eventually")
            state.pending_kidnaps[(ctx.guild.id, member.id)] = ctx.author.id

    @bot.command(name="stats")
    async def stats(ctx: commands.Context) -> None:
        stats_data = config_store.get_guild_stats(ctx.guild.id)
        if not stats_data:
            await ctx.send("📊 No statistics yet! The lizard hasn't visited anyone in this server.")
            return

        total_visits = sum(user_stats.get("visits", 0) for user_stats in stats_data.values())
        total_kidnaps = sum(user_stats.get("kidnaps", 0) for user_stats in stats_data.values())

        info = [
            f"**🦎 Lizard Statistics for {ctx.guild.name}**",
            "",
            f"**Total Visits:** {total_visits}",
            f"**Total Kidnaps:** {total_kidnaps}",
            f"**Unique Users Tracked:** {len(stats_data)}",
            "",
            "**🏆 Top 3 Most Visited:**",
        ]

        leaderboard = []
        for user_id, user_stats in stats_data.items():
            visits = user_stats.get("visits", 0)
            kidnaps = user_stats.get("kidnaps", 0)
            if visits > 0 or kidnaps > 0:
                member = ctx.guild.get_member(int(user_id))
                if member:
                    leaderboard.append({"member": member, "visits": visits, "kidnaps": kidnaps})

        leaderboard.sort(key=lambda entry: entry["visits"], reverse=True)

        if leaderboard:
            medals = ["🥇", "🥈", "🥉"]
            for index, entry in enumerate(leaderboard[:3]):
                medal = medals[index]
                info.append(
                    f"{medal} **{entry['member'].display_name}** - {entry['visits']} visits, {entry['kidnaps']} kidnaps"
                )
        else:
            info.append("No one yet!")

        await ctx.send("\n".join(info))

    @bot.command(name="timer")
    async def timer_status(ctx: commands.Context) -> None:
        guild_id = ctx.guild.id
        info = [f"**🦎 Lizard Timer Status for {ctx.guild.name}:**", ""]

        if guild_id not in state.guild_timers or state.guild_timers[guild_id] is None:
            info.append("⏸️ **Timer:** Waiting for users in voice channels")
        else:
            time_remaining = state.guild_timers[guild_id] - datetime.now()
            if time_remaining.total_seconds() > 0:
                minutes = int(time_remaining.total_seconds() / 60)
                seconds = int(time_remaining.total_seconds() % 60)
                info.append(f"⏱️ **Time Remaining:** {minutes}m {seconds}s")
                info.append("🎯 **Target:** Will visit ALL channels in this server with users")
            else:
                info.append("⏰ **Timer:** Expired, visiting channels soon...")

        info.append("")
        info.append("**👥 Users in Voice Channels (This Server):**")

        has_users = False
        for channel in ctx.guild.voice_channels:
            members = [member for member in channel.members if not member.bot]
            if members:
                has_users = True
                member_names = ", ".join(member.display_name for member in members)
                info.append(f"🔊 **{channel.name}**: {member_names}")

        if not has_users:
            info.append("No users in voice channels")

        guild_config = config_store.get_guild_config(guild_id)
        if guild_config:
            info.append("")
            info.append("⚙️ **Auto-mover:** Enabled")
        else:
            info.append("")
            info.append("⚙️ **Auto-mover:** Not configured (use `*setup`)")

        await ctx.send("\n".join(info))

    @bot.command(name="stop")
    async def stop(ctx: commands.Context) -> None:
        if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
            ctx.guild.voice_client.stop()
            await ctx.send("Stopped playback")
        else:
            await ctx.send("Nothing is playing!")


__all__ = ["register_commands"]
