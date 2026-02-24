# Always-on-mic Remote Workflow

This folder holds the Ubuntu-side companion for the always-on-mic system. The remote app is a minimalist listener that waits for a double Control key press to open and close a recording window, filters the live microphone feed with VAD, optionally runs a local Whisper transcription, and delivers the result to the Debian host over HTTP.

## Workflow

1. **Double-Control toggle** – The Python helper (`capture.py`) hooks a `ctrl, ctrl` hotkey using the `keyboard` library. The first double press enters a recording window; the next double press ends it. This keeps the mic capture entirely demand-driven without a persistent GUI.

2. **Chunked capture + VAD** – While the window is open, the script records short chunks (1–3 seconds) via `sounddevice`. Each chunk is converted to PCM frames and evaluated using `webrtcvad`. Any chunk classified as speech is cached for later; silence is discarded.

3. **Packaging + metadata** – When the window closes the buffered speech chunks are stitched together into a single WAV/OGG file (configurable inside `capture.py`). Metadata—including `session_id`, UTC timestamp, chunk duration, and optionally the Whisper transcript—is prepared alongside the binary payload.

4. **POST to Debian host** – The combined audio is uploaded via `POST` to the `REMOTE_HOST_URL` endpoint. Retries are handled with exponential backoff. The host is expected to reply with a JSON payload; the script logs the response status and any message.

5. **Optional transcription** – If `ENABLE_TRANSCRIPTION=true` (via environment/config), `capture.py` shells out to Whisper (`whisper`, `fast-whisper`, or any CLI pointed at `WHISPER_CMD`). The resulting transcript is included in the POST under the `transcript` field. Failures are logged but do not cancel delivery.

6. **Response handling** – Responses from the Debian host can be pulled by issuing a follow-up `GET` to the `RESPONSE_URL` provided in the POST reply, or by reading UDP packets if the host emits them (document that pattern in the Debian-side README). The remote script simply logs whatever response it receives; downstream components are responsible for polling the callback URL or listening for UDP updates.

## Logging & Debugging

- The script logs to stdout/stderr with timestamps. Look for `Recording window opened` / `Recording window closed` / `POST succeeded` entries.
- If Whisper is enabled but missing, the script warns and skips transcription gracefully.
- Audio artifacts are dropped silently whenever VAD says `False`, so noisy chunks won't inflate the payload.

## Running

```bash
cd projects/always-on-mic/remote
python capture.py
```

Set the following environment variables as needed before starting:

- `REMOTE_HOST_URL` – (required) `http(s)://` endpoint on the Debian host that accepts multipart uploads.
- `SESSION_ID` – (optional) UUID for correlating multiple captures.
- `ENABLE_TRANSCRIPTION` – set to `1` or `true` to turn on local Whisper transcription.
- `WHISPER_CMD` – path to the Whisper CLI if not on `$PATH`.
- `RESPONSE_URL` – if you expect to poll for a callback after POST completion.

See `capture.py` for exact field names and defaults.
