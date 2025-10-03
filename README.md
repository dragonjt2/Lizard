# Lizard Discord Bot 🦎

A Discord bot that randomly joins voice channels to play audio, with automatic user movement and manual control features.

## Features

- **Per-Guild Timers**: Each server has its own independent timer (2-30 minutes)
- **Multi-Guild Support**: Works across multiple Discord servers simultaneously
- **Per-Guild Configuration**: Each server configures its own TEMP/AFK channels using `*setup`
- **Auto-Mover**: Automatically moves users from a TEMP channel to AFK channel (configured per-guild)
- **Manual Control**: Commands to manually trigger bot actions
- **Kidnap Feature**: D20 dice roll system to attempt kidnapping users (with immunity and delayed kidnaps)
- **Statistics Tracking**: Track visits and kidnaps per user, with top 3 leaderboard
- **Interactive Responses**: Lizard-themed responses to @mentions and random emoji reactions
- **Lizard Facts**: 100+ educational facts about lizards

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

- `*setup` - (Admin only) Configure guild settings
  - `*setup` - Show help and current configuration
  - `*setup default-text #channel` - Set default text channel for bot messages
  - `*setup afk #temp_channel #afk_channel` - Configure auto-mover channels
- `*ping` - Check if the bot is responding and get latency
- `*stats` - Show server statistics and top 3 most visited users leaderboard
- `*timer` - Show remaining time before next automatic visit and list users in voice channels (for your server)
- `*lizard` - Manually trigger the lizard:
  - If you're in a voice channel: Bot joins your channel only
  - If you're NOT in a voice channel: Bot visits all channels with users (bypasses timer)
- `*kidnap @user` - Roll a D20 to attempt kidnapping a user to AFK channel! (requires `*setup` first)
  - **High roll (14-20):** Immediate kidnap with sound!
  - **Mid roll (8-13):** Pending kidnap - happens on next timer visit
  - **Low roll (1-7):** Failed - target gains 30 min immunity
  - `*kidnap @user !force` - (Admin only) Bypass dice roll and force immediate kidnap
- `*stop` - Stop current audio playback
- `*leave` - Manually disconnect the bot from voice

## Interactions

- **@mention the bot** - Get a random lizard response from 100+ quirky lizard messages!
  - Example: "@LizardBot hello!" → "Blink blink." or "Sun feels good today."
- **@mention + "fact"** - Get a random lizard fact!
  - Example: "@LizardBot fact" → "🦎 **Lizard Fact:** There are over 6,000 species of lizards worldwide."
- **Random emoji reactions** - Bot occasionally reacts to messages with 🦎 (3% chance)

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

### Kidnap Dice Roll System
- Use `*kidnap @user` to attempt kidnapping someone
- Bot sends a D20 dice roll gif, then shows the result (frame 1-20.png)
- **High Roll (14-20):** Instant kidnap! Bot joins, plays sound, moves target to AFK
- **Mid Roll (8-13):** Delayed kidnap - marked as "pending," happens on next timer visit
- **Low Roll (1-7):** Failed attempt - target gets 30 minutes of kidnap immunity
- Pending kidnaps execute automatically when bot visits that user's voice channel
- **Admin Override:** Use `*kidnap @user !force` to bypass dice roll (Administrator permission required)

## Notes

- **Multi-Guild Ready**: Works on multiple servers simultaneously without configuration
- The bot uses prefix commands (e.g., `*ping`)
- Audio playback requires FFmpeg (included: `ffmpeg.exe`)
- Make sure the bot has proper permissions in your Discord server
- Don't forget to enable "Message Content Intent" in the Discord Developer Portal
- Bot status will show "Lizard" when online

## Required Files

- `lizzard-1.mp3` - Audio file played when bot visits
- `Diceroll.gif` - Animated dice roll for kidnap attempts
- `frames/` directory - Contains `1.png` through `20.png` for dice results
- `lizard_bot_responses.txt` - 100 quirky lizard responses
- `lizard_facts.txt` - 100 educational lizard facts
- `guild_configs.json` - Auto-generated per-guild settings 