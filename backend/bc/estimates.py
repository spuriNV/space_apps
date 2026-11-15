"""Estimates for the routes California serves from US-only data (OpenET, RMA, CPC/USDM/CDEC, backend/ai, OPERA DSWx).

Every payload here keeps the California response shape, so the frontend reads it the same way, but it is an estimate:
values are SourcedNumbers with method "assumed" (U) and a note saying how they were estimated, each payload carries
`estimate_note`, and the API answers these routes with `_source: "estimate"` (backend/api/app/main.py, REGION_GAPS).

Called by build_api.py (backend/api venv; no network). Inputs: ECCC stations, POWER, IMERG, GRACE, the backend/field
S2/Landsat calendar and caches, the engine (per-year FAO-56 ETc) and engine strategies.json.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from statistics import NormalDist

import numpy as np
import pandas as pd

TODAY = "2026-11-15"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
AF_MM = 304.8  # mm per acre-ft/acre
EST = "Estimate (U): "
D_PCT = (("D4", 2), ("D3", 5), ("D2", 10), ("D1", 20), ("D0", 30))  # USDM percentile guide: category at or below
ENGINE_SRC = {"id": "fieldshift_engine_etc", "title": "CropLytics rotation engine: FAO-56 crop ET (ETc) of today's rotation, "
              "Penman-Monteith ETo on ECCC station temperatures and POWER radiation, humidity and wind",
              "url": "urn:fieldshift:engine", "accessed": TODAY, "verified": False}


def _src(sid: str, title: str, url: str, accessed: str = TODAY, verified: bool = False) -> dict:
    return {"id": sid, "title": title, "url": url, "accessed": accessed, "verified": verified}


def _sn(value, unit, source, note, low=None, high=None) -> dict:
    r = lambda v: None if v is None or not np.isfinite(float(v)) else round(float(v), 3)  # noqa: E731
    d = {"value": r(value), "unit": unit, "low": r(low), "high": r(high), "method": "assumed", "verified": False, "note": EST + note}
    if value is not None:
        d["source"] = source
    return d


# ------------------------------------------------------------------ station climatology helpers
def station(x) -> pd.DataFrame:
    s = x.station_daily.copy()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))
    return s


def drought_pct(prcp: pd.Series) -> pd.Series:
    """Percentile (0-100) of the trailing 90-day station precipitation against 1991-2020 for the same time of year
    (+/- 7 days). Days with < 80 of 90 reports are NaN; shorter windows are scaled to 90 days."""
    n = prcp.rolling(90, min_periods=80).count()
    s90 = prcp.rolling(90, min_periods=80).sum() * 90 / n
    doy = s90.index.day_of_year.values
    clim = s90[(s90.index.year >= 1991) & (s90.index.year <= 2020)]
    cd, cv = clim.index.day_of_year.values, clim.values
    sorted_by_doy = {}
    for d in range(1, 367):
        dist = np.abs(((cd - d + 183) % 366) - 183)
        v = cv[(dist <= 7) & np.isfinite(cv)]
        sorted_by_doy[d] = np.sort(v)
    out = np.full(len(s90), np.nan)
    for i, (d, v) in enumerate(zip(doy, s90.values)):
        ref = sorted_by_doy[d]
        if np.isfinite(v) and len(ref) >= 100:
            out[i] = 100.0 * np.searchsorted(ref, v, side="right") / len(ref)
    return pd.Series(out, index=s90.index)


def d_cat(p: float | None) -> str | None:
    if p is None or not np.isfinite(p):
        return None
    for c, t in D_PCT:
        if p <= t:
            return c
    return None


DROUGHT_RULE = ("station drought index: percentile of the trailing 90-day precipitation (mean of the ECCC stations Salmon Arm CS "
                "and Silver Creek) against 1991-2020 for the same time of year; D0 <= 30th, D1 <= 20th, D2 <= 10th, D3 <= 5th, "
                "D4 <= 2nd percentile (the US Drought Monitor's percentile guide, applied to rain only). Not the US or Canadian "
                "Drought Monitor, which weigh many indicators and expert input.")


# ------------------------------------------------------------------ /openet
def openet(x, fid: str) -> dict:
    os.environ["FIELDSHIFT_FIELDS"] = ",".join(sorted({*filter(None, os.environ.get("FIELDSHIFT_FIELDS", "").split(",")), fid}))
    from rotation_engine import engine as E  # noqa: PLC0415  (backend/engine path dependency of the API venv)
    from rotation_engine.model import water_metrics  # noqa: PLC0415
    from rotation_engine.timeline import build_timeline  # noqa: PLC0415

    crops = E.load_crops()
    base = next(s for s in E.load_strategies(fid) if s["is_baseline"])
    tl = build_timeline(base, crops)
    rows = []
    for y in range(2015, 2026):
        try:
            m = water_metrics(tl, list(E.weather_years(fid, (y,), 0.0, 0.0)))
        except Exception:  # noqa: BLE001  incomplete weather year
            m = None
        if m is None:
            continue
        for i, v in enumerate(m["etc_month"]):
            rows.append({"date": f"{y}-{i + 1:02d}-01", "month": f"{y}-{i + 1:02d}", "et_mm": round(float(v), 1),
                         "et_in": round(float(v) / 25.4, 2), "model": "fieldshift_engine_fao56_etc"})
    years = {}
    for r_ in rows:
        years.setdefault(r_["date"][:4], []).append(r_["et_mm"])
    note = ("Estimated from the rotation engine (FAO-56 ETc on Salmon Arm station weather); OpenET does not cover BC. "
            f"Today's rotation ({base['id']}: {base['name']}), modelled crop coefficients, full water supply assumed, so the "
            "2023 and 2026 irrigation orders (which stopped forage irrigation from mid-August) are not reflected. A model, not a "
            "measurement: do not use it to check the engine.")
    return {"location_id": fid, "unit": "mm/month", "rows": rows,
            "annual": [{"year": int(y), "et_mm": round(sum(v), 0), "months": len(v)} for y, v in sorted(years.items())],
            "source": ENGINE_SRC, "note": note, "estimate_note": note, "strategy_id": base["id"]}


# ------------------------------------------------------------------ /insurance
def insurance(x, fid: str, src_eccc: dict) -> dict:
    s = station(x)
    s = s[(s.index.year >= 1991) & (s.index.year <= 2025)]
    jja = s[s.index.month.isin([6, 7, 8])]
    g = jja.groupby(jja.index.year)
    cov = g.prcp_mm.count()
    psum = g.prcp_mm.sum() * 92 / cov
    ok = cov[cov >= 83].index
    clim = psum.loc[[y for y in ok if 1991 <= y <= 2020]].mean()
    heat = s.tmax_c.ge(38).groupby(s.index.year).sum()
    gs = s[((s.index.month == 5) & (s.index.day >= 10)) | s.index.month.isin([6, 7, 8]) | ((s.index.month == 9) & (s.index.day <= 15))]
    frost = gs.tmin_c.le(-1).groupby(gs.index.year).sum()
    perils = {}
    for y in ok:
        p = []
        if psum[y] < 0.5 * clim:
            p.append("drought")
        if psum[y] > 1.5 * clim:
            p.append("excess_moisture")
        if heat.get(y, 0) >= 1:
            p.append("heat")
        if frost.get(y, 0) >= 1:
            p.append("other")
        perils[int(y)] = p
    n = {k: sum(k in v for v in perils.values()) for k in ("drought", "excess_moisture", "heat", "other")}
    tot = sum(n.values()) or 1
    yrs = sorted(perils)
    scope = "Salmon Arm stations"
    rule = {"drought": f"June-August station rain < 50% of the 1991-2020 mean ({clim:.0f} mm)",
            "excess_moisture": f"June-August station rain > 150% of that mean (rain at haying)",
            "heat": "a day with station Tmax >= 38 C (35 C is reached in most summers on the valley floor)",
            "other": "frost: a day with station Tmin <= -1 C between 10 May and 15 Sep (frost after green-up)"}
    note = (f"Estimated from station history: share of {tot} peril-years among {len(yrs)} complete summers ({yrs[0]}-{yrs[-1]}), "
            "not insurance payouts. BC Production Insurance loss data is not public at field or county level, and USDA RMA "
            "covers the United States only. Each year with a peril counts once per peril; the peril rules are assumptions (U).")
    sh = lambda k: _sn(n[k] / tot, "fraction of peril-years", src_eccc, f"{n[k]} of {tot} peril-years; {rule[k]}. {note}")  # noqa: E731
    prof = {"scope": scope, "crop": "forage", "commodity_names_matched": [], "total_indemnity_usd": None,
            "years_with_indemnity": [], "indemnity_by_year_usd": {},
            "years_with_peril": [y for y in yrs if perils[y]], "perils_by_year": {str(y): perils[y] for y in yrs if perils[y]},
            "peril_year_counts": n, "summers_counted": len(yrs),
            "shares": {f"share_{k}": sh(k) for k in ("drought", "excess_moisture", "heat", "other")},
            "raw_cause_shares": {"summer drought (station rain)": round(n["drought"] / tot, 4), "rain at haying (station rain)": round(n["excess_moisture"] / tot, 4),
                                 "heat (station Tmax)": round(n["heat"] / tot, 4), "growing-season frost (station Tmin)": round(n["other"] / tot, 4)},
            "share_peril_unattributed": 0.0,
            "caveat": "Weather-risk estimate, not insurance history and not a forecast. Dollar amounts are null: no BC loss data was read."}
    return {"preset_id": fid, "years": [yrs[0], yrs[-1]], "file_url_template": None, "page_url": src_eccc["url"], "layout_url": None,
            "grouping": {k: [v] if k != "other" else v for k, v in rule.items()},
            "profiles": {f"{scope}|forage": prof}, "source": src_eccc, "note": note, "estimate_note": note}


# ------------------------------------------------------------------ /outlook
SEASONS = ["NDJ", "DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO"]
MON = "JFMAMJJASOND"


def _season_months(code: str) -> list[int]:
    for i in range(12):
        if all(MON[(i + k) % 12] == code[k] for k in range(3)):
            return [(i + k) % 12 + 1 for k in range(3)]
    raise ValueError(code)


def outlook(x, fid: str, src_eccc: dict, loc: dict, strategies: list | None, dpct: pd.Series) -> dict:
    s = station(x)
    c = s[(s.index.year >= 1991) & (s.index.year <= 2020)]
    mon_p = c.prcp_mm.groupby([c.index.year, c.index.month]).agg(["sum", "count"])
    mon_p = mon_p[mon_p["count"] >= 25]
    mon_p = (mon_p["sum"] * 30.4 / mon_p["count"]).groupby(level=1).mean()
    mon_t = ((c.tmax_c + c.tmin_c) / 2).groupby(c.index.month).mean()
    clim_note = ("ECCC 1991-2020 station climatology for these months (computed here from the daily records of Salmon Arm CS "
                 "and Silver Creek, not the official ECCC Climate Normals). No seasonal outlook is built for BC, so every "
                 "category is 'equal chances': each tercile is taken as 33% likely.")
    seasons = []
    y0 = 2026
    for lead, code in enumerate(SEASONS, 1):
        ms = _season_months(code)
        start_y = y0 if lead == 1 else y0 + (1 if ms[0] < 11 else 0)
        end_y = start_y + (1 if ms[-1] < ms[0] else 0)
        valid = f"{code} {start_y}" + (f"-{end_y}" if end_y != start_y else "")
        pn = float(sum(mon_p[m] for m in ms))
        tn = float(np.mean([mon_t[m] for m in ms]))
        prob = lambda kind: _sn(33.3, "percent", src_eccc, f"Climatology: {kind} has no tilt here (equal chances). {clim_note}")  # noqa: E731
        seasons.append({"lead": lead, "season": code,
                        "temperature": {"category": "equal chances", "valid_season": valid, "issued": TODAY, "probability": prob("temperature"),
                                        "normal_mean_c": _sn(tn, "degC", src_eccc, f"1991-2020 station mean of daily (Tmax+Tmin)/2 over {code}."),
                                        "label": "Climatology, not a forecast"},
                        "precipitation": {"category": "equal chances", "valid_season": valid, "issued": TODAY, "probability": prob("precipitation"),
                                          "normal_total_mm": _sn(pn, "mm", src_eccc, f"1991-2020 station mean precipitation total over {code}."),
                                          "label": "Climatology, not a forecast"}})
    # drought now (station index)
    last = dpct.dropna()
    now_d, now_p = last.index[-1], float(last.iloc[-1])
    worst = d_cat(now_p)
    rank = [c_ for c_, _ in reversed(D_PCT)]  # D0..D4
    area = {c_: _sn(100.0 if worst and rank.index(c_) <= rank.index(worst) else 0.0, "% of county area", src_eccc,
                    f"Point estimate at the stations (100 = in this category or worse, 0 = not); {DROUGHT_RULE} "
                    f"90-day rain percentile on {now_d:%Y-%m-%d}: {now_p:.0f}.") for c_ in rank}
    hist = []
    for d in pd.date_range("2026-08-25", now_d, freq="W-TUE"):
        p = dpct.get(d)
        w = d_cat(p)
        hist.append({"map_date": f"{d:%Y-%m-%d}", **{c_: (100.0 if w and rank.index(c_) <= rank.index(w) else 0.0) for c_ in rank},
                     "rain_90d_percentile": None if p is None or not np.isfinite(p) else round(float(p), 1)})
    markers = []
    for o in [*loc["water_context"].get("orders", []), *[e for e in x.fn["water_timeline"] if len(e["date"]) == 10 and e["date"] >= "2026"]] if getattr(x, "fn", None) else loc["water_context"].get("orders", []):
        d = pd.Timestamp(o["date"])
        p = dpct.get(d)
        markers.append({"date": o["date"], "title": o["title"], "url": o.get("url"), "verified": o.get("verified", False),
                        "station_drought_category": d_cat(p) or "none", "rain_90d_percentile": None if p is None or not np.isfinite(p) else round(float(p), 1)})
    dm = {"county": "Columbia-Shuswap (station estimate)", "fips": loc["state_fips"] + loc["county_fips"], "map_date": f"{now_d:%Y-%m-%d}",
          "valid_end": f"{now_d:%Y-%m-%d}", "worst_category": f"{worst} (station estimate)" if worst else "None (no D0-D4, station estimate)",
          "worst_category_code": worst or "None", "area_in_category_percent": area,
          "area_none_percent": _sn(0.0 if worst else 100.0, "% of county area", src_eccc, "Point estimate at the stations. " + DROUGHT_RULE),
          "map_date_sn_url": None, "history_2026": hist, "drought_markers": markers, "source_url": src_eccc["url"],
          "fetched_at": src_eccc["accessed"], "verified": False, "method": DROUGHT_RULE}
    no_out = {"category": "No outlook (climatology)", "target": "", "issued": "", "url": None, "fetched_at": TODAY, "verified": False,
              "label": "No drought outlook is built for BC; climatology only"}
    # field expectations and irrigation from the engine
    oc = loc.get("observed_cover") or {}
    hist_y = (loc.get("crop_history") or {})
    cur = hist_y.get("2025") or "Pasture / Forages"
    strat = []
    for st in strategies or []:
        I = st["water"]["irrigation_need_mm"]
        v, lo, hi = (I.get(k) for k in ("value", "low", "high"))
        strat.append({"id": st["id"], "name": st["name"], "is_baseline": st["is_baseline"],
                      "irrigation_need_af_ac": _sn(v / AF_MM, "acre-ft/acre/yr", ENGINE_SRC,
                                                   "Engine irrigation need under climatology (no outlook for BC, so every scenario "
                                                   "is the 2015-2025 mean weather); low/high = the engine's own parameter range.",
                                                   low=lo / AF_MM if lo is not None else None, high=hi / AF_MM if hi is not None else None),
                      "engine_param_range": {"low": round(lo / AF_MM, 2) if lo is not None else None, "high": round(hi / AF_MM, 2) if hi is not None else None},
                      "scenario_values": {k: round(v / AF_MM, 2) for k in ("low", "mid", "high")}, "change_vs_default_pct": 0.0,
                      "allocation_check": {"status": "no_allocation_entered", "allocation_mm": None}})
    summary = (f"No seasonal outlook is built for BC, so this shows climatology: the 1991-2020 station normals for the coming "
               f"seasons, with equal chances of wetter, normal or drier. Station drought estimate on {now_d:%d %b %Y}: "
               f"{(worst + ' (rain-only index)') if worst else 'no drought'}; the last 90 days' rain sits at the {now_p:.0f}th "
               "percentile for the time of year. Fish population protection orders stopped forage irrigation on the Salmon River "
               "in Aug 2023 and again in Aug 2026.")
    note = ("Estimated from station climatology: ECCC 1991-2020 normals for the coming seasons (equal chances) and a station "
            "rain-percentile drought index; no NOAA CPC, US Drought Monitor or CDEC product covers BC.")
    return {
        "preset_id": fid, "label": "Climatology, not a forecast (no seasonal outlook is built for BC)", "generated_at": NOW,
        "county": "Columbia-Shuswap", "county_fips": loc["state_fips"] + loc["county_fips"], "today": TODAY,
        "coming_season": "winter 2026-27 and the 2027 growing season",
        "cpc_seasonal_outlook": {"point": {"lon": loc["centroid"]["lon"], "lat": loc["centroid"]["lat"]}, "machine_readable_sources": {},
                                 "note": clim_note, "issued": TODAY, "next_issue": "None: climatology does not change. ECCC seasonal forecasts exist but are not built in.",
                                 "seasons": seasons},
        "drought": {"us_drought_monitor": dm, "cpc_drought_outlook": {"seasonal": {**no_out, "target": "Jan 2027"}, "monthly": {**no_out, "target": "Dec 2026"}}},
        "reservoirs_now": {},
        "snowpack_runoff": None,
        "allocations_context": {"bc_water_orders": {"watershed": loc["water_context"].get("watershed"), "orders": markers,
                                                    "note": loc["water_context"].get("note"), "verified": True}},
        "field_expectations_from_history": {"current_crop": cur, "crop_note": "2025 AAFC ACI class assumed again in 2026",
                                            "bare_window": {"note": "No typical bare window: the S2/Landsat calendar shows the forage field covered "
                                                            "through the growing season" if not oc.get("typically_bare_doy_ranges") else
                                                            f"Typically bare (days of year): {oc['typically_bare_doy_ranges']}"},
                                            "scenario_inputs": {"method": "climatology (dT 0, dP 0): no outlook for BC", "dT_c": {"low": 0.0, "mid": 0.0, "high": 0.0},
                                                                "dP_pct": {"low": 0.0, "mid": 0.0, "high": 0.0}}},
        "irrigation_2027": {"scenarios": {k: {"dT_c": 0.0, "dP_pct": 0.0} for k in ("low", "mid", "high")},
                            "default_is": "climatology (dT 0, dP 0)",
                            "allocation_note": "No allocation for BC fields: water use is set by the licence and any fish population protection order.",
                            "strategies": strat},
        "plain_language_summary": summary,
        "blocked_or_not_yet_published": [
            {"item": "NOAA CPC 90-day and drought outlooks", "status": "US only; not available for BC", "url_tried": None},
            {"item": "ECCC seasonal forecast", "status": "exists, not built in", "url_tried": "https://weather.gc.ca/saisons/index_e.html"},
            {"item": "Canadian Drought Monitor (AAFC)", "status": "exists, not built in", "url_tried": "https://agriculture.canada.ca/en/agricultural-production/weather/canadian-drought-monitor"},
            {"item": "BC River Forecast Centre snow and water supply bulletin", "status": "exists, not built in", "url_tried": "https://www2.gov.bc.ca/gov/content/environment/air-land-water/water/drought-flooding-dikes-dams/river-forecast-centre"},
        ],
        "estimate_note": note,
    }


# ------------------------------------------------------------------ trends: usdm_d2_weeks, reservoir_storage
def usdm_d2_weeks(dpct: pd.Series) -> dict:
    by = {}
    for y in range(2015, 2027):
        wk = [dpct.get(d) for d in pd.date_range(f"{y}-01-01", f"{y}-12-31", freq="W-TUE") if d <= dpct.index[-1]]
        wk = [p for p in wk if p is not None and np.isfinite(p)]
        if len(wk) >= 26:
            by[str(y)] = int(sum(p <= 10 for p in wk))
    return by


def water_orders_by_year(x, loc: dict) -> tuple[dict, list]:
    ev = [e for e in (x.fn["water_timeline"] if getattr(x, "fn", None) else loc["water_context"].get("orders", []))
          if len(e["date"]) == 10 and ("order" in e["title"].lower()) and "rescinded" not in e["title"].lower()]
    by = {str(y): sum(e["date"].startswith(str(y)) for e in ev) for y in range(2015, 2027)}
    return by, [{k: e.get(k) for k in ("date", "title", "url", "verified")} for e in ev]


# ------------------------------------------------------------------ S2 SCL labels (this field only)
def scl_labels(cache) -> dict:
    f = cache / "s2.parquet"
    if not f.exists():
        return {}
    s2 = pd.read_parquet(f)
    out = {}
    for r in s2.itertuples():
        clear = (r.scl_4 or 0) + (r.scl_5 or 0) + (r.scl_6 or 0)
        if not r.clear_frac or r.clear_frac < 0.5 or clear <= 0:
            continue
        for lab, v in (("covered", r.scl_4), ("bare", r.scl_5), ("water", r.scl_6)):
            if (v or 0) / clear >= 0.8:
                out[str(r.date)[:10]] = lab
    return out


# ------------------------------------------------------------------ two-class calendar (/calendar_ml)
COVER_T = 0.275  # midpoint of the rule's 0.20 / 0.35 thresholds: the estimate has no thin-cover class


def _two(o) -> str:
    if o.get("class") == "water":
        return "water"
    return "covered" if (o.get("ndvi") or 0) >= COVER_T else "bare"


def _markers(obs: list[dict]) -> list[dict]:
    """green_up = first of 3 covered after bare/water; senescence_harvest = first of 2 non-covered after cover;
    a senescence followed by cover again within 45 days is a cutting (same logic as backend/ai, on these classes)."""
    out, state = [], None          # None (start), "bare", "covered", "cut" (waiting for regrowth)
    cls = [o["class"] for o in obs]
    for i in range(len(obs)):
        if state in (None, "bare") and cls[i:i + 3] == ["covered"] * 3:
            if state == "bare":
                out.append({"date": obs[i]["date"], "type": "green_up", "ndvi": obs[i].get("ndvi")})
            state = "covered"
        elif state == "covered" and len(cls[i:i + 2]) == 2 and all(c != "covered" for c in cls[i:i + 2]):
            back = next((o for o in obs[i + 2:] if o["class"] == "covered"), None)
            cut = back is not None and (pd.Timestamp(back["date"]) - pd.Timestamp(obs[i]["date"])).days <= 45
            out.append({"date": obs[i]["date"], "type": "cutting" if cut else "senescence_harvest", "ndvi": obs[i].get("ndvi")})
            state = "cut" if cut else "bare"
        elif state == "cut" and cls[i] == "covered":
            state = "covered"
        elif state is None and cls[i] != "covered":
            state = "bare"
    return out


def calendar_ml(x, fid: str, scl: dict) -> dict | None:
    if not x.cal:
        return None
    allobs = []
    for y in x.cal["years"]:
        for o in y["observations"]:
            if o.get("ndvi") is not None or o.get("class") == "water":
                allobs.append({**o, "rule_class": o.get("class"), "class_unsmoothed": _two(o)})
    allobs.sort(key=lambda o: o["date"])
    for i, o in enumerate(allobs):   # 3-observation centred mode
        win = [allobs[j]["class_unsmoothed"] for j in (i - 1, i, i + 1) if 0 <= j < len(allobs)]
        o["class"] = max(set(win), key=lambda c: (win.count(c), c == o["class_unsmoothed"]))
        o["s2_scl_class"] = scl.get(o["date"]) if o.get("sensor") == "s2" else None
    dates = pd.to_datetime([o["date"] for o in allobs])
    years = []
    for y in x.cal["years"]:
        yr = y["year"]
        days = pd.date_range(f"{yr}-01-01", f"{yr}-12-31")
        idx = np.searchsorted(dates.values, days.values)
        cls = []
        for d, k in zip(days, idx):
            prev = allobs[k - 1] if k > 0 else None
            nxt = allobs[k] if k < len(allobs) else None
            if nxt is not None and dates[k] == d:
                cls.append(nxt["class"]); continue
            if prev is None or nxt is None or (dates[k] - dates[k - 1]).days > 30:
                cls.append("unknown"); continue
            cls.append(prev["class"] if (d - dates[k - 1]) <= (dates[k] - d) else nxt["class"])
        segs, trans = [], []
        for i, (d, c) in enumerate(zip(days, cls)):
            if not segs or segs[-1]["class"] != c:
                if segs and c != "unknown":
                    last_known = next((s_["class"] for s_ in reversed(segs) if s_["class"] != "unknown"), None)
                    if last_known and last_known != c:
                        trans.append({"date": f"{d:%Y-%m-%d}", "from": last_known, "to": c, "after_unknown_gap": segs[-1]["class"] == "unknown"})
                segs.append({"start": f"{d:%Y-%m-%d}", "end": f"{d:%Y-%m-%d}", "start_doy": d.day_of_year, "end_doy": d.day_of_year, "days": 0, "class": c, "n_obs": 0})
            s_ = segs[-1]
            s_["end"], s_["end_doy"], s_["days"] = f"{d:%Y-%m-%d}", d.day_of_year, s_["days"] + 1
        yobs = [o for o in allobs if o["date"].startswith(str(yr))]
        for o in yobs:
            for s_ in segs:
                if s_["start"] <= o["date"] <= s_["end"]:
                    s_["n_obs"] += 1
        dis = [o for o in yobs if o["rule_class"] != o["class"]]
        years.append({"year": yr, "segments": segs, "transitions": trans, "markers": [m for m in _markers(allobs) if m["date"].startswith(str(yr))],
                      "summary": {"days_by_class": {c: cls.count(c) for c in ("unknown", "bare", "partial", "covered", "water")},
                                  "n_obs": len(yobs), "n_obs_s2": sum(o.get("sensor") == "s2" for o in yobs),
                                  "n_obs_landsat": sum(o.get("sensor") == "landsat" for o in yobs), "in_training_years": False,
                                  "disagreement_with_rule_obs_pct": round(100 * len(dis) / len(yobs), 1) if yobs else None,
                                  "rule_days_by_class": (y.get("summary") or {}).get("days_by_class")},
                      "observations": [{k: o.get(k) for k in ("date", "sensor", "ndvi", "ndwi", "bsi", "clear_frac", "class", "class_unsmoothed",
                                                              "rule_class", "s2_scl_class")} for o in yobs]})
    n_dis = sum(o["rule_class"] != o["class"] for o in allobs)
    note = ("Estimated from the rule-based S2/Landsat calendar (backend/field calendar.json): no machine-learning model was run "
            f"on this BC field (the California models were trained on Kings and Colusa). Two classes plus water: NDVI >= {COVER_T} "
            "covered, else bare (the rule's 0.20/0.35 thresholds split at their midpoint, so it has no thin-cover class); "
            "3-observation centred mode; gaps <= 30 days filled from the nearest observation, longer gaps unknown.")
    return {"preset_id": fid, "generated_at": NOW, "detector": "two_class_ndvi_estimate",
            "classes": {"unknown": {"label": "No clear observation within 30 days", "color": "#bdbdbd", "pattern": "hatched"},
                        "bare": {"label": f"Bare (estimate: NDVI < {COVER_T})", "color": "#8c6d46"},
                        "partial": {"label": "Thin cover (rule only; the estimate has no partial class)", "color": "#b8d98b"},
                        "covered": {"label": f"Covered (estimate: NDVI >= {COVER_T})", "color": "#2e7d32"},
                        "water": {"label": "Water (rule: NDWI > 0.3 or water mask)", "color": "#2b7bba"}},
            "method": {"model": "none: NDVI threshold rule (estimate), not machine learning", "trained_on": "nothing (no training)",
                       "model_from": None, "labels": "none", "features": ["ndvi", "ndwi"],
                       "observations": "backend/field calendar.json observations (Sentinel-2 L2A and Landsat C2 L2)",
                       "smoothing": "3-observation centred mode", "daily_fill": "nearest observation within gaps <= 30 days; longer gaps unknown",
                       "markers": "green_up = first of 3 covered after bare/water; senescence_harvest = first of 2 non-covered after cover; cutting = cover back within 45 days",
                       "out_of_sample_years": [], "out_of_sample_field": True, "out_of_region": True, "forward_years": [],
                       "note": note},
            "data_through": x.cal.get("data_through"), "sources": x.cal.get("sources", []),
            "disagreement_with_rule_obs_pct": round(100 * n_dis / len(allobs), 1) if allobs else None,
            "field_evaluation": {}, "years": years, "estimate_note": note}


def transitions(fid: str, cal_ml: dict, rule_cal: dict, scl: dict) -> dict:
    rule = sorted(({"date": m["date"], "type": m["type"]} for y in rule_cal["years"] for m in y.get("markers", [])), key=lambda m: m["date"])
    est = sorted(({"date": m["date"], "type": m["type"]} for y in cal_ml["years"] for m in y["markers"]), key=lambda m: m["date"])
    ref_obs = sorted(({"date": d, "class": c} for d, c in scl.items()), key=lambda o: o["date"])
    ref = [{"date": m["date"], "type": m["type"]} for m in _markers(ref_obs)]

    def ev(ms):
        used, errs = set(), []
        for m in ms:
            best = None
            for j, r_ in enumerate(ref):
                if j in used or r_["type"] != m["type"]:
                    continue
                dd = abs((pd.Timestamp(r_["date"]) - pd.Timestamp(m["date"])).days)
                if dd <= 30 and (best is None or dd < best[1]):
                    best = (j, dd)
            if best:
                used.add(best[0]); errs.append(best[1])
        return {"transition_mae_vs_scl_days": float(np.mean(errs)) if errs else None, "transitions_matched": len(errs), "transitions_reference": len(ref)}
    note = ("Estimated: rule-based transitions from the S2/Landsat calendar (backend/field) and the two-class estimate; no "
            "machine-learning detector was run on this BC field. s2_scl_reference = the same logic on this field's Sentinel-2 "
            "scene classes (>= 80% of clear pixels): agreement, not ground truth.")
    return {"field_id": fid, "generated_at": NOW, "model_from": None,
            "types": {"green_up": "first of 3 covered dates after bare or water", "senescence_harvest": "first of 2 non-covered dates after cover",
                      "cutting": "hay: cover drops and is back within 45 days (not a harvest)"},
            "methods": {"rule_ndvi": rule, "two_class_ndvi_estimate": est, "s2_scl_reference": ref},
            "reference_note": "s2_scl_reference = the same logic on this field's Sentinel-2 SCL classes (>= 80% of clear pixels); agreement, not ground truth",
            "evaluation": {"rule_ndvi": ev(rule), "two_class_ndvi_estimate": ev(est)}, "estimate_note": note}


# ------------------------------------------------------------------ /stress
REASON = {"z_ndvi": "low greenness for the time of year (Sentinel-2/Landsat)", "z_sm": "dry soil (NASA GRACE-DA)",
          "z_eto": "very thirsty air (high reference evapotranspiration) (ECCC stations and NASA POWER)",
          "z_imerg30": "little rain in the last 30 days (NASA GPM IMERG)"}
SEASON_WEEKS = (14, 39)


def stress(x, fid: str, hist: dict | None) -> dict | None:
    if not x.cal:
        return None
    import nasa_build as NB  # noqa: PLC0415

    s = station(x)
    pw = x.power.set_index("date")
    tmax = s.tmax_c.combine_first(pw.T2M_MAX.reindex(s.index))
    tmin = s.tmin_c.combine_first(pw.T2M_MIN.reindex(s.index))
    eto = pd.Series(NB._hargreaves(tmax.values, tmin.values, x.pmeta["params"]["latitude"], s.index.day_of_year.values), index=s.index)
    im = x.nasa.get("imerg")
    im30 = im.precipitation.rolling("30D").sum() if im is not None else None
    gr = x.nasa.get("grace")
    obs = pd.DataFrame([{"date": pd.Timestamp(o["date"]), "ndvi": o.get("ndvi"), "sensor": o.get("sensor"), "cls": o.get("class")}
                        for y in x.cal["years"] for o in y["observations"]])
    by_y = (hist or {}).get("by_year") or {}
    rows = []
    for w in pd.date_range("2016-01-04", s.index[-1], freq="W-MON"):
        iso = w.isocalendar()
        if not SEASON_WEEKS[0] <= iso.week <= SEASON_WEEKS[1]:
            continue
        we = w + pd.Timedelta(days=6)
        o = obs[(obs.date >= w) & (obs.date <= we)]
        nd = o[o.ndvi.notna()]
        ndv = float(nd[nd.sensor == "s2"].ndvi.mean()) if (nd.sensor == "s2").any() else (float(nd.ndvi.mean()) if len(nd) else None)
        smp = None
        if gr is not None:
            g = gr.rtzsm_inst[(gr.index >= w - pd.Timedelta(days=6)) & (gr.index <= we)]
            smp = float(g.iloc[-1]) if len(g) else None
        crop = by_y.get(str(iso.year)) or by_y.get("2025")
        rows.append({"iso_year": int(iso.year), "iso_week": int(iso.week), "week_start": f"{w:%Y-%m-%d}", "crop": crop,
                     "crop_assumed": str(iso.year) not in by_y, "no_crop": False, "ndvi": None if ndv is None else round(ndv, 3),
                     "ndvi_sensor": (None if not len(nd) else ("s2" if (nd.sensor == "s2").any() else "landsat")),
                     "ndvi_modis": None, "ndvi_reference": "same field, other years",
                     "tmax_c": round(float(tmax[w:we].mean()), 1), "eto_mm_week": round(float(eto[w:we].sum()), 1),
                     "imerg_30d_mm": None if im30 is None or im30[:we].empty else round(float(im30[:we].iloc[-1]), 1),
                     "smap_pct": None if smp is None else round(smp, 1), "sm_source": "grace_da_rootzone_pctl" if smp is not None else None,
                     "water": bool((o.cls == "water").any())})
    df = pd.DataFrame(rows)

    def loyo(col):   # leave-one-year-out z vs the same ISO week +/- 1 in the other years
        z = np.full(len(df), np.nan)
        for i, r_ in df.iterrows():
            v = r_[col]
            if v is None or not np.isfinite(v):
                continue
            ref = df[(df.iso_year != r_.iso_year) & (abs(df.iso_week - r_.iso_week) <= 1)][col].dropna()
            if len(ref) >= 5 and ref.std() > 0:
                z[i] = (v - ref.mean()) / ref.std()
        return z
    for c_ in ("ndvi", "eto_mm_week", "imerg_30d_mm"):
        df[c_] = pd.to_numeric(df[c_], errors="coerce")
    df["z_ndvi"], df["z_eto"], df["z_imerg30"] = loyo("ndvi"), loyo("eto_mm_week"), loyo("imerg_30d_mm")
    nd_ = NormalDist()
    df["z_sm"] = [nd_.inv_cdf(min(max(p / 100, 0.01), 0.99)) if p is not None and np.isfinite(p) else np.nan for p in pd.to_numeric(df.smap_pct, errors="coerce")]
    weeks = []
    for r_ in df.to_dict("records"):
        z = {k: (None if not np.isfinite(r_[k]) else round(float(r_[k]), 2)) for k in ("z_ndvi", "z_sm", "z_eto", "z_imerg30")}
        comp_parts = [sgn * z[k] for k, sgn in (("z_ndvi", -1), ("z_sm", -1), ("z_eto", 1), ("z_imerg30", -1)) if z[k] is not None]
        comp = round(float(np.mean(comp_parts)), 2) if len(comp_parts) >= 2 else None
        two = sum([(z["z_ndvi"] or 0) < -1, (z["z_sm"] or 0) < -1, (z["z_eto"] or 0) > 1])
        evaluated = comp is not None and not r_["water"]
        flag = evaluated and ((comp is not None and comp > 1.0) or two >= 2)
        drivers = [k for k, sgn in (("z_ndvi", -1), ("z_sm", -1), ("z_eto", 1), ("z_imerg30", -1)) if z[k] is not None and sgn * z[k] > 1]
        weeks.append({**{k: r_[k] for k in ("iso_year", "iso_week", "week_start", "crop", "crop_assumed", "no_crop", "ndvi", "ndvi_sensor",
                                            "ndvi_modis", "ndvi_reference")},
                      "ndvi": None if r_["ndvi"] is None or not np.isfinite(r_["ndvi"]) else r_["ndvi"],
                      "z_ndvi": z["z_ndvi"], "z_lst": None, "z_esi": None, "z_sm": z["z_sm"], "z_eto": z["z_eto"], "z_imerg30": z["z_imerg30"],
                      "tmax_c": r_["tmax_c"], "eto_mm_week": r_["eto_mm_week"], "lst_minus_tmax_c": None, "lst_source": None, "esi": None,
                      "esi_source": None, "smap_pct": r_["smap_pct"], "sm_source": r_["sm_source"],
                      "imerg_30d_mm": None if r_["imerg_30d_mm"] is None or not np.isfinite(r_["imerg_30d_mm"]) else r_["imerg_30d_mm"],
                      "opera_water_frac": None, "usdm_d3plus_pct": None, "usdm_d3_event": None, "composite_z": comp, "if_score": None,
                      "water": r_["water"], "evaluated": evaluated, "flag_zscore": bool(flag), "flag_iforest": False,
                      "status": "water" if r_["water"] else ("one" if flag else "none"), "drivers": drivers if flag else [],
                      "reasons": [REASON[d] for d in drivers] if flag else []})
    note = ("Estimated with a z-score rule on this field's own series (S2/Landsat greenness, GRACE-DA root-zone soil moisture, "
            "station/POWER Hargreaves ETo, IMERG rain); the California-trained stress models (isolation forest) were not run "
            "here, so flag_iforest is always false and a flagged week shows as 'one'. No ECOSTRESS or MODIS LST is cached for BC.")
    return {"preset_id": fid, "generated_at": NOW, "season_iso_weeks": list(SEASON_WEEKS),
            "crop_years": {str(y): by_y.get(str(y)) or by_y.get("2025") for y in range(2016, int(s.index[-1].year) + 1)},
            "method": {"zscore": "composite = mean of the available (-z_ndvi, -z_sm, z_eto, -z_imerg30), at least two, > 1.0; or two of "
                                 "z_ndvi < -1, z_sm < -1, z_eto > +1. California method A uses NDVI, LST, ESI and soil moisture; LST and "
                                 "ESI are not cached for BC, so thirsty air (ETo) and 30-day rain stand in.",
                       "isolation_forest": "not run for BC (estimate)",
                       "z_scores": "leave-one-year-out vs the same ISO week +/- 1 in other years of this field; z_sm from the GRACE-DA percentile",
                       "status": "one / none (no second method); 'water' = water seen that week (never stress)",
                       "drivers": "keys of the z-scores beyond 1 in the stress direction; `reasons` says the same in words"},
            "inputs": {"tmax": "ECCC station mean (Salmon Arm CS, Silver Creek); NASA POWER T2M_MAX where no station reports",
                       "eto": "Hargreaves (FAO-56 eq. 52) on station Tmax/Tmin, POWER where missing",
                       "imerg": "NASA GPM IMERG V07 daily (backend/nasa imerg.parquet)",
                       "smap_pct": "GRACE-DA GRACEDADM_CLSM025GL_7D rtzsm_inst percentile (SMAP not cached for BC)",
                       "ndvi_hls": "field-median NDVI from backend/field calendar.json (Sentinel-2 first, then Landsat)"},
            "sources": [NB.src(k) for k in ("imerg", "grace") if k in x.nasa],
            "credit": "z-score composite and reasons follow backend/ai's stress method (spuriNV, ds branch); applied here as a rule, not the trained model.",
            "weeks": weeks, "estimate_note": note}


# ------------------------------------------------------------------ /models
def models(fid: str, cal_ml: dict | None, st: dict | None, rule_cal: dict | None, scl: dict) -> dict:
    items = []
    if cal_ml and rule_cal:
        rule_obs = {o["date"]: o["class"] for y in rule_cal["years"] for o in y["observations"] if o.get("sensor") == "s2"}
        est_obs = {o["date"]: o["class"] for y in cal_ml["years"] for o in y["observations"] if o.get("sensor") == "s2"}
        years = sorted({int(d[:4]) for d in scl})
        for mid, name, pred, feats in (("bare_rule_bc", "rule_ndvi (backend/field, 0.20/0.35)", rule_obs, ["ndvi", "ndwi"]),
                                       ("bare_twoclass_bc", f"two-class NDVI estimate ({COVER_T})", est_obs, ["ndvi", "ndwi"])):
            pairs = [(scl[d] == "covered", pred[d] == "covered") for d in scl if d in pred and scl[d] != "water"]
            tp = sum(a and b for a, b in pairs); tn = sum((not a) and (not b) for a, b in pairs)
            fp = sum((not a) and b for a, b in pairs); fn = sum(a and (not b) for a, b in pairs)
            n = len(pairs)
            f1b = (2 * tn / (2 * tn + fn + fp)) if tn else None   # bare = not covered is the positive class
            p22 = [(a, b) for (d, (a, b)) in zip([d for d in scl if d in pred and scl[d] != "water"], pairs) if d.startswith("2022")]
            items.append({"id": f"{mid}_{fid}_field_scl_estimate", "task": "bare_cover", "method": "rule_ndvi", "features": feats,
                          "labels": "s2_scl_pseudo (>= 80% of clear pixels; this field only)",
                          "split": {"type": "field_only", "train_years": [], "test_years": years},
                          "metrics": {"agreement_scl": round((tp + tn) / n, 4) if n else None, "n_scl": n,
                                      "f1_bare": round(f1b, 4) if f1b is not None else None,
                                      "accuracy_2022": round(sum(a == b for a, b in p22) / len(p22), 4) if p22 else None, "n_2022": len(p22)},
                          "confusion": [[tn, fp], [fn, tp]], "class_order": ["not_covered", "covered"], "feature_importance": [],
                          "disagreement_with": {}, "location_id": fid, "test": "field_scl_agreement",
                          "test_title": "Agreement with Sentinel-2 scene classes on this BC field (no training)",
                          "headline": mid == "bare_twoclass_bc", "badge": "estimate",
                          "notes": f"ESTIMATE, out of region: {name}. No California-trained model was run on this BC field. Scored against "
                                   "this field's own Sentinel-2 scene classes, which read the same reflectance: agreement, not accuracy. "
                                   "Rows of `confusion` = SCL label (not covered, covered), columns = prediction."})
    if st:
        ev = [w for w in st["weeks"] if w["evaluated"]]
        fl = [w for w in ev if w["flag_zscore"]]
        ja = lambda y: sum(1 for w in fl if w["iso_year"] == y and 27 <= w["iso_week"] <= 35)  # noqa: E731
        items.append({"id": f"stress_z_{fid}_estimate", "task": "stress_anomaly", "method": "zscore",
                      "features": ["z_ndvi", "z_sm", "z_eto", "z_imerg30"], "labels": "none (unsupervised); compared with the 2023 water-order summer",
                      "split": {"type": "unsupervised", "train_years": sorted({w["iso_year"] for w in ev}), "test_years": sorted({w["iso_year"] for w in ev})},
                      "metrics": {"weeks_scored": len(ev), "flag_rate": round(len(fl) / len(ev), 4) if ev else None,
                                  "julaug_2021_flagged_weeks": ja(2021), "julaug_2023_flagged_weeks": ja(2023), "julaug_2026_flagged_weeks": ja(2026)},
                      "feature_importance": [], "disagreement_with": {}, "location_id": fid, "badge": "estimate",
                      "notes": "ESTIMATE, out of region: z-score rule on this field's own series (see /stress method); the California "
                               "isolation forest was not run. No labelled stress events, so no accuracy."})
    note = ("Estimated: no California-trained model was run on this BC field. These reports describe the rule-based estimates "
            "served on /calendar_ml, /transitions and /stress, scored only against this field's own Sentinel-2 scene classes.")
    return {"location_id": fid, "generated_at": NOW, "source": "backend/bc/estimates.py (rule-based estimates, not backend/ai)",
            "headline_test": "field_scl_agreement", "items": items, "estimate_note": note}


# ------------------------------------------------------------------ /water_seen
def water_seen(fid: str, cache) -> dict | None:
    frames = []
    for name, sensor in (("s2", "s2"), ("landsat", "landsat")):
        f = cache / f"{name}.parquet"
        if f.exists():
            d = pd.read_parquet(f)
            d["sensor"] = sensor
            frames.append(d)
    if not frames:
        return None
    d = pd.concat(frames, ignore_index=True)
    d = d[d.clear_frac.fillna(0) > 0].copy()
    d["date"] = d.date.astype(str).str[:10]
    d = d[(d.date >= "2016-01-01")]
    d = d[pd.to_datetime(d.date).dt.month.between(3, 6)]
    scenes = []
    for r in d.sort_values(["date", "sensor"]).itertuples():
        wf = float(r.water_frac) if r.water_frac == r.water_frac else 0.0
        ndwi_water = r.ndwi_med == r.ndwi_med and r.ndwi_med > 0.3
        wf = min(max(wf, 0.0), 1.0)
        scenes.append({"date": r.date, "scene": r.scene_id, "sensor": r.sensor, "water_frac": round(wf, 3), "open_water_frac": round(wf, 3),
                       "partial_water_frac": 0.0, "cloud_snow_frac": round(1 - float(r.clear_frac), 3), "clear_frac": round(float(r.clear_frac), 3),
                       "ndwi_med": None if r.ndwi_med != r.ndwi_med else round(float(r.ndwi_med), 3), "ndwi_says_water": bool(ndwi_water),
                       "clear": bool(r.clear_frac >= 0.8)})
    seasons = []
    for y in sorted({s["date"][:4] for s in scenes}):
        cs = [s for s in scenes if s["date"].startswith(y) and s["clear"]]
        if not cs:
            continue
        wet = [s for s in cs if s["water_frac"] >= 0.5 or s["ndwi_says_water"]]
        seasons.append({"season": f"spring {y}", "clear_scenes": len(cs), "max_water_frac": max(s["water_frac"] for s in cs),
                        "scenes_over_half_water": sum(s["water_frac"] > 0.5 for s in cs), "first_wet": wet[0]["date"] if wet else None,
                        "last_wet": wet[-1]["date"] if wet else None, "water_seen": bool(wet)})
    seen = [s["season"] for s in seasons if s["water_seen"]]
    mx = max(seasons, key=lambda s: s["max_water_frac"]) if seasons else None
    summary = ((f"Sentinel-2/Landsat saw standing water on this field in {', '.join(seen)}. " if seen else
                f"In {len(seasons)} springs (Mar-Jun, {seasons[0]['season'][-4:]}-{seasons[-1]['season'][-4:]}) no clear Sentinel-2 or Landsat view showed the field flooded; ")
               + (f"the most water seen on a clear day was {mx['max_water_frac'] * 100:.0f}% of the field ({mx['season']}). " if mx else "")
               + "Estimate from the satellites' own water masks and NDWI, not NASA OPERA DSWx.")
    note = ("Estimated from the Sentinel-2 scene classification (water class) and the Landsat QA water bit, field share per scene "
            "(data/cache/<id>/s2.parquet, landsat.parquet), plus NDWI > 0.3 on the field median; NASA OPERA DSWx was not processed "
            "for this BC field. Spring (March-June: snowmelt and the Salmon River freshet) only, as for the California fields.")
    return {"location_id": fid, "rule": "clear = at least 80% of the field's pixels clear; water = S2 SCL water (class 6) or Landsat QA "
                                         "water share of the field; a spring counts as wet if a clear view is >= 50% water or its "
                                         "field-median NDWI > 0.3",
            "summary": summary, "seasons": seasons, "scenes": scenes,
            "source": _src("s2_landsat_water_mask", "Sentinel-2 L2A scene classification and Landsat C2 L2 QA water, field share per "
                           "scene (backend/field caches; estimate in place of OPERA DSWx)", "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a"),
            "fetched_at": NOW, "windows": [[f"{y}-03-01", f"{y}-06-30"] for y in sorted({s["date"][:4] for s in scenes})],
            "note": note, "estimate_note": note}
