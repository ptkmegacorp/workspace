# Shell Alias Tracker

This file captures the custom aliases we add to our shell rc files so they stay documented and portable.

- `shared-tmux` → `tmux -S /tmp/shared-tmux.sock attach -t shared-tmux`
- `shared-tmux-tree` → `tmux -S /tmp/shared-tmux.sock select-window -t shared-tmux:project-tree`
- `start-tmux` → `~/scripts/shared-tmux.sh` (spins up the session + windows)

Whenever we add or tweak aliases, update this file so it stays in sync with `~/.bashrc`/`~/.zshrc`. If you ever log in on a new machine, copy these entries into your rc before running the shared tmux helpers.
