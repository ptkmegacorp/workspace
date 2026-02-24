# Always-On Mic Project

## What’s Done
- Documented the full pipeline (audio capture → transcription → pause detection → OpenClaw trigger → response delivery) in `pipeline.md`, including the Tailscale-aware flow and required components.
- Captured implementation-level notes in `implementation.md` describing the remote Ubuntu app, OpenClaw trigger service, and coordination/safety expectations.
- Added `scripts/pause-trigger.sh` to consume pause events and feed transcripts into `openclaw prompt` along with metadata.
- Created `tasks.md` to track completed steps and next actions on the Debian host.
- Logged the current work in today’s memory file per the workflow rules.

## What’s Next
1. Build and secure the FastAPI/Flask listener on the Debian machine to receive `/pause` events from the remote app.
2. Layer in safety controls (rate limiting, mute flag, logging) before triggering `scripts/pause-trigger.sh`.
3. Document the trigger workflow (skill or instructions) and wire the response delivery back to Telegram or the originating remote client.
4. Test the end-to-end flow by posting fake pause payloads and ensuring OpenClaw replies appear in chat.
5. Later: implement the Ubuntu-side capture app that starts/stops recording via a double-tap of Control, wraps VAD/transcription, and optionally provides TTS feedback over Tailscale.
