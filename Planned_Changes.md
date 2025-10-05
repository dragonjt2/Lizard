Changes:
Kidnap multiple users at once (roll must be higher)
Lower latency for actions *maybe???
*need to do! Change the dice roll from delete and resend to edit message with new image
*Needs more testing/partially done Mark users for pending kidnap, this should allow users to be marked when not in a voice channel and solve the *a * also needs testing! - issue of what happens if someone leaves before kidnap occurs
*will do, cant be fucked atm! 
Fix file structure:
assets
assets/frames
etc
Make start scripts better (on windows make app hide in taskbar "show hidden items" tab)
*just set timer way into future? - Add admin only way of pausing lizard joining voice chat for a amount of time
*Will add - Add a list of lizard themed texts for any currently boring static messages

## v1.1 Update Notes:
*CRITICAL* Fix ML dependencies issue - sentence-transformers/huggingface_hub compatibility problem causing ImportError: cannot import name 'cached_download'. Currently using fallback mode (random responses). Need to resolve for proper embedding functionality.
*IMPORTANT* Remove database_file and guild_configs.json from distribution - these should be created by users on first run, not shipped with the executable.