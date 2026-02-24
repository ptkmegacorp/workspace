#!/usr/bin/env python3
"""Remote control for the always-on-mic pipeline."""
import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path

import requests
import sounddevice as sd
import webrtcvad
import keyboard

logging.basicConfig(level=logging.INFO, format="[remote] %(asctime)s %(levelname)s %(message)s")

SAMPLE_RATE = int(os.environ.get("SAMPLE_RATE", 16000))
CHANNELS = 1
FRAME_DURATION_MS = 30  # 10/20/30 ms frames work with WebRTC VAD
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
REMOTE_HOST_URL = os.environ.get("REMOTE_HOST_URL")
SESSION_ID = os.environ.get("SESSION_ID") or str(uuid.uuid4())
ENABLE_TRANSCRIPTION = os.environ.get("ENABLE_TRANSCRIPTION", "0").lower() in ("1", "true", "yes")
WHISPER_CMD = os.environ.get("WHISPER_CMD", "whisper")
RESPONSE_URL = os.environ.get("RESPONSE_URL")
RETRY_LIMIT = int(os.environ.get("RETRY_LIMIT", 3))
CTRL_DOUBLE_PRESS_INTERVAL = float(os.environ.get("CTRL_DOUBLE_PRESS_INTERVAL", 0.4))

if not REMOTE_HOST_URL:
    logging.error("REMOTE_HOST_URL is required to deliver audio payloads.")
    sys.exit(1)

vad = webrtcvad.Vad(3)
frame_queue: "queue.Queue[bytes]" = queue.Queue()
capture_active = threading.Event()
frames_buffer: list[bytes] = []
lock = threading.Lock()


@dataclass
class PayloadMetadata:
    session_id: str
    timestamp: float


def write_wav(frames: list[bytes]) -> Path:
    if not frames:
        raise ValueError("No speech frames to write")
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    tmp = Path(path)
    with wave.open(tmp, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return tmp


def run_whisper(wav_path: Path) -> str | None:
    try:
        result = subprocess.run(
            [WHISPER_CMD, str(wav_path), "--model", "tiny.en", "--language", "en", "--output_format", "json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logging.warning("Whisper transcription failed: %s", exc)
        return None
    try:
        data = json.loads(result.stdout)
        return data.get("text", "").strip()
    except json.JSONDecodeError:
        logging.warning("Whisper returned invalid JSON")
        return None


def post_payload(wav_path: Path, metadata: PayloadMetadata, transcript: str | None, frame_count: int):
    payload = {
        "session_id": metadata.session_id,
        "timestamp": metadata.timestamp,
        "duration": frame_count * FRAME_DURATION_MS / 1000,
    }
    if transcript:
        payload["transcript"] = transcript
    files = {"audio": (wav_path.name, wav_path.open("rb"), "audio/wav")}
    attempts = 0
    while attempts < RETRY_LIMIT:
        attempts += 1
        try:
            resp = requests.post(REMOTE_HOST_URL, data=payload, files=files, timeout=30)
            resp.raise_for_status()
            logging.info("POST successful (%s) → %s", resp.status_code, resp.text.strip())
            if RESPONSE_URL:
                follow_response(RESPONSE_URL)
            return
        except requests.RequestException as exc:
            logging.warning("POST attempt %d failed: %s", attempts, exc)
            time.sleep(2 ** attempts)
    logging.error("Exhausted retries sending to %s", REMOTE_HOST_URL)


def follow_response(url: str):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        logging.info("Response callback: %s", resp.text.strip())
    except requests.RequestException as exc:
        logging.warning("Response callback failed: %s", exc)


def finalize_capture():
    global frames_buffer
    with lock:
        if not frames_buffer:
            logging.info("No speech detected during window; skipping upload.")
            return
        frames = list(frames_buffer)
        frames_buffer = []
    metadata = PayloadMetadata(session_id=SESSION_ID, timestamp=time.time())
    try:
        wav_path = write_wav(frames)
    except ValueError as exc:
        logging.warning("Capture dropped: %s", exc)
        return
    transcript = None
    if ENABLE_TRANSCRIPTION:
        transcript = run_whisper(wav_path)
    post_payload(wav_path, metadata, transcript, len(frames))
    wav_path.unlink(missing_ok=True)


def audio_callback(indata: bytes, frames: int, time_info, status):
    del time_info, status
    if not capture_active.is_set():
        return
    data = bytes(indata)
    if vad.is_speech(data, SAMPLE_RATE):
        with lock:
            frames_buffer.append(data)


def capture_loop():
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SIZE,
        dtype="int16",
        channels=CHANNELS,
        callback=audio_callback,
    ):
        logging.info("Audio capture ready @ %d Hz", SAMPLE_RATE)
        while True:
            time.sleep(0.1)


def toggle_capture() -> None:
    if capture_active.is_set():
        capture_active.clear()
        logging.info("Recording window closed")
        finalize_capture()
    else:
        capture_active.set()
        logging.info("Recording window opened")


def keyboard_watcher():
    last_press = 0.0
    count = 0

    def on_ctrl(event):
        nonlocal last_press, count
        now = time.time()
        if now - last_press < CTRL_DOUBLE_PRESS_INTERVAL:
            count += 1
        else:
            count = 1
        last_press = now
        if count >= 2:
            count = 0
            toggle_capture()

    keyboard.on_press_key("ctrl", on_ctrl)
    keyboard.wait()


def main():
    parser = argparse.ArgumentParser(description="Always-on-mic remote capture daemon.")
    parser.add_argument("--session", default=SESSION_ID, help="Session ID for correlating posts.")
    args = parser.parse_args()
    logging.info("Starting remote capture (session %s)", args.session)
    global SESSION_ID
    SESSION_ID = args.session
    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()
    keyboard_watcher()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Shutting down remote capture")
