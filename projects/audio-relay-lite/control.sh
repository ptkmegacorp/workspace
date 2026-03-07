#!/usr/bin/env bash
set -euo pipefail

SESSION="audio-relay-lite"
ROOT="/home/bot/.openclaw/workspace/projects/audio-relay-lite"

start() {
  tmux has-session -t "$SESSION" 2>/dev/null && { echo "already running"; exit 1; }
  tmux new-session -d -s "$SESSION" -n relay "bash -lc 'cd $ROOT && chmod +x run-combined.sh && OPENCLAW_FORWARD_MODE=${OPENCLAW_FORWARD_MODE:-agent_only} OPENCLAW_REPLY_CHANNEL=${OPENCLAW_REPLY_CHANNEL:-telegram} OPENCLAW_REPLY_TO=${OPENCLAW_REPLY_TO:-8508546022} AUDIO_RELAY_SOURCE=${AUDIO_RELAY_SOURCE:-alsa_output.pci-0000_00_03.0.hdmi-stereo.monitor} ./run-combined.sh'"
  echo "started: $SESSION"
}

status() {
  tmux has-session -t "$SESSION" 2>/dev/null || { echo "not running"; exit 1; }
  tmux list-windows -t "$SESSION"
  echo '--- relay ---'
  tmux capture-pane -pt "$SESSION:relay" -S -120 | tail -n 60
}

stop() {
  tmux has-session -t "$SESSION" 2>/dev/null || { echo "already stopped"; exit 0; }
  tmux kill-session -t "$SESSION"
  echo "stopped: $SESSION"
}

case "${1:-}" in
  start) start ;;
  status) status ;;
  stop) stop ;;
  *) echo "usage: $0 {start|status|stop}"; exit 1 ;;
esac
