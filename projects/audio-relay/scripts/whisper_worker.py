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
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
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
RETENTION_HOURS = float(os.environ.get("AUDIO_RELAY_RETENTION_HOURS", "24"))
MAX_QUEUE_AGE_SECONDS = float(os.environ.get("AUDIO_RELAY_MAX_QUEUE_AGE_SECONDS", "20"))
MAX_QUEUE_CLIPS = int(os.environ.get("AUDIO_RELAY_MAX_QUEUE_CLIPS", "6"))
MIN_FORWARD_CHARS = int(os.environ.get("AUDIO_RELAY_MIN_FORWARD_CHARS", "25"))
FORWARD_COOLDOWN_SECONDS = float(os.environ.get("AUDIO_RELAY_FORWARD_COOLDOWN_SECONDS", "8"))
DUPLICATE_SUPPRESSION_SECONDS = int(os.environ.get("AUDIO_RELAY_DUPLICATE_SUPPRESSION_SECONDS", "120"))
WAKE_PHRASE = os.environ.get("AUDIO_RELAY_WAKE_PHRASE", "byte").strip().lower()
_WAKE_ALIASES_RAW = os.environ.get("AUDIO_RELAY_WAKE_ALIASES", "")
WAKE_ALIASES = [w.strip().lower() for w in _WAKE_ALIASES_RAW.split(",") if w.strip()]
WAKE_PHRASE_BUBBLE = os.environ.get("AUDIO_RELAY_WAKE_PHRASE_BUBBLE", "1").lower() in {"1", "true", "yes", "on"}
INTENT_KEYWORDS_PATTERN = os.environ.get(
    "AUDIO_RELAY_INTENT_KEYWORDS",
    "what|how|why|when|where|who|tell|ask|hey|oliver|claw|byte",
).strip()
REQUIRE_INTENT_KEYWORDS = os.environ.get("AUDIO_RELAY_REQUIRE_INTENT_KEYWORDS", "0").lower() in {"1", "true", "yes", "on"}
REQUIRE_SENTENCE_PUNCTUATION = os.environ.get("AUDIO_RELAY_REQUIRE_SENTENCE_PUNCTUATION", "1").lower() in {"1", "true", "yes", "on"}
INTENT_KEYWORDS_RE = re.compile(INTENT_KEYWORDS_PATTERN, re.IGNORECASE) if INTENT_KEYWORDS_PATTERN else None
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
_last_forwarded_text = ""
_last_forwarded_at = 0.0


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




def _normalize_transcript(transcript: str) -> str:
    return " ".join(transcript.lower().split())


def _wake_phrase_detected(normalized: str) -> bool:
    if not WAKE_PHRASE:
        return True
    candidates = [WAKE_PHRASE, *WAKE_ALIASES]
    return any(candidate and candidate in normalized for candidate in candidates)


def _should_forward_transcript(transcript: str, now: float) -> tuple[bool, str, str]:
    normalized = _normalize_transcript(transcript)
    raw = transcript.strip()

    if not normalized:
        return False, "transcript was empty", normalized
    if len(normalized) < MIN_FORWARD_CHARS:
        return False, f"transcript too short ({len(normalized)} chars < {MIN_FORWARD_CHARS})", normalized
    if not any(ch.isalnum() for ch in normalized):
        return False, "transcript contains no alphanumeric characters", normalized
    if REQUIRE_SENTENCE_PUNCTUATION and not re.search(r"[?.!]", raw):
        return False, "missing sentence punctuation (? . !)", normalized
    if not _wake_phrase_detected(normalized):
        alias_note = f" (+aliases: {', '.join(WAKE_ALIASES)})" if WAKE_ALIASES else ""
        return False, f"wake phrase '{WAKE_PHRASE}' missing{alias_note}", normalized
    if REQUIRE_INTENT_KEYWORDS and INTENT_KEYWORDS_RE and not INTENT_KEYWORDS_RE.search(raw):
        return False, "no intent keyword match", normalized
    if normalized == _last_forwarded_text and (now - _last_forwarded_at) < DUPLICATE_SUPPRESSION_SECONDS:
        return False, "duplicate of most recently forwarded transcript", normalized
    if (now - _last_forwarded_at) < FORWARD_COOLDOWN_SECONDS:
        return False, f"forward cooldown ({FORWARD_COOLDOWN_SECONDS}s) active", normalized
    return True, "transcript eligible for forwarding", normalized


def _deliver_transcript(metadata: dict, transcript: str, normalized: str, now: float) -> None:
    global _last_forwarded_text, _last_forwarded_at
    clip_id = metadata.get("clip_id", metadata.get("path", "unknown"))
    route_to_agent = os.environ.get("ROUTE_TO_OPENCLAW_AGENT", "0").lower() in {"1", "true", "yes", "on"}
    disable_telegram = os.environ.get("DISABLE_TELEGRAM_OUTPUT", "0").lower() in {"1", "true", "yes", "on"}

    if route_to_agent:
        channel = os.environ.get("OPENCLAW_REPLY_CHANNEL", "telegram")
        target = os.environ.get("OPENCLAW_REPLY_TO", os.environ.get("TELEGRAM_CHAT_ID", ""))
        if not target:
            raise RuntimeError("OPENCLAW_REPLY_TO (or TELEGRAM_CHAT_ID) must be set")

        if WAKE_PHRASE_BUBBLE:
            try:
                send_transcript(
                    {
                        "clip_id": clip_id,
                        "timestamp": metadata.get("recorded_at"),
                        "text": f"Wake phrase detected: {transcript}",
                    }
                )
                logger.info("Sent wake-phrase bubble for %s", clip_id)
            except Exception:
                logger.exception("Failed wake-phrase bubble for %s", clip_id)

        subprocess.run(
            [
                "openclaw",
                "agent",
                "--channel",
                channel,
                "--to",
                target,
                "--message",
                transcript,
                "--deliver",
                "--timeout",
                "120",
            ],
            check=True,
            timeout=130,
        )
        _last_forwarded_text = normalized
        _last_forwarded_at = now
        logger.info("Forwarded transcript to openclaw agent for %s", clip_id)
        return

    if disable_telegram:
        logger.info("Telegram output disabled; gating succeeded for %s", clip_id)
        return

    send_transcript(metadata)
    _last_forwarded_text = normalized
    _last_forwarded_at = now
    logger.info("Delivered transcript for %s", clip_id)


def _parse_chunk_timestamp_from_name(path: Path) -> Optional[datetime]:
    name = path.stem
    # Expected capture format: chunk-YYYYMMDD-HHMMSS
    if not name.startswith("chunk-"):
        return None
    parts = name.split("-")
    if len(parts) < 3:
        return None
    stamp = f"{parts[1]}-{parts[2]}"
    try:
        # ffmpeg strftime uses local time; keep timezone explicit to avoid ambiguity.
        local_dt = datetime.strptime(stamp, "%Y%m%d-%H%M%S")
        return local_dt.astimezone()
    except ValueError:
        return None


def _transcribe_clip(path: Path) -> dict:
    processing_started_at = datetime.now(timezone.utc)
    file_mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    chunk_started_at = _parse_chunk_timestamp_from_name(path)

    segments, info = MODEL.transcribe(str(path))
    transcript = " ".join(seg.text.strip() for seg in segments if seg.text.strip())

    metadata = {
        "clip_id": path.stem,
        "path": str(path),
        "recorded_at": chunk_started_at.isoformat() if chunk_started_at else file_mtime.isoformat(),
        "processing_started_at": processing_started_at.isoformat(),
        "source_file_mtime": file_mtime.isoformat(),
        "duration": getattr(info, "duration", None),
        "language": getattr(info, "language", "unknown"),
        "text": transcript,
        "segments": [
            {"text": seg.text.strip(), "start": seg.start, "end": seg.end}
            for seg in segments
            if seg.text.strip()
        ],
    }

    if chunk_started_at:
        metadata["ingest_latency_seconds"] = max(
            0.0,
            (processing_started_at - chunk_started_at.astimezone(timezone.utc)).total_seconds(),
        )

    return metadata


def process_clip(path: Path) -> None:
    logger.info("Processing clip %s", path)
    try:
        metadata = _transcribe_clip(path)
        _write_transcript(path.stem, metadata)
        clip_id = metadata.get("clip_id", path.stem)
        transcript = (metadata.get("text") or "").strip()
        now = time.time()
        should_forward, reason, normalized = _should_forward_transcript(transcript, now)
        if not should_forward:
            logger.info("Skipping delivery for %s: %s", clip_id, reason)
            return
        try:
            _deliver_transcript(metadata, transcript, normalized, now)
        except Exception:
            logger.exception("Failed to deliver transcript for %s", clip_id)
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
        clips.extend(AUDIO_QUEUE.glob(f"*{ext}"))

    # oldest -> newest
    clips = sorted(clips, key=lambda p: p.stat().st_mtime)

    now = time.time()
    fresh: list[Path] = []
    dropped_stale = 0
    for clip in clips:
        age = now - clip.stat().st_mtime
        if age > MAX_QUEUE_AGE_SECONDS:
            try:
                clip.unlink(missing_ok=True)
            except Exception:
                logger.exception("Failed to drop stale queue clip %s", clip)
            dropped_stale += 1
            continue
        fresh.append(clip)

    if dropped_stale:
        logger.info("Dropped %d stale queue clip(s)", dropped_stale)

    if len(fresh) > MAX_QUEUE_CLIPS:
        overflow = fresh[:-MAX_QUEUE_CLIPS]
        for clip in overflow:
            try:
                clip.unlink(missing_ok=True)
            except Exception:
                logger.exception("Failed to drop overflow queue clip %s", clip)
        logger.info("Dropped %d overflow queue clip(s); keeping newest %d", len(overflow), MAX_QUEUE_CLIPS)
        fresh = fresh[-MAX_QUEUE_CLIPS:]

    return fresh


def cleanup_expired_files() -> None:
    """Delete archived audio/transcripts older than retention window."""
    cutoff = time.time() - (RETENTION_HOURS * 3600)
    cleaned = 0

    for directory, patterns in (
        (TRANSCRIPTS, ("*.json",)),
        (ARCHIVE, ("*.wav", "*.ogg", "*.pcm")),
    ):
        for pattern in patterns:
            for path in directory.glob(pattern):
                try:
                    if path.stat().st_mtime < cutoff:
                        path.unlink(missing_ok=True)
                        cleaned += 1
                except FileNotFoundError:
                    continue
                except Exception:
                    logger.exception("Failed cleanup for %s", path)

    if cleaned:
        logger.info("Cleanup removed %d expired files (retention=%sh)", cleaned, RETENTION_HOURS)


if __name__ == "__main__":
    logger.info("Whisper worker ready. Watching queue for clips.")
    logger.info("Smoke test instructions:\n%s", SMOKE_TEST_INSTRUCTIONS)
    last_cleanup = 0.0
    while True:
        now = time.time()
        if now - last_cleanup >= 60:
            cleanup_expired_files()
            last_cleanup = now

        clips = scan_queue()
        if not clips:
            time.sleep(POLL_INTERVAL)
            continue
        for clip in clips:
            process_clip(clip)
