#!/bin/sh
SOCKET=/tmp/shared-tmux.sock
SESSION=shared-tmux
WINDOW_WORK=work
WINDOW_TREE=project-tree
if [ "$1" = "stop" ]; then
  if tmux -S "$SOCKET" has-session -t "$SESSION" 2>/dev/null; then
    tmux -S "$SOCKET" kill-session -t "$SESSION"
    printf "Stopped shared tmux session '%s'.\n" "$SESSION"
  else
    printf "No shared tmux session was running.\n"
  fi
  exit 0
fi
if ! tmux -S "$SOCKET" has-session -t "$SESSION" 2>/dev/null; then
  tmux -S "$SOCKET" new-session -d -s "$SESSION" -n "$WINDOW_WORK"
else
  if ! tmux -S "$SOCKET" list-windows -t "$SESSION" | grep -q "$WINDOW_WORK"; then
    tmux -S "$SOCKET" new-window -t "$SESSION" -n "$WINDOW_WORK"
  fi
fi
if ! tmux -S "$SOCKET" list-windows -t "$SESSION" | grep -q "$WINDOW_TREE"; then
  tmux -S "$SOCKET" new-window -t "$SESSION" -n "$WINDOW_TREE"
fi
tmux -S "$SOCKET" set-option -t "$SESSION" mouse on
sleep 0.2
tmux -S "$SOCKET" send-keys -t "$SESSION":"$WINDOW_TREE" "cd /home/bot/.openclaw/workspace && tree -L 2" C-m
printf "Shared tmux session '%s' is running via socket %s\n" "$SESSION" "$SOCKET"
printf "work = tmux-work   (alias for entering the work window)\n"
printf "tree = tmux-tree   (alias for switching to the project-tree overview)\n"
printf "Mouse support is on, so you can click the window names if your terminal supports it.\n"
printf "start-tmux already ran this script; use tmux-work or tmux-tree as needed.\n"
printf "To exit back to your normal shell, press Ctrl-b d, run 'tmux detach', or hit 'q' inside a pager.\n"
printf "Need to stop everything? Use stop-tmux to kill the shared session.\n"
