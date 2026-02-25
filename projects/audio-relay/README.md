# Audio Relay

This space coordinates Audio Relay → Whisper → delivery.
- `scripts/` holds helpers for watching upload directories and invoking Whisper.
- `scripts/watch_uploads.py` is the watcher that moves `.wav`, `.ogg`, or `.pcm` chunks from `/tmp/audio-relay/streams` (and `/tmp/audio-relay/inbox`) into `/tmp/audio-relay/queue` for downstream processing.
- Wake-word gating is now integrated in the watcher via `openWakeWord`, so clips can be filtered *before* Whisper runs (`/tmp/audio-relay/rejected` keeps misses for debugging).
- `scripts/capture_audiorelay.sh` discovers the dedicated AudioRelay Pulse source (not the HDMI monitor) and writes chunked `chunk-YYYYMMDD-HHMMSS.wav` files into `/tmp/audio-relay/inbox` for the watcher. Chunk length, gap, and sample parameters can be tuned via environment variables.
- `scripts/calibrate_audiorelay.sh` records a 5-10s sample from the captured source, prints `volumedetect`/source metadata, and removes the test file so you can tune gain before the worker runs.
- `scripts/health_check.py` reports capture/queue/worker activity so you can detect stalls from cron or fast failure hooks.
- `services/fastapi_app.py` exposes an upload endpoint that Audio Relay can call.
- `services/ws_server.py` listens on `/ws/audio`, persists each incoming frame as a `.wav` file, and appends a manifest entry so the watcher can detect the new chunk.
- `services/systemd/` contains example user-level units to keep capture, watcher, and Whisper worker services running with automatic restart and explicit environment placeholders.
- `docs/README.md` outlines the architecture and next steps.

## External Resources
[AudioRelay.net Documentation](https://audiorelay.net/docs#linux-instructions)
This link provides official documentation for Linux Audio Relay configuration and usage.