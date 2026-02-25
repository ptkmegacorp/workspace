# Audio Relay

This space coordinates Audio Relay → Whisper → delivery.
- `scripts/` holds helpers for watching upload directories and invoking Whisper.
- `scripts/watch_uploads.py` is the watcher that moves `.wav`, `.ogg`, or `.pcm` chunks from `/tmp/audio-relay/streams` (and `/tmp/audio-relay/inbox`) into `/tmp/audio-relay/queue` for downstream processing.
- `services/fastapi_app.py` exposes an upload endpoint that Audio Relay can call.
- `services/ws_server.py` listens on `/ws/audio`, persists each incoming frame as a `.wav` file, and appends a manifest entry so the watcher can detect the new chunk.
- `docs/README.md` outlines the architecture and next steps.

## External Resources
[AudioRelay.net Documentation](https://audiorelay.net/docs#linux-instructions)
This link provides official documentation for Linux Audio Relay configuration and usage.