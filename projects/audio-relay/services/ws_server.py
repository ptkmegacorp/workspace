"""
Audio Relay WebSocket service

I/O:
  * Input: binary audio frames (opus/pcm) streamed from Audio Relay over /ws/audio.
  * Output: sequential PCM files written to /tmp/audio-relay/streams and an optional queue notification for the watcher to pick up.

Pseudocode:
  1. Accept incoming WebSocket connections on /ws/audio.
  2. Loop and receive_bytes(); each chunk becomes a new frame file.
  3. Persist the frame, give it a unique name, and signal the watcher/queue layer (touch a manifest, notify via file, etc.).
  4. Keep the connection open for the always-on mic; log disconnects.

Tests:
  * Use websocat or wscat to open /ws/audio, send a small PCM/opus payload, and assert that a new file appears in /tmp/audio-relay/streams within a few seconds.
  * Confirm the watcher sees the manifest change (e.g., by checking last-modified or running the watcher script once)."""
import asyncio
import datetime
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("audio_relay.ws")

app = FastAPI()
STREAM_DIR = Path("/tmp/audio-relay/streams")
STREAM_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_FILE = STREAM_DIR / "manifest.txt"
MANIFEST_FILE.touch(exist_ok=True)


def detect_extension(chunk: bytes) -> str:
    if len(chunk) >= 12 and chunk[:4] == b"RIFF" and chunk[8:12] == b"WAVE":
        return ".wav"
    return ".pcm"


def build_filename(extension: str, ts: datetime.datetime) -> str:
    timestamp = ts.strftime("%Y%m%dT%H%M%S%fZ")
    return f"chunk-{timestamp}-{uuid.uuid4().hex}{extension}"


async def save_frame(data: bytes) -> tuple[Path, datetime.datetime]:
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    extension = detect_extension(data)
    filename = build_filename(extension, timestamp)
    target = STREAM_DIR / filename

    def _write() -> None:
        with target.open("wb") as fd:
            fd.write(data)

    await asyncio.to_thread(_write)
    logger.info("Saved streaming frame %s (%d bytes)", target.name, len(data))
    return target, timestamp


async def notify_watcher_about_frame(path: Path, size: int, timestamp: datetime.datetime) -> None:
    entry = f"{timestamp.isoformat()} {path.name} {size}\n"

    def _write_manifest() -> None:
        with MANIFEST_FILE.open("a") as manifest:
            manifest.write(entry)

    await asyncio.to_thread(_write_manifest)
    logger.debug("Manifest entry appended: %s", entry.strip())


@app.websocket("/ws/audio")
async def audio_stream(socket: WebSocket) -> None:
    await socket.accept()
    logger.info("Audio WebSocket connection opened")
    try:
        while True:
            chunk = await socket.receive_bytes()
            if not chunk:
                logger.debug("Received empty chunk; ignoring")
                continue
            path, timestamp = await save_frame(chunk)
            await notify_watcher_about_frame(path, len(chunk), timestamp)
    except WebSocketDisconnect:
        logger.info("Audio WebSocket client disconnected")
    except Exception:
        logger.exception("Unexpected error in audio_stream")
        raise
