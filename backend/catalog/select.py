"""Pick the farm catalog: ~150 real California fields and ~40 real BC fields, spread out, stratified by area and crop group.

California: DWR / Land IQ Statewide Crop Mapping 2023 (final) polygons, 20-300 acres, by MAIN_CROP code and county. The
2023 USDA Cropland Data Layer at the field's interior point must agree with the crop group (the Land IQ code table is not
published with the service, so CDL is the check), and the farmer-facing crop word comes from that CDL class.

BC: AAFC Annual Crop Inventory 2025 and 2024 (ImageServer exportImage, 30 m, BC Albers) per area box: pixels in the same
crop group both years, grouped into connected patches. A patch's interior point is kept when the ParcelMap BC parcel there,
clipped to the Agricultural Land Reserve, contains it, is 20-300 acres and is >= 50 % that crop group in 2025. The parcel
id and owner are never stored.

Spread: within an (area, crop group) cell, farthest-point sampling; every catalog point is >= MIN_SEP_KM from every other,
so no two fields touch. Reserve and tribal land are not excluded (the user asked for no special handling).

Names: "<crop word> near <nearest place>, <county or regional district>", the place from US Census TIGERweb incorporated
places / CDPs or the Canadian Geographical Names Database.

Writes backend/catalog/out/selection.json. Run: cd backend/catalog && uv run python select.py [--only ca|bc] [--seed 7]
"""
from __future__ import annotations

import argparse
import io
import json
import math
import random
import re

import time
from pathlib import Path

import warnings

import httpx
import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union

warnings.filterwarnings("ignore", category=DeprecationWarning)
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "out" / "selection.json"


def point_id(lat: float, lon: float) -> str:
    """Same id as backend/api/app/anyloc/build.py point_id (4 decimals)."""
    la, lo = round(lat * 1e4), round(lon * 1e4)
    return f"pt_{'n' if la >= 0 else 's'}{abs(la)}_{'e' if lo >= 0 else 'w'}{abs(lo)}"

UA = {"User-Agent": "CropLytics/0.1 (NASA Space Apps crop-rotation planner; farm catalog builder)"}
DWR = ("https://utility.arcgis.com/usrsvcs/servers/d94e891e00364e49a2ed9e9e2e27837d/rest/services/"
       "Planning/i15_Crop_Mapping_2023/MapServer/0")
CDL = "https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer"
PLACES = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer"
GEONAMES = "https://geogratis.gc.ca/services/geoname/en/geonames.json"
ACI = "https://agriculture.canada.ca/imagery-images/rest/services/annual_crop_inventory/{year}/ImageServer"
WFS = "https://openmaps.gov.bc.ca/geo/pub/wfs"
MIN_SEP_KM = 2.0
AC_MIN, AC_MAX = 20, 300
HA = 0.404686

GROUP_LABEL = {"rice": "Rice", "forage": "Alfalfa, hay and pasture", "grain": "Corn and grain", "cotton": "Cotton",
               "vegetables": "Tomatoes, vegetables and berries", "nuts": "Almonds, walnuts and pistachios", "grapes": "Grapes",
               "citrus": "Citrus", "orchard": "Tree fruit", "canola": "Canola"}

# ------------------------------------------------------------------ California
CA_AREAS = {
    "Sacramento Valley": ["Butte", "Colusa", "Glenn", "Sutter", "Yuba", "Tehama", "Shasta", "Yolo", "Placer", "Sacramento"],
    "Delta": ["San Joaquin", "Sacramento", "Contra Costa", "Solano", "Yolo"],
    "San Joaquin Valley": ["San Joaquin", "Stanislaus", "Merced", "Madera", "Fresno", "Kings", "Tulare", "Kern"],
    "Imperial / Coachella": ["Imperial", "Riverside"],
    "Central Coast": ["Monterey", "San Benito", "Santa Cruz", "San Luis Obispo", "Santa Barbara", "Santa Clara"],
    "North Coast": ["Sonoma", "Napa", "Mendocino", "Lake", "Humboldt", "Marin"],
}
DELTA_BOX = (-121.85, 37.75, -121.30, 38.45)   # the legal Delta, roughly (lon/lat)


def in_area(area, x, y):
    in_delta = DELTA_BOX[0] <= x <= DELTA_BOX[2] and DELTA_BOX[1] <= y <= DELTA_BOX[3]
    if area == "Delta":
        return in_delta
    if area in ("Sacramento Valley", "San Joaquin Valley"):
        return not in_delta and (area != "San Joaquin Valley" or x > -120.6)
    if area == "Imperial / Coachella":
        return x > -116.45
    return True


CA_CODES = {"rice": ["R1"], "forage": ["P1"], "grain": ["F16", "G2", "G6"], "cotton": ["F1"],
            "vegetables": ["T32", "T30", "T21", "T9", "T10", "T4", "T6", "T12", "T18", "T20", "T19"],
            "nuts": ["D12", "D13", "D14"], "grapes": ["V"], "citrus": ["C"]}
NC_FORAGE = ["P1", "P3", "P6"]   # North Coast: irrigated pasture and grass hay count as forage
CA_PLAN = {
    "Sacramento Valley": {"rice": 10, "nuts": 8, "grain": 4, "forage": 3, "vegetables": 3, "grapes": 2},
    "Delta": {"grain": 5, "forage": 4, "vegetables": 3, "grapes": 4, "nuts": 2, "rice": 2},
    "San Joaquin Valley": {"nuts": 12, "grapes": 8, "citrus": 8, "forage": 7, "cotton": 7, "vegetables": 6, "grain": 5, "rice": 2},
    "Imperial / Coachella": {"forage": 6, "vegetables": 4, "citrus": 3, "grain": 3, "grapes": 2},
    "Central Coast": {"vegetables": 7, "grapes": 5, "forage": 1, "citrus": 1},
    "North Coast": {"grapes": 9, "forage": 2},
}
CDL_OK = {
    "rice": {3}, "forage": {36, 37, 176, 58, 59, 60, 224}, "cotton": {2},
    "grain": {1, 4, 21, 22, 23, 24, 25, 26, 27, 28, 29, 205, 225, 226, 228, 236, 237, 238, 240, 241, 254},
    "vegetables": {12, 14, 42, 43, 44, 47, 48, 49, 50, 53, 54, 206, 207, 208, 209, 213, 214, 216, 219, 221, 222, 227, 229, 242, 243,
                   244, 245, 246, 247, 248, 249, 250},
    "nuts": {75, 76, 204}, "grapes": {69}, "citrus": {72, 212},
}
CDL_WORD = {3: "Rice field", 36: "Alfalfa field", 37: "Hay field", 176: "Pasture", 58: "Clover field", 59: "Grass seed field",
            60: "Grass hay field", 224: "Vetch field", 2: "Cotton field", 1: "Corn field", 12: "Sweet corn field", 4: "Sorghum field",
            21: "Barley field", 22: "Durum wheat field", 23: "Wheat field", 24: "Winter wheat field", 27: "Rye field", 28: "Oat field",
            29: "Millet field", 205: "Triticale field", 225: "Wheat and corn field", 226: "Oat and corn field", 228: "Triticale and corn field",
            236: "Wheat and sorghum field", 237: "Barley and corn field", 238: "Wheat and cotton field", 54: "Tomato field",
            49: "Onion field", 206: "Carrot field", 227: "Lettuce field", 216: "Pepper field", 209: "Cantaloupe field",
            48: "Watermelon field", 213: "Honeydew field", 214: "Broccoli field", 243: "Cabbage field", 244: "Cauliflower field",
            208: "Garlic field", 219: "Leafy greens field", 221: "Strawberry field", 222: "Squash field", 229: "Pumpkin field",
            43: "Potato field", 42: "Dry bean field", 53: "Pea field", 47: "Vegetable field", 207: "Asparagus field",
            242: "Blueberry field", 245: "Celery field", 246: "Radish field", 247: "Turnip field", 248: "Eggplant field",
            249: "Gourd field", 250: "Cranberry bog", 50: "Cucumber field", 44: "Other crop field",
            75: "Almond orchard", 76: "Walnut orchard", 204: "Pistachio orchard", 69: "Vineyard", 72: "Citrus orchard",
            212: "Orange grove"}


class Http:
    def __init__(self):
        self.c = httpx.Client(headers=UA, timeout=httpx.Timeout(60.0, connect=10.0), follow_redirects=True)

    def get(self, url, params=None, tries=4):
        last = None
        for i in range(tries):
            try:
                r = self.c.get(url, params=params)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(f"{r.status_code}", request=r.request, response=r)
                r.raise_for_status()
                return r
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (i + 1))
        raise last

    def json(self, url, params=None):
        d = self.get(url, params).json()
        if isinstance(d, dict) and "error" in d:
            raise RuntimeError(str(d["error"])[:300])
        return d


def km(a, b):
    (x1, y1), (x2, y2) = a, b
    p1, p2 = math.radians(y1), math.radians(y2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(x2 - x1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def spread_pick(cands, n, taken, min_cell_km=6.0, rng=None):
    """Farthest-point sampling over cands (dicts with 'pt'), >= MIN_SEP_KM from `taken` and from each other."""
    pool = [c for c in cands if all(km(c["pt"], t) >= MIN_SEP_KM for t in taken)]
    if not pool:
        return []
    rng = rng or random.Random(0)
    out = [pool.pop(rng.randrange(len(pool)))]
    while len(out) < n and pool:
        best, bd = None, -1
        for c in pool:
            d = min(km(c["pt"], o["pt"]) for o in out)
            if d > bd:
                best, bd = c, d
        pool.remove(best)
        if bd < MIN_SEP_KM:
            break
        if bd < min_cell_km and len(out) >= n // 2:   # crowded cell: still fine, but stop shrinking below the min spacing
            pass
        out.append(best)
    return out


def interior(g):
    """An interior point of the polygon that survives the 4-decimal point id."""
    for p in [g.centroid, g.representative_point()]:
        q = Point(round(p.x, 4), round(p.y, 4))
        if g.buffer(-0.00005).contains(q):
            return q
    p = g.buffer(-0.0001).representative_point() if not g.buffer(-0.0001).is_empty else g.representative_point()
    q = Point(round(p.x, 4), round(p.y, 4))
    return q if g.contains(q) else None


def cdl_2023(h: Http, pts):
    cat = h.json(CDL + "/query", {"where": "Year=2023", "outFields": "OBJECTID,Name", "returnGeometry": "false", "f": "json"})
    oid = [f["attributes"]["OBJECTID"] for f in cat["features"] if "_56m_" not in f["attributes"]["Name"]][0]
    out = []
    for i in range(0, len(pts), 100):
        chunk = pts[i:i + 100]
        d = h.json(CDL + "/getSamples", {"geometry": json.dumps({"points": chunk, "spatialReference": {"wkid": 4326}}),
                                         "geometryType": "esriGeometryMultipoint", "returnFirstValueOnly": "true", "sampleCount": 1000,
                                         "mosaicRule": json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [oid]}), "f": "json"})
        vals = {s["locationId"]: s.get("value") for s in d.get("samples", [])}
        for k in range(len(chunk)):
            v = vals.get(k)
            try:
                out.append(int(float(str(v).split(",")[0])))
            except (TypeError, ValueError):
                out.append(None)
    return out


def place_us(h: Http, x, y):
    best = None
    for layer in (4, 5):
        try:
            d = h.json(f"{PLACES}/{layer}/query", {"geometry": f"{x - 0.3},{y - 0.25},{x + 0.3},{y + 0.25}", "geometryType": "esriGeometryEnvelope",
                                               "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "BASENAME,INTPTLAT,INTPTLON",
                                                   "returnGeometry": "false", "f": "json"})
        except Exception as e:  # noqa: BLE001
            print("   place lookup failed", layer, x, y, str(e)[:80])
            continue
        for f in d.get("features", []):
            a = f["attributes"]
            dd = km((x, y), (float(a["INTPTLON"]), float(a["INTPTLAT"])))
            if best is None or dd < best[1]:
                best = (a["BASENAME"], dd)
    return best


def place_bc(h: Http, x, y):
    for radius in (12, 25, 50):
        d = h.json(GEONAMES, {"lat": round(y, 5), "lon": round(x, 5), "radius": radius, "concise": "CITY,TOWN,VILG,UNP,MUN1,MUN2"})
        items = d.get("items", [])
        if items:
            it = min(items, key=lambda i: km((x, y), (i["longitude"], i["latitude"])))
            return it["name"], km((x, y), (it["longitude"], it["latitude"]))
    return None


def select_ca(h: Http, rng, taken):
    picked = []
    cdl_cache = {}
    for area, plan in CA_PLAN.items():
        counties = CA_AREAS[area]
        for group, n in plan.items():
            codes = NC_FORAGE if (area == "North Coast" and group == "forage") else CA_CODES[group]
            where = (f"MAIN_CROP IN ({','.join(repr(c) for c in codes)}) AND ACRES >= {AC_MIN} AND ACRES <= {AC_MAX} "
                     f"AND COUNTY IN ({','.join(repr(c) for c in counties)})")
            ids = h.json(DWR + "/query", {"where": where, "returnIdsOnly": "true", "f": "json"}).get("objectIds") or []
            rng.shuffle(ids)
            ids = ids[: max(60, 12 * n)]
            cands = []
            for i in range(0, len(ids), 100):
                d = h.json(DWR + "/query", {"objectIds": ",".join(map(str, ids[i:i + 100])), "outSR": 4326, "returnGeometry": "true",
                                            "geometryPrecision": 6, "f": "geojson",
                                            "outFields": "OBJECTID,UniqueID,ACRES,COUNTY,MAIN_CROP,REGION,HYDRO_RGN"})
                for f in d.get("features", []):
                    g = shape(f["geometry"])
                    if not g.is_valid:
                        g = g.buffer(0)
                    if g.geom_type == "MultiPolygon":
                        g = max(g.geoms, key=lambda p: p.area)
                    q = interior(g)
                    if q is None or not in_area(area, q.x, q.y):
                        continue
                    pr = f["properties"]
                    cands.append({"pt": (q.x, q.y), "props": pr})
            if cands:
                vals = cdl_2023(h, [list(c["pt"]) for c in cands])
                for c, v in zip(cands, vals):
                    c["cdl"] = v
                cands = [c for c in cands if c["cdl"] in CDL_OK[group]]
            sel = spread_pick(cands, n, taken + [p["pt"] for p in picked], rng=rng)
            for c in sel:
                pr = c["props"]
                picked.append({"region": "ca", "area": area, "crop_group": group, "pt": c["pt"], "county": pr["COUNTY"],
                               "acres": round(pr["ACRES"], 1), "crop_word": CDL_WORD.get(c["cdl"], "Field"),
                               "source": {"dwr_unique_id": pr["UniqueID"], "dwr_main_crop": pr["MAIN_CROP"], "cdl_2023": c["cdl"]}})
            print(f"CA {area:22s} {group:10s} want {n:2d} ids {len(ids):4d} cdl-ok {len(cands):4d} picked {len(sel)}")
    for p in picked:
        pl = place_us(h, *p["pt"])
        p["place"] = pl[0] if pl and pl[1] <= 30 else None
        p["name"] = f"{p['crop_word']} near {p['place']}, {p['county']} County" if p["place"] else f"{p['crop_word']} in {p['county']} County"
    return picked


# ------------------------------------------------------------------ British Columbia
BC_AREAS = {   # lon/lat boxes around the farmed valley floors
    "Okanagan": (-119.75, 49.0, -119.25, 50.35),
    "Shuswap / Salmon Valley": (-119.55, 50.40, -118.95, 50.85),
    "Thompson / Kamloops": (-120.75, 50.55, -119.85, 50.95),
    "Fraser Valley": (-122.65, 49.0, -121.45, 49.25),
    "Peace River": (-121.0, 55.6, -119.95, 56.45),
    "Creston / Kootenay": (-116.75, 49.0, -116.40, 49.25),
}
BC_PLAN = {
    "Okanagan": {"orchard": 4, "grapes": 4, "forage": 2},
    "Shuswap / Salmon Valley": {"forage": 4, "grain": 2},
    "Thompson / Kamloops": {"forage": 5, "grain": 1},
    "Fraser Valley": {"forage": 3, "vegetables": 4, "grain": 1},
    "Peace River": {"canola": 4, "grain": 3, "forage": 2},
    "Creston / Kootenay": {"grain": 2, "forage": 2, "orchard": 1},
}
ACI_GROUPS = {"forage": {122}, "grain": {132, 133, 134, 136, 137, 139, 140, 145, 146, 147, 195}, "canola": {153},
              "orchard": {188, 189}, "grapes": {190}, "vegetables": {175, 176, 177, 179, 181, 182, 183, 185}}
ACI_WORD = {122: "Hay and pasture field", 132: "Cereal field", 133: "Barley field", 134: "Grain field", 136: "Oat field", 137: "Rye field",
            139: "Triticale field", 140: "Wheat field", 145: "Winter wheat field", 146: "Spring wheat field", 147: "Corn field",
            195: "Buckwheat field", 153: "Canola field", 188: "Orchard", 189: "Fruit orchard", 190: "Vineyard", 175: "Vegetable field",
            176: "Tomato field", 177: "Potato field", 179: "Vegetable field", 181: "Berry field", 182: "Blueberry field",
            183: "Cranberry bog", 185: "Berry field"}
ALBERS = "EPSG:3005"


def aci_export(h: Http, year, box):
    import rasterio  # noqa: PLC0415
    from rasterio.io import MemoryFile  # noqa: PLC0415
    tr = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)
    xs, ys = tr.transform([box[0], box[2], box[0], box[2]], [box[1], box[1], box[3], box[3]])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, ht = int((x1 - x0) / 30), int((y1 - y0) / 30)
    r = h.get(ACI.format(year=year) + "/exportImage", {"bbox": f"{x0},{y0},{x1},{y1}", "bboxSR": 3005, "imageSR": 3005, "size": f"{w},{ht}",
                                                         "format": "tiff", "pixelType": "U8", "interpolation": "RSP_NearestNeighbor", "f": "image"})
    with MemoryFile(io.BytesIO(r.content)) as mf, mf.open() as ds:
        return ds.read(1), ds.transform, rasterio.crs.CRS.from_epsg(3005)


def wfs(h: Http, layer, cql=None, bbox=None, props=None, count=20):
    p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeName": layer, "outputFormat": "application/json",
         "srsName": "EPSG:4326", "count": count}
    if cql:
        p["CQL_FILTER"] = cql
    if bbox:
        p["bbox"] = ",".join(f"{v:.6f}" for v in bbox) + ",EPSG:4326"
    if props:
        p["propertyName"] = ",".join(props)
    return h.json(WFS, p).get("features") or []


def bc_outline(h: Http, x, y):
    """ParcelMap BC parcel at the point clipped to the ALR, the piece containing the point (shapely, lon/lat) or None."""
    fs = wfs(h, "WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW", f"INTERSECTS(SHAPE, SRID=4326;POINT({x:.6f} {y:.6f}))",
             props=["SHAPE", "FEATURE_AREA_SQM"], count=3)
    fs = [f for f in fs if f.get("geometry")]
    if not fs:
        return None, None
    f = min(fs, key=lambda f: f["properties"].get("FEATURE_AREA_SQM") or 1e12)
    pg = shape(f["geometry"])
    pg = pg if pg.is_valid else pg.buffer(0)
    alr = wfs(h, "WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS", bbox=pg.bounds, props=["GEOMETRY", "STATUS"], count=20)
    alr = [shape(a["geometry"]) for a in alr if a.get("geometry") and (a["properties"].get("STATUS") or "ALR") == "ALR"]
    if not alr:
        return None, None
    inter = pg.intersection(unary_union([a if a.is_valid else a.buffer(0) for a in alr]))
    parts = [g for g in getattr(inter, "geoms", [inter]) if g.geom_type == "Polygon"]
    part = next((g for g in parts if g.contains(Point(x, y))), None)
    return part, f["properties"]


def regional_district(h: Http, x, y):
    fs = wfs(h, "WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_REGIONAL_DISTRICTS_SP", f"INTERSECTS(SHAPE, SRID=4326;POINT({x:.6f} {y:.6f}))",
             props=["ADMIN_AREA_NAME"], count=2)
    return fs[0]["properties"]["ADMIN_AREA_NAME"] if fs else None


def select_bc(h: Http, rng, taken):
    from rasterio.features import geometry_mask  # noqa: PLC0415
    from scipy import ndimage  # noqa: PLC0415
    to_alb = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True).transform
    to_ll = Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True)
    picked = []
    for area, plan in BC_PLAN.items():
        box = BC_AREAS[area]
        a25, tr, _ = aci_export(h, 2025, box)
        a24, tr24, _ = aci_export(h, 2024, box)
        if a24.shape != a25.shape:
            a24 = np.zeros_like(a25)
        print(f"BC {area}: ACI 2025 {a25.shape}, classes {np.unique(a25).size}")
        for group, n in plan.items():
            cls = ACI_GROUPS[group]
            # same group in 2024, or 2024 not crop-typed there (AAFC mapped some areas only as 120 Agriculture, e.g. Creston 2024)
            m = np.isin(a25, list(cls)) & (np.isin(a24, list(cls)) | np.isin(a24, [0, 120]))
            lab, k = ndimage.label(m)
            if not k:
                print(f"BC {area:24s} {group:10s} no patches")
                continue
            sizes = ndimage.sum(m, lab, index=np.arange(1, k + 1))
            keep = [i + 1 for i, s in enumerate(sizes) if s * 0.09 >= 4]   # >= 4 ha of the crop both years
            rng.shuffle(keep)
            objs = ndimage.find_objects(lab)
            cands = []
            for lid in keep[:400]:
                sl = objs[lid - 1]
                rr, cc = np.nonzero(lab[sl] == lid)
                rr, cc = rr + sl[0].start, cc + sl[1].start
                cy, cx = rr.mean(), cc.mean()
                j = int(np.argmin((rr - cy) ** 2 + (cc - cx) ** 2))
                xa, ya = tr * (cc[j] + 0.5, rr[j] + 0.5)
                lon, lat = to_ll.transform(xa, ya)
                cands.append({"pt": (round(lon, 4), round(lat, 4)), "px": int(sizes[lid - 1])})
            order = spread_pick(cands, min(len(cands), 6 * n), taken + [p["pt"] for p in picked], rng=rng)
            sel = []
            for c in order:
                if len(sel) >= n:
                    break
                x, y = c["pt"]
                try:
                    part, _pp = bc_outline(h, x, y)
                except Exception as e:  # noqa: BLE001
                    print("   parcel lookup failed", e)
                    continue
                if part is None:
                    continue
                pa = transform(to_alb, part)
                ac = pa.area / 1e4 / HA
                if not AC_MIN <= ac <= AC_MAX:
                    continue
                mk = ~geometry_mask([pa.__geo_interface__], out_shape=a25.shape, transform=tr)
                if mk.sum() < 5:
                    continue
                vals = a25[mk]
                share = float(np.isin(vals, list(cls)).mean())
                if share < 0.5:
                    continue
                if any(km(c["pt"], s["pt"]) < MIN_SEP_KM for s in sel):
                    continue
                codes, cnt = np.unique(vals[np.isin(vals, list(cls))], return_counts=True)
                top = int(codes[np.argmax(cnt)])
                sel.append({**c, "acres": round(ac, 1), "share": round(share, 2), "aci": top})
            for c in sel:
                rd = regional_district(h, *c["pt"])
                picked.append({"region": "bc", "area": area, "crop_group": group, "pt": c["pt"], "county": rd, "acres": c["acres"],
                               "crop_word": ACI_WORD.get(c["aci"], "Field"),
                               "source": {"aci_2025_majority": c["aci"], "aci_2025_group_share": c["share"]}})
            print(f"BC {area:24s} {group:10s} want {n} patches {len(keep):4d} picked {len(sel)}")
    for p in picked:
        pl = place_bc(h, *p["pt"])
        p["place"] = pl[0] if pl and pl[1] <= 40 else None
        p["name"] = f"{p['crop_word']} near {p['place']}, {p['county']}" if p["place"] else f"{p['crop_word']} in {p['county']}"
    return picked


def farm_name(p):
    """'Almond orchard near Kerman, Fresno County' / 'Canola field near Montney, Peace River Regional District'."""
    place = re.sub(r"\s*\(.*?\)", "", p.get("place") or "").strip()
    where = f"{p['county']} County" if p["region"] == "ca" else p["county"]
    return f"{p['crop_word']} near {place}, {where}" if place else f"{p['crop_word']} in {where}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["ca", "bc"])
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    h = Http()
    prev = json.loads(OUT.read_text())["fields"] if OUT.exists() else []
    keep = [p for p in prev if a.only and p["region"] != a.only]
    taken = [tuple(p["pt"]) for p in keep]
    new = []
    if a.only in (None, "ca"):
        new += select_ca(h, rng, taken)
    if a.only in (None, "bc"):
        new += select_bc(h, rng, taken + [p["pt"] for p in new])
    fields = keep + new
    for p in fields:
        p["pt"] = [round(p["pt"][0], 4), round(p["pt"][1], 4)]
        p["id"] = point_id(p["pt"][1], p["pt"][0])
        p["crop_group_label"] = GROUP_LABEL[p["crop_group"]]
        p["name"] = farm_name(p)
    ids = [p["id"] for p in fields]
    assert len(ids) == len(set(ids)), "duplicate ids"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rule": __doc__.split("Writes")[0].strip(), "seed": a.seed, "min_separation_km": MIN_SEP_KM,
                               "acres": [AC_MIN, AC_MAX], "fields": fields}, indent=1) + "\n")
    from collections import Counter
    print(len(fields), "fields", Counter(p["region"] for p in fields), Counter((p["region"], p["crop_group"]) for p in fields))


if __name__ == "__main__":
    main()
