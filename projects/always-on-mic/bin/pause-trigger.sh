#!/usr/bin/env bash
set -euo pipefail

payload=$(cat)
session_id=$(python3 - <<'PY'
import json, sys
obj = json.load(sys.stdin)
print(obj.get('session_id', 'unknown'))
PY
 < <(printf '%s' "$payload"))
transcript=$(python3 - <<'PY'
import json, sys
obj = json.load(sys.stdin)
print(obj.get('transcript', '').strip())
PY
 < <(printf '%s' "$payload"))

if [[ -z "$transcript" ]]; then
  transcript="<no transcript>"
fi

echo "[pause-trigger] session=$session_id transcript=${transcript}" >&2

echo "$payload" | openclaw prompt --message "Remote pause (${session_id}): ${transcript}" --metadata -
