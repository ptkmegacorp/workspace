# Implementation Details: Remote App + OpenClaw Trigger

## 1. Remote Ubuntu App (Bash/Python)
- **Purpose**: Run on your Ubuntu workstation (over Tailscale) to capture audio, detect pauses, and push events to the Debian host.
- **Structure**:
  - `capture.sh` (Bash) or `capture.py` (Python) loops on the microphone input using `arecord`/`ffmpeg` or PyAudio.
  - A double tap on the Control key (or another hotkey) toggles the capture state: two quick presses start recording, another double press ends the session and pushes the buffered audio onward.
  - Use a VAD library (webrtcvad, sox `silence`, or ffmpeg `silencedetect`) to mark speech vs silence during the active capture window.
  - Buffer short chunks (1–3 seconds) and only emit them once the buffer goes silent for >800 ms.
  - Transcription hook: send the chunk to the host service (HTTP POST of WAV/opus) or call local Whisper if latency allows.

```
# pseudocode
start_capture()
  while True:
    chunk = record_chunk(duration=2)
    if vad.is_speech(chunk):
      append(buffer, chunk)
    elif buffer and vad.silence_duration(buf_tail) > 0.8:
      emit(buffer)
      buffer.clear()
      call_transcription_service(buffer)
      monitor_for_pause()
```

- **Pause detection**: After emitting a chunk, start a timer; if silence continues beyond threshold while `expecting_input == true`, send `pause_event` to Debian host (via Tailscale HTTP) with metadata (transcript, confidence, session_id).
- **Transcription**: Post chunk to host endpoint `/transcribe` or run FastWhisper locally and pass transcript to the pause detector. Keep fallback to re-request transcription if confidence low.
- **Configuration**: Endpoint URL, session ID, silence threshold, and path to local scripts stored in a config file; the app can be packaged as shell script wrappers calling Python modules.

## 2. OpenClaw Trigger Program (Debian Host)
- **Purpose**: Receive pause events from the remote app and run the OpenClaw prompt/skill, then return the response.
- **Components**:
  - Listener (simple Flask/FastAPI) bound to localhost; accessible over Tailscale (via `tailscale up --accept-dns` bridging) to accept `/pause` POSTs with JSON `{session_id, transcript, timestamp, transcript_confidence}`.
  - CLI invoker script, e.g., `scripts/pause-trigger.sh`:
    ```bash
    #!/usr/bin/env bash
    set -euo pipefail
    json=$(cat)
    transcript=$(jq -r .transcript <<< "$json")
    openclaw prompt --message "Remote pause (${session_id}): $transcript" --metadata "$json"
    ```
  - The endpoint runs script, captures reply, and posts response back to session (via Telegram or HTTP callback to remote app for display).
- **Skill tie-in**: `openai-usage-check` demonstrates simple script + skill; here we add `projects/always-on-mic/skills/pause-responder` containing instructions for the CLI script and how to feed transcripts to the `openclaw prompt` command. The skill can pull from `projects/always-on-mic/pipeline.md` for context.
- **Response handling**:
  - Send to Telegram chat via existing channel/`message` tool.
  - Optionally respond over Tailscale via HTTP callback so remote app can render it or speak it.

## 3. Coordination + Safety Controls
- **Communication**: Remote app and host talk over Tailscale HTTP (Flask endpoint) secured either with a whitelist of session IDs or mutual TLS using self-signed certs created locally.
- **Event flow**: Audio chunk → transcription → pause event → host triggers OpenClaw → host sends text back → (optionally) remote TTS.
- **Safety**: Rate-limit conversions (e.g., one trigger per 5s), apply content filters before calling OpenClaw, log transcripts/responses, allow mute override (a `pause.muted` flag) and confirmation toggles.
- **Deployment**: Keep remote app as a Bash wrapper starting `python capture.py`, exposing config for thresholds/endpoints; the host script lives under `scripts/` and is referenced by the skill.

Let me know if you want me to template the actual Flask listener or the remote Bash wrappers next. If you want to iterate on this design, say so and we can break out the first prototype script. 
