# Shell Alias Tracker

This file captures the custom aliases we add to our shell rc files so they stay documented and portable.

- `tmux-work` → `tmux -S /tmp/shared-tmux.sock attach -t shared-tmux-work`
- `tmux-tree` → `tmux -S /tmp/shared-tmux.sock attach -t shared-tmux-tree`
- `start-tmux` → `/home/bot/.openclaw/workspace/scripts/shared-tmux/shared-tmux-project-mode.sh --sync-tree` (starts the project-mode sessions + tree sync)
- `stop-tmux` → `/home/bot/.openclaw/workspace/scripts/shared-tmux/shared-tmux.sh stop` (kills both sessions)

Whenever we add or tweak aliases, update this file so it stays in sync with `~/.bashrc`/`~/.zshrc`. If you ever log in on a new machine, copy these entries into your rc before running the shared tmux helpers.
