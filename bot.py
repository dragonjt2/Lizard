from datetime import datetime

from discord.ext import commands

from lizard_bot.commands import register_commands
from lizard_bot.events import register_events
from lizard_bot.settings import create_intents, load_settings
from lizard_bot.state import BotState, PendingKidnap
from lizard_bot.storage import SqliteGuildConfigStore
from lizard_bot.text_cache import TextCache
from lizard_bot.timer import create_lizard_timer


settings = load_settings()
intents = create_intents()

bot = commands.Bot(command_prefix=settings.command_prefix, intents=intents, help_command=None)
state = BotState()
config_store = SqliteGuildConfigStore(settings.database_file)
config_store.bootstrap_from_json(settings.config_file)

for (guild_id, user_id), record in config_store.load_pending_kidnaps().items():
    created_at = record.get("created_at") or datetime.utcnow()
    initiator = record.get("initiator_id", 0)
    if isinstance(initiator, str) and initiator.isdigit():
        initiator = int(initiator)
    pending = PendingKidnap(
        initiator_id=initiator,
        created_at=created_at,
        due_at=record.get("due_at"),
    )
    state.pending_kidnaps[(guild_id, user_id)] = pending

state.guild_timers.update(config_store.load_guild_timers())

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
