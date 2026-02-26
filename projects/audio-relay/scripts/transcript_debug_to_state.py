#!/usr/bin/env python3
import glob
import json
import os
import time
from pathlib import Path

TRANSCRIPTS_GLOB = os.environ.get("AUDIO_RELAY_TRANSCRIPTS_GLOB", "/tmp/audio-relay/transcripts/manual-*.json")
STATE_FILE = Path(os.environ.get("AUDIO_RELAY_STATE_FILE", "/tmp/audio-relay/manual/state.txt"))
POLL = float(os.environ.get("AUDIO_RELAY_DEBUG_POLL", "0.5"))


def append_state(line: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with STATE_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] 📝 {line}\n")


def main() -> None:
    seen = set()
    while True:
        files = sorted(glob.glob(TRANSCRIPTS_GLOB), key=os.path.getmtime)
        for p in files:
            if p in seen:
                continue
            seen.add(p)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                text = (data.get("text") or "").strip()
                segs = data.get("segments") or []
                if segs:
                    avg_lp_vals = [s.get("avg_logprob") for s in segs if s.get("avg_logprob") is not None]
                    ns_vals = [s.get("no_speech_prob") for s in segs if s.get("no_speech_prob") is not None]
                    cr_vals = [s.get("compression_ratio") for s in segs if s.get("compression_ratio") is not None]
                    avg_lp = (sum(avg_lp_vals) / len(avg_lp_vals)) if avg_lp_vals else None
                    avg_ns = (sum(ns_vals) / len(ns_vals)) if ns_vals else None
                    avg_cr = (sum(cr_vals) / len(cr_vals)) if cr_vals else None
                    meta = f"lp={avg_lp:.2f} ns={avg_ns:.2f} cr={avg_cr:.2f}" if avg_lp is not None and avg_ns is not None and avg_cr is not None else "lp/ns/cr=n/a"
                else:
                    meta = "lp/ns/cr=n/a"

                if text:
                    append_state(f"{text} ({meta})")
                else:
                    append_state(f"<empty transcript> ({meta})")
            except Exception as e:
                append_state(f"<parse error: {e}>")
        time.sleep(POLL)


if __name__ == "__main__":
    main()
