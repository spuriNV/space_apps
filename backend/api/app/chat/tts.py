"""Spoken answers: `POST /api/tts` turns one sentence of a chat answer into speech with Kokoro (open-source, Apache-2.0,
runs on this server's CPU through onnxruntime; nothing goes to another company). The browser asks for one sentence at a
time so speech starts quickly; without the model it falls back to the device's own voice.

Voice: TTS_VOICE (default af_heart, a warm, gentle US English female voice), TTS_SPEED (default 0.95).
Model files (git-ignored, ~120 MB): backend/api/models/kokoro-v1.0.int8.onnx and voices-v1.0.bin, from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0. The Dockerfile downloads them; locally run
`python -m app.chat.tts --download` from backend/api. Missing files: /api/chat/status says tts false.
"""
from __future__ import annotations

import io
import os
import threading
import time
from collections import OrderedDict, deque
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

router = APIRouter()
MODELS = Path(os.environ.get("TTS_MODELS", Path(__file__).resolve().parents[2] / "models"))
MODEL, VOICES = MODELS / "kokoro-v1.0.int8.onnx", MODELS / "voices-v1.0.bin"
RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
VOICE = os.environ.get("TTS_VOICE", "af_heart")
SPEED = float(os.environ.get("TTS_SPEED", "0.95"))
MAX_CHARS = 400          # one sentence or two; the browser splits answers
PER_MIN = 40             # sentences per IP per minute (an answer is 2-5 sentences)

_kokoro = None
_lock = threading.Lock()          # one synthesis at a time: bounded CPU and memory on a small server
_cache: OrderedDict[str, bytes] = OrderedDict()
_hits: dict[str, deque] = {}


def available() -> bool:
    return MODEL.is_file() and VOICES.is_file()


def _engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro  # noqa: PLC0415  (heavy import only when speech is first asked for)
        _kokoro = Kokoro(str(MODEL), str(VOICES))
    return _kokoro


def synth(text: str) -> bytes:
    """WAV bytes (24 kHz mono 16-bit) for `text`. Cached: replaying an answer costs nothing."""
    key = f"{VOICE}|{SPEED}|{text}"
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    import soundfile as sf  # noqa: PLC0415
    with _lock:
        audio, sr = _engine().create(text, voice=VOICE, speed=SPEED, lang="en-gb" if VOICE.startswith("b") else "en-us")
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
    data = buf.getvalue()
    _cache[key] = data
    while len(_cache) > 200:
        _cache.popitem(last=False)
    return data


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)


def _limit(req: Request):
    fwd = req.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (req.client.host if req.client else "?")
    now = time.time()
    q = _hits.setdefault(ip, deque())
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= PER_MIN:
        raise HTTPException(429, "Too many spoken answers at once. Please wait a moment.")
    q.append(now)


@router.post("/api/tts")
def tts(body: TTSRequest, req: Request):  # sync: FastAPI runs it in a worker thread, so synthesis never blocks the loop
    if not available():
        raise HTTPException(503, "Spoken answers are not set up on this server.")
    _limit(req)
    try:
        wav = synth(body.text.strip())
    except Exception:  # noqa: BLE001
        raise HTTPException(500, "Could not make speech for that answer.")
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "private, max-age=3600"})


if __name__ == "__main__":
    import sys
    import urllib.request
    if "--download" in sys.argv:
        MODELS.mkdir(parents=True, exist_ok=True)
        for f in (MODEL, VOICES):
            if not f.is_file():
                print("downloading", f.name)
                urllib.request.urlretrieve(RELEASE + f.name, f)
        print("ok:", available())
