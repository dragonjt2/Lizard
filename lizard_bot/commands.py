from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

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
    def get_guild_config(guild_id: int) -> Dict[str, Any]:
        return config_store.get_guild_config(guild_id)

    def resolve_kidnap_channel(
        guild: discord.Guild,
        guild_config: Dict[str, Any],
    ) -> Optional[discord.VoiceChannel]:
        channel_id = guild_config.get("kidnap_channel_id") or guild_config.get("afk_channel_id")
        if not channel_id:
            return None
        channel = bot.get_channel(channel_id)
        if isinstance(channel, discord.VoiceChannel):
            return channel
        return None

    async def resolve_pending_kidnap(
        guild: discord.Guild,
        member: discord.Member,
        target_channel: discord.VoiceChannel,
    ) -> None:
        pending_key = (guild.id, member.id)
        pending = state.pending_kidnaps.get(pending_key)
        if not pending:
            return

        success = await execute_kidnap(settings, guild, member, target_channel)
        if success:
            config_store.increment_user_stat(guild.id, member.id, "kidnapped")
            if pending.initiator_id:
                config_store.increment_user_stat(
                    guild.id,
                    pending.initiator_id,
                    "kidnap_successes",
                )
            del state.pending_kidnaps[pending_key]
            config_store.clear_pending_kidnap(guild.id, member.id)
            await asyncio.sleep(settings.pending_kidnap_delay_seconds)

    @bot.command(name="ping")
    async def ping(ctx: commands.Context) -> None:
        await ctx.send(f"Pong! 🦎 Latency: {round(bot.latency * 1000)}ms")

    @bot.command(name="help")
    async def help_command(ctx: commands.Context) -> None:
        prefix = ctx.prefix
        description_lines = [
            "**Core Commands**",
            f"`{prefix}lizard` - Summon the lizard to your voice channel or all active channels",
            f"`{prefix}kidnap @user` - Attempt a dice roll kidnap toward the configured channel",
            f"`{prefix}kidnap opt-out` / `{prefix}kidnap opt-in` - Toggle your kidnap preference",
            f"`{prefix}stats` - View weighted visit and kidnap statistics",
            f"`{prefix}timer` - Check time remaining before the next automatic visit",
            f"`{prefix}timer set <minutes>` - Admin: schedule the next automatic visit",
            f"`{prefix}setup` - Configure guild defaults (admin only)",
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
    @bot.command(name="lizard")
    @commands.cooldown(1, settings.lizard_cooldown, commands.BucketType.user)
    async def lizard_command(ctx: commands.Context) -> None:
        if ctx.author.voice and ctx.author.voice.channel:
            sender_channel = ctx.author.voice.channel
            await ctx.send(
                settings.messages.get(
                    "lizard_joining_message", "🦎 Joining {channel}..."
                ).format(channel=sender_channel.name)
            )

            try:
                await join_play_leave(sender_channel, settings)

                members = [member for member in sender_channel.members if not member.bot]
                for member in members:
                    config_store.increment_user_stat(ctx.guild.id, member.id, "visits")

                guild_config = get_guild_config(ctx.guild.id)
                kidnap_channel = resolve_kidnap_channel(ctx.guild, guild_config)

                if kidnap_channel:
                    for member in members:
                        await resolve_pending_kidnap(ctx.guild, member, kidnap_channel)

                await ctx.send(
                    settings.messages.get(
                        "lizard_visited_message", "🦎 Lizard has visited {channel}!"
                    ).format(channel=sender_channel.name)
                )
            except Exception as error:  # pragma: no cover - Discord runtime
                await ctx.send(
                    settings.messages.get(
                        "error_joining_message", "Failed to join channel: {error}"
                    ).format(error=error)
                )
        else:
            await ctx.send(
                settings.messages.get(
                    "lizard_visiting_all_message", "🦎 Lizard is visiting ALL channels with users..."
                )
            )

            voice_info = get_users_in_voice_channels(bot)
            if not voice_info:
                await ctx.send(
                    settings.messages.get(
                        "no_users_voice_message", "No users in any voice channels!"
                    )
                )
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

                        guild_config = get_guild_config(ctx.guild.id)
                        kidnap_channel = resolve_kidnap_channel(ctx.guild, guild_config)
                        if kidnap_channel:
                            for member in members:
                                await resolve_pending_kidnap(ctx.guild, member, kidnap_channel)

                        visited_channels.append(channel.name)
                        await asyncio.sleep(2)

                if visited_channels:
                    await ctx.send(
                        settings.messages.get(
                            "lizard_visited_all_message",
                            "🦎 Lizard has visited: {channels}!",
                        ).format(channels=", ".join(visited_channels))
                    )
            except Exception as error:  # pragma: no cover - Discord runtime
                await ctx.send(
                    settings.messages.get(
                        "error_tour_message", "Error during lizard tour: {error}"
                    ).format(error=error)
                )

    @bot.group(name="kidnap", invoke_without_command=True)
    @commands.cooldown(1, settings.kidnap_cooldown, commands.BucketType.user)
    async def kidnap(
        ctx: commands.Context,
        member: discord.Member | None = None,
        force_flag: str | None = None,
    ) -> None:
        guild_id = ctx.guild.id
        guild_config = get_guild_config(guild_id)
        target_channel = resolve_kidnap_channel(ctx.guild, guild_config)

        if member is None:
            await ctx.send(
                settings.messages.get(
                    "no_user_mentioned_message",
                    "You need to mention a user to kidnap! Example: `{prefix}kidnap @user` or `{prefix}kidnap @user !force` (admin)",
                ).format(prefix=ctx.prefix)
            )
            return

        if member is None:
            await ctx.send(
                settings.messages.get(
                    "no_user_mentioned_message",
                    "You need to mention a user to kidnap! Example: `{prefix}kidnap @user` or `{prefix}kidnap @user !force` (admin)",
                ).format(prefix=ctx.prefix)
            )
            return
        if member.bot:
            await ctx.send(
                settings.messages.get("cant_kidnap_bot_message", "Can't kidnap bots!")
            )
            return

        if not member.voice or not member.voice.channel:
            await ctx.send(
                settings.messages.get(
                    "user_not_in_voice_message", "{member} is not in a voice channel!"
                ).format(member=member.display_name)
            )
            return

        if not isinstance(target_channel, discord.VoiceChannel):
            await ctx.send(
                settings.messages.get(
                    "kidnap_channel_not_set_message",
                    "Kidnap channel not configured! Use `{prefix}setup kidnap #channel`.",
                ).format(prefix=ctx.prefix)
            )
            return

        preferences = config_store.get_user_preferences(guild_id, member.id)
        if preferences.get("kidnap_opt_out"):
            await ctx.send(
                settings.messages.get(
                    "kidnap_opt_out_message", "{member} has opted out of kidnaps."
                ).format(member=member.display_name)
            )
            return

        is_forced = force_flag == "!force"
        if is_forced:
            if not ctx.author.guild_permissions.administrator:
                await ctx.send(
                    settings.messages.get(
                        "force_admin_only_message", "Only administrators can use `!force`!"
                    )
                )
                return

            config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_attempts")
            success = await execute_kidnap(settings, ctx.guild, member, target_channel)
            if success:
                await ctx.send(
                    settings.messages.get(
                        "kidnap_success_message", "🦎 **FORCE KIDNAP!** {member} has been taken!"
                    ).format(member=member.mention)
                )
                config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_successes")
                config_store.increment_user_stat(guild_id, member.id, "kidnapped")
            else:
                config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_failures")
            return

        immunity_minutes = guild_config.get(
            "kidnap_immunity_minutes", settings.immunity_duration_minutes
        )
        immunity_key = (guild_id, member.id)
        now = datetime.now()
        if (
            immunity_key in state.kidnap_immunity
            and state.kidnap_immunity[immunity_key] > now
        ):
            time_left = state.kidnap_immunity[immunity_key] - now
            minutes = int(time_left.total_seconds() / 60)
            await ctx.send(
                settings.messages.get(
                    "kidnap_immunity_message",
                    "{member} has kidnap immunity for {minutes} more minutes!",
                ).format(member=member.mention, minutes=minutes)
            )
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
        if frame_path.exists():
            await dice_msg.delete()
            await ctx.send(file=discord.File(str(frame_path)))
        else:
            await ctx.send(
                settings.messages.get("dice_roll_message", "🎲 Rolled: {roll}").format(roll=roll)
            )

        config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_attempts")

        if roll <= settings.dice_roll_failure_threshold:
            await ctx.send(
                settings.messages.get(
                    "kidnap_failure_message", "*lizard crawls away*"
                )
            )
            config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_failures")
            state.kidnap_immunity[immunity_key] = now + timedelta(minutes=immunity_minutes)
        elif roll >= settings.dice_roll_success_threshold:
            success = await execute_kidnap(settings, ctx.guild, member, target_channel)
            if success:
                config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_successes")
                config_store.increment_user_stat(guild_id, member.id, "kidnapped")
            else:
                config_store.increment_user_stat(guild_id, ctx.author.id, "kidnap_failures")
        else:
            await ctx.send(
                settings.messages.get(
                    "kidnap_pending_message", "it'll happen, eventually"
                )
            )
            due_at = state.guild_timers.get(guild_id)
            if due_at is None:
                due_at = config_store.get_guild_timer(guild_id)
            pending = PendingKidnap(
                initiator_id=ctx.author.id,
                created_at=now,
                due_at=due_at,
            )
            state.pending_kidnaps[(guild_id, member.id)] = pending
            config_store.set_pending_kidnap(guild_id, member.id, ctx.author.id, due_at)

    @kidnap.command(name="opt-out")
    async def kidnap_opt_out(ctx: commands.Context) -> None:
        guild_id = ctx.guild.id
        config_store.set_user_preferences(guild_id, ctx.author.id, kidnap_opt_out=True)
        pending_key = (guild_id, ctx.author.id)
        if pending_key in state.pending_kidnaps:
            del state.pending_kidnaps[pending_key]
        config_store.clear_pending_kidnap(guild_id, ctx.author.id)
        await ctx.send(
            settings.messages.get(
                "kidnap_opt_out_message", "{member} has opted out of kidnaps."
            ).format(member=ctx.author.display_name)
        )

    @kidnap.command(name="opt-in")
    async def kidnap_opt_in(ctx: commands.Context) -> None:
        guild_id = ctx.guild.id
        config_store.set_user_preferences(guild_id, ctx.author.id, kidnap_opt_out=False)
        await ctx.send(
            settings.messages.get(
                "kidnap_opt_in_message", "{member} welcomes the kidnaps again!"
            ).format(member=ctx.author.display_name)
        )

    @bot.group(name="timer", invoke_without_command=True)
    async def timer_group(ctx: commands.Context) -> None:
        guild_id = ctx.guild.id
        guild_config = get_guild_config(guild_id)
        
        # Create embed
        embed = discord.Embed(
            title=f"🦎 Lizard Timer Status for {ctx.guild.name}",
            color=discord.Color.green()
        )

        # Timer status
        if guild_id not in state.guild_timers or state.guild_timers[guild_id] is None:
            embed.add_field(
                name="🕑 Timer",
                value="Waiting for users in voice channels",
                inline=True
            )
        else:
            time_remaining = state.guild_timers[guild_id] - datetime.now()
            if time_remaining.total_seconds() > 0:
                # Use Discord's relative timestamp format
                timestamp = int(state.guild_timers[guild_id].timestamp())
                embed.add_field(
                    name="🕑 Time Remaining",
                    value=f"<t:{timestamp}:R>",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🕑 Timer",
                    value="Expired, visiting channels soon...",
                    inline=True
                )

        # Check for pending kidnaps
        pending_kidnaps = []
        for (guild_id_key, user_id), pending in state.pending_kidnaps.items():
            if guild_id_key == guild_id:
                member = ctx.guild.get_member(user_id)
                if member:
                    pending_kidnaps.append(member.display_name)

        # Target field
        if pending_kidnaps:
            if len(pending_kidnaps) == 1:
                target_text = f"Kidnapping {pending_kidnaps[0]}"
            else:
                target_text = f"Kidnapping {len(pending_kidnaps)} users"
        else:
            target_text = "Lerking"
        
        embed.add_field(
            name="🎯 Target",
            value=target_text,
            inline=True
        )

        # Timer window
        timer_min = guild_config.get("timer_min_minutes", settings.timer_min_minutes)
        timer_max = guild_config.get("timer_max_minutes", settings.timer_max_minutes)
        embed.add_field(
            name="⏱️ Timer Window",
            value=f"{timer_min} – {timer_max} minutes",
            inline=True
        )

        # Users in voice channels
        voice_users = []
        for channel in ctx.guild.voice_channels:
            members = [member for member in channel.members if not member.bot]
            if members:
                member_names = ", ".join(member.display_name for member in members)
                voice_users.append(f"🦎 **{channel.name}**: {member_names}")

        if voice_users:
            embed.add_field(
                name="🗣️ Users in Voice Channels",
                value="\n".join(voice_users),
                inline=False
            )
        else:
            embed.add_field(
                name="🗣️ Users in Voice Channels",
                value="No users in voice channels",
                inline=False
            )

        # Kidnap channel and auto-move
        kidnap_channel = resolve_kidnap_channel(ctx.guild, guild_config)
        auto_move = guild_config.get("auto_move_enabled", True)
        
        status_text = []
        if kidnap_channel:
            status_text.append(f"🛸 **Kidnap Channel:** {kidnap_channel.mention}")
        else:
            status_text.append("🛸 **Kidnap Channel:** Not configured")
        
        status_text.append(f"🔁 **Auto-move:** {'Enabled' if auto_move else 'Disabled'}")
        
        embed.add_field(
            name="⚙️ Configuration",
            value="\n".join(status_text),
            inline=False
        )

        await ctx.send(embed=embed)

    @timer_group.command(name="set")
    @commands.has_permissions(administrator=True)
    async def timer_set(ctx: commands.Context, minutes: int) -> None:
        if minutes <= 0:
            await ctx.send("Minutes must be greater than 0.")
            return

        guild_id = ctx.guild.id
        when = datetime.now() + timedelta(minutes=minutes)
        state.guild_timers[guild_id] = when
        config_store.set_guild_timer(guild_id, when)
        await ctx.send(f"⏱️ Timer updated. Next visit in {minutes} minute(s).")

    @bot.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup(
        ctx: commands.Context,
        subcommand: str | None = None,
        *args: str,
    ) -> None:
        guild_id = ctx.guild.id
        guild_config = get_guild_config(guild_id)

        if subcommand is None:
            prefix = ctx.prefix
            current_prefix = guild_config.get("prefix") or state.guild_prefixes.get(guild_id) or prefix
            state.guild_prefixes[guild_id] = str(current_prefix)
            usage_lines = [
                f"`{prefix}setup` - Show this help message",
                f"`{prefix}setup default-text #channel` - Set default text channel",
                f"`{prefix}setup afk #temp_channel #afk_channel` - Configure auto-mover",
                f"`{prefix}setup auto-move on|off` - Toggle automatic AFK moving",
                f"`{prefix}setup kidnap #channel|none` - Set or clear kidnap destination",
                f"`{prefix}setup timer-range <min> <max>` - Set random visit window (minutes)",
                f"`{prefix}setup immunity <minutes>` - Set kidnap immunity duration",
                f"`{prefix}setup prefix <symbol>` - Change the command prefix",
            ]

            default_text_id = guild_config.get("default_text_channel_id")
            default_channel = bot.get_channel(default_text_id) if default_text_id else None
            temp_channel = bot.get_channel(guild_config.get("temp_channel_id")) if guild_config.get("temp_channel_id") else None
            afk_channel = bot.get_channel(guild_config.get("afk_channel_id")) if guild_config.get("afk_channel_id") else None
            kidnap_channel = resolve_kidnap_channel(ctx.guild, guild_config)
            auto_move = guild_config.get("auto_move_enabled", True)
            timer_min = guild_config.get("timer_min_minutes", settings.timer_min_minutes)
            timer_max = guild_config.get("timer_max_minutes", settings.timer_max_minutes)
            immunity_minutes = guild_config.get("kidnap_immunity_minutes", settings.immunity_duration_minutes)

            config_lines = [
                f"🔤 **Prefix:** `{current_prefix}`",
                "📝 **Default Text:** " + (default_channel.mention if isinstance(default_channel, discord.TextChannel) else "Not set"),
            ]

            if isinstance(temp_channel, discord.VoiceChannel) and isinstance(afk_channel, discord.VoiceChannel):
                route = f" ({temp_channel.mention} -> {afk_channel.mention})" if auto_move else ""
                config_lines.append(f"🔁 **Auto-move:** {'Enabled' if auto_move else 'Disabled'}{route}")
            else:
                config_lines.append(f"🔁 **Auto-move:** {'Enabled' if auto_move else 'Disabled'} (channels not set)")

            config_lines.append(
                "🛸 **Kidnap Channel:** "
                + (kidnap_channel.mention if isinstance(kidnap_channel, discord.VoiceChannel) else "Not set")
            )
            config_lines.append(f"⏱️ **Timer Window:** {timer_min} – {timer_max} minutes")
            config_lines.append(f"🛡️ **Immunity Duration:** {immunity_minutes} minutes")

            embed = discord.Embed(
                title=f"🦎 Setup Commands for {ctx.guild.name}",
                color=discord.Color.green(),
            )
            embed.add_field(name="Usage", value="\n".join(usage_lines), inline=False)
            embed.add_field(name="Current Configuration", value="\n".join(config_lines), inline=False)

            await ctx.send(embed=embed)
            return

        sub = subcommand.lower()
        if sub in {"default-text", "text", "default"}:
            if len(ctx.message.channel_mentions) != 1:
                await ctx.send(
                    f"❗ Please mention exactly one text channel.\n\nUsage: `{ctx.prefix}setup default-text #channel`"
                )
                return

            text_channel = ctx.message.channel_mentions[0]
            if text_channel.guild.id != guild_id:
                await ctx.send("❗ Channel must be from this server!")
                return

            config_store.set_guild_config(
                guild_id, default_text_channel_id=text_channel.id
            )
            await ctx.send(
                f"📝 **Default text channel set to {text_channel.mention}.**"
            )
            return
        if sub == "afk":
            if len(ctx.message.channel_mentions) != 2:
                await ctx.send(
                    f"❗ Please mention TEMP and AFK voice channels.\n\nUsage: `{ctx.prefix}setup afk #temp_channel #afk_channel`"
                )
                return

            temp_channel, afk_channel = ctx.message.channel_mentions[:2]
            if temp_channel.guild.id != guild_id or afk_channel.guild.id != guild_id:
                await ctx.send("❗ Channels must belong to this server!")
                return

            if not isinstance(temp_channel, discord.VoiceChannel) or not isinstance(
                afk_channel, discord.VoiceChannel
            ):
                await ctx.send("❗ Both channels must be voice channels!")
                return

            config_store.set_guild_config(
                guild_id,
                temp_channel_id=temp_channel.id,
                afk_channel_id=afk_channel.id,
            )
            await ctx.send(
                "✅ **Auto-mover configured!**\n\n"
                f"🧊 **TEMP:** {temp_channel.mention}\n"
                f"🔥 **AFK:** {afk_channel.mention}\n\n"
                f"Users joining {temp_channel.mention} will automatically be moved to {afk_channel.mention} when auto-move is enabled."
            )
            return
        if sub == "auto-move":
            if not args or args[0].lower() not in {"on", "off"}:
                await ctx.send("Usage: `{ctx.prefix}setup auto-move on` or `{ctx.prefix}setup auto-move off`")
                return
        if sub == "prefix":
            if not args:
                await ctx.send(f"Usage: `{ctx.prefix}setup prefix <symbol>`")
                return
            new_prefix = args[0].strip()
            if len(new_prefix) == 0:
                await ctx.send("Prefix cannot be empty or whitespace.")
                return
            if len(new_prefix) > 5:
                await ctx.send("Prefix must be 5 characters or fewer.")
                return
            config_store.set_guild_config(guild_id, prefix=new_prefix)
            state.guild_prefixes[guild_id] = new_prefix
            await ctx.send(f"🔤 Prefix updated to `{new_prefix}`.")
            return
        if sub == "kidnap":
            if not args:
                await ctx.send(
                    f"Usage: `{ctx.prefix}setup kidnap #channel` or `{ctx.prefix}setup kidnap none`"
                )
                return
            option = args[0].lower()
            if option in {"none", "clear", "off"}:
                config_store.set_guild_config(guild_id, kidnap_channel_id=None)
                await ctx.send(
                    "🛸 Kidnap channel cleared. Kidnaps will target the AFK channel if configured."
                )
                return

            if len(ctx.message.channel_mentions) != 1:
                await ctx.send("❗ Please mention exactly one voice channel or use `none`.")
                return
            kidnap_channel = ctx.message.channel_mentions[0]
            if kidnap_channel.guild.id != guild_id or not isinstance(
                kidnap_channel, discord.VoiceChannel
            ):
                await ctx.send("❗ Kidnap channel must be a voice channel in this server.")
                return
            config_store.set_guild_config(guild_id, kidnap_channel_id=kidnap_channel.id)
            await ctx.send(f"🛸 Kidnap channel set to {kidnap_channel.mention}.")
            return
        if sub in {"timer-range", "timer", "timer_range"}:
            if len(args) != 2:
                await ctx.send(
                    f"Usage: `{ctx.prefix}setup timer-range <min_minutes> <max_minutes>`"
                )
                return
            try:
                minimum = int(args[0])
                maximum = int(args[1])
            except ValueError:
                await ctx.send("❗ Min and max must be integers.")
                return
            if minimum <= 0 or maximum <= 0:
                await ctx.send("❗ Values must be greater than zero.")
                return
            if minimum > maximum:
                await ctx.send("❗ Minimum cannot exceed maximum.")
                return
            config_store.set_guild_config(
                guild_id,
                timer_min_minutes=minimum,
                timer_max_minutes=maximum,
            )
            await ctx.send(
                f"⏱️ Timer window updated to {minimum}–{maximum} minute(s)."
            )
            return
        if sub in {"immunity", "immunity_minutes"}:
            if len(args) != 1:
                await ctx.send(f"Usage: `{ctx.prefix}setup immunity <minutes>`")
                return
            try:
                minutes = int(args[0])
            except ValueError:
                await ctx.send("❗ Minutes must be an integer.")
                return
            if minutes <= 0:
                await ctx.send("❗ Minutes must be greater than zero.")
                return
            config_store.set_guild_config(
                guild_id, kidnap_immunity_minutes=minutes
            )
            await ctx.send(f"🛡️ Kidnap immunity duration set to {minutes} minute(s).")
            return
            try:
                minutes = int(args[0])
            except ValueError:
                await ctx.send("❗ Minutes must be an integer.")
                return
            if minutes <= 0:
                await ctx.send("❗ Minutes must be greater than zero.")
                return
            config_store.set_guild_config(
                guild_id, kidnap_immunity_minutes=minutes
            )
            await ctx.send(f"🛡️ Kidnap immunity duration set to {minutes} minute(s).")
            return

        await ctx.send(
            f"❔ Unknown subcommand: `{subcommand}`\n\nUse `{ctx.prefix}setup` to see available commands."
        )

    @bot.group(name="stats", invoke_without_command=True)
    async def stats_group(ctx: commands.Context) -> None:
        stats_data = config_store.get_guild_stats(ctx.guild.id)
        if not stats_data:
            await ctx.send(
                "🦎 No statistics yet! The lizard hasn't visited anyone in this server."
            )
            return

        total_visits = sum(user_stats.get("visits", 0) for user_stats in stats_data.values())
        total_kidnapped = sum(
            user_stats.get("kidnapped", 0) for user_stats in stats_data.values()
        )
        total_attempts = sum(
            user_stats.get("kidnap_attempts", 0) for user_stats in stats_data.values()
        )
        total_successes = sum(
            user_stats.get("kidnap_successes", 0) for user_stats in stats_data.values()
        )
        total_failures = sum(
            user_stats.get("kidnap_failures", 0) for user_stats in stats_data.values()
        )

        # Create embed
        embed = discord.Embed(
            title=f"🦎 Lizard Statistics for {ctx.guild.name}",
            color=discord.Color.green()
        )

        # Overview section
        embed.add_field(
            name="📊 Overview",
            value=f"Total Visits: {total_visits}\n"
                  f"Total Kidnapped: {total_kidnapped}\n"
                  f"Unique Users: {len(stats_data)}",
            inline=False
        )

        # Kidnap stats section
        embed.add_field(
            name="🎯 Kidnap Stats",
            value=f"Attempts: {total_attempts}\n"
                  f"Successes: {total_successes}\n"
                  f"Failures: {total_failures}",
            inline=False
        )

        # Calculate scores with correct weighting
        scoreboard = []
        for user_id, user_stats in stats_data.items():
            visits = user_stats.get("visits", 0)
            kidnapped = user_stats.get("kidnapped", 0)
            attempts = user_stats.get("kidnap_attempts", 0)
            successes = user_stats.get("kidnap_successes", 0)
            failures = user_stats.get("kidnap_failures", 0)

            if not any([visits, kidnapped, attempts, successes, failures]):
                continue

            # Use cached display name from database, fallback to current member if available
            display_name = user_stats.get("display_name")
            if not display_name:
                member = ctx.guild.get_member(int(user_id))
                display_name = member.display_name if member else f"User#{user_id[-4:]}"

            # Correct scoring: visit +1, got kidnapped -2, successfully kidnap +2, failed kidnap -2
            score = (
                visits * 1 +           # visit +1
                successes * 2 +        # successfully kidnap +2
                kidnapped * -2 +       # got kidnapped -2
                failures * -2          # failed kidnap -2
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

        # Leaderboard section
        if scoreboard:
            leaderboard_text = ""
            rank_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            
            for i, entry in enumerate(scoreboard[:5]):
                rank_emoji = rank_emojis[i] if i < len(rank_emojis) else f"{i+1}️⃣"
                leaderboard_text += (
                    f"{rank_emoji} {entry['display_name']} - {entry['score']:.0f} pts\n"
                    f"Visits: {entry['visits']} | Kidnapped: {entry['kidnapped']} | "
                    f"Attempts: {entry['attempts']} ({entry['successes']}✅/{entry['failures']}❌)\n\n"
                )
            
            embed.add_field(
                name="🏆 Leaderboard (Top 5)",
                value=leaderboard_text.strip(),
                inline=False
            )
        else:
            embed.add_field(
                name="🏆 Leaderboard (Top 5)",
                value="No qualifying activity yet!",
                inline=False
            )

        embed.set_footer(text="Stay warm and bask responsibly.")
        await ctx.send(embed=embed)

    @bot.command(name="stop")
    async def stop(ctx: commands.Context) -> None:
        if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
            ctx.guild.voice_client.stop()
            await ctx.send(
                settings.messages.get("stopped_playback_message", "Stopped playback")
            )
        else:
            await ctx.send(
                settings.messages.get("nothing_playing_message", "Nothing is playing!")
            )


__all__ = ["register_commands"]
