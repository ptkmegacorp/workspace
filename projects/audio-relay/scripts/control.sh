#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SESSION_NAME="${AUDIO_RELAY_SESSION:-audio-relay}"
TMUX_BIN="${TMUX_BIN:-tmux}"

WS_PORT="${AUDIO_RELAY_WS_PORT:-8765}"
SOURCE_DIRS=("/tmp/audio-relay/streams" "/tmp/audio-relay/inbox" "/tmp/audio-relay/queue" "/tmp/audio-relay/transcripts" "/tmp/audio-relay/archive")

function ensure_tmux_installed() {
  if ! command -v "$TMUX_BIN" >/dev/null 2>&1; then
    echo "tmux not found in PATH. Install tmux to use this control script." >&2
    exit 1
  fi
}

function ensure_runtime_dirs() {
  for dir in "${SOURCE_DIRS[@]}"; do
    mkdir -p "$dir"
  done
}

function start_services() {
  ensure_tmux_installed
  if "$TMUX_BIN" has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Audio relay session '$SESSION_NAME' is already running. Use 'status' to inspect it." >&2
    exit 1
  fi

  ensure_runtime_dirs

  echo "Starting audio relay session '$SESSION_NAME' (tmux)."

  local capture_cmd="cd \"$PROJECT_ROOT\" && PYTHONPATH=\"$PROJECT_ROOT\" AUDIO_RELAY_WS_PORT=\"$WS_PORT\" uvicorn services.ws_server:app --host 0.0.0.0 --port \"$WS_PORT\""
  local watcher_cmd="cd \"$PROJECT_ROOT\" && AUDIO_RELAY_ENABLE_WAKEWORD=1 AUDIO_RELAY_WAKEWORD_THRESHOLD=0.35 AUDIO_RELAY_WAKEWORD_TARGETS=hey_jarvis python3 scripts/watch_uploads.py"
  local worker_cmd="cd \"$PROJECT_ROOT\" && PYTHONPATH=\"$PROJECT_ROOT\" python3 scripts/whisper_worker.py"

  "$TMUX_BIN" new-session -d -s "$SESSION_NAME" -n capture bash -lc "$capture_cmd"
  "$TMUX_BIN" new-window -t "$SESSION_NAME" -n watcher bash -lc "$watcher_cmd"
  "$TMUX_BIN" new-window -t "$SESSION_NAME" -n worker bash -lc "$worker_cmd"

  echo "Services started. Use '$0 status' for runtime status or 'tmux attach -t $SESSION_NAME' to watch live logs."
}

function describe_status() {
  ensure_tmux_installed
  if ! "$TMUX_BIN" has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Audio relay session '$SESSION_NAME' is not running."
    exit 1
  fi

  echo "Audio relay session '$SESSION_NAME' is running. Windows:"
  "$TMUX_BIN" list-windows -t "$SESSION_NAME"
  echo
  for window in capture watcher worker; do
    echo "--- $window window output (last 5 lines) ---"
    if ! "$TMUX_BIN" capture-pane -pt "$SESSION_NAME:$window" >/tmp/audrelay.log 2>&1; then
      echo "(unable to capture pane output for $window)"
    else
      tail -n 5 /tmp/audrelay.log
    fi
  done
  rm -f /tmp/audrelay.log
}

function stop_services() {
  ensure_tmux_installed
  if ! "$TMUX_BIN" has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Audio relay session '$SESSION_NAME' is already stopped."
    exit 0
  fi

  "$TMUX_BIN" kill-session -t "$SESSION_NAME"
  echo "Audio relay session '$SESSION_NAME' stopped."
}

function usage() {
  cat <<EOF
Usage: $0 {start|status|stop|help}

Commands:
  start   Start capture, watcher, and worker inside a tmux session named $SESSION_NAME.
  status  Tail the last few lines from capture/watcher/worker panes.
  stop    Kill the tmux session and attached services.
  help    Display this usage message.
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

case "$1" in
  start)
    start_services
    ;;
  status)
    describe_status
    ;;
  stop)
    stop_services
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
