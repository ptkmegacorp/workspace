#!/usr/bin/env python3
import json
import os
import subprocess
import time
from pathlib import Path

STATE_FILE = Path(os.environ.get("AUDIO_RELAY_STATE_FILE", "/tmp/audio-relay/manual/state.txt"))
REPLY_CHANNEL = os.environ.get("OPENCLAW_SIGNAL_CHANNEL", "webchat").strip()
REPLY_TO = os.environ.get("OPENCLAW_SIGNAL_TO", "openclaw-control-ui").strip()
POLL = float(os.environ.get("AUDIO_RELAY_STATE_POLL_SECONDS", "0.4"))


def send_signal(text: str) -> None:
    if not text:
        return
    print(f"[signal] sending: {text}", flush=True)
    if REPLY_CHANNEL and REPLY_TO:
        # Keep existing assistant-echo behavior when possible.
        prompt = f"Signal event. Reply with exactly this text and nothing else:\n{text}"
        cmd = [
            "openclaw",
            "agent",
            "--agent",
            "main",
            "--message",
            prompt,
            "--timeout",
            "20",
            "--deliver",
            "--reply-channel",
            REPLY_CHANNEL,
            "--reply-to",
            REPLY_TO,
        ]
        try:
            subprocess.run(cmd, timeout=30, check=False)
            return
        except Exception:
            pass

    # Fallback: inject directly into main session via gateway (no model turn).
    try:
        params = json.dumps({"sessionKey": "agent:main:main", "message": text})
        subprocess.run([
            "openclaw", "gateway", "call", "chat.inject",
            "--params", params,
            "--json",
        ], timeout=15, check=False)
    except Exception:
        pass


def extract_status(line: str) -> str:
    s = line.strip()
    if not s:
        return ""
    # format: [ts] message
    if "] " in s:
        return s.split("] ", 1)[1].strip()
    return s


def main() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.touch(exist_ok=True)

    last_mtime = 0.0
    last_sent = ""

    while True:
        try:
            st = STATE_FILE.stat()
            if st.st_mtime > last_mtime:
                last_mtime = st.st_mtime
                lines = STATE_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
                if lines:
                    msg = extract_status(lines[-1])
                    if msg and msg != last_sent:
                        send_signal(msg)
                        last_sent = msg
        except Exception:
            pass
        time.sleep(POLL)


if __name__ == "__main__":
    main()
