"""Analyse any location: `GET /api/analyze?lat=&lon=` and the point-id sub-routes.

Mounted from app/main.py with one `app.include_router(anyloc_router)` placed before the preset routes, so the routes
below see `/api/locations/pt_*` first (PointRoute only matches ids starting with `pt_`; every other id falls through to
the preset routes untouched).

Routes (point ids look like `pt_n391414_w1220833`, 4 decimals):
  GET  /api/analyze?lat=&lon=[&refresh=1]   location-shaped payload + `sections` + `analysis` (also POST {lat, lon})
  GET  /api/analyze/{pid}/status            cached? sections, timings, expiry (never computes)
  GET  /api/locations/{pid}                 same payload as /api/analyze (computes on a miss)
  GET  /api/locations/{pid}/daily?from&to   POWER-only daily rows (same keys as preset /daily)
  GET  /api/locations/{pid}/strategies      engine strategies with the family's rotation set
  POST /api/locations/{pid}/score           re-score with weights/constraints/scenario (same body as preset /score)
  GET  /api/locations/{pid}/<anything else> 404 "not computed for tapped points" (see `sections`)

Guards (env, defaults for Render's 512 MB free instance): ANYLOC_MAX_CONCURRENT=2 cold analyses at once (else 429
Retry-After), ANYLOC_PER_IP_MIN=6 / ANYLOC_PER_IP_HOUR=40 cold analyses per client IP, ANYLOC_GLOBAL_HOUR=400 cold
analyses per hour for the whole instance, ANYLOC_READS_PER_MIN=120 cached reads per IP. Cache: ANYLOC_CACHE_DIR
(default data/cache/_points, git-ignored, ephemeral on Render), TTL ANYLOC_TTL_H=168 h (15 min when a tier-1 section
errored), POWER per 0.5 x 0.625 deg cell 24 h.
"""
from __future__ import annotations

import asyncio
import collections
import functools
import datetime as dt
import gzip
import json
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from starlette.routing import Match

ROOT = Path(os.environ.get("FIELDSHIFT_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "backend" / "fields"))

from . import build as B  # noqa: E402
from . import fetch as F  # noqa: E402

ENV = lambda k, d: type(d)(os.environ.get(k, d))  # noqa: E731
MAX_CONCURRENT = ENV("ANYLOC_MAX_CONCURRENT", 2)
PER_IP_MIN, PER_IP_HOUR = ENV("ANYLOC_PER_IP_MIN", 6), ENV("ANYLOC_PER_IP_HOUR", 40)
GLOBAL_HOUR = ENV("ANYLOC_GLOBAL_HOUR", 400)
READS_PER_MIN = ENV("ANYLOC_READS_PER_MIN", 120)
TTL_S = ENV("ANYLOC_TTL_H", 168) * 3600
TTL_ERR_S = 15 * 60
POWER_TTL_S = 24 * 3600
MAX_POINTS = ENV("ANYLOC_MAX_POINTS", 1500)
CACHE = Path(os.environ.get("ANYLOC_CACHE_DIR", ROOT / "data" / "cache" / "_points"))
TIER1 = ("weather", "soil", "crop_history", "boundary", "county", "water", "strategies")
CATALOG = Path(os.environ.get("ANYLOC_CATALOG_DIR", ROOT / "backend" / "api" / "out" / "catalog"))


# ------------------------------------------------------------------ guards (thread-safe, event-loop agnostic)
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

    def acquire_cold(self, ip):
        """Reserve one cold analysis for ip, or raise Busy (429)."""
        now = time.time()
        with self.lock:
            q = self.hits.setdefault(ip, collections.deque())
            self._prune(q, 3600, now)
            self._prune(self.glob, 3600, now)
            last_min = [t for t in q if t > now - 60]
            if len(last_min) >= PER_IP_MIN:
                raise Busy(int(last_min[0] + 60 - now) + 1 if last_min else 60, f"more than {PER_IP_MIN} new spots a minute from this address")
            if len(q) >= PER_IP_HOUR:
                raise Busy(int(q[0] + 3600 - now) + 1 if q else 3600, f"more than {PER_IP_HOUR} new spots an hour from this address")
            if len(self.glob) >= GLOBAL_HOUR:
                raise Busy(int(self.glob[0] + 3600 - now) + 1 if self.glob else 3600, "the site's hourly budget for new spots is used up")
            if self.active >= MAX_CONCURRENT:
                raise Busy(5, f"{MAX_CONCURRENT} spots are being analysed right now")
            self.active += 1
            q.append(now)
            self.glob.append(now)
            if len(self.hits) > 5000:
                self.hits = {k: v for k, v in self.hits.items() if v and v[-1] > now - 3600}

    def acquire_slot(self, ip):
        """A concurrency slot only (re-scores: cheap, but they run the engine), plus the per-IP read limit."""
        self.check_read(ip)
        with self.lock:
            if self.active >= MAX_CONCURRENT:
                raise Busy(3, f"{MAX_CONCURRENT} spots are being analysed right now")
            self.active += 1

    def release_cold(self):
        with self.lock:
            self.active = max(0, self.active - 1)


class Busy(Exception):
    def __init__(self, retry_after: int, why: str):
        super().__init__(why)
        self.retry_after, self.why = max(1, retry_after), why


GUARD = Guard()
INFLIGHT: set[str] = set()
_INF_LOCK = threading.Lock()


def client_ip(req: Request) -> str:
    for h in ("cf-connecting-ip", "true-client-ip"):
        if req.headers.get(h):
            return req.headers[h].strip()
    xff = req.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


def busy_response(e: Busy) -> JSONResponse:
    return JSONResponse({"detail": f"busy: {e.why}; try again in {e.retry_after} s", "retry_after_s": e.retry_after,
                         "_source": "live"}, status_code=429, headers={"Retry-After": str(e.retry_after)})


# ------------------------------------------------------------------ disk + memory caches
def _rj(p: Path):
    try:
        with gzip.open(p, "rt") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _wj(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".{os.getpid()}.{threading.get_ident()}.tmp")
    with gzip.open(tmp, "wt", compresslevel=5) as f:
        json.dump(obj, f, separators=(",", ":"))
    tmp.replace(p)


class Store:
    """POWER per cell (memory LRU of 3 + parquet on disk), CDL catalog/legend and the State Water Board list."""

    def __init__(self):
        self.mem: collections.OrderedDict = collections.OrderedDict()
        self.lock = threading.Lock()
        self.small: dict[str, tuple[float, Any]] = {}

    async def get(self, c, lon, lat):
        row, col, clon, clat, _ = F.power_cell(lon, lat)
        key = f"{row}_{col}"
        for _ in range(150):              # another request is fetching this cell: wait for it (max ~30 s)
            with self.lock:
                if key in self.mem and time.time() - self.mem[key][2] < POWER_TTL_S:
                    self.mem.move_to_end(key)
                    df, meta, _t = self.mem[key]
                    return df, {**meta, "cache": "memory"}
                busy = key in INFLIGHT_CELLS
                if not busy:
                    INFLIGHT_CELLS.add(key)
                    break
            await asyncio.sleep(0.2)
        try:
            import pandas as pd  # noqa: PLC0415
            pq, mp = CACHE / "cells" / f"power_{key}.parquet", CACHE / "cells" / f"power_{key}.meta.json.gz"
            meta = _rj(mp) if pq.exists() else None
            if meta and time.time() - meta.get("_t", 0) < POWER_TTL_S:
                df = pd.read_parquet(pq)
                how = "disk"
            else:
                end = (dt.date.today()).strftime("%Y%m%d")
                df, meta = await F.power_daily(c, clon, clat, end)
                meta["_t"] = time.time()
                meta["cell"] = {"row": row, "col": col, "centre": [clon, clat]}
                pq.parent.mkdir(parents=True, exist_ok=True)
                df.to_parquet(pq)
                _wj(mp, meta)
                how = "fetched"
            with self.lock:
                self.mem[key] = (df, meta, meta["_t"])
                while len(self.mem) > 3:
                    self.mem.popitem(last=False)
            return df, {**meta, "cache": how}
        finally:
            with self.lock:
                INFLIGHT_CELLS.discard(key)

    async def _small(self, name, ttl, make):
        hit = self.small.get(name)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        p = CACHE / "_global" / f"{name}.json.gz"
        d = _rj(p)
        if d and time.time() - d["_t"] < ttl:
            self.small[name] = (d["_t"], d["v"])
            return d["v"]
        v = await make()
        _wj(p, {"_t": time.time(), "v": v})
        self.small[name] = (time.time(), v)
        return v

    async def cdl_meta(self, c):
        async def make():
            cat, leg = await asyncio.gather(F.cdl_catalog(c), F.cdl_legend(c))
            return [{str(k): v for k, v in cat.items()}, leg]
        cat, leg = await self._small("cdl_meta", 7 * 86400, make)
        return {int(k): v for k, v in cat.items()}, leg

    async def swrcb(self, c, url):
        return await self._small("swrcb", 86400, lambda: F.swrcb(c, url))


STORE = Store()
INFLIGHT_CELLS: set[str] = set()


def pdir(pid: str) -> Path:
    return CACHE / "pts" / pid


def load_point(pid: str):
    """(location, strategies, meta) from the disk cache if fresh, else None."""
    m = _rj(pdir(pid) / "meta.json.gz")
    if not m or time.time() > m.get("expires", 0):
        return None
    loc = _rj(pdir(pid) / "location.json.gz")
    if loc is None:
        return None
    return loc, _rj(pdir(pid) / "strategies.json.gz"), m


def save_point(pid, loc, items, meta):
    _wj(pdir(pid) / "location.json.gz", loc)
    if items is not None:
        _wj(pdir(pid) / "strategies.json.gz", items)
    _wj(pdir(pid) / "meta.json.gz", meta)
    _prune_disk()


def _prune_disk():
    d = CACHE / "pts"
    try:
        ents = list(d.iterdir())
    except OSError:
        return
    if len(ents) <= MAX_POINTS:
        return
    ents.sort(key=lambda p: p.stat().st_mtime)
    for p in ents[: len(ents) - int(MAX_POINTS * 0.9)]:
        shutil.rmtree(p, ignore_errors=True)


# ------------------------------------------------------------------ farm catalog (backend/catalog; committed outputs)
_CAT_INDEX: list | None = None


def catalog_index() -> list:
    global _CAT_INDEX
    if _CAT_INDEX is None:
        try:
            _CAT_INDEX = json.loads((CATALOG / "index.json").read_text())
        except (OSError, ValueError):
            _CAT_INDEX = []
    return _CAT_INDEX


@functools.lru_cache(maxsize=64)
def _catalog_read(pid: str):
    d = CATALOG / pid
    try:
        loc = json.loads((d / "location.json").read_text())
    except (OSError, ValueError):
        return None
    try:
        with gzip.open(d / "strategies.json.gz", "rt") as f:
            items = json.load(f).get("items")
    except (OSError, ValueError):
        items = None
    return loc, items


def load_catalog(pid: str):
    """(location, strategies, meta) for a catalog id from the committed outputs, else None. Daily stays lazy (POWER route)."""
    if not pid.startswith("pt_") or "/" in pid or not (CATALOG / pid / "location.json").exists():
        return None
    got = _catalog_read(pid)
    if not got:
        return None
    loc, items = got
    loc = dict(loc)
    cat = loc.pop("_catalog", {})
    sections = loc.pop("sections", {})
    meta = {"id": pid, "computed_at": cat.get("built_at"), "expires_at": None, "sections": sections,
            "timings_ms": cat.get("timings_ms", {}), "catalog": cat}
    return loc, items, meta


# ------------------------------------------------------------------ presets containing the point
_PRESET_RINGS: list | None = None


def matches_preset(lon, lat) -> str | None:
    global _PRESET_RINGS
    if _PRESET_RINGS is None:
        rings = []
        for f in sorted((ROOT / "backend" / "field" / "polygons").glob("*.geojson")):
            try:
                gj = json.loads(f.read_text())
                feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
                for ft in feats:
                    for r in F.rings_of(ft.get("geometry", ft)):
                        rings.append((f.stem, r))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        _PRESET_RINGS = rings
    try:
        import fieldreg  # noqa: PLC0415
        known = set(fieldreg.ids(region=None))
    except Exception:  # noqa: BLE001
        known = set()
    return next((pid for pid, r in _PRESET_RINGS if pid in known and F.in_ring(lon, lat, r)), None)


# ------------------------------------------------------------------ analysis (cache -> compute)
async def get_or_compute(req: Request, lat: float, lon: float, refresh: bool = False):
    pid = B.point_id(lat, lon)
    ip = client_ip(req)
    if not refresh:
        cat = load_catalog(pid)
        if cat:
            GUARD.check_read(ip)
            return pid, cat, "catalog"
        hit = load_point(pid)
        if hit:
            GUARD.check_read(ip)
            return pid, hit, "hit"
    # same point already being computed by another request: wait for it rather than compute twice
    with _INF_LOCK:
        mine = pid not in INFLIGHT
        if mine:
            INFLIGHT.add(pid)
    if not mine:
        for _ in range(200):
            await asyncio.sleep(0.2)
            if pid not in INFLIGHT:
                break
        hit = load_point(pid)
        if hit:
            return pid, hit, "hit_shared"
        raise Busy(5, "this spot is still being analysed")
    try:
        try:
            GUARD.acquire_cold(ip)
        except Busy:
            raise
        try:
            plat, plon = B.parse_id(pid)
            loc, _daily, items, info = await asyncio.wait_for(B.analyse(plat, plon, STORE), 45)
        finally:
            GUARD.release_cold()
        errored = any(info["sections"].get(k, {}).get("status") == "error" for k in TIER1)
        now = time.time()
        meta = {"id": pid, "computed_at": dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(timespec="seconds"),
                "expires": now + (TTL_ERR_S if errored else TTL_S), "sections": info["sections"], "timings_ms": info["timings_ms"],
                "tapped": {"lat": lat, "lon": lon}}
        meta["expires_at"] = dt.datetime.fromtimestamp(meta["expires"], dt.timezone.utc).isoformat(timespec="seconds")
        await asyncio.to_thread(save_point, pid, loc, items, meta)
        return pid, (loc, items, meta), "miss"
    finally:
        with _INF_LOCK:
            INFLIGHT.discard(pid)


def payload(pid, hit, cache_state, plon, plat):
    loc, _items, meta = hit
    out = dict(loc)
    out["_source"] = "catalog" if cache_state == "catalog" else "live"
    out["sections"] = meta["sections"]
    out["analysis"] = {"id": pid, "point": {"lat": plat, "lon": plon}, "computed_at": meta["computed_at"],
                       "expires_at": meta["expires_at"], "cache": cache_state, "timings_ms": meta["timings_ms"],
                       "matches_preset": matches_preset(plon, plat),
                       "section_statuses": list(B.STATUSES)}
    if meta.get("catalog"):
        out["analysis"]["catalog"] = {k: meta["catalog"].get(k) for k in ("name", "crop_group", "region_name", "built_at")}
    return out


def send(resp: Response, data: dict, source: str = "live") -> dict:
    resp.headers["X-Data-Source"] = source
    resp.headers["Cache-Control"] = "public, max-age=3600" if source == "catalog" else "no-store"
    data["_source"] = source
    return data


# ------------------------------------------------------------------ routes
class PointRoute(APIRoute):
    """Matches only when the {pid} path parameter is a tapped-point id (pt_...); otherwise lets the preset routes match."""

    def matches(self, scope):
        match, child = super().matches(scope)
        if match != Match.NONE and "pid" in self.param_convertors and not str(child.get("path_params", {}).get("pid", "")).startswith("pt_"):
            return Match.NONE, {}
        return match, child


router = APIRouter(route_class=PointRoute)
LAT = Query(..., ge=-90, le=90, description="latitude, WGS84 degrees")
LON = Query(..., ge=-180, le=180, description="longitude, WGS84 degrees")


class AnalyzeBody(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    refresh: bool = False


async def _analyze(req, resp, lat, lon, refresh):
    try:
        pid, hit, state = await get_or_compute(req, lat, lon, refresh)
    except Busy as e:
        return busy_response(e)
    except asyncio.TimeoutError:
        raise HTTPException(504, "analysis took longer than 45 s; try again (partial upstream results are not cached)")
    plat, plon = B.parse_id(pid)
    return send(resp, payload(pid, hit, state, plon, plat), "catalog" if state == "catalog" else "live")


@router.get("/api/analyze")
async def analyze(req: Request, resp: Response, lat: float = LAT, lon: float = LON, refresh: bool = False):
    """Analyse any tapped point: location payload (schemas/location.schema.json) + `sections` (status per data section:
    ready | not_computed | unavailable | error) + `analysis` (id, cache hit/miss, timings, matches_preset)."""
    return await _analyze(req, resp, lat, lon, refresh)


@router.post("/api/analyze")
async def analyze_post(body: AnalyzeBody, req: Request, resp: Response):
    return await _analyze(req, resp, body.lat, body.lon, body.refresh)


def _pid_point(pid: str) -> tuple[float, float]:
    p = B.parse_id(pid)
    if p is None:
        raise HTTPException(404, f"bad point id {pid}; expected pt_<n|s><lat x 1e4>_<e|w><lon x 1e4>, e.g. pt_n391414_w1220833")
    return p


@router.get("/api/analyze/{pid}/status")
def analyze_status(pid: str, resp: Response):
    lat, lon = _pid_point(pid)
    hit = load_point(pid)
    cat = load_catalog(pid)
    hit = cat or hit
    out = {"id": pid, "point": {"lat": lat, "lon": lon}, "in_flight": pid in INFLIGHT, "cached": bool(hit), "catalog": bool(cat)}
    if hit:
        m = hit[2]
        out.update(computed_at=m["computed_at"], expires_at=m["expires_at"], sections=m["sections"], timings_ms=m["timings_ms"])
    return send(resp, out)


@router.get("/api/locations/{pid}")
async def point_location(pid: str, req: Request, resp: Response):
    lat, lon = _pid_point(pid)
    return await _analyze(req, resp, lat, lon, False)


async def _ensure(pid, req):
    lat, lon = _pid_point(pid)
    return await get_or_compute(req, lat, lon, False)


@router.get("/api/locations/{pid}/strategies")
async def point_strategies(pid: str, req: Request, resp: Response):
    try:
        _, (loc, items, meta), state = await _ensure(pid, req)
    except Busy as e:
        return busy_response(e)
    if not items:
        raise HTTPException(404, f"strategies not available for {pid}: {meta['sections']['strategies'].get('reason')}")
    return send(resp, {"location_id": pid, "items": items, "template": loc.get("template"),
                       "note": meta["sections"]["strategies"].get("reason")}, "catalog" if state == "catalog" else "live")


@router.get("/api/locations/{pid}/daily")
async def point_daily(pid: str, req: Request, resp: Response, from_: str | None = Query(None, alias="from"), to: str | None = None):
    lat, lon = _pid_point(pid)
    try:
        GUARD.check_read(client_ip(req))
        async with F.client() as c:
            df, pmeta = await asyncio.wait_for(STORE.get(c, lon, lat), 30)
    except Busy as e:
        return busy_response(e)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"NASA POWER did not answer for {pid} ({type(e).__name__})")
    d = B.daily_payload(pid, df, lat, pmeta, dt.date.today().isoformat())
    if from_ or to:
        d["rows"] = [r for r in d["rows"] if (not from_ or r["date"] >= from_) and (not to or r["date"] <= to)]
    return send(resp, d)


DEFAULT_W = {"water_use": 1, "forage_value": 1, "n_fixation": 1, "erosion": 1, "organic_matter": 1, "market": 1,
             "pest_break": 0, "infiltration": 0, "n_scavenging": 0, "income": 0}   # same defaults as main.py POST /score


class Scenario(BaseModel):
    dT_c: float = Field(0, ge=-1, le=4)
    dP_pct: float = Field(0, ge=-30, le=30)


class ScoreRequest(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    market_preference: str | None = None
    allocation: float | None = None
    replay_year: int | None = None
    scenario: Scenario = Scenario()


def _rank(strats):
    out = []
    ordered = sorted(strats, key=lambda s: -s["composite"]["value"])
    for i, s in enumerate(ordered):
        c = s["composite"]; tie = False
        if i:
            p = ordered[i - 1]["composite"]
            tie = min(c["high"], p["high"]) - max(c["low"], p["low"]) > 0.5 * min(c["high"] - c["low"], p["high"] - p["low"])
        out.append({"id": s["id"], "composite": c["value"], "low": c["low"], "high": c["high"], "tie_with_previous": tie})
    return out


@router.post("/api/locations/{pid}/score")
async def point_score(pid: str, body: ScoreRequest, req: Request, resp: Response):
    for k, v in body.weights.items():
        if k not in DEFAULT_W:
            raise HTTPException(422, f"unknown weight '{k}'; valid: {list(DEFAULT_W)}")
        if not 0 <= v <= 4:
            raise HTTPException(422, f"weight {k} must be in [0, 4]")
    w = {**DEFAULT_W, **body.weights}
    if sum(w.values()) <= 0:
        raise HTTPException(422, "at least one weight must be > 0")
    try:
        _, (loc, items, meta), _ = await _ensure(pid, req)
        if not items:
            raise HTTPException(404, f"strategies not available for {pid}: {meta['sections']['strategies'].get('reason')}")
        lat, lon = _pid_point(pid)
        GUARD.acquire_slot(client_ip(req))       # a re-score runs the engine: takes a concurrency slot, not the new-spot budget
    except Busy as e:
        return busy_response(e)
    try:
        async with F.client() as c:
            df, pmeta = await asyncio.wait_for(STORE.get(c, lon, lat), 30)
        from . import engine_bridge  # noqa: PLC0415
        entry = B.engine_entry(pid, loc["name"], loc.get("family", "other"), "bc" if loc.get("region") == "bc" else "ca", loc["centroid"])
        soil = loc.get("soil") or {}
        esoil = {k: soil.get(k) for k in ("drainage_class", "hydrologic_group", "mukey", "muname")} if soil.get("mukey") not in (None, "unavailable") else None
        try:
            res = await asyncio.to_thread(engine_bridge.run, pid, entry, df, lat, pmeta.get("elevation_m"), pmeta["url"], esoil,
                                          weights=w, constraints=body.constraints, market_preference=body.market_preference or "no_preference",
                                          allocation=body.allocation, replay_year=body.replay_year, scenario=body.scenario.model_dump())
        except ValueError as e:
            raise HTTPException(422, str(e))
    finally:
        GUARD.release_cold()
    res = B._plain(res)
    for st in res:
        gaps = (st.get("brief") or {}).get("gaps")
        if isinstance(gaps, list):
            st["brief"]["gaps"] = [{"text": g, "source_ids": []} if isinstance(g, str) else g for g in gaps]
    return send(resp, {"location_id": pid, "request": body.model_dump(), "items": res, "ranking": _rank(res),
                       "note": "scored by backend/engine for a tapped point (rule of thumb, not a model)"})


@router.get("/api/catalog")
def catalog(resp: Response, region: str | None = Query(None, description="ca | bc"),
            crop_group: str | None = Query(None, description="e.g. rice, forage, grain, nuts, grapes, citrus, vegetables, cotton, orchard, canola"),
            area: str | None = Query(None, description="catalog area, e.g. 'San Joaquin Valley', 'Okanagan'")):
    """The farm catalog: real fields across California and BC with pre-built tier-1 payloads. Open one with
    GET /api/locations/{id} (served from the committed outputs, `_source: "catalog"`)."""
    items = catalog_index()
    out = [x for x in items if (not region or x["region"] == region.lower()) and (not crop_group or x["crop_group"] == crop_group.lower())
           and (not area or x["area"].lower() == area.lower())]
    resp.headers["Cache-Control"] = "public, max-age=3600"
    resp.headers["X-Data-Source"] = "catalog"
    groups: dict = {}
    for x in items:
        groups.setdefault(x["crop_group"], {"label": x["crop_group_label"], "count": 0})["count"] += 1
    return {"count": len(out), "total": len(items), "filters": {"region": region, "crop_group": crop_group, "area": area},
            "regions": sorted({x["region"] for x in items}), "areas": sorted({x["area"] for x in items}),
            "crop_groups": groups, "items": out, "_source": "catalog"}


@router.get("/api/locations/{pid}/outlook")
def point_outlook(pid: str, resp: Response):
    """Coming-season outlook for a tapped point: nearest prepared CA field's CPC / reservoirs file (regional)."""
    lat, lon = _pid_point(pid)
    from ..outlook_near import nearest_ca_outlook  # noqa: PLC0415
    d = nearest_ca_outlook(lat, lon)
    if not d:
        raise HTTPException(404, "winter outlook is not available outside California prepared-field coverage for this tap")
    d = {**d, "location_id": pid}
    return send(resp, d, "real")


@router.get("/api/locations/{pid}/{rest:path}")
def point_other(pid: str, rest: str):
    _pid_point(pid)
    raise HTTPException(404, f"{rest} is not computed for tapped points (only the location, daily, strategies and score are); "
                             "see `sections` in GET /api/analyze for why")
