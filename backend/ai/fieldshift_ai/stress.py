"""Crop-stress anomaly, reduced (spec B6.2): z-score composite vs IsolationForest on the preset field.

Unit: ISO week x preset field, in the existing crop's growing season (CAR rice: ISO weeks 23-39, Jun-Sep;
CAF forage: weeks 14-39, Apr-Sep), years 2016-2025 in which CDL shows the crop (CAR fallow years are skipped:
no crop, nothing to stress).

Features available without keys
  z_ndvi : weekly field NDVI (backend/field s2 + landsat medians; S2 preferred, Landsat fills weeks without S2)
           vs the same ISO week (+/-1) in the field's OTHER years with the same CDL crop (>= 3 years needed, else
           all other crop years of the preset), leave-one-year-out.
  z_tmax : weekly mean POWER T2M_MAX vs the same ISO week 1991-2020.
  z_eto  : weekly Hargreaves ETo (backend/regional daily_derived.parquet, from POWER) vs ISO week 1991-2020.
Blocked (spec lists them; need keys): z_LST (ECOSTRESS), ESI, z_SM (SMAP), IMERG 30-day anomaly, OpenET anomaly,
MODIS NDVI climatology. USDM county category is attached as context only.

Method A (zscore): composite = mean(-z_ndvi, z_tmax, z_eto) over available components; flag if composite > 1.0
or at least two components > 1.0.
Method B (isolation_forest): IsolationForest(n_estimators=200, contamination=0.10, random_state=0) on
[-z_ndvi, z_tmax, z_eto] of the preset's evaluated weeks.
Weeks with a water observation (NDWI > 0.3 or water mask > 50%) are labelled water and never flagged as stress.

Outputs out/<preset>/stress_weekly.json and two stress_anomaly ModelReports appended to out/<preset>/models.json.
Usage: uv run python -m fieldshift_ai.stress [preset ...]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .common import FIELD_DIR, PRESETS, REGIONAL_DIR, cache, now, out, read_json, write_json

SEASON = {"car_colusa_rice": (23, 39), "caf_tulare_forage": (14, 39)}
CROPS = {"car_colusa_rice": {"Rice"}, "caf_tulare_forage": {"Alfalfa", "Corn"}}
EVENTS = {"julaug_2021": (2021, 7, 8), "julaug_2022": (2022, 7, 8)}
HEATWAVE_2022 = ("2022-08-30", "2022-09-10")  # Sept 2022 California heat wave, dates U
CLIM = (1991, 2020)
FEATS = ["neg_z_ndvi", "z_tmax", "z_eto"]


def iso(df, col="date"):
    c = df[col].dt.isocalendar()
    df["iso_year"], df["iso_week"] = c.year.astype(int), c.week.astype(int)
    return df


def weekly_ndvi(preset):
    frames = []
    for src in ("s2", "landsat"):
        d = pd.read_parquet(cache(preset) / f"{src}.parquet")
        d = d[(d.clear_frac >= 0.5) & (d.n_valid >= 20) & d.ndvi_med.notna()].copy()
        d["src"] = src
        frames.append(d[["date", "src", "ndvi_med", "ndwi_med", "water_frac"]])
    d = pd.concat(frames)
    d["date"] = pd.to_datetime(d["date"])
    d["water"] = (d.ndwi_med > 0.3) | (d.water_frac.fillna(0) > 0.5)
    d = iso(d)
    rows = []
    for (y, w), g in d.groupby(["iso_year", "iso_week"]):
        s2 = g[g.src == "s2"]
        use = s2 if len(s2) else g
        rows.append({"iso_year": y, "iso_week": w, "ndvi": float(use.ndvi_med.mean()), "n_obs": int(len(use)),
                     "ndvi_sensor": "s2" if len(s2) else "landsat", "water": bool(g.water.any())})
    return pd.DataFrame(rows)


def weekly_weather(preset):
    w = pd.read_parquet(REGIONAL_DIR / "out" / preset / "daily_derived.parquet")[["date", "T2M_MAX", "eto_hargreaves_mm"]]
    w["date"] = pd.to_datetime(w["date"])
    w = iso(w)
    g = w.groupby(["iso_year", "iso_week"]).agg(tmax=("T2M_MAX", "mean"), eto=("eto_hargreaves_mm", "sum"),
                                                n=("date", "size")).reset_index()
    g = g[g.n == 7]
    clim = g[g.iso_year.between(*CLIM)].groupby("iso_week").agg(tm=("tmax", "mean"), ts=("tmax", "std"),
                                                                em=("eto", "mean"), es=("eto", "std"))
    g = g.join(clim, on="iso_week")
    g["z_tmax"] = (g.tmax - g.tm) / g.ts
    g["z_eto"] = (g.eto - g.em) / g.es
    return g[["iso_year", "iso_week", "tmax", "eto", "z_tmax", "z_eto"]]


def weekly_usdm(preset):
    u = pd.read_parquet(cache(preset) / "usdm.parquet")
    u["date"] = pd.to_datetime(u.valid_start)
    u = iso(u)
    cat = np.select([u.d4 > 0, u.d3 > 0, u.d2 > 0, u.d1 > 0, u.d0 > 0], ["D4", "D3", "D2", "D1", "D0"], "none")
    u["usdm_max_cat"] = cat
    return u[["iso_year", "iso_week", "usdm_max_cat"]].drop_duplicates(["iso_year", "iso_week"])


def run(preset):
    hist = read_json(FIELD_DIR / "out" / preset / "crop_history.json")["by_year"]
    crop_years = {int(y): c for y, c in hist.items() if c in CROPS[preset] and 2016 <= int(y) <= 2025}
    wk = weekly_ndvi(preset)
    lo, hi = SEASON[preset]
    # leave-one-year-out same-week (+/-1) NDVI climatology from the field's other years with the same crop
    z, ref = [], []
    for r in wk.itertuples():
        if r.iso_year not in crop_years or r.water:
            z.append(np.nan); ref.append(None); continue
        same = [y for y, c in crop_years.items() if c == crop_years[r.iso_year] and y != r.iso_year]
        pool_years, how = (same, "same crop") if len(same) >= 3 else (
            [y for y in crop_years if y != r.iso_year], "all crop years (same-crop years < 3)")
        v = wk[wk.iso_year.isin(pool_years) & (wk.iso_week - r.iso_week).abs().le(1) & ~wk.water].ndvi
        if len(v) >= 3 and v.std() > 0:
            z.append((r.ndvi - v.mean()) / v.std()); ref.append(how)
        else:
            z.append(np.nan); ref.append(how)
    wk["z_ndvi"], wk["ndvi_reference"] = z, ref
    wx = weekly_weather(preset)
    d = wx.merge(wk, on=["iso_year", "iso_week"], how="left")
    d = d.merge(weekly_usdm(preset), on=["iso_year", "iso_week"], how="left")
    d = d[d.iso_year.isin(list(crop_years)) & d.iso_week.between(lo, hi)].copy()
    d["water"] = d.water.fillna(False).astype(bool)
    d["neg_z_ndvi"] = -d.z_ndvi
    d["week_start"] = [pd.Timestamp.fromisocalendar(int(y), int(w), 1) for y, w in zip(d.iso_year, d.iso_week)]
    d["month"] = d.week_start.dt.month
    # Method A
    comp = d[FEATS]
    d["composite_z"] = comp.mean(axis=1, skipna=True)
    d["n_components_gt1"] = (comp > 1.0).sum(axis=1)
    d["flag_zscore"] = ((d.composite_z > 1.0) | (d.n_components_gt1 >= 2)) & ~d.water
    # Method B
    ev = d[~d.water & d[FEATS].notna().all(axis=1)]
    iforest = IsolationForest(n_estimators=200, contamination=0.10, random_state=0).fit(ev[FEATS])
    d["if_score"] = np.nan
    d.loc[ev.index, "if_score"] = -iforest.score_samples(ev[FEATS])
    d["flag_iforest"] = False
    d.loc[ev.index, "flag_iforest"] = iforest.predict(ev[FEATS]) == -1
    d["evaluated"] = d.index.isin(ev.index)
    e = d[d.evaluated]

    def ev_count(col, y, m0, m1):
        if y not in crop_years:
            return None
        return int(e[(e.iso_year == y) & e.month.between(m0, m1)][col].sum())

    agree = float((e.flag_zscore == e.flag_iforest).mean())
    both = int((e.flag_zscore & e.flag_iforest).sum())
    hw = e[(e.week_start >= pd.Timestamp(HEATWAVE_2022[0]) - pd.Timedelta(days=6)) & (e.week_start <= HEATWAVE_2022[1])]
    cool = e[e.z_tmax < -1.0]
    reports = []
    for method, col in (("zscore", "flag_zscore"), ("isolation_forest", "flag_iforest")):
        other = "flag_iforest" if col == "flag_zscore" else "flag_zscore"
        met = {"weeks_evaluated": int(len(e)), "weeks_flagged": int(e[col].sum()),
               "flagged_pct": round(100 * float(e[col].mean()), 1),
               "julaug_2021_flagged_weeks": ev_count(col, 2021, 7, 8),
               "julaug_2022_flagged_weeks": ev_count(col, 2022, 7, 8),
               "sept2022_heatwave_weeks_flagged": int(hw[col].sum()) if len(hw) else None,
               "sept2022_heatwave_weeks_evaluated": int(len(hw)),
               "cool_weeks": int(len(cool)), "cool_week_flags": int(cool[col].sum()),
               "agreement_pct": round(100 * agree, 1), "both_flag_weeks": both,
               "water_weeks_in_season": int(d.water.sum()), "water_weeks_flagged": 0}
        reports.append({
            "id": f"stress_{'z' if method == 'zscore' else 'if'}_{preset}_v1", "task": "stress_anomaly",
            "method": method, "features": FEATS + (["usdm_max_cat (context only)"] if method == "zscore" else []),
            "labels": "none (unsupervised); checked against Jul-Aug 2021/2022 drought and Sept 2022 heat wave (U dates)",
            "split": {"type": "unsupervised", "train_years": sorted(crop_years), "test_years": sorted(crop_years)},
            "metrics": met, "feature_importance": [],
            "disagreement_with": {"isolation_forest" if method == "zscore" else "zscore": round(1 - agree, 4)},
            "notes": ("Reduced B6.2: only Sentinel-2/Landsat NDVI (field vs its own same-week history, leave-one-year-out) "
                      "and POWER Tmax / Hargreaves ETo anomalies. Blocked: ECOSTRESS LST, ESI, SMAP, IMERG, OpenET, MODIS "
                      "(Earthdata / OpenET keys). Tmax and Hargreaves ETo are strongly correlated, so 'two components "
                      "> 1' is mostly a heat rule. The isolation forest is two-sided (cool/green weeks can be outliers); "
                      "see cool_week_flags. " + ("" if 2022 in crop_years else
                      "2022 was fallow on this field (CDL), so Jul-Aug 2022 is not a crop week and is not evaluated.")),
        })
    weeks = []
    for r in d.sort_values(["iso_year", "iso_week"]).itertuples():
        drivers = [f for f in FEATS if pd.notna(getattr(r, f)) and getattr(r, f) > 1.0]
        weeks.append({"iso_year": int(r.iso_year), "iso_week": int(r.iso_week), "week_start": r.week_start.strftime("%Y-%m-%d"),
                      "crop": crop_years.get(int(r.iso_year)),
                      "ndvi": None if pd.isna(r.ndvi) else round(float(r.ndvi), 3),
                      "ndvi_sensor": None if pd.isna(r.ndvi) else r.ndvi_sensor,
                      "z_ndvi": None if pd.isna(r.z_ndvi) else round(float(r.z_ndvi), 2),
                      "ndvi_reference": r.ndvi_reference if isinstance(r.ndvi_reference, str) else None,
                      "tmax_c": round(float(r.tmax), 1), "z_tmax": round(float(r.z_tmax), 2),
                      "eto_mm_week": round(float(r.eto), 1), "z_eto": round(float(r.z_eto), 2),
                      "composite_z": None if pd.isna(r.composite_z) else round(float(r.composite_z), 2),
                      "if_score": None if pd.isna(r.if_score) else round(float(r.if_score), 3),
                      "water": bool(r.water), "evaluated": bool(r.evaluated),
                      "flag_zscore": bool(r.flag_zscore), "flag_iforest": bool(r.flag_iforest),
                      "status": "water" if r.water else ("both" if r.flag_zscore and r.flag_iforest else
                                                         "one" if r.flag_zscore or r.flag_iforest else "none"),
                      "drivers": drivers, "usdm_max_cat": r.usdm_max_cat if isinstance(r.usdm_max_cat, str) else None})
    write_json(out(preset) / "stress_weekly.json", {
        "preset_id": preset, "generated_at": now(), "season_iso_weeks": [lo, hi], "crop_years": crop_years,
        "method": {"zscore": "composite = mean(-z_ndvi, z_tmax, z_eto); flag if > 1.0 or >= 2 components > 1.0",
                   "isolation_forest": "IsolationForest(n_estimators=200, contamination=0.10, random_state=0)",
                   "water": "weeks with any water observation are 'water', never stress",
                   "climatology": f"weather: ISO week {CLIM[0]}-{CLIM[1]} (POWER); NDVI: field's other crop years, ISO week +/-1"},
        "blocked_inputs": ["ECOSTRESS LST (Earthdata)", "ESI (Earthdata)", "SMAP (Earthdata)", "IMERG (Earthdata)",
                           "OpenET (OpenET API key)", "MODIS NDVI climatology (Earthdata)"],
        "sources": [{"id": "power", "url": "https://power.larc.nasa.gov/", "verified": True},
                    {"id": "s2_l2a_mpc", "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", "verified": True},
                    {"id": "landsat_c2_l2_mpc", "url": "https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2", "verified": True},
                    {"id": "usdm", "url": "https://droughtmonitor.unl.edu/", "verified": True}],
        "weeks": weeks})
    p = out(preset) / "models.json"
    doc = read_json(p) if p.exists() else {"location_id": preset, "items": []}
    doc["items"] = [i for i in doc["items"] if i["task"] != "stress_anomaly"] + reports
    doc["generated_at"] = now()
    write_json(p, doc)
    for r in reports:
        m = r["metrics"]
        print(f"{preset} {r['method']:16s} evaluated {m['weeks_evaluated']} flagged {m['weeks_flagged']} "
              f"JulAug21 {m['julaug_2021_flagged_weeks']} JulAug22 {m['julaug_2022_flagged_weeks']} "
              f"heatwave22 {m['sept2022_heatwave_weeks_flagged']}/{m['sept2022_heatwave_weeks_evaluated']} "
              f"cool-week flags {m['cool_week_flags']}/{m['cool_weeks']} agreement {m['agreement_pct']}%")


if __name__ == "__main__":
    for p in (sys.argv[1:] or PRESETS):
        run(p)
