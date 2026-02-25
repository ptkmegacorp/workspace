# Audio Relay → Whisper Integration Plan

## Quickstart
1. **Install prerequisites**: make sure you have `tmux`, `fastapi`, `uvicorn`, `faster-whisper`, `requests`, and `openwakeword` available. A quick start is:
   ```bash
   sudo apt install -y tmux python3-pip
   python3 -m pip install --break-system-packages fastapi uvicorn faster-whisper requests openwakeword
   ```
2. **Start the pipeline** with the bundled controller so capture, watcher, and worker come up in one tmux session:
   ```bash
   ./projects/audio-relay/scripts/control.sh start
   ```
3. **Inspect the runtime** by tailing the panes or rerunning the controller with `status`:
   ```bash
   ./projects/audio-relay/scripts/control.sh status
   ```
   The controller shows the tmux windows and the last few lines from each pane so you can confirm the WebSocket server, watcher, and worker are alive.
4. **Stop everything** when you are done:
   ```bash
   ./projects/audio-relay/scripts/control.sh stop
   ```
   The script kills the tmux session cleanly and leaves the `/tmp/audio-relay` buckets in place for the next start.

## Environment Variables
- `AUDIO_RELAY_WS_PORT` (default `8765`): port exposed by `services/ws_server.py` for Audio Relay to stream frames into.
- `AUDIO_RELAY_SESSION` (default `audio-relay`): tmux session name used by `scripts/control.sh` to orchestrate the capture, watcher, and worker panes.
- `WHISPER_MODEL`, `WHISPER_FALLBACK_MODEL`, `WHISPER_DEVICE`: control the faster-whisper model families and device used by `scripts/whisper_worker.py`. Defaults are `small`, `tiny`, and `auto` respectively.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`: required when the worker should deliver transcripts via Telegram. Missing values cause the delivery helper to raise unless `DISABLE_TELEGRAM_OUTPUT` is set.
- `AUDIO_RELAY_DELIVERY_LOG`: override path for `/tmp/audio-relay/delivery.log` if you want to capture delivery audit trails elsewhere.
- `AUDIO_RELAY_WAKE_PHRASE` (default `byte`): normalized token that must appear in transcripts before `ROUTE_TO_OPENCLAW_AGENT` forwards a message. Use this to gate responses to an explicit wake-up cue.
- `AUDIO_RELAY_WAKE_PHRASE_BUBBLE` (default `1`/true): when enabled, the worker emits an auxiliary Telegram message whenever the wake phrase is detected so you can observe the gating behavior live.
- `ROUTE_TO_OPENCLAW_AGENT`: set to `1`/`true` to forward transcripts to `openclaw agent` instead of sending Telegram messages directly. When enabled, wake phrase, cooldown, and duplicate filtering are enforced.
- `OPENCLAW_REPLY_CHANNEL` (default `telegram`) and `OPENCLAW_REPLY_TO` (falls back to `TELEGRAM_CHAT_ID`): configure where `openclaw agent` should deliver the forwarded text.
- `DISABLE_TELEGRAM_OUTPUT`: set to `1` to skip Telegram delivery entirely and keep transcripts local while you iterate.
- `AUDIO_RELAY_MIN_FORWARD_CHARS` and `AUDIO_RELAY_FORWARD_COOLDOWN_SECONDS`: adjust the gating thresholds for `ROUTE_TO_OPENCLAW_AGENT`, ensuring short clips or repeated phrases do not flood the agent.
- `AUDIO_RELAY_REQUIRE_SENTENCE_PUNCTUATION` (default `1`): when enabled, transcripts must include sentence punctuation (`?`, `.`, `!`) before forwarding.
- `AUDIO_RELAY_INTENT_KEYWORDS` (regex) + `AUDIO_RELAY_REQUIRE_INTENT_KEYWORDS` (default `0`): optional intent filter. Set `REQUIRE...=1` to require a keyword hit before forwarding.
- `AUDIO_RELAY_RETENTION_HOURS`, `AUDIO_RELAY_MAX_QUEUE_AGE_SECONDS`, and `AUDIO_RELAY_MAX_QUEUE_CLIPS`: tune cleanup behavior for transcripts, archived audio, and queue overflow.
- `AUDIO_RELAY_ENABLE_WAKEWORD` (default `0` in script, `1` in systemd watcher example): enable `openWakeWord` gating in the watcher so only wake hits reach Whisper.
- `AUDIO_RELAY_WAKEWORD_THRESHOLD` (default `0.5`): minimum wake score required for enqueue.
- `AUDIO_RELAY_WAKEWORD_TARGETS` (comma list, default `byte`): wake model label matching rule; if empty, any model score above threshold can pass.

## Testing & Wake Phrase Behavior
1. **Start the services** with `./projects/audio-relay/scripts/control.sh start` so capture, watcher, and worker run inside tmux.
2. **Produce a clip** and drop it into the queue for processing:
   ```bash
   ffmpeg -f lavfi -i "sine=frequency=440:duration=2" /tmp/audio-relay/queue/test-sine.wav
   ```
3. **Watch the worker logs** (via `status` or `tmux attach`) and confirm `/tmp/audio-relay/transcripts/test-sine.json` appears. The delivery helper should log to `/tmp/audio-relay/delivery.log` or forward through Telegram/OpenClaw depending on your config.
4. **Validate wake phrase + intent gating** by setting `ROUTE_TO_OPENCLAW_AGENT=1` and tuning `AUDIO_RELAY_WAKE_PHRASE`:
   - Only transcripts that contain the normalized wake phrase, pass `AUDIO_RELAY_MIN_FORWARD_CHARS`, and satisfy punctuation/intent filters are forwarded to `openclaw agent`.
   - When `AUDIO_RELAY_REQUIRE_SENTENCE_PUNCTUATION=1`, clipped fragments without `?`, `.`, or `!` are skipped.
   - Optional keyword gating: set `AUDIO_RELAY_REQUIRE_INTENT_KEYWORDS=1` and tune `AUDIO_RELAY_INTENT_KEYWORDS` for stricter intent detection.
   - When `AUDIO_RELAY_WAKE_PHRASE_BUBBLE` is enabled, the worker still sends a short `"Wake phrase detected"` Telegram message so you can see activations even when the main transcript is rerouted through OpenClaw.
   - Lower the cooldown by adjusting `AUDIO_RELAY_FORWARD_COOLDOWN_SECONDS` if you want faster turnarounds during testing, but keep it ≥8 seconds to avoid duplicate suppression.
   - If OpenClaw Telegram ingest still drops valid requests, set Telegram adapter `requireMention: false` in your OpenClaw config so voice messages do not need an explicit @mention.
5. **Stop** with `./projects/audio-relay/scripts/control.sh stop` once the smoke test finishes.

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
