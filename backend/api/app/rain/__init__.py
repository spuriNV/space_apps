"""Rain forecast for the map: NOAA Weather Prediction Center Quantitative Precipitation Forecast (WPC QPF), the official
US forecast of total rain, issued twice a day.

  GET /api/rain_forecast?days=1|3|7          GeoJSON bands over California (property qpf = band floor, in inches)
  GET /api/rain_forecast/at?lat=&lon=&days=  the band at one point ("1 to 1.25 in")

Source: https://mapservices.weather.noaa.gov/vector/rest/services/precip/wpc_qpf/MapServer (public, no key).
Layers: 1 = Day 1 (24 h), 9 = Days 1-3 (72 h), 11 = Days 1-7 (168 h). Each feature is one contour band: rain at least
`qpf` and below the next band's value (checked: the bands do not overlap). Shapes are simplified on NOAA's side
(maxAllowableOffset) to keep the payload small, and repaired with shapely before point lookups.

Cached in memory for 3 hours and on disk (data/cache/rain/), so a NOAA outage serves the last copy with `stale: true`
and its own issue time. Outside the lower 48 (BC) there is no WPC forecast: the point route says so.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query, Response

router = APIRouter()
ROOT = Path(os.environ.get("FIELDSHIFT_ROOT", Path(__file__).resolve().parents[4]))
CACHE = ROOT / "data" / "cache" / "rain"
SERVICE = "https://mapservices.weather.noaa.gov/vector/rest/services/precip/wpc_qpf/MapServer"
LAYER = {1: 1, 3: 9, 5: 10, 7: 11}
LABEL = {1: "next 24 hours", 3: "next 3 days", 5: "next 5 days", 7: "next 7 days"}
STEPS = 12   # 6-hour steps over the next 72 hours: NOAA layers 13 (0-6 h) to 24 (66-72 h)
BBOX = (-126.0, 31.0, -109.0, 44.0)   # California with a wide margin, so the clip edge sits off-screen at the state view
TTL = 3 * 3600
# WPC contour levels (inches); a band runs from its level to the next
LEVELS = [0.01, 0.1, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5, 3, 4, 5, 7, 10, 15, 20]

_mem: dict[str, tuple[float, dict]] = {}
_shapes: dict[int, tuple[str, list]] = {}
_lock = threading.Lock()


def _fetch(days: int, step: int | None = None) -> dict:
    params = {
        "where": "1=1", "geometry": ",".join(map(str, BBOX)), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": "qpf,units,issue_time,start_time,end_time",
        "returnGeometry": "true", "outSR": 4326, "maxAllowableOffset": 0.05, "geometryPrecision": 3, "f": "geojson",
    }
    layer = 13 + step if step is not None else LAYER[days]
    r = httpx.get(f"{SERVICE}/{layer}/query", params=params, timeout=30)
    r.raise_for_status()
    fc = r.json()
    feats = [f for f in fc.get("features", []) if f.get("geometry") and (f.get("properties") or {}).get("qpf") is not None]
    if not feats:
        raise ValueError("NOAA returned no rain bands")
    p0 = feats[0]["properties"]
    for f in feats:
        q = float(f["properties"]["qpf"])
        nxt = next((x for x in LEVELS if x > q + 1e-9), None)
        f["properties"] = {"qpf": q, "qpf_next": nxt}
    feats.sort(key=lambda f: f["properties"]["qpf"])   # light bands drawn first
    return {
        "type": "FeatureCollection", "features": feats,
        "days": days, "step": step, "label": f"6 hours, from hour {step * 6}" if step is not None else LABEL[days], "units": "inches",
        "issued": p0.get("issue_time"), "valid_from": p0.get("start_time"), "valid_to": p0.get("end_time"),
        "source": {"title": "NOAA Weather Prediction Center, Quantitative Precipitation Forecast", "url": "https://www.wpc.ncep.noaa.gov/qpf/qpf2.shtml"},
        "note": "A forecast, not a guarantee. Total rain expected, in inches.",
    }


def get_forecast(days: int, step: int | None = None) -> dict:
    """The forecast for `days` (or one 6-hour `step`), from memory, NOAA, or the last copy on disk (stale)."""
    key = f"s{step}" if step is not None else f"{days}d"
    return _cached(key, TTL if step is None else 3600, lambda: _fetch(days, step), "The NOAA rain forecast is not reachable right now.")


def _cached(key: str, ttl: int, fetch, down: str) -> dict:
    with _lock:
        hit = _mem.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        f = CACHE / f"{key}.json"
        try:
            data = fetch()
            data["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            CACHE.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(data, separators=(",", ":")))
        except Exception:  # noqa: BLE001  source down or slow: the last copy, marked stale
            if hit:
                return hit[1]
            if not f.is_file():
                raise HTTPException(503, down)
            data = {**json.loads(f.read_text()), "stale": True}
        _mem[key] = (time.time(), data)
        return data


def _days(days: int) -> int:
    if days not in LAYER:
        raise HTTPException(422, "days must be 1, 3, 5 or 7")
    return days


@router.get("/api/rain_forecast")
def rain_forecast(resp: Response, days: int = Query(7), step: int | None = Query(None, ge=0, lt=STEPS)):
    """Total rain over `days`, or with `step` (0-11) the rain in one 6-hour step of the next 72 hours (the timeline)."""
    data = get_forecast(_days(days) if step is None else 1, step)
    resp.headers["Cache-Control"] = "public, max-age=900"
    return data


@router.get("/api/rain_forecast/at")
def rain_at(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180), days: int = Query(7)):
    days = _days(days)
    data = get_forecast(days)
    base = {"days": days, "label": LABEL[days], "issued": data.get("issued"), "stale": data.get("stale", False), "units": "inches"}
    if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
        return {**base, "covered": False, "note": "The NOAA forecast here covers California and nearby states only."}
    lo = _point_exact(days, lat, lon, data.get("issued") or "")
    if lo is None:  # NOAA's point query failed: read the simplified bands we already hold
        lo = _point_simplified(days, data, lat, lon)
    if lo is None:
        return {**base, "covered": True, "low": 0.0, "high": 0.01, "text": "No rain expected"}
    b = {"qpf": lo, "qpf_next": next((x for x in LEVELS if x > lo + 1e-9), None)}
    lo, hi = b["qpf"], b.get("qpf_next")
    text = f"{_fmt(lo)} to {_fmt(hi)} in" if hi else f"{_fmt(lo)} in or more"
    if lo <= 0.01:
        text = "Under 0.1 in"
    return {**base, "covered": True, "low": lo, "high": hi, "text": text}


_points: dict[tuple, tuple[float, float | None]] = {}


def _point_exact(days: int, lat: float, lon: float, issued: str) -> float | None:
    """The band floor at a point from NOAA's full-detail shapes (the map's simplified shapes can shift a band edge by a few
    miles). Cached per forecast issue and ~100 m point. Returns None when NOAA cannot be asked; 0.0 when no band covers it."""
    k = (days, issued, round(lat, 3), round(lon, 3))
    hit = _points.get(k)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    try:
        r = httpx.get(f"{SERVICE}/{LAYER[days]}/query", timeout=12, params={
            "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
            "outFields": "qpf", "returnGeometry": "false", "f": "json"})
        r.raise_for_status()
        vals = [float(f["attributes"]["qpf"]) for f in r.json().get("features", []) if f.get("attributes", {}).get("qpf") is not None]
    except Exception:  # noqa: BLE001
        return None
    v = max(vals) if vals else None
    if len(_points) > 2000:
        _points.clear()
    _points[k] = (time.time(), v)
    return v


def _point_simplified(days: int, data: dict, lat: float, lon: float) -> float | None:
    from shapely.geometry import Point, shape  # noqa: PLC0415
    from shapely.validation import make_valid  # noqa: PLC0415
    key = data.get("issued") or ""
    if _shapes.get(days, ("", []))[0] != key:
        _shapes[days] = (key, [(f["properties"], make_valid(shape(f["geometry"]))) for f in data["features"]])
    pt = Point(lon, lat)
    hit = [props["qpf"] for props, g in _shapes[days][1] if g.contains(pt)]
    return max(hit) if hit else None


def _fmt(x: float) -> str:
    return f"{x:g}"


# ---------------- drought now: US Drought Monitor (weekly; map of Tuesday, out Thursday) ----------------
USDM_URL = "https://droughtmonitor.unl.edu/data/json/usdm_current.json"
DM_NAME = {0: "D0 Abnormally dry", 1: "D1 Moderate drought", 2: "D2 Severe drought", 3: "D3 Extreme drought", 4: "D4 Exceptional drought"}


def _usdm_date() -> str:
    """The map date of the current USDM: the latest Tuesday whose map is out (released the Thursday after)."""
    import datetime as dt  # noqa: PLC0415
    today = dt.date.today()
    tue = today - dt.timedelta(days=(today.weekday() - 1) % 7)
    if today < tue + dt.timedelta(days=2):
        tue -= dt.timedelta(days=7)
    return tue.isoformat()


def _fetch_drought() -> dict:
    from shapely.geometry import box, mapping, shape  # noqa: PLC0415
    from shapely.validation import make_valid  # noqa: PLC0415
    r = httpx.get(USDM_URL, timeout=60)
    r.raise_for_status()
    clip = box(*BBOX)
    feats = []
    for f in r.json().get("features", []):
        dm = int(f["properties"]["DM"])
        g = make_valid(shape(f["geometry"])).intersection(clip)
        if g.is_empty:
            continue
        g = g.simplify(0.02, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"dm": dm, "name": DM_NAME.get(dm, f"D{dm}")}, "geometry": mapping(g)})
    feats.sort(key=lambda f: f["properties"]["dm"])
    return {"type": "FeatureCollection", "features": feats, "map_date": _usdm_date(),
            "source": {"title": "U.S. Drought Monitor (NDMC, USDA, NOAA)", "url": "https://droughtmonitor.unl.edu/"},
            "note": "Weekly drought map. Categories D0 (abnormally dry) to D4 (exceptional drought)."}


@router.get("/api/drought_now")
def drought_now(resp: Response):
    data = _cached("usdm", 12 * 3600, _fetch_drought, "The U.S. Drought Monitor map is not reachable right now.")
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return data
