"""First Nations reserves and tribal lands for the CropLytics map (context and Nation panel; boundaries are legal/statistical
boundaries, not traditional territory and not where a Nation's rights apply).

BC: every Indian reserve in WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP (BC Data Catalogue WFS, paged, EPSG:4326).
California: US Census TIGERweb AIANNHA layers 2 (federal reservations) and 3 (off-reservation trust lands), clipped to California.

Writes backend/api/out/lands/lands.geojson (simplified to ~75 m, coordinates rounded to 5 decimals). Served by GET /api/lands.
Run: cd backend/nation && uv run --project ../bc python fetch_lands.py
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import requests
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "bc"))
from nations import nation as bc_nation  # noqa: E402

OUT = HERE.parent / "api" / "out" / "lands" / "lands.geojson"
WFS = "https://openmaps.gov.bc.ca/geo/pub/wfs"
BC_LAYER = "WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP"
BC_URL = "https://catalogue.data.gov.bc.ca/dataset/8efe9193-80d2-4fdf-a18c-d531a94196ad"
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
UA = {"User-Agent": "CropLytics NASA Space Apps 2026 (backend/nation; research use)"}
SIMPLIFY_DEG = 0.0007       # about 75 m
GEOD = Geod(ellps="WGS84")


def get(url, params, timeout=180):
    last = None
    for i in range(5):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers=UA)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (i + 1))
    raise last


def area_ha(g) -> float:
    return abs(GEOD.geometry_area_perimeter(g)[0]) / 1e4


def finish(g, tol=SIMPLIFY_DEG):
    g = g.simplify(tol, preserve_topology=True)
    if g.is_empty:
        return None
    def rr(c): return [[round(x, 5), round(y, 5)] for x, y in c]
    polys = [g] if isinstance(g, Polygon) else [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]
    out = [[rr(p.exterior.coords)] + [rr(i.coords) for i in p.interiors] for p in polys if not p.is_empty]
    if not out:
        return None
    return {"type": "Polygon", "coordinates": out[0]} if len(out) == 1 else {"type": "MultiPolygon", "coordinates": out}


def rep(g):
    """A point inside the land (not the bounding-box centre), [lon, lat] to 4 decimals (the tap-anywhere grid)."""
    p = g.representative_point()
    return [round(p.x, 4), round(p.y, 4)]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def bc_lands():
    feats, start = [], 0
    while True:
        d = get(WFS, {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeName": BC_LAYER, "outputFormat": "json",
                      "srsName": "EPSG:4326", "sortBy": "OBJECTID", "count": 500, "startIndex": start})
        got = d["features"]
        feats += got
        if len(got) < 500:
            break
        start += 500
    out = []
    for f in feats:
        p = f["properties"]
        g = shape(f["geometry"])
        geom = finish(g)
        if not geom:
            continue
        name = (p.get("ENGLISH_NAME") or "").strip()
        nm = re.sub(r"(^|[\s(])(\w)", lambda m: m.group(1) + m.group(2).upper(), name.lower()).replace("No.", "No.") or name
        out.append({"type": "Feature", "geometry": geom, "properties": {
            "id": f"bc-{p['OBJECTID']}", "name": nm, "nation": bc_nation(p.get("BAND_NAME")), "band_number": str(p.get("BAND_NUMBER")),
            "area_ha": round(area_ha(g), 1), "kind": "reserve", "province": "BC", "centroid": rep(g)}})
    return out


def ca_lands():
    st = get(f"{TIGER}/State_County/MapServer/0/query", {"where": "STATE='06'", "outFields": "NAME", "outSR": 4326, "f": "geojson", "maxAllowableOffset": 0.0005})
    ca = unary_union([shape(f["geometry"]).buffer(0) for f in st["features"]])
    out = []
    for layer, kind in ((2, "reservation"), (3, "trust")):
        offset = 0
        while True:
            d = get(f"{TIGER}/AIANNHA/MapServer/{layer}/query", {
                "geometry": "-124.6,32.4,-114.0,42.1", "geometryType": "esriGeometryEnvelope", "inSR": 4326, "outSR": 4326,
                "spatialRel": "esriSpatialRelIntersects", "outFields": "NAME,BASENAME,GEOID,AIANNH", "where": "1=1", "f": "geojson",
                "maxAllowableOffset": 0.0003, "resultOffset": offset, "resultRecordCount": 100})
            for f in d["features"]:
                g = shape(f["geometry"]).buffer(0).intersection(ca)
                if g.is_empty or g.area == 0:
                    continue
                geom = finish(g)
                p = f["properties"]
                if not geom:
                    continue
                name = (p.get("NAME") or "").strip()
                nation = re.sub(r"\s+(Indian\s+)?(Reservation|Off-Reservation Trust Land)(\s+and\s+Off-Reservation Trust Land)?$", "", name, flags=re.I).strip() or name
                out.append({"type": "Feature", "geometry": geom, "properties": {
                    "id": f"ca-{kind[0]}{p.get('GEOID') or slug(name)}", "name": name, "nation": nation,
                    "area_ha": round(area_ha(g), 1), "kind": kind, "state": "CA", "centroid": rep(g)}})
            if len(d["features"]) < 100 and not d.get("exceededTransferLimit"):
                break
            offset += 100
    return out


def main():
    bc, ca = bc_lands(), ca_lands()
    fc = {"type": "FeatureCollection", "properties": {
        "fetched": dt.date.today().isoformat(), "simplified_m": 75, "coordinate_decimals": 5,
        "note": "Legal and statistical boundaries, not traditional territory and not where a Nation's rights apply.",
        "counts": {"bc": len(bc), "ca": len(ca)},
        "sources": [
            {"region": "BC", "title": "Indian reserves with band names (CLSS legal boundaries), BC Data Catalogue", "layer": BC_LAYER, "wfs": WFS, "url": BC_URL,
             "licence": "Open Government Licence - British Columbia"},
            {"region": "CA", "title": "US Census TIGERweb AIANNHA: Federal American Indian Reservations (layer 2) and Off-Reservation Trust Lands (layer 3), clipped to California",
             "url": TIGER + "/AIANNHA/MapServer", "page": "https://www.census.gov/programs-surveys/geography/guidance/geo-areas/aian.html"}]},
        "features": bc + ca}
    ids = [f["properties"]["id"] for f in fc["features"]]
    assert len(ids) == len(set(ids)), "duplicate ids"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fc, separators=(",", ":")))
    print(f"BC {len(bc)}, CA {len(ca)}, {OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
