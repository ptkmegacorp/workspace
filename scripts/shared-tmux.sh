#!/bin/sh
SOCKET=/tmp/shared-tmux.sock
SESSION=shared-tmux
WINDOW_WORK=work
WINDOW_TREE=project-tree
if ! tmux -S "$SOCKET" has-session -t "$SESSION" 2>/dev/null; then
  tmux -S "$SOCKET" new-session -d -s "$SESSION" -n "$WINDOW_WORK"
else
  tmux -S "$SOCKET" list-windows -t "$SESSION" | grep -q "$WINDOW_WORK" || tmux -S "$SOCKET" new-window -t "$SESSION" -n "$WINDOW_WORK"
fi
if ! tmux -S "$SOCKET" list-windows -t "$SESSION" | grep -q "$WINDOW_TREE"; then
  tmux -S "$SOCKET" new-window -t "$SESSION" -n "$WINDOW_TREE"
fi
tmux -S "$SOCKET" send-keys -t "$SESSION":"$WINDOW_TREE" "cd /home/bot/.openclaw/workspace && tree -L 2" C-m
printf "Shared tmux session '%s' is running via socket %s\n" "$SESSION" "$SOCKET"
printf "Attach locally to the work window: tmux -S %s attach -t %s\n" "$SOCKET" "$SESSION"
printf "Use `tmux -S %s select-window -t %s:%s` for the project tree overview window.\n" "$SOCKET" "$SESSION" "$WINDOW_TREE"
printf "Remote peers can SSH here (e.g., via Tailscale) and run the same attach/select commands to follow along.\n"
