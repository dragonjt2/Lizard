# Work Plan (2025-10-05)

## Planned Tasks
1. **Cache frequently used text files in memory.**
   - Load `lizard_facts.txt` and `lizard_bot_responses.txt` once at startup and refresh them on demand to reduce repeated disk I/O during mention handling.
2. **Introduce basic cooldowns for high-traffic commands.**
   - Apply per-user cooldowns to commands like `*kidnap` and `*lizard` to reduce spam while keeping functionality accessible.
3. **Add a `help` command with resource links.**
   - Provide a concise overview of available commands and include links to the README and Ko-fi page for support information.
4. **Improve inline documentation where changes occur.**
   - Add short, direct comments in modified sections to explain key logic without overwhelming the file.

## Approach
- Review current command implementations to determine appropriate cooldown durations and ensure they respect admin overrides when applicable.
- Refactor message handling to leverage cached data while retaining a method to refresh caches if the source files change.
- Implement a new Discord command (`*help`) following existing style conventions and verify permission requirements.
- Add brief comments adjacent to new or complex logic introduced during the above tasks.

## Post-Implementation Summary
- Cached lizard facts and responses with mtime-aware loaders to avoid repeated disk reads during mentions.
- Added per-user cooldowns to `*lizard` (30s) and `*kidnap` (45s) along with a friendly cooldown error message.
- Introduced a custom `*help` command featuring quick command references plus configurable README/Ko-fi links.
- Inserted concise comments where new behavior was added and documented optional environment variables for link overrides.
- **Testing:** `python -m compileall bot.py`

## Testing Plan
- Run targeted unit or integration checks as available (likely manual invocation due to Discord context).
- Ensure linting/static checks if configured; otherwise document manual reasoning about tested functionality.
