"""
Telegram delivery helper specification

I/O:
  * Input: transcript payload (text, timestamp, source clip id, confidence).
  * Output: an HTTP POST to Telegram Bot API, logging the delivery result for audits.

Pseudocode:
  1. Read TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from env or config; fail fast if missing.
  2. Format the transcript message (include clip id, time, short excerpt) and POST to https://api.telegram.org/bot{token}/sendMessage.
  3. Append a delivery record (status, HTTP code, response) to /tmp/audio-relay/delivery.log for audits.
  4. Return the response object so the caller can decide whether to retry or mark the transcript.

Tests:
  * Mock requests.post and invoke send_transcript() with a sample payload; assert the right URL, chat_id, and text payload are used.
  * Use a temp log file to ensure each delivery appends a JSON line describing the attempt."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Mapping

import requests

LOG_ENV_VAR = "AUDIO_RELAY_DELIVERY_LOG"
LOG_PATH = Path(os.environ.get(LOG_ENV_VAR, "/tmp/audio-relay/delivery.log"))
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

SNIPPET_LENGTH = 180
TIME_KEYS = ("timestamp", "time", "recorded_at")


def _shorten(text: str, length: int) -> str:
    text = text.strip()
    if len(text) <= length:
        return text
    return text[: length - 1].rstrip() + "…"


def _format_message(payload: Mapping[str, object]) -> str:
    clip_id = payload.get("clip_id", "unknown clip")
    timestamp = "unknown time"
    for key in TIME_KEYS:
        if key in payload:
            timestamp = payload[key]
            break
    text = payload.get("text", "(no transcript text)")
    excerpt = payload.get("excerpt") or _shorten(text, SNIPPET_LENGTH)

    header = "[Audio Relay]"
    lines = [header, f"Clip: {clip_id}", f"When: {timestamp}", f"Excerpt: {excerpt}"]
    return "\n".join(lines)


def _log_delivery(payload: Mapping[str, object], response: requests.Response) -> None:
    entry = {
        "sent_at": datetime.utcnow().isoformat() + "Z",
        "clip_id": payload.get("clip_id"),
        "timestamp": next((payload[key] for key in TIME_KEYS if key in payload), None),
        "confidence": payload.get("confidence"),
        "status": response.status_code,
        "ok": response.ok,
        "response": response.text,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fp:
        json.dump(entry, fp)
        fp.write("\n")


def send_transcript(payload: Mapping[str, object]) -> requests.Response:
    """Send the transcript payload via Telegram and log the attempt."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    message = _format_message(payload)

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=10,
    )

    _log_delivery(payload, response)

    response.raise_for_status()
    return response
