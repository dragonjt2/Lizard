import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')
VOICE_CHANNEL = os.getenv('DISCORD_VOICE_CHANNEL')

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='*', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    print('Bot is ready to receive commands!')
    
    # Check for voice support
    if not discord.opus.is_loaded():
        print('WARNING: Opus library not loaded. Voice may not work properly.')
    else:
        print('✓ Opus library loaded successfully')

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state updates and potential disconnections"""
    if member == bot.user and after.channel is None:
        logger.info(f"Bot was disconnected from voice channel")

@bot.command(name='ping')
async def ping(ctx):
    """Simple ping command"""
    await ctx.send(f"Pong! 🏓 Latency: {round(bot.latency * 1000)}ms")

@bot.command(name='hello')
async def hello(ctx):
    """Greet the user"""
    await ctx.send(f"Hello {ctx.author.mention}! 👋")

@bot.command(name='join')
async def join(ctx):
    """Join the user's voice channel"""
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel!")
        return
    
    channel = ctx.author.voice.channel
    
    try:
        # If already connected, disconnect first to avoid session issues
        if ctx.guild.voice_client:
            if ctx.guild.voice_client.channel.id == channel.id:
                await ctx.send(f"Already in {channel.name}")
                return
            await ctx.guild.voice_client.disconnect(force=True)
            await asyncio.sleep(1)  # Wait a moment before reconnecting
        
        # Connect with timeout and reconnect settings
        voice_client = await channel.connect(timeout=30.0, reconnect=False)
        await ctx.send(f"Joined {channel.name}")
        logger.info(f"Successfully connected to voice channel: {channel.name}")
    except asyncio.TimeoutError:
        await ctx.send("Connection timed out. Please try again.")
        logger.error("Voice connection timeout")
    except discord.ClientException as e:
        await ctx.send(f"Connection error: {str(e)}")
        logger.error(f"ClientException: {e}")
    except Exception as e:
        await ctx.send(f"Failed to join voice channel: {str(e)}")
        logger.error(f"Unexpected error joining voice: {e}")

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

@bot.command(name='play')
async def play(ctx):
    """Play the audio file"""
    if not ctx.guild.voice_client:
        await ctx.send("I need to be in a voice channel first! Use *join")
        return
    
    if not os.path.exists("lizzard-1.mp3"):
        await ctx.send("Audio file not found!")
        return
    
    voice_client = ctx.guild.voice_client
    
    # Check if voice client is connected
    if not voice_client.is_connected():
        await ctx.send("Voice connection lost. Please use *join again.")
        return
    
    if voice_client.is_playing():
        voice_client.stop()
    
    try:
        # Create audio source with error handling
        def after_playback(error):
            if error:
                logger.error(f'Playback error: {error}')
            else:
                logger.info('Playback finished successfully')
        
        # Get the path to ffmpeg.exe in the current directory
        ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
        audio_source = discord.FFmpegPCMAudio("lizzard-1.mp3", executable=ffmpeg_path)
        voice_client.play(audio_source, after=after_playback)
        
        await ctx.send("🎵 Playing lizzard-1.mp3")
        logger.info("Started playing audio")
    except discord.ClientException as e:
        await ctx.send(f"Playback error: {str(e)}")
        logger.error(f"ClientException during playback: {e}")
    except Exception as e:
        await ctx.send(f"Failed to play audio: {str(e)}\nMake sure FFmpeg is installed!")
        logger.error(f"Error playing audio: {e}")

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

