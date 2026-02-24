#!/bin/sh
SOCKET=/tmp/shared-tmux.sock
WORK_SESSION=shared-tmux-work
TREE_SESSION=shared-tmux-tree
TREE_WINDOW=tree
TREE_DEPTH=2
last=""
while sleep 1; do
  path=$(tmux -S "$SOCKET" display-message -p -t "$WORK_SESSION" "#{pane_current_path}")
  if [ -n "$path" ] && [ "$path" != "$last" ]; then
    tmux -S "$SOCKET" send-keys -t "$TREE_SESSION":"$TREE_WINDOW" \
      "cd \"$path\" && clear && printf '== SYNCED DIR: %s ==\\n' \"$path\" && tree -L $TREE_DEPTH" C-m
    last="$path"
  fi
done
