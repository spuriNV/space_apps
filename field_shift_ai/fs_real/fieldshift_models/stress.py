"""B6.2 Crop-stress anomaly: z-score vs isolation forest (planner-spec.md B6.2; checks B10.1 #8).

Input: one row per field x week (week_start date). NDVI history should go back to 2000 (MODIS)
so the same-week climatology is built from 2000-2025; scoring is done on in-season weeks of
2015-2025. See README.md for the column list.

Output: per-week flags for both methods + the "both / one / none" vulnerability strip,
driving features per flagged week, and ModelReports (B3 schema) per location.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import IsolationForest

from .common import model_report, write_json

ANALYSIS_YEARS = list(range(2015, 2026))
COMPOSITE_THR = 1.0
Z_THR = 1.0
IF_N_ESTIMATORS = 200
IF_CONTAMINATION = 0.10

Z_FEATURES = ["z_ndvi", "z_lst", "z_esi", "z_sm", "z_eto", "z_imerg30"]
# sign so that positive = more stressed (used for "driving features" text)
STRESS_SIGN = {"z_ndvi": -1, "z_lst": +1, "z_esi": -1, "z_sm": -1, "z_eto": +1, "z_imerg30": -1}
FEATURE_TEXT = {"z_ndvi": "low NDVI", "z_lst": "hot canopy (LST - Tmax)", "z_esi": "low ESI",
                "z_sm": "dry soil (SMAP)", "z_eto": "high ETo", "z_imerg30": "low 30-day rain"}

REQUIRED_COLS = ["location_id", "week_start"]
OPTIONAL_COLS = ["in_season", "ndvi_modis", "ndvi_hls", "lst_k", "t2m_max_c", "lst_minus_tmax_c",
                 "esi", "smap_pct", "eto_mm", "imerg_30d_mm"]

# Known stress episodes for event recall. The docs name the events; the exact date windows are
# assumptions (U) - edit to match what the team agrees.
DEFAULT_EVENTS = {
    "fv_sumas_dairy": [
        {"name": "BC heat dome, late June 2021", "start": "2021-06-21", "end": "2021-07-04"},
        {"name": "Jul-Aug 2023 drought", "start": "2023-07-01", "end": "2023-08-31"},
    ],
    "sr_salmon_river_hay": [
        {"name": "BC heat dome, late June 2021", "start": "2021-06-21", "end": "2021-07-04"},
        {"name": "Jul-Aug 2023 drought", "start": "2023-07-01", "end": "2023-08-31"},
    ],
    "ca_colusa_rice": [
        {"name": "CA 2021-22 drought", "start": "2021-01-01", "end": "2022-12-31"},
    ],
}


# =============================================================================================
# Feature construction
# =============================================================================================
def _iso_week(d: pd.Series) -> pd.Series:
    return d.dt.isocalendar().week.astype(int).clip(upper=52)  # fold week 53 into 52


def _z_same_week(df: pd.DataFrame, col: str) -> pd.Series:
    """(x - mean_same_week) / std_same_week, per location, climatology over all years present."""
    g = df.groupby(["location_id", "iso_week"])[col]
    mu, sd = g.transform("mean"), g.transform("std")
    return (df[col] - mu) / sd.replace(0, np.nan)


def _z_record(df: pd.DataFrame, col: str) -> pd.Series:
    """Standardised against the field's own record (all weeks with a value)."""
    g = df.groupby("location_id")[col]
    return (df[col] - g.transform("mean")) / g.transform("std").replace(0, np.nan)


def build_weekly_features(weekly: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in weekly.columns]
    if missing:
        raise ValueError(f"weekly table missing columns: {missing}")
    df = weekly.copy()
    for c in OPTIONAL_COLS:
        if c not in df.columns:
            df[c] = np.nan
    df["week_start"] = pd.to_datetime(df["week_start"])
    df = df.sort_values(["location_id", "week_start"]).reset_index(drop=True)
    df["iso_week"] = _iso_week(df["week_start"])
    df["year"] = df["week_start"].dt.year

    # z_NDVI: MODIS 2000-2025 same-week climatology; HLS (own same-week climatology) averaged in
    # where available (assumption: the spec says "and HLS where available" without a rule).
    z_modis = _z_same_week(df, "ndvi_modis")
    z_hls = _z_same_week(df, "ndvi_hls")
    df["z_ndvi"] = pd.concat([z_modis, z_hls], axis=1).mean(axis=1, skipna=True)

    # z_LST: ECOSTRESS LST minus POWER T2M_MAX same day, standardised vs the field's own record
    diff = df["lst_minus_tmax_c"]
    diff = diff.where(diff.notna(), (df["lst_k"] - 273.15) - df["t2m_max_c"])
    df["lst_minus_tmax_c"] = diff
    df["z_lst"] = _z_record(df, "lst_minus_tmax_c")

    df["z_esi"] = _z_record(df, "esi")  # ESI weekly mean, standardised (composite uses -ESI_z)
    p = (df["smap_pct"] / 100.0).clip(0.001, 0.999)
    df["z_sm"] = pd.Series(norm.ppf(p), index=df.index).where(df["smap_pct"].notna())
    df["z_eto"] = _z_same_week(df, "eto_mm")
    df["z_imerg30"] = _z_same_week(df, "imerg_30d_mm")
    return df


# =============================================================================================
# Methods
# =============================================================================================
def method_a_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """composite = mean(-z_NDVI, +z_LST, -ESI_z, -z_SM); flag if composite > 1.0
    or any two of (z_NDVI < -1, z_LST > +1, z_SM < -1)."""
    comp = pd.concat([-df["z_ndvi"], df["z_lst"], -df["z_esi"], -df["z_sm"]], axis=1).mean(axis=1, skipna=True)
    two = ((df["z_ndvi"] < -Z_THR).astype(int) + (df["z_lst"] > Z_THR).astype(int)
           + (df["z_sm"] < -Z_THR).astype(int)) >= 2
    out = pd.DataFrame(index=df.index)
    out["composite_z"] = comp
    out["flag_zscore"] = (comp > COMPOSITE_THR) | two
    return out


def method_b_isolation_forest(df: pd.DataFrame, seed: int = 0, leave_one_year_out: bool = False) -> pd.DataFrame:
    """IsolationForest(n_estimators=200, contamination=0.10) on the weekly z vector, fit per field
    on all years. Missing z values are filled with 0 (= normal for that week; assumption).
    leave_one_year_out=True [S]: each year is scored by a model fit on the other years."""
    out = pd.DataFrame(index=df.index, columns=["if_score", "flag_iforest"], dtype=float)
    for _, g in df.groupby("location_id", sort=False):
        X = g[Z_FEATURES].fillna(0.0)
        if leave_one_year_out:
            for yr in g["year"].unique():
                tr, te = X[g["year"] != yr], X[g["year"] == yr]
                if len(tr) < 20:
                    continue
                m = IsolationForest(n_estimators=IF_N_ESTIMATORS, contamination=IF_CONTAMINATION,
                                    random_state=seed).fit(tr)
                out.loc[te.index, "if_score"] = m.decision_function(te)
                out.loc[te.index, "flag_iforest"] = (m.predict(te) == -1).astype(float)
        else:
            m = IsolationForest(n_estimators=IF_N_ESTIMATORS, contamination=IF_CONTAMINATION,
                                random_state=seed).fit(X)
            out.loc[g.index, "if_score"] = m.decision_function(X)
            out.loc[g.index, "flag_iforest"] = (m.predict(X) == -1).astype(float)
    out["flag_iforest"] = out["flag_iforest"].fillna(0).astype(bool)
    return out


def _driving_features(row) -> str:
    hits = [(STRESS_SIGN[f] * row[f], f) for f in Z_FEATURES
            if pd.notna(row[f]) and STRESS_SIGN[f] * row[f] > Z_THR]
    if not hits:  # anomaly not in the stress direction (e.g. IF on a wet/cold week)
        hits = sorted([(abs(row[f]), f) for f in Z_FEATURES if pd.notna(row[f])], reverse=True)[:2]
        return "; ".join(f"{f}={row[f]:+.1f}" for _, f in hits)
    return "; ".join(f"{FEATURE_TEXT[f]} ({row[f]:+.1f})" for _, f in sorted(hits, reverse=True))


# =============================================================================================
# Evaluation (no ground truth)
# =============================================================================================
def _in_window(d: pd.Series, start, end):
    return (d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))


def evaluate_location(g: pd.DataFrame, events: list[dict]) -> dict:
    res = {"weeks_scored": int(len(g))}
    for meth in ["zscore", "iforest"]:
        res[f"flag_rate_{meth}"] = float(g[f"flag_{meth}"].mean()) if len(g) else np.nan
    res["agreement"] = float((g["flag_zscore"] == g["flag_iforest"]).mean()) if len(g) else np.nan

    ev_out = []
    for e in events:
        w = g[_in_window(g["week_start"], e["start"], e["end"])]
        ev_out.append({
            "name": e["name"], "start": e["start"], "end": e["end"], "weeks_in_window": int(len(w)),
            "flagged_zscore": int(w["flag_zscore"].sum()), "flagged_iforest": int(w["flag_iforest"].sum()),
            "flagged_both": int((w["flag_zscore"] & w["flag_iforest"]).sum()),
            "recall_zscore": float(w["flag_zscore"].mean()) if len(w) else None,
            "recall_iforest": float(w["flag_iforest"].mean()) if len(w) else None,
        })
    res["events"] = ev_out

    # False-positive proxy: flags in wet, cool weeks. Definition is an assumption:
    # wet = SMAP z > 0 or 30-day rain z > 0; cool = ETo z < 0 (ETo as temperature/demand proxy).
    wet = (g["z_sm"] > 0) | (g["z_imerg30"] > 0)
    cool = g["z_eto"] < 0
    wc = g[wet & cool]
    res["wet_cool_weeks"] = int(len(wc))
    for meth in ["zscore", "iforest"]:
        res[f"false_positive_proxy_{meth}"] = float(wc[f"flag_{meth}"].mean()) if len(wc) else None
    return res


def validation_check_8(g: pd.DataFrame, location_id: str) -> dict:
    """B10.1 #8: both methods flag >= 1 week in late June 2021 (BC) and >= 2 weeks in
    Jul-Aug 2023 (SR). CA: 2022 should look anomalous (fallow is not stress; label it)."""
    out = {}
    if location_id in ("fv_sumas_dairy", "sr_salmon_river_hay"):
        w = g[_in_window(g["week_start"], "2021-06-21", "2021-07-04")]
        out["late_june_2021_ge1_week_zscore"] = bool(w["flag_zscore"].sum() >= 1)
        out["late_june_2021_ge1_week_iforest"] = bool(w["flag_iforest"].sum() >= 1)
    if location_id == "sr_salmon_river_hay":
        w = g[_in_window(g["week_start"], "2023-07-01", "2023-08-31")]
        out["jul_aug_2023_ge2_weeks_zscore"] = bool(w["flag_zscore"].sum() >= 2)
        out["jul_aug_2023_ge2_weeks_iforest"] = bool(w["flag_iforest"].sum() >= 2)
    if location_id == "ca_colusa_rice":
        w = g[g["year"] == 2022]
        out["2022_flag_rate_zscore"] = float(w["flag_zscore"].mean()) if len(w) else None
        out["2022_flag_rate_iforest"] = float(w["flag_iforest"].mean()) if len(w) else None
        out["note"] = "2022 was a fallow year: anomalous, but fallow is not crop stress"
    return out


def evidence_line(g: pd.DataFrame, no_crop_years=()) -> str:
    """Brief evidence sentence for the *current crop*: years with no crop (fallow) are excluded."""
    g = g[~g["year"].isin(list(no_crop_years))]
    both = g[g["flag_zscore"] & g["flag_iforest"]]
    yrs = f"{g['year'].min()}-{g['year'].max()}" if len(g) else ""
    if both.empty:
        return f"No weeks flagged by both stress models over {yrs}."
    d = both["week_start"]
    part = np.where(d.dt.day <= 15, "early", "late")
    mode = pd.Series([f"{p} {m}" for p, m in zip(part, d.dt.strftime("%B"))]).mode().iloc[0]
    return f"Current crop showed stress in {len(both)} weeks over {yrs}, mostly {mode}."


# =============================================================================================
# Main
# =============================================================================================
@dataclass
class StressResult:
    weekly: pd.DataFrame
    reports: list[dict] = field(default_factory=list)
    summaries: dict = field(default_factory=dict)


def run_stress(weekly: pd.DataFrame, out_dir: str | Path | None = None, events: dict | None = None,
               seed: int = 0, leave_one_year_out: bool = False, no_crop_years: dict | None = None) -> StressResult:
    """no_crop_years: {location_id: [years]} with no crop on the field (e.g. CDL 61 fallow); they are still
    scored (check #8 wants to see them) but left out of the crop-stress evidence line."""
    no_crop_years = no_crop_years or {}
    if "cdl_class" in weekly.columns:
        _w = weekly.assign(_y=pd.to_datetime(weekly["week_start"]).dt.year)
        for loc, g in _w[_w["cdl_class"] == 61].groupby("location_id"):
            no_crop_years.setdefault(loc, sorted(g["_y"].unique().tolist()))
    events = events if events is not None else DEFAULT_EVENTS
    feats = build_weekly_features(weekly)

    # scoring unit: in-season weeks of the existing crop, 2015-2025
    m = feats["year"].isin(ANALYSIS_YEARS)
    if feats["in_season"].notna().any():
        m &= feats["in_season"].fillna(0).astype(bool)
    df = feats[m].copy()
    if df.empty:
        raise ValueError("no in-season weeks in 2015-2025")

    df = df.join(method_a_zscore(df)).join(method_b_isolation_forest(df, seed, leave_one_year_out))
    n = df["flag_zscore"].astype(int) + df["flag_iforest"].astype(int)
    df["strip"] = np.select([n == 2, n == 1], ["both", "one"], "none")
    flagged = df["flag_zscore"] | df["flag_iforest"]
    df["driving_features"] = ""
    df.loc[flagged, "driving_features"] = df[flagged].apply(_driving_features, axis=1)

    reports, summaries = [], {}
    split = {"fit_years": ANALYSIS_YEARS, "scheme": "leave_one_year_out" if leave_one_year_out else "all_years"}
    for loc, g in df.groupby("location_id", sort=False):
        ev = evaluate_location(g, events.get(loc, []))
        chk = validation_check_8(g, loc)
        summaries[loc] = {"evidence": evidence_line(g, no_crop_years.get(loc, ())), "evaluation": ev,
                          "checks": chk, "no_crop_years_excluded_from_evidence": no_crop_years.get(loc, [])}
        common = dict(task="stress_anomaly", labels="none (unsupervised; checked against known episodes)",
                      split=split, location_id=loc, checks=chk)
        reports.append(model_report(
            id="stress_zscore_v1", method="zscore", features=["z_ndvi", "z_lst", "z_esi", "z_sm"],
            metrics={"flag_rate": ev["flag_rate_zscore"],
                     "event_recall": {e["name"]: e["recall_zscore"] for e in ev["events"]},
                     "false_positive_proxy": ev["false_positive_proxy_zscore"],
                     "weeks_scored": ev["weeks_scored"]},
            disagreement_with={"isolation_forest": 1 - ev["agreement"]},
            notes="composite z > 1.0 or two of (z_NDVI<-1, z_LST>+1, z_SM<-1); no labelled stress events",
            **common))
        reports.append(model_report(
            id="stress_iforest_v1", method="isolation_forest", features=Z_FEATURES,
            metrics={"flag_rate": ev["flag_rate_iforest"],
                     "event_recall": {e["name"]: e["recall_iforest"] for e in ev["events"]},
                     "false_positive_proxy": ev["false_positive_proxy_iforest"],
                     "weeks_scored": ev["weeks_scored"]},
            disagreement_with={"zscore": 1 - ev["agreement"]},
            notes=(f"IsolationForest(n_estimators={IF_N_ESTIMATORS}, contamination={IF_CONTAMINATION}) "
                   "per field; flags anomalies in any direction; missing z filled with 0"),
            **common))

    keep = ["location_id", "week_start", "year", "iso_week"] + Z_FEATURES + \
           ["composite_z", "flag_zscore", "if_score", "flag_iforest", "strip", "driving_features"]
    res = StressResult(df[keep].reset_index(drop=True), reports, summaries)
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        res.weekly.to_csv(out / "stress_weekly_flags.csv", index=False)
        write_json(out / "stress_model_reports.json", reports)
        write_json(out / "stress_summary.json", summaries)
    return res
