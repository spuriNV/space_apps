"""Input tables for B6.1 and B6.2, built only from cached, scripted data on main (no hand-downloaded files).

The `ds` branch (spuriNV) built the same two tables (`obs_ca.csv`, `weekly_ca.csv`) from files downloaded by hand
in a browser for one 200 m box. This module builds them for every field, with the same column names where they
exist, from the caches written by backend/field, backend/nasa, backend/nasa_open, backend/regional and this chunk.

Tables (data/cache/<fid>/ai/, + inputs.meta.json with the source and coverage of every column):

  obs_clusters.parquet  one row per Sentinel-2 date x 150 m training cluster of the field's 10 km box (templates only)
      reflectance (blue..swir2), ndvi/ndwi/bsi medians, valid_fraction, SCL fractions over clear pixels
      (scl_veg_frac = SCL 4, scl_bare_frac = SCL 5, scl_water_frac = SCL 6), cdl_class for that year, block,
      modis_ndvi_clim (MOD13Q1 2001-2015 same-DOY mean at the cluster), context (below)
  obs_field.parquet     one row per clear satellite date on the field polygon: S2 L2A (backend/field, with SCL
      fractions), HLS L30/S30 (backend/nasa LP DAAC + backend/nasa_open Planetary Computer copy), sensor column;
      cdl_class from crop_history; modis_ndvi_clim at the field; opera_water_frac (OPERA DSWx-HLS scene of the same
      day, >= 50% clear); context
  weekly.parquet        one row per ISO week (Monday start) 2000-.. on the field (B6.2):
      ndvi_modis    MOD13Q1 at the field centroid (backend/nasa AppEEARS file if present, else Planetary Computer)
      ndvi_hls      field-median NDVI: S2 first, then HLS, then Landsat (backend/field, backend/nasa)
      lst_k         ECOSTRESS LST (backend/nasa) when cached; MODIS MOD11A2 LST as fallback (lst_source)
      lst_minus_tmax_c  LST minus the same days' station Tmax
      esi           ECOSTRESS ESI when cached; else ECOSTRESS JET ETdaily / Penman-Monteith ETo (the ESI ratio);
                    else OpenET monthly ET / ETo (esi_source)
      smap_pct      SMAP L4 root-zone percentile (backend/nasa); GRACE-DA root-zone percentile as fallback (sm_source)
      imerg_30d_mm, imerg_7d_mm  GPM IMERG trailing sums at the week's end
      t2m_max_c     NOAA NCEI station Tmax (mean of the field's stations), NASA POWER where no station reports
      eto_mm        FAO-56 Penman-Monteith (station Tmax/Tmin, POWER radiation, humidity, wind), as in backend/engine
      water         any water observation that week (S2/Landsat NDWI > 0.3 or SCL water > 50%, or OPERA >= 50%)
      usdm_d3plus_pct  US Drought Monitor % of the county area in D3 or worse (max over the field's counties)
      cdl_class, crop, in_season

Context columns shared by both observation tables (one value per date for the whole 10 km box): tmax_7d_c,
imerg_7d_mm, smap_pct.

Usage: uv run python -m fieldshift_ai.inputs [fid ...]
"""
from __future__ import annotations

import importlib.util
import sys

import numpy as np
import pandas as pd

from .common import (CROP_NAME_TO_CODE, ENGINE_DIR, REPO, YEARS, ai_cache, cache, crop_history, family,
                     field_ids, field_polygon, now, read_json, write_json)

S2_CLEAR = (2, 4, 5, 6)
SEASON_WEEKS = {"rice": (23, 39), "forage": (14, 39)}   # ISO weeks scored for crop stress (U, preset calendars)
CLIM_YEARS = (2001, 2015)                               # MODIS NDVI climatology: before every label/test year
WEEK0 = pd.Timestamp("2000-01-03")


def _engine_weather():
    """backend/engine's FAO-56 functions (pm_eto, power_ea), loaded from the file without importing the package."""
    spec = importlib.util.spec_from_file_location("_engine_weather", ENGINE_DIR / "src" / "rotation_engine" / "weather.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_engine_weather"] = mod
    spec.loader.exec_module(mod)
    return mod


def _read(fid, name):
    p = cache(fid) / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def _date(s):
    return pd.to_datetime(s, utc=True, errors="coerce").dt.tz_localize(None).dt.normalize() \
        if getattr(pd.to_datetime(s, errors="coerce").dt, "tz", None) is not None else pd.to_datetime(s).dt.normalize()


# ------------------------------------------------------------------ daily context
def daily_context(fid: str) -> tuple[pd.DataFrame, dict]:
    """Daily Tmax/Tmin (station, POWER fill), Penman-Monteith ETo, IMERG rain and soil-moisture percentile."""
    src = {}
    pw = _read(fid, "power")
    pw["date"] = pd.to_datetime(pw["date"])
    nrt = _read(fid, "power_nrt")
    if nrt is not None:
        nrt["date"] = pd.to_datetime(nrt["date"])
        pw = pd.concat([pw, nrt[~nrt.date.isin(pw.date)]])
    pw = pw.replace(-999.0, np.nan).set_index("date").sort_index()
    d = pd.DataFrame(index=pd.date_range("2000-01-01", pw.index.max(), freq="D"))
    d = d.join(pw)
    st = _read(fid, "ncei")
    d["tmax_c"], d["tmin_c"], d["tmax_source"] = d.T2M_MAX, d.T2M_MIN, "power"
    if st is not None:
        st["date"] = pd.to_datetime(st["date"])
        st = st.dropna(subset=["tmax_c", "tmin_c"])
        st = st[st.tmax_c >= st.tmin_c].groupby("date")[["tmax_c", "tmin_c"]].mean()
        st = st.reindex(d.index)
        has = st.tmax_c.notna()
        d.loc[has, "tmax_c"], d.loc[has, "tmin_c"], d.loc[has, "tmax_source"] = st.tmax_c[has], st.tmin_c[has], "ncei_stations"
        src["tmax"] = "NOAA NCEI GHCN-D station mean (data/cache/<fid>/ncei.parquet); NASA POWER T2M_MAX where no station reports"
    else:
        src["tmax"] = "NASA POWER T2M_MAX (no NCEI station cache for this field)"
    # FAO-56 Penman-Monteith, exactly backend/engine's pm_eto (station T, POWER Rs, RH-based ea, u2)
    ew = _engine_weather()
    meta = read_json(cache(fid) / "power.meta.json")
    elev = float(meta.get("elevation_m") or 50.0)
    lat = field_polygon(fid).centroid.y
    ok = d[["ALLSKY_SFC_SW_DWN", "WS2M", "RH2M", "T2M_MAX", "T2M_MIN"]].notna().all(axis=1)
    eto = np.full(len(d), np.nan)
    sub = d[ok]
    eto[ok.values] = ew.pm_eto(sub.tmax_c.to_numpy(float), sub.tmin_c.to_numpy(float), ew.power_ea(sub),
                               sub.ALLSKY_SFC_SW_DWN.to_numpy(float), sub.WS2M.to_numpy(float), lat, elev,
                               sub.index.day_of_year.to_numpy())
    d["eto_pm_mm"] = eto
    src["eto"] = (f"FAO-56 Penman-Monteith (backend/engine weather.pm_eto): station Tmax/Tmin, POWER ALLSKY_SFC_SW_DWN, "
                  f"WS2M, RH2M; elevation {elev} m, latitude {lat:.3f}")
    im = _read(fid, "imerg")
    if im is not None:
        im["date"] = pd.to_datetime(im["date"])
        d["imerg_mm"] = im.groupby("date").precipitation.mean().reindex(d.index)
        src["imerg"] = "NASA GPM IMERG V07 daily (Final, Late after 2025-09-30), backend/nasa imerg.parquet"
    else:
        d["imerg_mm"] = np.nan
        src["imerg"] = "missing (no imerg.parquet for this field)"
    d["imerg_7d_mm"] = d.imerg_mm.rolling(7, min_periods=6).sum()
    d["imerg_30d_mm"] = d.imerg_mm.rolling(30, min_periods=27).sum()
    d["smap_pct"], d["sm_source"] = np.nan, None
    sm = _read(fid, "smap_l4")
    if sm is not None and len(sm) > 30:
        sm["date"] = pd.to_datetime(sm["date"])
        v = sm.groupby("date").sm_rootzone_pctl.mean().reindex(d.index)
        d.loc[v.notna(), "smap_pct"], d.loc[v.notna(), "sm_source"] = v[v.notna()], "smap_l4_rootzone_pctl"
    gr = _read(fid, "grace")
    if gr is not None:
        gr["date"] = pd.to_datetime(gr["date"])
        g = gr.groupby("date").rtzsm_inst.mean()
        g = g.reindex(pd.date_range(g.index.min(), g.index.max() + pd.Timedelta(days=6))).ffill(limit=6).reindex(d.index)
        fill = d.smap_pct.isna() & g.notna()
        d.loc[fill, "smap_pct"], d.loc[fill, "sm_source"] = g[fill], "grace_da_rootzone_pctl"
    src["smap_pct"] = ("NASA SMAP L4 SPL4SMGP.008 sm_rootzone_pctl (backend/nasa smap_l4.parquet); GRACE-DA "
                       "GRACEDADM_CLSM025GL_7D rtzsm_inst percentile where SMAP is missing")
    d["tmax_7d_c"] = d.tmax_c.rolling(7, min_periods=4).mean()
    d.index.name = "date"
    return d, src


# ------------------------------------------------------------------ MODIS
def modis_ndvi(fid: str) -> pd.DataFrame:
    """MOD13Q1 good-quality NDVI per point (field + clusters) with mid-composite dates."""
    rows = []
    nasa = _read(fid, "modis")
    if nasa is not None and "NDVI" in nasa and len(nasa) > 100:
        nasa["date"] = pd.to_datetime(nasa["date"])
        good = nasa.get("ndvi_good", pd.Series(True, index=nasa.index)).astype(bool)
        rows.append(pd.DataFrame({"point_id": "field", "date": nasa.date[good], "ndvi": nasa.NDVI[good],
                                  "src": "appeears_mod13q1"}))
    p = ai_cache(fid) / "modis_pc_mod13q1.parquet"
    if p.exists():
        m = pd.read_parquet(p)
        m = m[(m["product"] == "mod13q1") & m.ndvi_good.fillna(False).astype(bool)]
        m = m.assign(date=pd.to_datetime(m.date) + pd.Timedelta(days=8), src="planetary_computer_mod13q1")
        if rows:  # the AppEEARS series wins for the field point
            m = m[m.point_id != "field"]
        rows.append(m[["point_id", "date", "ndvi", "src"]])
    md = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["point_id", "date", "ndvi", "src"])
    md["date"] = pd.to_datetime(md["date"])
    return md


def modis_clim(md: pd.DataFrame) -> dict[str, np.ndarray]:
    """Per point: 366-day circular climatology (mean NDVI by 16-day composite, CLIM_YEARS), linearly interpolated."""
    out = {}
    md = md[md.date.dt.year.between(*CLIM_YEARS)]
    for pid, g in md.groupby("point_id"):
        c = g.groupby(g.date.dt.day_of_year).ndvi.mean()
        if len(c) < 15:
            continue
        x = np.r_[c.index.values - 366, c.index.values, c.index.values + 366]
        y = np.r_[c.values, c.values, c.values]
        out[pid] = np.interp(np.arange(1, 367), x, y)
    return out


def modis_lst(fid: str) -> pd.DataFrame:
    p = ai_cache(fid) / "modis_pc_mod11a2.parquet"
    if not p.exists():
        return pd.DataFrame(columns=["date", "lst_k"])
    m = pd.read_parquet(p)
    m = m[(m["product"] == "mod11a2") & (m.point_id == "field") & m.lst_good.fillna(False).astype(bool)]
    return pd.DataFrame({"date": pd.to_datetime(m.date), "lst_k": m.lst_k})


def ecostress(fid: str) -> pd.DataFrame | None:
    e = _read(fid, "ecostress")
    if e is None or not len(e):
        return None
    e["date"] = pd.to_datetime(e["date"]).dt.tz_localize(None).dt.normalize() if hasattr(pd.to_datetime(e["date"]).dt, "tz") \
        else pd.to_datetime(e["date"])
    return e


def ecostress_jet_bundle(fid: str) -> pd.DataFrame | None:
    """ECOSTRESS L3T JET ETdaily from backend/nasa's AppEEARS bundle CSV (data/cache/_appeears), if the parquet is
    not written yet. Cloud-flagged rows dropped."""
    import glob  # noqa: PLC0415
    fs = glob.glob(str(REPO / "data" / "cache" / "_appeears" / "ecostress_ECO_L3T_JET" / "*JET*results.csv"))
    if not fs:
        return None
    j = pd.concat(pd.read_csv(f) for f in fs)
    j = j[j.ID == fid]
    if not len(j):
        return None
    et = [c for c in j.columns if c.endswith("ETdaily")][0]
    cl = [c for c in j.columns if c.endswith("_cloud")]
    if cl:
        j = j[j[cl[0]].fillna(1) == 0]
    j = j[j[et].between(0, 15)]
    return pd.DataFrame({"date": pd.to_datetime(j.Date.str[:10]), "et_mm": j[et].astype(float)})


# ------------------------------------------------------------------ observation tables
def _ctx(df, ctx):
    return df.merge(ctx[["tmax_7d_c", "imerg_7d_mm", "smap_pct"]].reset_index(), on="date", how="left")


def cluster_obs(fid: str, ctx: pd.DataFrame, clim: dict) -> pd.DataFrame | None:
    c = ai_cache(fid)
    if not (c / "s2_clusters.parquet").exists():
        return None
    cl = pd.read_parquet(c / "clusters.parquet")
    s = pd.read_parquet(c / "s2_clusters.parquet")
    s = s[(s.clear_frac >= 0.99) & s.ndvi_med.notna() & (s.n_px40 >= 2)].copy()
    s = s.rename(columns={"cluster_id": "location_id", "ndvi_med": "ndvi", "ndwi_med": "ndwi", "bsi_med": "bsi",
                          "clear_frac": "valid_fraction", "scl4_frac": "scl_veg_frac", "scl5_frac": "scl_bare_frac",
                          "water_frac": "scl_water_frac"})
    s["date"] = pd.to_datetime(s["date"])
    s["year"] = s.date.dt.year
    s = s.merge(cl[["cluster_id", "block"] + [f"cdl_{y}" for y in YEARS]].rename(columns={"cluster_id": "location_id"}),
                on="location_id")
    s = s[s.year.isin(YEARS)]
    cdl = s[[f"cdl_{y}" for y in YEARS]].to_numpy()
    s["cdl_class"] = cdl[np.arange(len(s)), s.year.values - YEARS[0]]
    s["cdl_class"] = s.cdl_class.where(s.cdl_class >= 0)
    s = s.drop(columns=[f"cdl_{y}" for y in YEARS])
    doy = s.date.dt.day_of_year.values
    s["modis_ndvi_clim"] = [clim[p][d - 1] if p in clim else np.nan for p, d in zip(s.location_id, doy)]
    s["sensor"] = "s2"
    return _ctx(s, ctx).sort_values(["location_id", "date"]).reset_index(drop=True)


def field_obs(fid: str, ctx: pd.DataFrame, clim: dict) -> pd.DataFrame | None:
    frames = []
    s2 = _read(fid, "s2")
    if s2 is not None:
        s2 = s2[(s2.clear_frac >= 0.5) & (s2.n_valid >= 20) & s2.ndvi_med.notna()].copy()
        clear = s2[[f"scl_{k}" for k in S2_CLEAR]].sum(axis=1).replace(0, np.nan)
        s2["scl_veg_frac"], s2["scl_bare_frac"], s2["scl_water_frac"] = s2.scl_4 / clear, s2.scl_5 / clear, s2.scl_6 / clear
        s2["sensor"] = "s2"
        frames.append(s2)
    for name in ("hls_lpdaac", "hls"):
        h = _read(fid, name)
        if h is not None:
            h = h[(h.clear_frac >= 0.5) & (h.n_valid >= 20) & h.ndvi_med.notna()].copy()
            h["sensor"] = "hls_" + h.sensor.astype(str).str.lower() if "sensor" in h else "hls"
            h["hls_source"] = name
            frames.append(h)
    if not frames:
        return None
    d = pd.concat(frames, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])
    d = d.rename(columns={"ndvi_med": "ndvi", "ndwi_med": "ndwi", "bsi_med": "bsi", "clear_frac": "valid_fraction"})
    # one row per date and sensor family: S2 L2A first; one HLS row per date (LP DAAC copy preferred)
    d["fam"] = np.where(d.sensor == "s2", "s2", "hls")
    d["_pri"] = np.where(d.sensor == "s2", 0, np.where(d.get("hls_source") == "hls_lpdaac", 1, 2))
    d = d.sort_values(["date", "fam", "_pri", "n_valid"], ascending=[True, True, True, False]).drop_duplicates(["date", "fam"])
    d = d.drop(columns=["_pri"])
    d["location_id"] = fid
    d["year"] = d.date.dt.year
    hist = crop_history(fid)
    d["crop"] = d.year.map(hist)
    d["cdl_class"] = d.crop.map(CROP_NAME_TO_CODE)
    cl = clim.get("field")
    d["modis_ndvi_clim"] = cl[d.date.dt.day_of_year.values - 1] if cl is not None else np.nan
    dsw = _read(fid, "dswx")
    d["opera_water_frac"] = np.nan
    if dsw is not None:
        dsw["date"] = pd.to_datetime(dsw.datetime, utc=True).dt.tz_localize(None).dt.normalize()
        dsw = dsw[dsw.frac_clear >= 0.5].groupby("date").frac_water.max()
        d["opera_water_frac"] = d.date.map(dsw)
    keep = ["location_id", "date", "year", "sensor", "fam", "ndvi", "ndwi", "bsi", "valid_fraction", "n_valid",
            "water_frac", "scl_veg_frac", "scl_bare_frac", "scl_water_frac", "crop", "cdl_class", "modis_ndvi_clim",
            "opera_water_frac", "scene_id"]
    d = d[[k for k in keep if k in d.columns]]
    return _ctx(d, ctx).sort_values(["date", "fam"]).reset_index(drop=True)


# ------------------------------------------------------------------ weekly table (B6.2)
def _week(dates: pd.Series) -> pd.Series:
    return dates - pd.to_timedelta(dates.dt.day_of_week, unit="D")


def weekly(fid: str, ctx: pd.DataFrame, md: pd.DataFrame, fobs: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    src = {}
    last = ctx.index.max()
    weeks = pd.date_range(WEEK0, last - pd.Timedelta(days=6), freq="7D")
    w = pd.DataFrame({"week_start": weeks})
    w["location_id"] = fid
    c = ctx.copy()
    c["week_start"] = _week(c.index.to_series())
    agg = c.groupby("week_start").agg(t2m_max_c=("tmax_c", "mean"), eto_mm=("eto_pm_mm", "sum"),
                                      n_eto=("eto_pm_mm", "count"), smap_pct=("smap_pct", "mean"),
                                      sm_source=("sm_source", lambda x: x.dropna().mode().iloc[0] if x.notna().any() else None),
                                      tmax_source=("tmax_source", lambda x: x.mode().iloc[0]),
                                      imerg_7d_mm=("imerg_7d_mm", "last"), imerg_30d_mm=("imerg_30d_mm", "last"))
    agg.loc[agg.n_eto < 7, "eto_mm"] = np.nan
    w = w.merge(agg.drop(columns="n_eto").reset_index(), on="week_start", how="left")
    # MODIS NDVI at the field: interpolate good composites (mid-dates) to the week's middle, max 16 days away
    mf = md[md.point_id == "field"].sort_values("date")
    w["ndvi_modis"], w["ndvi_modis_source"] = np.nan, None
    if len(mf):
        t = mf.date.values.astype("datetime64[D]").astype(float)
        mid = (w.week_start + pd.Timedelta(days=3)).values.astype("datetime64[D]").astype(float)
        v = np.interp(mid, t, mf.ndvi.values, left=np.nan, right=np.nan)
        j = np.searchsorted(t, mid)
        near = np.minimum(np.abs(mid - t[np.clip(j - 1, 0, len(t) - 1)]), np.abs(t[np.clip(j, 0, len(t) - 1)] - mid))
        v[near > 16] = np.nan
        w["ndvi_modis"], w["ndvi_modis_source"] = v, mf.src.iloc[0]
    src["ndvi_modis"] = f"MOD13Q1.061 NDVI at the field centroid ({mf.src.iloc[0] if len(mf) else 'missing'}), good/marginal pixels"
    # field NDVI and water from the field windows (S2 first, HLS, then Landsat)
    w["ndvi_hls"], w["ndvi_hls_sensor"], w["water_obs"] = np.nan, None, False
    obs = []
    if fobs is not None:
        obs.append(fobs.assign(_pri=np.where(fobs.fam == "s2", 0, 1)))
    ls = _read(fid, "landsat")
    if ls is not None:
        ls = ls[(ls.clear_frac >= 0.5) & (ls.n_valid >= 20) & ls.ndvi_med.notna()].rename(
            columns={"ndvi_med": "ndvi", "ndwi_med": "ndwi"})
        obs.append(ls.assign(date=pd.to_datetime(ls.date), sensor="landsat", _pri=2))
    if obs:
        o = pd.concat(obs, ignore_index=True)
        o["water"] = (o.ndwi > 0.3) | (o.get("water_frac", pd.Series(0, index=o.index)).fillna(0) > 0.5)
        o["week_start"] = _week(o.date)
        best = o.groupby("week_start")._pri.transform("min")
        g = o[o._pri == best].groupby("week_start").agg(ndvi_hls=("ndvi", "mean"), ndvi_hls_sensor=("sensor", "first"))
        g["water_obs"] = o.groupby("week_start").water.any()
        w = w.drop(columns=["ndvi_hls", "ndvi_hls_sensor", "water_obs"]).merge(g.reset_index(), on="week_start", how="left")
        w["water_obs"] = w.water_obs.fillna(False).astype(bool)
    src["ndvi_hls"] = "field-median NDVI, S2 L2A (backend/field) first, then HLS (backend/nasa, nasa_open), then Landsat C2 L2"
    dsw = _read(fid, "dswx")
    w["opera_water_frac"] = np.nan
    if dsw is not None:
        dsw["date"] = pd.to_datetime(dsw.datetime, utc=True).dt.tz_localize(None).dt.normalize()
        dsw = dsw[dsw.frac_clear >= 0.5]
        dw = dsw.assign(week_start=_week(dsw.date)).groupby("week_start").frac_water.max()
        w["opera_water_frac"] = w.week_start.map(dw)
    w["water"] = w.water_obs | (w.opera_water_frac.fillna(0) >= 0.5)
    src["water"] = "S2/Landsat NDWI > 0.3 or SCL water > 50% on the field, or OPERA DSWx-HLS water >= 50% of the clear field"
    # LST: ECOSTRESS (per overpass, minus that day's Tmax) or MODIS MOD11A2 (8-day, minus mean Tmax of its 8 days)
    w["lst_k"], w["lst_minus_tmax_c"], w["lst_source"] = np.nan, np.nan, None
    eco = ecostress(fid)
    if eco is not None and "LST" in eco and eco.LST.notna().sum() > 20:
        e = eco[eco.LST.notna()].copy()
        if "cloud" in e:
            e = e[e.cloud.fillna(0) == 0]
        e["tmax"] = e.date.map(ctx.tmax_c)
        e["d"] = e.LST - 273.15 - e.tmax
        g = e.assign(week_start=_week(e.date)).groupby("week_start").agg(lst_k=("LST", "mean"), lst_minus_tmax_c=("d", "mean"))
        m = w.week_start.isin(g.index)
        w.loc[m, "lst_k"] = w.loc[m, "week_start"].map(g.lst_k)
        w.loc[m, "lst_minus_tmax_c"] = w.loc[m, "week_start"].map(g.lst_minus_tmax_c)
        w.loc[m, "lst_source"] = "ecostress_l2t_lste"
    ml = modis_lst(fid)
    if len(ml):
        tm8 = ctx.tmax_c.rolling(8, min_periods=6).mean().shift(-7)  # mean Tmax over the 8 days starting at date
        ml["d"] = ml.lst_k - 273.15 - ml.date.map(tm8)
        ml["week_start"] = _week(ml.date + pd.Timedelta(days=3))
        g = ml.groupby("week_start").agg(lst_k=("lst_k", "mean"), d=("d", "mean"))
        # MOD11A2 composites are 8-day: fill the following week too when it has no composite of its own
        g = g.reindex(w.week_start).ffill(limit=1)
        w["lst_k_modis"] = g.lst_k.values
        w["lst_minus_tmax_modis_c"] = g.d.values
        m = w.lst_source.isna() & w.lst_k_modis.notna()
        w.loc[m, "lst_k"], w.loc[m, "lst_minus_tmax_c"], w.loc[m, "lst_source"] = w.lst_k_modis[m], w.lst_minus_tmax_modis_c[m], "modis_mod11a2"
    src["lst"] = "ECOSTRESS ECO_L2T_LSTE.002 (backend/nasa) where cached, else MODIS MOD11A2.061 LST_Day_1km (Planetary Computer)"
    # ESI
    w["esi"], w["esi_source"] = np.nan, None
    if eco is not None and "ESI" in eco and eco.ESI.notna().sum() > 20:
        e = eco[eco.ESI.notna()]
        g = e.assign(week_start=_week(e.date)).groupby("week_start").ESI.mean()
        m = w.week_start.isin(g.index)
        w.loc[m, "esi"], w.loc[m, "esi_source"] = w.loc[m, "week_start"].map(g), "ecostress_l4t_esi"
    jet = ecostress_jet_bundle(fid)
    if jet is not None and len(jet) > 20:
        jet["eto"] = jet.date.map(ctx.eto_pm_mm)
        jet = jet[jet.eto > 0.5]
        jet["r"] = (jet.et_mm / jet.eto).clip(0, 1.5)
        g = jet.assign(week_start=_week(jet.date)).groupby("week_start").r.mean()
        m = w.esi.isna() & w.week_start.isin(g.index)
        w.loc[m, "esi"], w.loc[m, "esi_source"] = w.loc[m, "week_start"].map(g), "ecostress_jet_et_over_pm_eto"
    oe = _read(fid, "openet")
    if oe is not None and len(oe):
        oe["month"] = pd.to_datetime(oe.date).dt.to_period("M")
        eto_m = ctx.eto_pm_mm.groupby(ctx.index.to_period("M")).sum(min_count=25)
        r = (oe.set_index("month").et_mm / eto_m.reindex(oe.month).values).clip(0, 1.5)
        wm = (w.week_start + pd.Timedelta(days=3)).dt.to_period("M")
        m = w.esi.isna() & wm.isin(r.index)
        w.loc[m, "esi"], w.loc[m, "esi_source"] = wm[m].map(r).values, "openet_monthly_et_over_pm_eto"
    src["esi"] = ("ECOSTRESS ECO_L4T_ESI.002 where cached; else ECOSTRESS ECO_L3T_JET ETdaily / Penman-Monteith ETo "
                  "(same ratio as ESI, AppEEARS bundle in data/cache/_appeears); else OpenET Ensemble monthly ET / "
                  "Penman-Monteith ETo")
    # USDM D3+ (cumulative % of county area in D3 or worse), max over the field's counties
    w["usdm_d3plus_pct"] = np.nan
    us = [u for u in (_read(fid, "usdm"), _read(fid, "usdm_2026")) if u is not None]
    if us:
        u = pd.concat(us)
        u = u[u.stat == "cumulative"].copy()
        u["week_start"] = _week(pd.to_datetime(u.valid_start))
        g = u.groupby(["week_start", "fips"]).d3.max().groupby("week_start").max()
        w["usdm_d3plus_pct"] = w.week_start.map(g)
    src["usdm"] = "US Drought Monitor county statistics, cumulative % area in D3-D4 (data/cache/<fid>/usdm*.parquet)"
    # crop and season
    w["year"] = w.week_start.dt.year
    w["iso_week"] = w.week_start.dt.isocalendar().week.astype(int)
    hist = crop_history(fid)
    w["crop"] = w.year.map(hist)
    w["cdl_class"] = w.crop.map(CROP_NAME_TO_CODE)
    lo, hi = SEASON_WEEKS[family(fid)]
    w["in_season"] = w.iso_week.between(lo, hi).astype(int)
    return w, src


def coverage(df: pd.DataFrame, date_col: str, cols) -> dict:
    out = {}
    for c in cols:
        if c not in df:
            out[c] = {"n": 0}
            continue
        v = df[df[c].notna()]
        out[c] = {"n": int(len(v)), "first": v[date_col].min().strftime("%Y-%m-%d") if len(v) else None,
                  "last": v[date_col].max().strftime("%Y-%m-%d") if len(v) else None}
    return out


def build(fid: str) -> dict:
    ctx, src = daily_context(fid)
    md = modis_ndvi(fid)
    clim = modis_clim(md)
    c = ai_cache(fid)
    meta = {"field_id": fid, "generated_at": now(), "sources": src, "tables": {}}
    co = cluster_obs(fid, ctx, clim)
    if co is not None:
        co.to_parquet(c / "obs_clusters.parquet", index=False)
        meta["tables"]["obs_clusters"] = {"rows": len(co), "clusters": int(co.location_id.nunique()),
                                          "coverage": coverage(co, "date", ["ndvi", "scl_veg_frac", "modis_ndvi_clim",
                                                                            "tmax_7d_c", "imerg_7d_mm", "smap_pct", "cdl_class"])}
    fo = field_obs(fid, ctx, clim)
    if fo is not None:
        fo.to_parquet(c / "obs_field.parquet", index=False)
        meta["tables"]["obs_field"] = {"rows": len(fo), "by_sensor": fo.sensor.value_counts().to_dict(),
                                       "coverage": coverage(fo, "date", ["ndvi", "bsi", "scl_veg_frac", "modis_ndvi_clim",
                                                                         "opera_water_frac", "smap_pct", "imerg_7d_mm"])}
    wk, wsrc = weekly(fid, ctx, md, fo)
    wk.to_parquet(c / "weekly.parquet", index=False)
    meta["sources"].update(wsrc)
    meta["tables"]["weekly"] = {"rows": len(wk), "coverage": coverage(wk, "week_start", [
        "ndvi_modis", "ndvi_hls", "lst_k", "lst_minus_tmax_c", "esi", "smap_pct", "imerg_30d_mm", "t2m_max_c", "eto_mm",
        "opera_water_frac", "usdm_d3plus_pct", "crop"]),
        "source_counts": {k: wk[k].value_counts().to_dict() for k in ("lst_source", "esi_source", "sm_source", "tmax_source")
                          if k in wk}}
    write_json(c / "inputs.meta.json", meta)
    return meta


if __name__ == "__main__":
    for f in (sys.argv[1:] or field_ids()):
        m = build(f)
        t = m["tables"]
        print(f, {k: v["rows"] for k, v in t.items()}, t["weekly"]["source_counts"])
