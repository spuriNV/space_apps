"""My fields: user-drawn polygons analysed like a tapped point, but over the whole polygon.

Nothing has to persist server-side: the field id `my_<base64url(zlib(JSON {name, outline}))>` (see fid.py) carries the name
and outline, so any server decodes it and recomputes. A disk cache (MYFIELDS_DIR, default data/user_fields/, optional) only
saves the recompute. Rename or redraw = a new id; "delete" is the client forgetting the id.

  POST /api/my-fields {name, geometry}        validate, encode the id, analyse (or cache hit) -> location payload
  GET  /api/my-fields/{id}                    decode, serve from cache or recompute
  GET  /api/my-fields?ids=a,b,c               summaries decoded from the ids (no upstream calls)
  GET  /api/locations/{my_id}[/strategies|/daily], POST /api/locations/{my_id}/score, other sub-routes 404 with a reason

Guards (env): MYFIELDS_MAX_CONCURRENT=2 analyses at once (else 429 Retry-After), MYFIELDS_PER_IP_MIN=4 / MYFIELDS_PER_IP_HOUR=30
new analyses per client IP, MYFIELDS_GLOBAL_HOUR=300, MYFIELDS_READS_PER_MIN=120 cheap reads per IP, MYFIELDS_MAX_CACHED=5000
cache files, MYFIELDS_TTL_H=168 (15 min when a tier-1 section errored).
"""
from __future__ import annotations

import asyncio
import collections
import datetime as dt
import gzip
import hashlib
import json
import os
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.routing import Match

from .. import anyloc as AL
from ..anyloc import build as B
from ..anyloc import fetch as F
from . import build as MB
from . import fid as FID
from . import geom as G

ENV = AL.ENV
ROOT = AL.ROOT
MAX_CONCURRENT = ENV("MYFIELDS_MAX_CONCURRENT", 2)
PER_IP_MIN, PER_IP_HOUR, GLOBAL_HOUR = ENV("MYFIELDS_PER_IP_MIN", 4), ENV("MYFIELDS_PER_IP_HOUR", 30), ENV("MYFIELDS_GLOBAL_HOUR", 300)
READS_PER_MIN = ENV("MYFIELDS_READS_PER_MIN", 120)
MAX_CACHED = ENV("MYFIELDS_MAX_CACHED", 5000)
TTL_S, TTL_ERR_S = ENV("MYFIELDS_TTL_H", 168) * 3600, 15 * 60
DIR = Path(os.environ.get("MYFIELDS_DIR", ROOT / "data" / "user_fields"))
TIER1 = ("weather", "soil", "crop_history", "county", "strategies")


# ------------------------------------------------------------------ guards
class Busy(Exception):
    def __init__(self, retry_after, why):
        super().__init__(why)
        self.retry_after, self.why = max(1, retry_after), why


class Guard:
    def __init__(self):
        self.lock = threading.Lock()
        self.active = 0
        self.hits: dict[str, collections.deque] = {}
        self.reads: dict[str, collections.deque] = {}
        self.glob: collections.deque = collections.deque()

    @staticmethod
    def _prune(q, horizon, now):
        while q and q[0] < now - horizon:
            q.popleft()

    def check_read(self, ip):
        now = time.time()
        with self.lock:
            q = self.reads.setdefault(ip, collections.deque())
            self._prune(q, 60, now)
            if len(q) >= READS_PER_MIN:
                raise Busy(int(q[0] + 60 - now) + 1, f"more than {READS_PER_MIN} requests a minute from this address")
            q.append(now)
            if len(self.reads) > 5000:
                self.reads = {k: v for k, v in self.reads.items() if v and v[-1] > now - 60}

    def acquire(self, ip):
        """Reserve one analysis (a create, a recompute after a cache miss, or a re-score), or raise Busy (429)."""
        now = time.time()
        with self.lock:
            q = self.hits.setdefault(ip, collections.deque())
            self._prune(q, 3600, now)
            self._prune(self.glob, 3600, now)
            last = [t for t in q if t > now - 60]
            if len(last) >= PER_IP_MIN:
                raise Busy(int(last[0] + 60 - now) + 1 if last else 60, f"more than {PER_IP_MIN} field analyses a minute from this address")
            if len(q) >= PER_IP_HOUR:
                raise Busy(int(q[0] + 3600 - now) + 1, f"more than {PER_IP_HOUR} field analyses an hour from this address")
            if len(self.glob) >= GLOBAL_HOUR:
                raise Busy(int(self.glob[0] + 3600 - now) + 1, "the site's hourly budget for field analyses is used up")
            if self.active >= MAX_CONCURRENT:
                raise Busy(5, f"{MAX_CONCURRENT} fields are being analysed right now")
            self.active += 1
            q.append(now)
            self.glob.append(now)

    def acquire_slot(self, ip):
        self.check_read(ip)
        with self.lock:
            if self.active >= MAX_CONCURRENT:
                raise Busy(3, f"{MAX_CONCURRENT} fields are being analysed right now")
            self.active += 1

    def release(self):
        with self.lock:
            self.active = max(0, self.active - 1)


GUARD = Guard()
INFLIGHT: set[str] = set()
_INF = threading.Lock()


def busy_response(e: Busy):
    return JSONResponse({"detail": f"busy: {e.why}; try again in {e.retry_after} s", "retry_after_s": e.retry_after, "_source": "user"},
                        status_code=429, headers={"Retry-After": str(e.retry_after)})


# ------------------------------------------------------------------ optional disk cache (a miss just recomputes)
def _path(fid):
    return DIR / (hashlib.sha256(fid.encode()).hexdigest()[:40] + ".json.gz")


def cache_get(fid):
    try:
        with gzip.open(_path(fid), "rt") as f:
            d = json.load(f)
        return d if d.get("id") == fid and time.time() < d.get("expires", 0) else None
    except (OSError, ValueError):
        return None


def cache_put(fid, d):
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        p = _path(fid)
        tmp = p.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        with gzip.open(tmp, "wt", compresslevel=5) as f:
            json.dump(d, f, separators=(",", ":"))
        tmp.replace(p)
        files = sorted(DIR.glob("*.json.gz"), key=lambda x: x.stat().st_mtime)
        for old in files[: max(0, len(files) - MAX_CACHED)]:
            old.unlink(missing_ok=True)
    except OSError:
        pass                      # read-only or full disk: serve without a cache


# ------------------------------------------------------------------ compute
async def get_or_compute(req: Request, fid: str, name: str, poly, ha, note, refresh=False):
    ip = AL.client_ip(req)
    if not refresh:
        hit = await asyncio.to_thread(cache_get, fid)
        if hit:
            GUARD.check_read(ip)
            return hit, "hit"
    with _INF:
        mine = fid not in INFLIGHT
        if mine:
            INFLIGHT.add(fid)
    if not mine:
        for _ in range(200):
            await asyncio.sleep(0.2)
            if fid not in INFLIGHT:
                break
        hit = await asyncio.to_thread(cache_get, fid)
        if hit:
            return hit, "hit_shared"
        raise Busy(5, "this field is still being analysed")
    try:
        GUARD.acquire(ip)
        try:
            loc, _d, items, info = await asyncio.wait_for(MB.analyse(fid, name, poly, ha, AL.STORE, note), 50)
        finally:
            GUARD.release()
        errored = any(info["sections"].get(k, {}).get("status") == "error" for k in TIER1)
        now = time.time()
        rec = {"id": fid, "loc": loc, "items": items, "sections": info["sections"], "timings_ms": info["timings_ms"],
               "computed_at": dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(timespec="seconds"),
               "expires": now + (TTL_ERR_S if errored else TTL_S)}
        await asyncio.to_thread(cache_put, fid, rec)
        return rec, "miss"
    finally:
        with _INF:
            INFLIGHT.discard(fid)


def payload(rec, state):
    out = dict(rec["loc"])
    out["_source"] = "user"
    out["sections"] = rec["sections"]
    out["analysis"] = {"id": rec["id"], "computed_at": rec["computed_at"],
                       "expires_at": dt.datetime.fromtimestamp(rec["expires"], dt.timezone.utc).isoformat(timespec="seconds"),
                       "cache": state, "timings_ms": rec["timings_ms"], "section_statuses": list(B.STATUSES)}
    return out


def send(resp: Response, data: dict):
    resp.headers["X-Data-Source"] = "user"
    resp.headers["Cache-Control"] = "no-store"
    data["_source"] = "user"
    return data


def decode_or_400(fid):
    try:
        return FID.decode(fid)
    except FID.BadId as e:
        raise HTTPException(400, f"bad field id: {e}")


async def _ensure(req, fid, refresh=False):
    name, poly, ha = decode_or_400(fid)
    return await get_or_compute(req, fid, name, poly, ha, None, refresh)


# ------------------------------------------------------------------ routes
class MyRoute(APIRoute):
    """Matches `/api/locations/{pid}...` only for my_* ids; all other ids fall through to anyloc and the preset routes."""

    def matches(self, scope):
        match, child = super().matches(scope)
        if match != Match.NONE and "pid" in self.param_convertors and not str(child.get("path_params", {}).get("pid", "")).startswith("my_"):
            return Match.NONE, {}
        return match, child


router = APIRouter(route_class=MyRoute)


class CreateBody(BaseModel):
    name: str
    geometry: dict


def _summary(fid, name, poly, ha):
    ring = poly["coordinates"][0]
    cx, cy = G.centroid(ring)
    return {"id": fid, "name": name, "acres": round(ha * 2.47105, 1), "area_ha": round(ha, 2), "centroid": {"lon": round(cx, 6), "lat": round(cy, 6)},
            "bbox": [min(p[0] for p in ring), min(p[1] for p in ring), max(p[0] for p in ring), max(p[1] for p in ring)], "geometry": poly}


@router.post("/api/my-fields")
async def create(body: CreateBody, req: Request, resp: Response):
    """Validate (single Polygon, <= 200 corners, 0.5-2,000 ha, no self-crossing), encode the id, analyse. 422 on bad geometry."""
    try:
        fid, poly, ha, note = FID.encode(body.name, body.geometry)
        name = FID.clean_name(body.name)
    except G.GeomError as e:
        raise HTTPException(422, str(e))
    try:
        rec, state = await get_or_compute(req, fid, name, poly, ha, note)
    except Busy as e:
        return busy_response(e)
    except asyncio.TimeoutError:
        raise HTTPException(504, "analysis took longer than 50 s; try again")
    out = payload(rec, state)
    out["field_id"] = fid
    out["id_note"] = note
    return send(resp, out)


@router.get("/api/my-fields")
def list_fields(req: Request, resp: Response, ids: str = Query("", description="comma-separated my_ ids")):
    try:
        GUARD.check_read(AL.client_ip(req))
    except Busy as e:
        return busy_response(e)
    items, bad = [], []
    for fid in [s.strip() for s in ids.split(",") if s.strip()][:100]:
        try:
            name, poly, ha = FID.decode(fid)
        except FID.BadId as e:
            bad.append({"id": fid[:40], "reason": str(e)})
            continue
        s = _summary(fid, name, poly, ha)
        c = cache_get(fid)
        if c:
            L = c["loc"]
            s.update(family=L.get("family"), county_name=L.get("county_name"), computed=True,
                     last_crop=next(iter(reversed(list(L.get("crop_history", {}).values()))), None))
        else:
            s["computed"] = False
        items.append(s)
    return send(resp, {"items": items, "invalid": bad, "note": "decoded from the ids; open one for the full analysis"})


async def _get(req, resp, fid, refresh):
    try:
        rec, state = await _ensure(req, fid, refresh)
    except Busy as e:
        return busy_response(e)
    except asyncio.TimeoutError:
        raise HTTPException(504, "analysis took longer than 50 s; try again")
    return send(resp, payload(rec, state))


@router.get("/api/my-fields/{fid}")
async def get_field(fid: str, req: Request, resp: Response, refresh: bool = False):
    """Decode the id (400 if bad), serve from cache or recompute. Same payload as /api/locations/{id}."""
    return await _get(req, resp, fid, refresh)


@router.get("/api/locations/{pid}")
async def get_location(pid: str, req: Request, resp: Response):
    return await _get(req, resp, pid, False)


@router.get("/api/locations/{pid}/strategies")
async def strategies(pid: str, req: Request, resp: Response):
    try:
        rec, _ = await _ensure(req, pid)
    except Busy as e:
        return busy_response(e)
    if not rec["items"]:
        raise HTTPException(404, f"strategies not available for {pid}: {rec['sections']['strategies'].get('reason')}")
    return send(resp, {"location_id": pid, "items": rec["items"], "template": rec["loc"].get("template"), "note": rec["sections"]["strategies"].get("reason")})


@router.get("/api/locations/{pid}/daily")
async def daily(pid: str, req: Request, resp: Response, from_: str | None = Query(None, alias="from"), to: str | None = None):
    try:
        rec, _ = await _ensure(req, pid)
        c0 = rec["loc"]["centroid"]
        GUARD.check_read(AL.client_ip(req))
        async with F.client() as c:
            df, pmeta = await asyncio.wait_for(AL.STORE.get(c, c0["lon"], c0["lat"]), 30)
    except Busy as e:
        return busy_response(e)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"NASA POWER did not answer for {pid} ({type(e).__name__})")
    d = B.daily_payload(pid, df, c0["lat"], pmeta, dt.date.today().isoformat())
    if from_ or to:
        d["rows"] = [r for r in d["rows"] if (not from_ or r["date"] >= from_) and (not to or r["date"] <= to)]
    return send(resp, d)


@router.post("/api/locations/{pid}/score")
async def score(pid: str, body: AL.ScoreRequest, req: Request, resp: Response):
    for k, v in body.weights.items():
        if k not in AL.DEFAULT_W:
            raise HTTPException(422, f"unknown weight '{k}'; valid: {list(AL.DEFAULT_W)}")
        if not 0 <= v <= 4:
            raise HTTPException(422, f"weight {k} must be in [0, 4]")
    w = {**AL.DEFAULT_W, **body.weights}
    if sum(w.values()) <= 0:
        raise HTTPException(422, "at least one weight must be > 0")
    try:
        rec, _ = await _ensure(req, pid)
        if not rec["items"]:
            raise HTTPException(404, f"strategies not available for {pid}: {rec['sections']['strategies'].get('reason')}")
        loc = rec["loc"]
        GUARD.acquire_slot(AL.client_ip(req))
    except Busy as e:
        return busy_response(e)
    try:
        lat, lon = loc["centroid"]["lat"], loc["centroid"]["lon"]
        async with F.client() as c:
            df, pmeta = await asyncio.wait_for(AL.STORE.get(c, lon, lat), 30)
        from ..anyloc import engine_bridge  # noqa: PLC0415
        fam = loc.get("family", "other")
        entry = {"id": pid, "name": loc["name"], "family": "rice" if fam == "rice" else "forage", "template": loc["template"], "region": "ca",
                 "centroid": loc["centroid"], "slope_pct": 0.0 if fam == "rice" else 0.5}
        soil = loc.get("soil") or {}
        esoil = {k: soil.get(k) for k in ("drainage_class", "hydrologic_group", "mukey", "muname")} if soil.get("mukey") not in (None, "unavailable") else None
        try:
            res = await asyncio.to_thread(engine_bridge.run, pid, entry, df, lat, pmeta.get("elevation_m"), pmeta["url"], esoil,
                                          weights=w, constraints=body.constraints, market_preference=body.market_preference or "no_preference",
                                          allocation=body.allocation, replay_year=body.replay_year, scenario=body.scenario.model_dump())
        except ValueError as e:
            raise HTTPException(422, str(e))
    finally:
        GUARD.release()
    res = B._plain(res)
    for st in res:
        gaps = (st.get("brief") or {}).get("gaps")
        if isinstance(gaps, list):
            st["brief"]["gaps"] = [{"text": g, "source_ids": []} if isinstance(g, str) else g for g in gaps]
    return send(resp, {"location_id": pid, "request": body.model_dump(), "items": res, "ranking": AL._rank(res),
                       "note": "scored by backend/engine for a user-drawn field (rule of thumb, not a model)"})


@router.get("/api/locations/{pid}/{rest:path}")
def other(pid: str, rest: str):
    decode_or_400(pid)
    raise HTTPException(404, f"{rest} is not computed for user-drawn fields (only the location, daily, strategies and score are); "
                             "see `sections` for why")
