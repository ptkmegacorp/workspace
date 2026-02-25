#!/usr/bin/env python3
"""
Whisper worker specification

I/O:
  * Input: PCM/opus clip paths that the watcher enqueues into /tmp/audio-relay/queue.
  * Output: JSON/text transcripts in /tmp/audio-relay/transcripts and delivery events (Telegram push, logs, etc.).

Pseudocode:
  1. Watch /tmp/audio-relay/queue for new clips (by polling or file notification).
  2. For each clip, call faster-whisper (or the preferred model) to transcribe its contents.
  3. Write transcripts/metadata (text, confidence, timestamps) into /tmp/audio-relay/transcripts/clip-id.json.
  4. Invoke the delivery helper (Telegram push module) with the transcript payload.
  5. Move the clip into an archive folder or delete it after processing; catch and log errors.

Tests:
  * Drop a synthetic clip into the queue and assert a transcript JSON file appears with the expected keys.
  * Mock the delivery helper to verify it receives the right text before the worker marks the clip as done.

Quick smoke test:
  1. Start the worker: `python projects/audio-relay/scripts/whisper_worker.py`.
  2. Produce or copy a short clip into /tmp/audio-relay/queue, e.g.
     `ffmpeg -f lavfi -i "sine=frequency=440:duration=2" /tmp/audio-relay/queue/sample.wav`.
  3. Wait for /tmp/audio-relay/transcripts/sample.json to appear and inspect the logs for the Telegram delivery call.
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_ROOT))
from services.telegram_delivery import send_transcript

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

AUDIO_QUEUE = Path("/tmp/audio-relay/queue")
TRANSCRIPTS = Path("/tmp/audio-relay/transcripts")
ARCHIVE = Path("/tmp/audio-relay/archive")
POLL_INTERVAL = 1.0
SUPPORTED_EXT = (".wav", ".ogg", ".pcm")
SMOKE_TEST_INSTRUCTIONS = """\
1. Run `python projects/audio-relay/scripts/whisper_worker.py`.
2. Drop or generate a short clip into /tmp/audio-relay/queue (e.g., use ffmpeg to create `sample.wav`).
3. Confirm /tmp/audio-relay/transcripts/<clip-id>.json exists and the log shows the Telegram delivery.
"""

for directory in (AUDIO_QUEUE, TRANSCRIPTS, ARCHIVE):
    directory.mkdir(parents=True, exist_ok=True)


def _resolved_model_env(env_var: str, default: str) -> str:
    value = os.environ.get(env_var)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def _load_model() -> WhisperModel:
    device = _resolved_model_env("WHISPER_DEVICE", "auto")
    preferred_model = _resolved_model_env("WHISPER_MODEL", "small")
    fallback_model = _resolved_model_env("WHISPER_FALLBACK_MODEL", "tiny")

    candidates = [preferred_model]
    if fallback_model and fallback_model != preferred_model:
        candidates.append(fallback_model)

    last_error: Optional[Exception] = None
    for index, model_size in enumerate(candidates):
        logger.info("Attempting to load WhisperModel '%s' on device '%s'", model_size, device)
        try:
            model = WhisperModel(model_size, device=device)
            logger.info("Loaded WhisperModel '%s' on device '%s'", model_size, device)
            return model
        except Exception as exc:
            logger.exception("Failed to initialize WhisperModel '%s'", model_size)
            last_error = exc
            if index == 0 and len(candidates) > 1:
                logger.info(
                    "Falling back to WhisperModel '%s' after failure loading '%s'",
                    candidates[index + 1],
                    model_size,
                )
    raise RuntimeError(
        "Unable to load WhisperModel candidates (" + ", ".join(candidates) + ")"
    ) from last_error


MODEL = _load_model()


def _write_transcript(clip_id: str, metadata: dict) -> Path:
    target = TRANSCRIPTS / f"{clip_id}.json"
    with target.open("w", encoding="utf-8") as fd:
        json.dump(metadata, fd, ensure_ascii=False, indent=2)
    logger.info("Transcript persisted: %s", target)
    return target


def _move_to_archive(path: Path) -> None:
    dest = ARCHIVE / path.name
    if dest.exists():
        dest = ARCHIVE / f"{path.stem}-{int(time.time())}{path.suffix}"
    shutil.move(str(path), str(dest))
    logger.info("Archived clip to %s", dest)


def _transcribe_clip(path: Path) -> dict:
    segments, info = MODEL.transcribe(str(path))
    transcript = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
    metadata = {
        "clip_id": path.stem,
        "path": str(path),
        "duration": getattr(info, "duration", None),
        "language": getattr(info, "language", "unknown"),
        "text": transcript,
        "segments": [
            {"text": seg.text.strip(), "start": seg.start, "end": seg.end}
            for seg in segments
            if seg.text.strip()
        ],
    }
    return metadata


def process_clip(path: Path) -> None:
    logger.info("Processing clip %s", path)
    try:
        metadata = _transcribe_clip(path)
        _write_transcript(path.stem, metadata)
        try:
            if os.environ.get("USE_OPENCLAW_PROMPT", "0").lower() in {"1", "true", "yes", "on"}:
                transcript = (metadata.get("text") or "").strip() or "(no transcript text)"
                subprocess.run(
                    ["openclaw", "prompt", "--message", transcript],
                    check=True,
                    timeout=30,
                )
                logger.info("Forwarded transcript to openclaw prompt for %s", metadata["clip_id"])
            else:
                send_transcript(metadata)
                logger.info("Delivered transcript for %s", metadata["clip_id"])
        except Exception:
            logger.exception("Failed to deliver transcript for %s", metadata["clip_id"])
    except Exception:
        logger.exception("Failed to process clip %s", path)
    finally:
        try:
            _move_to_archive(path)
        except Exception:
            logger.exception("Failed to archive clip %s", path)


def scan_queue() -> list[Path]:
    clips: list[Path] = []
    for ext in SUPPORTED_EXT:
        clips.extend(sorted(AUDIO_QUEUE.glob(f"*{ext}")))
    return clips


if __name__ == "__main__":
    logger.info("Whisper worker ready. Watching queue for clips.")
    logger.info("Smoke test instructions:\n%s", SMOKE_TEST_INSTRUCTIONS)
    while True:
        clips = scan_queue()
        if not clips:
            time.sleep(POLL_INTERVAL)
            continue
        for clip in clips:
            process_clip(clip)
