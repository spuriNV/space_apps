"""B6.2 crop-stress weeks: z-score composite vs isolation forest (planner-spec.md B6.2; check B10.1 #9).

From the `ds` branch library by spuriNV (field_shift_ai/field_shift_models/fieldshift_models/stress.py): the six
weekly z-scores, method A (composite of -z_NDVI, z_LST, -z_ESI, -z_SM > 1.0, or two of z_NDVI < -1, z_LST > +1,
z_SM < -1), method B (IsolationForest, 200 trees, 10% contamination, missing z = 0), the both / one / none strip,
the driving features of each flagged week, the event-recall / wet-cool-week evaluation, "fallow is not stress" and
the evidence sentence. Changed here:
  * inputs are the real NASA series built by inputs.py from cached, scripted data (MODIS NDVI 2000-, ECOSTRESS or
    MODIS LST minus station Tmax, ECOSTRESS ESI or its ET/ETo ratio, SMAP L4 or GRACE-DA root-zone percentile,
    IMERG 30-day rain, Penman-Monteith ETo) instead of hand-downloaded CSVs and stand-ins;
  * events are US Drought Monitor D3+ weeks (>= 50% of the county in extreme or exceptional drought, from the cached
    USDM county statistics) instead of the assumed DEFAULT_EVENTS;
  * same-week climatologies are leave-one-year-out and use only years with the same crop on the field (CDL);
  * the isolation forest is fitted on crop years only (fallow weeks are scored, never fitted, never in the evidence);
  * water weeks (S2/Landsat or NASA OPERA DSWx) are "water", never stress;
  * reasons are written in plain words with their NASA source.

Unit: ISO week x field, in-season weeks (rice ISO weeks 23-39, forage 14-39), 2015-2026.
Outputs out/<fid>/stress_weekly.json, out/<fid>/stress_summary.json and two stress_anomaly ModelReports appended to
out/<fid>/models.json. Usage: uv run python -m fieldshift_ai.stress [fid ...]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import IsolationForest

from .common import ai_cache, crop_history, field_ids, family, model_report, now, out, read_json, write_json
from .inputs import SEASON_WEEKS

ANALYSIS_YEARS = list(range(2015, 2027))
COMPOSITE_THR, Z_THR = 1.0, 1.0
IF_N_ESTIMATORS, IF_CONTAMINATION = 200, 0.10
USDM_D3_EVENT_PCT = 50.0      # an event week: >= 50% of the field's county in D3-D4 (cumulative USDM statistics)
MIN_POOL_YEARS = 5            # same-crop climatology needs >= 5 other years, else all other crop years

Z_FEATURES = ["z_ndvi", "z_lst", "z_esi", "z_sm", "z_eto", "z_imerg30"]
STRESS_SIGN = {"z_ndvi": -1, "z_lst": +1, "z_esi": -1, "z_sm": -1, "z_eto": +1, "z_imerg30": -1}
SOURCE_WORDS = {"modis_mod13q1": "NASA MODIS", "s2": "Sentinel-2", "hls": "NASA HLS", "landsat": "Landsat",
                "ecostress_l2t_lste": "NASA ECOSTRESS", "modis_mod11a2": "NASA MODIS",
                "ecostress_l4t_esi": "NASA ECOSTRESS", "ecostress_jet_et_over_pm_eto": "NASA ECOSTRESS",
                "openet_monthly_et_over_pm_eto": "OpenET", "smap_l4_rootzone_pctl": "NASA SMAP",
                "grace_da_rootzone_pctl": "NASA GRACE-DA"}
TEXT = {"z_ndvi": ("weaker growth than in its other {crop} years", "greener than usual"),
        "z_lst": ("hot leaves for the air temperature", "cool leaves for the air temperature"),
        "z_esi": ("crop using less water than the weather allows", "crop using more water than usual"),
        "z_sm": ("dry soil", "wet soil"),
        "z_eto": ("very thirsty air (high reference evapotranspiration)", "mild, low-demand weather"),
        "z_imerg30": ("little rain in the last 30 days", "more rain than usual in the last 30 days")}
CREDIT = "Stress method, reasons and evidence sentence: spuriNV (ds branch); real NASA inputs and Drought Monitor events: backend/ai."


# =================================================================================================== z-scores
def _pool_years(year, crop, crops: dict, years_with_data):
    """Other years with the same crop (>= MIN_POOL_YEARS), else every other year with a crop (not fallow);
    years before the crop record count as the field's usual crop only if the family is a perennial rotation."""
    same = [y for y in years_with_data if y != year and crops.get(y) == crop]
    if len(same) >= MIN_POOL_YEARS:
        return same, "same crop"
    other = [y for y in years_with_data if y != year and crops.get(y) not in (None, "Fallow/Idle Cropland")]
    return other, "all crop years"


def z_same_week(df: pd.DataFrame, col: str, crops: dict | None, rows: pd.Index, window=1, min_n=3):
    """Leave-one-year-out same-ISO-week (+/- window) z-score for `rows`. crops=None: all other years (weather)."""
    v = df[[col, "year", "iso_week"]].dropna()
    yrs = sorted(v.year.unique())
    z, how = pd.Series(np.nan, index=rows), pd.Series(None, index=rows, dtype=object)
    for i in rows:
        x = df.at[i, col]
        if pd.isna(x):
            continue
        y, w = df.at[i, "year"], df.at[i, "iso_week"]
        if crops is None:
            pool, h = [k for k in yrs if k != y], "all other years"
        else:
            pool, h = _pool_years(y, crops.get(y), crops, yrs)
        ref = v[v.year.isin(pool) & ((v.iso_week - w).abs() <= window)][col]
        if len(ref) >= min_n and ref.std() > 0:
            z[i], how[i] = (x - ref.mean()) / ref.std(), h
    return z, how


def z_record(df: pd.DataFrame, col: str, crops: dict, rows: pd.Index, season: pd.Series, min_n=8):
    """Leave-one-year-out z against the field's own in-season record in years with the same crop (sparse series:
    ECOSTRESS, ESI ratios)."""
    v = df[season & df[col].notna()][[col, "year"]]
    yrs = sorted(v.year.unique())
    z = pd.Series(np.nan, index=rows)
    for i in rows:
        x = df.at[i, col]
        if pd.isna(x):
            continue
        y = df.at[i, "year"]
        pool, _ = _pool_years(y, crops.get(y), crops, yrs)
        ref = v[v.year.isin(pool)][col]
        if len(ref) >= min_n and ref.std() > 0:
            z[i] = (x - ref.mean()) / ref.std()
    return z


def build_weekly_features(w: pd.DataFrame, crops: dict) -> pd.DataFrame:
    df = w.copy().reset_index(drop=True)
    df["week_start"] = pd.to_datetime(df.week_start)
    iso = df.week_start.dt.isocalendar()
    df["iso_year"], df["iso_week"] = iso.year.astype(int), iso.week.astype(int).clip(upper=52)
    df["year"] = df.iso_year
    season = df.in_season.astype(bool)
    rows = df.index[season & df.year.isin(ANALYSIS_YEARS)]
    # z_NDVI: MODIS (2000-) and the field's own S2/HLS/Landsat series, each vs its own same-week record; mean (ds)
    zm, how = z_same_week(df, "ndvi_modis", crops, rows)
    zh, _ = z_same_week(df, "ndvi_hls", crops, rows)
    df["z_ndvi_modis"], df["z_ndvi_field"] = zm, zh
    df["z_ndvi"] = pd.concat([zm, zh], axis=1).mean(axis=1, skipna=True)
    df["ndvi_reference"] = how
    # z_LST: (LST - station Tmax); MODIS vs same-week record, ECOSTRESS vs its in-season record; ECOSTRESS wins
    z_lst = pd.Series(np.nan, index=df.index)
    if "lst_minus_tmax_modis_c" in df:
        z_lst = z_same_week(df, "lst_minus_tmax_modis_c", crops, rows)[0].reindex(df.index)
    if (df.lst_source == "ecostress_l2t_lste").any():
        eco = df.lst_minus_tmax_c.where(df.lst_source == "ecostress_l2t_lste")
        ze = z_record(df.assign(_e=eco), "_e", crops, rows, season).reindex(df.index)
        z_lst = ze.where(ze.notna(), z_lst)
    df["z_lst"] = z_lst
    # z_ESI: per source vs its own in-season record (sources are not mixed in one reference)
    z_esi = pd.Series(np.nan, index=df.index)
    for s in ("openet_monthly_et_over_pm_eto", "ecostress_jet_et_over_pm_eto", "ecostress_l4t_esi"):  # last wins
        if (df.esi_source == s).any():
            zs = z_record(df.assign(_s=df.esi.where(df.esi_source == s)), "_s", crops, rows, season).reindex(df.index)
            z_esi = zs.where(zs.notna(), z_esi)
    df["z_esi"] = z_esi
    p = (df.smap_pct / 100.0).clip(0.001, 0.999)
    df["z_sm"] = pd.Series(norm.ppf(p), index=df.index).where(df.smap_pct.notna())
    df["z_eto"] = z_same_week(df, "eto_mm", None, rows)[0].reindex(df.index)
    df["z_imerg30"] = z_same_week(df, "imerg_30d_mm", None, rows)[0].reindex(df.index)
    return df


# =================================================================================================== methods
def method_a_zscore(df: pd.DataFrame) -> pd.DataFrame:
    comp = pd.concat([-df.z_ndvi, df.z_lst, -df.z_esi, -df.z_sm], axis=1).mean(axis=1, skipna=True)
    two = ((df.z_ndvi < -Z_THR).astype(int) + (df.z_lst > Z_THR).astype(int) + (df.z_sm < -Z_THR).astype(int)) >= 2
    return pd.DataFrame({"composite_z": comp, "flag_zscore": (comp > COMPOSITE_THR) | two}, index=df.index)


def field_only_zscore(df: pd.DataFrame) -> pd.Series:
    """Diagnostic: method A with only the field-scale signals (NDVI, LST - Tmax, ESI). The Drought Monitor itself uses
    modelled / GRACE-based soil moisture, so recall of D3+ weeks by the full method is partly shared input."""
    comp = pd.concat([-df.z_ndvi, df.z_lst, -df.z_esi], axis=1).mean(axis=1, skipna=True)
    two = ((df.z_ndvi < -Z_THR).astype(int) + (df.z_lst > Z_THR).astype(int) + (df.z_esi < -Z_THR).astype(int)) >= 2
    return (comp > COMPOSITE_THR) | two


def method_b_isolation_forest(df: pd.DataFrame, fit_mask: pd.Series, seed=0, leave_one_year_out=False) -> pd.DataFrame:
    X = df[Z_FEATURES].fillna(0.0)
    out = pd.DataFrame({"if_score": np.nan, "flag_iforest": False}, index=df.index)
    if leave_one_year_out:
        for yr in df.year.unique():
            tr = X[fit_mask & (df.year != yr)]
            te = X[df.year == yr]
            if len(tr) < 20:
                continue
            m = IsolationForest(n_estimators=IF_N_ESTIMATORS, contamination=IF_CONTAMINATION, random_state=seed).fit(tr)
            out.loc[te.index, "if_score"] = m.decision_function(te)
            out.loc[te.index, "flag_iforest"] = m.predict(te) == -1
    else:
        m = IsolationForest(n_estimators=IF_N_ESTIMATORS, contamination=IF_CONTAMINATION, random_state=seed).fit(X[fit_mask])
        out["if_score"] = m.decision_function(X)
        out["flag_iforest"] = m.predict(X) == -1
    out["flag_iforest"] = out.flag_iforest.astype(bool)
    return out


def _src_word(row, f):
    key = {"z_ndvi": "ndvi_modis_source", "z_lst": "lst_source", "z_esi": "esi_source", "z_sm": "sm_source"}.get(f)
    if f == "z_ndvi":
        parts = (["NASA MODIS"] if pd.notna(row.get("z_ndvi_modis")) else []) + \
                ([SOURCE_WORDS.get(str(row.get("ndvi_hls_sensor")), "Sentinel-2")] if pd.notna(row.get("z_ndvi_field")) else [])
        return " and ".join(parts)
    if f == "z_eto":
        return "NOAA stations and NASA POWER"
    if f == "z_imerg30":
        return "NASA GPM IMERG"
    v = row.get(key)
    return SOURCE_WORDS.get(str(v), str(v)) if isinstance(v, str) else ""


def reasons(row, crop) -> tuple[list[str], list[str]]:
    """ds _driving_features in plain words: features whose stress-direction z > 1, strongest first; for a flagged
    week with none (an isolation-forest outlier in the non-stress direction), the two largest |z| as 'unusual'."""
    hits = sorted([(STRESS_SIGN[f] * row[f], f) for f in Z_FEATURES if pd.notna(row[f]) and STRESS_SIGN[f] * row[f] > Z_THR],
                  reverse=True)
    if hits:
        return [f for _, f in hits], [f"{TEXT[f][0].format(crop=(crop or 'crop').lower())} ({_src_word(row, f)})"
                                      for _, f in hits]
    big = sorted([(abs(row[f]), f) for f in Z_FEATURES if pd.notna(row[f])], reverse=True)[:2]
    return [], [f"unusual week: {TEXT[f][1 if STRESS_SIGN[f] * row[f] < 0 else 0].format(crop=(crop or 'crop').lower())} "
                f"({_src_word(row, f)})" for _, f in big]


# =================================================================================================== evaluation
def usdm_events(g: pd.DataFrame) -> list[dict]:
    """Contiguous D3+ episodes among the scored weeks, one per season."""
    ev = []
    for y, gy in g[g.usdm_d3plus_pct >= USDM_D3_EVENT_PCT].groupby("year"):
        ev.append({"name": f"{y} season, Drought Monitor D3+ weeks", "year": int(y),
                   "start": gy.week_start.min().strftime("%Y-%m-%d"), "end": gy.week_start.max().strftime("%Y-%m-%d"),
                   "weeks_in_window": int(len(gy)), "flagged_zscore": int(gy.flag_zscore.sum()),
                   "flagged_iforest": int(gy.flag_iforest.sum()), "flagged_both": int((gy.flag_zscore & gy.flag_iforest).sum()),
                   "recall_zscore": float(gy.flag_zscore.mean()), "recall_iforest": float(gy.flag_iforest.mean())})
    return ev


def evaluate(g: pd.DataFrame, loyo: pd.Series) -> dict:
    """g: scored weeks (in season, crop year, not water)."""
    r = {"weeks_scored": int(len(g))}
    for m in ("zscore", "iforest"):
        r[f"flag_rate_{m}"] = float(g[f"flag_{m}"].mean()) if len(g) else None
    r["agreement"] = float((g.flag_zscore == g.flag_iforest).mean()) if len(g) else None
    d3 = g.usdm_d3plus_pct >= USDM_D3_EVENT_PCT
    calm = g.usdm_d3plus_pct == 0
    r["usdm_d3_weeks"], r["usdm_no_d3_weeks"] = int(d3.sum()), int(calm.sum())
    for m in ("zscore", "iforest"):
        r[f"recall_usdm_d3_{m}"] = float(g[d3][f"flag_{m}"].mean()) if d3.any() else None
        r[f"flag_rate_no_drought_{m}"] = float(g[calm][f"flag_{m}"].mean()) if calm.any() else None
        rec, base = r[f"recall_usdm_d3_{m}"], r[f"flag_rate_no_drought_{m}"]
        r[f"lift_usdm_d3_{m}"] = (rec / base) if rec is not None and base else None
    r["recall_usdm_d3_zscore_field_only"] = float(g[d3].flag_zscore_field.mean()) if d3.any() else None
    r["flag_rate_no_drought_zscore_field_only"] = float(g[calm].flag_zscore_field.mean()) if calm.any() else None
    r["recall_usdm_d3_iforest_loyo"] = float(loyo[g[d3].index].mean()) if d3.any() else None
    r["flag_rate_no_drought_iforest_loyo"] = float(loyo[g[calm].index].mean()) if calm.any() else None
    r["events"] = usdm_events(g)
    wet = (g.z_sm > 0) | (g.z_imerg30 > 0)
    cool = g.z_eto < 0
    wc = g[wet & cool]
    r["wet_cool_weeks"] = int(len(wc))
    for m in ("zscore", "iforest"):
        r[f"false_positive_proxy_{m}"] = float(wc[f"flag_{m}"].mean()) if len(wc) else None
    return r


def evidence_line(g: pd.DataFrame, latest=False) -> str:
    """ds evidence_line in plain words: weeks flagged by both methods in crop years (fallow excluded)."""
    if not len(g):
        return "No growing-season weeks checked yet."
    yrs = f"{g.year.min()}-{g.year.max()}" if g.year.nunique() > 1 else f"the {g.year.iloc[0]} season"
    both = g[g.flag_zscore & g.flag_iforest]
    if both.empty:
        return f"Neither stress check flagged the same week over {yrs}."
    d = both.week_start
    part = np.where(d.dt.day <= 15, "early", "late")
    mode = pd.Series([f"{p} {m}" for p, m in zip(part, d.dt.strftime("%B"))]).mode().iloc[0]
    why = pd.Series([x for r in both.reasons for x in r if not x.startswith("unusual")]).value_counts()
    tail = f"; most often {why.index[0]}" + (f" and {why.index[1]}" if len(why) > 1 else "") if len(why) else ""
    n = len(both)
    return (f"The crop looked stressed in {n} week{'s' if n != 1 else ''} over {yrs} (both checks agree), "
            f"mostly {mode}{tail}.")


def checks_9(g_all: pd.DataFrame, crops: dict) -> dict:
    """Spec B10.1 #9: both methods flag >= 2 weeks in Jul-Aug 2021 and 2022 (crop years only); 2023 water weeks
    are water, not stress. Plus the ds California check: the fallow year looks anomalous but is not stress."""
    out = {}
    for yr in (2021, 2022):
        if crops.get(yr) in (None, "Fallow/Idle Cropland"):
            out[f"julaug_{yr}"] = {"applicable": False, "note": f"{yr}: {crops.get(yr)} on this field (no crop to stress)"}
            continue
        w = g_all[(g_all.year == yr) & g_all.week_start.dt.month.isin([7, 8]) & g_all.evaluated]
        out[f"julaug_{yr}"] = {"applicable": True, "flagged_zscore": int(w.flag_zscore.sum()),
                               "flagged_iforest": int(w.flag_iforest.sum()), "weeks": int(len(w)),
                               "pass": bool(w.flag_zscore.sum() >= 2 and w.flag_iforest.sum() >= 2)}
    w23 = g_all[(g_all.year == 2023) & g_all.water]
    out["flood_2023_water_not_stress"] = {"water_weeks": int(len(w23)),
                                          "flagged": int((w23.status.isin(["one", "both"])).sum()),
                                          "pass": bool(not w23.status.isin(["one", "both"]).any())}
    fy = g_all[g_all.no_crop & ~g_all.water]
    out["fallow_not_stress"] = {"fallow_years": sorted(fy.year.unique().tolist()), "weeks": int(len(fy)),
                                "flag_rate_zscore": float(fy.flag_zscore.mean()) if len(fy) else None,
                                "flag_rate_iforest": float(fy.flag_iforest.mean()) if len(fy) else None,
                                "note": "fallow weeks are scored (they look anomalous) but are shown as fallow, "
                                        "never as crop stress, and are left out of the evidence sentence"}
    return out


# =================================================================================================== main
def _r(x, n=2):
    return None if x is None or pd.isna(x) else round(float(x), n)


def run(fid: str, seed: int = 0):
    p = ai_cache(fid) / "weekly.parquet"
    if not p.exists():
        print(f"{fid}: no weekly.parquet (run fieldshift_ai.inputs first)")
        return None
    w = pd.read_parquet(p)
    crops = crop_history(fid)
    last_crop = crops[max(crops)] if crops else None
    for y in ANALYSIS_YEARS:   # years after the crop map (2026): assume last year's crop, flagged in the output
        crops.setdefault(y, last_crop)
    df = build_weekly_features(w, crops)
    df = df[df.in_season.astype(bool) & df.year.isin(ANALYSIS_YEARS)].copy()
    df["crop"] = df.year.map(crops)
    df["no_crop"] = df.crop.isin(["Fallow/Idle Cropland"]) | df.crop.isna()
    df["water"] = df.water.fillna(False).astype(bool)
    df["evaluated"] = ~df.no_crop & ~df.water
    df = df.join(method_a_zscore(df))
    df["flag_zscore_field"] = field_only_zscore(df) & ~df.water
    fit = df.evaluated
    df = df.join(method_b_isolation_forest(df, fit, seed))
    loyo = method_b_isolation_forest(df, fit, seed, leave_one_year_out=True).flag_iforest
    df.loc[df.water, ["flag_zscore", "flag_iforest"]] = False
    n = df.flag_zscore.astype(int) + df.flag_iforest.astype(int)
    df["status"] = np.select([df.water, df.no_crop, n == 2, n == 1], ["water", "fallow", "both", "one"], "none")
    rs = [reasons(r, r["crop"]) if r["status"] in ("one", "both") else ([], []) for _, r in df.iterrows()]
    df["drivers"], df["reasons"] = [a for a, _ in rs], [b for _, b in rs]
    g = df[df.evaluated]
    ev = evaluate(g, loyo)
    chk = checks_9(df, crops)
    latest_year = int(g.year.max()) if len(g) else None
    summary = {
        "field_id": fid, "generated_at": now(),
        "evidence": evidence_line(g),
        "latest_season": {"year": latest_year, "evidence": evidence_line(g[g.year == latest_year]) if latest_year else None,
                          "weeks_flagged_both": int((g[g.year == latest_year].status == "both").sum()) if latest_year else 0,
                          "weeks_flagged_one": int((g[g.year == latest_year].status == "one").sum()) if latest_year else 0,
                          "crop": crops.get(latest_year), "crop_assumed": latest_year not in crop_history(fid)},
        "evaluation": ev, "checks": chk,
        "no_crop_years_excluded_from_evidence": sorted(df[df.no_crop].year.unique().tolist()),
        "events_source": f"US Drought Monitor county statistics: weeks with >= {USDM_D3_EVENT_PCT:.0f}% of the county in "
                         "D3 (extreme) or D4 (exceptional) drought, cumulative statistic, max over the field's counties",
        "inputs": {k: df[k].value_counts().to_dict() for k in ("lst_source", "esi_source", "sm_source") if k in df},
        "input_coverage_scored_weeks": {f: int(g[f].notna().sum()) for f in Z_FEATURES},
        "how_to_read": "A week is flagged when the field looks unusual for that week of the year in a stress direction. "
                       "Both checks = stronger evidence. No labelled stress events exist, so there is no accuracy; the "
                       "Drought Monitor weeks show whether flags line up with known drought.",
        "credit": CREDIT}
    weeks = []
    for _, r in df.sort_values("week_start").iterrows():
        weeks.append({
            "iso_year": int(r.iso_year), "iso_week": int(r.iso_week), "week_start": r.week_start.strftime("%Y-%m-%d"),
            "crop": r.crop, "crop_assumed": int(r.year) not in crop_history(fid), "no_crop": bool(r.no_crop),
            "ndvi": _r(r.ndvi_hls, 3), "ndvi_sensor": r.ndvi_hls_sensor if isinstance(r.ndvi_hls_sensor, str) else None,
            "ndvi_modis": _r(r.ndvi_modis, 3), "ndvi_reference": r.ndvi_reference if isinstance(r.ndvi_reference, str) else None,
            **{f: _r(r[f]) for f in Z_FEATURES},
            "tmax_c": _r(r.t2m_max_c, 1), "eto_mm_week": _r(r.eto_mm, 1), "lst_minus_tmax_c": _r(r.lst_minus_tmax_c, 1),
            "lst_source": r.lst_source if isinstance(r.lst_source, str) else None, "esi": _r(r.esi, 3),
            "esi_source": r.esi_source if isinstance(r.esi_source, str) else None, "smap_pct": _r(r.smap_pct, 1),
            "sm_source": r.sm_source if isinstance(r.sm_source, str) else None, "imerg_30d_mm": _r(r.imerg_30d_mm, 1),
            "opera_water_frac": _r(r.opera_water_frac, 3), "usdm_d3plus_pct": _r(r.usdm_d3plus_pct, 1),
            "usdm_d3_event": bool(r.usdm_d3plus_pct >= USDM_D3_EVENT_PCT) if pd.notna(r.usdm_d3plus_pct) else None,
            "composite_z": _r(r.composite_z), "if_score": _r(r.if_score, 3),
            "water": bool(r.water), "evaluated": bool(r.evaluated),
            "flag_zscore": bool(r.flag_zscore), "flag_iforest": bool(r.flag_iforest),
            "status": r.status, "drivers": list(r.drivers), "reasons": list(r.reasons)})
    lo, hi = SEASON_WEEKS[family(fid)]
    write_json(out(fid) / "stress_weekly.json", {
        "preset_id": fid, "generated_at": now(), "season_iso_weeks": [lo, hi],
        "crop_years": {int(y): c for y, c in crops.items() if y in ANALYSIS_YEARS and c != "Fallow/Idle Cropland"},
        "method": {"zscore": "composite = mean(-z_ndvi, z_lst, -z_esi, -z_sm) > 1.0, or two of z_ndvi < -1, z_lst > +1, "
                             "z_sm < -1 (ds method A)",
                   "isolation_forest": f"IsolationForest(n_estimators={IF_N_ESTIMATORS}, contamination={IF_CONTAMINATION}, "
                                       "random_state=0) on the six z-scores (missing = 0), fitted on crop-year in-season "
                                       "weeks (ds method B)",
                   "z_scores": "leave-one-year-out; NDVI, LST and ESI vs years with the same crop on this field (>= 5, "
                               "else all crop years); ETo and 30-day rain vs all other years; soil moisture from the "
                               "product percentile (probit)",
                   "status": "both / one / none; 'water' = water seen that week (never stress); 'fallow' = no crop "
                             "(scored, never shown as stress)",
                   "drivers": "keys of the z-scores beyond 1 in the stress direction; `reasons` says the same in words"},
        "inputs": read_json(ai_cache(fid) / "inputs.meta.json")["sources"],
        "sources": [{"id": "modis_mod13q1", "url": "https://planetarycomputer.microsoft.com/dataset/modis-13Q1-061", "verified": True},
                    {"id": "modis_mod11a2", "url": "https://planetarycomputer.microsoft.com/dataset/modis-11A2-061", "verified": True},
                    {"id": "smap_l4", "url": "https://nsidc.org/data/spl4smgp", "verified": True},
                    {"id": "grace_da", "url": "https://disc.gsfc.nasa.gov/datasets/GRACEDADM_CLSM025GL_7D_3.0/summary", "verified": True},
                    {"id": "gpm_imerg", "url": "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary", "verified": True},
                    {"id": "ecostress", "url": "https://lpdaac.usgs.gov/products/eco_l3t_jetv002/", "verified": True},
                    {"id": "opera_dswx_hls", "url": "https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-HLS_V1", "verified": True},
                    {"id": "noaa_ncei_ghcnd", "url": "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily", "verified": True},
                    {"id": "power", "url": "https://power.larc.nasa.gov/", "verified": True},
                    {"id": "usdm", "url": "https://droughtmonitor.unl.edu/", "verified": True}],
        "credit": CREDIT, "weeks": weeks})
    write_json(out(fid) / "stress_summary.json", summary)
    common = dict(task="stress_anomaly", labels="none (unsupervised); checked against US Drought Monitor D3+ weeks",
                  split={"type": "unsupervised", "train_years": sorted(g.year.unique().tolist()),
                         "test_years": sorted(g.year.unique().tolist())}, location_id=fid, checks=chk)
    reps = []
    for m, method, feats, note in (
            ("zscore", "zscore", ["z_ndvi", "z_lst", "z_esi", "z_sm"],
             "composite z > 1.0 or two of (z_NDVI < -1, z_LST > +1, z_SM < -1). "),
            ("iforest", "isolation_forest", Z_FEATURES,
             f"IsolationForest(n_estimators={IF_N_ESTIMATORS}, contamination={IF_CONTAMINATION}) fitted on crop-year "
             "weeks; flags unusual weeks in any direction; missing z = 0. ")):
        mt = {"weeks_scored": ev["weeks_scored"], "flag_rate": ev[f"flag_rate_{m}"], "agreement": ev["agreement"],
              "recall_usdm_d3": ev[f"recall_usdm_d3_{m}"], "flag_rate_no_drought": ev[f"flag_rate_no_drought_{m}"],
              "lift_usdm_d3": ev[f"lift_usdm_d3_{m}"], "usdm_d3_weeks": ev["usdm_d3_weeks"],
              "false_positive_proxy_wet_cool": ev[f"false_positive_proxy_{m}"], "wet_cool_weeks": ev["wet_cool_weeks"]}
        if m == "iforest":
            mt["recall_usdm_d3_loyo"] = ev["recall_usdm_d3_iforest_loyo"]
        else:
            mt["recall_usdm_d3_field_only"] = ev["recall_usdm_d3_zscore_field_only"]
            mt["flag_rate_no_drought_field_only"] = ev["flag_rate_no_drought_zscore_field_only"]
        for k in ("julaug_2021", "julaug_2022"):
            if chk[k]["applicable"]:
                mt[f"{k}_flagged_weeks"] = chk[k][f"flagged_{m}"]
        reps.append(model_report(
            id=f"stress_{'z' if m == 'zscore' else 'if'}_{fid}_v2", method=method, features=feats, metrics=mt,
            disagreement_with={"isolation_forest" if m == "zscore" else "zscore": 1 - ev["agreement"]},
            notes=note + "No labelled stress events, so no accuracy: recall_usdm_d3 = share of Drought Monitor D3+ "
                         "crop weeks flagged; flag_rate_no_drought = the same in weeks with no D3; lift = their ratio. "
                         + CREDIT, **common))
    mp = out(fid) / "models.json"
    doc = read_json(mp) if mp.exists() else {"location_id": fid, "items": []}
    doc["items"] = [i for i in doc["items"] if i["task"] != "stress_anomaly"] + reps
    doc["generated_at"] = now()
    write_json(mp, doc)
    print(f"{fid}: {ev['weeks_scored']} weeks; flags z {ev['flag_rate_zscore']:.2f} if {ev['flag_rate_iforest']:.2f}; "
          f"USDM D3+ weeks {ev['usdm_d3_weeks']}: recall z {ev['recall_usdm_d3_zscore']} if {ev['recall_usdm_d3_iforest']} "
          f"vs no-drought {ev['flag_rate_no_drought_zscore']} / {ev['flag_rate_no_drought_iforest']}; "
          f"agreement {ev['agreement']:.2f}\n   {summary['evidence']}", flush=True)
    return summary


if __name__ == "__main__":
    for f in (sys.argv[1:] or field_ids()):
        run(f)
