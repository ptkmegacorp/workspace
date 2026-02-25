#!/usr/bin/env bash
set -euo pipefail

NODE_BIN_DIR="${NODE_BIN_DIR:-/home/bot/.npm-global/bin}"
PATH_EXTRA="$PATH"
if [[ -d "$NODE_BIN_DIR" ]]; then
  PATH_EXTRA="$NODE_BIN_DIR:$PATH"
  export PATH="$PATH_EXTRA"
fi
PATH_ENV="PATH=$PATH_EXTRA"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SESSION_NAME="${AUDIO_RELAY_SESSION:-audio-relay}"
TMUX_BIN="${TMUX_BIN:-tmux}"

WS_PORT="${AUDIO_RELAY_WS_PORT:-8765}"
ENABLE_WATCHER="${AUDIO_RELAY_ENABLE_WATCHER:-1}"
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

  local capture_cmd="cd \"$PROJECT_ROOT\" && AUDIO_RELAY_CAPTURE_GAIN=20.0 AUDIO_RELAY_CHUNK_SECONDS=5 AUDIO_RELAY_CHUNK_GAP_SECONDS=0.1 bash scripts/capture_audiorelay.sh"
  local watcher_cmd="cd \"$PROJECT_ROOT\" && AUDIO_RELAY_ENABLE_WAKEWORD=0 python3 scripts/watch_uploads.py"
  local worker_cmd="cd \"$PROJECT_ROOT\" && PYTHONPATH=\"$PROJECT_ROOT\" AUDIO_RELAY_MIN_FORWARD_CHARS=1 AUDIO_RELAY_WAKE_PHRASE='' AUDIO_RELAY_WAKE_ALIASES='' AUDIO_RELAY_WAKE_PHRASE_BUBBLE=0 AUDIO_RELAY_FORWARD_COOLDOWN_SECONDS=0 AUDIO_RELAY_DUPLICATE_SUPPRESSION_SECONDS=0 AUDIO_RELAY_MAX_QUEUE_AGE_SECONDS=300 AUDIO_RELAY_MAX_QUEUE_CLIPS=50 AUDIO_RELAY_ENABLE_WEBRTCVAD=0 AUDIO_RELAY_FORCE_LANGUAGE=en AUDIO_RELAY_EVENT_ONLY=1 ROUTE_TO_OPENCLAW_AGENT=0 OPENCLAW_REPLY_CHANNEL=telegram OPENCLAW_REPLY_TO=8508546022 python3 scripts/whisper_worker.py"

  "$TMUX_BIN" new-session -d -s "$SESSION_NAME" -n capture bash -lc "$capture_cmd"
  if [[ "$ENABLE_WATCHER" == "1" ]]; then
    "$TMUX_BIN" new-window -t "$SESSION_NAME" -n watcher bash -lc "$watcher_cmd"
  fi
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
  local windows
  windows=$("$TMUX_BIN" list-windows -t "$SESSION_NAME" -F '#W')
  while IFS= read -r window; do
    [[ -z "$window" ]] && continue
    echo "--- $window window output (last 5 lines) ---"
    if ! "$TMUX_BIN" capture-pane -pt "$SESSION_NAME:$window" >/tmp/audrelay.log 2>&1; then
      echo "(unable to capture pane output for $window)"
    else
      tail -n 5 /tmp/audrelay.log
    fi
  done <<< "$windows"
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
  start   Start capture + worker (and optional watcher when AUDIO_RELAY_ENABLE_WATCHER=1) in tmux session $SESSION_NAME.
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
