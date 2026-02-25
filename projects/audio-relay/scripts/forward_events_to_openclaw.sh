#!/usr/bin/env bash
set -euo pipefail

EVENT_DIR="${AUDIO_RELAY_EVENTS_DIR:-/tmp/audio-relay/events}"
STATE_FILE="${AUDIO_RELAY_EVENTS_STATE:-/tmp/audio-relay/events/.processed}"
CHANNEL="${OPENCLAW_REPLY_CHANNEL:-telegram}"
TARGET="${OPENCLAW_REPLY_TO:-8508546022}"
DRY_RUN="${DRY_RUN:-0}"

mkdir -p "$(dirname "$STATE_FILE")"
touch "$STATE_FILE"

latest="$(ls -1t "$EVENT_DIR"/*.json 2>/dev/null | head -n1 || true)"
if [[ -z "$latest" ]]; then
  echo "No events found in $EVENT_DIR"
  exit 0
fi

chunk_id="$(python3 - <<'PY' "$latest"
import json,sys
p=sys.argv[1]
with open(p) as f:d=json.load(f)
print(d.get('clip_id',''))
PY
)"

if grep -qx "$chunk_id" "$STATE_FILE"; then
  echo "Already processed: $chunk_id"
  exit 0
fi

readarray -t fields < <(python3 - <<'PY' "$latest"
import json,sys
p=sys.argv[1]
with open(p) as f:d=json.load(f)
print('1' if d.get('delivery',{}).get('status') in ('event_only','forwarded') or d.get('gate_passed',False) else '0')
print((d.get('text') or '').strip())
PY
)

pass="${fields[0]:-0}"
text="${fields[1]:-}"

if [[ "$pass" != "1" || -z "$text" ]]; then
  echo "Skipping $chunk_id (not passable or empty text)"
  echo "$chunk_id" >> "$STATE_FILE"
  exit 0
fi

if [[ "$DRY_RUN" == "1" ]]; then
  echo "DRY_RUN would send: [$chunk_id] $text"
  echo "$chunk_id" >> "$STATE_FILE"
  exit 0
fi

openclaw agent --channel "$CHANNEL" --to "$TARGET" --message "$text" --deliver --timeout 120

echo "$chunk_id" >> "$STATE_FILE"
echo "Forwarded $chunk_id"
