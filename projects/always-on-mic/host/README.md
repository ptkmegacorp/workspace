# Always-on-mic Host Listener

This folder contains the Debian-host FastAPI service that receives `/pause` events from the Ubuntu remote app, enforces safety guards, and forwards transcripts/audio to `projects/always-on-mic/bin/pause-trigger.sh`.

## Endpoints
- `POST /pause` (multipart): Accepts `session_id`, `timestamp`, optional `transcript`, and an `audio` file (`wav` or `ogg`). Validates the session, checks rate limits (default one event per 5 seconds), enforces the `MUTE` flag, saves the upload under `uploads/`, and pipes metadata + audio path to the trigger script.
- `GET /status`: Returns `{"status": "ok", "last_trigger": ...}` for monitoring and health checks.

## Configuration
Use env vars (or load via a `.env` file) to adjust behavior:
- `ALLOWED_SESSIONS` – comma-separated session IDs allowed to trigger the pipeline. Defaults to `*` (any session).
- `MUTE` – set to `1` to temporarily ignore pause events (still nets status OK).
- `RATE_LIMIT_S` – minimum seconds between triggers per session (default 5).
- `CALLBACK_URL` – included in the JSON response so the remote helper knows where to poll for replies.
- `PAUSE_TRIGGER_TIMEOUT` – timeout in seconds when invoking `pause-trigger.sh`.

## Running
```bash
pip install fastapi uvicorn python-dotenv
cd projects/always-on-mic/host
uvicorn listener:app --host 0.0.0.0 --port 8000
```
Set `REMOTE_HOST_URL` on the Ubuntu side to hit this API.

## Tracing
- The service logs every POST, rate-limit block, and trigger invocation. Look in `/var/log` or the terminal for `triggered`, `rate limited`, and `mute` entries.
- Uploaded audio files remain under `uploads/` for troubleshooting; rotate/clean them as needed.
