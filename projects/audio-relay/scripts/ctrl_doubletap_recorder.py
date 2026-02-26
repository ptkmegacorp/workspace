#!/usr/bin/env python3
import os
import signal
import subprocess
import time
from pathlib import Path

import requests

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None

try:
    from evdev import InputDevice, ecodes, list_devices
except Exception:  # pragma: no cover
    InputDevice = None
    ecodes = None
    list_devices = None

DOUBLE_TAP_WINDOW = float(os.environ.get("AUDIO_RELAY_CTRL_DOUBLE_TAP_WINDOW", "0.45"))
MIN_BYTES = int(os.environ.get("AUDIO_RELAY_MIN_CLIP_BYTES", "0"))
QUEUE_DIR = Path(os.environ.get("AUDIO_RELAY_QUEUE_DIR", "/tmp/audio-relay/queue"))
TMP_DIR = Path(os.environ.get("AUDIO_RELAY_TMP_DIR", "/tmp/audio-relay/manual"))
RECORD_SOURCE = os.environ.get("AUDIO_RELAY_RECORD_SOURCE", "").strip()
STATE_FILE = Path(os.environ.get("AUDIO_RELAY_STATE_FILE", "/tmp/audio-relay/manual/state.txt"))
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TRANSCRIPT_BUBBLE = os.environ.get("AUDIO_RELAY_TRANSCRIPT_BUBBLE", "1").lower() in {"1", "true", "yes", "on"}
TRANSCRIBE_MODEL = os.environ.get("AUDIO_RELAY_TRANSCRIBE_MODEL", "tiny")
OPENCLAW_SIGNAL_CHANNEL = os.environ.get("OPENCLAW_SIGNAL_CHANNEL", "").strip()
OPENCLAW_SIGNAL_TO = os.environ.get("OPENCLAW_SIGNAL_TO", "").strip()

QUEUE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

last_ctrl_press = 0.0
recording_proc: subprocess.Popen | None = None
recording_file: Path | None = None
_transcriber = None


def _now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _discover_record_source() -> str:
    if RECORD_SOURCE:
        return RECORD_SOURCE

    pactl_cmd = ["pactl", "list", "short", "sources"]
    if os.geteuid() == 0:
        pactl_cmd = [
            "sudo",
            "-u",
            "bot",
            "env",
            "XDG_RUNTIME_DIR=/run/user/1000",
            "PULSE_SERVER=unix:/run/user/1000/pulse/native",
            *pactl_cmd,
        ]

    try:
        out = subprocess.check_output(pactl_cmd, text=True)
        rows = [line.split("\t") for line in out.splitlines() if line.strip()]
        # Prefer real input devices over monitor sources.
        for row in rows:
            if len(row) >= 2:
                name = row[1]
                if ".monitor" not in name and "input" in name:
                    return name
        for row in rows:
            if len(row) >= 2:
                name = row[1]
                if ".monitor" not in name:
                    return name
    except Exception:
        pass
    return "default"


def _notify_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=8,
        )
    except Exception:
        pass


def _notify_openclaw_signal(text: str) -> None:
    if not OPENCLAW_SIGNAL_CHANNEL:
        return
    try:
        prompt = f"Signal event. Reply with exactly this text and nothing else:\n{text}"
        cmd = [
            "openclaw",
            "agent",
            "--agent",
            "main",
            "--message",
            prompt,
            "--timeout",
            "30",
            "--deliver",
            "--reply-channel",
            OPENCLAW_SIGNAL_CHANNEL,
        ]
        if OPENCLAW_SIGNAL_TO:
            cmd.extend(["--reply-to", OPENCLAW_SIGNAL_TO])
        subprocess.Popen(cmd)
    except Exception:
        pass


def _write_state(text: str) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        STATE_FILE.write_text(f"[{ts}] {text}\n", encoding='utf-8')
    except Exception:
        pass


def _signal(text: str) -> None:
    _write_state(text)
    _notify_telegram(text)
    _notify_openclaw_signal(text)


def _transcribe_file(path: Path) -> str:
    global _transcriber
    if not TRANSCRIPT_BUBBLE:
        return ""
    if WhisperModel is None:
        return ""
    try:
        if _transcriber is None:
            _transcriber = WhisperModel(TRANSCRIBE_MODEL, device="cpu")
        segments, _info = _transcriber.transcribe(str(path))
        return " ".join(s.text.strip() for s in segments if s.text.strip())
    except Exception:
        return ""


def start_recording() -> None:
    global recording_proc, recording_file
    recording_file = TMP_DIR / f"manual-{_now_stamp()}.wav"
    source = _discover_record_source()
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-f",
        "pulse",
        "-i",
        source,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(recording_file),
    ]

    # If hotkey listener runs as root (for /dev/input access), capture audio as user 'bot'.
    if os.geteuid() == 0:
        cmd = [
            "sudo",
            "-u",
            "bot",
            "env",
            "XDG_RUNTIME_DIR=/run/user/1000",
            "PULSE_SERVER=unix:/run/user/1000/pulse/native",
            *ffmpeg_cmd,
        ]
    else:
        cmd = ffmpeg_cmd

    recording_proc = subprocess.Popen(cmd)
    print(f"[hotkey] REC START: {recording_file} (source={source})", flush=True)
    _signal("🔴 Recording ON")


def stop_recording() -> None:
    global recording_proc, recording_file
    if not recording_proc or not recording_file:
        return

    proc = recording_proc
    path = recording_file
    recording_proc = None
    recording_file = None

    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=2)

    if not path.exists() or path.stat().st_size < MIN_BYTES:
        if path.exists():
            path.unlink(missing_ok=True)
        print(f"[hotkey] REC DROP: too small ({path})", flush=True)
        _signal("⚪ Recording OFF (clip too short)")
        return

    target = QUEUE_DIR / f"{path.stem}.wav"
    if target.exists():
        target = QUEUE_DIR / f"{path.stem}-{int(time.time())}.wav"
    path.replace(target)
    print(f"[hotkey] REC STOP -> QUEUED: {target}", flush=True)
    transcript = _transcribe_file(target)
    if transcript:
        preview = transcript if len(transcript) <= 300 else transcript[:297] + "..."
        _signal(f"⚪ Recording OFF (queued)\n📝 {preview}")
    else:
        _signal("⚪ Recording OFF (queued)")


def toggle_recording() -> None:
    if recording_proc is None:
        start_recording()
    else:
        stop_recording()


def handle_ctrl_press() -> None:
    global last_ctrl_press
    now = time.time()
    if now - last_ctrl_press <= DOUBLE_TAP_WINDOW:
        toggle_recording()
        last_ctrl_press = 0.0
    else:
        last_ctrl_press = now


def run_evdev() -> bool:
    if InputDevice is None or list_devices is None or ecodes is None:
        return False
    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities().get(ecodes.EV_KEY, [])
            if ecodes.KEY_LEFTCTRL in caps or ecodes.KEY_RIGHTCTRL in caps:
                devices.append(dev)
        except Exception:
            continue
    if not devices:
        return False

    print(f"[hotkey] Listening with evdev on {len(devices)} keyboard device(s). Double-tap Ctrl to start/stop.", flush=True)
    dev = devices[0]
    while True:
        for event in dev.read_loop():
            if event.type != ecodes.EV_KEY:
                continue
            if event.value != 1:  # key down
                continue
            if event.code in (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL):
                handle_ctrl_press()
    return True


def run_xev() -> None:
    print("[hotkey] Listening with xev fallback. Double-tap Ctrl to start/stop recording.", flush=True)
    proc = subprocess.Popen(
        ["xev", "-event", "keyboard", "-root"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    pending_keypress = False
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if "KeyPress event" in line:
                pending_keypress = True
                continue
            if pending_keypress and "keysym" in line:
                pending_keypress = False
                if "Control_L" in line or "Control_R" in line:
                    handle_ctrl_press()
    finally:
        if recording_proc is not None:
            stop_recording()
        proc.terminate()


def run() -> None:
    try:
        if run_evdev():
            return
    except Exception as exc:
        print(f"[hotkey] evdev unavailable ({exc!r}), falling back to xev", flush=True)
    run_xev()


if __name__ == "__main__":
    run()
