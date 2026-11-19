"""Frame-extraction service for Marrying Ghana Dating verification.

Receives a member's intro video, extracts a single frame (~0.5s in,
640px wide JPEG) with FFmpeg, returns the JPEG, and deletes everything
it received. No file is ever kept: temp files are removed in a finally
block on every request, and nothing is logged except request metadata
(status, size, duration).

Auth: X-Api-Key header must match MGDV_API_KEY.
Limits: video/mp4 or video/webm only, max 20 MB (matches the site's
upload limit), FFmpeg timeout 25s, request timeout handled by the server.
"""
import os
import shutil
import subprocess
import tempfile
import uuid

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import Response

API_KEY = os.environ.get("MGDV_API_KEY", "")
MAX_BYTES = 20 * 1024 * 1024
ALLOWED_TYPES = {"video/mp4", "video/webm"}
FRAME_AT_SECONDS = "0.5"

app = FastAPI(title="mgdv-frame-extraction")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/extract")
async def extract(
    video: UploadFile = File(...),
    x_api_key: str = Header(default=""),
):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    if video.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported content type: {video.content_type}",
        )
    data = await video.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="file too large (max 20 MB)")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="empty file")

    tmpdir = tempfile.mkdtemp(prefix="mgdv-frame-")
    try:
        ext = ".mp4" if video.content_type == "video/mp4" else ".webm"
        src = os.path.join(tmpdir, f"input-{uuid.uuid4().hex}{ext}")
        dst = os.path.join(tmpdir, "frame.jpg")
        with open(src, "wb") as f:
            f.write(data)
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-ss", FRAME_AT_SECONDS,
            "-i", src,
            "-frames:v", "1",
            "-vf", "scale=640:-2",
            "-q:v", "3",
            dst,
        ]
        try:
            subprocess.run(cmd, timeout=25, check=True, capture_output=True)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="frame extraction timed out")
        except subprocess.CalledProcessError:
            raise HTTPException(status_code=422, detail="could not extract a frame")
        if not os.path.exists(dst) or os.path.getsize(dst) == 0:
            raise HTTPException(status_code=422, detail="could not extract a frame")
        with open(dst, "rb") as f:
            jpeg = f.read()
        return Response(content=jpeg, media_type="image/jpeg")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
