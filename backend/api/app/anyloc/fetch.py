"""Upstream fetchers for "analyse any location" (all async httpx, no key, hard timeout on every call).

Each function returns plain dicts/lists and raises on failure; the caller (build.py) turns a failure into a section
status. Same public services the registry pipeline uses:

- NASA POWER daily point (CSV, 1990 to the latest day), cached per 0.5 x 0.625 deg cell (the POWER grid);
- USDA NRCS SSURGO via Soil Data Access (same SQL as backend/regional/src/fetch_ssurgo.py);
- USDA NASS Cropland Data Layer, CroplandCROS ImageServer `CDL_WM` (backend/field/fieldshift_field/cdl.py's service),
  sampled at up to 9 points inside the field with `getSamples` (5 rasters per request = the service's mosaic limit);
- DWR / Land IQ Statewide Crop Mapping 2023 field outline containing the point (backend/field select_fields.py layer);
- county and state from the FCC Census Area API (2020 blocks);
- water district, Bulletin 118 subbasin, SGMA priority, GSA, GSP, adjudicated area: the DWR layers of
  backend/fields/water_sources.py, plus the State Water Board probation list (cached a day).
"""
from __future__ import annotations

import asyncio
import io
import json
import math
import re

import httpx

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_PARAMS = "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR"
SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
CDL = "https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer"
DWR_2023 = ("https://utility.arcgis.com/usrsvcs/servers/d94e891e00364e49a2ed9e9e2e27837d/rest/services/"
            "Planning/i15_Crop_Mapping_2023/MapServer/0")
FCC = "https://geo.fcc.gov/api/census/area"
UA = {"User-Agent": "CropLytics/0.1 (NASA Space Apps crop-rotation planner; any-location analysis)"}
TIMEOUT = httpx.Timeout(12.0, connect=5.0)
MAX_BYTES = 8_000_000   # no upstream answer we read is near this; a bigger one is refused (memory guard)


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=UA, timeout=TIMEOUT, follow_redirects=True,
                             limits=httpx.Limits(max_connections=12, max_keepalive_connections=6))


async def _get(c: httpx.AsyncClient, url: str, params: dict | None = None, timeout: float | None = None) -> bytes:
    async with c.stream("GET", url, params=params, timeout=timeout or TIMEOUT) as r:
        r.raise_for_status()
        buf = bytearray()
        async for chunk in r.aiter_bytes():
            buf += chunk
            if len(buf) > MAX_BYTES:
                raise RuntimeError(f"upstream answer over {MAX_BYTES} bytes: {url}")
        return bytes(buf)


async def _json(c, url, params=None, timeout=None):
    d = json.loads(await _get(c, url, params, timeout))
    if isinstance(d, dict) and "error" in d:
        raise RuntimeError(str(d["error"])[:200])
    return d


# ------------------------------------------------------------------ POWER
def power_cell(lon: float, lat: float):
    """MERRA-2 cell (0.5 deg lat x 0.625 deg lon) containing the point: (row, col, centre lon, centre lat, footprint)."""
    row, col = round((lat + 90) / 0.5), round((lon + 180) / 0.625)
    clat, clon = row * 0.5 - 90, col * 0.625 - 180
    ring = [[clon - .3125, clat - .25], [clon + .3125, clat - .25], [clon + .3125, clat + .25], [clon - .3125, clat + .25],
            [clon - .3125, clat - .25]]
    return int(row), int(col), clon, clat, {"type": "Polygon", "coordinates": [ring]}


async def power_daily(c, lon: float, lat: float, end: str):
    """POWER daily point CSV 1990-01-01..end for the cell centre. Returns (DataFrame indexed by date, meta)."""
    import pandas as pd  # noqa: PLC0415
    q = dict(parameters=POWER_PARAMS, community="AG", longitude=round(lon, 4), latitude=round(lat, 4),
             start="19900101", end=end, format="CSV")
    raw = (await _get(c, POWER_URL, q, timeout=httpx.Timeout(25.0, connect=5.0))).decode("utf-8", "replace")
    head, _, body = raw.partition("-END HEADER-")
    elev = re.search(r"=\s*([-\d.]+)\s*meters", head)
    df = pd.read_csv(io.StringIO(body.strip()), dtype="float64")
    del body, raw
    df["date"] = pd.to_datetime(df["YEAR"].astype(int).astype(str) + df["DOY"].astype(int).astype(str).str.zfill(3), format="%Y%j")
    df = df.drop(columns=["YEAR", "DOY"]).set_index("date").replace(-999.0, float("nan")).astype("float32")
    df = df[df[["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"]].notna().any(axis=1)]   # trailing days not published yet
    url = str(httpx.URL(POWER_URL, params={**q, "format": "JSON"}))
    meta = {"url": url, "elevation_m": float(elev.group(1)) if elev else None, "rows": int(len(df)),
            "date_min": str(df.index.min().date()), "date_max": str(df.index.max().date())}
    return df, meta


# ------------------------------------------------------------------ county (FCC census area)
async def county(c, lon, lat):
    d = await _json(c, FCC, {"lat": lat, "lon": lon, "censusYear": "2020", "format": "json"}, timeout=httpx.Timeout(8.0, connect=4.0))
    r = (d.get("results") or [None])[0]
    if not r:
        return None
    return {"state_fips": r["state_fips"], "state_code": r["state_code"], "state_name": r["state_name"],
            "county_fips": r["county_fips"][2:], "county_fips5": r["county_fips"],
            "county_name": r["county_name"].removesuffix(" County").removesuffix(" Parish")}


# ------------------------------------------------------------------ DWR / Land IQ field outline
async def dwr_field(c, lon, lat):
    """The DWR/Land IQ 2023 crop-mapping polygon containing the point (GeoJSON feature) or None."""
    d = await _json(c, DWR_2023 + "/query", {
        "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326, "outSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "returnGeometry": "true", "f": "geojson",
        "outFields": "UniqueID,ACRES,COUNTY,CLASS1,SUBCLASS1,CROPTYP1,CROPTYP2,MAIN_CROP,MAIN_CROP_DATE"})
    fs = d.get("features") or []
    return fs[0] if fs else None


# ------------------------------------------------------------------ geometry helpers (no shapely)
def rings_of(geom: dict) -> list[list]:
    """Outer rings of a Polygon / MultiPolygon (holes ignored)."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [p[0] for p in geom["coordinates"]]


def in_ring(lon, lat, ring) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-300) + x1:
            inside = not inside
    return inside


def ring_area_m2(ring) -> float:
    """Shoelace area on a local equirectangular projection (field-sized polygons: error well under 0.1 %)."""
    lat0 = sum(p[1] for p in ring) / len(ring)
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110574
    xy = [(p[0] * kx, p[1] * ky) for p in ring]
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(xy, xy[1:]))) / 2


def ring_centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        f = x1 * y2 - x2 * y1
        a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f
    if abs(a) < 1e-18:
        return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    return cx / (3 * a), cy / (3 * a)


def square(lon, lat, half_m=100.0):
    dlat = half_m / 110574
    dlon = half_m / (111320 * math.cos(math.radians(lat)))
    ring = [[lon - dlon, lat - dlat], [lon + dlon, lat - dlat], [lon + dlon, lat + dlat], [lon - dlon, lat + dlat], [lon - dlon, lat - dlat]]
    return {"type": "Polygon", "coordinates": [ring]}


def wkt(ring, max_pts=200) -> str:
    step = max(1, math.ceil(len(ring) / max_pts))
    pts = ring[::step]
    if pts[-1] != ring[-1]:
        pts.append(ring[-1])
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return "POLYGON((" + ",".join(f"{x:.6f} {y:.6f}" for x, y in pts) + "))"


def sample_points(ring, lon, lat, n=3):
    """Up to n x n grid points inside the ring (the tapped point first), for CDL sampling."""
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    out = [[lon, lat]]
    for i in range(n):
        for j in range(n):
            x = min(xs) + (i + 0.5) * (max(xs) - min(xs)) / n
            y = min(ys) + (j + 0.5) * (max(ys) - min(ys)) / n
            if in_ring(x, y, ring):
                out.append([x, y])
    return out[:10]


# ------------------------------------------------------------------ CDL
async def cdl_catalog(c):
    d = await _json(c, CDL + "/query", {"where": "1=1", "outFields": "OBJECTID,Name,Year", "returnGeometry": "false", "f": "json"})
    return {int(f["attributes"]["Year"]): int(f["attributes"]["OBJECTID"]) for f in d["features"]
            if "_56m_" not in f["attributes"]["Name"] and int(f["attributes"]["Year"]) >= 2008}


async def cdl_legend(c):
    d = await _json(c, CDL + "/rasterAttributeTable", {"f": "json"})
    return {str(int(f["attributes"]["Value"])): f["attributes"]["Class_Names"] for f in d["features"] if f["attributes"].get("Class_Names")}


async def cdl_history(c, pts: list, catalog: dict) -> dict:
    """{year: {"counts": {code: n}, "n": samples}} at the given points, every catalog year (5 rasters per request)."""
    years = sorted(catalog)
    chunks = [years[i:i + 5] for i in range(0, len(years), 5)]
    geom = json.dumps({"points": pts, "spatialReference": {"wkid": 4326}})

    async def one(ys):
        mr = {"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [catalog[y] for y in ys]}
        d = await _json(c, CDL + "/getSamples", {"geometry": geom, "geometryType": "esriGeometryMultipoint",
                                                  "returnFirstValueOnly": "false", "mosaicRule": json.dumps(mr),
                                                  "outFields": "Year", "sampleCount": 1000, "f": "json"})
        return d.get("samples", [])

    out: dict[int, dict] = {}
    for samples in await asyncio.gather(*(one(ys) for ys in chunks)):
        for s in samples:
            y = int((s.get("attributes") or {}).get("Year", 0))
            v = s.get("value")
            if not y or v in (None, "NoData", ""):
                continue
            code = str(int(float(str(v).split(",")[0])))
            e = out.setdefault(y, {"counts": {}, "n": 0})
            e["counts"][code] = e["counts"].get(code, 0) + 1
            e["n"] += 1
    return out


# ------------------------------------------------------------------ SSURGO (Soil Data Access)
async def _sda(c, sql):
    r = await c.post(SDA, json={"format": "JSON+COLUMNNAME", "query": sql}, timeout=httpx.Timeout(15.0, connect=5.0))
    r.raise_for_status()
    if len(r.content) > MAX_BYTES:
        raise RuntimeError("SDA answer too large")
    t = r.json().get("Table", [])
    if not t:
        return []
    return [dict(zip(t[0], row)) for row in t[1:]]


def _f(x):
    return None if x in (None, "") else float(x)


def texture_class(sand, silt, clay):
    """USDA texture triangle (percent); same rule as backend/regional/src/fetch_ssurgo.py."""
    if clay >= 40 and sand <= 45 and silt < 40: return "clay"  # noqa: E701
    if clay >= 40 and silt >= 40: return "silty clay"  # noqa: E701
    if clay >= 35 and sand > 45: return "sandy clay"  # noqa: E701
    if 27 <= clay < 40 and sand <= 20: return "silty clay loam"  # noqa: E701
    if 27 <= clay < 40 and sand <= 45: return "clay loam"  # noqa: E701
    if 20 <= clay < 35 and silt < 28 and sand > 45: return "sandy clay loam"  # noqa: E701
    if silt >= 80 and clay < 12: return "silt"  # noqa: E701
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12): return "silt loam"  # noqa: E701
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52: return "loam"  # noqa: E701
    if silt + 1.5 * clay < 15: return "sand"  # noqa: E701
    if silt + 2 * clay < 30: return "loamy sand"  # noqa: E701
    return "sandy loam"


def _wavg(h, key, top=0, bot=100):
    num = den = 0.0
    for r in h:
        v, a, b = _f(r[key]), _f(r["hzdept_r"]), _f(r["hzdepb_r"])
        if v is None or a is None or b is None:
            continue
        t = max(0.0, min(b, bot) - max(a, top))
        num += v * t; den += t
    return num / den if den else None


async def ssurgo(c, ring, wkt_str=None) -> dict | None:
    """SSURGO summary over the footprint (0-100 cm, component- and area-weighted), the registry's soil.json shape.
    None where SSURGO has no map unit (outside the US survey area)."""
    w = wkt_str or wkt(ring)
    areas = await _sda(c, f"SELECT mukey, mupolygongeo.STIntersection(geometry::STGeomFromText('{w}',4326)).STArea() AS a "
                          f"FROM mupolygon WHERE mukey IN (SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{w}'))")
    share: dict[str, float] = {}
    for r in areas:
        share[r["mukey"]] = share.get(r["mukey"], 0) + float(r["a"] or 0)
    if not share:
        return None
    tot = sum(share.values())
    share = {k: (v / tot if tot > 0 else 1 / len(share)) for k, v in share.items()}
    mukeys = sorted(share, key=lambda k: -share[k])[:12]
    mk = ",".join(f"'{int(m)}'" for m in mukeys)
    comps, hz = await asyncio.gather(
        _sda(c, f"SELECT mu.mukey, mu.muname, c.cokey, c.compname, c.comppct_r, c.drainagecl, c.hydgrp, c.taxorder FROM mapunit mu "
                f"JOIN component c ON c.mukey=mu.mukey WHERE mu.mukey IN ({mk}) ORDER BY mu.mukey, c.comppct_r DESC"),
        _sda(c, f"SELECT c.cokey, h.hzdept_r, h.hzdepb_r, h.awc_l, h.awc_r, h.awc_h, h.om_l, h.om_r, h.om_h, h.sandtotal_r, "
                f"h.silttotal_r, h.claytotal_r, h.ec_r FROM chorizon h JOIN component c ON c.cokey=h.cokey "
                f"WHERE c.mukey IN ({mk}) ORDER BY c.cokey, h.hzdept_r"))
    if not comps:
        return None
    by_co: dict[str, list] = {}
    for r in hz:
        by_co.setdefault(r["cokey"], []).append(r)
    keys = [("awc_r", "awc"), ("awc_l", "awc_l"), ("awc_h", "awc_h"), ("om_r", "om"), ("om_l", "om_l"), ("om_h", "om_h"),
            ("sandtotal_r", "sand"), ("silttotal_r", "silt"), ("claytotal_r", "clay"), ("ec_r", "ec")]
    prof = {co: {out: _wavg(h, k) for k, out in keys} for co, h in by_co.items()}

    def area_mean(key):
        num = den = 0.0
        for m in mukeys:
            cn = cd = 0.0
            for cc in comps:
                if cc["mukey"] != m or cc["cokey"] not in prof or prof[cc["cokey"]][key] is None:
                    continue
                wgt = float(cc["comppct_r"] or 0); cn += prof[cc["cokey"]][key] * wgt; cd += wgt
            if cd:
                num += cn / cd * share[m]; den += share[m]
        return num / den if den else None

    dom = mukeys[0]
    dc = max((cc for cc in comps if cc["mukey"] == dom), key=lambda cc: float(cc["comppct_r"] or 0), default=comps[0])
    rnd = lambda v, k=1, s=1: None if v is None else round(v * s, k)  # noqa: E731
    sand, silt, clay = area_mean("sand"), area_mean("silt"), area_mean("clay")
    return {
        "mukey": str(dom), "muname": dc["muname"], "drainage_class": dc["drainagecl"], "hydrologic_group": dc["hydgrp"],
        "dominant_component": {"compname": dc["compname"], "comppct_r": dc["comppct_r"], "taxorder": dc["taxorder"]},
        "awc": [rnd(area_mean(k), 1, 1000) for k in ("awc", "awc_l", "awc_h")],
        "om": [rnd(area_mean(k), 2) for k in ("om", "om_l", "om_h")],
        "texture_class": texture_class(sand, silt, clay) if None not in (sand, silt, clay) else None,
        "texture_detail": {"sand_pct": rnd(sand), "silt_pct": rnd(silt), "clay_pct": rnd(clay),
                           "method": "USDA triangle on 0-100 cm weighted sand/silt/clay"},
        "ec_ds_per_m": rnd(area_mean("ec"), 2),
        "map_units": [{"mukey": str(m), "muname": next((cc["muname"] for cc in comps if cc["mukey"] == m), None),
                       "area_share": round(share[m], 3)} for m in mukeys],
    }


# ------------------------------------------------------------------ DWR water layers (backend/fields/water_sources.py)
async def _at_point(c, url, lon, lat, fields="*"):
    d = await _json(c, url + "/query", {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
                                        "spatialRel": "esriSpatialRelIntersects", "outFields": fields, "returnGeometry": "false", "f": "json"},
                    timeout=httpx.Timeout(6.0, connect=4.0))
    return [f["attributes"] for f in d.get("features", [])]


def parse_swrcb(html: str) -> dict:
    """State Water Board basin page -> {'probationary': [...], 'under_evaluation': [...], 'returned_to_dwr': [...]}
    (same text markers as backend/fields/water_sources.py swrcb_status)."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    t = re.sub(r"<[^>]+>", " | ", t)
    t = re.sub(r"\s+", " ", t)

    def names(start, stop):
        i = t.find(start)
        if i < 0:
            return None
        j = t.find(stop, i + len(start))
        return sorted({m.strip() for m in re.findall(r"([A-Z][A-Za-z\-\. ]+? Subbasin)", t[i + len(start): j if j > 0 else i + 600])})

    return {"probationary": names("designated the following basins probationary:", "Basins Returned"),
            "under_evaluation": names("for a potential probationary designation:", "Basins Designated"),
            "returned_to_dwr": names("Basins Returned to Department of Water Resources", "Basins Under")}


async def swrcb(c, url):
    return parse_swrcb((await _get(c, url, timeout=httpx.Timeout(8.0, connect=4.0))).decode("utf-8", "ignore"))


async def water(c, lon, lat, layers: dict, ag_words: tuple, today: str) -> dict:
    """The registry's `water` lookup (water_sources.lookup) at a point, every layer in parallel; a failed layer is null
    with its error, never guessed. The State Water Board status is added by the caller (cached list)."""
    names = ("districts", "b118", "priority", "cod", "gsa", "gsp", "adjudicated")
    flds = {"districts": "AGENCYNAME", "b118": "Basin_Subbasin_Number,Basin_Subbasin_Name,Basin_Name", "priority": "*",
            "cod": "Basin_Subbasin_Number,critical_flag", "gsa": "GSA_ID,GSA_Name,GSA_URL,Exclusive", "gsp": "GSP_ID,Status", "adjudicated": "NAME"}
    res = await asyncio.gather(*(_at_point(c, layers[n], lon, lat, flds[n]) for n in names), return_exceptions=True)
    got = dict(zip(names, res))
    w = {"looked_up": today, "point": [lon, lat], "method": "layers queried at the tapped point", "errors": {}}
    src = lambda title, k: {"title": title, "url": layers[k], "accessed": today, "verified": True}  # noqa: E731

    def ok(k):
        if isinstance(got[k], Exception):
            w["errors"][k] = str(got[k])[:200] or type(got[k]).__name__
            return None
        return got[k]
    ds = ok("districts")
    if ds is not None:
        nm = sorted({d["AGENCYNAME"].strip() for d in ds if d.get("AGENCYNAME")}, key=lambda n: (not any(k in n.lower() for k in ag_words), n))
        w["district"], w["other_agencies"] = (nm[0] if nm else None), nm[1:]
        w["district_source"] = src("DWR i03 Water Districts", "districts")
    else:
        w["district"], w["other_agencies"] = None, []
    b = ok("b118")
    w["subbasin"] = ({"number": b[0]["Basin_Subbasin_Number"], "name": b[0]["Basin_Subbasin_Name"], "basin": b[0]["Basin_Name"]} if b else None)
    if b is not None:
        w["subbasin_source"] = src("DWR Bulletin 118 groundwater basins (i08_B118_CA_GroundwaterBasins)", "b118")
    pr = ok("priority")
    w["sgma_priority"] = next((v for r in (pr or []) for k, v in r.items() if k.endswith(".Priority") or k == "Priority"), None)
    if pr is not None:
        w["sgma_priority_source"] = src("DWR SGMA 2019 Basin Prioritization", "priority")
    cod = ok("cod")
    w["critically_overdrafted"] = (None if cod is None else bool(cod) and any(
        str(x.get("critical_flag", "")).strip().lower() in ("y", "yes", "1", "true") or x.get("critical_flag") is None for x in cod))
    g = ok("gsa")
    w["gsa"] = None if g is None else [{"name": (x.get("GSA_Name") or "").strip(), "id": x.get("GSA_ID"),
                                        "url": (x.get("GSA_URL") or "").strip() or None, "exclusive": x.get("Exclusive")} for x in g]
    if g is not None:
        w["gsa_source"] = src("DWR SGMA Portal, Groundwater Sustainability Agencies (i03)", "gsa")
    a = ok("adjudicated")
    w["adjudicated_area"] = a[0]["NAME"] if a else None
    gp = ok("gsp")   # GSP plan area at the point (a where= query on the subbasin number takes 15 s+ on this server)
    w["gsp"] = None if gp is None else [{"gsp_id": x.get("GSP_ID"), "dwr_status": x.get("Status")} for x in gp]
    if gp is not None:
        w["gsp_source"] = src("DWR SGMA Portal, Groundwater Sustainability Plan areas (i03)", "gsp")
    if not w["errors"]:
        del w["errors"]
    return w
