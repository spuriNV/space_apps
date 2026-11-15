"""Voice input for browsers without a usable Web Speech API (Firefox, Brave): `POST /api/ask/transcribe` (multipart `audio`)
transcribes a short clip with local faster-whisper (STT_MODEL, default tiny.en, base.en via STT_MODEL if the server is fast enough, int8, CPU). Nothing leaves this server.

Optional: faster-whisper lives in the `stt` extra (`uv sync --extra stt`). Without it the route returns 501 and the web app
tells people to type. Limits: 2 MB, 30 s, 6 a minute per IP, 2 at a time. Audio is decoded in memory (no temp files); audio and
transcripts are never logged. Model files cache under ~/.cache (HF_HOME), outside release directories.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile

router = APIRouter()
MAX_BYTES, MAX_SECONDS, PER_MIN, CONCURRENT = 2_000_000, 30.0, 6, 2
MODEL_NAME = os.environ.get("STT_MODEL", "tiny.en")
os.environ.setdefault("HF_HOME", str(Path.home() / ".cache" / "huggingface"))

_model = None
_mlock = threading.Lock()
_slots = threading.BoundedSemaphore(CONCURRENT)
_hits: dict[str, deque] = {}


def available() -> bool:
    try:
        import importlib.util  # noqa: PLC0415
        return importlib.util.find_spec("faster_whisper") is not None
    except Exception:
        return False


def _engine():
    global _model
    with _mlock:
        if _model is None:
            from faster_whisper import WhisperModel  # noqa: PLC0415
            _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8", cpu_threads=4)
    return _model


def _ip(req: Request) -> str:
    return (req.headers.get("x-forwarded-for") or (req.client.host if req.client else "?")).split(",")[0].strip()


def _limited(ip: str) -> bool:
    now = time.time()
    q = _hits.setdefault(ip, deque())
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= PER_MIN:
        return True
    q.append(now)
    if len(_hits) > 5000:
        for k in [k for k, v in _hits.items() if not v or now - v[-1] > 60]:
            _hits.pop(k, None)
    return False


def _decode(data: bytes):
    """Any container/codec -> 16 kHz mono float32 samples, through an ffmpeg pipe (no temp files)."""
    import numpy as np  # noqa: PLC0415
    r = subprocess.run(["ffmpeg", "-v", "error", "-t", "31", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
                       input=data, capture_output=True, timeout=30)
    if r.returncode != 0 or not r.stdout:
        raise ValueError("undecodable")
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


@router.post("/api/ask/transcribe")
async def transcribe(request: Request, audio: UploadFile):
    if not available():
        raise HTTPException(501, "Speech-to-text (faster-whisper) is not installed on this server")
    if _limited(_ip(request)):
        raise HTTPException(429, "Too many voice requests. Wait a minute.")
    data = await audio.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Recording too large")
    if not data:
        raise HTTPException(400, "Empty recording")
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Busy. Try again in a moment.")
    try:
        return _run(data)
    finally:
        _slots.release()


def _run(data: bytes) -> dict:
    try:
        pcm = _decode(data)
    except Exception:
        raise HTTPException(415, "Could not read that audio")
    dur = len(pcm) / 16000.0
    if dur > MAX_SECONDS + 1:
        raise HTTPException(413, "Recording too long")
    segs, info = _engine().transcribe(pcm, language="en", beam_size=1, best_of=1, temperature=0.0, vad_filter=True,
                                      without_timestamps=True, condition_on_previous_text=False)
    text = " ".join(s.text.strip() for s in segs).strip()
    return {"text": text, "language": info.language, "duration_s": round(dur, 2)}


def preload() -> None:
    """Load the model in a background thread at startup so the first request never waits for it."""
    if available():
        threading.Thread(target=lambda: _engine(), name="stt-preload", daemon=True).start()
