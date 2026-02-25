# Audio Relay → Whisper Integration Plan

## Goals
- Capture the always-on Audio Relay feed and hand clips to a local Whisper service.
- Transcribe each clip, then forward the text through Telegram or another delivery channel.
- Keep monitoring/logging, allow future rate limiting or keyword detection.

## Architecture
1. **Audio Relay Stream**: Audio Relay connects over a WebSocket to `services/ws_server.py` (or the FastAPI HTTP upload for fallbacks) and streams audio frames directly into the host. Each frame is tagged and written into `/tmp/audio-relay/streams` along with metadata so the watcher can pick it up.
2. **Watcher/Queue**: The watcher (`scripts/watch_uploads.py`) observes `/tmp/audio-relay/streams`, deduplicates or batches frames, and pushes them into `/tmp/audio-relay/queue` or notifies the Whisper worker about new content.
3. **Whisper Worker**: `scripts/whisper_worker.py` polls the queue, runs faster-whisper (or another model) on each clip, and writes transcripts to `/tmp/audio-relay/transcripts` plus emit structured JSON events.
4. **Delivery Channel**: Transcripts can be piped into Telegram (via an OpenClaw prompt/bot) or another messaging service, with support for summaries or keyword alerts.
5. **Observability**: Log each clip, transcription confidence, timestamps, and delivery status in `projects/audio-relay/docs/ops.md` (or similar) to keep the pipeline auditable.

## Whisper Worker configuration
- `WHISPER_MODEL` controls the preferred faster-whisper model size. It defaults to `small`, which is a good balance for quality, but can be overridden with smaller families (e.g., `tiny`, `base`, `medium`) when you want to avoid downloading large weights during testing.
- `WHISPER_FALLBACK_MODEL` defaults to `tiny`. If the preferred model raises an exception during initialization (missing weights, incompatible device, etc.), the worker logs the failure and retries with this smaller model so transcription can keep running.
- `WHISPER_DEVICE` defaults to `auto`, letting faster-whisper choose between CPU and GPU. Set it explicitly to `cpu` when you're running tests on a machine without CUDA.

The fallback model keeps the worker resilient when the heavier `small` weights are unavailable or fail to load, which is especially useful in resource-constrained environments or fresh setups that haven't downloaded the full checkpoint yet. The loader only stops if both the preferred and fallback models fail, so you can safely experiment with different sizes without editing the code.

## Testing Status
- Initial clip-routing tests have started by pushing audio through the WebSocket and queue; still need to verify Whisper transcription and Telegram delivery end-to-end.
- Next tests: run the watcher+worker while streaming a known clip, then confirm `/tmp/audio-relay/transcripts` contains JSON, the archive folder captures the clip, and `/tmp/audio-relay/delivery.log` records the Telegram call.
- After tests, capture: any failures, adjusted env vars (TELEGRAM_BOT_TOKEN/CHAT_ID), and potential retries for the delivery helper.

## Next Steps
- Finalize the WebSocket server so Audio Relay can maintain a constant stream and drop chunks directly into the queue.
- Implement the Whisper worker queue consumer and hook it to faster-whisper (reuse the existing virtual environment and GPU/CPU config).
- Build the delivery helper to emit transcripts via Telegram or a push endpoint, including logging of success/failure.
- Add regression tests by replaying recorded clips through the WebSocket > queue > Whisper path and verifying transcripts.
