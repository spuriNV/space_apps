"""?lang=es for the whole API, in one place: a middleware (mounted in main.py) that translates the user-facing English strings of
a JSON response into Latin American Spanish with DeepSeek, and a disk cache so each sentence is translated once.

Nothing else in the API knows about languages. `lang` other than "es" costs nothing (the middleware returns at once).

Which strings are translated (conservative; everything else is left exactly as served):
  * never under sanitize.SKIP_KEYS or a key ending _id/_url/_key, nor under NEVER_KEYS (place, Nation, publisher, dataset keys);
  * never a string with no letters, a URL, a path, a code (snake_case, '=' ...), or only Capitalised/UPPER words (a name);
  * `name` only on strategy/crop objects (a dict that also has short_name / crop_id / role / kc), never a field, place or program name;
  * `title` only when the object is not a source / news item (those titles are dataset names and headlines);
  * translated: any string with >= 2 English words that includes a lowercase word of 3+ letters (prose), and the short display
    labels in ALLOW_SHORT / four-digit-year keys (crop names such as "Rice") when they start with a capital.
Failure modes: no DEEPSEEK_API_KEY -> English + `X-Lang-Fallback: en`; not finished within DEADLINE s -> those strings stay English
+ `X-Lang-Fallback: partial`, and the translation keeps running in the background to fill the cache for the next call.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .chat import DEEPSEEK_URL, MODEL, ROOT, _key
from .sanitize import SKIP_KEYS

DEADLINE = float(os.environ.get("I18N_DEADLINE_S", "8"))
CHUNK_N, CHUNK_CHARS = 40, 6000
MAX_BODY = 6_000_000
CACHE_FILE = Path(os.environ.get("I18N_CACHE", ROOT / "data" / "cache" / "_i18n" / "es.json"))

NEVER_KEYS = {"nation", "nearest_area", "nearest_nation", "nearest_reserve", "reserve", "band", "county", "county_name", "scope",
              "station", "source", "provider", "dataset", "place_match", "agency", "district", "gsa", "sgma_subbasin", "muname",
              "compname", "probationary", "under_evaluation", "returned_to_dwr", "jurisdiction", "location_jurisdiction",
              "nearest_nation", "lower_river_nation", "sensor", "ndvi_sensor", "cache_path", "detail_url", "weekday", "model",
              "geometry", "coordinates", "accessed", "generated_at", "as_of", "also", "read_from", "sources", "latest_on_cdec_page",
              "url_tried", "also_tried", "worst_category", "worst_category_code", "regime", "station_name"}
ALLOW_SHORT = {"label", "verdict", "line", "why", "short_name", "term", "majority_name", "current_crop", "crop", "name", "reasons"}
ALLOW_ANY_CASE = {"label", "verdict", "line", "why", "reasons"}   # display words that may start lowercase
NAME_SIBLINGS = {"description", "short_name", "crop_id", "role", "kc", "kc_mid", "stage_mode", "water_use", "plant"}
SOURCE_SIBLINGS = {"url", "source_url", "accessed", "verified", "source", "_via", "_publisher_url", "query_id"}

_LETTERS = re.compile(r"[^\W\d_]", re.U)
_WORD = re.compile(r"[^\W\d_]{2,}", re.U)
_CODEY = re.compile(r"[a-z0-9]_[a-z0-9]|=|https?://|www\.|\.(?:parquet|json|py|csv|md|zip|geojson)\b|(?:^|\s)(?:data|backend|fixtures|docs)/|\{|\}|\b(?:max|min)\(")
_YEAR = re.compile(r"^\d{4}$")


def _contract() -> set[str]:
    """Strings that schemas/*.schema.json pin with const / enum (e.g. label "Forecast, not a guarantee"): the front end and the
    checks compare them, so they stay as the contract wrote them."""
    out: set[str] = set()

    def rec(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "const" and isinstance(v, str):
                    out.add(v)
                elif k == "enum" and isinstance(v, list):
                    out.update(i for i in v if isinstance(i, str))
                else:
                    rec(v)
        elif isinstance(x, list):
            for v in x:
                rec(v)
    for f in (ROOT / "schemas").glob("*.schema.json"):
        try:
            rec(json.loads(f.read_text()))
        except (OSError, ValueError):
            pass
    return out


CONTRACT = _contract()


def _prose(s: str) -> bool:
    words = _WORD.findall(s)
    if len(words) < 2 or _CODEY.search(s):
        return False
    return any(w[0].islower() and len(w) >= 3 for w in words)      # all-Capitalised / UPPER text is a name


def _translatable(s: str, key: str | None, parent: dict | None) -> bool:
    if not s or len(s) > 1500 or not _LETTERS.search(s):
        return False
    if s in CONTRACT and (key == "label" or " " not in s):   # machine values / schema-pinned labels stay as written
        return False
    if key is None or key in SKIP_KEYS or key in NEVER_KEYS or key.endswith(("_id", "_url", "_key", "_ids")):
        return False
    if key == "name" and not (parent and NAME_SIBLINGS & parent.keys()):
        return False
    if key == "title" and parent and SOURCE_SIBLINGS & parent.keys():
        return False
    if _prose(s):
        return True
    if (key in ALLOW_SHORT or _YEAR.match(key)) and not _CODEY.search(s):
        return key in ALLOW_ANY_CASE or s[0].isupper()
    return False


def _walk(x: Any, fn, key: str | None = None, parent: dict | None = None) -> Any:
    """Rebuild x with fn(s) applied to every translatable string (fn returns the replacement; collectors return s)."""
    if isinstance(x, dict):
        return {k: _walk(v, fn, k, x) for k, v in x.items()}
    if isinstance(x, list):
        return [_walk(v, fn, key, parent) for v in x]
    if isinstance(x, str) and _translatable(x, key, parent):
        return fn(x)
    return x


# ---------------------------------------------------------------- cache
_lock = threading.Lock()
_cache: dict[str, str] | None = None


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _load() -> dict[str, str]:
    global _cache
    with _lock:
        if _cache is None:
            try:
                _cache = json.loads(CACHE_FILE.read_text())
            except (OSError, ValueError):
                _cache = {}
        return _cache


def _store(pairs: dict[str, str]):
    c = _load()
    with _lock:
        c.update(pairs)
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=CACHE_FILE.parent, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(c, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, CACHE_FILE)
        except OSError:
            pass   # read-only disk: the in-memory cache still works


# ---------------------------------------------------------------- DeepSeek
SYSTEM = ("You translate short texts from an agricultural water and crop-rotation app for growers from English to natural Latin "
          "American Spanish. Use the vocabulary growers use: parcela or campo (field), rotación de cultivos, riego, sequía, "
          "acre-pie for acre-foot, cultivo de cobertura, humedad del suelo. Keep every number, unit, id, URL, code, place name, "
          "Nation or tribe name, program name and dataset or satellite name (NASA SMAP, GRACE, IMERG, Sentinel-2, OpenET, etc.) "
          "unchanged. Do not add or drop information. Keep the same tone: plain and short. The user message is a JSON object "
          '{"strings": [...]}. Reply with a JSON object {"translations": [...]} with exactly the same number of items in the same order.')
_inflight: dict[str, asyncio.Future] = {}
_bg: set[asyncio.Task] = set()


async def _chunk(key: str, texts: list[str]):
    """Translate one chunk; fulfil the in-flight futures (result str, or None when it failed)."""
    out: list[str | None] = [None] * len(texts)
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(DEEPSEEK_URL, headers={"Authorization": f"Bearer {key}"}, json={
                "model": MODEL, "temperature": 0.1, "max_tokens": 8000, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": json.dumps({"strings": texts}, ensure_ascii=False)}]})
        if r.status_code == 200:
            got = json.loads(r.json()["choices"][0]["message"]["content"])
            got = got.get("translations") if isinstance(got, dict) else got
            if isinstance(got, list) and len(got) == len(texts) and all(isinstance(g, str) for g in got):
                out = [g.strip() or None for g in got]
    except Exception:  # noqa: BLE001  any failure leaves these strings in English
        pass
    good = {_h(t): o for t, o in zip(texts, out) if o}
    if good:
        _store(good)
    for t, o in zip(texts, out):
        fut = _inflight.pop(_h(t), None)
        if fut and not fut.done():
            fut.set_result(o)


def _chunks(texts: list[str]):
    cur, n = [], 0
    for t in texts:
        if cur and (len(cur) >= CHUNK_N or n + len(t) > CHUNK_CHARS):
            yield cur
            cur, n = [], 0
        cur.append(t)
        n += len(t)
    if cur:
        yield cur


async def translate_payload(data: Any, lang: str | None) -> tuple[Any, str | None]:
    """(translated copy of a JSON payload, fallback) where fallback is None (all done), "en" (no key, nothing translated) or
    "partial" (some strings still English). lang != "es": the payload comes back untouched, instantly."""
    if lang != "es":
        return data, None
    found: dict[str, str] = {}
    _walk(data, lambda s: found.setdefault(s, s))
    if not found:
        return data, None
    cache = _load()
    need = [s for s in found if _h(s) not in cache]
    if need:
        key = _key()
        if not key:
            return (data, "en") if len(need) == len(found) else (_walk(data, lambda s: cache.get(_h(s), s)), "en")
        loop = asyncio.get_running_loop()
        fresh = [s for s in need if _h(s) not in _inflight]
        for s in fresh:
            _inflight[_h(s)] = loop.create_future()
        for part in _chunks(fresh):
            t = asyncio.create_task(_chunk(key, part))
            _bg.add(t)
            t.add_done_callback(_bg.discard)      # not awaited past DEADLINE: it keeps running and fills the cache
        futs = [_inflight[_h(s)] for s in need if _h(s) in _inflight]
        if futs:
            await asyncio.wait(futs, timeout=DEADLINE)
        cache = _load()
    missing = sum(1 for s in found if _h(s) not in cache)
    return _walk(data, lambda s: cache.get(_h(s), s)), ("partial" if missing else None)


# ---------------------------------------------------------------- middleware
class SpanishMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.query_params.get("lang") != "es" or request.method != "GET" or not request.url.path.startswith("/api/"):
            return await call_next(request)
        resp = await call_next(request)
        ctype = resp.headers.get("content-type", "")
        if resp.status_code != 200 or ("json" not in ctype):
            return resp
        body = b"".join([c async for c in resp.body_iterator])
        headers = {k: v for k, v in resp.headers.items() if k.lower() not in ("content-length", "content-type")}
        if len(body) > MAX_BODY:
            return Response(body, 200, headers, ctype)
        try:
            data = json.loads(body)
        except ValueError:
            return Response(body, 200, headers, ctype)
        data, fb = await translate_payload(data, "es")
        headers["Content-Language"] = "es"
        if fb:
            headers["X-Lang-Fallback"] = fb
        return Response(json.dumps(data, ensure_ascii=False, separators=(",", ":")), 200, headers, ctype)
