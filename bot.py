import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import logging
import asyncio
import random
from datetime import datetime, timedelta
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='*', intents=intents)

# Guild configuration file
CONFIG_FILE = 'guild_configs.json'

# Per-guild timer tracking: {guild_id: next_play_time}
guild_timers = {}

# Kidnap immunity tracking: {(guild_id, user_id): expiry_time}
kidnap_immunity = {}

# Pending kidnaps: {(guild_id, user_id): requester_id}
pending_kidnaps = {}

def load_guild_configs():
    """Load guild configurations from JSON file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading guild configs: {e}")
            return {}
    return {}

def save_guild_configs(configs):
    """Save guild configurations to JSON file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(configs, f, indent=2)
        logger.info("Guild configurations saved")
    except Exception as e:
        logger.error(f"Error saving guild configs: {e}")

def get_guild_config(guild_id):
    """Get configuration for a specific guild"""
    configs = load_guild_configs()
    return configs.get(str(guild_id), {})

def set_guild_config(guild_id, **kwargs):
    """Set configuration for a specific guild"""
    configs = load_guild_configs()
    if str(guild_id) not in configs:
        configs[str(guild_id)] = {'stats': {}}
    
    # Update only the provided keys
    for key, value in kwargs.items():
        configs[str(guild_id)][key] = value
    
    save_guild_configs(configs)

def increment_user_stat(guild_id, user_id, stat_type='visits'):
    """Increment a stat for a user in a guild"""
    configs = load_guild_configs()
    guild_key = str(guild_id)
    user_key = str(user_id)
    
    if guild_key not in configs:
        configs[guild_key] = {'stats': {}}
    if 'stats' not in configs[guild_key]:
        configs[guild_key]['stats'] = {}
    if user_key not in configs[guild_key]['stats']:
        configs[guild_key]['stats'][user_key] = {'visits': 0, 'kidnaps': 0}
    
    configs[guild_key]['stats'][user_key][stat_type] = configs[guild_key]['stats'][user_key].get(stat_type, 0) + 1
    save_guild_configs(configs)

def get_guild_stats(guild_id):
    """Get all stats for a guild"""
    configs = load_guild_configs()
    guild_key = str(guild_id)
    if guild_key in configs and 'stats' in configs[guild_key]:
        return configs[guild_key]['stats']
    return {}

# Load configs on startup
guild_configs = load_guild_configs()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    print('Bot is ready to receive commands!')
    
    # Set custom activity
    activity = discord.CustomActivity(name="Lizard")
    await bot.change_presence(activity=activity)
    print('Bot status set to: Lizard')
    
    # Check for voice support
    if not discord.opus.is_loaded():
        print('WARNING: Opus library not loaded. Voice may not work properly.')
    else:
        print('Opus library loaded successfully')
    
    # Start the background task
    if not lizard_timer.is_running():
        lizard_timer.start()
        print('Lizard timer started (per-guild)')
    
    # Show configured guilds
    configs = load_guild_configs()
    if configs:
        print(f'Configured guilds: {len(configs)}')
        for guild_id, config in configs.items():
            guild = bot.get_guild(int(guild_id))
            if guild:
                print(f'  - {guild.name}: Auto-mover enabled')
    else:
        print('No guilds configured yet. Use *setup to configure per-guild settings.')
    
    # Send startup message to all guilds
    for guild in bot.guilds:
        config = get_guild_config(guild.id)
        default_text_id = config.get('default_text_channel_id')
        
        # Try to use configured default text channel
        if default_text_id:
            channel = bot.get_channel(default_text_id)
            if channel and channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send("lizard is lerking")
                    logger.info(f"Sent startup message to {channel.name} in {guild.name}")
                    continue
                except:
                    pass
        
        # Fallback: Find the first text channel the bot can send messages to
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send("lizard is lerking")
                    logger.info(f"Sent startup message to {channel.name} in {guild.name} (fallback)")
                    break
                except:
                    continue

@bot.event
async def on_message(message):
    """Handle messages, especially when bot is mentioned"""
    # Don't respond to self
    if message.author == bot.user:
        return
    
    # Random lizard emoji reaction (3% chance)
    if random.random() < 0.03:
        try:
            await message.add_reaction('🦎')
        except:
            pass  # Silently fail if can't react
    
    # Check if bot is mentioned
    if bot.user in message.mentions:
        try:
            # Check if "fact" is in the message
            if 'fact' in message.content.lower():
                # Read random fact from lizard_facts.txt
                if os.path.exists('lizard_facts.txt'):
                    with open('lizard_facts.txt', 'r', encoding='utf-8') as f:
                        facts = [line.strip() for line in f.readlines() if line.strip()]
                    
                    if facts:
                        fact = random.choice(facts)
                        await message.reply(f"🦎 **Lizard Fact:** {fact}")
                        logger.info(f"Sent fact to {message.author.display_name}: {fact}")
                else:
                    await message.reply("Fact file not found. Hiss.")
                    logger.warning("lizard_facts.txt not found")
            else:
                # Regular lizard response
                if os.path.exists('lizard_bot_responses.txt'):
                    with open('lizard_bot_responses.txt', 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                    
                    if lines:
                        response = random.choice(lines)
                        await message.reply(response)
                        logger.info(f"Responded to mention from {message.author.display_name}: {response}")
                else:
                    await message.reply("Hiss. (Response file not found)")
                    logger.warning("lizard_bot_responses.txt not found")
        except Exception as e:
            logger.error(f"Error handling mention: {e}")
            await message.reply("Hiss?")
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state updates and potential disconnections"""
    if member == bot.user and after.channel is None:
        logger.info(f"Bot was disconnected from voice channel")
        return
    
    # Auto-move users from TEMP channel to AFK channel (per-guild)
    if after.channel and not member.bot:
        guild_config = get_guild_config(member.guild.id)
        temp_channel_id = guild_config.get('temp_channel_id')
        afk_channel_id = guild_config.get('afk_channel_id')
        
        if temp_channel_id and afk_channel_id:
            # If user joined the TEMP channel
            if after.channel.id == temp_channel_id:
                # Get the AFK channel
                afk_channel = bot.get_channel(afk_channel_id)
                if afk_channel:
                    try:
                        await member.move_to(afk_channel)
                        logger.info(f"Moved {member.display_name} from TEMP to AFK channel in {member.guild.name}")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to move {member.display_name}: {e}")
                    except Exception as e:
                        logger.error(f"Error moving user: {e}")

@bot.command(name='ping')
async def ping(ctx):
    """Simple ping command"""
    await ctx.send(f"Pong! 🏓 Latency: {round(bot.latency * 1000)}ms")

def get_users_in_voice_channels():
    """Get all users currently in voice channels"""
    users_info = []
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            members = [m for m in channel.members if not m.bot]
            if members:
                users_info.append({
                    'channel': channel,
                    'members': members,
                    'guild': guild
                })
    return users_info

def get_users_in_voice_channels_per_guild():
    """Get users in voice channels organized by guild"""
    guild_voice_info = {}
    for guild in bot.guilds:
        channels_with_users = []
        for channel in guild.voice_channels:
            members = [m for m in channel.members if not m.bot]
            if members:
                channels_with_users.append({
                    'channel': channel,
                    'members': members
                })
        if channels_with_users:
            guild_voice_info[guild.id] = {
                'guild': guild,
                'channels': channels_with_users
            }
    return guild_voice_info

async def join_play_leave(channel):
    """Join a voice channel, play audio, then leave"""
    try:
        # If already connected, disconnect first
        if channel.guild.voice_client:
            await channel.guild.voice_client.disconnect(force=True)
            await asyncio.sleep(1)
        
        # Connect to voice channel (not self-muted or self-deafened)
        voice_client = await channel.connect(timeout=30.0, reconnect=False, self_deaf=False, self_mute=False)
        logger.info(f"Joined {channel.name} in {channel.guild.name}")
        
        # Ensure bot is unmuted (in case the channel has default mute settings)
        await channel.guild.me.edit(mute=False, deafen=False)
        logger.info(f"Bot unmuted in {channel.name}")
        
        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)
        
        # Check if audio file exists
        if not os.path.exists("lizzard-1.mp3"):
            logger.error("Audio file not found!")
            await voice_client.disconnect(force=True)
            return
        
        # Play the audio
        ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
        audio_source = discord.FFmpegPCMAudio("lizzard-1.mp3", executable=ffmpeg_path)
        
        def after_playback(error):
            if error:
                logger.error(f'Playback error: {error}')
            else:
                logger.info('Playback finished successfully')
        
        voice_client.play(audio_source, after=after_playback)
        logger.info("Playing lizzard-1.mp3")
        
        # Wait for playback to finish
        while voice_client.is_playing():
            await asyncio.sleep(1)
        
        # Leave the channel
        await asyncio.sleep(1)
        await voice_client.disconnect(force=True)
        logger.info(f"Left {channel.name}")
        
    except asyncio.TimeoutError:
        logger.error("Voice connection timeout")
    except discord.ClientException as e:
        logger.error(f"ClientException: {e}")
    except Exception as e:
        logger.error(f"Error in join_play_leave: {e}")

@tasks.loop(seconds=10)
async def lizard_timer():
    """Background task that monitors voice channels per guild and plays audio on timer"""
    global guild_timers
    
    # Get users in voice channels organized by guild
    guild_voice_info = get_users_in_voice_channels_per_guild()
    
    # Get current time
    now = datetime.now()
    
    # Process each guild independently
    for guild in bot.guilds:
        guild_id = guild.id
        has_users = guild_id in guild_voice_info
        
        # If no users in this guild's voice channels, reset its timer
        if not has_users:
            if guild_id in guild_timers and guild_timers[guild_id] is not None:
                logger.info(f"[{guild.name}] No users in voice channels. Timer paused.")
            guild_timers[guild_id] = None
            continue
        
        # If timer not set for this guild and there are users, set a new timer
        if guild_id not in guild_timers or guild_timers[guild_id] is None:
            # Random time between 2 and 30 minutes
            minutes = random.randint(2, 30)
            guild_timers[guild_id] = now + timedelta(minutes=minutes)
            logger.info(f"[{guild.name}] Timer set for {minutes} minutes.")
            continue
        
        # Check if it's time to play for this guild
        if now >= guild_timers[guild_id]:
            logger.info(f"[{guild.name}] Time to play! Visiting all channels...")
            
            guild_info = guild_voice_info.get(guild_id)
            if guild_info:
                # Visit each channel with users in this guild
                for channel_info in guild_info['channels']:
                    channel = channel_info['channel']
                    members = channel_info['members']
                    
                    if members:
                        logger.info(f"[{guild.name}] Joining {channel.name} ({len(members)} users)")
                        await join_play_leave(channel)
                        
                        # Track stats for all users in the channel
                        for member in members:
                            increment_user_stat(guild.id, member.id, 'visits')
                        
                        # Check for pending kidnaps
                        guild_config = get_guild_config(guild.id)
                        afk_channel_id = guild_config.get('afk_channel_id')
                        if afk_channel_id:
                            afk_channel = bot.get_channel(afk_channel_id)
                            if afk_channel:
                                for member in members:
                                    pending_key = (guild.id, member.id)
                                    if pending_key in pending_kidnaps:
                                        logger.info(f"Executing pending kidnap for {member.display_name}")
                                        success = await execute_kidnap(guild, member, afk_channel)
                                        if success:
                                            del pending_kidnaps[pending_key]
                                            await asyncio.sleep(2)
                        
                        # Small delay between channels
                        await asyncio.sleep(2)
                
                logger.info(f"[{guild.name}] Finished visiting all channels!")
            
            # Reset timer for this guild
            guild_timers[guild_id] = None

@lizard_timer.before_loop
async def before_lizard_timer():
    """Wait until the bot is ready before starting the timer"""
    await bot.wait_until_ready()

@bot.command(name='leave')
async def leave(ctx):
    """Leave the voice channel"""
    if ctx.guild.voice_client:
        try:
            await ctx.guild.voice_client.disconnect(force=True)
            await ctx.send("Left the voice channel")
            logger.info("Disconnected from voice channel")
        except Exception as e:
            await ctx.send(f"Error leaving channel: {str(e)}")
            logger.error(f"Error disconnecting: {e}")
    else:
        await ctx.send("I'm not in a voice channel!")

@bot.command(name='lizard')
async def lizard_command(ctx):
    """Manually trigger the lizard - joins your channel, or all channels if you're not in one"""
    
    # Check if the sender is in a voice channel
    if ctx.author.voice and ctx.author.voice.channel:
        # Join the sender's channel specifically
        sender_channel = ctx.author.voice.channel
        await ctx.send(f"🦎 Joining {sender_channel.name}...")
        
        try:
            await join_play_leave(sender_channel)
            
            # Track stats for all users in the channel
            members = [m for m in sender_channel.members if not m.bot]
            for member in members:
                increment_user_stat(ctx.guild.id, member.id, 'visits')
            
            # Check for pending kidnaps
            guild_config = get_guild_config(ctx.guild.id)
            afk_channel_id = guild_config.get('afk_channel_id')
            if afk_channel_id:
                afk_channel = bot.get_channel(afk_channel_id)
                if afk_channel:
                    for member in members:
                        pending_key = (ctx.guild.id, member.id)
                        if pending_key in pending_kidnaps:
                            logger.info(f"Executing pending kidnap for {member.display_name}")
                            success = await execute_kidnap(ctx.guild, member, afk_channel)
                            if success:
                                del pending_kidnaps[pending_key]
                                await asyncio.sleep(2)
            
            await ctx.send(f"🦎 Lizard has visited {sender_channel.name}!")
            logger.info(f"Manual lizard command executed in {sender_channel.name} by {ctx.author.display_name}")
        except Exception as e:
            await ctx.send(f"Failed to join channel: {str(e)}")
            logger.error(f"Error in manual lizard command: {e}")
    else:
        # Not in a voice channel - trigger the timer behavior (visit all channels)
        await ctx.send("🦎 Lizard is visiting ALL channels with users...")
        
        voice_info = get_users_in_voice_channels()
        
        if not voice_info:
            await ctx.send("No users in any voice channels!")
            return
        
        try:
            # Visit each channel with users
            visited_channels = []
            for channel_info in voice_info:
                channel = channel_info['channel']
                members = [m for m in channel.members if not m.bot]
                
                if members and channel.guild.id == ctx.guild.id:  # Only visit channels in current guild
                    logger.info(f"Manual timer trigger: Joining {channel.name} in {channel.guild.name}")
                    await join_play_leave(channel)
                    
                    # Track stats for all users
                    for member in members:
                        increment_user_stat(ctx.guild.id, member.id, 'visits')
                    
                    # Check for pending kidnaps
                    guild_config = get_guild_config(ctx.guild.id)
                    afk_channel_id = guild_config.get('afk_channel_id')
                    if afk_channel_id:
                        afk_channel = bot.get_channel(afk_channel_id)
                        if afk_channel:
                            for member in members:
                                pending_key = (ctx.guild.id, member.id)
                                if pending_key in pending_kidnaps:
                                    logger.info(f"Executing pending kidnap for {member.display_name}")
                                    success = await execute_kidnap(ctx.guild, member, afk_channel)
                                    if success:
                                        del pending_kidnaps[pending_key]
                                        await asyncio.sleep(2)
                    
                    visited_channels.append(channel.name)
                    await asyncio.sleep(2)
            
            if visited_channels:
                await ctx.send(f"🦎 Lizard has visited: {', '.join(visited_channels)}!")
            
            logger.info(f"Manual timer trigger completed by {ctx.author.display_name}")
        except Exception as e:
            await ctx.send(f"Error during lizard tour: {str(e)}")
            logger.error(f"Error in manual timer trigger: {e}")

@bot.command(name='setup')
@commands.has_permissions(administrator=True)
async def setup(ctx, subcommand: str = None, *args):
    """Configure guild settings (Admin only)
    
    Usage:
    *setup - Show this help message and current config
    *setup default-text #channel - Set default text channel for bot messages
    *setup afk #temp_channel #afk_channel - Configure auto-mover channels
    """
    guild_id = ctx.guild.id
    
    # Show help if no subcommand provided
    if subcommand is None:
        config = get_guild_config(guild_id)
        
        info = [
            f"**🦎 Setup Commands for {ctx.guild.name}**",
            "",
            "**Usage:**",
            "`*setup` - Show this help message",
            "`*setup default-text #channel` - Set default text channel",
            "`*setup afk #temp_channel #afk_channel` - Configure auto-mover",
            "",
            "**Current Configuration:**"
        ]
        
        # Show default text channel
        default_text_id = config.get('default_text_channel_id')
        if default_text_id:
            default_ch = bot.get_channel(default_text_id)
            info.append(f"📝 **Default Text:** {default_ch.mention if default_ch else 'Channel not found'}")
        else:
            info.append("📝 **Default Text:** Not set")
        
        # Show AFK channels
        temp_ch = bot.get_channel(config.get('temp_channel_id')) if config.get('temp_channel_id') else None
        afk_ch = bot.get_channel(config.get('afk_channel_id')) if config.get('afk_channel_id') else None
        
        if temp_ch and afk_ch:
            info.append(f"🚪 **Auto-mover:** {temp_ch.mention} → {afk_ch.mention}")
        else:
            info.append("🚪 **Auto-mover:** Not set")
        
        await ctx.send("\n".join(info))
        return
    
    # Handle 'default-text' subcommand
    if subcommand.lower() in ['default-text', 'text', 'default']:
        if len(ctx.message.channel_mentions) != 1:
            await ctx.send("❌ Please mention exactly one text channel.\n\nUsage: `*setup default-text #channel`")
            return
        
        text_channel = ctx.message.channel_mentions[0]
        
        if text_channel.guild.id != guild_id:
            await ctx.send("❌ Channel must be from this server!")
            return
        
        # Save the configuration
        set_guild_config(guild_id, default_text_channel_id=text_channel.id)
        
        await ctx.send(
            f"✅ **Default text channel set!**\n\n"
            f"📝 **Channel:** {text_channel.mention}\n\n"
            f"Bot startup messages will be sent here."
        )
        logger.info(f"Guild {ctx.guild.name} default text channel set: {text_channel.id}")
        return
    
    # Handle 'afk' subcommand
    if subcommand.lower() == 'afk':
        voice_mentions = [m for m in ctx.message.mentions if isinstance(ctx.guild.get_channel(m.id), discord.VoiceChannel)]
        channel_mentions = [ctx.guild.get_channel(m.id) for m in ctx.message.mentions]
        voice_channels = [ch for ch in channel_mentions if isinstance(ch, discord.VoiceChannel)]
        
        if len(voice_channels) != 2:
            await ctx.send("❌ Please mention exactly two voice channels.\n\nUsage: `*setup afk #temp_channel #afk_channel`")
            return
        
        temp_channel = voice_channels[0]
        afk_channel = voice_channels[1]
        
        # Verify channels are in the same guild
        if temp_channel.guild.id != guild_id or afk_channel.guild.id != guild_id:
            await ctx.send("❌ Channels must be from this server!")
            return
        
        # Save the configuration
        set_guild_config(guild_id, temp_channel_id=temp_channel.id, afk_channel_id=afk_channel.id)
        
        await ctx.send(
            f"✅ **Auto-mover configured!**\n\n"
            f"🚪 **TEMP:** {temp_channel.mention}\n"
            f"🚪 **AFK:** {afk_channel.mention}\n\n"
            f"Users joining {temp_channel.mention} will automatically be moved to {afk_channel.mention}"
        )
        logger.info(f"Guild {ctx.guild.name} AFK channels configured: TEMP={temp_channel.id}, AFK={afk_channel.id}")
        return
    
    # Unknown subcommand
    await ctx.send(f"❌ Unknown subcommand: `{subcommand}`\n\nUse `*setup` to see available commands.")

async def execute_kidnap(guild, member, afk_channel):
    """Execute the actual kidnap - join, play, move"""
    try:
        if not member.voice or not member.voice.channel:
            return False
        
        victim_channel = member.voice.channel
        
        # Join the victim's channel
        if guild.voice_client:
            await guild.voice_client.disconnect(force=True)
            await asyncio.sleep(1)
        
        voice_client = await victim_channel.connect(timeout=30.0, reconnect=False, self_deaf=False, self_mute=False)
        logger.info(f"Joined {victim_channel.name} to kidnap {member.display_name}")
        
        # Ensure bot is unmuted
        await guild.me.edit(mute=False, deafen=False)
        
        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)
        
        # Play the lizard sound
        if os.path.exists("lizzard-1.mp3"):
            ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
            audio_source = discord.FFmpegPCMAudio("lizzard-1.mp3", executable=ffmpeg_path)
            
            def after_playback(error):
                if error:
                    logger.error(f'Kidnap playback error: {error}')
            
            voice_client.play(audio_source, after=after_playback)
            logger.info(f"Playing kidnap sound for {member.display_name}")
            
            # Wait for playback to finish
            while voice_client.is_playing():
                await asyncio.sleep(1)
        
        # Move the victim to AFK channel
        await member.move_to(afk_channel)
        logger.info(f"Moved {member.display_name} to AFK channel")
        
        # Track kidnap stat
        increment_user_stat(guild.id, member.id, 'kidnaps')
        
        # Move bot to AFK channel briefly
        await guild.me.move_to(afk_channel)
        await asyncio.sleep(1)
        
        # Leave the channel
        await voice_client.disconnect(force=True)
        logger.info(f"Kidnap complete for {member.display_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during kidnap execution: {e}")
        if guild.voice_client:
            await guild.voice_client.disconnect(force=True)
        return False

@bot.command(name='kidnap')
async def kidnap(ctx, member: discord.Member = None, force_flag: str = None):
    """Kidnap a user to the AFK channel with a D20 dice roll! Admins can use !force to bypass the roll."""
    global kidnap_immunity, pending_kidnaps
    
    # Get guild-specific AFK channel
    guild_config = get_guild_config(ctx.guild.id)
    afk_channel_id = guild_config.get('afk_channel_id')
    
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
    if not afk_channel:
        await ctx.send("AFK channel not found!")
        return
    
    # Check for !force flag
    is_forced = force_flag == "!force"
    
    # If forced, check admin permissions
    if is_forced:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("Only administrators can use `!force`!")
            return
        
        # Admin force kidnap - no dice roll, just do it
        logger.info(f"Force kidnap by admin {ctx.author.display_name} on {member.display_name}")
        success = await execute_kidnap(ctx.guild, member, afk_channel)
        if success:
            await ctx.send(f"🦎 **FORCE KIDNAP!** {member.mention} has been taken!")
        return
    
    # Check immunity (only for non-forced kidnaps)
    immunity_key = (ctx.guild.id, member.id)
    now = datetime.now()
    if immunity_key in kidnap_immunity and kidnap_immunity[immunity_key] > now:
        time_left = kidnap_immunity[immunity_key] - now
        minutes = int(time_left.total_seconds() / 60)
        await ctx.send(f"{member.mention} has kidnap immunity for {minutes} more minutes!")
        return
    
    # Send Diceroll.gif
    gif_path = "Diceroll.gif"
    if not os.path.exists(gif_path):
        await ctx.send("Diceroll.gif not found!")
        return
    
    dice_msg = await ctx.send(file=discord.File(gif_path))
    await asyncio.sleep(2)  # Let the gif play
    
    # Roll the dice (1-20)
    roll = random.randint(1, 20)
    logger.info(f"Kidnap roll for {member.display_name}: {roll}")
    
    # Get the frame image
    frame_path = f"frames/{roll}.png"
    if os.path.exists(frame_path):
        await dice_msg.delete()
        result_msg = await ctx.send(file=discord.File(frame_path))
    else:
        result_msg = await ctx.send(f"🎲 Rolled: {roll}")
    
    # Determine outcome
    if roll <= 7:  # Low roll - failed, immunity
        await ctx.send("*lizard crawls away*")
        kidnap_immunity[immunity_key] = now + timedelta(minutes=30)
        logger.info(f"Kidnap failed for {member.display_name}, immunity granted for 30 mins")
    
    elif roll >= 14:  # High roll - immediate kidnap
        success = await execute_kidnap(ctx.guild, member, afk_channel)
        if success:
            logger.info(f"Immediate kidnap successful for {member.display_name}")
    
    else:  # Mid roll (8-13) - pending kidnap
        await ctx.send("it'll happen, eventually")
        pending_kidnaps[(ctx.guild.id, member.id)] = ctx.author.id
        logger.info(f"Kidnap for {member.display_name} marked as pending")

@bot.command(name='stats')
async def stats(ctx):
    """Show lizard visit statistics and top 3 leaderboard for this guild"""
    guild_id = ctx.guild.id
    stats_data = get_guild_stats(guild_id)
    
    if not stats_data:
        await ctx.send("📊 No statistics yet! The lizard hasn't visited anyone in this server.")
        return
    
    # Calculate totals
    total_visits = sum(user_stats.get('visits', 0) for user_stats in stats_data.values())
    total_kidnaps = sum(user_stats.get('kidnaps', 0) for user_stats in stats_data.values())
    
    info = []
    info.append(f"**🦎 Lizard Statistics for {ctx.guild.name}**")
    info.append("")
    info.append(f"**Total Visits:** {total_visits}")
    info.append(f"**Total Kidnaps:** {total_kidnaps}")
    info.append(f"**Unique Users Tracked:** {len(stats_data)}")
    info.append("")
    
    # Create leaderboard for visits
    leaderboard = []
    for user_id, user_stats in stats_data.items():
        visits = user_stats.get('visits', 0)
        kidnaps = user_stats.get('kidnaps', 0)
        if visits > 0 or kidnaps > 0:
            member = ctx.guild.get_member(int(user_id))
            if member:
                leaderboard.append({
                    'member': member,
                    'visits': visits,
                    'kidnaps': kidnaps
                })
    
    # Sort by visits (descending)
    leaderboard.sort(key=lambda x: x['visits'], reverse=True)
    
    # Top 3 leaderboard
    info.append("**🏆 Top 3 Most Visited:**")
    if leaderboard:
        for i, entry in enumerate(leaderboard[:3], 1):
            medal = ["🥇", "🥈", "🥉"][i-1]
            info.append(
                f"{medal} **{entry['member'].display_name}** - "
                f"{entry['visits']} visits, {entry['kidnaps']} kidnaps"
            )
    else:
        info.append("No one yet!")
    
    await ctx.send("\n".join(info))

@bot.command(name='timer')
async def timer_status(ctx):
    """Show timer status and users in voice channels for this guild"""
    global guild_timers
    
    guild_id = ctx.guild.id
    info = []
    info.append(f"**🦎 Lizard Timer Status for {ctx.guild.name}:**")
    info.append("")
    
    # Show timer information for this guild
    if guild_id not in guild_timers or guild_timers[guild_id] is None:
        info.append("⏸️ **Timer:** Waiting for users in voice channels")
    else:
        time_remaining = guild_timers[guild_id] - datetime.now()
        if time_remaining.total_seconds() > 0:
            minutes = int(time_remaining.total_seconds() / 60)
            seconds = int(time_remaining.total_seconds() % 60)
            info.append(f"⏱️ **Time Remaining:** {minutes}m {seconds}s")
            info.append(f"🎯 **Target:** Will visit ALL channels in this server with users")
        else:
            info.append("⏰ **Timer:** Expired, visiting channels soon...")
    
    info.append("")
    info.append("**👥 Users in Voice Channels (This Server):**")
    
    # Show users in voice channels for this guild only
    has_users = False
    for channel in ctx.guild.voice_channels:
        members = [m for m in channel.members if not m.bot]
        if members:
            has_users = True
            member_names = [m.display_name for m in members]
            info.append(f"🔊 **{channel.name}**: {', '.join(member_names)}")
    
    if not has_users:
        info.append("No users in voice channels")
    
    # Show configuration status
    guild_config = get_guild_config(guild_id)
    if guild_config:
        info.append("")
        info.append("⚙️ **Auto-mover:** Enabled")
    else:
        info.append("")
        info.append("⚙️ **Auto-mover:** Not configured (use `*setup`)")
    
    await ctx.send("\n".join(info))

@bot.command(name='stop')
async def stop(ctx):
    """Stop audio playback"""
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()
        await ctx.send("Stopped playback")
    else:
        await ctx.send("Nothing is playing!")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file based on .envexample")
    else:
        bot.run(TOKEN)

