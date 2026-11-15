"""First Nations reserves and tribal lands for the CropLytics map (context and Nation panel; boundaries are legal/statistical
boundaries, not traditional territory and not where a Nation's rights apply).

Whole of the US and Canada: US TIGERweb AIANNHA (layers 2-7), Canada NRCan CLSS Aboriginal Lands (outside BC).
BC: every Indian reserve in WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP (BC Data Catalogue WFS, paged, EPSG:4326).

Writes backend/api/out/lands/lands.geojson (simplified by land size, coordinates rounded to 4-5 decimals). Served by GET /api/lands.
Run: cd backend/nation && uv run --project ../bc python fetch_lands.py
"""
from __future__ import annotations

import datetime as dt
import json
import math
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


def finish(g, tol=SIMPLIFY_DEG, dec=5):
    if tol:
        g = g.simplify(tol, preserve_topology=True)
    if g.is_empty:
        return None
    def rr(c): return [[round(x, dec), round(y, dec)] for x, y in c]
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
        name = (p.get("ENGLISH_NAME") or "").strip()
        nm = re.sub(r"(^|[\s(])(\w)", lambda m: m.group(1) + m.group(2).upper(), name.lower()).replace("No.", "No.") or name
        out.append((g, {"id": f"bc-{p['OBJECTID']}", "name": nm, "nation": bc_nation(p.get("BAND_NAME")), "band_number": str(p.get("BAND_NUMBER")),
                        "kind": "reserve", "country": "CAN", "province": "BC"}))
    return out


US_LAYERS = ((2, "reservation", "r"), (3, "trust", "t"), (4, "reservation", "s"), (5, "trust", "h"), (6, "other", "a"), (7, "other", "o"))
CAN_PROV = {"Yukon": "YT", "Northwest Territories": "NT", "Manitoba": "MB", "Alberta": "AB", "Quebec": "QC", "Ontario": "ON", "Prince Edward Island": "PE",
            "Nunavut": "NU", "Newfoundland and Labrador": "NL", "Saskatchewan": "SK", "Nova Scotia": "NS", "British Columbia": "BC", "New Brunswick": "NB"}
CLSS = "https://proxyinternet.nrcan-rncan.gc.ca/arcgis/rest/services/CLSS-SATC/CLSS_Administrative_Boundaries/MapServer/0"
CLSS_URL = "https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067"
CAN_SKIP = {"Inuit Owned Land", "Inuvialuit Land"}  # not First Nations reserves
CAN_KIND = {"Indian Reserve": "reserve", "Indian Land": "reserve"}
SMALL = {"of", "the", "and", "de", "la", "du", "des", "at", "on", "in", "no."}


def tcase(s: str) -> str:
    out = []
    for i, w in enumerate(s.lower().split()):
        out.append("No." if w in ("no.", "no") and i else "IR" if w in ("ir", "i.r.") else w.upper() if re.fullmatch(r"\d+[a-z]?(\([a-z0-9]+\))?", w) else w if (w in SMALL and i) else re.sub(r"(^|[-(/'’])([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), w))
    return " ".join(out)


def can_nation(name: str) -> str:
    n = re.sub(r"\s+(I\.?\s?R\.?|INDIAN RESERVE|RESERVE|INDIAN SETTLEMENT)\b.*$", "", name, flags=re.I)
    n = re.sub(r"\s+NO\.?\s*[\dA-Z][\dA-Z\-]*$", "", n, flags=re.I)
    n = re.sub(r"(\s+\d[\dA-Z\-]*(\s*\([A-Z0-9]+\))?)+$", "", n).strip(" ,-")
    return tcase(n or name)


def us_states():
    """STUSAB polygons (coarse) to name the state of each tribal land by a point inside it."""
    d = get(f"{TIGER}/State_County/MapServer/0/query", {"where": "1=1", "outFields": "STUSAB", "outSR": 4326, "f": "geojson", "maxAllowableOffset": 0.01, "resultRecordCount": 100})
    sts = [(f["properties"]["STUSAB"], shape(f["geometry"]).buffer(0)) for f in d["features"]]
    return sts


def state_of(g, sts):
    pt = g.representative_point()
    for ab, sg in sts:
        if sg.contains(pt):
            return ab
    return min(sts, key=lambda s: s[1].distance(pt))[0]


def us_lands():
    sts = us_states()
    out = []
    for layer, kind, letter in US_LAYERS:
        offset = 0
        while True:
            d = get(f"{TIGER}/AIANNHA/MapServer/{layer}/query", {
                "where": "1=1", "outFields": "NAME,BASENAME,GEOID", "outSR": 4326, "f": "geojson",
                "maxAllowableOffset": 0.0004, "resultOffset": offset, "resultRecordCount": 25})
            for f in d["features"]:
                if not f.get("geometry"):
                    continue
                g = shape(f["geometry"]).buffer(0)
                if g.is_empty or g.area == 0:
                    continue
                p = f["properties"]
                name = (p.get("NAME") or "").strip()
                nation = re.sub(r"\s+(Indian\s+)?(Reservation|Off-Reservation Trust Land|ANVSA|OTSA|Hawaiian Home Land)(\s+and\s+Off-Reservation Trust Land)?$", "", name, flags=re.I).strip() or name
                st = state_of(g, sts)
                out.append((g, {"id": f"{'ca' if st == 'CA' else 'us'}-{letter}{p.get('GEOID') or slug(name)}", "name": name, "nation": nation,
                                "kind": kind, "country": "US", "state": st}))
            if len(d["features"]) < 25 and not d.get("exceededTransferLimit"):
                break
            offset += 25
    return out


def can_lands():
    out, offset = [], 0
    while True:
        d = get(f"{CLSS}/query", {"where": "jurisdictionEng <> 'British Columbia'", "outFields": "OBJECTID,adminAreaId,adminAreaNameEng,distributionTypeEng,jurisdictionEng",
                                  "outSR": 4326, "f": "geojson", "maxAllowableOffset": 0.0004, "resultOffset": offset, "resultRecordCount": 100})
        for f in d["features"]:
            p = f["properties"]
            if p["distributionTypeEng"] in CAN_SKIP or not f.get("geometry"):
                continue
            g = shape(f["geometry"]).buffer(0)
            if g.is_empty:
                continue
            raw = (p["adminAreaNameEng"] or "").strip()
            out.append((g, {"id": f"can-{p['adminAreaId']}", "oid": p["OBJECTID"], "name": tcase(raw), "nation": can_nation(raw), "kind": CAN_KIND.get(p["distributionTypeEng"], "other"),
                            "country": "CAN", "province": CAN_PROV.get(p["jurisdictionEng"], p["jurisdictionEng"])}))
        if len(d["features"]) < 100 and not d.get("exceededTransferLimit"):
            break
        offset += 100
    return out


def tol_for(g, ha):
    w, s, e, n = g.bounds
    diag = max(e - w, n - s)
    return min(0.012, max(0.00006, diag * 0.004))


def circle(g, ha):
    p = g.representative_point()
    r = math.sqrt(ha * 1e4 / math.pi)
    return Point(p.x, p.y).buffer(r / 111320 / max(0.2, math.cos(math.radians(p.y))) , 6) if False else Polygon(
        [(p.x + r / (111320 * max(0.2, math.cos(math.radians(p.y)))) * math.cos(a * math.pi / 5), p.y + r / 111320 * math.sin(a * math.pi / 5)) for a in range(10)])


def feature(g, props):
    ha = area_ha(g)
    if ha < 2:
        sg = circle(g, max(ha, 0.05))  # very small land: a small circle of the same area around a point inside it
        dec = 5
    else:
        sg, dec = g, 5 if ha < 300 else 4
    geom = finish(sg, 0 if ha < 2 else tol_for(g, ha), dec)
    if not geom:
        return None
    pt = rep(g)
    w, s, e, n = g.bounds
    props = {**props, "area_ha": round(ha, 1), "centroid": pt, "bbox": [round(w, 3), round(s, 3), round(e, 3), round(n, 3)]}
    props.pop("oid", None)
    return {"type": "Feature", "geometry": geom, "properties": props}


def main():
    bc = [x for x in (feature(g, p) for g, p in bc_lands()) if x]
    us = [x for x in (feature(g, p) for g, p in us_lands()) if x]
    can = [x for x in (feature(g, p) for g, p in can_lands()) if x]
    seen = {}
    for f in us + can:  # ids must be unique
        i = f["properties"]["id"]
        seen[i] = seen.get(i, 0) + 1
        if seen[i] > 1:
            f["properties"]["id"] = f"{i}-{seen[i]}"
    feats = bc + us + can
    fc = {"type": "FeatureCollection", "properties": {
        "fetched": dt.date.today().isoformat(), "coordinate_decimals": "4-5, simplified by land size",
        "note": "Legal and statistical boundaries, not traditional territory and not where a Nation's rights apply.",
        "counts": {"bc": len(bc), "canada_other": len(can), "us": len(us)},
        "sources": [
            {"region": "BC", "title": "Indian reserves with band names (CLSS legal boundaries), BC Data Catalogue", "layer": BC_LAYER, "wfs": WFS, "url": BC_URL,
             "licence": "Open Government Licence - British Columbia"},
            {"region": "CAN", "title": "Aboriginal Lands of Canada Legislative Boundaries (NRCan CLSS), outside British Columbia", "url": CLSS_URL,
             "licence": "Open Government Licence - Canada"},
            {"region": "US", "title": "US Census TIGERweb AIANNHA: reservations, off-reservation trust lands, state reservations, Hawaiian Home Lands, Alaska Native village and Oklahoma tribal statistical areas",
             "url": TIGER + "/AIANNHA/MapServer", "page": "https://www.census.gov/programs-surveys/geography/guidance/geo-areas/aian.html"}]},
        "features": feats}
    ids = [f["properties"]["id"] for f in feats]
    assert len(ids) == len(set(ids)), "duplicate ids"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fc, separators=(",", ":")))
    print(f"BC {len(bc)}, Canada other {len(can)}, US {len(us)}, {OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
