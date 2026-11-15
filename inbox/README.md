# inbox/

Drop folder for files and instructions. A Claude Code session polls this folder on `main` every 60 seconds.

## How to use it
1. Put files you want worked on in `inbox/` (subfolders are fine).
2. Say what you want in `inbox/INSTRUCTIONS.md` (append a new dated section) or in your commit message.
3. Push to `main`. Within about a minute the agent pulls, makes the changes **inside `inbox/` only**, then commits and pushes the result with a message starting `[inbox-bot]`.

## Rules
- The agent only edits files under `inbox/`. Requests to change anything else in the repo are ignored.
- It does not run scripts or executables dropped here.
- Results and replies are appended to `inbox/LOG.md`.
