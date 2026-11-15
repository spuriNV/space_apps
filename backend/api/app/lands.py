"""First Nations reserves and tribal lands (backend/nation/fetch_lands.py -> backend/api/out/lands/lands.geojson).

  GET /api/lands        GeoJSON of the lands: whole file, or ?bbox=w,s,e,n&country=US|CAN&province=&state=&min_ha=&limit= (the map viewport)
  GET /api/lands/overview  every land without outlines (id, name, Nation, kind, area, region, centroid, bbox) for the zoomed-out map and the list
  GET /api/lands/{id}   one land: name, Nation, area, kind, centroid, nearby catalog farms and prepared fields within 15 km,
                        links to the Nation tools at its centroid, the Nation's public website when backend data has one

Boundaries are legal or statistical lines, not traditional territory and not where a Nation's rights apply.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[3]
LANDS = ROOT / "backend" / "api" / "out" / "lands" / "lands.geojson"
CATALOG = ROOT / "backend" / "api" / "out" / "catalog" / "index.json"
NEAR_KM = 15
router = APIRouter()
KIND = {"reserve": "Reserve", "reservation": "Tribal land", "trust": "Tribal land", "other": "Tribal area",
        "inuit_land": "Inuit land", "settlement_land": "Settlement land"}
KINDS = ["reserve", "reservation", "trust", "other", "inuit_land", "settlement_land"]


@lru_cache(maxsize=1)
def _load() -> dict:
    d = json.loads(LANDS.read_text())
    d["_by_id"] = {f["properties"]["id"]: f for f in d["features"]}
    d["_json"] = {f["properties"]["id"]: _fjson(f) for f in d["features"]}
    rows = []
    for f in d["features"]:
        p = f["properties"]
        rows.append([p["id"], p["name"], p["nation"], KINDS.index(p["kind"]) if p["kind"] in KINDS else 3, p["area_ha"], p["country"], _region(p), *p["centroid"], *p["bbox"]])
    d["_overview"] = json.dumps({"cols": ["id", "name", "nation", "kind", "area_ha", "country", "region", "lon", "lat", "w", "s", "e", "n"], "kinds": KINDS,
                                 "fetched": d["properties"].get("fetched"), "rows": rows}, separators=(",", ":"), ensure_ascii=False)
    return d


def _km(lon1, lat1, lon2, lat2) -> float:
    kx = math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lon1 - lon2) * kx, lat1 - lat2) * 111.32


def _sid(lat: float, lon: float) -> str:
    return f"pt_{'s' if lat < 0 else 'n'}{round(abs(lat) * 1e4)}_{'w' if lon < 0 else 'e'}{round(abs(lon) * 1e4)}"


@lru_cache(maxsize=1)
def _sites() -> dict:
    """Nation display name -> public website, from the BC First Nations card (backend/bc/build_api.py) where it names one."""
    out: dict = {}
    for f in (ROOT / "backend" / "api" / "out").glob("*/first_nations.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:  # noqa: BLE001
            continue
        for c in d.get("contacts", []):
            if c.get("url", "").startswith("https://") and c.get("nation"):
                out.setdefault(c["nation"], c["url"])
        ln = d.get("lower_river_nation") or {}
        if ln.get("url", "").startswith("https://") and ln.get("nation"):
            out.setdefault(ln["nation"], ln["url"])
    return out


@lru_cache(maxsize=1)
def _presets() -> list[dict]:
    from . import main as M  # lazy: main imports this module
    out = []
    for pid in M.PRESETS:
        try:
            loc, _ = M.resolve("location", pid)
            c = loc["centroid"]
            out.append({"id": pid, "name": loc.get("farmer_name") or loc.get("short_name") or loc.get("name") or pid, "lat": c["lat"], "lon": c["lon"], "kind": "prepared field"})
        except Exception:  # noqa: BLE001
            continue
    return out


def _norm_country(c: str | None) -> str | None:
    if not c:
        return None
    c = c.strip().upper()
    if c in ("US", "USA", "UNITED STATES"):
        return "US"
    if c in ("CAN", "CANADA"):
        return "CAN"
    raise HTTPException(422, "country must be US or CAN (Canada)")


def _fjson(f: dict) -> str:
    return json.dumps(f, separators=(",", ":"))


def _region(p: dict) -> str:
    return p.get("province") or p.get("state") or ""


@router.get("/api/lands")
def lands(resp: Response, bbox: str | None = Query(None, description="west,south,east,north (lon/lat): lands that touch it"),
          country: str | None = Query(None, description="US | CAN"), province: str | None = None, state: str | None = None,
          min_ha: float = Query(0, ge=0), limit: int = Query(4000, ge=1, le=20000)):
    """GeoJSON of the lands. No filters: the whole file. With a bbox (the map viewport) only lands that touch it, largest first, up to `limit`."""
    if not LANDS.is_file():
        raise HTTPException(404, "lands.geojson not built (run backend/nation/fetch_lands.py)")
    hdr = {"Cache-Control": "public, max-age=86400"}
    if not (bbox or country or province or state or min_ha):
        return FileResponse(LANDS, media_type="application/geo+json", headers=hdr)
    d = _load()
    cc, pv, st = _norm_country(country), (province or "").upper(), (state or "").upper()
    box = None
    if bbox:
        try:
            box = [float(x) for x in bbox.split(",")]
            assert len(box) == 4
        except Exception:  # noqa: BLE001
            raise HTTPException(422, "bbox must be west,south,east,north") from None
    out = []
    for f in d["features"]:
        p = f["properties"]
        if cc and p.get("country") != cc or pv and p.get("province") != pv or st and p.get("state") != st or p["area_ha"] < min_ha:
            continue
        if box:
            w, s, e, n = p["bbox"]
            if e < box[0] or w > box[2] or n < box[1] or s > box[3]:
                continue
        out.append(f)
    total = len(out)
    out.sort(key=lambda f: -f["properties"]["area_ha"])
    out = out[:limit]
    body = '{"type":"FeatureCollection","properties":{"total":%d,"returned":%d},"features":[%s]}' % (total, len(out), ",".join(d["_json"][f["properties"]["id"]] for f in out))
    return Response(body, media_type="application/geo+json", headers=hdr)


@router.get("/api/lands/overview")
def overview():
    """Light index of every land without outlines (for the zoomed-out map and the list): one row per land, columns named in `cols`."""
    if not LANDS.is_file():
        raise HTTPException(404, "lands.geojson not built")
    return Response(_load()["_overview"], media_type="application/json", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/api/lands/{lid}")
def land(lid: str, resp: Response):
    if not LANDS.is_file():
        raise HTTPException(404, "lands.geojson not built")
    f = _load()["_by_id"].get(lid)
    if not f:
        raise HTTPException(404, f"unknown land {lid}")
    p = f["properties"]
    lon, lat = p["centroid"]
    pid = _sid(lat, lon)
    near = []
    try:
        for it in json.loads(CATALOG.read_text()):
            km = _km(lon, lat, it["lon"], it["lat"])
            if km <= NEAR_KM:
                near.append({"id": it["id"], "name": it["name"], "lat": it["lat"], "lon": it["lon"], "kind": "catalog farm", "crop": it.get("crop_group_label"), "acres": it.get("acres"), "distance_km": round(km, 1)})
    except Exception:  # noqa: BLE001
        pass
    for it in _presets():
        km = _km(lon, lat, it["lon"], it["lat"])
        if km <= NEAR_KM:
            near.append({**it, "distance_km": round(km, 1)})
    near.sort(key=lambda x: x["distance_km"])
    jur = "BC" if p.get("province") == "BC" else "CAN" if p.get("country") == "CAN" else "CA" if p.get("state") == "CA" else "US"
    base = f"/api/locations/{pid}/nation"
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return {
        "id": lid, "name": p["name"], "nation": p["nation"], "kind": p["kind"], "kind_label": KIND.get(p["kind"], "Tribal land"),
        "jurisdiction": jur, "area_ha": p["area_ha"], "area_acres": round(p["area_ha"] * 2.47105, 1), "band_number": p.get("band_number"),
        "centroid": {"lon": lon, "lat": lat}, "location_id": pid,
        "nearby": near[:12], "nearby_radius_km": NEAR_KM,
        "tools": {"summary": base, "drought_rotation": f"{base}/drought_rotation", "groundwater": f"{base}/groundwater", "land_season": f"{base}/land_season",
                  "funding": f"{base}/funding?jurisdiction={jur}", "report_pdf": f"{base}/report.pdf"},
        "website": _sites().get(p["nation"]),
        "caveat": "Reserve, reservation and trust boundaries are legal or statistical lines, not traditional territory and not where a Nation's rights apply.",
        "country": p["country"], "region": _region(p),
        "source": next((s for s in _load()["properties"]["sources"] if s["region"] == {"BC": "BC", "CAN": "CAN"}.get(jur, "US")), None),
    }
