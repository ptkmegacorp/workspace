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

## Future remote-app tasks (after host is ready)
- Create the Bash/Python wrapper for microphone capture + VAD + HTTP posting.
- Implement optional local Whisper transcription + fallback to host-owned transcription.
- Add an interactive remote-mode CLI that can play back OpenClaw responses via TTS over Tailscale.
