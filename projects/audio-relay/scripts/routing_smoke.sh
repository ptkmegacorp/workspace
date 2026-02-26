#!/usr/bin/env bash
set -euo pipefail

QUEUE_DIR="/tmp/audio-relay/queue"
TRANSCRIPTS_DIR="/tmp/audio-relay/transcripts"
SOURCE_WAV="/tmp/audio-relay/archive/manual-20260226-092749.wav"
CLIP_ID="smoke-$(date +%Y%m%d-%H%M%S)"
CLIP_PATH="$QUEUE_DIR/$CLIP_ID.wav"
TRANSCRIPT_PATH="$TRANSCRIPTS_DIR/$CLIP_ID.json"

pass() { echo "[PASS] $*"; }
fail() { echo "[FAIL] $*"; exit 1; }

# Test 1: gateway inject path works (used as fallback signal path)
if openclaw gateway call chat.inject --params '{"sessionKey":"agent:main:main","message":"[routing-smoke] gateway-inject-ok"}' --json >/tmp/routing-smoke.inject.json 2>/dev/null; then
  if jq -e '.ok == true' /tmp/routing-smoke.inject.json >/dev/null 2>&1; then
    pass "gateway chat.inject"
  else
    fail "gateway chat.inject returned non-ok"
  fi
else
  fail "gateway chat.inject command failed"
fi

# Test 2: worker end-to-end route status should become forwarded
[[ -f "$SOURCE_WAV" ]] || fail "source wav missing: $SOURCE_WAV"
cp "$SOURCE_WAV" "$CLIP_PATH"
pass "queued probe clip $CLIP_PATH"

for _ in $(seq 1 45); do
  [[ -f "$TRANSCRIPT_PATH" ]] && break
  sleep 1
done
[[ -f "$TRANSCRIPT_PATH" ]] || fail "worker did not emit transcript: $TRANSCRIPT_PATH"

# Wait for delivery status field to be written (worker writes transcript twice).
for _ in $(seq 1 30); do
  STATUS=$(jq -r '.delivery.status // ""' "$TRANSCRIPT_PATH")
  [[ -n "$STATUS" ]] && break
  sleep 1
done

STATUS=$(jq -r '.delivery.status // ""' "$TRANSCRIPT_PATH")
REASON=$(jq -r '.delivery.reason // ""' "$TRANSCRIPT_PATH")
TEXT=$(jq -r '.text // ""' "$TRANSCRIPT_PATH")

if [[ "$STATUS" == "forwarded" ]]; then
  pass "worker delivery forwarded (text='$TEXT', reason='$REASON')"
else
  fail "worker delivery not forwarded (status='$STATUS', text='$TEXT', reason='$REASON')"
fi

echo "All routing smoke tests passed."