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

def set_guild_config(guild_id, temp_channel_id, afk_channel_id):
    """Set configuration for a specific guild"""
    configs = load_guild_configs()
    configs[str(guild_id)] = {
        'temp_channel_id': temp_channel_id,
        'afk_channel_id': afk_channel_id
    }
    save_guild_configs(configs)

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

@bot.event
async def on_message(message):
    """Handle messages, especially when bot is mentioned"""
    # Don't respond to self
    if message.author == bot.user:
        return
    
    # Check if bot is mentioned
    if bot.user in message.mentions:
        try:
            # Read random line from lizard_bot_responses.txt
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
            logger.error(f"Error reading response file: {e}")
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
                
                if members:
                    logger.info(f"Manual timer trigger: Joining {channel.name} in {channel.guild.name}")
                    await join_play_leave(channel)
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
async def setup(ctx, temp_channel: discord.VoiceChannel = None, afk_channel: discord.VoiceChannel = None):
    """Configure TEMP and AFK channels for this guild (Admin only)
    
    Usage: *setup #temp_channel #afk_channel
    Or just: *setup (to view current config)
    """
    guild_id = ctx.guild.id
    
    # If no channels provided, show current config
    if temp_channel is None and afk_channel is None:
        config = get_guild_config(guild_id)
        if config:
            temp_ch = bot.get_channel(config.get('temp_channel_id'))
            afk_ch = bot.get_channel(config.get('afk_channel_id'))
            info = [
                f"**🦎 Configuration for {ctx.guild.name}:**",
                f"**TEMP Channel:** {temp_ch.mention if temp_ch else 'Not found'} (ID: {config.get('temp_channel_id')})",
                f"**AFK Channel:** {afk_ch.mention if afk_ch else 'Not found'} (ID: {config.get('afk_channel_id')})",
                "",
                "To update: `*setup #temp_channel #afk_channel`"
            ]
            await ctx.send("\n".join(info))
        else:
            await ctx.send(f"No configuration set for {ctx.guild.name}.\n\nUsage: `*setup #temp_channel #afk_channel`")
        return
    
    # Both channels must be provided together
    if temp_channel is None or afk_channel is None:
        await ctx.send("Please provide both TEMP and AFK channels.\n\nUsage: `*setup #temp_channel #afk_channel`")
        return
    
    # Verify channels are in the same guild
    if temp_channel.guild.id != guild_id or afk_channel.guild.id != guild_id:
        await ctx.send("Channels must be from this server!")
        return
    
    # Save the configuration
    set_guild_config(guild_id, temp_channel.id, afk_channel.id)
    
    await ctx.send(
        f"✅ **Configuration saved for {ctx.guild.name}!**\n\n"
        f"**TEMP Channel:** {temp_channel.mention}\n"
        f"**AFK Channel:** {afk_channel.mention}\n\n"
        f"Users joining {temp_channel.mention} will automatically be moved to {afk_channel.mention}"
    )
    logger.info(f"Guild {ctx.guild.name} configured: TEMP={temp_channel.id}, AFK={afk_channel.id}")

@bot.command(name='kidnap')
async def kidnap(ctx, member: discord.Member = None):
    """Kidnap a user to the AFK channel with the lizard sound"""
    # Get guild-specific AFK channel
    guild_config = get_guild_config(ctx.guild.id)
    afk_channel_id = guild_config.get('afk_channel_id')
    
    if not afk_channel_id:
        await ctx.send("AFK channel not configured! Use `*setup` to configure channels.")
        return
    
    if member is None:
        await ctx.send("You need to mention a user to kidnap! Example: `*kidnap @user`")
        return
    
    if member.bot:
        await ctx.send("Can't kidnap bots!")
        return
    
    if not member.voice or not member.voice.channel:
        await ctx.send(f"{member.display_name} is not in a voice channel!")
        return
    
    victim_channel = member.voice.channel
    afk_channel = bot.get_channel(afk_channel_id)
    
    if not afk_channel:
        await ctx.send("AFK channel not found!")
        return
    
    try:
        await ctx.send(f"🦎 Kidnapping {member.mention}...")
        
        # Join the victim's channel
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect(force=True)
            await asyncio.sleep(1)
        
        voice_client = await victim_channel.connect(timeout=30.0, reconnect=False, self_deaf=False, self_mute=False)
        logger.info(f"Joined {victim_channel.name} to kidnap {member.display_name}")
        
        # Ensure bot is unmuted
        await ctx.guild.me.edit(mute=False, deafen=False)
        
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
        
        # Move bot to AFK channel briefly
        await ctx.guild.me.move_to(afk_channel)
        await asyncio.sleep(1)
        
        # Leave the channel
        await voice_client.disconnect(force=True)
        logger.info(f"Kidnap complete for {member.display_name}")
        
        await ctx.send(f"{member.mention} has been kidnapped to {afk_channel.name}! 🦎")
        
    except discord.HTTPException as e:
        await ctx.send(f"Failed to kidnap user: {str(e)}")
        logger.error(f"HTTPException during kidnap: {e}")
    except discord.ClientException as e:
        await ctx.send(f"Connection error: {str(e)}")
        logger.error(f"ClientException during kidnap: {e}")
    except Exception as e:
        await ctx.send(f"Error during kidnap: {str(e)}")
        logger.error(f"Error during kidnap: {e}")
        # Cleanup
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect(force=True)

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

