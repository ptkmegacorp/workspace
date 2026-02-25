#!/usr/bin/env python3
"""Watch directories and move new audio clips into the processing queue."""
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Optional

SOURCES = [
    Path("/tmp/audio-relay/inbox"),
    Path("/tmp/audio-relay/streams"),
]
QUEUE_DIR = Path("/tmp/audio-relay/queue")
REJECT_DIR = Path("/tmp/audio-relay/rejected")
for source in SOURCES:
    source.mkdir(parents=True, exist_ok=True)
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
REJECT_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_EXTENSIONS = {".wav", ".ogg", ".pcm"}
MIN_FILE_SIZE = 128
STABLE_SECONDS = 0.5
OWW_ENABLED = os.environ.get("AUDIO_RELAY_ENABLE_WAKEWORD", "0").lower() in {"1", "true", "yes", "on"}
OWW_THRESHOLD = float(os.environ.get("AUDIO_RELAY_WAKEWORD_THRESHOLD", "0.5"))
OWW_TARGETS = [x.strip().lower() for x in os.environ.get("AUDIO_RELAY_WAKEWORD_TARGETS", "byte").split(",") if x.strip()]
_pending_files: Dict[Path, Dict[str, float]] = {}


class WakeWordGate:
    def __init__(self) -> None:
        self.enabled = OWW_ENABLED
        self.ready = False
        self.model = None
        if not self.enabled:
            print("Wake-word gate disabled (AUDIO_RELAY_ENABLE_WAKEWORD=0).", flush=True)
            return
        try:
            from openwakeword.model import Model  # type: ignore

            self.model = Model()
            self.ready = True
            print(
                f"Wake-word gate enabled (threshold={OWW_THRESHOLD}, targets={OWW_TARGETS or ['*']}).",
                flush=True,
            )
        except Exception as exc:
            self.enabled = False
            print(f"Wake-word gate unavailable ({exc!r}); continuing without it.", flush=True)

    def accepts(self, path: Path) -> tuple[bool, str]:
        if not self.enabled:
            return True, "wake gate disabled"
        if not self.ready or self.model is None:
            return True, "wake gate not ready"
        if path.suffix.lower() != ".wav":
            return True, "non-wav input bypassed"

        try:
            scores = self.model.predict_clip(str(path))
        except Exception as exc:
            return False, f"wake-word inference error: {exc!r}"

        aggregated = self._normalize_scores(scores)
        best_label = None
        best_score = 0.0
        if isinstance(aggregated, dict):
            for label, value in aggregated.items():
                score = self._extract_score(value)
                if best_label is None or score > best_score:
                    best_score = score
                    best_label = str(label)

        if best_label is None:
            return False, "wake-word model returned no scores"

        label_l = best_label.lower()
        targets_match = not OWW_TARGETS or any(t in label_l for t in OWW_TARGETS)
        if targets_match and best_score >= OWW_THRESHOLD:
            return True, f"wake hit {best_label}={best_score:.3f}"
        return False, f"wake miss best={best_label}:{best_score:.3f}"

    @staticmethod
    def _normalize_scores(scores):
        if isinstance(scores, dict):
            return scores
        if isinstance(scores, list):
            merged: dict[str, float] = {}
            for row in scores:
                if not isinstance(row, dict):
                    continue
                for k, v in row.items():
                    if isinstance(v, (int, float)):
                        merged[k] = max(merged.get(k, 0.0), float(v))
            return merged
        return {}

    @staticmethod
    def _extract_score(value) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, list) and value:
            nums = [float(v) for v in value if isinstance(v, (int, float))]
            return max(nums) if nums else 0.0
        if isinstance(value, dict):
            nums = [float(v) for v in value.values() if isinstance(v, (int, float))]
            return max(nums) if nums else 0.0
        return 0.0


def enqueue(path: Path, size: int) -> None:
    """Move the incoming file into the queue directory."""
    target = QUEUE_DIR / path.name
    if target.exists():
        target = QUEUE_DIR / f"{path.stem}-{int(time.time())}{path.suffix}"
    shutil.move(str(path), str(target))
    print(f"Queued {target} ({size} bytes)", flush=True)


def reject(path: Path, reason: str) -> None:
    target = REJECT_DIR / path.name
    if target.exists():
        target = REJECT_DIR / f"{path.stem}-{int(time.time())}{path.suffix}"
    shutil.move(str(path), str(target))
    print(f"Rejected {target}: {reason}", flush=True)


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
    gate = WakeWordGate()
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
                accepted, reason = gate.accepts(path)
                if accepted:
                    enqueue(path, stats.st_size)
                    moved = True
                else:
                    reject(path, reason)
                _pending_files.pop(path, None)
        clean_pending()
        if not moved:
            time.sleep(1)
