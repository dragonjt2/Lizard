# Simple Discord Bot that plays sound at random times

### Will join a voice channel when users exist at a random time frame and play an audio file

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.envexample`:
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   DISCORD_GUILD_ID=your_server_id
   TEMP_Channel=temp_snowflake
   AFK_Channel=afk_snowflake
   ```

4. Get your bot token:
   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the token and paste it in `.env`
   - **IMPORTANT:** Enable "Message Content Intent" in the Bot settings (required for prefix commands)

5. Invite your bot to your server:
   - Go to OAuth2 > URL Generator
   - Select scopes: `bot`
   - Select permissions: `Send Messages`, `Connect`, `Speak`, `Use Voice Activity`
   - Copy the generated URL and open it in your browser

## Running the Bot

```bash
python bot.py
```

## Commands

All commands use the `*` prefix:

- `*ping` - Check if the bot is responding
- `*timer` - will show the remaining time before next join
- `*kidnap @username` will drag the person to an AFK channel
- `*stop` - Stop playing audio

## Notes

- The bot uses prefix commands (e.g., `*ping`)
- Audio playback requires FFmpeg to be installed
- Make sure the bot has proper permissions in your Discord server
- Don't forget to enable "Message Content Intent" in the Discord Developer Portal 