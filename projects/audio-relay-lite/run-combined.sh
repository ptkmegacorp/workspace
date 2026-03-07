#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/bot/.openclaw/workspace/projects/audio-relay-lite"
cd "$ROOT"

mkdir -p runtime
: > runtime/combined.log

AUDIO_RELAY_SOURCE="${AUDIO_RELAY_SOURCE:-alsa_output.pci-0000_00_03.0.hdmi-stereo.monitor}" \
  node recorder.js >> runtime/combined.log 2>&1 &
REC_PID=$!

OPENCLAW_FORWARD_MODE="${OPENCLAW_FORWARD_MODE:-agent_only}" \
OPENCLAW_REPLY_CHANNEL="${OPENCLAW_REPLY_CHANNEL:-telegram}" \
OPENCLAW_REPLY_TO="${OPENCLAW_REPLY_TO:-8508546022}" \
  node worker.js >> runtime/combined.log 2>&1 &
WRK_PID=$!

WEB_PORT="${WEB_PORT:-3092}" node web.js >> runtime/combined.log 2>&1 &
WEB_PID=$!

cleanup() {
  kill "$REC_PID" "$WRK_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Single unified output stream for tmux window
exec tail -n +1 -f runtime/combined.log
