from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from .state import BotState, PendingKidnap
from .settings import Settings
from .storage.base import BaseGuildConfigStore
from .voice import execute_kidnap, get_users_in_voice_channels, join_play_leave


def register_commands(
    bot: commands.Bot,
    state: BotState,
    settings: Settings,
    config_store: BaseGuildConfigStore,
) -> None:
    async def resolve_pending_kidnap(
        guild: discord.Guild,
        member: discord.Member,
        afk_channel: discord.VoiceChannel,
    ) -> None:
        pending_key = (guild.id, member.id)
        pending = state.pending_kidnaps.get(pending_key)
        if not pending:
            return
        success = await execute_kidnap(settings, guild, member, afk_channel)
        if success:
            config_store.increment_user_stat(guild.id, member.id, "kidnapped", display_name=member.display_name)
            if pending.initiator_id:
                # We don't have the initiator's display name here, so we'll update it later
                config_store.increment_user_stat(
                    guild.id,
                    pending.initiator_id,
                    "kidnap_successes",
                )
            del state.pending_kidnaps[pending_key]
            config_store.clear_pending_kidnap(guild.id, member.id)
            delay = getattr(settings, "pending_kidnap_delay_seconds", 2)
            await asyncio.sleep(delay)

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
                await ctx.send(settings.messages.get("left_voice_message", "Left the voice channel"))
            except Exception as error:
                await ctx.send(f"Error leaving channel: {error}")
        else:
            await ctx.send(settings.messages.get("not_in_voice_message", "I'm not in a voice channel!"))

    @bot.command(name="lizard")
    @commands.cooldown(1, settings.lizard_cooldown, commands.BucketType.user)
    async def lizard_command(ctx: commands.Context) -> None:
        if ctx.author.voice and ctx.author.voice.channel:
            sender_channel = ctx.author.voice.channel
            await ctx.send(settings.messages.get("lizard_joining_message", "🦎 Joining {channel}...").format(channel=sender_channel.name))

            try:
                await join_play_leave(sender_channel, settings)

                members = [member for member in sender_channel.members if not member.bot]
                for member in members:
                    config_store.increment_user_stat(ctx.guild.id, member.id, "visits", display_name=member.display_name)

                guild_config = config_store.get_guild_config(ctx.guild.id)
                afk_channel_id = guild_config.get("afk_channel_id")
                if afk_channel_id:
                    afk_channel = bot.get_channel(afk_channel_id)
                    if isinstance(afk_channel, discord.VoiceChannel):
                        for member in members:
                            await resolve_pending_kidnap(ctx.guild, member, afk_channel)

                await ctx.send(settings.messages.get("lizard_visited_message", "🦎 Lizard has visited {channel}!").format(channel=sender_channel.name))
            except Exception as error:
                await ctx.send(settings.messages.get("error_joining_message", "Failed to join channel: {error}").format(error=error))
        else:
            await ctx.send(settings.messages.get("lizard_visiting_all_message", "🦎 Lizard is visiting ALL channels with users..."))

            voice_info = get_users_in_voice_channels(bot)
            if not voice_info:
                await ctx.send(settings.messages.get("no_users_voice_message", "No users in any voice channels!"))
                return

            try:
                visited_channels = []
                for channel_info in voice_info:
                    channel = channel_info["channel"]
                    members = [member for member in channel.members if not member.bot]

                    if members and channel.guild.id == ctx.guild.id:
                        await join_play_leave(channel, settings)

                        for member in members:
                            config_store.increment_user_stat(ctx.guild.id, member.id, "visits", display_name=member.display_name)

                        guild_config = config_store.get_guild_config(ctx.guild.id)
                        afk_channel_id = guild_config.get("afk_channel_id")
                        if afk_channel_id:
                            afk_channel = bot.get_channel(afk_channel_id)
                            if isinstance(afk_channel, discord.VoiceChannel):
                                for member in members:
                                    await resolve_pending_kidnap(ctx.guild, member, afk_channel)

                        visited_channels.append(channel.name)
                        await asyncio.sleep(2)

                if visited_channels:
                    await ctx.send(settings.messages.get("lizard_visited_all_message", "🦎 Lizard has visited: {channels}!").format(channels=', '.join(visited_channels)))
            except Exception as error:
                await ctx.send(settings.messages.get("error_tour_message", "Error during lizard tour: {error}").format(error=error))

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
    @commands.cooldown(1, settings.kidnap_cooldown, commands.BucketType.user)
    async def kidnap(
        ctx: commands.Context,
        member: discord.Member | None = None,
        force_flag: str | None = None,
    ) -> None:
        guild_id = ctx.guild.id
        guild_config = config_store.get_guild_config(guild_id)
        afk_channel_id = guild_config.get("afk_channel_id")

        if not afk_channel_id:
            await ctx.send(settings.messages.get("no_afk_channel_message", "AFK channel not configured! Use `*setup` to configure channels."))
            return

        if member is None:
            await ctx.send(settings.messages.get("no_user_mentioned_message", "You need to mention a user to kidnap! Example: `*kidnap @user` or `*kidnap @user !force` (admin)"))
            return

        if member.bot:
            await ctx.send(settings.messages.get("cant_kidnap_bot_message", "Can't kidnap bots!"))
            return

        is_self_kidnap = member.id == ctx.author.id

        if not member.voice or not member.voice.channel:
            await ctx.send(settings.messages.get("user_not_in_voice_message", "{member} is not in a voice channel!").format(member=member.display_name))
            return

        afk_channel = bot.get_channel(afk_channel_id)
        if not isinstance(afk_channel, discord.VoiceChannel):
            await ctx.send(settings.messages.get("afk_channel_not_found_message", "AFK channel not found!"))
            return

        preferences = config_store.get_user_preferences(guild_id, member.id)
        if preferences.get("kidnap_opt_out"):
            await ctx.send(settings.messages.get("kidnap_opt_out_message", "🦎 {member} has opted out of kidnaps.").format(member=member.display_name))
            return

        is_forced = force_flag == "!force"
        if is_forced:
            if not ctx.author.guild_permissions.administrator:
                await ctx.send(settings.messages.get("force_admin_only_message", "Only administrators can use `!force`!"))
                return

            # Force kidnaps don't affect stats
            success = await execute_kidnap(settings, ctx.guild, member, afk_channel)
            if success:
                if is_self_kidnap:
                    await ctx.send("🦎 **FORCE SELF-KIDNAP!** You've been taken!")
                else:
                    await ctx.send(settings.messages.get("kidnap_success_message", "🦎 **FORCE KIDNAP!** {member} has been taken!").format(member=member.mention))
            return

        immunity_key = (guild_id, member.id)
        now = datetime.now()
        if immunity_key in state.kidnap_immunity and state.kidnap_immunity[immunity_key] > now:
            time_left = state.kidnap_immunity[immunity_key] - now
            minutes = int(time_left.total_seconds() / 60)
            await ctx.send(settings.messages.get("kidnap_immunity_message", "{member} has kidnap immunity for {minutes} more minutes!").format(member=member.mention, minutes=minutes))
            return

        gif_path = settings.dice_gif
        if not gif_path.exists():
            await ctx.send("Diceroll.gif not found!")
            return

        dice_msg = await ctx.send(file=discord.File(str(gif_path)))
        await asyncio.sleep(2)

        roll = random.randint(1, 20)

        frames_dir = settings.frames_directory
        frame_path = frames_dir / f"{roll}.png"
        frame_exists = frame_path.exists()

        if frame_exists:
            await dice_msg.delete()
            await ctx.send(file=discord.File(str(frame_path)))
        else:
            await ctx.send(settings.messages.get("dice_roll_message", "🎲 Rolled: {roll}").format(roll=roll))

        # Only track stats for non-self kidnaps
        if not is_self_kidnap:
            config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_attempts", display_name=ctx.author.display_name)

        if roll <= settings.dice_roll_failure_threshold:
            await ctx.send(settings.messages.get("kidnap_failure_message", "*lizard crawls away*"))
            if not is_self_kidnap:
                config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_failures", display_name=ctx.author.display_name)
            state.kidnap_immunity[immunity_key] = now + timedelta(minutes=settings.immunity_duration_minutes)
        elif roll >= settings.dice_roll_success_threshold:
            success = await execute_kidnap(settings, ctx.guild, member, afk_channel)
            if success:
                if is_self_kidnap:
                    await ctx.send("🦎 **SELF-KIDNAP!** You've been taken!")
                else:
                    config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_successes", display_name=ctx.author.display_name)
                    config_store.increment_user_stat(guild_id, member.id, "kidnapped", display_name=member.display_name)
            else:
                if not is_self_kidnap:
                    config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_failures", display_name=ctx.author.display_name)
        else:
            await ctx.send(settings.messages.get("kidnap_pending_message", "it'll happen, eventually"))
            if not is_self_kidnap:
                due_at = state.guild_timers.get(guild_id)
                if due_at is None:
                    due_at = config_store.get_guild_timer(guild_id)
                pending = PendingKidnap(initiator_id=ctx.author.id, created_at=now, due_at=due_at)
                state.pending_kidnaps[(guild_id, member.id)] = pending
                config_store.set_pending_kidnap(guild_id, member.id, ctx.author.id, due_at)

    @bot.command(name="stats")
    async def stats(ctx: commands.Context) -> None:
        stats_data = config_store.get_guild_stats(ctx.guild.id)
        if not stats_data:
            embed = discord.Embed(
                title="🦎 Lizard Statistics",
                description="No statistics yet! The lizard hasn't visited anyone in this server.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            return

        total_visits = sum(user_stats.get("visits", 0) for user_stats in stats_data.values())
        total_kidnapped = sum(user_stats.get("kidnapped", 0) for user_stats in stats_data.values())
        total_attempts = sum(user_stats.get("kidnap_attempts", 0) for user_stats in stats_data.values())
        total_successes = sum(user_stats.get("kidnap_successes", 0) for user_stats in stats_data.values())
        total_failures = sum(user_stats.get("kidnap_failures", 0) for user_stats in stats_data.values())

        # Create the main embed
        embed = discord.Embed(
            title=f"🦎 Lizard Statistics for {ctx.guild.name}",
            color=discord.Color.green(),
        )

        # Add overview fields
        embed.add_field(
            name="📊 Overview",
            value=f"**Total Visits:** {total_visits}\n"
                  f"**Total Kidnapped:** {total_kidnapped}\n"
                  f"**Unique Users:** {len(stats_data)}",
            inline=True
        )

        embed.add_field(
            name="🎯 Kidnap Stats",
            value=f"**Attempts:** {total_attempts}\n"
                  f"**Successes:** {total_successes}\n"
                  f"**Failures:** {total_failures}",
            inline=True
        )

        # Calculate leaderboard
        scoreboard = []
        for user_id, user_stats in stats_data.items():
            visits = user_stats.get("visits", 0)
            kidnapped = user_stats.get("kidnapped", 0)
            attempts = user_stats.get("kidnap_attempts", 0)
            successes = user_stats.get("kidnap_successes", 0)
            failures = user_stats.get("kidnap_failures", 0)

            if not any([visits, kidnapped, attempts, successes, failures]):
                continue

            # Try to get member, but don't filter out if they're offline
            member = ctx.guild.get_member(int(user_id))
            if member:
                display_name = member.display_name
                # Update the stored display name while we have it
                if not user_stats.get("display_name"):
                    config_store.increment_user_stat(ctx.guild.id, int(user_id), "visits", amount=0, display_name=member.display_name)
            else:
                # User is offline or left the server, use stored name or fallback
                stored_name = user_stats.get("display_name")
                if stored_name and stored_name != "None" and stored_name.strip():
                    display_name = stored_name
                else:
                    # Try to get a more user-friendly fallback
                    try:
                        # Extract last 4 digits of user ID for a more readable fallback
                        user_id_str = str(user_id)
                        short_id = user_id_str[-4:] if len(user_id_str) > 4 else user_id_str
                        display_name = f"User#{short_id}"
                    except:
                        display_name = f"User {user_id}"

            score = (
                visits * 1          # Visits are +1
                + successes * 2     # Success on others is +2
                - kidnapped * 2     # Kidnaps to user are -2
                - failures * 1      # Failed on others is -1
            )

            scoreboard.append(
                {
                    "display_name": display_name,
                    "visits": visits,
                    "kidnapped": kidnapped,
                    "attempts": attempts,
                    "successes": successes,
                    "failures": failures,
                    "score": score,
                }
            )

        scoreboard.sort(key=lambda entry: entry["score"], reverse=True)

        # Add leaderboard field
        if scoreboard:
            leaderboard_text = []
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            
            for i, entry in enumerate(scoreboard[:5]):
                medal = medals[i] if i < len(medals) else "•"
                leaderboard_text.append(
                    f"{medal} **{entry['display_name']}** - {entry['score']} pts\n"
                    f"   Visits: {entry['visits']} | Kidnapped: {entry['kidnapped']} | "
                    f"Attempts: {entry['attempts']} ({entry['successes']}✅/{entry['failures']}❌)"
                )
            
            embed.add_field(
                name="🏆 Leaderboard (Top 5)",
                value="\n".join(leaderboard_text),
                inline=False
            )
        else:
            embed.add_field(
                name="🏆 Leaderboard",
                value="No qualifying activity yet!",
                inline=False
            )

        # Add footer
        embed.set_footer(text="Stay warm and bask responsibly.")

        await ctx.send(embed=embed)

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
            await ctx.send(settings.messages.get("stopped_playback_message", "Stopped playback"))
        else:
            await ctx.send(settings.messages.get("nothing_playing_message", "Nothing is playing!"))


__all__ = ["register_commands"]
