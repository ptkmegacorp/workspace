#!/usr/bin/env python3
"""FastAPI listener for the Debian host of the always-on-mic project."""
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="[host] %(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Always-on-mic Host Listener")

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", Path(__file__).parent / "uploads"))
LAST_TRIGGER: Dict[str, float] = {}
RATE_LIMIT = float(os.environ.get("RATE_LIMIT_S", 5))
ALLOWED_SESSIONS = [s.strip() for s in os.environ.get("ALLOWED_SESSIONS", "*").split(",") if s.strip()]
MUTE = os.environ.get("MUTE", "0") in ("1", "true", "yes")
CALLBACK_URL = os.environ.get("CALLBACK_URL")
TRIGGER_SCRIPT = Path(__file__).parent.parent / "bin" / "pause-trigger.sh"
TRIGGER_TIMEOUT = int(os.environ.get("PAUSE_TRIGGER_TIMEOUT", 30))


def allowed_session(session_id: str) -> bool:
    allowed = ALLOWED_SESSIONS
    return "*" in allowed or session_id in allowed


def rate_limited(session_id: str) -> bool:
    last = LAST_TRIGGER.get(session_id)
    if not last:
        return False
    return time.time() - last < RATE_LIMIT


async def persist_audio(upload: UploadFile, session_id: str) -> Path:
    suffix = Path(upload.filename).suffix or ".wav"
    target = UPLOAD_DIR / f"{session_id}_{int(time.time())}{suffix}"
    data = await upload.read()
    with target.open("wb") as out_file:
        out_file.write(data)
    return target


def trigger_openclaw(payload: dict) -> subprocess.CompletedProcess:
    data = json.dumps(payload).encode("utf-8")
    return subprocess.run(
        [str(TRIGGER_SCRIPT)],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=TRIGGER_TIMEOUT,
    )


@app.on_event("startup")
def prepare_dirs():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logging.info("Upload dir set to %s", UPLOAD_DIR)


@app.post("/pause")
async def pause_endpoint(
    session_id: str = Form(...),
    timestamp: float = Form(...),
    transcript: Optional[str] = Form(None),
    audio: UploadFile = File(...),
):
    if not allowed_session(session_id):
        raise HTTPException(status_code=403, detail="session not allowed")
    if MUTE:
        logging.info("Mute flag set; ignoring payload from %s", session_id)
        return JSONResponse({"status": "muted", "triggered": False, "callback_url": CALLBACK_URL})
    if rate_limited(session_id):
        logging.warning("Rate limit hit for %s", session_id)
        return JSONResponse({"status": "rate_limited", "triggered": False, "callback_url": CALLBACK_URL})

    audio_path = await persist_audio(audio, session_id)
    payload = {
        "session_id": session_id,
        "timestamp": timestamp,
        "audio_path": str(audio_path.resolve()),
    }
    if transcript:
        payload["transcript"] = transcript
    try:
        result = trigger_openclaw(payload)
        triggered = result.returncode == 0
        if triggered:
            LAST_TRIGGER[session_id] = time.time()
        logging.info("Trigger result for %s: %s", session_id, result.stdout.decode().strip())
    except subprocess.TimeoutExpired as exc:
        logging.error("Trigger timed out: %s", exc)
        triggered = False
    except Exception as exc:
        logging.error("Trigger failed: %s", exc)
        triggered = False

    return {
        "status": "ok",
        "triggered": triggered,
        "callback_url": CALLBACK_URL,
        "audio_path": str(audio_path),
    }


@app.get("/status")
def status():
    return {
        "status": "ok",
        "last_trigger": LAST_TRIGGER,
        "mute": MUTE,
        "rate_limit_s": RATE_LIMIT,
    }
