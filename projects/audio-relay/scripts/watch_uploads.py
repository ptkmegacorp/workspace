#!/usr/bin/env python3
"""Watch directories and move new audio clips into the processing queue."""
import shutil
import time
from pathlib import Path
from typing import Dict

SOURCES = [
    Path("/tmp/audio-relay/inbox"),
    Path("/tmp/audio-relay/streams"),
]
QUEUE_DIR = Path("/tmp/audio-relay/queue")
for source in SOURCES:
    source.mkdir(parents=True, exist_ok=True)
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_EXTENSIONS = {".wav", ".ogg", ".pcm"}
MIN_FILE_SIZE = 128
STABLE_SECONDS = 0.5
_pending_files: Dict[Path, Dict[str, float]] = {}


def enqueue(path: Path, size: int) -> None:
    """Move the incoming file into the queue directory."""
    target = QUEUE_DIR / path.name
    if target.exists():
        target = QUEUE_DIR / f"{path.stem}-{int(time.time())}{path.suffix}"
    shutil.move(str(path), str(target))
    print(f"Queued {target} ({size} bytes)", flush=True)


def should_enqueue(path: Path, stats, now: float) -> bool:
    """Decide whether the file is stable enough to move."""
    if stats.st_size < MIN_FILE_SIZE:
        print(f"Skipped tiny file {path} ({stats.st_size} bytes)", flush=True)
        _pending_files.pop(path, None)
        return False
    record = _pending_files.get(path)
    if record is None or record["mtime"] != stats.st_mtime:
        _pending_files[path] = {"mtime": stats.st_mtime, "first_seen": now}
        return False
    if now - record["first_seen"] < STABLE_SECONDS:
        return False
    return True


def clean_pending() -> None:
    """Drop tracking data for files that no longer exist."""
    for stale in list(_pending_files):
        if not stale.exists():
            _pending_files.pop(stale, None)


if __name__ == "__main__":
    print("Watcher ready: monitoring", ", ".join(str(src) for src in SOURCES), flush=True)
    while True:
        moved = False
        now = time.time()
        for source in SOURCES:
            for path in sorted(source.iterdir()):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in AUDIO_EXTENSIONS:
                    continue
                stats = path.stat()
                if not should_enqueue(path, stats, now):
                    continue
                enqueue(path, stats.st_size)
                moved = True
                _pending_files.pop(path, None)
        clean_pending()
        if not moved:
            time.sleep(1)
