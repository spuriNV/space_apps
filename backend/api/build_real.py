"""Build the API's real lookup files from existing chunk outputs. No network.

Run:  cd backend/api && uv run python build_real.py            (both presets)
      uv run python build_real.py car_colusa_rice

Reads (never writes) data/cache/<id>/*, backend/regional/out/<id>/*, backend/field/{polygons,out}/*,
backend/engine (observed consensus cover). Writes backend/api/out/<id>/:
  location.json, daily.json, features_weekly.json, zones.json, validation.json, trends_<layer>.json

Every number is a SourcedNumber where the schema asks for one; blocked items are null with a "blocked: ..." note.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import nasa_build as NB

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]
NAMES = {"car_colusa_rice": "Colusa County rice check", "caf_tulare_forage": "Kings County forage-for-dairy check"}
COUNTY = {"car_colusa_rice": "011", "caf_tulare_forage": "031"}   # CAF centre is in Kings County (06031), not Tulare
FIPS = {"car_colusa_rice": "06011", "caf_tulare_forage": "06031"}
BASELINE_CROP = {"car_colusa_rice": "Rice", "caf_tulare_forage": "Alfalfa"}
ACCESSED = "2026-11-14"
DAILY_FROM = "2015-01-01"


def jload(p: Path):
    return json.loads(p.read_text())


def clean(x):
    """NaN/inf -> None, numpy -> python, recursively."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if x is pd.NaT:
        return None
    return x


def r(x, n=2):
    return None if x is None or not math.isfinite(float(x)) else round(float(x), n)


def sn(value, unit, source, note=None, low=None, high=None, method="computed"):
    d = {"value": r(value, 3), "unit": unit, "low": r(low, 3), "high": r(high, 3), "method": method}
    if value is not None:
        d["source"] = source
    if note:
        d["note"] = note
    return d


def blocked_sn(unit, why):
    return {"value": None, "unit": unit, "method": "assumed", "note": f"blocked: {why}"}


def meta_source(p: str, ds: str, sid: str, title: str, url_key="url") -> dict:
    m = jload(ROOT / "data" / "cache" / p / f"{ds}.meta.json")
    url = m.get(url_key) or (m.get("urls") or [""])[0]
    return {"id": sid, "title": title, "url": url, "accessed": m["fetched_at"][:10], "verified": True}


def write(p: str, name: str, obj: dict):
    d = OUT / p
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(clean(obj), separators=(",", ":"), allow_nan=False))


# ------------------------------------------------------------------ loading
class Ctx:
    def __init__(self, p: str):
        self.p = p
        c = ROOT / "data" / "cache" / p
        self.cache = c
        self.power = pd.read_parquet(c / "power.parquet")
        self.derived = pd.read_parquet(ROOT / "backend/regional/out" / p / "daily_derived.parquet")
        self.ncei = pd.read_parquet(c / "ncei.parquet")
        self.usdm = pd.read_parquet(c / "usdm.parquet")
        self.cdec = pd.read_parquet(c / "cdec.parquet")
        self.cal = jload(ROOT / "backend/field/out" / p / "calendar.json")
        self.hist = jload(ROOT / "backend/field/out" / p / "crop_history.json")
        self.poly = jload(ROOT / "backend/field/polygons" / f"{p}.geojson")["features"][0]
        self.soil = jload(c / "soil.json")
        self.pmeta = jload(c / "power.meta.json")
        self.nmeta = jload(c / "ncei.meta.json")
        self.src_power = meta_source(p, "power", "nasa_power", "NASA POWER daily point (MERRA-2 cell), AG community")
        self.src_ncei = meta_source(p, "ncei", "noaa_ncei_ghcnd", "NOAA NCEI GHCN-Daily (selected long-record stations)")
        self.src_usdm = meta_source(p, "usdm", "usdm", "US Drought Monitor county statistics")
        self.src_cdec = meta_source(p, "cdec", "cdec", "CDEC reservoir storage (sensor 15, daily)")
        self.station_daily = (self.ncei.groupby("date")[["prcp_mm", "tmax_c", "tmin_c"]].mean())  # skipna mean over stations
        self.nasa = NB.load(p)                      # backend/nasa + nasa_open caches (Earthdata datasets, HLS, POWER NRT)
        self.ext = NB.extended_derived(self.derived, self.nasa, self.pmeta["params"]["latitude"])  # POWER through the latest NRT day
        self.hls_cover = NB.hls_cover_by_date(p)


# ------------------------------------------------------------------ location
def power_cell(lon, lat):
    """MERRA-2 cell (0.5 deg lat x 0.625 deg lon, centres at multiples of those) containing the point."""
    row, col = round((lat + 90) / 0.5), round((lon + 180) / 0.625)
    clat, clon = row * 0.5 - 90, col * 0.625 - 180
    ring = [[clon - .3125, clat - .25], [clon + .3125, clat - .25], [clon + .3125, clat + .25], [clon - .3125, clat + .25], [clon - .3125, clat - .25]]
    return int(row), int(col), {"type": "Polygon", "coordinates": [ring]}


def doy_ranges(mask: np.ndarray) -> list[list[int]]:
    """1-based doy ranges where mask is True; a range wrapping the year end is [start, end] with start > end."""
    n = len(mask)
    if mask.all():
        return [[1, n]]
    if not mask.any():
        return []
    start = next(i for i in range(n) if not mask[i])      # rotate so we begin at a False
    out, i = [], 0
    rot = np.roll(mask, -start)
    while i < n:
        if rot[i]:
            j = i
            while j + 1 < n and rot[j + 1]:
                j += 1
            out.append([(i + start) % n + 1, (j + start) % n + 1])
            i = j + 1
        else:
            i += 1
    out = sorted(out)
    merged = []
    for a, b in out:          # close gaps of <= 10 days so the consensus reads as periods, not single days
        if merged and a - merged[-1][1] - 1 <= 10 and a <= b and merged[-1][0] <= merged[-1][1]:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return merged


def build_location(x: Ctx):
    p = x.p
    props = x.poly["properties"]
    fix = jload(ROOT / "fixtures" / p / "location.json")      # spec-stated (U) items: regime, water, market, events
    bs = props["boundary_source"]
    area = sn(props["area_ha"], "ha", {"id": bs["id"], "title": bs["title"], "url": bs["url"], "accessed": props["selected_at"][:10], "verified": True},
              "polygon area in EPSG:32610 from the DWR/Land IQ 2023 field outline chosen by backend/field")
    s = x.soil
    soil = {k: s[k] for k in ("mukey", "muname", "drainage_class", "hydrologic_group", "awc_mm_per_m", "om_pct", "texture_class")}
    soil["source"] = {"id": "ssurgo_sda", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": True}
    for extra in ("ec_ds_per_m", "dominant_component", "texture_detail"):
        if extra in s:
            soil[extra] = s[extra]
    elev = x.pmeta.get("elevation_m")
    tf = ROOT / "backend/nasa_open/out" / p / "terrain.json"
    nasadem = jload(tf)["field_summary"] if tf.exists() else None
    terrain = {
        "slope_mean_pct": blocked_sn("%", "no DEM fetched (NASADEM needs Earthdata; 3DEP not fetched)"),
        "slope_p90_pct": blocked_sn("%", "no DEM fetched"),
        "elev_m": sn(elev, "m", x.src_power, "elevation of the POWER (MERRA-2) grid cell, NOT a field DEM value", method="lookup"),
        "low_spot_fraction": blocked_sn("fraction", "no DEM fetched"),
    }
    if nasadem:  # NASADEM (backend/nasa_open): smoothed slope, field elevation, low-spot candidates
        terrain = {k: nasadem[k] for k in ("slope_mean_pct", "slope_p90_pct", "elev_m", "low_spot_fraction") if k in nasadem}

    cons = None
    try:
        from rotation_engine.engine import load_strategies
        from rotation_engine.observed import consensus
        base = next(st for st in load_strategies(p) if st["is_baseline"])
        cons = consensus(p, base)
    except Exception:  # noqa: BLE001
        cons = None
    if cons:
        bare = np.array([c == "bare" for c in cons["classes"]])
        observed = {"typically_bare_doy_ranges": doy_ranges(bare), "bare_doy_file": None, "years_used": cons["years"],
                    "detector": "rule_ndvi consensus (backend/field calendar.json, calendar years whose CDL crop is the baseline crop; bare gaps <= 10 days merged)"}
    else:
        observed = {"typically_bare_doy_ranges": [], "bare_doy_file": None, "years_used": [], "detector": "unavailable"}
    cell = power_cell(*[x.pmeta["params"]["longitude"], x.pmeta["params"]["latitude"]])
    stations = [{"network": "NOAA", "id": st["station"], "name": st["name"], "distance_km": r(st["dist_km"], 1),
                 "years": [int(st["first_obs"][:4]), int(st["last_obs"][:4])]} for st in x.nmeta["selected_stations"]]
    blocked = lambda why: {"status": "blocked", "reason": why}  # noqa: E731
    datasets = {
        "power": {"status": "real", "meta_path": f"data/cache/{p}/power.meta.json", "range": [x.pmeta["date_min"], x.pmeta["date_max"]]},
        "s2": {"status": "real", "meta_path": f"data/cache/{p}/s2.meta.json", "also": "landsat (data/cache/<id>/landsat.parquet)"},
        "cdl": {"status": "real", "meta_path": f"data/cache/{p}/cdl.meta.json"},
        "cdec": {"status": "real", "meta_path": f"data/cache/{p}/cdec.meta.json"},
        "usdm": {"status": "real", "meta_path": f"data/cache/{p}/usdm.meta.json", "county_fips": FIPS[p]},
        "news": {"status": "real", "meta_path": "backend/news/out/_stats.json"},
        "dem": ({"status": "real", "meta_path": f"backend/nasa_open/out/{p}/terrain.json", "product": "NASADEM_HGT.001"} if nasadem
                else blocked("NASADEM not built")),
        "openet": ({"status": "real", "meta_path": f"data/cache/{p}/openet.meta.json"} if (x.cache / "openet.parquet").exists()
                   else blocked("needs OpenET API key")),
        "cimis": blocked("needs CIMIS appKey"),
        "dwr_wells": {"status": "not_fetched"}, "rma": {"status": "not_fetched"},
    }
    for k in ("imerg", "smap_l3", "smap_l4", "hls", "modis", "ecostress", "grace"):
        meta_p = x.cache / f"{k}.meta.json"
        datasets[k] = ({"status": "real", "meta_path": f"data/cache/{p}/{k}.meta.json"} if k in x.nasa
                       else {"status": "pending", "reason": "Earthdata login works; fetch not finished (backend/nasa)"})
        if k == "hls" and k in x.nasa:
            datasets[k]["also"] = f"data/cache/{p}/hls_lpdaac.parquet (NASA LP DAAC, 2016-2019 and 2026)"
    ch = {k: v for k, v in x.hist["by_year"].items()}
    loc = {
        "id": p, "name": NAMES[p], "dwr_unique_id": bs.get("dwr_unique_id"), "region_adapter": "ca", "regime": fix["regime"], "state_fips": "06", "county_fips": COUNTY[p],
        "geometry": x.poly["geometry"], "centroid": props["centroid"], "area_ha": area, "crs_working": "EPSG:32610",
        "soil": soil, "terrain": terrain, "water": fix["water"], "market_preference": fix["market_preference"],
        "stations": stations,
        "regional_cell": {"grid": "POWER_MERRA2_0.5x0.625", "row": cell[0], "col": cell[1], "footprint": cell[2]},
        "datasets": datasets, "nasa_datasets": NB.nasa_datasets(p, x.nasa), "crop_history": ch, "observed_cover": observed, "events": fix["events"],
        "_notes": {"water_and_market": "water.* and market_preference are spec statements marked U (see fixtures); not looked up",
                   "boundary": props["boundary_source"]["title"],
                   "terrain": (f"NASADEM via backend/nasa_open/out/{p}/terrain.json (smoothed 150 m; raw values there as *_raw)" if nasadem else "no DEM"), "cdl_majority_by_year": "see crop_history (CDL)"},
    }
    write(p, "location.json", loc)
    return loc


# ------------------------------------------------------------------ daily + weekly features
def cover_by_date(x: Ctx):
    cls, ndvi = {}, {}
    for y in x.cal["years"]:
        for seg in y["segments"]:
            for d in pd.date_range(seg["start"], seg["end"]):
                cls[d] = seg["class"]
        for o in y["observations"]:
            ndvi.setdefault(pd.Timestamp(o["date"]), []).append(o)
    return cls, ndvi


def build_daily(x: Ctx):
    d = x.ext[x.ext.date >= DAILY_FROM].set_index("date")
    st = x.station_daily
    cls, obs = cover_by_date(x)
    rows = []
    for dt_, row in d.iterrows():
        o = obs.get(dt_)
        ndv = float(np.mean([a["ndvi"] for a in o if a.get("ndvi") is not None])) if o else None
        rows.append({
            "date": dt_.strftime("%Y-%m-%d"), "tmax_c": r(row.T2M_MAX), "tmin_c": r(row.T2M_MIN), "precip_mm": r(row.PRECTOTCORR),
            "eto_mm": r(row.eto_hargreaves_mm), "ndvi": r(ndv, 3),
            "cover_class": cls.get(dt_) or x.hls_cover.get(dt_, "unknown"),
            "cover_source": "s2_landsat" if dt_ in cls else ("hls" if dt_ in x.hls_cover else None),
            "power_run": row.power_run, **NB.daily_extra(x.nasa, dt_),
            "ncei_tmax_c": r(st.tmax_c.get(dt_)), "ncei_tmin_c": r(st.tmin_c.get(dt_)), "ncei_precip_mm": r(st.prcp_mm.get(dt_)),
            "heatwave_day": bool(row.heatwave_day), "severe_heat_40c": bool(row.severe_heat),
        })
    write(x.p, "daily.json", {
        "location_id": x.p, "from": rows[0]["date"], "to": rows[-1]["date"],
        "sources": {"power": x.src_power, "ncei": x.src_ncei,
                    **{k: NB.src(k) for k in ("imerg", "smap_l4", "smap_l3", "grace") if k in x.nasa},
                    "eto": {"id": "hargreaves_fao56_eq52", "title": "Hargreaves ETo (FAO-56 eq. 52) on POWER Tmax/Tmin, backend/regional", "url": "https://www.fao.org/3/x0490e/x0490e07.htm", "accessed": ACCESSED, "verified": True},
                    "cover_class_ndvi": {"id": "s2_landsat_rule", "title": "Rule-based class from Sentinel-2/Landsat NDVI/NDWI (backend/field); NDVI shown only on observation days, not interpolated", "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", "accessed": ACCESSED, "verified": True}},
        "notes": ["imerg_precip_mm = NASA GPM IMERG daily rain at the field's 0.1 deg cell (imerg_run 'final' or 'late'); "
                  "smap_sm_pct = SMAP L4 root-zone soil-moisture percentile (product sm_rootzone_pctl, daily mean of 3-hourly); "
                  "smap_rootzone_m3m3 its volumetric value; smap_l3_sm_m3m3 = SMAP L3 surface retrieval, recommended quality only; "
                  "grace_gw_pct = GRACE-DA groundwater percentile of the week containing the day. Null = not available that day.",
                  "Rows after 2025-12-31 use NASA POWER near-real-time values (power_run 'nrt', data/cache/<id>/power_nrt.parquet) "
                  "with the same Hargreaves ETo and heat rules; NOAA station columns are null there (station cache ends earlier).",
                  "cover_class after the Sentinel-2/Landsat calendar ends comes from the HLS calendar (cover_source 'hls').",
                  "cover_class is 'unknown' before 2016 (no satellite classification) and across gaps > 30 days",
                  "ncei_* = mean over the selected NCEI stations, null where no station reported; precip/temps are not the same quantity as POWER (50 km reanalysis vs points)",
                  "POWER Tmax runs warm vs NCEI stations in summer (see /validation); severe_heat_40c / heatwave_day inherit that bias"],
        "rows": rows})


def build_weekly(x: Ctx):
    cls, obs = cover_by_date(x)
    d = x.ext.set_index("date")
    d = d[d.index >= "2016-01-01"]
    us = x.usdm[(x.usdm.fips == FIPS[x.p])]
    cum, cat = us[us.stat == "cumulative"].sort_values("map_date"), us[us.stat == "categorical"]
    o = pd.DataFrame([{"date": pd.Timestamp(a["date"]), "ndvi": a["ndvi"], "bsi": a.get("bsi")} for y in x.cal["years"] for a in y["observations"]])
    o["week"] = o.date.dt.to_period("W-SUN").dt.start_time
    ow = o.groupby("week").agg(ndvi_median=("ndvi", "median"), ndvi_p10=("ndvi", lambda s: s.quantile(.1)), ndvi_p90=("ndvi", lambda s: s.quantile(.9)), bsi=("bsi", "median"))
    wk = d.index.to_period("W-SUN").start_time
    g = d.groupby(wk)
    rows = []
    for w, df in g:
        if len(df) < 7:
            continue
        iso = w.isocalendar()
        u = cum[cum.map_date <= w + pd.Timedelta(days=6)].tail(1)
        usc = None
        if len(u):
            u = u.iloc[0]
            usc = "None"
            for k, col in (("D0", "d0"), ("D1", "d1"), ("D2", "d2"), ("D3", "d3"), ("D4", "d4")):
                if u[col] >= 50:
                    usc = k
        rw = ow.loc[w] if w in ow.index else None
        rows.append({
            "week_start": w.strftime("%Y-%m-%d"), "iso_year": int(iso.year), "iso_week": int(iso.week),
            "ndvi_median": r(rw.ndvi_median, 3) if rw is not None else None, "ndvi_p10": r(rw.ndvi_p10, 3) if rw is not None else None,
            "ndvi_p90": r(rw.ndvi_p90, 3) if rw is not None else None, "bsi": r(rw.bsi, 3) if rw is not None else None,
            "nbr2": None, "lst_anomaly_k": None, "esi": None, "openet_et_mm_month": None, "smap_sm": None, "smap_sm_pct": None,
            "imerg_7d_mm": None, "power_tmax_c": r(df.T2M_MAX.mean()), "power_tmin_c": r(df.T2M_MIN.mean()),
            "power_eto_mm": r(df.eto_hargreaves_mm.sum()), "grace_sfsm_pct": None, "grace_rzsm_pct": None, "grace_gws_pct": None,
            "modis_ndvi_anomaly": None, "usdm_category": usc})
        rows[-1].update({k: v for k, v in NB.weekly_extra(x.nasa, w).items()})
    write(x.p, "features_weekly.json", {
        "location_id": x.p,
        "sources": {"power": x.src_power, "usdm": x.src_usdm, **{k: NB.src(k) for k in ("imerg", "smap_l4", "grace", "modis", "ecostress") if k in x.nasa}},
        "notes": ["weeks start Monday; ndvi_* are over the Sentinel-2/Landsat observations in that week (null if none), p10/p90 are across observations not pixels",
                  "power_tmax_c/tmin_c weekly means, power_eto_mm weekly sum (Hargreaves)",
                  "usdm_category = highest category with >= 50% of the county in that category or worse (county " + FIPS[x.p] + ")",
                  "NASA columns: imerg_7d_mm (IMERG week total), smap_sm / smap_sm_pct (SMAP L4 root zone m3/m3 / percentile), "
                  "grace_*_pct (GRACE-DA percentiles), modis_ndvi_anomaly (latest 16-day composite vs 2000-2025), esi (ECOSTRESS, clear scenes). "
                  "Null = no observation that week or dataset not cached yet; nbr2, lst_anomaly_k and openet_et_mm_month are not filled."],
        "rows": rows})


# ------------------------------------------------------------------ trends
def trend_file(x: Ctx, layer: str, unit: str, grid: str, source: dict, by_year: dict, note: str, default_year: int):
    years = sorted(by_year)
    series = [{"year": int(y), "value": by_year[y]} for y in years]
    markers = [{"date": e["date"], "title": e["title"], "url": e["url"], "verified": e["verified"]} for e in jload(ROOT / "fixtures" / x.p / "location.json")["events"]]
    write(x.p, f"trends_{layer}.json", {
        "location_id": x.p, "layer": layer, "unit": unit, "grid": grid, "source": source, "note": note,
        "default_year": default_year, "years": [int(y) for y in years],
        "by_year": {y: [{"row": 0, "col": 0, "value": v}] for y, v in by_year.items()},
        "field_cell_series": series, "event_markers": markers})


def build_trends(x: Ctx):
    d = x.derived.copy()
    d["year"] = d.date.dt.year
    cellid = "POWER_MERRA2_0.5x0.625"
    # heatwave days per calendar year (>=3 consecutive days with Tmax >= 35 C), POWER
    hw = d.groupby("year").heatwave_day.sum()
    trend_file(x, "heatwave_days", "days/yr", cellid, x.src_power, {str(y): int(v) for y, v in hw.items()},
               "Days per calendar year inside a >=3-day run of POWER Tmax >= 35 C (backend/regional risk rule, thresholds U). "
               "One grid cell only: POWER MERRA-2 0.5x0.625 deg, so `cells` has a single entry (row 0, col 0). "
               "POWER Tmax runs warm vs NCEI stations in summer (see /validation), so counts are likely high.", 2025)
    # precip anomaly vs 1991-2020 calendar-year mean, %
    pr = d.groupby("year").PRECTOTCORR.sum()
    base = pr.loc[1991:2020].mean()
    trend_file(x, "precip_anomaly", "% of 1991-2020 mean", cellid, x.src_power, {str(y): r((v / base - 1) * 100, 1) for y, v in pr.items()},
               f"Calendar-year POWER PRECTOTCORR total vs its 1991-2020 mean ({base:.0f} mm). POWER rain is a ~50 km reanalysis; "
               "station totals are lower (see /validation). 2025 is a full year in the cache.", 2025)
    # USDM weeks with >= 50 % of the county in D2 or worse
    us = x.usdm[(x.usdm.fips == FIPS[x.p]) & (x.usdm.stat == "cumulative")].copy()
    us["year"] = us.map_date.dt.year
    w = us[us.d2 >= 50].groupby("year").size().reindex(range(2015, 2026), fill_value=0)
    trend_file(x, "usdm_d2_weeks", "weeks/yr", "county_" + FIPS[x.p], x.src_usdm, {str(y): int(v) for y, v in w.items()},
               f"Weeks per year (by USDM map date) with >= 50% of county {FIPS[x.p]} in D2 (severe drought) or worse. "
               "County statistic, not a grid; `cells` has one entry. The 50% cut-off is ours (U).", 2022)
    # reservoir storage: mean of daily storage, thousand acre-feet, summed over the preset's reservoirs
    stns = jload(ROOT / "fixtures" / x.p / "location.json")["water"]["cdec_stations"]
    c = x.cdec[x.cdec.station.isin(stns)].copy()
    c["year"] = c.date.dt.year
    s = c.groupby(["year", "station"]).storage_af.mean().unstack().sum(axis=1) / 1000
    for layer, (unit, grid, source, by, note, dy) in NB.trends(x.nasa).items():
        trend_file(x, layer, unit, grid, source, {k: v for k, v in by.items()}, note, dy)
    trend_file(x, "reservoir_storage", "thousand acre-ft (annual mean)", "cdec_" + "_".join(stns), x.src_cdec,
               {str(y): r(v, 1) for y, v in s.items()},
               f"Annual mean of daily CDEC storage (sensor 15), summed over {', '.join(stns)}. Absolute storage, not % of capacity "
               "(capacity not fetched). Reservoirs are context, not the field's own water supply (water source is a spec item, U).", 2022)


# ------------------------------------------------------------------ validation
def monthly_compare(x: Ctx):
    pw = x.power.set_index("date")
    st = x.station_daily
    j = pd.DataFrame({"p_pr": pw.PRECTOTCORR, "p_tx": pw.T2M_MAX, "p_tn": pw.T2M_MIN}).join(st, how="inner")
    j["m"] = j.index.to_period("M")
    out = {}
    for name, pc, nc, agg in (("precip", "p_pr", "prcp_mm", "sum"), ("tmax", "p_tx", "tmax_c", "mean"), ("tmin", "p_tn", "tmin_c", "mean")):
        g = j.groupby("m")
        ok = g[nc].count() >= 27      # >= ~90% of days observed
        a = getattr(g[pc], agg)()[ok]
        b = getattr(g[nc], agg)()[ok]
        out[name] = pd.DataFrame({"power": a, "ncei": b})
    return out


def stats(df: pd.DataFrame, pct: bool):
    diff = df.power - df.ncei
    rr = float(np.corrcoef(df.power, df.ncei)[0, 1] ** 2)
    res = {"n_months": int(len(df)), "bias": float(diff.mean()), "rmse": float(np.sqrt((diff ** 2).mean())), "r2": rr}
    if pct:
        res["bias_pct"] = float(diff.sum() / df.ncei.sum() * 100)
    return res


def build_validation(x: Ctx):
    mc = monthly_compare(x)
    checks = []
    nst = len(x.nmeta["selected_stations"])
    meta_note = f"POWER point (0.5 deg cell) vs mean of {nst} NCEI stations ({', '.join(s['station'] for s in x.nmeta['selected_stations'])}); months with >= 27 station-mean days; {mc['precip'].index.min()}..{mc['precip'].index.max()}. Bias = POWER minus stations."
    for cid, key, title, unit, pct in (("power_vs_ncei_precip", "precip", "POWER vs NCEI station rain (monthly totals)", "mm/month", True),
                                       ("power_vs_ncei_tmax", "tmax", "POWER vs NCEI station Tmax (monthly means)", "degC", False),
                                       ("power_vs_ncei_tmin", "tmin", "POWER vs NCEI station Tmin (monthly means)", "degC", False)):
        df = mc[key]
        s = stats(df, pct)
        src = x.src_ncei
        met = {"bias": sn(s["bias"], unit, src, "POWER - stations, mean over months"),
               "rmse": sn(s["rmse"], unit, src, "root mean square difference of monthly values"),
               "r2": sn(s["r2"], "", src, "squared correlation of monthly values"),
               "n_months": sn(s["n_months"], "months", src, "months compared")}
        if pct:
            met["bias_pct"] = sn(s["bias_pct"], "%", src, "total POWER rain vs total station rain")
        by_cal = []
        for mth in range(1, 13):
            dm = df[df.index.month == mth]
            by_cal.append({"month": mth, "bias": r((dm.power - dm.ncei).mean(), 2), "power_mean": r(dm.power.mean(), 2), "ncei_mean": r(dm.ncei.mean(), 2)})
        checks.append({"id": cid, "title": title, "status": "computed", "metrics": met, "note": meta_note, "by_calendar_month": by_cal,
                       "series": [{"month": str(k), "power": r(v.power), "ncei": r(v.ncei)} for k, v in df.tail(120).iterrows()]})
    # >= 40 C days per year: POWER vs each station (the flagged 2022 Colusa number)
    pw = x.power.assign(year=x.power.date.dt.year)
    nn = x.ncei.assign(year=x.ncei.date.dt.year)
    rows = []
    for y in range(2015, 2026):
        row = {"year": y, "power_days_ge_40c": int((pw[pw.year == y].T2M_MAX >= 40).sum()), "stations": {}}
        for sid, g in nn[nn.year == y].groupby("station"):
            row["stations"][sid] = {"days_ge_40c": int((g.tmax_c >= 40).sum()), "tmax_days_observed": int(g.tmax_c.notna().sum())}
        rows.append(row)
    y22 = next(q for q in rows if q["year"] == 2022)
    checks.append({"id": "power_vs_ncei_heat40", "title": "Days >= 40 C per year, POWER vs each NCEI station", "status": "computed",
                   "metrics": {"power_days_2022": sn(y22["power_days_ge_40c"], "days", x.src_power, "POWER Tmax >= 40 C in 2022"),
                               "station_max_days_2022": sn(max(v["days_ge_40c"] for v in y22["stations"].values()), "days", x.src_ncei,
                                                           "highest station count in 2022 (stations with <330 observed days understate)")},
                   "note": "Station counts are of observed days only; a station with missing days can undercount. " + meta_note, "by_year": rows})
    blocked = lambda cid, title, why: {"id": cid, "title": title, "status": "blocked",  # noqa: E731
                                       "metrics": {"bias_pct": blocked_sn("%", why), "r2": blocked_sn("", why)}, "note": f"blocked: {why}"}
    nasa_checks = NB.validation_checks(x.nasa, x.station_daily, x.ext[["date", "PRECTOTCORR"]], sn, x.src_ncei, x.src_power)
    checks += nasa_checks
    if not nasa_checks:
        checks.append(blocked("station_vs_imerg", "Station rain vs IMERG", "IMERG not cached yet (backend/nasa/fetch_imerg.py)"))
    checks.append(openet_check(x) or blocked("openet_vs_etc", "OpenET vs modelled ETc", "needs OpenET API key"))
    checks.append(blocked("cimis_vs_power", "CIMIS vs NASA POWER ETo", "needs CIMIS appKey"))
    write(x.p, "validation.json", {"location_id": x.p, "checks": checks})


def openet_check(x: Ctx):
    """Copy the engine's baseline OpenET comparison (backend/engine strategies water.etc_vs_openet_pct)."""
    f = ROOT / "backend/engine/out" / x.p / "strategies.json"
    if not f.exists():
        return None
    items = jload(f)
    items = items if isinstance(items, list) else items.get("items", [])
    base = next((s for s in items if s.get("is_baseline")), None)
    w = (base or {}).get("water", {})
    if "etc_vs_openet_pct" not in w:
        return None
    met = {"bias_pct": w["etc_vs_openet_pct"]}
    if "openet_et_mm_season" in w:
        met["openet_et_mm"] = w["openet_et_mm_season"]
    return {"id": "openet_vs_etc", "title": "OpenET measured ET vs the engine's modelled crop water use (baseline rotation)",
            "status": "computed", "metrics": met, "note": w["etc_vs_openet_pct"].get("note", "")}


# ------------------------------------------------------------------ nasa series + bc
def build_nasa_series(x: Ctx):
    write(x.p, "nasa_series.json", NB.nasa_series(x.p, x.nasa))
    ws = NB.water_seen(x.p, x.nasa)
    if ws:
        write(x.p, "water_seen.json", ws)


# ------------------------------------------------------------------ zones
def build_zones(x: Ctx):
    g = jload(ROOT / "backend/field/out" / x.p / "grid.geojson")
    feats = [f for f in g["features"] if f["properties"]["frac_in_field"] >= 0.5]
    keys = [f"ndvi_{y}_q3" for y in range(2016, 2026)]      # Jul-Sep Sentinel-2 median per year
    vals = []
    for f in feats:
        v = [f["properties"].get(k) for k in keys]
        v = [a for a in v if a is not None]
        vals.append(float(np.mean(v)) if v else None)
    ok = [v for v in vals if v is not None]
    cut, fmean = float(np.percentile(ok, 10)), float(np.mean(ok))
    out = []
    for f, v in zip(feats, vals):
        if v is not None and v <= cut:
            out.append({"type": "Feature", "geometry": f["geometry"], "properties": {
                "layer": "stress_hotspot", "meaningful": True, "label": "lowest-decile mean Jul-Sep NDVI, 2016-2025 (U)",
                "value": sn(v, "NDVI", g["source"], f"cell {f['properties']['cell_id']} mean of yearly Q3 median NDVI; field mean {fmean:.3f}; 10th-percentile cut {cut:.3f}. "
                            "Shows where the crop is weaker on average, not why (rule of thumb, U)."),
                "cell_id": f["properties"]["cell_id"]}})
    field = x.poly["geometry"]
    for lay, lab in (("slope", "slope class"), ("low_spot", "low spot (>= 1 m below 300 m focal mean) (U)")):
        out.append({"type": "Feature", "geometry": field, "properties": {
            "layer": lay, "meaningful": False, "label": lab, "value": blocked_sn("", "no DEM fetched"),
            "note": "blocked: needs a DEM (NASADEM needs Earthdata; 3DEP not fetched)"}})
    write(x.p, "zones.json", {"location_id": x.p, "type": "FeatureCollection", "source": g["source"], "features": out,
                              "notes": [f"{len(out) - 2} stress-hotspot cells out of {len(feats)} 30 m cells with >= 50% inside the field",
                                        "openet_zone: blocked (needs OpenET key). Full 30 m NDVI grid: GET /api/locations/{id}/grid"]})


def main():
    ids = sys.argv[1:] or PRESETS
    for p in ids:
        x = Ctx(p)
        build_location(x)
        build_daily(x)
        build_weekly(x)
        build_trends(x)
        build_validation(x)
        build_zones(x)
        build_nasa_series(x)
        print(f"{p}: wrote {sorted(f.name for f in (OUT / p).iterdir())}")
    bc = NB.bc_signal()
    if bc:
        (OUT / "bc_signal.json").write_text(json.dumps(clean(bc), separators=(",", ":"), allow_nan=False))
        print("wrote bc_signal.json")


if __name__ == "__main__":
    main()
