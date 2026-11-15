"""Nation tools: features for First Nations and tribal farm, lands and water staff, for any location the API serves
(presets such as car_colusa_rice and bc_salmon_river_forage, and tapped points pt_*).

  GET /api/locations/{pid}/nation                  summary: land status, nearest Nations/tribes, place names, links
  GET /api/locations/{pid}/nation/drought_rotation rotations vs a mid-season water cutoff, drought history by water year
  GET /api/locations/{pid}/nation/groundwater      California only (404 elsewhere): subbasin, GSAs, SGMA status, GRACE-DA, pumping need
  GET /api/locations/{pid}/nation/land_season      NDVI phenology (proxy), snow-off, fire detections, regulation links
  GET /api/locations/{pid}/nation/funding          programs table (backend/nation/programs.json), filtered and sorted
  GET /api/locations/{pid}/nation/report.json|.pdf one-page field report, optionally for a funding program

Mounted from app/main.py BEFORE the anyloc router (whose catch-all would otherwise answer pt_* ids with 404).
All data comes from existing cached outputs, the rotation engine's strategies, and short live lookups (BC reserve WFS, Census
AIANNH, NASA POWER for tapped points, FIRMS open CSVs).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import os
import re
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from . import data as D
from . import geo as G

router = APIRouter()
_FEEDS: dict = {}
FIRMS_KEY_ENV = "FIRMS_MAP_KEY"
GRACE_CAVEAT = ("GRACE-DA is a ~25 km (0.25 degree) regional groundwater and soil-moisture product, not a well measurement; "
                "it shows how this area's groundwater storage compares with its own history, not the level in any well.")
NDVI_CAVEAT = ("NDVI phenology is a proxy for when green vegetation grows and dies back on this polygon. It is not a measure of game, berries "
               "or plant abundance, and for a farm field it follows the crop, not wild plants.")
HARVEST_NOTE = ("Aboriginal/treaty and tribal harvesting rights are set by the Nation and by law, not by this tool; provincial/state seasons "
                "shown for context only. CropLytics stores no harvest, hunting or cultural-site locations.")
BOUNDARY_CAVEAT = "Reserve, reservation and trust boundaries are legal or statistical boundaries, not traditional territory and not where a Nation's rights apply."


class Ctx:
    pass


def _mod():
    from .. import main as M  # lazy: main imports this package
    return M


def _al():
    from .. import anyloc as A
    return A


async def get_ctx(pid: str, req: Request, need_daily: bool = False) -> Ctx:
    M, A = _mod(), _al()
    c = Ctx()
    c.pid, c.is_point, c.daily, c.series, c.weekly = pid, False, None, None, None
    if pid in M.PRESETS:
        loc, _ = await asyncio.to_thread(M.resolve, "location", pid)
        try:
            st, _ = await asyncio.to_thread(M.resolve, "strategies", pid)
            c.strategies = st.get("items", [])
        except HTTPException:
            c.strategies = []
        c.region_code = M.fieldreg.region(pid)
        c.source = "real"
    else:
        pt = A.B.parse_id(pid) if pid.startswith("pt_") else None
        if pt is None:
            raise HTTPException(404, f"unknown location {pid}: expected a preset id or a tapped-point id pt_<n|s><lat x 1e4>_<e|w><lon x 1e4>")
        c.is_point = True
        lat, lon = pt
        _, (loc, items, meta), _ = await A.get_or_compute(req, lat, lon, False)
        c.strategies = items or []
        c.region_code = loc.get("region") or ("ca" if loc.get("state_fips") == "06" else None)
        c.source = "live"
    c.loc = loc
    c.lon, c.lat = loc["centroid"]["lon"], loc["centroid"]["lat"]
    if c.region_code not in ("ca", "bc"):
        c.region_code = "bc" if D.BC_BOX[0] <= c.lon <= D.BC_BOX[2] and D.BC_BOX[1] <= c.lat <= D.BC_BOX[3] and c.lat > 49.0 and c.lon < -114.0 else "us"
    c.jurisdiction = "BC" if c.region_code == "bc" else ("CA" if c.region_code == "ca" or loc.get("state_fips") == "06" else "US")
    c.name = loc.get("name") or pid
    a = loc.get("area_ha")
    c.area_ha = a.get("value") if isinstance(a, dict) else a
    c.acres = loc.get("acres") or (c.area_ha * 2.47105 if c.area_ha else None)
    if need_daily:
        await _load_series(c, M, A, req)
    return c


async def _load_series(c: Ctx, M, A, req):
    if not c.is_point:
        def rd():
            for kind, attr in (("daily", "daily"), ("features_weekly", "weekly")):
                try:
                    setattr(c, attr, M.resolve(kind, c.pid)[0].get("rows", []))
                except Exception:  # noqa: BLE001
                    setattr(c, attr, None)
            f = D.ROOT / "backend" / "api" / "out" / c.pid / "nasa_series.json"
            c.series = D.read_json(f).get("rows") if f.is_file() else None
        await asyncio.to_thread(rd)
        return
    try:
        async with A.F.client() as cl:
            df, pmeta = await asyncio.wait_for(A.STORE.get(cl, c.lon, c.lat), 30)
        c.daily = A.B.daily_payload(c.pid, df, c.lat, pmeta, dt.date.today().isoformat()).get("rows", [])
    except Exception:  # noqa: BLE001
        c.daily = None


def out(resp: Response, c: Ctx, body: dict) -> dict:
    body = {"location_id": c.pid, **body, "_source": c.source}
    resp.headers["X-Data-Source"] = c.source
    return body


async def guarded(pid: str, req: Request, build, need_daily=False):
    """Run build(ctx) in a worker thread; tapped-point guard errors become the anyloc 429 response."""
    A = _al()
    try:
        c = await get_ctx(pid, req, need_daily)
    except A.Busy as e:
        return A.busy_response(e), None
    return None, c


# ------------------------------------------------------------------ builders (sync)
def src(id_, title, url, verified=True):
    return {"id": id_, "title": title, "url": url, "verified": verified}


SRC = {
    "engine": src("engine", "CropLytics rotation engine (backend/engine; FAO-56 crop water use, rule-of-thumb scores)", "https://www.fao.org/3/x0490e/x0490e00.htm", False),
    "power": src("nasa_power", "NASA POWER daily point (MERRA-2), reference ET and rain", "https://power.larc.nasa.gov/"),
    "imerg": src("gpm_imerg", "NASA GPM IMERG daily precipitation V07", "https://doi.org/10.5067/GPM/IMERGDF/DAY/07"),
    "grace": src("grace_da", "NASA GRACE/GRACE-FO data-assimilation drought indicators (GRACEDADM_CLSM025GL_7D)", "https://doi.org/10.5067/8DNK2ZU3U1RO"),
    "smap": src("smap_l4", "NASA SMAP L4 root-zone soil moisture", "https://nsidc.org/data/spl4smgp"),
    "bc_reserves": src("bc_reserves", "BC Indian reserves with band names (CLSS legal boundaries)", G.BC_URL),
    "aiannh": src("census_aiannh", "US Census TIGERweb American Indian/Alaska Native/Native Hawaiian areas", G.TIGER_URL),
    "modis_snow": src("mod10a2", "MODIS/Terra Snow Cover 8-Day L3 (MOD10A2 v061)", "https://doi.org/10.5067/MODIS/MOD10A2.061"),
    "firms": src("firms", "NASA FIRMS active fire (VIIRS)", "https://firms.modaps.eosdis.nasa.gov/"),
    "mtbs": src("mtbs", "MTBS burn severity and perimeters (US)", "https://www.mtbs.gov/"),
    "bcfire": src("bc_fire_hist", "BC Wildfire Fire Perimeters - Historical", "https://catalogue.data.gov.bc.ca/dataset/bc-wildfire-fire-perimeters-historical"),
}


def links_for(pid: str) -> dict:
    b = f"/api/locations/{pid}/nation"
    return {"drought_rotation": f"{b}/drought_rotation", "groundwater": f"{b}/groundwater", "land_season": f"{b}/land_season",
            "funding": f"{b}/funding", "report_pdf": f"{b}/report.pdf", "report_json": f"{b}/report.json"}


def build_summary(c: Ctx) -> dict:
    res = G.nearby(c.lon, c.lat, "bc" if c.region_code == "bc" else "us")
    ls = G.land_status(res, c.region_code)
    seen, nearest = set(), []
    for a in res["areas"]:
        if a["nation"] in seen:
            continue
        seen.add(a["nation"])
        nearest.append({"nation": a["nation"], "nearest_area": a["name"], "area_kind": a["kind"], "distance_km": a["distance_km"], "inside": a["inside"]})
        if len(nearest) >= 6:
            break
    names = [{"name": n["name"], "english": n["english"], "nation": n["nation"], "language": n["language"], "source_url": n["source_url"],
              "source_type": n["source_type"], "source_text": n["source_text"], "approved_by_nation": n["approved_by_nation"]}
             for n in D.place_names() if D.km_between(c.lon, c.lat, *n["center"]) <= n["radius_km"]]
    return {"location": {"name": c.name, "lat": c.lat, "lon": c.lon, "region": c.region_code, "jurisdiction": c.jurisdiction, "area_ha": c.area_ha},
            "land_status": ls, "nearest_nations": nearest,
            "nearby_areas_count": len(res["areas"]), "search_radius_km": 65,
            "place_names": names, "tools": links_for(c.pid),
            "sources": [SRC["bc_reserves"] if c.region_code == "bc" else SRC["aiannh"]],
            "caveats": [BOUNDARY_CAVEAT,
                        "Nations and tribes are listed by distance only. Nothing here implies that any Nation or tribe uses, endorses or partners with CropLytics."]}


def series_status(c: Ctx) -> dict:
    has = bool(c.series) and not c.is_point
    st = {"power_et0": {"status": "real" if c.daily else "not_computed", "reason": None if c.daily else "NASA POWER did not answer"},
          "imerg": {"status": "real" if has else "not_computed", "reason": None if has else "IMERG is cached for the preset fields only, not tapped points"},
          "grace": {"status": "not_computed", "reason": "GRACE-DA is cached for the preset fields only, not tapped points"},
          "smap": {"status": "not_computed", "reason": "SMAP L4 is cached for the preset fields only, not tapped points"}}
    if c.daily and not c.is_point:
        if any(r.get("grace_gw_pct") is not None for r in c.daily):
            st["grace"] = {"status": "real", "reason": None}
        st["smap"] = ({"status": "real", "reason": None} if any(r.get("smap_sm_pct") is not None for r in c.daily)
                      else {"status": "not_computed", "reason": "SMAP L4 fetch not finished for this field (backend/nasa)"})
    return st


def build_drought(c: Ctx, cutoff: str) -> dict:
    rots = D.rotations(c.strategies, c.acres, cutoff)
    hist = D.drought_history(c.daily, c.series) if c.daily else []
    sources = [SRC["engine"], SRC["power"]]
    st = series_status(c)
    if st["imerg"]["status"] == "real":
        sources.append(SRC["imerg"])
    if st["grace"]["status"] == "real":
        sources.append(SRC["grace"])
    if st["smap"]["status"] == "real":
        sources.append(SRC["smap"])
    return {"cutoff_date": cutoff, "cutoff_note": "MM-DD, the day irrigation water stops (for example a licence order). Crop water use after it is prorated from the engine's monthly ETc.",
            "rotations": rots, "cutoff_scenarios": D.cutoff_scenarios(c.strategies, cutoff),
            "drought_history": hist, "history_basis": "water years (1 Oct to 30 Sep); year = the year the water year ends; partial = fewer than 360 days of data",
            "series_status": st, "sources": sources,
            "caveats": ["Rotation numbers are the engine's rule-of-thumb estimates (FAO-56 ETc from POWER weather), the mean of 2015-2025 weather years; "
                        "water_mm_after_cutoff is prorated from monthly ETc, not a simulation of a shut-off.",
                        "irrigation_need_mm_after_cutoff scales the engine's irrigation need by the share of crop water use after the cutoff.",
                        "yield_loss_pct is null: CropLytics does not model yield loss from a cutoff; unmet_water_share_pct is the share of crop water use that would not be met.",
                        "n_balance_kg_ha is null: the engine gives nitrogen scores (0-100), not kilograms. erosion_index is rain-weighted bare days per year, not tonnes per hectare.",
                        "soil_cover_pct = 100 x (1 - bare days / 365) from the engine's bare-day count.",
                        "imerg_precip_anom_pct compares the water-year IMERG total with the 2001-2025 mean for the same day; the other columns are water-year means (GRACE, SMAP) or sums (ET0)."]
            + (["Tapped point: only NASA POWER weather is computed; IMERG, SMAP and GRACE columns are not_computed."] if c.is_point else [])}


def lookup_water(c: Ctx) -> dict:
    return (c.loc.get("water") or {})


def build_groundwater(c: Ctx) -> dict:
    w = lookup_water(c)
    lk = w.get("lookup") or {}
    gsas = lk.get("gsa") or [{"name": n, "id": None, "url": None} for n in (w.get("gsa") or [])]
    sb = w.get("sgma_subbasin")
    sub_title = sb.split(" - ")[-1].title() + " Subbasin" if sb else None
    board = (lk.get("state_board") or {})
    gw, smap = [], []
    status = {"status": "not_computed", "reason": "GRACE-DA is cached for the preset fields only, not tapped points"}
    if c.weekly:
        gw = [{"week_start": r["week_start"], "gw_pctl": r["grace_gws_pct"]} for r in c.weekly if r.get("grace_gws_pct") is not None]
        smap = [{"week_start": r["week_start"], "smap_pctl": r["smap_sm_pct"]} for r in c.weekly if r.get("smap_sm_pct") is not None]
        if gw:
            status = {"status": "real", "reason": None}
    pump = []
    for st in c.strategies:
        af = D._v((st.get("water") or {}).get("irrigation_need_af_ac"))
        pump.append({"id": st["id"], "name": st.get("short_name") or st.get("name"), "irrigation_need_af_per_acre": D._r(af, 2),
                     "acres": D._r(c.acres), "pumping_need_af": D._r(af * c.acres) if af is not None and c.acres else None})
    links = [
        {"title": "DWR guidance: Engagement with Tribal Governments under SGMA (June 2017 draft text)", "url": "https://cawaterlibrary.net/wp-content/uploads/2018/03/GD_Tribal_Final_2017-06-28.pdf", "verified": True},
        {"title": "DWR Tribal Policy and SGMA Tribal Advisory Group", "url": "https://water.ca.gov/About/Tribal-Policy", "verified": False},
        {"title": "State Water Board: SGMA groundwater basins and tribal affairs", "url": "https://www.waterboards.ca.gov/water_issues/programs/sgma/groundwater_basins/", "verified": True},
        {"title": "DWR SGMA Data Viewer and portal", "url": "https://sgma.water.ca.gov/portal/", "verified": True}]
    if sb and "TULARE LAKE" in sb.upper():
        links.append({"title": "State Water Board, Tulare Lake probationary hearing, Final Staff Report Appendix C (tribal consultation record, 2024)",
                      "url": "https://www.waterboards.ca.gov/sgma/docs/tulare-lake/202403-tulare-lake-pbh-final-staff-report-appendix-c.pdf", "verified": True})
    return {"b118_subbasin_id": w.get("sgma_subbasin_number"), "b118_subbasin_name": sb, "subbasin_title": sub_title,
            "sgma_priority": w.get("sgma_priority"), "critically_overdrafted": w.get("critically_overdrafted"),
            "gsa_names": [g.get("name") for g in gsas if g.get("name")], "gsas": [{"name": g.get("name"), "id": g.get("id"), "url": g.get("url")} for g in gsas],
            "sgma_status": (w.get("sgma_status") or {}).get("text"), "sgma_status_url": (w.get("sgma_status") or {}).get("url"),
            "state_board_status": board.get("status"),
            "gw_pctl_weekly": gw, "gw_pctl_status": status,
            "smap_rootzone_weekly": smap,
            "smap_status": {"status": "real" if smap else "not_computed", "reason": None if smap else "SMAP L4 fetch not finished or not computed for this location"},
            "et_mm_by_crop": [{"rotation_id": st["id"], "crops": [{"crop_id": b["crop_id"], "etc_mm": D._r(D._v(b.get("etc_mm")))} for b in (st.get("water") or {}).get("by_crop", [])]} for st in c.strategies],
            "pumping_need_af_by_rotation": pump,
            "pumping_note": "Irrigation need x acres, as if all of it were pumped. How much is pumped depends on surface supply, which is not known here.",
            "tribal_links": links, "caveat": GRACE_CAVEAT,
            "caveats": [GRACE_CAVEAT, "This tool does not recommend recharge, flooding or any site on the ground."],
            "sources": [SRC["grace"], src("dwr_b118", "DWR Bulletin 118 groundwater basins and SGMA portal layers", "https://sgma.water.ca.gov/portal/")]}


def _firms(c: Ctx) -> tuple[dict, dict]:
    import httpx
    d7 = {"window_days": 7, "status": "not_computed", "count": 0, "detections": [], "within_km": 10, "reason": None, "source": SRC["firms"]}
    d365 = {"window_days": 365, "status": "not_computed", "count": 0, "detections": [], "within_km": 10, "source": SRC["firms"],
            "reason": f"The FIRMS 365-day area API needs a free MAP_KEY (set {FIRMS_KEY_ENV}); none is configured. See the 7-day open feed and the FIRMS map."}
    feeds = {"ca": "SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_7d", "us": "SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_7d", "bc": "SUOMI_VIIRS_C2_Canada_7d"}
    url = f"https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/{feeds[c.region_code]}.csv"
    try:
        hit = _FEEDS.get(url)
        if not hit or time.time() - hit[0] > 3600:
            r = httpx.get(url, timeout=httpx.Timeout(15.0, connect=5.0), follow_redirects=True)
            r.raise_for_status()
            lines = r.text.splitlines()
            hdr = lines[0].split(",")
            i = [hdr.index(k) for k in ("latitude", "longitude", "acq_date", "frp", "confidence")]
            rows = []
            for ln in lines[1:]:
                p = ln.split(",")
                rows.append((float(p[i[0]]), float(p[i[1]]), p[i[2]], float(p[i[3]] or 0), p[i[4]]))
            hit = _FEEDS[url] = (time.time(), rows)
        for la, lo, day, frp, conf in hit[1]:
            km = D.km_between(c.lon, c.lat, lo, la)
            if km <= 10:
                d7["detections"].append({"date": day, "lat": round(la, 3), "lon": round(lo, 3), "frp_mw": frp, "confidence": conf, "distance_km": round(km, 1)})
        d7["count"], d7["status"] = len(d7["detections"]), "real"
    except Exception as e:  # noqa: BLE001
        d7["reason"] = f"FIRMS open 7-day feed did not answer ({type(e).__name__})"
    key = os.environ.get(FIRMS_KEY_ENV)
    if key:
        d365 = _firms_365(c, key, d365)
    return d365, d7


def _firms_365(c: Ctx, key: str, base: dict) -> dict:
    import httpx
    from concurrent.futures import ThreadPoolExecutor
    dlat = 10 / 111.32
    dlon = dlat / max(0.3, __import__("math").cos(__import__("math").radians(c.lat)))
    area = f"{c.lon - dlon:.4f},{c.lat - dlat:.4f},{c.lon + dlon:.4f},{c.lat + dlat:.4f}"
    start = dt.date.today() - dt.timedelta(days=364)

    def one(k):
        d0 = start + dt.timedelta(days=5 * k)
        r = httpx.get(f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_SP/{area}/5/{d0.isoformat()}", timeout=20)
        r.raise_for_status()
        return r.text.splitlines()
    try:
        with ThreadPoolExecutor(8) as ex:
            chunks = list(ex.map(one, range(73)))
        seen = set()
        for ch in chunks:
            if len(ch) < 2 or "latitude" not in ch[0]:
                continue
            hdr = ch[0].split(",")
            for ln in ch[1:]:
                p = dict(zip(hdr, ln.split(",")))
                k = (p["latitude"], p["longitude"], p["acq_date"], p["acq_time"])
                if k in seen:
                    continue
                seen.add(k)
                km = D.km_between(c.lon, c.lat, float(p["longitude"]), float(p["latitude"]))
                if km <= 10:
                    base["detections"].append({"date": p["acq_date"], "lat": round(float(p["latitude"]), 3), "lon": round(float(p["longitude"]), 3),
                                               "frp_mw": float(p.get("frp") or 0), "confidence": p.get("confidence"), "distance_km": round(km, 1)})
        base["detections"].sort(key=lambda d: d["date"])
        base["count"], base["status"], base["reason"] = len(base["detections"]), "real", None
    except Exception as e:  # noqa: BLE001
        base["reason"] = f"FIRMS area API failed ({type(e).__name__})"
    return base


def build_land_season(c: Ctx) -> dict:
    rows = [{"week_start": r["week_start"], "ndvi": r["ndvi_median"]} for r in (c.weekly or []) if r.get("ndvi_median") is not None]
    if rows:
        nd = {"status": "real", "reason": None, "source": "field-median NDVI per week from Sentinel-2/Landsat/HLS (backend/field features_weekly)"}
        ph = D.phenology(rows)
    else:
        nd = {"status": "not_computed", "reason": "Weekly NDVI is built for the preset fields only. MODIS MOD13Q1 for a tapped point needs raster reads (Planetary Computer) that this API does not run."}
        ph = {"by_year": [], "greenup_doy": None, "peak_doy": None, "senescence_doy": None}
    snow = {"status": "not_computed", "reason": "MODIS snow-off is computed for the Salmon River (BC) preset watershed only (backend/nation/snow_off.py)", "years": [], "snow_off_doy": None}
    sf = D.NATION_DIR / "out" / f"snow_off_{c.pid}.json"
    if sf.is_file():
        j = D.read_json(sf)
        ys = [y for y in j["years"] if y["snow_off_doy"] is not None]
        snow = {"status": "real", "reason": None, "scope": j["scope"], "rule": j["rule"], "years": ys[-10:],
                "snow_off_doy": round(sum(y["snow_off_doy"] for y in ys) / len(ys)) if ys else None, "source": SRC["modis_snow"]}
    f365, f7 = _firms(c)
    if c.region_code == "bc":
        scars = [{"source": "BC Wildfire Fire Perimeters - Historical (BC Data Catalogue)", "url": SRC["bcfire"]["url"], "kind": "link", "year": None}]
        regs = [{"title": "BC Hunting and Trapping Regulations Synopsis", "url": "https://www2.gov.bc.ca/gov/content/sports-culture/recreation/fishing-hunting/hunting/regulations-synopsis"}]
    else:
        scars = [{"source": "MTBS burn severity and fire perimeters (US)", "url": SRC["mtbs"]["url"], "kind": "link", "year": None}]
        regs = ([{"title": "CDFW deer hunting zones", "url": "https://wildlife.ca.gov/Hunting/Deer/Zones"}, {"title": "CDFW elk hunting", "url": "https://wildlife.ca.gov/Hunting/Elk"}]
                if c.jurisdiction == "CA" else [{"title": "Your state wildlife agency's hunting regulations (not linked here)", "url": "https://www.usa.gov/state-wildlife-agencies"}])
    return {"ndvi_weekly": rows[-156:], "ndvi_status": nd, "phenology": ph,
            "phenology_note": NDVI_CAVEAT, "snow": snow, "fire_detections_365d": f365, "fire_detections_7d": f7,
            "burn_scars": scars, "regs_links": regs, "harvest_rights_note": HARVEST_NOTE,
            "sources": [SRC["firms"], SRC["modis_snow"]] + ([SRC["bcfire"]] if c.region_code == "bc" else [SRC["mtbs"]]),
            "caveats": [NDVI_CAVEAT, "Fire detections are satellite hot spots (375 m VIIRS), not fire perimeters.", HARVEST_NOTE,
                        "Used on the polygon you chose only; nothing here records where anyone hunts, fishes or gathers."]}


_ORDER = {"open": 0, "rolling": 1, "unknown": 2, "closed": 3}
_JUR = {"CA": {"CA", "US"}, "BC": {"BC", "CAN"}, "US": {"US"}, "CAN": {"CAN"}}


def build_funding(c: Ctx, jurisdiction: str | None) -> dict:
    j = (jurisdiction or c.jurisdiction).upper()
    if j not in _JUR:
        raise HTTPException(422, f"jurisdiction must be one of {sorted(_JUR)}")
    fmt = {"subbasin": ((lookup_water(c).get("sgma_subbasin") or "").split(" - ")[-1].title() + " Subbasin") if lookup_water(c).get("sgma_subbasin") else "this area",
           "watershed": "Salmon River watershed" if c.pid == "bc_salmon_river_forage" else (c.loc.get("county_name") or "this area"),
           "region": {"CA": "California", "BC": "British Columbia", "US": "the US"}.get(c.jurisdiction, c.jurisdiction)}
    d = D.programs()
    out = []
    for p in d["programs"]:
        if not set(p["jurisdictions"]) & _JUR[j]:
            continue
        reasons = p.get("reasons", {})
        key = "ca" if c.jurisdiction == "CA" else ("bc" if c.jurisdiction == "BC" else None)
        tpl = reasons.get(key) or reasons.get("default")
        reason = tpl.format(**fmt) if tpl else f"{p['agency']} program for {fmt['region']}. Eligibility: {p['eligible']}. {p['how_croplytics_helps']}"
        q = {k: v for k, v in p.items() if k not in ("reasons", "jurisdictions")}
        q["jurisdictions"] = p["jurisdictions"]
        q["matched_reason"] = reason
        out.append(q)
    out.sort(key=lambda p: _ORDER[p["status"]])
    counts = {s: sum(1 for p in out if p["status"] == s) for s in _ORDER}
    return {"jurisdiction": j, "location_jurisdiction": c.jurisdiction, "as_of": d["as_of"], "programs": out, "counts": counts,
            "disclaimer": d["about"]}


# ------------------------------------------------------------------ routes
def _cutoff(cutoff: str) -> str:
    if not D.CUTOFF_RE.match(cutoff):
        raise HTTPException(422, "cutoff must be MM-DD, for example 08-15")
    return cutoff


@router.get("/api/locations/{pid}/nation")
async def nation_summary(pid: str, req: Request, resp: Response):
    early, c = await guarded(pid, req, None)
    if early:
        return early
    return out(resp, c, await asyncio.to_thread(build_summary, c))


@router.get("/api/locations/{pid}/nation/drought_rotation")
async def nation_drought(pid: str, req: Request, resp: Response, cutoff: str = Query("08-15", description="MM-DD irrigation cutoff")):
    cutoff = _cutoff(cutoff)
    early, c = await guarded(pid, req, None, need_daily=True)
    if early:
        return early
    return out(resp, c, await asyncio.to_thread(build_drought, c, cutoff))


@router.get("/api/locations/{pid}/nation/groundwater")
async def nation_groundwater(pid: str, req: Request, resp: Response):
    early, c = await guarded(pid, req, None, need_daily=True)
    if early:
        return early
    if c.jurisdiction != "CA":
        raise HTTPException(404, "groundwater is built for California locations only (SGMA, Bulletin 118, GRACE-DA). "
                                 + ("For BC use the river flow view (/salmon) and the First Nations route." if c.jurisdiction == "BC" else "This location is outside California."))
    return out(resp, c, await asyncio.to_thread(build_groundwater, c))


@router.get("/api/locations/{pid}/nation/land_season")
async def nation_land_season(pid: str, req: Request, resp: Response):
    early, c = await guarded(pid, req, None, need_daily=True)
    if early:
        return early
    return out(resp, c, await asyncio.to_thread(build_land_season, c))


@router.get("/api/locations/{pid}/nation/funding")
async def nation_funding(pid: str, req: Request, resp: Response, jurisdiction: str | None = Query(None, description="CA | BC | US | CAN; default from the location")):
    early, c = await guarded(pid, req, None)
    if early:
        return early
    return out(resp, c, await asyncio.to_thread(build_funding, c, jurisdiction))


def build_report(c: Ctx, program: str | None, cutoff: str) -> dict:
    prog = None
    if program:
        prog = next((p for p in D.programs()["programs"] if p["id"] == program), None)
        if prog is None:
            raise HTTPException(422, f"unknown program '{program}'; see /nation/funding for ids")
    dr = build_drought(c, cutoff)
    gw = build_groundwater(c) if c.jurisdiction == "CA" else None
    ls = G.land_status(G.nearby(c.lon, c.lat, "bc" if c.region_code == "bc" else "us"), c.region_code)
    hist = (c.loc.get("crop_history") or {})
    last = max((k for k in hist if str(k).isdigit()), default=None)
    base = next((r for r in dr["rotations"] if r["is_baseline"]), dr["rotations"][0] if dr["rotations"] else None)
    ctx_block = ({"kind": "groundwater", "subbasin": gw["b118_subbasin_name"], "subbasin_id": gw["b118_subbasin_id"], "gsa_names": gw["gsa_names"],
                  "sgma_status": gw["sgma_status"], "grace_status": gw["gw_pctl_status"]["status"], "caveat": GRACE_CAVEAT} if gw else
                 {"kind": "river", "text": ("See /api/locations/bc_salmon_river_forage/salmon for the river-flow view." if c.region_code == "bc" else "No river or groundwater view is built for this location."),
                  "water_context": (c.loc.get("water_context") or {}).get("watershed")})
    secs = prog["report_sections"] if prog else ["field_outline", "drought_history", "water_baseline", "rotation_comparison", "water_context", "sources_caveats"]
    sources = list({s["id"]: s for s in dr["sources"] + (gw["sources"] if gw else []) + [src("land_status", ls["source"]["title"], ls["source"]["url"])]}.values())
    return {
        "title": "Field report: water, drought and rotation baseline", "generated": dt.date.today().isoformat(),
        "program": ({"id": prog["id"], "name": prog["name"], "agency": prog["agency"], "url": prog["url"], "status": prog["status"], "verified": prog["verified"]} if prog else None),
        "report_sections": secs,
        "field_outline": {"name": c.name, "lat": round(c.lat, 5), "lon": round(c.lon, 5), "area_ha": D._r(c.area_ha, 2), "acres": D._r(c.acres),
                          "land_status": ls["value"], "geometry": c.loc.get("geometry"),
                          "land_cover": {"label": hist.get(last), "year": int(last) if last else None, "source": "USDA Cropland Data Layer (majority class at the field)"} if last else {"label": None, "year": None, "source": None}},
        "drought_history": dr["drought_history"], "drought_basis": dr["history_basis"], "series_status": dr["series_status"],
        "water_baseline": {"cutoff_date": cutoff, "baseline_rotation": base["name"] if base else None,
                           "crop_water_use_mm_season": base["water_mm_season"] if base else None,
                           "irrigation_need_mm_season": base["irrigation_need_mm_season"] if base else None,
                           "irrigation_need_af_per_acre": base["irrigation_need_af_ac"] if base else None,
                           "note": "Crop water use (ETc) per the engine, mean of 2015-2025 weather years; OpenET is used by the engine as a check where available."},
        "rotation_comparison": dr["rotations"], "context": ctx_block,
        "sources": sources, "caveats": dr["caveats"] + ([GRACE_CAVEAT] if gw else []) + [BOUNDARY_CAVEAT],
        "prepared_for": None,
    }


@router.get("/api/locations/{pid}/nation/report.json")
async def nation_report_json(pid: str, req: Request, resp: Response, program: str | None = None, cutoff: str = "08-15"):
    cutoff = _cutoff(cutoff)
    early, c = await guarded(pid, req, None, need_daily=True)
    if early:
        return early
    return out(resp, c, await asyncio.to_thread(build_report, c, program, cutoff))


@router.get("/api/locations/{pid}/nation/report.pdf")
async def nation_report_pdf(pid: str, req: Request, program: str | None = None, cutoff: str = "08-15"):
    from .pdf import render
    cutoff = _cutoff(cutoff)
    early, c = await guarded(pid, req, None, need_daily=True)
    if early:
        return early
    rep = await asyncio.to_thread(build_report, c, program, cutoff)
    pdf = await asyncio.to_thread(render, rep)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="croplytics_field_report_{pid}.pdf"', "X-Data-Source": c.source})
