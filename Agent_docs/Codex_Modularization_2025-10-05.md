# Modularization & Storage Prep — 2025-10-05

## Planned Work
- Remove completed items from `Planned_Changes.md` so the backlog reflects only outstanding tasks.
- Break the monolithic `bot.py` into focused modules for settings, storage, events, commands, and timers while keeping behaviour unchanged.
- Introduce a storage abstraction layer and scaffold a SQLite-backed implementation for the upcoming migration.

## Implementation Notes
- Created a `lizard_bot` package with dedicated modules (`settings`, `text_cache`, `state`, `voice`, `events`, `commands`, `timer`, and `storage`).
- Replaced direct JSON helpers with a `JsonGuildConfigStore` that satisfies a new `BaseGuildConfigStore` interface; added a stubbed `SqliteGuildConfigStore` that sets up the schema.
- Adjusted the entrypoint `bot.py` to instantiate shared services, register events/commands, and start the background timer through the modular components.
- Updated `Planned_Changes.md` to drop the already-completed caching, cooldown, help command, and monolith-splitting items.

## Testing
- `python -m compileall bot.py lizard_bot`
