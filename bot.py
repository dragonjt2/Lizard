from discord.ext import commands

from lizard_bot.commands import register_commands
from lizard_bot.events import register_events
from lizard_bot.settings import create_intents, load_settings
from lizard_bot.state import BotState
from lizard_bot.storage.json_store import JsonGuildConfigStore
from lizard_bot.text_cache import TextCache
from lizard_bot.timer import create_lizard_timer


settings = load_settings()
intents = create_intents()

bot = commands.Bot(command_prefix="*", intents=intents, help_command=None)
state = BotState()
config_store = JsonGuildConfigStore(settings.config_file)
text_cache = TextCache(base_path=settings.audio_file.parent)
text_cache.register("facts", "lizard_facts.txt")
text_cache.register("responses", "lizard_bot_responses.txt")

lizard_timer = create_lizard_timer(bot, state, settings, config_store)


def start_timer() -> None:
    if not lizard_timer.is_running():
        lizard_timer.start()


register_events(bot, state, settings, text_cache, config_store, start_timer)
register_commands(bot, state, settings, config_store)


if __name__ == "__main__":
    if not settings.token:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file based on .envexample")
    else:
        bot.run(settings.token)
