#!/bin/sh
# Wrapper/playbook for Project Mode: ensures our two gadgets (work & tree) exist,
# keeps the UXterm windows attached, and optionally keeps the tree session in sync
# with whatever directory the work pane is in.
# It builds on scripts/shared-tmux/shared-tmux.sh; the shared script can still run on its own, but
# the wrapper automates the UXterm windows and pairing/sync flags for display mode.

SOCKET=/tmp/shared-tmux.sock
WORK_SESSION=shared-tmux-work
TREE_SESSION=shared-tmux-tree
WORK_WINDOW=work
TREE_WINDOW=tree
UXTERM_WORK_TITLE="shared-work"
UXTERM_TREE_TITLE="shared-tree"
UXTERM_WORK_GEOMETRY="854x973+494+77"
UXTERM_TREE_GEOMETRY="464x973+21+77"
SYNC_TREE=0
SYNC_LOOP_PID=/tmp/pm-tree-sync-loop.pid

usage() {
  cat <<'EOF'
Usage: shared-tmux-project-mode.sh [--sync-tree]
Start/attach the Project Mode tmux sessions; --sync-tree sets up an automatic
update hook so shared-tmux-tree always mirrors the work pane's current directory.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --sync-tree)
      SYNC_TREE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown flag: $1" >&2
      usage
      exit 1
      ;;
  esac
done

ensure_session() {
  session=$1
  window=$2
  if ! tmux -S "$SOCKET" has-session -t "$session" 2>/dev/null; then
    tmux -S "$SOCKET" new-session -d -s "$session" -n "$window"
  else
    tmux -S "$SOCKET" list-windows -t "$session" | grep -q "$window" >/dev/null 2>&1 || \
      tmux -S "$SOCKET" new-window -t "$session" -n "$window"
  fi
}

# Launch uxterms (non-blocking) that attach to work/tree sessions and remember them.
ensure_uxterm() {
  title=$1
  target=$2
  geometry=$3
  existing=$(DISPLAY=:0 xdotool search --onlyvisible --name "$title" 2>/dev/null)
  if [ -n "$existing" ]; then
    # If it's already there, just reattach
    DISPLAY=:0 xdotool windowactivate "$existing"
  else
    DISPLAY=:0 uxterm -title "$title" -e "tmux -S $SOCKET attach -t $target" >/tmp/uxterm-${title}.log 2>&1 &
  fi
  # always enforce geometry after ensuring window exists
  if [ -n "$geometry" ]; then
    geom_id="$(sleep 1 && DISPLAY=:0 xdotool search --name "$title" 2>/dev/null | head -n1)"
    if [ -n "$geom_id" ]; then
      size=${geometry%%+*}
      width=${size%x*}
      height=${size#*x}
      offset=${geometry#*+}
      pos_x=${offset%%+*}
      pos_y=${offset#*+}
      [ -n "$width" ] && [ -n "$height" ] && DISPLAY=:0 xdotool windowsize "$geom_id" "$width" "$height"
      [ -n "$pos_x" ] && [ -n "$pos_y" ] && DISPLAY=:0 xdotool windowmove "$geom_id" "$pos_x" "$pos_y"
    fi
  fi
}

ensure_session "$WORK_SESSION" "$WORK_WINDOW"
ensure_session "$TREE_SESSION" "$TREE_WINDOW"
ensure_uxterm "$UXTERM_WORK_TITLE" "$WORK_SESSION:$WORK_WINDOW" "$UXTERM_WORK_GEOMETRY"
ensure_uxterm "$UXTERM_TREE_TITLE" "$TREE_SESSION:$TREE_WINDOW" "$UXTERM_TREE_GEOMETRY"

if [ "$SYNC_TREE" -eq 1 ]; then
  if [ -f "$SYNC_LOOP_PID" ]; then
    kill "$(cat "$SYNC_LOOP_PID")" >/dev/null 2>&1 || true
  fi
  nohup "$PWD/scripts/shared-tmux/pm-tree-sync-loop.sh" >/tmp/pm-tree-sync-loop.log 2>&1 &
  echo $! >"$SYNC_LOOP_PID"
fi

printf "Project mode sessions ready. Work session: %s; Tree session: %s\n" "$WORK_SESSION" "$TREE_SESSION"
printf "Use uxterm titles '%s' and '%s' on display :0 to follow along.\n" "$UXTERM_WORK_TITLE" "$UXTERM_TREE_TITLE"
if [ "$SYNC_TREE" -eq 1 ]; then
  printf "Tree sync is enabled via the project-mode sync loop.\n"
else
  printf "Run with --sync-tree to mirror work directory changes in the tree pane.\n"
fi
