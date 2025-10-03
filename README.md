# Lizard Discord Bot 🦎

A Discord bot that randomly joins voice channels to play audio, with automatic user movement and manual control features.

## Features

- **Per-Guild Timers**: Each server has its own independent timer (2-30 minutes)
- **Multi-Guild Support**: Works across multiple Discord servers simultaneously
- **Per-Guild Configuration**: Each server configures its own TEMP/AFK channels using `*setup`
- **Auto-Mover**: Automatically moves users from a TEMP channel to AFK channel (configured per-guild)
- **Manual Control**: Commands to manually trigger bot actions
- **Kidnap Feature**: Drag users to AFK channel with audio playback

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file based on `.envexample`:
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   ```
   That's it! No need to configure channels in .env anymore.

3. Get your bot token:
   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the token and paste it in `.env`
   - **IMPORTANT:** Enable "Message Content Intent" in the Bot settings (required for prefix commands)

4. Invite your bot to your server:
   - Go to OAuth2 > URL Generator
   - Select scopes: `bot`
   - Select permissions: `Send Messages`, `Connect`, `Speak`, `Use Voice Activity`, `Move Members`
   - Copy the generated URL and open it in your browser

## Running the Bot

```bash
python bot.py
```

## Commands

All commands use the `*` prefix:

- `*setup` - (Admin only) Configure TEMP and AFK channels for auto-mover
  - Usage: `*setup #temp_channel #afk_channel`
  - Or just `*setup` to view current configuration
- `*ping` - Check if the bot is responding and get latency
- `*timer` - Show remaining time before next automatic visit and list users in voice channels (for your server)
- `*lizard` - Manually trigger the lizard:
  - If you're in a voice channel: Bot joins your channel only
  - If you're NOT in a voice channel: Bot visits all channels with users (bypasses timer)
- `*kidnap @user` - Drag a user to AFK channel with audio playback (requires `*setup` first)
- `*stop` - Stop current audio playback
- `*leave` - Manually disconnect the bot from voice

## Interactions

- **@mention the bot** - Get a random lizard response from 100+ quirky lizard messages!
  - Example: "@LizardBot hello!" → "Blink blink." or "Sun feels good today."

## How It Works

### Per-Guild Automatic Timers
- Bot monitors voice channels **independently for each server**
- Each server has its own timer (2-30 minutes random)
- When a server's timer expires, bot visits ALL voice channels **in that server only**
- Timers run simultaneously across all servers
- Example: Guild A might get visited at 10 minutes, Guild B at 25 minutes

### Auto-Mover (Optional, Per-Guild)
- Configure using `*setup #temp_channel #afk_channel` (requires Admin permissions)
- Each server has its own configuration stored locally
- Automatically moves users from TEMP to AFK channel instantly
- Only works in servers where it's been configured
- Useful for custom AFK management

## Notes

- **Multi-Guild Ready**: Works on multiple servers simultaneously without configuration
- The bot uses prefix commands (e.g., `*ping`)
- Audio playback requires FFmpeg (included: `ffmpeg.exe`)
- Make sure the bot has proper permissions in your Discord server
- Don't forget to enable "Message Content Intent" in the Discord Developer Portal
- Bot status will show "Lizard" when online 