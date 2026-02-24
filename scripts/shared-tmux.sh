#!/bin/sh
SOCKET=/tmp/shared-tmux.sock
SESSION=shared-tmux
if ! tmux -S "$SOCKET" has-session -t "$SESSION" 2>/dev/null; then
  tmux -S "$SOCKET" new-session -d -s "$SESSION"
fi
printf "Shared tmux session '%s' is running via socket %s\n" "$SESSION" "$SOCKET"
printf "Attach locally: tmux -S %s attach -t %s\n" "$SOCKET" "$SESSION"
printf "Remote peers can SSH here (e.g., via Tailscale) and run the same attach command to follow along.\n"
