#!/usr/bin/env python3
import glob
import json
from pathlib import Path

files = sorted(glob.glob('/tmp/audio-relay/transcripts/chunk-*.json'))
if not files:
    print('No transcript files found.')
    raise SystemExit(1)

path = Path(files[-1])
data = json.loads(path.read_text())
print(f'file: {path.name}')
print(f"text: {data.get('text','')!r}")
print(f"delivery: {data.get('delivery')}")
print(f"skip_reason: {data.get('skip_reason')}")
print(f"vad: {data.get('vad')}")
