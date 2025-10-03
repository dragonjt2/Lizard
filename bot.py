import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

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

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    print('Bot is ready to receive commands!')

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
    
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.move_to(channel)
        await ctx.send(f"Moved to {channel.name}")
    else:
        await channel.connect()
        await ctx.send(f"Joined {channel.name}")

@bot.command(name='leave')
async def leave(ctx):
    """Leave the voice channel"""
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("Left the voice channel")
    else:
        await ctx.send("I'm not in a voice channel!")

@bot.command(name='play')
async def play(ctx):
    """Play the audio file"""
    if not ctx.guild.voice_client:
        await ctx.send("I need to be in a voice channel first! Use !join")
        return
    
    if not os.path.exists("lizzard-1.mp3"):
        await ctx.send("Audio file not found!")
        return
    
    voice_client = ctx.guild.voice_client
    
    if voice_client.is_playing():
        voice_client.stop()
    
    # Play the audio file
    voice_client.play(
        discord.FFmpegPCMAudio("lizzard-1.mp3"),
        after=lambda e: print(f'Player error: {e}') if e else None
    )
    
    await ctx.send("🎵 Playing lizzard-1.mp3")

@bot.command(name='stop')
async def stop(ctx):
    """Stop audio playback"""
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()
        await ctx.send("⏹️ Stopped playback")
    else:
        await ctx.send("Nothing is playing!")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file based on .envexample")
    else:
        bot.run(TOKEN)

