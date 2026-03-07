# audio-relay-lite

Minimal AudioRelay -> Whisper -> OpenClaw pipeline.

## What it does
- `recorder.js`: double-tap Ctrl (via `xev`) to start/stop ffmpeg recording.
- saves clips into `/tmp/audio-relay-lite/queue`.
- `worker.js`: picks queued clips, transcribes with faster-whisper, forwards text to OpenClaw.
- `control.sh`: runs both in one tmux session so you can see REC START/STOP + worker logs.

## Run
```bash
cd /home/bot/.openclaw/workspace/projects/audio-relay-lite
bash control.sh start
bash control.sh status
bash control.sh stop
```

## Env (optional)
- `AUDIO_RELAY_SOURCE` (default: `default`)
- `OPENCLAW_REPLY_CHANNEL` (default: `telegram`)
- `OPENCLAW_REPLY_TO` (chat id; optional)
- `WHISPER_MODEL` (default: `tiny`)
- `WAKE_PHRASE` (default: `byte`; set empty to disable)
