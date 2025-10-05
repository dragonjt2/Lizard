Changes:

Store data in sqliteDB

Per Guild config, time settings for lizard joining
be able to disable auto move while still allowing kidnap to another channel
Kidnap multiple users at once (roll must be higher)
per server allow command prefix setup
Lower latency for actions

Change the dice roll from delete and resend to edit message with new image
Lower resolution of gif and frames

Add ini file for default configs (ffmpeg path, varables, etc)

Mark users for pending kidnap, this should allow users to be marked when not in a voice channel and solve the issue of what happens if someone leaves before kidnap occurs

Cache text files in memory.
Add comments to code, short and simple, no emojis!
Split code into seperate files, no more monolithic code files
Fix file structure:
assets
assets/frames
etc


Make start scripts better (on windows make app hide in taskbar "show hidden items" tab)
Add some small cooldowns to prevent spam
add a help command to show docs, link to github readme (not yet public) and my kofi.
Make Github docs better, easier to follow, troubleshooting steps, venv setup/conda, linux setup 

Add admin only way of pausing lizard joining voice chat for a amount of time
Add per user opt-out of kidnap feature - send lizard themed messages saying why it cant do it, (list of options again)

Also add a list of text for any currently static messages

