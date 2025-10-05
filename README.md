# Lizard Discord Bot 🦎

A Discord bot that randomly joins voice channels to play audio, with automatic user movement and manual control features. Features per-guild timers, kidnap mechanics, statistics tracking, and interactive lizard-themed responses.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Commands](#commands)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [File Structure](#file-structure)

## Features

- **Per-Guild Timers**: Each server has its own independent timer (2-30 minutes)
- **Multi-Guild Support**: Works across multiple Discord servers simultaneously
- **Per-Guild Configuration**: Each server configures its own TEMP/AFK channels, command prefix, and settings using `*setup`
- **Auto-Mover**: Automatically moves users from a TEMP channel to AFK channel (configured per-guild)
- **Manual Control**: Commands to manually trigger bot actions
- **Kidnap Feature**: D20 dice roll system to attempt kidnapping users (with immunity and delayed kidnaps)
- **Statistics Tracking**: Track visits and kidnaps per user, with top 3 leaderboard
- **Interactive Responses**: Lizard-themed responses to @mentions and random emoji reactions
- **Lizard Facts**: 100+ educational facts about lizards
- **Configurable**: Extensive configuration options via `config.ini`

## Installation

### Prerequisites

- Python 3.8 or higher
- Discord Developer Account
- Git (optional, for cloning)

### Step 1: Clone or Download

**Option A: Clone with Git**
```bash
git clone https://github.com/yourusername/Lizard.git
cd Lizard
```

**Option B: Download ZIP**
1. Download the repository as a ZIP file
2. Extract to your desired location
3. Open terminal/command prompt in the extracted folder

### Step 2: Set Up Virtual Environment

**Windows:**
```cmd
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate

# Verify activation (should show (.venv) in prompt)
python --version
```

**macOS/Linux:**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Verify activation (should show (.venv) in prompt)
python --version
```

### Step 3: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 4: Configure Environment

1. **Create environment file:**
   ```bash
   # Copy the example (if available)
   copy .envexample .env
   
   # Or create manually
   echo DISCORD_BOT_TOKEN=your_bot_token_here > .env
   ```

2. **Get Discord Bot Token:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to "Bot" section and click "Add Bot"
   - Copy the token and paste it in your `.env` file
   - **IMPORTANT:** Enable "Message Content Intent" in the Bot settings

3. **Invite Bot to Server:**
   - Go to OAuth2 > URL Generator
   - Select scopes: `bot`
   - Select permissions: `Send Messages`, `Connect`, `Speak`, `Use Voice Activity`, `Move Members`
   - Copy the generated URL and open it in your browser

### Step 5: Verify Installation

```bash
# Test the bot (will show errors if not configured properly)
python bot.py
```

Press `Ctrl+C` to stop the bot after verification.

## Configuration

The bot uses `config.ini` for configuration. All settings have sensible defaults, but you can customize them:

### Basic Configuration

```ini
[bot]
# Discord bot token (can also be set via DISCORD_BOT_TOKEN environment variable)
token = your_bot_token_here

# Bot command prefix
command_prefix = *

# Bot activity status
activity_name = Lizard
```

### Timer Settings

```ini
[timer]
# Lizard visit timer settings (in minutes)
min_visit_delay = 2
max_visit_delay = 30
timer_check_interval = 10
```

### Kidnap System

```ini
[kidnap]
# Kidnap system settings
immunity_duration_minutes = 30
dice_roll_success_threshold = 14
dice_roll_failure_threshold = 7
pending_kidnap_delay_seconds = 2
```

### Voice Settings

```ini
[voice]
# Voice connection settings
connection_timeout = 30.0
playback_delay_seconds = 1
disconnect_delay_seconds = 1
```

### Cooldowns

```ini
[cooldowns]
# Command cooldown settings (in seconds)
lizard_cooldown = 30
kidnap_cooldown = 45
```

## Running the Bot

### Development Mode

```bash
# Activate virtual environment first
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Run the bot
python bot.py
```

### Production Mode

**Windows:**
```cmd
# Use the provided batch files
start_lizard.bat          # Visible window
start_lizard_silent.bat   # Hidden window
start_lizard_hidden.vbs   # Completely hidden
```

**macOS/Linux:**
```bash
# Run in background
nohup python bot.py > bot.log 2>&1 &

# Or use screen/tmux
screen -S lizard-bot
python bot.py
# Ctrl+A, D to detach
```

## Commands

All commands use the `*` prefix (configurable):

### Setup Commands
- `*setup` - (Admin only) Configure guild settings
  - `*setup` - Show help and current configuration
  - `*setup default-text #channel` - Set default text channel for bot messages
  - `*setup afk #temp_channel #afk_channel` - Configure auto-mover channels
  - `*setup prefix <symbol>` - Change the command prefix for this server

### Information Commands
- `*ping` - Check if the bot is responding and get latency
- `*stats` - Show server statistics and top 3 most visited users leaderboard
- `*timer` - Show remaining time before next automatic visit and list users in voice channels

### Control Commands
- `*lizard` - Manually trigger the lizard:
  - If you're in a voice channel: Bot joins your channel only
  - If you're NOT in a voice channel: Bot visits all channels with users (bypasses timer)
- `*stop` - Stop current audio playback
- `*leave` - Manually disconnect the bot from voice

### Kidnap Commands
- `*kidnap @user` - Roll a D20 to attempt kidnapping a user to AFK channel!
  - **High roll (14-20):** Immediate kidnap with sound!
  - **Mid roll (8-13):** Pending kidnap - happens on next timer visit
  - **Low roll (1-7):** Failed - target gains 30 min immunity
- `*kidnap @user !force` - (Admin only) Bypass dice roll and force immediate kidnap

## Customization

### Custom Audio Files

Replace `lizzard-1.mp3` with your own audio file:
- Supported formats: MP3, WAV, OGG
- Update `config.ini`:
  ```ini
  [files]
  audio_file = your_audio_file.mp3
  ```

### Custom Responses

Edit `lizard_bot_responses.txt` to add your own lizard responses:
- One response per line
- Supports Discord markdown formatting
- Bot randomly selects from all responses

### Custom Facts

Edit `lizard_facts.txt` to add your own lizard facts:
- One fact per line
- Format: `🦎 **Lizard Fact:** Your fact here`
- Bot randomly selects from all facts

### Per-Guild Customization

Each Discord server can have its own configuration:

**Command Prefix:**
- Use `*setup prefix <symbol>` to change the prefix for that server
- Example: `*setup prefix !` changes all commands to use `!` instead of `*`
- Each server can have a different prefix
- Prefixes are stored per-guild and persist across bot restarts

**Channel Configuration:**
- Each server configures its own default text channel
- Each server sets its own TEMP and AFK channels for auto-mover
- Each server can set its own kidnap destination channel

**Timer Settings:**
- Each server has independent timer ranges
- Each server can set its own kidnap immunity duration
- Timer settings are per-guild and don't affect other servers

### Custom Messages

Modify messages in `config.ini` under `[messages]` section:
```ini
[messages]
startup_message = Your custom startup message
kidnap_success_message = Your custom success message
# ... and more
```

### Custom Dice Roll Animation

Replace `Diceroll.gif` with your own animation:
- Must be a GIF file
- Update `config.ini`:
  ```ini
  [files]
  dice_gif = your_dice_animation.gif
  ```

### Custom Dice Result Frames

Replace frames in `Frames/` directory:
- Files must be named `1.png` through `20.png`
- Each represents a dice roll result
- Update `config.ini`:
  ```ini
  [files]
  frames_directory = YourFramesFolder
  ```

## Troubleshooting

### Common Issues

**Bot doesn't respond to commands:**
- Check if "Message Content Intent" is enabled in Discord Developer Portal
- Verify the bot has proper permissions in your server
- Ensure the command prefix is correct (default: `*`)

**Bot can't join voice channels:**
- Check if bot has "Connect" and "Speak" permissions
- Verify the voice channel allows the bot to join
- Check if another bot is already in the voice channel

**Audio doesn't play:**
- Ensure `ffmpeg.exe` is in the project directory
- Check if the audio file exists and is a supported format
- Verify the bot has "Use Voice Activity" permission

**Database errors:**
- Delete `guild_data.sqlite3` to reset the database
- Check file permissions in the project directory

**Bot crashes on startup:**
- Check the console output for error messages
- Verify all required files are present
- Ensure Python version is 3.8 or higher

### Logs and Debugging

**Enable debug logging:**
```python
# In bot.py, change logging level
logging.basicConfig(level=logging.DEBUG)
```

**Check bot status:**
- Use `*ping` command to verify bot is responding
- Check Discord server member list to see if bot is online
- Look for error messages in console output

### Getting Help

1. Check the console output for error messages
2. Verify all configuration settings
3. Test with a fresh Discord server
4. Check Discord Developer Portal settings
5. Ensure all required files are present

## Development

### Project Structure

```
Lizard/
├── lizard_bot/           # Main bot code
│   ├── commands.py       # Command implementations
│   ├── events.py         # Discord event handlers
│   ├── timer.py          # Timer system
│   ├── voice.py          # Voice channel management
│   └── storage/          # Data storage (SQLite/JSON)
├── Frames/               # Dice roll result images
├── Agent_docs/           # Development documentation
├── bot.py                # Main entry point
├── config.ini            # Configuration file
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Adding New Commands

1. Add command function to `lizard_bot/commands.py`
2. Register command in the bot's command handler
3. Update this README with command documentation
4. Test thoroughly before deploying

### Adding New Features

1. Create feature branch: `git checkout -b feature-name`
2. Implement feature with proper error handling
3. Add configuration options to `config.ini` if needed
4. Update documentation
5. Test with multiple Discord servers
6. Submit pull request

### Database Schema

The bot uses SQLite for data storage:
- `guilds` - Guild configuration settings
- `user_stats` - User statistics and preferences
- `pending_kidnaps` - Delayed kidnap actions
- `guild_timers` - Per-guild timer information

## File Structure

### Required Files

- `bot.py` - Main bot entry point
- `config.ini` - Configuration file
- `requirements.txt` - Python dependencies
- `lizzard-1.mp3` - Audio file played when bot visits
- `Diceroll.gif` - Animated dice roll for kidnap attempts
- `ffmpeg.exe` - Audio processing (Windows)

### Optional Files

- `.env` - Environment variables (alternative to config.ini)
- `guild_configs.json` - Legacy JSON storage (auto-generated)
- `guild_data.sqlite3` - SQLite database (auto-generated)

### Directories

- `Frames/` - Contains `1.png` through `20.png` for dice results
- `lizard_bot/` - Main bot code
- `Agent_docs/` - Development documentation

### Text Files

- `lizard_bot_responses.txt` - 100 quirky lizard responses
- `lizard_facts.txt` - 100 educational lizard facts

---

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Support

For issues, questions, or contributions:
1. Check this README first
2. Look at the troubleshooting section
3. Check console output for error messages
4. Create an issue with detailed information

---

**Happy Lizard Botting! 🦎**