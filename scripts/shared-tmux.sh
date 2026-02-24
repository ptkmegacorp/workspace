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
tmux -S "$SOCKET" set-option -t "$SESSION" status-bg colour237
tmux -S "$SOCKET" set-option -t "$SESSION" status-fg colour231
tmux -S "$SOCKET" set-option -t "$SESSION" status-interval 5

# pretty theme
tmux -S "$SOCKET" set-window-option -t "$SESSION" window-status-style "fg=colour250,bg=colour237"
tmux -S "$SOCKET" set-window-option -t "$SESSION" window-status-current-style "fg=colour231,bg=colour31,bold"
tmux -S "$SOCKET" set-option -t "$SESSION" status-left-length 40
tmux -S "$SOCKET" set-option -t "$SESSION" status-right-length 60

# buttons
tmux -S "$SOCKET" set-option -t "$SESSION" status-left '#[bg=colour25,fg=colour231,bold] work #[bg=colour25,fg=colour231,bold] tree '
tmux -S "$SOCKET" set-option -t "$SESSION" status-right '#[bg=colour196,fg=colour231,bold] detach #[bg=colour226,fg=colour16,bold] stop '
tmux -S "$SOCKET" bind-key -n MouseDown1StatusLeft select-window -t "$SESSION:work"
tmux -S "$SOCKET" bind-key -n MouseDown3StatusLeft select-window -t "$SESSION:project-tree"
tmux -S "$SOCKET" bind-key -n MouseDown1StatusRight detach-client
tmux -S "$SOCKET" bind-key -n MouseDown3StatusRight kill-session -t "$SESSION"
tmux -S "$SOCKET" set-option -t "$SESSION" mouse on
sleep 0.2
tmux -S "$SOCKET" send-keys -t "$SESSION":"$WINDOW_TREE" "cd /home/bot/.openclaw/workspace && tree -L 2" C-m
printf "Shared tmux session '%s' is running via socket %s\n" "$SESSION" "$SOCKET"
printf "work = tmux-work   (alias for entering the work window)\n"
printf "tree = tmux-tree   (alias for switching to the project-tree overview)\n"
printf "Mouse support is on, so you can click the window names and the status-right controls if your terminal supports it.\n"
printf "MouseLeft (status-left) = switch to work window, MouseRight (status-left) = switch to tree window.\n"
printf "MouseLeft (status-right) = detach, MouseRight (status-right) = stop the session.\n"
printf "start-tmux already ran this script; use tmux-work or tmux-tree as needed.\n"
printf "To exit back to your normal shell, press Ctrl-b d, run 'tmux detach', or hit 'q' inside a pager (or click Detach).\n"
printf "Need to stop everything? Use stop-tmux, the status-right exit button, or kill the session.\n"
