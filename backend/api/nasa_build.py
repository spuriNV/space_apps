"""NASA layers for the API, built from the backend/nasa (Earthdata) and backend/nasa_open caches. No network.
Imported by build_real.py. Every value comes from a cache file; a dataset that is not cached is reported as
pending/blocked and its fields stay null.

Outputs (backend/api/out/<id>/): nasa_series.json (10-day steps), trends_{smap_anomaly,grace_gw_pct,modis_ndvi_anomaly}.json,
plus extra columns in daily/features_weekly/validation/location written by build_real.py with the helpers here.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"
ACCESSED = "2026-11-14"


def _pq(p: str, ds: str):
    f = CACHE / p / f"{ds}.parquet"
    if not f.exists():
        return None
    d = pd.read_parquet(f)
    if "date" in d.columns and isinstance(d["date"].dtype, pd.DatetimeTZDtype):
        d["date"] = d["date"].dt.tz_convert(None)
    return d


def _meta(p: str, ds: str) -> dict:
    f = CACHE / p / f"{ds}.meta.json"
    return json.loads(f.read_text()) if f.exists() else {}


def _num(x, n=3):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(x) else round(x, n)


SRC = {
    "imerg": {"id": "gpm_imerg", "title": "NASA GPM IMERG daily precipitation V07 (Final run; Late run after the last Final day), 0.1 deg",
              "url": "https://doi.org/10.5067/GPM/IMERGDF/DAY/07"},
    "smap_l4": {"id": "smap_l4", "title": "NASA SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture (SPL4SMGP v008), via AppEEARS",
                "url": "https://nsidc.org/data/spl4smgp/versions/8"},
    "smap_l3": {"id": "smap_l3", "title": "NASA SMAP Enhanced L3 Radiometer 9 km daily soil moisture (SPL3SMP_E v006), via AppEEARS",
                "url": "https://nsidc.org/data/spl3smp_e/versions/6"},
    "grace": {"id": "grace_da", "title": "NASA GRACE/GRACE-FO data-assimilation drought indicators (GRACEDADM_CLSM025GL_7D v3.0), 0.25 deg weekly",
              "url": "https://doi.org/10.5067/8DNK2ZU3U1RO"},
    "modis": {"id": "modis_mod13q1", "title": "NASA MODIS Terra MOD13Q1 v061 NDVI 250 m 16-day, via AppEEARS", "url": "https://doi.org/10.5067/MODIS/MOD13Q1.061"},
    "ecostress": {"id": "ecostress", "title": "NASA ECOSTRESS v002 tiled LST, JPL ET and ESI (70 m), via AppEEARS",
                  "url": "https://lpdaac.usgs.gov/products/eco_l4t_esiv002/"},
    "dswx": {"id": "opera_dswx_hls", "title": "NASA/JPL OPERA Dynamic Surface Water Extent from HLS (OPERA_L3_DSWX-HLS_V1), 30 m",
             "url": "https://doi.org/10.5067/OPDSW-PL3V0"},
    "hls": {"id": "hls", "title": "NASA/USGS Harmonized Landsat Sentinel-2 (HLS v2.0) 30 m", "url": "https://doi.org/10.5067/HLS/HLSS30.002"},
    "power": {"id": "nasa_power", "title": "NASA POWER daily (MERRA-2 / GEOS), AG community", "url": "https://power.larc.nasa.gov/"},
}


def src(k: str) -> dict:
    return {**SRC[k], "accessed": ACCESSED, "verified": True}


# ---------------------------------------------------------------- loading
def load(p: str) -> dict:
    n = {}
    d = _pq(p, "imerg")
    if d is not None and len(d) > 30:
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        n["imerg"] = d.dropna(subset=["precipitation"]).drop_duplicates("date").set_index("date").sort_index()
    d = _pq(p, "smap_l4")
    if d is not None and len(d) > 30:
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        d = d.groupby("date").mean(numeric_only=True).sort_index()
        d["sm_rootzone_pct_own"] = own_percentile(d["sm_rootzone"])
        n["smap_l4"] = d
    d = _pq(p, "smap_l3")
    if d is not None and len(d) > 30:
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        n["smap_l3"] = d.groupby("date").agg(sm_valid=("sm_valid", "mean"), soil_moisture=("soil_moisture", "mean")).sort_index()
    d = _pq(p, "grace")
    if d is not None and len(d) > 30:
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        n["grace"] = d.dropna(subset=["gws_inst"]).drop_duplicates("date").set_index("date").sort_index()
    d = _pq(p, "modis")
    if d is not None and len(d) > 30:
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        d = d.drop_duplicates("date").set_index("date").sort_index()
        doy = d.index.day_of_year
        clim = d[d.index.year <= 2025].groupby(d[d.index.year <= 2025].index.day_of_year)["ndvi_good"].mean()
        d["ndvi_anomaly"] = d["ndvi_good"] - pd.Series(doy, index=d.index).map(clim)
        n["modis"] = d
    d = _pq(p, "ecostress")
    if d is not None and len(d) > 5:
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        n["ecostress"] = d
    d = _pq(p, "dswx")
    if d is not None and len(d):
        d["date"] = pd.to_datetime(d["datetime"]).dt.tz_localize(None).dt.normalize()
        n["dswx"] = d.sort_values("date")
    frames = [x for x in (_pq(p, "hls"), _pq(p, "hls_lpdaac")) if x is not None]
    if frames:
        h = pd.concat(frames, ignore_index=True)
        h["_sid"] = h.scene_id.str.replace(r"\.v2\.0$", "", regex=True)
        h = h.drop_duplicates("_sid", keep="last")
        h["date"] = pd.to_datetime(h["date"]).dt.normalize()
        n["hls"] = h[(h.clear_frac >= 0.5) & (h.n_valid >= 20) & h.ndvi_med.notna()].sort_values("date")
    d = _pq(p, "power_nrt")
    if d is not None and len(d):
        d["date"] = pd.to_datetime(d["date"])
        n["power_nrt"] = d
    return n


def own_percentile(s: pd.Series, half_window: int = 15, base_end: int = 2025) -> pd.Series:
    """Empirical percentile (0-100) of each day's value among all baseline values (years <= base_end) whose day of year is
    within +-half_window days (circular). Used because the SMAP L4 product percentile (sm_rootzone_pctl) is missing on
    a third to a half of days at these cells."""
    s = s.dropna()
    base = s[s.index.year <= base_end]
    bdoy = base.index.day_of_year.values
    bval = base.values
    out = {}
    for t, v in s.items():
        dd = np.abs(bdoy - t.day_of_year)
        dd = np.minimum(dd, 366 - dd)
        peers = bval[dd <= half_window]
        out[t] = 100.0 * ((peers < v).sum() + 0.5 * (peers == v).sum()) / len(peers) if len(peers) >= 30 else np.nan
    return pd.Series(out)


# ---------------------------------------------------------------- POWER near-real-time extension of daily_derived
GSC = 0.0820


def _ra_mj(lat_deg, doy):  # FAO-56 eq. 21, identical to backend/regional/src/derive.py
    phi = np.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    return (24 * 60 / np.pi) * GSC * dr * (ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))


def _hargreaves(tmax, tmin, lat_deg, doy):  # FAO-56 eq. 52, identical to backend/regional
    tmean = (tmax + tmin) / 2
    return np.maximum(0.0023 * (tmean + 17.8) * np.sqrt(np.maximum(tmax - tmin, 0)) * 0.408 * _ra_mj(lat_deg, doy), 0)


def extended_derived(derived: pd.DataFrame, nasa: dict, lat: float) -> pd.DataFrame:
    """backend/regional daily_derived (POWER to 2025-12-31) + POWER near-real-time rows after it, with the same
    Hargreaves ETo and heat flags (>= 35 C runs of 3+ days, >= 40 C). Adds column power_run = 'archive' | 'nrt'."""
    d = derived.copy()
    d["power_run"] = "archive"
    nrt = nasa.get("power_nrt")
    if nrt is None:
        return d
    nrt = nrt[nrt.date > d.date.max()].copy()
    if not len(nrt):
        return d
    doy = nrt.date.dt.day_of_year.values
    nrt["eto_hargreaves_mm"] = _hargreaves(nrt.T2M_MAX.values, nrt.T2M_MIN.values, lat, doy)
    nrt["power_run"] = "nrt"
    allx = pd.concat([d[["date", "T2M_MAX"]], nrt[["date", "T2M_MAX"]]]).sort_values("date").reset_index(drop=True)
    heat = allx.T2M_MAX >= 35
    s = heat.astype(int)
    g = (s != s.shift()).cumsum()
    hw = heat & (s.groupby(g).transform("size") >= 3)
    hwmap = dict(zip(allx.date, hw))
    nrt["heatwave_day"] = nrt.date.map(hwmap).fillna(False)
    nrt["severe_heat"] = nrt.T2M_MAX >= 40
    keep = ["date", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "eto_hargreaves_mm", "heatwave_day", "severe_heat", "power_run"]
    return pd.concat([d, nrt[keep]], ignore_index=True).sort_values("date").reset_index(drop=True)


def hls_cover_by_date(p: str) -> dict:
    """{Timestamp: class} from backend/nasa/out/<id>/calendar_hls.json (used for days after the S2/Landsat calendar)."""
    f = ROOT / "backend" / "nasa" / "out" / p / "calendar_hls.json"
    if not f.exists():
        return {}
    cal = json.loads(f.read_text())
    out = {}
    for y in cal["years"]:
        for seg in y["segments"]:
            for d in pd.date_range(seg["start"], seg["end"]):
                out[d] = seg["class"]
    return out


def daily_extra(nasa: dict, dt: pd.Timestamp) -> dict:
    """Per-day NASA columns for GET /daily."""
    row = {"imerg_precip_mm": None, "imerg_run": None, "smap_sm_pct": None, "smap_sm_pctl_product": None, "smap_rootzone_m3m3": None,
           "smap_l3_sm_m3m3": None, "grace_gw_pct": None}
    im = nasa.get("imerg")
    if im is not None and dt in im.index:
        row["imerg_precip_mm"] = _num(im.at[dt, "precipitation"], 2)
        row["imerg_run"] = im.at[dt, "run"] if "run" in im.columns else "final"
    l4 = nasa.get("smap_l4")
    if l4 is not None and dt in l4.index:
        row["smap_sm_pct"] = _num(l4.at[dt, "sm_rootzone_pct_own"], 1)
        row["smap_sm_pctl_product"] = _num(l4.at[dt, "sm_rootzone_pctl"], 1) if "sm_rootzone_pctl" in l4 else None
        row["smap_rootzone_m3m3"] = _num(l4.at[dt, "sm_rootzone"], 3)
    l3 = nasa.get("smap_l3")
    if l3 is not None and dt in l3.index:
        row["smap_l3_sm_m3m3"] = _num(l3.at[dt, "sm_valid"], 3)
    gr = nasa.get("grace")
    if gr is not None:
        i = gr.index.searchsorted(dt, side="right") - 1
        if i >= 0 and (dt - gr.index[i]).days <= 6:
            row["grace_gw_pct"] = _num(gr.iloc[i]["gws_inst"], 1)
    return row


def weekly_extra(nasa: dict, w: pd.Timestamp) -> dict:
    """NASA columns for one features_weekly row (week starting Monday w)."""
    e = w + pd.Timedelta(days=6)
    out = {}
    im = nasa.get("imerg")
    if im is not None:
        s = im.loc[w:e, "precipitation"]
        out["imerg_7d_mm"] = _num(s.sum(), 1) if len(s) == 7 else None
    l4 = nasa.get("smap_l4")
    if l4 is not None:
        s = l4.loc[w:e]
        out["smap_sm"] = _num(s["sm_rootzone"].mean(), 3) if len(s) else None
        out["smap_sm_pct"] = _num(s["sm_rootzone_pct_own"].mean(), 1) if len(s) else None
    gr = nasa.get("grace")
    if gr is not None:
        s = gr.loc[w - pd.Timedelta(days=6):e]
        if len(s):
            r = s.iloc[-1]
            out.update(grace_sfsm_pct=_num(r.sfsm_inst, 1), grace_rzsm_pct=_num(r.rtzsm_inst, 1), grace_gws_pct=_num(r.gws_inst, 1))
    mo = nasa.get("modis")
    if mo is not None:
        s = mo.loc[w - pd.Timedelta(days=15):e, "ndvi_anomaly"].dropna()
        out["modis_ndvi_anomaly"] = _num(s.iloc[-1], 3) if len(s) else None
    ec = nasa.get("ecostress")
    if ec is not None:
        s = ec[(ec["product"] == "ECO_L4T_ESI.002") & (ec.date >= w) & (ec.date <= e) & (ec["cloud"].fillna(1) == 0)]["ESI"].dropna()
        out["esi"] = _num(s.mean(), 3) if len(s) else None
    return out


# ---------------------------------------------------------------- trends (NASA layers)
def trends(nasa: dict) -> dict:
    """{layer: (unit, grid, source, by_year {str: value}, note, default_year)} for the three NASA trend layers present."""
    out = {}
    l4 = nasa.get("smap_l4")
    if l4 is not None:
        m = l4["sm_rootzone"].resample("MS").mean().dropna()
        full = m[m.index.year <= 2025]
        mu, sd = full.groupby(full.index.month).mean(), full.groupby(full.index.month).std()
        z = (m - m.index.month.map(mu).values) / m.index.month.map(sd).values
        by = {str(y): _num(v, 2) for y, v in z.groupby(z.index.year).mean().items()}
        pc = l4["sm_rootzone_pct_own"].groupby(l4.index.year).mean()
        out["smap_anomaly"] = ("sd", "SMAP_L4_EASE2_9km", src("smap_l4"), by,
                               "Calendar-year mean of the monthly standardized anomaly of SMAP L4 root-zone soil moisture "
                               f"(0-100 cm, m3/m3) at the field's 9 km cell, vs the same calendar month over {full.index.year.min()}-2025 "
                               "(0 = normal, -1 = one standard deviation drier). One cell (row 0, col 0), not an 11x11 neighbourhood. "
                               "Our same-season percentile per year (mean): "
                               + (", ".join(f"{y} {v:.0f}" for y, v in pc.items()) if pc is not None else "n/a")
                               + f". {m.index.max().year} is partial (through {l4.index.max().date()}).", 2025)
    gr = nasa.get("grace")
    if gr is not None:
        by = {str(y): _num(v, 1) for y, v in gr["gws_inst"].groupby(gr.index.year).mean().items()}
        out["grace_gw_pct"] = ("percentile (0-100)", "GRACE_DA_0.25deg", src("grace"), by,
                               "Calendar-year mean of the weekly GRACE/GRACE-FO data-assimilation groundwater percentile "
                               "(gws_inst; NASA's drought-indicator percentiles are relative to the product's own long-term record) "
                               f"at the 0.25 deg cell containing the field. 50 = typical, below 30 = dry. One cell. Latest week {gr.index.max().date()}.", 2025)
    mo = nasa.get("modis")
    if mo is not None:
        a = mo["ndvi_anomaly"].dropna()
        by = {str(y): _num(v, 3) for y, v in a.groupby(a.index.year).mean().items()}
        out["modis_ndvi_anomaly"] = ("NDVI difference", "MODIS_250m_pixel", src("modis"), by,
                                     "Calendar-year mean of MODIS MOD13Q1 16-day NDVI minus the 2000-2025 mean NDVI of the same "
                                     "composite period, good/marginal pixels only (pixel_reliability 0-1), at the 250 m pixel containing "
                                     "the field centroid (pixel can mix field edges and ditches). Positive = greener than usual.", 2025)
    return out


# ---------------------------------------------------------------- validation: IMERG vs stations vs POWER
def _cmp(a: pd.Series, b: pd.Series) -> dict:
    df = pd.DataFrame({"a": a, "b": b}).dropna()
    diff = df.a - df.b
    return {"n_months": int(len(df)), "bias": float(diff.mean()), "rmse": float(np.sqrt((diff ** 2).mean())),
            "r2": float(np.corrcoef(df.a, df.b)[0, 1] ** 2), "bias_pct": float(diff.sum() / df.b.sum() * 100), "df": df}


def validation_checks(nasa: dict, station_daily: pd.DataFrame, power: pd.DataFrame, sn, src_ncei, src_power) -> list:
    im = nasa.get("imerg")
    if im is None:
        return []
    st = station_daily["prcp_mm"]
    cnt = st.groupby(st.index.to_period("M")).count()
    stm = st.groupby(st.index.to_period("M")).sum()[cnt >= 27]
    imc = im["precipitation"].groupby(im.index.to_period("M")).count()
    imm = im["precipitation"].groupby(im.index.to_period("M")).sum()
    imm = imm[imc >= imm.index.days_in_month - 1]
    pw = power.set_index("date")["PRECTOTCORR"]
    pwm = pw.groupby(pw.index.to_period("M")).sum()
    out = []
    for cid, title, other, osrc, oname in (("station_vs_imerg", "IMERG vs NOAA NCEI station rain (monthly totals)", stm, src_ncei, "stations"),
                                           ("imerg_vs_power_precip", "IMERG vs NASA POWER rain (monthly totals)", pwm, src_power, "POWER")):
        c = _cmp(imm, other)
        df = c["df"]
        s = src("imerg")
        met = {"bias": sn(c["bias"], "mm/month", s, f"IMERG minus {oname}, mean over months"),
               "bias_pct": sn(c["bias_pct"], "%", s, f"total IMERG rain vs total {oname} rain over the same months"),
               "rmse": sn(c["rmse"], "mm/month", s, "root mean square difference of monthly totals"),
               "r2": sn(c["r2"], "", s, "squared correlation of monthly totals"),
               "n_months": sn(c["n_months"], "months", s, "months compared")}
        by_cal = [{"month": m, "bias": _num((df[df.index.month == m].a - df[df.index.month == m].b).mean(), 2),
                   "imerg_mean": _num(df[df.index.month == m].a.mean(), 2), f"{oname.lower()}_mean": _num(df[df.index.month == m].b.mean(), 2)}
                  for m in range(1, 13)]
        out.append({"id": cid, "title": title, "status": "computed", "metrics": met, "by_calendar_month": by_cal,
                    "note": f"IMERG 0.1 deg cell ({im.grid_lon.iloc[0]}, {im.grid_lat.iloc[0]}) monthly totals vs {oname}; "
                            f"{df.index.min()}..{df.index.max()}. Station months need >= 27 days with a station-mean value. "
                            "IMERG is Final run to its last granule, Late run after (satellite only, no gauge adjustment).",
                    "series": [{"month": str(k), "imerg": _num(v.a, 1), oname.lower(): _num(v.b, 1)} for k, v in df.tail(120).iterrows()]})
    # water-year totals, all three sources side by side (Oct-Sep)
    def wy(s):
        s = s.copy()
        s.index = s.index.to_timestamp() if hasattr(s.index, "to_timestamp") else s.index
        return s.groupby([d.year + 1 if d.month >= 10 else d.year for d in s.index])
    imw, imn = wy(imm).sum(), wy(imm).count()
    stw, stn = wy(stm).sum(), wy(stm).count()
    pwc = pw.groupby(pw.index.to_period("M")).count()
    pwm_full = pwm[pwc >= pwm.index.days_in_month - 1]
    pww, pwn = wy(pwm_full).sum(), wy(pwm_full).count()
    rows = []
    for y in sorted(set(imw.index) & set(pww.index)):
        rows.append({"water_year": int(y), "imerg_mm": _num(imw[y], 0) if imn[y] == 12 else None,
                     "power_mm": _num(pww[y], 0) if pwn.get(y, 0) == 12 else None, "stations_mm": _num(stw.get(y), 0) if stn.get(y, 0) == 12 else None})
    out[0]["by_water_year"] = [r for r in rows if any(r[k] is not None for k in ("imerg_mm", "power_mm", "stations_mm"))]
    return out


# ---------------------------------------------------------------- 10-day NASA readings ("field now" at any date)
def _pct_words(v, what):
    if v is None:
        return None
    v = int(round(v))
    suf = "th" if 10 <= v % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(v % 10, "th")
    if v < 10:
        tag = "far drier than usual"
    elif v < 30:
        tag = "drier than usual"
    elif v <= 70:
        tag = "about normal"
    elif v <= 90:
        tag = "wetter than usual"
    else:
        tag = "far wetter than usual"
    return f"{what} at the {v}{suf} percentile for this time of year: {tag}."


def nasa_series(p: str, nasa: dict) -> dict:
    """10-day steps (1st, 11th, 21st of each month) from 2015-01-01 to the last day any NASA dataset has data.
    Each value is the latest observation inside the step window or within a dataset-specific look-back; obs dates kept."""
    last = max([v.index.max() if isinstance(v.index, pd.DatetimeIndex) else v.date.max() for k, v in nasa.items()
                if k not in ("power_nrt",)] + [pd.Timestamp("2015-01-01")])
    starts = [d for d in pd.date_range("2015-01-01", last, freq="D") if d.day in (1, 11, 21)]
    im, l4, l3, gr, mo, ec, dw, hl = (nasa.get(k) for k in ("imerg", "smap_l4", "smap_l3", "grace", "modis", "ecostress", "dswx", "hls"))
    # IMERG water-year-to-date and its 2001-2025 mean for the same day of the water year
    wytd = norm = None
    if im is not None:
        pr = im["precipitation"]
        wyear = pd.Series([d.year + 1 if d.month >= 10 else d.year for d in pr.index], index=pr.index)
        wytd = pr.groupby(wyear).cumsum()
        wday = pd.Series([(d - pd.Timestamp(year=(d.year if d.month >= 10 else d.year - 1), month=10, day=1)).days for d in pr.index], index=pr.index)
        full_years = [y for y, n in pr.groupby(wyear).count().items() if n >= 360 and 2001 <= y <= 2025]
        clim = wytd[wyear.isin(full_years)].groupby(wday[wyear.isin(full_years)]).mean()
        norm = wday.map(clim)
    rows = []
    for s in starts:
        e = (s + pd.offsets.MonthEnd(0)) if s.day == 21 else s + pd.Timedelta(days=9)
        r = {"date": s.strftime("%Y-%m-%d"), "end": e.strftime("%Y-%m-%d")}
        if im is not None:
            w = im.loc[s:e, "precipitation"]
            r["imerg_rain_mm"] = _num(w.sum(), 1) if len(w) == (e - s).days + 1 else None
            k = wytd.loc[:e]
            if len(k) and k.index[-1] >= s:
                r["imerg_wy_to_date_mm"] = _num(k.iloc[-1], 0)
                r["imerg_wy_to_date_normal_mm"] = _num(norm.loc[k.index[-1]], 0)
                r["imerg_obs_date"] = k.index[-1].strftime("%Y-%m-%d")
        if l4 is not None:
            w = l4.loc[s:e]
            if len(w):
                r["smap_rootzone_pct"] = _num(w["sm_rootzone_pct_own"].mean(), 1)
                r["smap_rootzone_pctl_product"] = _num(w["sm_rootzone_pctl"].mean(), 1) if "sm_rootzone_pctl" in w else None
                r["smap_rootzone_m3m3"] = _num(w["sm_rootzone"].mean(), 3)
                r["smap_surface_m3m3"] = _num(w["sm_surface"].mean(), 3)
                r["smap_obs_date"] = w.index.max().strftime("%Y-%m-%d")
        if l3 is not None:
            w = l3.loc[s:e, "sm_valid"].dropna()
            r["smap_l3_sm_m3m3"] = _num(w.mean(), 3) if len(w) else None
        if gr is not None:
            w = gr.loc[s - pd.Timedelta(days=6):e]
            if len(w):
                g = w.iloc[-1]
                r.update(grace_gw_pct=_num(g.gws_inst, 1), grace_rootzone_pct=_num(g.rtzsm_inst, 1), grace_obs_date=w.index[-1].strftime("%Y-%m-%d"))
        if mo is not None:
            w = mo.loc[s - pd.Timedelta(days=16):e].dropna(subset=["ndvi_good"])
            if len(w):
                r.update(modis_ndvi=_num(w.ndvi_good.iloc[-1], 3), modis_ndvi_anomaly=_num(w.ndvi_anomaly.iloc[-1], 3),
                         modis_obs_date=w.index[-1].strftime("%Y-%m-%d"))
        if ec is not None:
            w = ec[(ec["product"] == "ECO_L4T_ESI.002") & (ec.date >= s - pd.Timedelta(days=20)) & (ec.date <= e) & (ec["cloud"].fillna(1) == 0)].dropna(subset=["ESI"])
            if len(w):
                r.update(ecostress_esi=_num(w.ESI.iloc[-1], 3), ecostress_obs_date=w.date.iloc[-1].strftime("%Y-%m-%d"))
            w = ec[(ec["product"] == "ECO_L3T_JET.002") & (ec.date >= s - pd.Timedelta(days=20)) & (ec.date <= e) & (ec["cloud"].fillna(1) == 0)].dropna(subset=["ETdaily"])
            if len(w):
                r.update(ecostress_et_mm_day=_num(w.ETdaily.iloc[-1], 2), ecostress_et_obs_date=w.date.iloc[-1].strftime("%Y-%m-%d"))
        if dw is not None:
            w = dw[(dw.date >= s) & (dw.date <= e) & (dw.frac_clear >= 0.8)]
            if len(w):
                r.update(dswx_water_frac=_num(w.frac_water.max(), 3), dswx_obs_date=w.date[w.frac_water.idxmax()].strftime("%Y-%m-%d"))
        if hl is not None:
            w = hl[(hl.date >= s) & (hl.date <= e)]
            if len(w):
                r.update(hls_ndvi=_num(w.ndvi_med.iloc[-1], 3), hls_obs_date=w.date.iloc[-1].strftime("%Y-%m-%d"))
        rows.append(r)
    latest = {}
    for k, col in (("imerg", "precipitation"), ("smap_l4", "sm_rootzone"), ("smap_l3", "sm_valid"), ("grace", "gws_inst"),
                   ("modis", "ndvi_good")):
        v = nasa.get(k)
        if v is not None:
            s = v[col].dropna()
            latest[k] = s.index.max().strftime("%Y-%m-%d") if len(s) else None
    for k in ("ecostress", "dswx", "hls"):
        v = nasa.get(k)
        if v is not None and len(v):
            latest[k] = v.date.max().strftime("%Y-%m-%d")
    fields = {
        "imerg_rain_mm": "IMERG rain in the 10-day step (mm); null if a day is missing",
        "imerg_wy_to_date_mm": "IMERG rain since 1 Oct (water year to date, mm) at imerg_obs_date",
        "imerg_wy_to_date_normal_mm": "mean IMERG water-year-to-date for the same day, water years 2001-2025",
        "smap_rootzone_pct": "SMAP L4 root-zone (0-100 cm) soil moisture percentile, ours: rank of the day's value among all SMAP days "
                             "2015-2025 within +-15 days of the same date (0 = driest on record for the season), step mean",
        "smap_rootzone_pctl_product": "SMAP L4 product percentile (sm_rootzone_pctl, vs the model's long climatology); missing on "
                                      "a third to a half of days at these cells",
        "smap_rootzone_m3m3": "SMAP L4 root-zone soil moisture, m3/m3", "smap_surface_m3m3": "SMAP L4 surface (0-5 cm) soil moisture, m3/m3",
        "smap_l3_sm_m3m3": "SMAP L3 retrieved surface soil moisture, recommended-quality retrievals only (flooded rice often fails)",
        "grace_gw_pct": "GRACE-DA groundwater percentile (weekly; latest week starting within 6 days before the step end)",
        "grace_rootzone_pct": "GRACE-DA root-zone soil moisture percentile",
        "modis_ndvi": "MODIS 16-day NDVI (good pixels)", "modis_ndvi_anomaly": "MODIS NDVI minus 2000-2025 mean of the same 16-day period",
        "ecostress_esi": "ECOSTRESS Evaporative Stress Index (actual/potential ET, 0-1; low = stressed), clear scenes",
        "ecostress_et_mm_day": "ECOSTRESS JPL daily ET (mm/day), clear scenes",
        "dswx_water_frac": "OPERA DSWx share of the field under water (max over clear scenes in the step)",
        "hls_ndvi": "HLS field-median NDVI (latest clear scene in the step)",
    }
    return {"location_id": p, "step": "10-day (1st, 11th, 21st)", "latest_by_dataset": latest, "fields": fields,
            "sources": {k: src(k) for k in ("imerg", "smap_l4", "smap_l3", "grace", "modis", "ecostress", "dswx", "hls") if nasa.get(k) is not None},
            "rows": rows}


def now_reading(series: dict, date: str | None) -> dict:
    """Readings for the 10-day step containing `date` (default: today), falling back per field to the latest step that has
    the value (look-back marked with `as_of`). Plain-language lines for SMAP and GRACE."""
    rows = series["rows"]
    target = date or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    idx = max([i for i, r in enumerate(rows) if r["date"] <= target] or [0])
    pick = {}
    keys = [k for k in series["fields"]]
    max_stale = 18  # 10-day steps (~6 months): older values are not "now"
    for k in keys:
        for j in range(idx, max(idx - max_stale, 0) - 1, -1):
            if rows[j].get(k) is not None:
                obs = None
                for oc in ("smap_obs_date", "grace_obs_date", "modis_obs_date", "ecostress_obs_date", "ecostress_et_obs_date",
                           "dswx_obs_date", "hls_obs_date", "imerg_obs_date"):
                    if k.split("_")[0] == oc.split("_")[0] and rows[j].get(oc):
                        obs = rows[j][oc]
                        if k.startswith("ecostress_et") != oc.startswith("ecostress_et"):
                            continue
                        break
                pick[k] = {"value": rows[j][k], "step": rows[j]["date"], "obs_date": obs, "stale_steps": idx - j}
                break
    sm, gw = pick.get("smap_rootzone_pct"), pick.get("grace_gw_pct")
    words = [w for w in (_pct_words(sm["value"] if sm else None, "Root-zone soil moisture (NASA SMAP) is"),
                         _pct_words(gw["value"] if gw else None, "Groundwater (NASA GRACE-FO) is")) if w]
    return {"date_requested": target, "step": rows[idx]["date"] if rows else None, "readings": pick,
            "plain_language": words, "latest_by_dataset": series["latest_by_dataset"], "fields": series["fields"],
            "sources": series["sources"],
            "note": "Values older than 18 steps (~6 months) are left out. stale_steps = how many 10-day steps back the value comes from (0 = this step). GRACE has ~2-3 months "
                    "latency, so recent dates show the latest week available."}


# ---------------------------------------------------------------- nasa_datasets block for GET /api/locations/{id}
def nasa_datasets(p: str, nasa: dict) -> list:
    def rng(k, col="date"):
        v = nasa.get(k)
        if v is None:
            return None
        idx = v.index if isinstance(v.index, pd.DatetimeIndex) else pd.to_datetime(v[col])
        return [idx.min().strftime("%Y-%m-%d"), idx.max().strftime("%Y-%m-%d")]

    def rows(k):
        v = nasa.get(k)
        return int(len(v)) if v is not None else 0

    pw = _meta(p, "power")
    pn = _meta(p, "power_nrt")
    terrain = ROOT / "backend" / "nasa_open" / "out" / p / "terrain.json"
    iss = CACHE / p / "iss" / "iss.json"
    land = _pq(p, "landsat")
    ec = nasa.get("ecostress")

    def entry(id_, name, tells, res, dr, n, status, used_in, url, note=None):
        d = {"id": id_, "name": name, "tells_you": tells, "resolution": res, "date_range": dr, "rows": n, "status": status,
             "used_in": used_in, "source_url": url}
        if note:
            d["note"] = note
        return d

    def st(k):
        return "live" if nasa.get(k) is not None else "pending"

    out = [
        entry("power", "NASA POWER daily weather", "Daily heat, cold, rain and the reference crop water demand (ETo) for your area.",
              "about 50 km (0.5 x 0.625 deg)", [pw.get("date_min"), pn.get("date_max") or pw.get("date_max")],
              int(pw.get("rows", 0)) + int(pn.get("rows", 0)), "live", ["daily", "strategies water use", "heat and frost days", "trends"],
              "https://power.larc.nasa.gov/"),
        entry("imerg", "GPM IMERG rainfall", "How much rain fell on your field each day, from NASA's satellite rain estimate.",
              "about 10 km (0.1 deg), daily", rng("imerg"), rows("imerg"), st("imerg"),
              ["daily rain column", "rain so far this season", "validation vs stations"], SRC["imerg"]["url"],
              "Final run (gauge-adjusted) to its last day, Late run (satellite only) after that." if nasa.get("imerg") is not None else None),
        entry("smap_l4", "SMAP soil moisture (L4, root zone)", "How wet the soil is down to about 1 m compared with normal for this time of year.",
              "9 km, daily", rng("smap_l4"), rows("smap_l4"), st("smap_l4"), ["field now: soil moisture", "3D soil slab", "trends"], SRC["smap_l4"]["url"]),
        entry("smap_l3", "SMAP soil moisture (L3, surface retrievals)", "The satellite's direct measurement of the top 5 cm of soil, on days it is reliable.",
              "9 km, daily", rng("smap_l3"), rows("smap_l3"), st("smap_l3"), ["checks", "daily"], SRC["smap_l3"]["url"],
              "Retrievals over flooded rice or open water are flagged and dropped, not filled."),
        entry("grace", "GRACE-FO groundwater", "Whether groundwater under your area is higher or lower than usual (percentile).",
              "about 25 km (0.25 deg), weekly", rng("grace"), rows("grace"), st("grace"), ["field now: groundwater", "3D groundwater slab", "trends"],
              SRC["grace"]["url"], "Model that assimilates GRACE/GRACE-FO gravity data; 2-3 month latency."),
        entry("modis", "MODIS vegetation greenness (NDVI)", "How green the area is compared with the same two weeks in 2000-2025.",
              "250 m, 16-day", rng("modis"), rows("modis"), st("modis"), ["trends", "features"], SRC["modis"]["url"]),
        entry("ecostress", "ECOSTRESS crop stress and water use", "Whether the crop is using as much water as it could (stress index) on days the space station passes over.",
              "70 m, irregular (ISS overpasses)", rng("ecostress"), rows("ecostress"), st("ecostress"), ["field now: crop stress", "features"],
              SRC["ecostress"]["url"]),
        entry("dswx", "OPERA surface water (DSWx)", "When and how much of the field was under water (winter flooding, floods).",
              "30 m, every few days", rng("dswx"), rows("dswx"), st("dswx"), ["field now", "winter flooding check", "nasa_series"],
              SRC["dswx"]["url"], "Scenes only where OPERA has processed HLS; none exist over the Colusa field for the 2020-21 and 2021-22 winters."
              if p == "car_colusa_rice" else "Fetched for spring 2023 (Tulare Lake re-flooding)."),
        entry("hls", "HLS (Harmonized Landsat Sentinel-2)", "What is growing on the field and when it is bare, green or flooded, every 2-3 days.",
              "30 m, every 2-3 days", rng("hls"), rows("hls"), st("hls"), ["calendar?source=hls", "nasa_series"], SRC["hls"]["url"]),
        entry("landsat", "Landsat 8/9 (NASA/USGS)", "Field greenness record used with Sentinel-2 in the main calendar.", "30 m, 8-16 days",
              [str(pd.to_datetime(land.date).min().date()), str(pd.to_datetime(land.date).max().date())] if land is not None else None,
              int(len(land)) if land is not None else 0, "live" if land is not None else "pending", ["calendar", "grid"],
              "https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2"),
        entry("nasadem", "NASADEM elevation", "Slope and low spots on and around the field.", "30 m, one-time (2000 radar)", ["2000-02-11", "2000-02-22"],
              None, "live" if terrain.exists() else "pending", ["terrain", "3D view"], "https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001",
              "Radar noise of 2-4 m on flat fields: slope uses a 150 m smoothed surface."),
        entry("iss_photos", "ISS astronaut photographs", "Photos of the area taken by astronauts on the International Space Station.",
              "varies (400 mm lens: ~10 m)", None, None, "live" if iss.exists() else "pending", ["pitch", "3D view"], "https://eol.jsc.nasa.gov",
              "Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center. Near the field, not of it."),
    ]
    if ec is not None:
        for e in out:
            if e["id"] == "ecostress":
                e["note"] = f"{int((ec['cloud'].fillna(1) == 0).sum())} clear scene-product rows of {len(ec)}."
    return out


def bc_signal() -> dict | None:
    """BcSignal payload from data/cache/bc/signal_raw.parquet (backend/nasa/fetch_bc_signal.py). Markers copied from the
    fixture (spec-stated events, dates marked approximate there); lead_days = days from the first week GRACE
    groundwater or SMAP root zone fell below the 20th percentile to the marker, if that happened before it."""
    f = CACHE / "bc" / "signal_raw.parquet"
    if not f.exists():
        return None
    d = pd.read_parquet(f)
    d["date"] = pd.to_datetime(d["date"])
    w = d.set_index("date").resample("W-WED").agg({"smap_rootzone_pctl": "mean", "grace_gw_pct": "last", "power_tmax_c": "max"})
    w["grace_gw_pct"] = w["grace_gw_pct"].ffill(limit=1)
    series = [{"date": i.strftime("%Y-%m-%d"), "smap_pct": _num(r.smap_rootzone_pctl, 1), "grace_gw_pct": _num(r.grace_gw_pct, 1),
               "power_tmax_c": _num(r.power_tmax_c, 1)} for i, r in w.iterrows()]
    fx = json.loads((ROOT / "fixtures" / "bc_signal.json").read_text())
    low = w[(w.smap_rootzone_pctl < 20) | (w.grace_gw_pct < 20)]
    first = low.index.min() if len(low) else None
    markers = []
    for m in fx["markers"]:
        md = pd.Timestamp(m["date"])
        lead = int((md - first).days) if first is not None and first <= md else None
        markers.append({**m, "lead_days": lead})
    meta = json.loads((CACHE / "bc" / "signal.meta.json").read_text())
    return {"point": {"lon": meta["point_lon_lat"][0], "lat": meta["point_lon_lat"][1]}, "series": series, "markers": markers,
            "sources": {"smap": src("smap_l4"), "grace": src("grace"), "power": src("power")},
            "note": "NASA-only signal at a representative point on the lower Salmon River (U). smap_pct = SMAP L4 root-zone percentile "
                    "(weekly mean), grace_gw_pct = GRACE-DA groundwater percentile, power_tmax_c = weekly max POWER Tmax. lead_days = days "
                    "between the first week either percentile fell below 20 and the marker (rule ours, U). Marker dates are as in the spec "
                    "(the mid-June request date is approximate)."}


# ---------------------------------------------------------------- GET /water_seen (OPERA DSWx)
def water_seen(p: str, nasa: dict) -> dict | None:
    """Per-scene share of the field under water (OPERA DSWx-HLS, 30 m) plus a per-season summary in plain words."""
    d = nasa.get("dswx")
    if d is None or not len(d):
        return None
    m = _meta(p, "dswx")
    scenes = [{"date": r.date.strftime("%Y-%m-%d"), "scene": r.scene, "water_frac": _num(r.frac_water, 3),
               "open_water_frac": _num(r.frac_open_water, 3), "partial_water_frac": _num(r.frac_partial_water, 3),
               "cloud_snow_frac": _num(r.frac_cloud_snow, 3), "clear_frac": _num(r.frac_clear, 3), "clear": bool(r.frac_clear >= 0.8)}
              for r in d.itertuples()]
    c = d[d.frac_clear >= 0.8].copy()
    seasons = []
    if p == "car_colusa_rice":
        c = c[c.date.dt.month.isin([11, 12, 1, 2, 3, 4])]
        c["season"] = np.where(c.date.dt.month >= 11, c.date.dt.year, c.date.dt.year - 1)
        label = lambda y: f"{y}-{(y + 1) % 100:02d} winter"  # noqa: E731
    else:
        c["season"] = c.date.dt.year
        label = lambda y: f"spring {y}"  # noqa: E731
    for y, g in c.groupby("season"):
        wet = g[g.frac_water > 0.5]
        seasons.append({"season": label(int(y)), "clear_scenes": int(len(g)), "max_water_frac": _num(g.frac_water.max(), 3),
                        "scenes_over_half_water": int(len(wet)),
                        "first_wet": wet.date.min().strftime("%Y-%m-%d") if len(wet) else None,
                        "last_wet": wet.date.max().strftime("%Y-%m-%d") if len(wet) else None,
                        "water_seen": bool(len(wet))})
    full = [s for s in seasons if s["clear_scenes"] >= 5]
    n_w = sum(s["water_seen"] for s in full)
    if p == "car_colusa_rice":
        summary = (f"NASA OPERA saw more than half of this field under water in {n_w} of {len(full)} winters with at least 5 clear "
                   "satellite views (2016-17 to 2025-26). Much of it is classed as partial surface water (shallow water mixed with "
                   "stubble or soil), which greenness-based images can miss. No OPERA images exist over this field for the 2020-21 "
                   "and 2021-22 winters.")
    else:
        mx = max((s["max_water_frac"] or 0) for s in seasons) if seasons else 0
        summary = (f"In spring 2023 (Tulare Lake re-flooding) NASA OPERA saw at most {mx:.0%} of this field as water on a clear day; "
                   "no clear view showed the field flooded.")
    return {"location_id": p, "rule": "clear = at least 80% of the field's pixels free of cloud/snow; water = open (class 1) + partial (class 2) surface water",
            "summary": summary, "seasons": seasons, "scenes": scenes, "source": src("dswx"),
            "fetched_at": m.get("fetched_at"), "windows": (m.get("params") or {}).get("windows")}
