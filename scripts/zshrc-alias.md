# Shell Alias Tracker

This file captures the custom aliases we add to our shell rc files so they stay documented and portable.

- `tmux-work` → `tmux -S /tmp/shared-tmux.sock attach -t shared-tmux -n work`
- `tmux-tree` → `tmux -S /tmp/shared-tmux.sock attach -t shared-tmux -n project-tree`
- `start-tmux` → `/home/bot/.openclaw/workspace/scripts/shared-tmux.sh` (spins up the session + windows)
- `stop-tmux` → `/home/bot/.openclaw/workspace/scripts/shared-tmux.sh stop` (kills the shared session)

Whenever we add or tweak aliases, update this file so it stays in sync with `~/.bashrc`/`~/.zshrc`. If you ever log in on a new machine, copy these entries into your rc before running the shared tmux helpers.
