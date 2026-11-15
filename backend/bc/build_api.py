"""API payloads for the British Columbia field (bc_salmon_river_forage). No network.

Run (uses the backend/api venv, which has pandas and the API's builders):
    cd backend/api && uv run python ../bc/build_api.py

Writes backend/api/out/bc_salmon_river_forage/:
  location.json, daily.json, features_weekly.json, nasa_series.json, validation.json,
  trends_{heatwave_days,precip_anomaly,grace_gw_pct,smap_anomaly,modis_ndvi_anomaly}.json (the NASA ones when cached),
  zones.json (when backend/field has built the 30 m grid)
first_nations.json (GET /first_nations; facts from docs/bc-first-nations.md, reserves from reserves_nearby.json)
and backend/news/out/bc_salmon_river_forage.json (the Salmon River items of bc_opener.json).

Reuses backend/api/nasa_build.py (load, nasa_series, nasa_datasets, validation_checks, trends, Hargreaves) and the generic
helpers of backend/api/build_real.py. The California-only pieces (NCEI, USDM, CDEC, SSURGO, CDL, OpenET, RMA, DSWx summary)
are not built: the registry's `not_available` reasons go into location.json `data_gaps`, and the API answers those routes
with 404 "not available in BC: <reason>".

Every input is optional except the registry entry, the field polygon, POWER and ECCC. Anything missing is listed at the end
under "skipped" so the script can simply be rerun once the downloads finish.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
API = REPO / "backend" / "api"
sys.path.insert(0, str(API))
sys.path.insert(0, str(REPO / "backend" / "fields"))
import build_real as BR  # noqa: E402  generic helpers: clean, r, sn, blocked_sn, write, power_cell, doy_ranges, monthly_compare
import fieldreg  # noqa: E402
import nasa_build as NB  # noqa: E402

FID = "bc_salmon_river_forage"
CACHE = REPO / "data" / "cache" / FID
FIELD_OUT = REPO / "backend" / "field" / "out" / FID
OUT = API / "out" / FID
DAILY_FROM = "2015-01-01"
skipped: list[str] = []
used: list[str] = []

GAP_LABEL = {
    "openet": "Measured crop water use (OpenET)",
    "cimis": "CIMIS weather stations",
    "insurance": "Crop-insurance loss records (USDA RMA)",
    "sgma": "Water district, groundwater basin and reservoirs (SGMA, CDEC)",
    "cdl": "USDA Cropland Data Layer",
    "soil_survey": "Field-scale soil survey (SSURGO)",
    "outlook": "Coming-season outlooks (NOAA CPC, US Drought Monitor, CDEC)",
    "ml_calendar": "Machine-learning calendar and crop-stress flags",
}
# which API routes each gap closes (the API returns 404 "not available in BC: <reason>" for them)
GAP_ROUTES = {"openet": ["/openet"], "insurance": ["/insurance"], "outlook": ["/outlook", "/trends?layer=usdm_d2_weeks"],
              "sgma": ["/trends?layer=reservoir_storage"], "ml_calendar": ["/calendar_ml", "/stress", "/transitions", "/models"]}


def jload(p: Path):
    return json.loads(Path(p).read_text())


def have(path: Path, what: str) -> bool:
    ok = path.exists()
    (used if ok else skipped).append(f"{what} ({path.relative_to(REPO)})")
    return ok


def write(name: str, obj: dict):
    BR.write(FID, name, obj)


# ------------------------------------------------------------------ inputs
class Ctx:
    def __init__(self):
        self.p = FID
        self.reg = fieldreg.get(FID)
        self.poly = jload(REPO / "backend" / "field" / "polygons" / f"{FID}.geojson")["features"][0]
        self.power = pd.read_parquet(CACHE / "power.parquet")
        self.power["date"] = pd.to_datetime(self.power["date"])
        self.pmeta = jload(CACHE / "power.meta.json")
        self.eccc = pd.read_parquet(CACHE / "eccc.parquet")
        self.eccc["date"] = pd.to_datetime(self.eccc["date"])
        self.emeta = jload(CACHE / "eccc.meta.json")
        used.extend(["NASA POWER (data/cache/<id>/power.parquet)", "ECCC stations (data/cache/<id>/eccc.parquet)"])
        self.src_power = BR.meta_source(FID, "power", "nasa_power", "NASA POWER daily point (MERRA-2 cell), AG community")
        self.src_eccc = {"id": "eccc_climate_daily", "title": self.emeta["title"], "url": self.emeta["url"],
                         "accessed": self.emeta["fetched_at"][:10], "verified": True}
        self.station_daily = self.eccc.groupby("date")[["prcp_mm", "tmax_c", "tmin_c"]].mean()  # skipna mean over stations
        self.nasa = NB.load(FID)
        for k in ("imerg", "smap_l4", "smap_l3", "grace", "modis", "ecostress", "dswx", "hls", "power_nrt"):
            (used if k in self.nasa else skipped).append(f"NASA {k} (data/cache/<id>/{k}.parquet)")
        self.derived = derived_from_power(self.power, self.pmeta["params"]["latitude"])
        self.ext = NB.extended_derived(self.derived, self.nasa, self.pmeta["params"]["latitude"])
        self.cal = jload(FIELD_OUT / "calendar.json") if have(FIELD_OUT / "calendar.json", "S2/Landsat calendar") else None
        self.hist = jload(FIELD_OUT / "crop_history.json") if have(FIELD_OUT / "crop_history.json", "AAFC ACI crop history") else None
        sg = CACHE / "soilgrids.json"
        self.soilgrids = jload(sg) if have(sg, "SoilGrids") else None
        tf = REPO / "backend" / "nasa_open" / "out" / FID / "terrain.json"
        self.nasadem = jload(tf)["field_summary"] if have(tf, "NASADEM terrain") else None
        self.hls_cover = NB.hls_cover_by_date(FID)
        have(REPO / "backend" / "nasa" / "out" / FID / "calendar_hls.json", "HLS calendar")
        self.grid = FIELD_OUT / "grid.geojson"
        have(self.grid, "30 m NDVI grid")
        have(REPO / "backend" / "engine" / "out" / FID / "strategies.json", "engine strategies (served by the API as is)")


def derived_from_power(pw: pd.DataFrame, lat: float) -> pd.DataFrame:
    """The backend/regional daily_derived columns for a field it does not cover: Hargreaves ETo (FAO-56 eq. 52) on POWER
    Tmax/Tmin and the same heat flags (>= 35 C runs of 3+ days, >= 40 C)."""
    d = pw[["date", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"]].copy().sort_values("date").reset_index(drop=True)
    d["eto_hargreaves_mm"] = NB._hargreaves(d.T2M_MAX.values, d.T2M_MIN.values, lat, d.date.dt.day_of_year.values)
    heat = d.T2M_MAX >= 35
    s = heat.astype(int)
    g = (s != s.shift()).cumsum()
    d["heatwave_day"] = heat & (s.groupby(g).transform("size") >= 3)
    d["severe_heat"] = d.T2M_MAX >= 40
    return d


# ------------------------------------------------------------------ location
def example_limit(family: str) -> dict:
    return BR.example_limit(family)


def soil_block(x: Ctx) -> dict:
    gaps = x.reg.get("not_available", {})
    sg = x.soilgrids
    if not sg:
        why = "SoilGrids not fetched yet (backend/bc/fetch_soilgrids.py)"
        return {"mukey": "pending", "muname": "SoilGrids v2.0 not fetched yet", "drainage_class": "unknown", "hydrologic_group": "unknown",
                "awc_mm_per_m": BR.blocked_sn("mm/m", why), "om_pct": BR.blocked_sn("%", why), "texture_class": "unknown",
                "source": {"id": "soilgrids_v2", "url": "https://rest.isric.org/soilgrids/v2.0/properties/query", "verified": False},
                "note": gaps.get("soil_survey", "")}
    src = {k: sg["source"][k] for k in ("id", "title", "url", "accessed", "verified")}
    top = sg["summary"]["0-30cm"]
    soc, lo, hi = top.get("soc"), (top.get("low") or {}).get("soc"), (top.get("high") or {}).get("soc")
    om = lambda v: None if v is None else v / 10 * 1.724  # noqa: E731  SOC g/kg -> OM % (van Bemmelen, assumed)
    return {
        "mukey": "soilgrids_v2",
        "muname": "ISRIC SoilGrids v2.0 250 m model at the field (not a soil-survey map unit)",
        "drainage_class": "unknown", "hydrologic_group": "unknown",
        "awc_mm_per_m": BR.blocked_sn("mm/m", "available water capacity is not a SoilGrids property; no BC soil-survey API"),
        "om_pct": BR.sn(om(soc), "%", src, "0-30 cm SoilGrids SOC x 1.724 (van Bemmelen factor, assumed); low/high from the 5-95% "
                        "prediction interval at the centroid", low=om(lo), high=om(hi), method="model"),
        "texture_class": (sg.get("texture_class_0_30cm") or "unknown").lower(),
        "texture_detail": {"sand_pct": top.get("sand"), "silt_pct": top.get("silt"), "clay_pct": top.get("clay"),
                           "method": "USDA triangle on 0-30 cm SoilGrids median sand/silt/clay (mean of 5 points in the field)"},
        "ph_0_30cm": top.get("phh2o"),
        "source": {"id": src["id"], "url": src["url"], "verified": bool(src["verified"])},
        "note": gaps.get("soil_survey", "") + " Drainage class and hydrologic group are not SoilGrids properties: unknown.",
    }


def observed_cover(x: Ctx) -> dict:
    """Days of the year the S2/Landsat rule detector calls the field bare in most calendar years with forage in the ACI."""
    if not x.cal:
        return {"typically_bare_doy_ranges": [], "bare_doy_file": None, "years_used": [], "detector": "unavailable (S2/Landsat calendar not built yet)"}
    forage = {int(y) for y, c in ((x.hist or {}).get("by_year") or {}).items() if "Forage" in c}
    yrs = [y for y in x.cal["years"] if (not forage or y["year"] in forage) and y.get("segments")]
    if not yrs:
        return {"typically_bare_doy_ranges": [], "bare_doy_file": None, "years_used": [], "detector": "unavailable (no calendar years)"}
    votes = np.zeros(365)
    for y in yrs:
        for seg in y["segments"]:
            if seg["class"] != "bare":
                continue
            for d in pd.date_range(seg["start"], seg["end"]):
                if d.year == y["year"] and d.day_of_year <= 365:
                    votes[d.day_of_year - 1] += 1
    bare = votes > len(yrs) / 2
    return {"typically_bare_doy_ranges": BR.doy_ranges(bare), "bare_doy_file": None, "years_used": [y["year"] for y in yrs],
            "detector": "rule_ndvi majority (backend/field calendar.json, years the AAFC ACI maps Pasture / Forages; bare gaps <= 10 days merged)"}


# ------------------------------------------------------------------ First Nations context (facts and URLs from docs/bc-first-nations.md)
FN_DOC = "docs/bc-first-nations.md"
FN_STATEMENT = "Built to be co-developed with First Nations farmers; we'd only add a reserve field with the Nation's permission."
NATION = {"Splatsin": "Splatsin", "Neskonlith": "Neskonlith", "Adams Lake": "Adams Lake",
          "Skwlax te Secwepemculecw": "Skwlax te Secwépemc", "Okanagan": "Okanagan Indian Band (Syilx)"}
SPLATSIN_LAND = "https://splatsin.ca/your-government/land"
FN_STEPS = [
    "Contact Splatsin first: its reserve, Salmon River 1, is on the lower Salmon River. Its public lands page lists the Lands Department and the Territorial Water Manager role.",
    "Send a short, plain-language note: what the tool does, that no reserve data has been analysed, and whether there is any interest at all. Accept \"no\" or no reply.",
    "Ask for the Nation's research protocol and who decides. A Band Council Resolution or a data-sharing agreement may be needed.",
    "Offer in writing: Nation ownership of all outputs for its land, co-design, no publication without written consent, data returned or deleted on request, credit and paid time, and a community-controlled version if wanted.",
    "Expect months, not a hackathon weekend. Nothing is added before the answer is yes.",
    "Talk to the neighbouring Nations and bodies with interests in the river (Neskonlith, Adams Lake, Okanagan Indian Band, Secwépemc Fisheries Commission).",
]
FN_PRINCIPLES = [
    {"id": "ocap", "name": "OCAP®", "description": "Ownership, Control, Access and Possession: First Nations control data collection in their communities and own their information collectively. OCAP® is a registered trademark of the First Nations Information Governance Centre (FNIGC).",
     "url": "https://fnigc.ca/wp-content/uploads/2022/10/OCAP_Brochure_20220927_web.pdf", "verified": True},
    {"id": "care", "name": "CARE Principles for Indigenous Data Governance", "description": "Collective benefit, Authority to control, Responsibility and Ethics (Global Indigenous Data Alliance); they complement the FAIR data principles.",
     "url": "https://www.gida-global.org/careprinciples", "verified": True},
    {"id": "tcps2_ch9", "name": "TCPS 2 (2022), Chapter 9", "description": "Research involving First Nations, Inuit and Métis Peoples: Art. 9.1 requires seeking community engagement, including for research on First Nations lands.",
     "url": "https://ethics.gc.ca/eng/tcps2-eptc2_2022_chapter9-chapitre9.html", "verified": True},
]
FN_CONTACTS = [
    {"nation": "Splatsin", "department": "Lands Department; Territorial Water Manager", "url": SPLATSIN_LAND},
    {"nation": "Neskonlith", "department": "Contact page", "url": "https://neskonlith.net/contact-us/"},
    {"nation": "Adams Lake", "department": "Lands, Natural Resources", "url": "https://adamslakeband.org/contact-us/"},
    {"nation": "Okanagan Indian Band", "department": "Administration", "url": "https://okib.ca/services/administration"},
    {"nation": "Shuswap Nation Tribal Council", "department": "Secwépemc Fisheries Commission", "url": "https://shuswapnation.org/fisheries/"},
]
BC_2026 = "https://news.gov.bc.ca/releases/2026WLRS0042-000965"
FN_WATER = [
    {"date": "2023-08-16", "title": "Fish population protection order M0238_2023 (lower Salmon River; M0239_2023 for Bessette Creek): about 398 surface and groundwater licence holders stop using water for forage crops.",
     "url": "https://news.gov.bc.ca/releases/2023FOR0052-001305", "verified": True},
    {"date": "2025", "title": "Low-flow monitoring: the Secwépemc Fisheries Commission and Splatsin's Yucwmenlúcwu (caretakers of the land) staff assessed low-flow barriers to fish passage on the lower Salmon River.",
     "url": "https://psf.ca/blog/smarter-drought-monitoring-for-salmon/", "verified": True},
    {"date": "2026-07-28", "title": "Temporary protection order issued for the Salmon River.", "url": BC_2026, "verified": True},
    {"date": "2026-08-08", "title": "Order rescinded as farmers and ranchers dealt with elevated wildfire risk (BC's wording).", "url": BC_2026, "verified": True},
    {"date": "2026-08-10", "title": "Okanagan Nation Chiefs Executive Council letter to the Minister about the order being rescinded without consultation.", "url": "https://syilx.org/?p=5013", "verified": True},
    {"date": "2026-08-19", "title": "New temporary protection order: 458 surface water and groundwater licences and transitioning groundwater users in the Salmon River watershed stop irrigating forage crops, lawns, fairways and gardens; effective 19 Aug 2026.",
     "url": BC_2026, "verified": True, "licences": 458, "effective": "2026-08-19"},
]


def first_nations(x: Ctx) -> dict | None:
    f = CACHE / "reserves_nearby.json"
    if not have(f, "reserves list (reserves_nearby.json)"):
        return None
    rj = jload(f)
    nearby = sorted(({"reserve": r["name"], "nation": NATION.get(r["band"], r["band"]), "band": r["band"], "band_number": str(r["band_number"]),
                      "area_ha": r["area_ha"], "distance_to_field_km": r["distance_to_field_km"]} for r in rj["reserves"]),
                    key=lambda r: r["distance_to_field_km"])
    near = nearby[0]
    return {
        "location_id": FID,
        "statement": FN_STATEMENT,
        "field_on_reserve": False,
        "nearest_km": near["distance_to_field_km"],
        "nearest_reserve": near["reserve"], "nearest_nation": near["nation"],
        "lower_river_nation": {"nation": "Splatsin", "band_number": "600", "reserve": "SALMON RIVER 1 (SPLATSIN)",
                               "note": "Salmon River 1 is the reserve on the lower Salmon River", "url": SPLATSIN_LAND, "verified": True},
        "nearby": nearby,
        "engagement_steps": FN_STEPS,
        "principles": FN_PRINCIPLES,
        "contacts": FN_CONTACTS,
        "water_timeline": FN_WATER,
        "reserves_geojson": f"/api/locations/{FID}/first_nations/reserves.geojson" if (CACHE / "reserves_nearby.geojson").exists() else None,
        "source": {**rj["source"], "accessed": rj["fetched_at"][:10], "verified": True},
        "notes": ["Reserve boundaries are legal survey boundaries (CLSS), not traditional territories; territories are wider and overlap. "
                  "No reserve land was analysed. Distances are straight-line from the field outline.",
                  f"Facts and links from {FN_DOC} (checked 15 Nov 2026). Nothing here speaks for any Nation."],
    }


def build_first_nations(x: Ctx) -> dict | None:
    fn = x.fn = first_nations(x)
    if fn:
        write("first_nations.json", fn)
    return fn


def build_location(x: Ctx) -> dict:
    reg, props = x.reg, x.poly["properties"]
    bs = props["boundary_source"]
    area = BR.sn(props["area_ha"], "ha", {"id": bs["id"], "title": bs["title"], "url": bs["url"], "accessed": props.get("selected_at", x.emeta["fetched_at"])[:10],
                                         "verified": True}, "polygon area of the ParcelMap BC x AAFC ACI outline chosen by backend/bc")
    terrain = {
        "slope_mean_pct": BR.blocked_sn("%", "NASADEM not built for this field yet (backend/nasa_open)"),
        "slope_p90_pct": BR.blocked_sn("%", "NASADEM not built yet"),
        "elev_m": BR.sn(x.pmeta.get("elevation_m"), "m", x.src_power, "elevation of the POWER (MERRA-2) grid cell, NOT a field DEM value "
                        "(the valley floor is far lower than the cell mean)", method="lookup"),
        "low_spot_fraction": BR.blocked_sn("fraction", "NASADEM not built yet"),
    }
    if x.nasadem:
        terrain = {k: x.nasadem[k] for k in ("slope_mean_pct", "slope_p90_pct", "elev_m", "low_spot_fraction") if k in x.nasadem}
    gaps = reg.get("not_available", {})
    na = lambda k: {"status": "not_available", "reason": gaps.get(k, "")}  # noqa: E731
    datasets = {
        "power": {"status": "real", "meta_path": f"data/cache/{FID}/power.meta.json", "range": [x.pmeta["date_min"], x.pmeta["date_max"]]},
        "s2": ({"status": "real", "meta_path": f"backend/field/out/{FID}/calendar.json"} if x.cal else {"status": "pending", "reason": "S2/Landsat fetch not finished (backend/field)"}),
        "cdl": {**na("cdl"), "replaced_by": {"id": "aafc_aci", "meta_path": f"data/cache/{FID}/aci.meta.json"}},
        "cdec": na("sgma"), "dwr_wells": na("sgma"), "usdm": na("outlook"), "rma": na("insurance"), "openet": na("openet"), "cimis": na("cimis"),
        "news": {"status": "real", "meta_path": "backend/news/out/bc_salmon_river_forage.json (from bc_opener.json)"},
        "dem": ({"status": "real", "meta_path": f"backend/nasa_open/out/{FID}/terrain.json", "product": "NASADEM_HGT.001"} if x.nasadem
                else {"status": "pending", "reason": "NASADEM not built yet (backend/nasa_open)"}),
    }
    for k in ("imerg", "smap_l3", "smap_l4", "hls", "modis", "ecostress", "grace"):
        datasets[k] = ({"status": "real", "meta_path": f"data/cache/{FID}/{k}.meta.json"} if k in x.nasa
                       else {"status": "pending", "reason": "not fetched for this field yet (backend/nasa)"})
    nds = NB.nasa_datasets(FID, x.nasa)
    for e in nds:   # nasa_datasets carries California-specific notes for DSWx
        if e["id"] == "dswx":
            e["note"] = "Not fetched for this field; GET /water_seen is not available in BC."
    stations = []
    for st in x.emeta["selected_stations"]:
        last = st.get("last") or st["daily"][1]
        stations.append({"network": "ECCC", "id": st["climate_id"], "name": st["name"],
                         "distance_km": BR.r(_km(reg["centroid"], st), 1), "years": [int(st["first"][:4]), int(last[:4])]})
    cell = BR.power_cell(x.pmeta["params"]["longitude"], x.pmeta["params"]["latitude"])
    wc = reg.get("water_context") or {}
    water = {"source": None, "source_note": "surface vs groundwater use not looked up (BC water licences are not queried)",
             "allocation_input": {"unit": "acre-ft/acre", "value": None},
             "example_limit_af_ac": example_limit(reg["family"]),
             "district": None, "other_agencies": [], "sgma_subbasin": None, "sgma_subbasin_number": None, "sgma_priority": None,
             "critically_overdrafted": None, "gsa": [],
             "sgma_status": {"text": gaps.get("sgma"), "url": None, "verified": False},
             "cdec_stations": []}
    events = [{"date": o["date"], "type": "water_order", "title": o["title"], "url": o["url"], "verified": o["verified"]} for o in wc.get("orders", [])]
    loc = {
        "id": FID, "name": reg["name"], "region": "bc", "region_adapter": "bc", "regime": "summer_drought_water_order",
        "state_fips": reg["county"]["fips"][:2], "county_fips": reg["county"]["fips"][2:],
        "county_code_system": reg["county"].get("code_system"), "province": reg["county"].get("province"),
        "geometry": x.poly["geometry"], "centroid": reg["centroid"], "area_ha": area, "crs_working": props.get("crs_working", "EPSG:32610"),
        "family": reg["family"], "farmer_name": reg["farmer_name"], "acres": reg["acres"], "county_name": reg["county"]["name"],
        "county_kind": reg["county"].get("kind"), "template": reg["template"], "why_chosen": reg["why"],
        "soil": soil_block(x), "terrain": terrain, "water": water, "water_context": wc, "market_preference": "no_preference",
        "stations": stations,
        "regional_cell": {"grid": "POWER_MERRA2_0.5x0.625", "row": cell[0], "col": cell[1], "footprint": cell[2]},
        "datasets": datasets, "nasa_datasets": nds,
        "crop_history": dict((x.hist or {}).get("by_year", {})), "crop_history_source": (x.hist or {}).get("source"),
        "observed_cover": observed_cover(x), "events": events,
        "first_nations": ({k: fn[k] for k in ("statement", "field_on_reserve", "nearest_km", "nearest_reserve", "nearest_nation")}
                          | {"lower_river_nation": "Splatsin", "route": f"/api/locations/{FID}/first_nations"}) if (fn := getattr(x, "fn", None)) else None,
        "data_gaps": [{"id": k, "what": GAP_LABEL.get(k, k), "reason": v, "routes": GAP_ROUTES.get(k, [])} for k, v in gaps.items()],
        "_notes": {"region": "British Columbia field: CA-only layers are listed in data_gaps; their API routes return 404 'not available in BC: <reason>'.",
                   "water_and_market": "No water district or SGMA basin in BC; water_context holds the watershed and the 2023 orders. "
                                       "market_preference is not stated for this field (no_preference, U).",
                   "boundary": bs["title"], "crop_history": "AAFC Annual Crop Inventory majority class per year (no alfalfa class)",
                   "stations": x.emeta.get("note", "")},
    }
    write("location.json", loc)
    return loc


def _km(c: dict, st: dict) -> float:
    lat1, lon1, lat2, lon2 = map(np.radians, (c["lat"], c["lon"], st["lat"], st["lon"]))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return float(6371 * 2 * np.arcsin(np.sqrt(a)))


# ------------------------------------------------------------------ daily + weekly
def cover_by_date(x: Ctx):
    if not x.cal:
        return {}, {}
    return BR.cover_by_date(x)


def build_daily(x: Ctx):
    d = x.ext[x.ext.date >= DAILY_FROM].set_index("date")
    st = x.station_daily
    cls, obs = cover_by_date(x)
    rows = []
    for dt_, row in d.iterrows():
        o = obs.get(dt_)
        ndv = float(np.mean([a["ndvi"] for a in o if a.get("ndvi") is not None])) if o else None
        rows.append({
            "date": dt_.strftime("%Y-%m-%d"), "tmax_c": BR.r(row.T2M_MAX), "tmin_c": BR.r(row.T2M_MIN), "precip_mm": BR.r(row.PRECTOTCORR),
            "eto_mm": BR.r(row.eto_hargreaves_mm), "ndvi": BR.r(ndv, 3) if ndv is not None else None,
            "cover_class": cls.get(dt_) or x.hls_cover.get(dt_, "unknown"),
            "cover_source": "s2_landsat" if dt_ in cls else ("hls" if dt_ in x.hls_cover else None),
            "power_run": row.power_run, **NB.daily_extra(x.nasa, dt_),
            "eccc_tmax_c": BR.r(st.tmax_c.get(dt_)), "eccc_tmin_c": BR.r(st.tmin_c.get(dt_)), "eccc_precip_mm": BR.r(st.prcp_mm.get(dt_)),
            "ncei_tmax_c": None, "ncei_tmin_c": None, "ncei_precip_mm": None,
            "heatwave_day": bool(row.heatwave_day), "severe_heat_40c": bool(row.severe_heat),
        })
    write("daily.json", {
        "location_id": FID, "from": rows[0]["date"], "to": rows[-1]["date"], "station_network": "ECCC",
        "sources": {"power": x.src_power, "eccc": x.src_eccc,
                    **{k: NB.src(k) for k in ("imerg", "smap_l4", "smap_l3", "grace") if k in x.nasa},
                    "eto": {"id": "hargreaves_fao56_eq52", "title": "Hargreaves ETo (FAO-56 eq. 52) on POWER Tmax/Tmin (backend/bc/build_api.py, same formula as backend/regional)",
                            "url": "https://www.fao.org/3/x0490e/x0490e07.htm", "accessed": NB.ACCESSED, "verified": True}},
        "notes": ["Station columns are eccc_* (mean of the ECCC stations Salmon Arm CS and Silver Creek, the latter closed Oct 2021); "
                  "ncei_* are null because there are no NOAA stations in BC.",
                  "POWER rows run to the latest day in data/cache/<id>/power.parquet (power_run 'archive'), then power_nrt if cached.",
                  "cover_class is 'unknown' where no S2/Landsat or HLS calendar covers the day.",
                  "NASA columns (imerg_*, smap_*, grace_gw_pct) are null where the dataset is not cached for this field."],
        "rows": rows})


def build_weekly(x: Ctx):
    d = x.ext.set_index("date")
    d = d[d.index >= "2016-01-01"]
    ow = None
    if x.cal:
        o = pd.DataFrame([{"date": pd.Timestamp(a["date"]), "ndvi": a["ndvi"], "bsi": a.get("bsi")} for y in x.cal["years"] for a in y["observations"]])
        if len(o):
            o["week"] = o.date.dt.to_period("W-SUN").dt.start_time
            ow = o.groupby("week").agg(ndvi_median=("ndvi", "median"), ndvi_p10=("ndvi", lambda s: s.quantile(.1)),
                                       ndvi_p90=("ndvi", lambda s: s.quantile(.9)), bsi=("bsi", "median"))
    rows = []
    for w, df in d.groupby(d.index.to_period("W-SUN").start_time):
        if len(df) < 7:
            continue
        iso = w.isocalendar()
        rw = ow.loc[w] if ow is not None and w in ow.index else None
        g = (lambda k: BR.r(rw[k], 3) if rw is not None else None)
        rows.append({
            "week_start": w.strftime("%Y-%m-%d"), "iso_year": int(iso.year), "iso_week": int(iso.week),
            "ndvi_median": g("ndvi_median"), "ndvi_p10": g("ndvi_p10"), "ndvi_p90": g("ndvi_p90"), "bsi": g("bsi"),
            "nbr2": None, "lst_anomaly_k": None, "esi": None, "openet_et_mm_month": None, "smap_sm": None, "smap_sm_pct": None,
            "imerg_7d_mm": None, "power_tmax_c": BR.r(df.T2M_MAX.mean()), "power_tmin_c": BR.r(df.T2M_MIN.mean()),
            "power_eto_mm": BR.r(df.eto_hargreaves_mm.sum()), "grace_sfsm_pct": None, "grace_rzsm_pct": None, "grace_gws_pct": None,
            "modis_ndvi_anomaly": None, "usdm_category": None})
        rows[-1].update(NB.weekly_extra(x.nasa, w))
    write("features_weekly.json", {
        "location_id": FID,
        "sources": {"power": x.src_power, **{k: NB.src(k) for k in ("imerg", "smap_l4", "grace", "modis", "ecostress") if k in x.nasa}},
        "notes": ["weeks start Monday; ndvi_* over the Sentinel-2/Landsat observations in that week (null if none or the calendar is not built)",
                  "power_tmax_c/tmin_c weekly means, power_eto_mm weekly sum (Hargreaves)",
                  "usdm_category is null: " + x.reg.get("not_available", {}).get("outlook", "US Drought Monitor does not cover BC"),
                  "openet_et_mm_month is null: " + x.reg.get("not_available", {}).get("openet", "")],
        "rows": rows})


# ------------------------------------------------------------------ trends
def trend(layer, unit, grid, source, by_year, note, default_year, markers):
    years = sorted(by_year)
    write(f"trends_{layer}.json", {
        "location_id": FID, "layer": layer, "unit": unit, "grid": grid, "source": source, "note": note,
        "default_year": default_year, "years": [int(y) for y in years],
        "by_year": {y: [{"row": 0, "col": 0, "value": v}] for y, v in by_year.items()},
        "field_cell_series": [{"year": int(y), "value": by_year[y]} for y in years], "event_markers": markers})


def build_trends(x: Ctx, loc: dict):
    markers = [{k: e[k] for k in ("date", "title", "url", "verified")} for e in loc["events"]]
    d = x.derived.copy()
    d["year"] = d.date.dt.year
    cell = "POWER_MERRA2_0.5x0.625"
    full = d.groupby("year").date.count()
    full = full[full >= 365].index
    hw = d[d.year.isin(full)].groupby("year").heatwave_day.sum()
    trend("heatwave_days", "days/yr", cell, x.src_power, {str(y): int(v) for y, v in hw.items()},
          "Days per calendar year inside a >=3-day run of POWER Tmax >= 35 C (same rule as the California fields, thresholds U). "
          "One grid cell (row 0, col 0). The POWER cell is mostly mountains, so its Tmax is likely cooler than the valley floor.", 2023, markers)
    pr = d[d.year.isin(full)].groupby("year").PRECTOTCORR.sum()
    base = pr.loc[1991:2020].mean()
    trend("precip_anomaly", "% of 1991-2020 mean", cell, x.src_power, {str(y): BR.r((v / base - 1) * 100, 1) for y, v in pr.items()},
          f"Calendar-year POWER PRECTOTCORR total vs its 1991-2020 mean ({base:.0f} mm). Complete years only.", 2023, markers)
    for layer, (unit, grid, source, by, note, _dy) in NB.trends(x.nasa).items():
        trend(layer, unit, grid, source, by, note, 2023, markers)


# ------------------------------------------------------------------ validation
def build_validation(x: Ctx):
    mc = BR.monthly_compare(x)
    checks = []
    names = ", ".join(f"{s['name']} ({s['climate_id']})" for s in x.emeta["selected_stations"])
    for cid, key, title, unit, pct in (("power_vs_eccc_precip", "precip", "POWER vs ECCC station rain (monthly totals)", "mm/month", True),
                                       ("power_vs_eccc_tmax", "tmax", "POWER vs ECCC station Tmax (monthly means)", "degC", False),
                                       ("power_vs_eccc_tmin", "tmin", "POWER vs ECCC station Tmin (monthly means)", "degC", False)):
        df = mc[key]
        if len(df) < 12:
            continue
        s = BR.stats(df, pct)
        met = {"bias": BR.sn(s["bias"], unit, x.src_eccc, "POWER - stations, mean over months"),
               "rmse": BR.sn(s["rmse"], unit, x.src_eccc, "root mean square difference of monthly values"),
               "r2": BR.sn(s["r2"], "", x.src_eccc, "squared correlation of monthly values"),
               "n_months": BR.sn(s["n_months"], "months", x.src_eccc, "months compared")}
        if pct:
            met["bias_pct"] = BR.sn(s["bias_pct"], "%", x.src_eccc, "total POWER rain vs total station rain")
        checks.append({"id": cid, "title": title, "status": "computed", "metrics": met,
                       "note": f"POWER point (0.5 deg cell, elevation {x.pmeta.get('elevation_m')} m) vs mean of ECCC stations {names}; "
                               f"months with >= 27 station-mean days; {df.index.min()}..{df.index.max()}. Bias = POWER minus stations.",
                       "by_calendar_month": [{"month": m, "bias": BR.r((df[df.index.month == m].power - df[df.index.month == m].ncei).mean(), 2),
                                              "power_mean": BR.r(df[df.index.month == m].power.mean(), 2),
                                              "eccc_mean": BR.r(df[df.index.month == m].ncei.mean(), 2)} for m in range(1, 13)],
                       "series": [{"month": str(k), "power": BR.r(v.power), "eccc": BR.r(v.ncei)} for k, v in df.tail(120).iterrows()]})
    for c in NB.validation_checks(x.nasa, x.station_daily, x.ext[["date", "PRECTOTCORR"]], BR.sn, x.src_eccc, x.src_power):
        c["title"] = c["title"].replace("NOAA NCEI", "ECCC")
        checks.append(c)
    gaps = x.reg.get("not_available", {})
    blocked = lambda cid, title, why: {"id": cid, "title": title, "status": "blocked",  # noqa: E731
                                       "metrics": {"bias_pct": BR.blocked_sn("%", why), "r2": BR.blocked_sn("", why)}, "note": f"not available in BC: {why}"}
    checks.append(blocked("openet_vs_etc", "OpenET vs modelled ETc", gaps.get("openet", "")))
    checks.append(blocked("cimis_vs_power", "CIMIS vs NASA POWER ETo", gaps.get("cimis", "")))
    write("validation.json", {"location_id": FID, "checks": checks})


# ------------------------------------------------------------------ nasa series, zones
def build_nasa_series(x: Ctx):
    write("nasa_series.json", NB.nasa_series(FID, x.nasa))


def build_zones(x: Ctx):
    if x.grid.exists():
        BR.build_zones(x)


def build_news():
    """backend/news/out/<id>.json: the Salmon River / Shuswap items of bc_opener.json (query bc_salmon_2023), so the API's
    family-template news fallback never serves California news for this field. The Fraser Valley (Sumas 2021) items stay on
    GET /api/bc/news only: different valley."""
    src = REPO / "backend" / "news" / "out" / "bc_opener.json"
    if not have(src, "BC news (bc_opener.json)"):
        return
    items = [{**i, "_derived_from": "backend/news/out/bc_opener.json"} for i in jload(src) if i.get("query_id") == "bc_salmon_2023"]
    items.sort(key=lambda i: (i["date"], i["rank"]))
    (REPO / "backend" / "news" / "out" / f"{FID}.json").write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    x = Ctx()
    build_first_nations(x)
    loc = build_location(x)
    build_daily(x)
    build_weekly(x)
    build_trends(x, loc)
    build_validation(x)
    build_nasa_series(x)
    build_zones(x)
    build_news()
    print(f"{FID}: wrote {sorted(f.name for f in OUT.iterdir())}")
    print("used:\n  " + "\n  ".join(used))
    print("skipped (missing; rerun `cd backend/api && uv run python ../bc/build_api.py` once fetched):\n  " + ("\n  ".join(skipped) or "none"))


if __name__ == "__main__":
    main()
