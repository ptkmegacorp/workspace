from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import re
import uuid

app = FastAPI()
UPLOAD_DIR = Path("/tmp/audio-relay/inbox")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(name: str) -> str:
    candidate = Path(name).name
    candidate = _FILENAME_SANITIZER.sub("_", candidate or "")
    candidate = candidate.strip("._-")
    if not candidate:
        candidate = f"upload-{uuid.uuid4().hex}"
    return candidate


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    sanitized_name = sanitize_filename(file.filename or "")
    target = UPLOAD_DIR / sanitized_name
    content = await file.read()
    target.write_bytes(content)
    return {
        "status": "saved",
        "filename": sanitized_name,
        "size": len(content),
        "content_type": file.content_type,
        "saved_path": str(target),
    }
