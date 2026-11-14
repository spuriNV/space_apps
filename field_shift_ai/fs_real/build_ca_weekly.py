"""Build the B6.2 weekly table for ca_colusa_rice from real data.
NASA POWER daily (T2M_MAX/MIN, PRECTOTCORR) + AppEEARS point extracts (MOD13Q1 NDVI, SMAP L3E,
ECOSTRESS LST + ESI) when present in data/appeears/."""
import glob
import numpy as np
import pandas as pd

LOC, LAT = "ca_colusa_rice", 39.15
D = "data/"

# ---- NASA POWER daily -> Hargreaves ETo (FAO-56 eq. 52), 30-day rain --------------------------
pw = pd.read_csv(D + "fs_power_ca_colusa_rice.csv", dtype={"date": str})
pw["date"] = pd.to_datetime(pw["date"], format="%Y%m%d")
pw = pw.set_index("date").sort_index().replace(-999, np.nan)
doy = pw.index.dayofyear.values
phi = np.deg2rad(LAT)
dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
dec = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
ws = np.arccos(-np.tan(phi) * np.tan(dec))
Ra = 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))  # MJ m-2 d-1
tmax, tmin = pw["T2M_MAX"], pw["T2M_MIN"]
pw["eto_mm"] = 0.0023 * 0.408 * Ra * ((tmax + tmin) / 2 + 17.8) * np.sqrt((tmax - tmin).clip(lower=0))
pw["precip_30d_mm"] = pw["PRECTOTCORR"].rolling(30, min_periods=30).sum()

wk = pd.DataFrame({
    "t2m_max_c": pw["T2M_MAX"].resample("W-SUN").mean(),
    "eto_mm": pw["eto_mm"].resample("W-SUN").sum(),
    # stand-in for "IMERG 30-day": POWER PRECTOTCORR 30-day total at week end (IMERG needs GES DISC)
    "imerg_30d_mm": pw["precip_30d_mm"].resample("W-SUN").last(),
})
wk.index = wk.index - pd.Timedelta(days=6)  # week_start = Monday
wk.index.name = "week_start"


def _appeears(pattern):
    fs = glob.glob(D + "appeears/" + pattern)
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else None


def _col(df, key):
    return next(c for c in df.columns if key in c)


# ---- MODIS MOD13Q1 NDVI (QA: pixel_reliability 0 good, 1 marginal) -----------------------------
m = _appeears("*MOD13Q1*results.csv")
if m is None and glob.glob(D + "fs_modis_ca_colusa_rice.csv"):  # same product via Planetary Computer
    pc = pd.read_csv(D + "fs_modis_ca_colusa_rice.csv").drop_duplicates("start")
    m = pd.DataFrame({"Date": pc["start"], "MOD13Q1_061__250m_16_days_NDVI": pc["ndvi_raw"] * 0.0001,
                      "MOD13Q1_061__250m_16_days_pixel_reliability": pc["pixel_reliability"]})
if m is not None:
    m["Date"] = pd.to_datetime(m["Date"])
    rel = m[_col(m, "pixel_reliability")]
    nd = m[_col(m, "_NDVI")].where(rel.isin([0, 1]))
    s = pd.Series(nd.values, index=m["Date"]).sort_index()
    # 16-day composites -> weekly: assign to each week by time interpolation (<= 24-day gaps)
    daily = s.resample("D").mean().interpolate(limit=24, limit_area="inside")
    wkly = daily.resample("W-SUN").mean()
    wkly.index = wkly.index - pd.Timedelta(days=6)
    wk["ndvi_modis"] = wkly.reindex(wk.index)

# ---- SMAP L3 Enhanced 9 km (AM, recommended-quality bit 0 == 0) --------------------------------
sm = _appeears("*SPL3SMP-E*results.csv")
if sm is None:
    sm = _appeears("*SPL3SMP*results.csv")
if sm is not None:
    sm["Date"] = pd.to_datetime(sm["Date"])
    v = sm[_col(sm, "AM_soil_moisture")].where(lambda x: x > 0)
    q = sm[_col(sm, "AM_retrieval_qual_flag")]
    v = v.where((q.fillna(1).astype(int) & 1) == 0)
    s = pd.Series(v.values, index=sm["Date"]).sort_index().resample("W-SUN").mean()
    s.index = s.index - pd.Timedelta(days=6)
    wk["smap_sm"] = s.reindex(wk.index)
    # percentile vs same ISO week across 2015-2025
    iso = wk.index.isocalendar().week.clip(upper=52).values
    wk["smap_pct"] = wk.groupby(iso)["smap_sm"].rank(pct=True) * 100

# ---- ECOSTRESS LST (K) and ESI ------------------------------------------------------------------
e = _appeears("*ECO-L2T-LSTE*results.csv")
if e is None:
    e = _appeears("*ECO_L2T_LSTE*results.csv")
if e is not None:
    e["Date"] = pd.to_datetime(e["Date"])
    lst = e[_col(e, "_LST")].where(lambda x: x > 200)
    cl = e[[c for c in e.columns if "cloud" in c.lower() and "Description" not in c][0]] if any("cloud" in c.lower() for c in e.columns) else 0
    lst = lst.where(pd.Series(cl).fillna(0).values == 0)
    d = pd.DataFrame({"date": e["Date"].dt.normalize(), "lst_k": lst.values}).dropna()
    d = d.merge(pw[["T2M_MAX"]], left_on="date", right_index=True)
    d["lst_minus_tmax_c"] = d["lst_k"] - 273.15 - d["T2M_MAX"]
    w = d.set_index("date")[["lst_k", "lst_minus_tmax_c"]].resample("W-SUN").mean()
    w.index = w.index - pd.Timedelta(days=6)
    wk = wk.join(w)
es = _appeears("*ECO-L4T-ESI*results.csv")
if es is None:
    es = _appeears("*ECO_L4T_ESI*results.csv")
if es is not None:
    es["Date"] = pd.to_datetime(es["Date"])
    v = es[_col(es, "_ESI")].where(lambda x: (x >= 0) & (x <= 2))
    s = pd.Series(v.values, index=es["Date"]).sort_index().resample("W-SUN").mean()
    s.index = s.index - pd.Timedelta(days=6)
    wk["esi"] = s.reindex(wk.index)

iso = wk.index.isocalendar().week.clip(upper=52).values


def _weekly(series, how="mean"):
    w = getattr(series.sort_index().resample("W-SUN"), how)()
    w.index = w.index - pd.Timedelta(days=6)
    return w.reindex(wk.index)


# ---- NASA SERVIR ClimateSERV (no login): ESI 4-week, NASA-USDA SMAP surface SM, GPM IMERG late ------
for c in ("smap_pct", "esi"):
    if c not in wk:
        wk[c] = np.nan
wk["sm_source"] = np.where(wk["smap_pct"].notna(), "SMAP SPL3SMP_E (AppEEARS)", None)
wk["esi_source"] = np.where(wk["esi"].notna(), "ECOSTRESS L4T ESI (AppEEARS)", None)
wk["rain_source"] = "NASA POWER PRECTOTCORR"
if glob.glob(D + "fs_climateserv_ca_colusa_rice.csv"):
    cs = pd.read_csv(D + "fs_climateserv_ca_colusa_rice.csv")
    cs["date"] = pd.to_datetime(cs["date"], format="%m/%d/%Y")
    get = lambda v: cs[cs["var"] == v].drop_duplicates("date").set_index("date")["value"]
    # ESI (SPoRT/NASA, ALEXI 4-week composite, ~5 km): fills weeks with no ECOSTRESS ESI
    e = _weekly(get("esi").resample("D").ffill(limit=6))
    m = wk["esi"].isna() & e.notna()
    wk.loc[m, "esi"], wk.loc[m, "esi_source"] = e[m], "SERVIR ESI 4-week (ALEXI, ~5 km)"
    # NASA-USDA enhanced SMAP surface soil moisture (mm), 3-daily, 2015-04..2022-08 -> same-week percentile
    sm = _weekly(get("smap"))
    pct = sm.groupby(iso).rank(pct=True) * 100
    m = wk["smap_pct"].isna() & pct.notna()
    wk.loc[m, "smap_pct"], wk.loc[m, "sm_source"] = pct[m], "NASA-USDA SMAP surface SM (ClimateSERV)"
    # GPM IMERG late daily -> 30-day total at week end (to 2024-06); POWER fills after
    im = get("imerg").resample("D").sum(min_count=1)
    im30 = im.rolling(30, min_periods=28).sum()
    w30 = im30.resample("W-SUN").last()
    w30.index = w30.index - pd.Timedelta(days=6)
    w30 = w30.reindex(wk.index)
    m = w30.notna()
    wk.loc[m, "imerg_30d_mm"], wk.loc[m, "rain_source"] = w30[m], "GPM IMERG late (ClimateSERV)"

# ---- stand-in for remaining soil-moisture gaps: NASA POWER GWETTOP ---------------------------------
if wk["smap_pct"].isna().any() and glob.glob(D + "fs_power_soilwet_ca_colusa_rice.csv"):
    sw = pd.read_csv(D + "fs_power_soilwet_ca_colusa_rice.csv", dtype={"date": str})
    sw["date"] = pd.to_datetime(sw["date"], format="%Y%m%d")
    g = _weekly(sw.set_index("date")["GWETTOP"].replace(-999, np.nan))
    wk["soil_wetness_top"] = g
    gp = g.groupby(iso).rank(pct=True) * 100  # same-week percentile, 2000-2025
    m = wk["smap_pct"].isna() & gp.notna()
    wk.loc[m, "smap_pct"], wk.loc[m, "sm_source"] = gp[m], "NASA POWER GWETTOP (model; SMAP stand-in)"
wk["lst_source"] = "ECOSTRESS L2T LSTE (AppEEARS)" if "lst_minus_tmax_c" in wk else None
if "lst_minus_tmax_c" not in wk and glob.glob(D + "fs_modis_lst_ca_colusa_rice.csv"):
    ml = pd.read_csv(D + "fs_modis_lst_ca_colusa_rice.csv").drop_duplicates("start")
    qc = ml["qc_day"].fillna(0).astype(int)
    ok = (qc & 3) <= 1  # MOD11A2 QC bits 0-1: 00 good, 01 other quality; 10/11 not produced
    k = (ml["lst_day_raw"] * 0.02).where(ok & ml["lst_day_raw"].notna())
    s8 = pd.Series(k.values, index=pd.to_datetime(ml["start"]) + pd.Timedelta(days=4)).sort_index()  # composite mid-point
    daily = s8.resample("D").mean().interpolate(limit=8, limit_area="inside")
    w = daily.resample("W-SUN").mean()
    w.index = w.index - pd.Timedelta(days=6)
    wk["lst_k"] = w.reindex(wk.index)
    wk["lst_minus_tmax_c"] = wk["lst_k"] - 273.15 - wk["t2m_max_c"]
    wk["lst_source"] = "MODIS MOD11A2 day LST 1 km (Planetary Computer; ECOSTRESS stand-in)"

# ---- season and CDL -------------------------------------------------------------------------------
cdl = pd.read_csv(D + "fs_cdl_ca_colusa_rice.csv").set_index("year").mode(axis=1)[0].astype(int)
yr = wk.index.year
wk["cdl_class"] = pd.Series(yr, index=wk.index).map(cdl)
# growing season of the existing crop (rice, B1 CA0 calendar U): May 1 - Sep 30; fallow years have no season
mo = wk.index.month
# 2022 (fallow) kept in-season so check B10.1 #8 can see it; it is labelled fallow, not stress.
wk["in_season"] = ((mo >= 5) & (mo <= 9)).astype(int)
wk["location_id"] = LOC
wk = wk.reset_index()
wk.to_csv(D + "weekly_ca.csv", index=False)
print(D + "weekly_ca.csv", wk.shape, "cols:", [c for c in wk.columns])
print(wk.notna().sum().to_dict())
