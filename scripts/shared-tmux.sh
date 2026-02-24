#!/bin/sh
SOCKET=/tmp/shared-tmux.sock
WORK_SESSION=shared-tmux-work
TREE_SESSION=shared-tmux-tree
WORK_WINDOW=work
TREE_WINDOW=tree
work_status_left='#[bg=colour25,fg=colour231,bold] work #[bg=colour25,fg=colour231,bold] tree '
tree_status_left='#[bg=colour22,fg=colour231,bold] tree view '
status_right='#[bg=colour196,fg=colour231,bold] detach #[bg=colour226,fg=colour16,bold] stop '
tree_status_right='#[bg=colour196,fg=colour231,bold] detach #[bg=colour226,fg=colour16,bold] stop '

stop_all() {
  for session in "$WORK_SESSION" "$TREE_SESSION"; do
    if tmux -S "$SOCKET" has-session -t "$session" 2>/dev/null; then
      tmux -S "$SOCKET" kill-session -t "$session"
      printf "Stopped shared tmux session '%s'.\n" "$session"
    fi
  done
}

if [ "$1" = "stop" ]; then
  stop_all
  exit 0
fi

ensure_session() {
  session=$1
  window=$2
  if ! tmux -S "$SOCKET" has-session -t "$session" 2>/dev/null; then
    tmux -S "$SOCKET" new-session -d -s "$session" -n "$window"
  else
    if ! tmux -S "$SOCKET" list-windows -t "$session" | grep -q "$window"; then
      tmux -S "$SOCKET" new-window -t "$session" -n "$window"
    fi
  fi
}

configure_work_session() {
  tmux -S "$SOCKET" set-option -t "$WORK_SESSION" mouse on
  tmux -S "$SOCKET" set-option -t "$WORK_SESSION" status-bg colour237
  tmux -S "$SOCKET" set-option -t "$WORK_SESSION" status-fg colour231
  tmux -S "$SOCKET" set-option -t "$WORK_SESSION" status-interval 5
  tmux -S "$SOCKET" set-window-option -t "$WORK_SESSION" window-status-style "fg=colour250,bg=colour237"
  tmux -S "$SOCKET" set-window-option -t "$WORK_SESSION" window-status-current-style "fg=colour231,bg=colour31,bold"
  tmux -S "$SOCKET" set-option -t "$WORK_SESSION" status-left-length 40
  tmux -S "$SOCKET" set-option -t "$WORK_SESSION" status-right-length 60
  tmux -S "$SOCKET" set-option -t "$WORK_SESSION" status-left "$work_status_left"
  tmux -S "$SOCKET" set-option -t "$WORK_SESSION" status-right "$status_right"
  tmux -S "$SOCKET" bind-key -n MouseDown1StatusLeft select-window -t "$WORK_SESSION:$WORK_WINDOW"
  tmux -S "$SOCKET" bind-key -n MouseDown3StatusLeft select-window -t "$WORK_SESSION:$TREE_WINDOW"
  tmux -S "$SOCKET" bind-key -n MouseDown1StatusRight detach-client
  tmux -S "$SOCKET" bind-key -n MouseDown3StatusRight kill-session -t "$WORK_SESSION"
}

configure_tree_session() {
  tmux -S "$SOCKET" set-option -t "$TREE_SESSION" mouse on
  tmux -S "$SOCKET" set-option -t "$TREE_SESSION" status-bg colour237
  tmux -S "$SOCKET" set-option -t "$TREE_SESSION" status-fg colour231
  tmux -S "$SOCKET" set-option -t "$TREE_SESSION" status-left-length 30
  tmux -S "$SOCKET" set-option -t "$TREE_SESSION" status-right-length 60
  tmux -S "$SOCKET" set-option -t "$TREE_SESSION" status-left "$tree_status_left"
  tmux -S "$SOCKET" set-option -t "$TREE_SESSION" status-right "$tree_status_right"
  tmux -S "$SOCKET" bind-key -n MouseDown1StatusRight detach-client
  tmux -S "$SOCKET" bind-key -n MouseDown3StatusRight kill-session -t "$TREE_SESSION"
}

ensure_session "$WORK_SESSION" "$WORK_WINDOW"
ensure_session "$TREE_SESSION" "$TREE_WINDOW"
configure_work_session
configure_tree_session
sleep 0.2
tmux -S "$SOCKET" send-keys -t "$TREE_SESSION":"$TREE_WINDOW" "cd /home/bot/.openclaw/workspace && tree -L 2" C-m
printf "Shared tmux work session '%s' and tree session '%s' are running via socket %s\n" "$WORK_SESSION" "$TREE_SESSION" "$SOCKET"
printf "tmux-work → tmux -S %s attach -t %s\n" "$SOCKET" "$WORK_SESSION"
printf "tmux-tree → tmux -S %s attach -t %s\n" "$SOCKET" "$TREE_SESSION"
printf "Mouse support is on; click the status-left/right buttons if your terminal allows it.\n"
printf "To exit the work session, detach (Ctrl-b d) or use the alias. Need to stop everything? run stop-tmux.\n"
printf "start-tmux already ran this script; keep your tree/view sessions open as needed.\n"
