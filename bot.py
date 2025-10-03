import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import logging
import asyncio
import random
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')
VOICE_CHANNEL = os.getenv('DISCORD_VOICE_CHANNEL')
TEMP_CHANNEL_ID = int(os.getenv('TEMP_Channel')) if os.getenv('TEMP_Channel') else None
AFK_CHANNEL_ID = int(os.getenv('AFK_Channel')) if os.getenv('AFK_Channel') else None

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='*', intents=intents)

# Timer tracking variables
next_play_time = None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    print('Bot is ready to receive commands!')
    
    # Check for voice support
    if not discord.opus.is_loaded():
        print('WARNING: Opus library not loaded. Voice may not work properly.')
    else:
        print('Opus library loaded successfully')
    
    # Start the background task
    if not lizard_timer.is_running():
        lizard_timer.start()
        print('Lizard timer started')
    
    # Check if auto-mover is configured
    if TEMP_CHANNEL_ID and AFK_CHANNEL_ID:
        print(f'Auto-mover enabled: TEMP ({TEMP_CHANNEL_ID}) → AFK ({AFK_CHANNEL_ID})')
    else:
        print('Auto-mover not configured (TEMP_Channel and AFK_Channel required in .env)')

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state updates and potential disconnections"""
    if member == bot.user and after.channel is None:
        logger.info(f"Bot was disconnected from voice channel")
        return
    
    # Auto-move users from TEMP channel to AFK channel
    if TEMP_CHANNEL_ID and AFK_CHANNEL_ID and after.channel:
        # If user joined the TEMP channel
        if after.channel.id == TEMP_CHANNEL_ID and not member.bot:
            # Get the AFK channel
            afk_channel = bot.get_channel(AFK_CHANNEL_ID)
            if afk_channel:
                try:
                    await member.move_to(afk_channel)
                    logger.info(f"Moved {member.display_name} from TEMP to AFK channel")
                except discord.HTTPException as e:
                    logger.error(f"Failed to move {member.display_name}: {e}")
                except Exception as e:
                    logger.error(f"Error moving user: {e}")

@bot.command(name='ping')
async def ping(ctx):
    """Simple ping command"""
    await ctx.send(f"Pong! 🏓 Latency: {round(bot.latency * 1000)}ms")

@bot.command(name='hello')
async def hello(ctx):
    """Greet the user"""
    await ctx.send(f"Hello {ctx.author.mention}! 👋")

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
    """Background task that monitors voice channels and plays audio on timer"""
    global next_play_time
    
    # Get users in voice channels
    voice_info = get_users_in_voice_channels()
    
    # If no users in any voice channel, reset timer
    if not voice_info:
        if next_play_time is not None:
            logger.info("No users in voice channels. Timer paused.")
        next_play_time = None
        return
    
    # If timer not set and there are users, set a new timer
    if next_play_time is None:
        # Random time between 1 and 2 minutes (you had changed this)
        minutes = random.randint(2, 30)
        next_play_time = datetime.now() + timedelta(minutes=minutes)
        logger.info(f"Timer set for {minutes} minutes. Will visit all channels with users.")
        return
    
    # Check if it's time to play
    if datetime.now() >= next_play_time:
        logger.info(f"Time to play! Visiting all channels with users...")
        
        # Get fresh list of channels with users
        current_voice_info = get_users_in_voice_channels()
        
        if current_voice_info:
            # Visit each channel with users
            for channel_info in current_voice_info:
                channel = channel_info['channel']
                members = [m for m in channel.members if not m.bot]
                
                if members:
                    logger.info(f"Joining {channel.name} in {channel.guild.name} ({len(members)} users)")
                    await join_play_leave(channel)
                    # Small delay between channels
                    await asyncio.sleep(2)
            
            logger.info("Finished visiting all channels!")
        else:
            logger.info("No channels with users at trigger time. Skipping.")
        
        # Reset timer
        next_play_time = None

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

@bot.command(name='kidnap')
async def kidnap(ctx, member: discord.Member = None):
    """Kidnap a user to the AFK channel with the lizard sound"""
    if not AFK_CHANNEL_ID:
        await ctx.send(" AFK channel not configured!")
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
    afk_channel = bot.get_channel(AFK_CHANNEL_ID)
    
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
    """Show timer status and users in voice channels"""
    global next_play_time
    
    info = []
    info.append("**🦎 Lizard Timer Status:**")
    info.append("")
    
    # Show timer information
    if next_play_time is None:
        info.append("⏸️ **Timer:** Waiting for users in voice channels")
    else:
        time_remaining = next_play_time - datetime.now()
        minutes = int(time_remaining.total_seconds() / 60)
        seconds = int(time_remaining.total_seconds() % 60)
        info.append(f"⏱️ **Time Remaining:** {minutes}m {seconds}s")
        info.append(f"🎯 **Target:** Will visit ALL channels with users")
    
    info.append("")
    info.append("**👥 Users in Voice Channels:**")
    
    # Show users in voice channels
    voice_info = get_users_in_voice_channels()
    if not voice_info:
        info.append("No users in voice channels")
    else:
        for channel_info in voice_info:
            channel = channel_info['channel']
            members = channel_info['members']
            member_names = [m.display_name for m in members]
            info.append(f"🔊 **{channel.name}** ({channel.guild.name}): {', '.join(member_names)}")
    
    await ctx.send("\n".join(info))

@bot.command(name='stop')
async def stop(ctx):
    """Stop audio playback"""
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()
        await ctx.send("Stopped playback")
    else:
        await ctx.send("Nothing is playing!")

@bot.command(name='debug')
async def debug(ctx):
    """Show debug information for voice connection"""
    info = []
    info.append("**Voice Debug Information:**")
    info.append(f"Bot Latency: {round(bot.latency * 1000)}ms")
    info.append(f"Opus Loaded: {'True' if discord.opus.is_loaded() else 'False'}")
    
    if ctx.guild.voice_client:
        vc = ctx.guild.voice_client
        info.append(f"Voice Connected: True")
        info.append(f"Voice Channel: {vc.channel.name}")
        info.append(f"Voice Latency: {round(vc.latency * 1000)}ms")
        info.append(f"Is Playing: {'Yes' if vc.is_playing() else 'No'}")
        info.append(f"Is Connected: {'Yes' if vc.is_connected() else 'No'}")
    else:
        info.append(f"Voice Connected: False")
    
    info.append(f"\nFFmpeg Available: Check console logs")
    await ctx.send("\n".join(info))

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file based on .envexample")
    else:
        bot.run(TOKEN)

