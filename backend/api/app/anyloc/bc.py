"""British Columbia tier 1 for a tapped point, plus land status and Nation tools (BC reserves and US tribal land).

All public, no key, async httpx with hard timeouts (same rules as fetch.py):

- regional district, Indian reserve, ParcelMap BC parcel, Agricultural Land Reserve (ALR) and the Salmon River (Shuswap)
  named watershed from BC's open WFS (openmaps.gov.bc.ca; CQL point queries, the ALR by a 2 m box because its CQL
  INTERSECTS answers nothing);
- ECCC climate stations near the point and the nearest active station's monthly climate (MSC GeoMet OGC API,
  api.weather.gc.ca collections climate-stations and climate-monthly);
- AAFC Annual Crop Inventory 2011-2025 at up to 10 points in the field (one ImageServer per year, `getSamples`);
- AAFC Soil Landscapes of Canada v3.2 from slc_bc.json.gz (built once by backend/catalog/slc_bc.py; no download here);
- US tribal land from the Census TIGERweb AIANNH service (federal reservations, off-reservation trust land).

The parcel outline is kept as geometry only: PID, PIN, plan number and owner details are never copied.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import gzip
import json
import math
from functools import lru_cache
import os
import sys
from pathlib import Path

import httpx

from . import fetch as F

ROOT = Path(os.environ.get("FIELDSHIFT_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "backend" / "bc"))
try:
    from nations import nation  # noqa: E402  (backend/bc/nations.py, stdlib only; copied into the Docker image)
except ImportError:  # pragma: no cover
    def nation(band):
        return band

WFS = "https://openmaps.gov.bc.ca/geo/pub/wfs"
L_RESERVE = "WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP"
L_PARCEL = "WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW"
L_ALR = "WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS"
L_RD = "WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_REGIONAL_DISTRICTS_SP"
L_FWA = "WHSE_BASEMAPPING.FWA_NAMED_WATERSHEDS_POLY"
SALMON_FWA = "100-190442-999098-995997-990301"   # Salmon River -> Shuswap Lake (FWA watershed code prefix)
ECCC = "https://api.weather.gc.ca/collections"
ACI = "https://agriculture.canada.ca/imagery-images/rest/services/annual_crop_inventory/{year}/ImageServer"
ACI_YEARS = list(range(2011, 2026))
ACI_SPEC = ("https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/supportdocument_documentdesupport/en/"
            "ISO%2019131_AAFC_Annual_Crop_Inventory_Data_Product_Specifications.pdf")
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/AIANNHA/MapServer"
TIGER_LAYERS = {2: "Federal American Indian Reservation", 3: "Off-Reservation Trust Land"}
BC_BOX = (-139.1, 48.2, -114.0, 60.0)
CAN_BOX = (-141.0, 41.6, -52.0, 62.0)   # all of Canada's farmland; the FCC census lookup (no US block) tells Canada from the US
SLC_REST = Path(__file__).with_name("slc_can.json.gz")   # AB SK MB ON QC (backend/catalog/slc_bc.py --rest)
GEONAMES = "https://geogratis.gc.ca/services/geoname/en/geonames.json"
SLC_FILE = Path(__file__).with_name("slc_bc.json.gz")
TO = httpx.Timeout(10.0, connect=5.0)
# ACI class names (same table as backend/bc/aci.py, from the ACI Data Product Specification, section 4)
ACI_LEGEND = {
    0: "Not mapped (no data)", 10: "Cloud", 20: "Water", 30: "Exposed Land / Barren", 34: "Urban / Developed", 35: "Greenhouses", 50: "Shrubland",
    60: "Forest Fire / Burnt Area", 80: "Wetland", 85: "Peatland", 110: "Grassland", 120: "Agriculture (undifferentiated)",
    121: "Cropland", 122: "Pasture / Forages", 130: "Too Wet to be Seeded", 131: "Fallow", 132: "Cereals", 133: "Barley",
    134: "Other Grains", 135: "Millet", 136: "Oats", 137: "Rye", 138: "Spelt", 139: "Triticale", 140: "Wheat",
    141: "Switchgrass", 142: "Sorghum", 143: "Quinoa", 145: "Winter Wheat", 146: "Spring Wheat", 147: "Corn",
    148: "Tobacco", 149: "Ginseng", 150: "Oilseeds", 151: "Borage", 152: "Camelina", 153: "Canola / Rapeseed",
    154: "Flaxseed", 155: "Mustard", 156: "Safflower", 157: "Sunflower", 158: "Soybeans", 159: "Other Oilseeds",
    160: "Pulses", 161: "Other Pulses", 162: "Peas", 163: "Chickpeas", 167: "Beans", 168: "Fababeans", 174: "Lentils",
    175: "Vegetables", 176: "Tomatoes", 177: "Potatoes", 178: "Sugarbeets", 179: "Other Vegetables", 180: "Fruits",
    181: "Berries", 182: "Blueberry", 183: "Cranberry", 185: "Other Berries", 188: "Orchards", 189: "Other Fruits",
    190: "Vineyards", 191: "Hops", 192: "Sod", 193: "Herbs", 194: "Nursery", 195: "Buckwheat", 196: "Canaryseed",
    197: "Hemp", 198: "Vetch", 199: "Other Crops", 200: "Forest (undifferentiated)", 210: "Coniferous",
    220: "Broadleaf", 230: "Mixedwood",
}
FORAGE = "122"
NOT_CROP = {"0", "10", "20", "30", "34", "50", "60", "80", "85", "110", "200", "210", "220", "230"}


def in_bc_box(lon, lat) -> bool:
    return BC_BOX[0] <= lon <= BC_BOX[2] and BC_BOX[1] <= lat <= BC_BOX[3]


PROVINCES = {"10": ("NL", "Newfoundland and Labrador"), "11": ("PE", "Prince Edward Island"), "12": ("NS", "Nova Scotia"),
             "13": ("NB", "New Brunswick"), "24": ("QC", "Quebec"), "35": ("ON", "Ontario"), "46": ("MB", "Manitoba"),
             "47": ("SK", "Saskatchewan"), "48": ("AB", "Alberta"), "59": ("BC", "British Columbia"), "60": ("YT", "Yukon"),
             "61": ("NT", "Northwest Territories"), "62": ("NU", "Nunavut")}


def in_canada_box(lon, lat) -> bool:
    return CAN_BOX[0] <= lon <= CAN_BOX[2] and CAN_BOX[1] <= lat <= CAN_BOX[3]


def km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


# ------------------------------------------------------------------ BC WFS
async def wfs(c, layer, cql=None, bbox=None, props=None, count=10, geom=True, timeout=None):
    p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeName": layer, "outputFormat": "application/json",
         "srsName": "EPSG:4326", "count": count}
    if cql:
        p["CQL_FILTER"] = cql
    if bbox:
        p["bbox"] = ",".join(f"{v:.6f}" for v in bbox) + ",EPSG:4326"
    if props:
        p["propertyName"] = ",".join(props)
    d = await F._json(c, WFS, p, timeout or TO)
    return d.get("features") or []


def _pt(geom_col, lon, lat):
    return f"INTERSECTS({geom_col}, SRID=4326;POINT({lon:.6f} {lat:.6f}))"


async def regional_district(c, lon, lat) -> str | None:
    fs = await wfs(c, L_RD, _pt("SHAPE", lon, lat), props=["ADMIN_AREA_NAME"], count=2)
    return fs[0]["properties"]["ADMIN_AREA_NAME"] if fs else None


async def reserve_at(c, lon, lat) -> dict | None:
    fs = await wfs(c, L_RESERVE, _pt("GEOMETRY", lon, lat), props=["ENGLISH_NAME", "BAND_NAME", "BAND_NUMBER"], count=2)
    if not fs:
        return None
    p = fs[0]["properties"]
    return {"name": p.get("ENGLISH_NAME"), "band": p.get("BAND_NAME"), "band_number": str(p.get("BAND_NUMBER") or "")}


async def parcel_at(c, lon, lat) -> dict | None:
    """The ParcelMap BC parcel containing the point: geometry + class, owner type and area only (no PID, PIN, plan or name)."""
    fs = await wfs(c, L_PARCEL, _pt("SHAPE", lon, lat), count=3,
                   props=["SHAPE", "PARCEL_CLASS", "OWNER_TYPE", "PARCEL_STATUS", "MUNICIPALITY", "REGIONAL_DISTRICT", "FEATURE_AREA_SQM"])
    fs = [f for f in fs if f.get("geometry")]
    if not fs:
        return None
    f = min(fs, key=lambda f: f["properties"].get("FEATURE_AREA_SQM") or 1e12)
    p = f["properties"]
    return {"geometry": f["geometry"], "parcel_class": p.get("PARCEL_CLASS"), "owner_type": p.get("OWNER_TYPE"),
            "status": p.get("PARCEL_STATUS"), "municipality": p.get("MUNICIPALITY"), "regional_district": p.get("REGIONAL_DISTRICT"),
            "area_ha": round((p.get("FEATURE_AREA_SQM") or 0) / 1e4, 2)}


def _box(lon, lat, m):
    dlat, dlon = m / 110574, m / (111320 * math.cos(math.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


async def in_alr(c, lon, lat) -> bool:
    fs = await wfs(c, L_ALR, bbox=_box(lon, lat, 1), props=["ALR_POLY_ID", "STATUS"], count=2)
    return any((f["properties"].get("STATUS") or "ALR") == "ALR" for f in fs)


async def alr_clip(c, parcel_geom: dict, lon, lat):
    """(outline geometry, share of the parcel inside the ALR). The ALR polygons whose geometry meets the parcel's box are
    fetched whole (a few hundred kB) and intersected with the parcel; the part containing the point is kept."""
    from shapely.geometry import Point, mapping, shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    pg = shape(parcel_geom)
    if not pg.is_valid:
        pg = pg.buffer(0)
    fs = await wfs(c, L_ALR, bbox=pg.bounds, props=["GEOMETRY", "STATUS"], count=20, timeout=httpx.Timeout(15.0, connect=5.0))
    alr = [shape(f["geometry"]) for f in fs if f.get("geometry") and (f["properties"].get("STATUS") or "ALR") == "ALR"]
    if not alr:
        return None, 0.0
    a = unary_union([g if g.is_valid else g.buffer(0) for g in alr])
    inter = pg.intersection(a)
    share = inter.area / pg.area if pg.area else 0.0
    parts = [g for g in getattr(inter, "geoms", [inter]) if g.geom_type == "Polygon" and not g.is_empty]
    if not parts:
        return None, share
    pt = Point(lon, lat)
    part = next((g for g in parts if g.contains(pt)), max(parts, key=lambda g: g.area))
    return mapping(part.simplify(0.00002)), share


async def salmon_watershed(c, lon, lat) -> bool:
    if not (-119.9 <= lon <= -118.9 and 50.2 <= lat <= 50.8):
        return False
    fs = await wfs(c, L_FWA, _pt("GEOMETRY", lon, lat), props=["GNIS_NAME", "FWA_WATERSHED_CODE"], count=20)
    return any(str(f["properties"].get("FWA_WATERSHED_CODE", "")).startswith(SALMON_FWA) for f in fs)


# ------------------------------------------------------------------ ECCC
async def eccc(c, lon, lat, today: dt.date) -> dict:
    """Nearest ECCC daily-climate stations (<= 3, within ~80 km) and a 10-year monthly climate summary at the nearest one
    that is still reporting."""
    d = await F._json(c, f"{ECCC}/climate-stations/items", {"f": "json", "bbox": f"{lon - 1.1},{lat - 0.75},{lon + 1.1},{lat + 0.75}",
                                                           "limit": 500, "properties": "CLIMATE_IDENTIFIER,STATION_NAME,STN_ID,ELEVATION,"
                                                           "DLY_FIRST_DATE,DLY_LAST_DATE,MLY_LAST_DATE,LATITUDE,LONGITUDE,PROV_STATE_TERR_CODE"},
                      httpx.Timeout(15.0, connect=5.0))
    sts = []
    for f in d.get("features", []):
        p = f["properties"]
        x, y = f["geometry"]["coordinates"]
        first, last = (p.get("DLY_FIRST_DATE") or "")[:10], (p.get("DLY_LAST_DATE") or "")[:10]
        if not first or not last:
            continue
        sts.append({"id": p["CLIMATE_IDENTIFIER"], "stn_id": p.get("STN_ID"), "name": p["STATION_NAME"], "lat": round(y, 4), "lon": round(x, 4),
                    "elev_m": float(p["ELEVATION"]) if p.get("ELEVATION") not in (None, "") else None,
                    "daily": [first, last], "distance_km": round(km(lat, lon, y, x), 1),
                    "active": last >= (today - dt.timedelta(days=60)).isoformat()})
    sts = [s for s in sts if s["distance_km"] <= 80]
    active = sorted((s for s in sts if s["active"]), key=lambda s: s["distance_km"])
    long_closed = sorted((s for s in sts if not s["active"] and s["daily"][1] >= "2010"), key=lambda s: s["distance_km"])
    chosen = (active[:2] + long_closed[:1])[:3] or sorted(sts, key=lambda s: s["distance_km"])[:2]
    out = {"stations": chosen, "monthly": None}
    if not active:
        return out
    st = active[0]
    y1 = today.year - 1
    m = await F._json(c, f"{ECCC}/climate-monthly/items", {
        "f": "json", "CLIMATE_IDENTIFIER": st["id"], "datetime": f"{y1 - 9}-01/{y1}-12", "limit": 200,
        "properties": "LOCAL_YEAR,LOCAL_MONTH,MEAN_TEMPERATURE,TOTAL_PRECIPITATION,DAYS_WITH_VALID_PRECIP,DAYS_WITH_VALID_MEAN_TEMP"},
        httpx.Timeout(15.0, connect=5.0))
    rows = [f["properties"] for f in m.get("features", [])]
    out["monthly"] = summarise_monthly(rows, st, y1)
    return out


def summarise_monthly(rows, st, y1) -> dict | None:
    t = {}
    p = {}
    for r in rows:
        mo = int(r["LOCAL_MONTH"])
        if r.get("MEAN_TEMPERATURE") is not None and (r.get("DAYS_WITH_VALID_MEAN_TEMP") or 0) >= 25:
            t.setdefault(mo, []).append(float(r["MEAN_TEMPERATURE"]))
        if r.get("TOTAL_PRECIPITATION") is not None and (r.get("DAYS_WITH_VALID_PRECIP") or 0) >= 25:
            p.setdefault(mo, []).append(float(r["TOTAL_PRECIPITATION"]))
    if len(t) < 12 and len(p) < 12:
        return None
    mean = lambda v: round(sum(v) / len(v), 1) if v else None  # noqa: E731
    tm = {m: mean(t.get(m, [])) for m in range(1, 13)}
    pm = {m: mean(p.get(m, [])) for m in range(1, 13)}
    full_p = all(pm[m] is not None for m in range(1, 13))
    full_t = all(tm[m] is not None for m in range(1, 13))
    return {"station": st["id"], "name": st["name"], "years": [y1 - 9, y1],
            "mean_temp_c": round(sum(tm.values()) / 12, 1) if full_t else None,
            "july_mean_c": tm[7], "january_mean_c": tm[1],
            "annual_precip_mm": round(sum(pm.values())) if full_p else None,
            "apr_sep_precip_mm": round(sum(pm[m] for m in range(4, 10))) if all(pm[m] is not None for m in range(4, 10)) else None,
            "monthly_mean_temp_c": [tm[m] for m in range(1, 13)], "monthly_precip_mm": [pm[m] for m in range(1, 13)],
            "months_used": {"temp": sum(len(v) for v in t.values()), "precip": sum(len(v) for v in p.values())},
            "method": "mean of the station's monthly values with >= 25 valid days, over the last 10 complete years"}


# ------------------------------------------------------------------ AAFC ACI
async def aci_history(c, pts: list) -> dict:
    """{year: {"counts": {code: n}, "n": samples}} (the CDL shape build.crop_history reads)."""
    geom = json.dumps({"points": pts, "spatialReference": {"wkid": 4326}})
    sem = asyncio.Semaphore(2)   # the ACI servers stall a third concurrent request for ~5 s

    async def one(y):
        async with sem:
            d = await F._json(c, ACI.format(year=y) + "/getSamples", {"geometry": geom, "geometryType": "esriGeometryMultipoint",
                                                                       "returnFirstValueOnly": "true", "f": "json"})
        return y, d.get("samples", [])

    out = {}
    for res in await asyncio.gather(*(one(y) for y in ACI_YEARS), return_exceptions=True):
        if isinstance(res, Exception):
            continue
        y, samples = res
        for s in samples:
            v = s.get("value")
            if v in (None, "NoData", ""):
                continue
            code = str(int(float(str(v).split(",")[0])))
            e = out.setdefault(y, {"counts": {}, "n": 0})
            e["counts"][code] = e["counts"].get(code, 0) + 1
            e["n"] += 1
    if not out:
        raise RuntimeError("AAFC ACI ImageServer answered no year")
    return {y: v for y, v in out.items() if set(v["counts"]) != {"0"}}


def aci_legend() -> dict:
    return {str(k): v for k, v in ACI_LEGEND.items()}


def family_bc(aci: dict) -> tuple[str, str, bool]:
    years = sorted(aci)
    if not years:
        return "other", "no AAFC crop inventory here: the BC forage rotation set (BC0-BC3) is shown as a stand-in", False
    maj = {y: max(aci[y]["counts"], key=aci[y]["counts"].get) for y in years}
    typed = {y: c for y, c in maj.items() if c not in ("120", "0")}
    n_for = sum(c == FORAGE for c in typed.values())
    n_crop = sum(c not in NOT_CROP for c in maj.values())
    span = f"{years[0]}-{years[-1]}"
    if typed and n_for >= max(2, len(typed) / 2):
        return "forage", f"the AAFC crop inventory shows pasture / forages in {n_for} of {len(typed)} crop-typed years {span}", True
    if n_crop < len(years) / 2:
        return "other", (f"the AAFC crop inventory shows cropland in only {n_crop} of {len(years)} years {span} (not a farm field?): "
                         "the BC forage rotation set (BC0-BC3) is shown as a stand-in"), False
    return "other", (f"the AAFC crop inventory shows mostly crops other than forage {span}: the BC forage rotation set (BC0-BC3) is "
                     "the closest stand-in, not a plan for this crop"), True


# ------------------------------------------------------------------ SLC (local file)
@lru_cache(maxsize=1)
def _slc() -> dict:
    with gzip.open(SLC_FILE, "rt") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _slc_rest() -> dict:
    with gzip.open(SLC_REST, "rt") as f:
        return json.load(f)


def slc_at(lon, lat) -> dict | None:
    for doc in (_slc(), _slc_rest()):
        for p in doc["polygons"]:
            b = p["bbox"]
            if not (b[0] <= lon <= b[2] and b[1] <= lat <= b[3]):
                continue
            if sum(F.in_ring(lon, lat, r) for r in p["rings"]) % 2 == 1:
                return {**p, "source": doc["source"]}
    return None


async def canada_place(c, lon, lat) -> dict | None:
    """Nearest named place and province from the Canadian Geographical Names Database (any province)."""
    for radius in (12, 25, 50):
        d = await F._json(c, GEONAMES, {"lat": round(lat, 5), "lon": round(lon, 5), "radius": radius,
                                        "concise": "CITY,TOWN,VILG,UNP,MUN1,MUN2"}, httpx.Timeout(12.0, connect=5.0))
        items = d.get("items", [])
        if items:
            it = min(items, key=lambda i: km(lat, lon, i["latitude"], i["longitude"]))
            code = str((it.get("province") or {}).get("code"))
            return {"name": it["name"], "province": PROVINCES.get(code, (None, None))[0],
                    "province_name": PROVINCES.get(code, (None, None))[1],
                    "distance_km": round(km(lat, lon, it["latitude"], it["longitude"]), 1)}
    return None


# ------------------------------------------------------------------ US tribal land (Census AIANNH)
async def tribal_at(c, lon, lat) -> dict | None:
    async def one(layer):
        d = await F._json(c, f"{TIGER}/{layer}/query", {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
                                                        "spatialRel": "esriSpatialRelIntersects", "outFields": "NAME,BASENAME,GEOID",
                                                        "returnGeometry": "false", "f": "json"}, httpx.Timeout(8.0, connect=4.0))
        return [(layer, f["attributes"]) for f in d.get("features", [])]
    res = await asyncio.gather(*(one(k) for k in TIGER_LAYERS), return_exceptions=True)
    hits = [h for r in res if not isinstance(r, Exception) for h in r]
    if not hits:
        if all(isinstance(r, Exception) for r in res):
            raise res[0]
        return None
    layer, a = hits[0]
    return {"name": a.get("NAME"), "basename": a.get("BASENAME"), "geoid": a.get("GEOID"), "kind_detail": TIGER_LAYERS[layer]}


# ------------------------------------------------------------------ land status + Nation tools
def _prog(name, url, what, verified=True, note=None):
    d = {"name": name, "what": what, "verified": verified}
    if verified:
        d["url"] = url
    else:
        d["unverified_url"] = url
    if note:
        d["note"] = note
    return d


BC_PROGRAMS = [
    _prog("B.C. Indigenous food systems and agriculture (Ministry of Agriculture and Food)",
          "https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/indigenous-food-systems-and-agriculture",
          "Provincial hub for Indigenous-led farming and food programs, including the B.C. Indigenous Pathfinder service."),
    _prog("Investment Agriculture Foundation of BC (IAF) programs",
          "https://iafbc.ca/programs/",
          "IAF delivers the cost-shared Indigenous Food Systems and Agriculture programs (IFSAP, up to $80,000 per project in "
          "past intakes; skills and training). Check the page for which intakes are open."),
    _prog("IAF Indigenous Food Systems and Agriculture Skills and Training Program",
          "https://iafbc.ca/indigenous-food-systems-and-agriculture-skills-and-training-program/",
          "Training and skills funding for Indigenous farm and food projects (IAF)."),
    _prog("AAFC Indigenous Pathfinder Service",
          "https://agriculture.canada.ca/en/programs/indigenous-pathfinder-service",
          "Free one-on-one advice from Agriculture and Agri-Food Canada on federal programs for First Nations, Metis and Inuit farms."),
]
CA_PROGRAMS = [
    _prog("BIA Branch of Tribal Community Resilience (Tribal Climate Resilience annual awards)",
          "https://www.bia.gov/bia/ots/descrm/tcr",
          "Bureau of Indian Affairs funding for Tribes' climate adaptation, drought and water planning."),
    _prog("USDA Office of Tribal Relations", "https://www.usda.gov/tribalrelations",
          "USDA's government-to-government office for Tribes: the entry point to USDA farm, conservation and loan programs.",
          verified=False, note="usda.gov answered 403 to the build host's automated check (15 Nov 2026); open it in a browser"),
    _prog("NRCS Environmental Quality Incentives Program (EQIP): historically underserved and tribal provisions",
          "https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives",
          "Cost-share for conservation practices; Tribes and tribal members qualify for historically underserved payment rates and "
          "advance payments.",
          verified=False, note="nrcs.usda.gov did not answer the build host's automated check (15 Nov 2026); open it in a browser"),
]
SGMA_TRIBAL = {"text": "Under SGMA a Groundwater Sustainability Agency must consider the interests of all beneficial uses and users "
                       "of groundwater, which the law lists to include California Native American tribes (Water Code section "
                       "10723.2(h)). Ask the GSA how it consults the Tribe on its groundwater plan.",
               "citation": "California Water Code section 10723.2(h)",
               "url": "https://california.public.law/codes/water_code_section_10723.2", "verified": True}


def land_status_bc(reserve: dict) -> dict:
    return {"kind": "first_nations_reserve", "name": (reserve.get("name") or "").title(),
            "nation": nation(reserve.get("band")), "band": reserve.get("band"), "band_number": reserve.get("band_number"),
            "source": {"title": "Indian reserves with band names (CLSS boundaries), BC Data Catalogue", "layer": L_RESERVE,
                       "url": "https://catalogue.data.gov.bc.ca/dataset/8efe9193-80d2-4fdf-a18c-d531a94196ad", "verified": True}}


def land_status_us(t: dict) -> dict:
    return {"kind": "tribal_land", "name": t.get("name"), "nation": t.get("basename") or t.get("name"), "detail": t.get("kind_detail"),
            "geoid": t.get("geoid"),
            "source": {"title": "US Census TIGERweb AIANNH (American Indian, Alaska Native and Native Hawaiian areas)", "url": TIGER,
                       "verified": True}}


def nation_tools(land: dict | None, *, salmon: bool = False, water: dict | None = None) -> dict | None:
    if not land:
        return None
    out = {"nation": land.get("nation"), "land": land.get("name")}
    if land["kind"] == "first_nations_reserve":
        out["programs"] = BC_PROGRAMS
        if salmon:
            out["salmon"] = {"route": "/salmon", "text": "This land drains to the Salmon River (Shuswap): see the salmon and "
                                                         "water-licence page for the river's flows and fish protection orders."}
    else:
        out["programs"] = CA_PROGRAMS
        w = (water or {})
        out["groundwater"] = {"sgma_subbasin": w.get("sgma_subbasin"), "sgma_subbasin_number": w.get("sgma_subbasin_number"),
                              "gsa": w.get("gsa") or [], "tribal_engagement": SGMA_TRIBAL}
    return out
