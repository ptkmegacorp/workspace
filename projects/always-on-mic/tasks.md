# Always-On Mic Worklog & To-do

## Completed so far
- [x] Documented the high-level pipeline for audio capture → transcription → OpenClaw trigger → response delivery (`pipeline.md`).
- [x] Captured implementation notes for the remote Ubuntu app and the Debian-host trigger (`implementation.md`).
- [x] Added `projects/always-on-mic/bin/pause-trigger.sh` to invoke `openclaw prompt` from a JSON payload.

## Next tasks (Debian host scope)
1. **Build the FastAPI listener** that accepts `/pause` events, validates Tailscale session IDs, and pipes payloads into `projects/always-on-mic/bin/pause-trigger.sh`.
2. **Wire a safety/override layer** (mute flag, rate limit, logging) that the listener checks before invoking the script.
3. **Package a helper skill or documentation** describing the `pause-trigger` workflow (e.g., `projects/always-on-mic/skills/pause-responder`).
4. **Hook response delivery**: capture the CLI output and send it via Telegram or a callback to whichever remote client posted the event.
5. **Test end-to-end** by simulating a POST from the remote app, ensuring OpenClaw replies appear in the chat.

## Remote-app progress
- [x] Implemented the double-Control capture helper (`capture.py`) plus README for the Ubuntu client. The script records with VAD, concatenates voiced chunks, optionally runs Whisper, and uploads the bundle to the Debian host.
- [ ] Wire a response callback (HTTP polling or UDP) so the remote client can surface OpenClaw replies or play them back via TTS after the POST completes.
- [ ] Add a remote health/visibility command (e.g., `pull-status`) that shows whether the host is reachable before recording.

## Host-side plan
1. **FastAPI listener** – Accept multipart `/pause` POSTs with audio metadata, save the upload, and pass metadata to `bin/pause-trigger.sh` for OpenClaw responses.
2. **Safety layer** – Validate session ID, enforce rate limits, respect mute overrides, and log each event before invoking the trigger.
3. **Response webhook** – Return a JSON payload so the remote side can poll a callback; include any callback URL or UDP details in the body.
4. **Documentation** – Create `host/README.md` that explains the endpoints, env vars, and how to run the listener alongside the remote helper.
