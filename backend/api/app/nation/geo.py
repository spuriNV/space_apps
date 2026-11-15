"""Live land-status and nearest-Nation lookups (stdlib + httpx; no shapely).

BC: WFS layer WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP (legal reserve boundaries with band names).
US: Census TIGERweb AIANNHA MapServer, layer 2 (federal American Indian reservations) and layer 3 (off-reservation trust lands).
Both are legal/statistical boundaries, not traditional territory and not where a Nation's rights apply.
Results are kept in memory for an hour per ~100 m cell (a speed-up only; nothing is written to disk).
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend" / "bc"))
try:
    from nations import nation as bc_nation  # noqa: E402  (backend/bc/nations.py, stdlib only)
except Exception:  # noqa: BLE001
    bc_nation = lambda b: b  # noqa: E731

BC_WFS = "https://openmaps.gov.bc.ca/geo/pub/wfs"
BC_LAYER = "WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP"
BC_URL = "https://catalogue.data.gov.bc.ca/dataset/8efe9193-80d2-4fdf-a18c-d531a94196ad"
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/AIANNHA/MapServer"
TIGER_URL = "https://www.census.gov/programs-surveys/geography/guidance/geo-areas/aian.html"
RADIUS_DEG = 0.6          # about 65 km in latitude
_cache: dict = {}


def _rings(geom: dict) -> list[list[list[float]]]:
    """Every ring of a Polygon/MultiPolygon as (outer, hole...) groups flattened: returns [[outer, *holes], ...]."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return list(geom["coordinates"])
    return []


def _in_ring(x, y, ring) -> bool:
    ins = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


def _seg_km(px, py, ax, ay, bx, by, kx) -> float:
    ax, bx, px = ax * kx, bx * kx, px * kx
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)) * 111.32


def distance_km(lon: float, lat: float, geom: dict) -> tuple[float, bool]:
    """(km from the point to the polygon edge, point inside). Distance is 0 when inside."""
    kx = math.cos(math.radians(lat))
    best, inside = 1e9, False
    for poly in _rings(geom):
        if _in_ring(lon, lat, poly[0]) and not any(_in_ring(lon, lat, h) for h in poly[1:]):
            return 0.0, True
        for ring in poly:
            for a, b in zip(ring, ring[1:]):
                best = min(best, _seg_km(lon, lat, a[0], a[1], b[0], b[1], kx))
    return round(best, 2), inside


def _bbox(lon, lat):
    return lon - RADIUS_DEG / max(0.3, math.cos(math.radians(lat))), lat - RADIUS_DEG, lon + RADIUS_DEG / max(0.3, math.cos(math.radians(lat))), lat + RADIUS_DEG


def _get(url, params, timeout=12.0):
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=5.0), follow_redirects=True) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        return r.json()


def _bc(lon, lat) -> dict:
    x0, y0, x1, y1 = _bbox(lon, lat)
    d = _get(BC_WFS, {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeName": BC_LAYER, "outputFormat": "json",
                      "srsName": "EPSG:4326", "count": 300, "bbox": f"{x0},{y0},{x1},{y1},EPSG:4326"}, 20)
    areas = []
    for f in d.get("features", []):
        p = f["properties"]
        km, inside = distance_km(lon, lat, f["geometry"])
        areas.append({"name": p.get("ENGLISH_NAME"), "nation": bc_nation(p.get("BAND_NAME")), "band_name": p.get("BAND_NAME"),
                      "kind": "reserve", "distance_km": km, "inside": inside})
    return {"areas": areas, "source": {"title": "Indian reserves with band names (CLSS legal boundaries), BC Data Catalogue",
                                       "url": BC_URL, "layer": BC_LAYER, "licence": "Open Government Licence - British Columbia"}}


def _us(lon, lat) -> dict:
    x0, y0, x1, y1 = _bbox(lon, lat)
    areas, err = [], []
    for layer, kind in ((2, "reservation"), (3, "off-reservation trust land")):
        try:
            d = _get(f"{TIGER}/{layer}/query", {"geometry": f"{x0},{y0},{x1},{y1}", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                                                "outSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "NAME,GEOID",
                                                "maxAllowableOffset": 0.002, "f": "geojson"}, 20)
        except Exception as e:  # noqa: BLE001
            err.append(f"layer {layer}: {type(e).__name__}")
            continue
        for f in d.get("features", []):
            km, inside = distance_km(lon, lat, f["geometry"])
            nm = (f["properties"].get("NAME") or "").strip()
            areas.append({"name": nm, "nation": nm, "band_name": None, "kind": kind, "distance_km": km, "inside": inside})
    if len(err) == 2:
        raise RuntimeError("; ".join(err))
    return {"areas": areas, "errors": err, "source": {"title": "US Census TIGERweb American Indian/Alaska Native/Native Hawaiian areas (reservations, off-reservation trust lands)",
                                                      "url": TIGER_URL, "layer": TIGER}}


_CAN_POLY = None


def in_canada(lon: float, lat: float) -> bool:
    """Coarse test (about 20 km) for 'north of the US border': picks the Canada programs and reserve source for a tapped point."""
    global _CAN_POLY
    if _CAN_POLY is None:
        from shapely.geometry import Polygon
        _CAN_POLY = Polygon([(-141, 84), (-141, 60), (-137.5, 58.9), (-135.5, 59.6), (-134, 58.5), (-132, 56.6), (-130, 55.9), (-130, 54.7), (-135, 51), (-129, 48), (-123.0, 48.2),
                             (-123.0, 49.0), (-95.15, 49.0), (-95.15, 49.4), (-94.6, 48.7), (-92.0, 48.3), (-89.6, 48.0), (-88.4, 48.3), (-84.8, 46.5), (-83.5, 46.0), (-82.5, 45.3), (-82.4, 43.0),
                             (-83.2, 42.0), (-82.4, 42.2), (-80.0, 42.2), (-79.0, 42.85), (-79.0, 43.65), (-76.3, 44.1), (-75.0, 44.9), (-71.5, 45.0), (-70.8, 45.4), (-70.3, 46.1),
                             (-69.2, 47.45), (-68.3, 47.35), (-67.8, 47.07), (-67.8, 45.7), (-67.4, 45.2), (-66.9, 44.8), (-66.0, 43.0), (-58, 44), (-50, 52), (-50, 84)])
    from shapely.geometry import Point
    return _CAN_POLY.contains(Point(lon, lat))


def _can(lon, lat) -> dict:
    """Canada outside BC: the NRCan CLSS reserves in backend/api/out/lands (same file as /api/lands)."""
    from .. import lands as L
    areas = []
    for f in L._load()["features"]:
        p = f["properties"]
        if p.get("country") != "CAN":
            continue
        w, s, e, n = p["bbox"]
        if lon < w - 0.3 or lon > e + 0.3 or lat < s - 0.3 or lat > n + 0.3:
            continue
        km, inside = distance_km(lon, lat, f["geometry"])
        areas.append({"name": p["name"], "nation": p["nation"], "band_name": None, "kind": "reserve", "distance_km": km, "inside": inside})
    return {"areas": areas, "source": {"title": "Aboriginal Lands of Canada Legislative Boundaries (NRCan CLSS)", "url": "https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067",
                                       "licence": "Open Government Licence - Canada"}}


def nearby(lon: float, lat: float, region: str) -> dict:
    """{'ok': bool, 'areas': [...sorted by distance], 'source': {...}, 'error'?}. Never raises."""
    key = (round(lon, 3), round(lat, 3), region)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    try:
        r = _bc(lon, lat) if region == "bc" else _can(lon, lat) if region == "can" else _us(lon, lat)
        r["ok"] = True
        r["areas"].sort(key=lambda a: a["distance_km"])
    except Exception as e:  # noqa: BLE001
        r = {"ok": False, "areas": [], "error": f"{type(e).__name__}: {str(e)[:120]}",
             "source": {"title": "BC reserve boundaries" if region == "bc" else "US Census AIANNH", "url": BC_URL if region == "bc" else TIGER_URL}}
    if r["ok"]:
        _cache[key] = (time.time(), r)
        if len(_cache) > 500:
            _cache.pop(next(iter(_cache)))
    return r


def land_status(res: dict, region: str) -> dict:
    """reserve / trust / fee / private / unknown from a nearby() result."""
    src = res["source"]
    if not res["ok"]:
        return {"value": "unknown", "detail": f"boundary lookup failed ({res.get('error')})", "area_name": None, "nation": None, "source": src}
    ins = [a for a in res["areas"] if a["inside"]]
    if ins:
        a = ins[0]
        if a["kind"] == "off-reservation trust land":
            return {"value": "trust", "detail": "The point is inside an off-reservation trust land area (US Census boundary).", "area_name": a["name"], "nation": a["nation"], "source": src}
        note = ("The point is inside a federal reservation boundary (US Census). Reservations can include fee-simple parcels; this does not show tenure of an individual parcel."
                if region != "bc" else "The point is inside a reserve boundary (CLSS legal boundary).")
        return {"value": "reserve", "detail": note, "area_name": a["name"], "nation": a["nation"], "source": src}
    return {"value": "private", "detail": "The point is outside every reserve/reservation and off-reservation trust boundary in this layer; it may be Crown, state, fee-simple or allotted land. "
                                           "This layer does not show individual allotments or tenure.", "area_name": None, "nation": None, "source": src}
