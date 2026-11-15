"""B6.1 bare / covered / water detector: NDVI rule (spec B5.1) vs random forest vs gradient boosting, their
majority vote, smoothing and green-up / harvest / cutting dates.

Merged code. From the `ds` branch library by spuriNV (field_shift_ai/field_shift_models/fieldshift_models/bare_cover.py):
the feature set (NDVI/NDWI/BSI, EVI and NBR2 in the spectral ablation, 30/60-day NDVI statistics, 30-day slope, NDVI
minus the MODIS same-DOY normal, DOY sin/cos, soil moisture, 7-day rain, 7-day Tmax), the labels (Sentinel-2 SCL at
>= 80% pixel agreement per date, overriding CDL fallow years and half-weight CDL season windows), the rule-RF-HGB
majority vote, the 3-observation smoothing, the transition logic and the "below target" badge. From backend/ai on
main: the multi-field training sample (150 m CDL-homogeneous clusters across a 10 km box, sample.py), the spatial
hold-out by 2.5 km block, the CDL crop windows, the water class and the ML calendar for the field.

Classes: bare / covered / water (decision in docs/ai-integration.md: no label source gives "partial"; the rule's
"partial" is shown as "thin cover" on the rule strip only and is scored as covered).

Tests (all on clusters the field is never part of):
  unseen_fields  GroupKFold(4) over 2.5 km blocks, all years: test clusters never seen in any year (HEADLINE)
  unseen_years   train 2016-2022, test 2023-2025 (the ds design, on the multi-field sample)
  fallow_2022    train every other year, test 2022 (drought-fallow year; at Colusa almost every label is bare: easy)
Each test reports, for rule / RF / HGB / vote:
  accuracy, f1_bare              vs the USDA crop-map labels only (CDL fallow years + season windows), covered vs not
                                 covered: these labels do not come from the imagery, so this is the headline metric
  accuracy_merged, f1_*_merged   vs the training labels (mostly Sentinel-2 SCL), 3 classes
  agreement_scl                  vs Sentinel-2 scene classification; "agreement", not accuracy (the model reads the
                                 same reflectance that ESA's classifier used)
  transition_mae_days            green-up / harvest date error vs the midpoint of the crop-map window gap (crude)
  transition_mae_vs_labels_days  the same vs the transitions of the label sequence itself (ds design; circular)
On the field itself (calendar_ml): agreement with the field's own Sentinel-2 classes, and water vs NASA OPERA DSWx
(independent water labels: the model never sees OPERA).

Cuttings: on perennial forage (CDL alfalfa / other hay in that year) a drop in cover followed by regrowth within
CUTTING_MAX_DAYS is a "cutting", not a harvest; the regrowth is not a green-up.

Outputs backend/ai/out/<fid>/: models.json (bare_cover ModelReports; stress.py appends its own), calendar_ml.json
(same shape as backend/field calendar.json), transitions.json, bare_cover_eval.json (details for checks/run_checks.py).
Usage: uv run python -m fieldshift_ai.bare_cover [fid ...] [--calendar-only]
       (fields without a training box use their template's models, no retraining)
"""
from __future__ import annotations

import math
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold

from .common import (CAL_LAST_YEAR, CLASSES3, CROP_WINDOWS, FIELD_DIR, PERENNIAL_FORAGE, TRAINED, YEARS, ai_cache,
                     field_ids, model_report, now, out, read_json, template, today, window_label, write_json)

from fieldshift_field.detector import CLASSES as RULE_CLASSES  # noqa: E402  (backend/field, read-only import)
from fieldshift_field.detector import segments, transitions  # noqa: E402

# ---- B5.1 rule (backend/field thresholds) -----------------------------------------------------------------------
RULE_BARE_NDVI, RULE_COVERED_NDVI, NDWI_WATER, WATER_FRAC = 0.20, 0.35, 0.3, 0.5
GREENUP_RUN, SENESCENCE_RUN, SENESCENCE_DROP = 3, 2, 0.2   # ds transition rule
CUTTING_MAX_DAYS = 45      # perennial forage: cover back within 45 days of a drop = cutting (U; alfalfa cycles 28-35 d)
MAX_GAP = 30               # calendar: daily fill only between observations <= 30 days apart
TRANSITION_MATCH_DAYS = 60  # ds: a predicted transition matches a reference one within 60 days

# ---- labels (ds) --------------------------------------------------------------------------------------------------
SCL_AGREEMENT = 0.80       # Sentinel-2 SCL label when >= 80% of the clear pixels agree
WEAK_LABEL_WEIGHT = 0.5    # CDL season-window labels are weak
CDL_FALLOW = 61

# ---- targets (spec B10.1 check 8) --------------------------------------------------------------------------------
TARGET_ACCURACY, TARGET_F1_BARE, TARGET_DISAGREEMENT = 0.85, 0.80, 0.15

FEATURES = ["ndvi", "ndwi", "bsi",
            "ndvi_30d_mean", "ndvi_30d_min", "ndvi_30d_max", "ndvi_60d_mean", "ndvi_60d_min", "ndvi_60d_max",
            "ndvi_30d_slope", "ndvi_anom_modis",
            "doy_sin", "doy_cos",
            "tmax_7d_c", "imerg_7d_mm", "smap_pct"]
SPECTRAL_EXTRA = ["evi", "nbr2", "red", "nir", "swir1", "swir2"]   # clusters only (the field series stores no bands)
SEASONAL = ["doy_sin", "doy_cos", "tmax_7d_c", "imerg_7d_mm", "smap_pct"]
METHODS = ["rule_ndvi", "random_forest", "hist_gbt", "consensus"]
SHORT = {"rule_ndvi": "rule", "random_forest": "rf", "hist_gbt": "hgb", "consensus": "vote"}
TESTS = {
    "unseen_fields": {"type": "spatial_block", "train_years": YEARS, "test_years": YEARS, "headline": True,
                      "title": "Fields it never saw (2.5 km blocks held out, all years)"},
    "unseen_years": {"type": "year_2023_2025", "train_years": [y for y in YEARS if y <= 2022],
                     "test_years": [2023, 2024, 2025], "title": "Years it never saw (2023-2025)"},
    "fallow_2022": {"type": "year", "train_years": [y for y in YEARS if y != 2022], "test_years": [2022],
                    "title": "2022 drought-fallow year (easy test)"},
}
LABELS_DESC = "s2_scl_pseudo (>=80% agreement) > cdl_fallow > cdl_window (weight 0.5)"
CREDIT = "Labels, features, vote and transition logic: spuriNV (ds branch); multi-field sample and splits: backend/ai."


# =================================================================================================== features
def add_indices(df: pd.DataFrame) -> pd.DataFrame:
    """EVI and NBR2 from field-median reflectance where bands exist (ds add_indices); NDVI/NDWI/BSI are the
    per-pixel medians already in the table."""
    if "red" in df:
        with np.errstate(divide="ignore", invalid="ignore"):
            df["evi"] = 2.5 * (df.nir - df.red) / (df.nir + 6 * df.red - 7.5 * df.blue + 1)
            df["nbr2"] = (df.swir1 - df.swir2) / (df.swir1 + df.swir2)
        for c in ("evi", "nbr2"):
            df[c] = df[c].replace([np.inf, -np.inf], np.nan)
    return df


def _slope_per_day(t: np.ndarray, v: np.ndarray) -> np.ndarray:
    out = np.full(len(t), np.nan)
    for i in range(len(t)):
        m = (t >= t[i] - 30) & (t <= t[i])
        if m.sum() >= 2 and np.ptp(t[m]) > 0:
            out[i] = np.polyfit(t[m], v[m], 1)[0]
    return out


def add_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """ds add_temporal: trailing 30/60-day NDVI mean/min/max (incl. the current date), 30-day slope per day,
    days since the last observation, NDVI minus the MODIS same-DOY normal, DOY sin/cos."""
    parts = []
    for _, g in df.groupby("location_id", sort=False):
        g = g.sort_values("date").copy()
        s = g.set_index("date")["ndvi"]
        for w in (30, 60):
            r = s.rolling(f"{w}D", min_periods=1)
            g[f"ndvi_{w}d_mean"], g[f"ndvi_{w}d_min"], g[f"ndvi_{w}d_max"] = r.mean().values, r.min().values, r.max().values
        t = (g["date"] - g["date"].iloc[0]).dt.days.to_numpy(float)
        g["ndvi_30d_slope"] = _slope_per_day(t, g["ndvi"].to_numpy(float))
        g["days_since_last_obs"] = np.r_[np.nan, np.diff(t)]
        parts.append(g)
    d = pd.concat(parts, ignore_index=True)
    d["ndvi_anom_modis"] = d["ndvi"] - d["modis_ndvi_clim"]
    doy = d["date"].dt.day_of_year
    d["doy"], d["year"] = doy, d["date"].dt.year
    d["doy_sin"], d["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    return d


def rule_classify(d: pd.DataFrame) -> pd.Series:
    """backend/field B5.1: water if NDWI > 0.3 or SCL water > 50%, else NDVI < 0.20 bare, > 0.35 covered, else partial."""
    wf = d.get("scl_water_frac", d.get("water_frac", pd.Series(0.0, index=d.index))).fillna(0)
    water = (d.ndwi > NDWI_WATER) | (wf > WATER_FRAC)
    return pd.Series(np.where(water, "water", np.where(d.ndvi < RULE_BARE_NDVI, "bare",
                                                       np.where(d.ndvi <= RULE_COVERED_NDVI, "partial", "covered"))),
                     index=d.index)


def make_labels(d: pd.DataFrame) -> pd.DataFrame:
    """ds make_labels with a water class. Priority: Sentinel-2 SCL (>= 80% of clear pixels water / vegetation /
    not-vegetated) > CDL fallow year (bare) > CDL season window (weak, weight 0.5)."""
    cdl = [window_label(c, doy) if pd.notna(c) else None for c, doy in zip(d.cdl_class, d.doy)]
    d["label_cdl"] = pd.Series(cdl, index=d.index, dtype=object)
    scl = np.where(d.scl_water_frac >= SCL_AGREEMENT, "water", np.where(
        d.scl_veg_frac >= SCL_AGREEMENT, "covered", np.where(d.scl_bare_frac >= SCL_AGREEMENT, "bare", None)))
    d["label_scl"] = pd.Series(scl, index=d.index, dtype=object)
    fallow = d.cdl_class == CDL_FALLOW
    d["label"] = d.label_scl.where(d.label_scl.notna(), d.label_cdl)
    d["label_source"] = np.where(d.label_scl.notna(), "s2_scl_pseudo", np.where(
        d.label_cdl.notna() & fallow, "cdl_fallow", np.where(d.label_cdl.notna(), "cdl_window", None)))
    d["label_weight"] = np.where(d.label_source == "cdl_window", WEAK_LABEL_WEIGHT, 1.0)
    return d


def prepare(obs: pd.DataFrame) -> pd.DataFrame:
    d = add_temporal(add_indices(obs.copy()))
    d["rule4"] = rule_classify(d)
    d["rule_ndvi"] = d.rule4.replace({"partial": "covered"})  # scored: thin cover counts as covered
    return make_labels(d)


# =================================================================================================== transitions
def smooth3(seq):
    """3-observation centred mode (a b a -> a a a); works with the water class (ds used a median on ordinals)."""
    s = list(seq)
    o = s.copy()
    for i in range(1, len(s) - 1):
        if s[i - 1] == s[i + 1] and s[i - 1] != s[i]:
            o[i] = s[i - 1]
    return o


def _apply_cuttings(events, perennial):
    """senescence followed by green-up within CUTTING_MAX_DAYS on perennial forage -> one 'cutting'."""
    out, i = [], 0
    while i < len(events):
        e = events[i]
        nxt = events[i + 1] if i + 1 < len(events) else None
        if e["type"] == "senescence_harvest" and perennial(e["date"]) and nxt is not None and nxt["type"] == "green_up" \
                and (nxt["date"] - e["date"]).days <= CUTTING_MAX_DAYS:
            out.append({"type": "cutting", "date": e["date"], "regrowth": nxt["date"]})
            i += 2
            continue
        out.append(e)
        i += 1
    return out


def class_transitions(dates, classes, perennial=lambda _d: False):
    """ds class_transitions: green-up = first of 3 consecutive `covered` after a bare/water period; senescence/harvest
    = first of 2 consecutive non-covered after a covered period. Then the cutting rule."""
    d = list(dates)
    cov = np.array([c == "covered" for c in classes])
    low = np.array([c in ("bare", "water") for c in classes])
    ev, seen_bare, in_cover = [], False, bool(len(cov) and cov[0])
    for i in range(len(cov)):
        if low[i]:
            seen_bare = True
        if seen_bare and i + GREENUP_RUN <= len(cov) and cov[i:i + GREENUP_RUN].all():
            ev.append({"type": "green_up", "date": d[i]})
            seen_bare, in_cover = False, True
        elif in_cover and i + SENESCENCE_RUN <= len(cov) and (~cov[i:i + SENESCENCE_RUN]).all():
            ev.append({"type": "senescence_harvest", "date": d[i]})
            in_cover = False
    return _apply_cuttings(ev, perennial)


def rule_transitions(dates, ndvi, ndvi_max30, perennial=lambda _d: False):
    """ds rule_transitions: green-up = first of 3 consecutive NDVI > 0.35 after NDVI < 0.20; senescence/harvest =
    first of 2 consecutive dates with NDVI more than 0.2 below its 30-day max. Then the cutting rule."""
    d, v, mx = list(dates), np.asarray(ndvi, float), np.asarray(ndvi_max30, float)
    ev, seen_bare, in_cover = [], False, bool(len(v) and v[0] > RULE_COVERED_NDVI)
    for i in range(len(v)):
        if v[i] < RULE_BARE_NDVI:
            seen_bare = True
        if seen_bare and i + GREENUP_RUN <= len(v) and np.all(v[i:i + GREENUP_RUN] > RULE_COVERED_NDVI):
            ev.append({"type": "green_up", "date": d[i]})
            seen_bare, in_cover = False, True
        elif in_cover and i + SENESCENCE_RUN <= len(v) and np.all(
                (mx[i:i + SENESCENCE_RUN] - v[i:i + SENESCENCE_RUN]) > SENESCENCE_DROP):
            ev.append({"type": "senescence_harvest", "date": d[i]})
            in_cover = False
    return _apply_cuttings(ev, perennial)


def transition_mae(pred, ref):
    """ds transition_mae: each reference event vs the nearest predicted event of the same type within 60 days."""
    errs = []
    for r in ref:
        c = [abs((p["date"] - r["date"]).days) for p in pred if p["type"] == r["type"]]
        c = [x for x in c if x <= TRANSITION_MATCH_DAYS]
        if c:
            errs.append(min(c))
    return errs, len(ref)


def _perennial_fn(g):
    by_year = dict(zip(g.year, g.cdl_class))
    return lambda dt_: by_year.get(dt_.year) in PERENNIAL_FORAGE


def cdl_mid_errors(g, col):
    """Pre-merge reference: per cluster-year, the green-up / harvest date vs the midpoint of the CDL window gap."""
    errs = []
    for y, gy in g.groupby("year"):
        w = CROP_WINDOWS.get(int(gy.cdl_class.iloc[0])) if pd.notna(gy.cdl_class.iloc[0]) else None
        if not w or not w["covered"] or len(gy) < 3:
            continue
        cov = np.array([c == "covered" for c in smooth3(gy[col])])
        doy = gy.doy.values
        for a, b in w["covered"]:
            before = [be for (_, be) in w["bare"] if be < a]
            after = [bs for (bs, _) in w["bare"] if bs > b]
            if before:
                ref, lo, hi = (max(before) + a) / 2, max(before) - 30, b
                idx = [i for i in range(1, len(doy)) if lo <= doy[i] <= hi and cov[i] and not cov[i - 1]]
                if idx:
                    errs.append(abs(doy[idx[0]] - ref))
            if after:
                ref, lo, hi = (b + min(after)) / 2, a, min(after) + 30
                idx = [i for i in range(1, len(doy)) if lo <= doy[i] <= hi and not cov[i] and cov[i - 1]]
                if idx:
                    errs.append(abs(doy[idx[0]] - ref))
    return errs


# =================================================================================================== models
def make_model(method):
    if method == "random_forest":
        return RandomForestClassifier(n_estimators=300, class_weight="balanced", n_jobs=-1, random_state=0)
    return HistGradientBoostingClassifier(class_weight="balanced", random_state=0)


def _proba(m, X):
    return pd.DataFrame(m.predict_proba(X), columns=m.classes_, index=X.index).reindex(columns=CLASSES3, fill_value=0.0)


def vote(rule4, rf, hgb, p_mean):
    """ds consensus: majority of rule / RF / HGB; the rule's 'partial' abstains. No majority -> the class with the
    highest mean RF+HGB probability (ds fell back to the rule, which cannot say water vs bare on thin cover)."""
    out = []
    for r, a, b, pm in zip(rule4, rf, hgb, p_mean):
        votes = [v for v in (r, a, b) if v in CLASSES3]
        win = next((v for v in votes if votes.count(v) >= 2), None)
        out.append(win or CLASSES3[int(np.argmax(pm))])
    return out


def fit_predict(d: pd.DataFrame, tr: np.ndarray, te: np.ndarray, feats):
    """Fit RF + HGB on labelled train rows (sample weights = label weights), predict every test row."""
    t = d[tr & d.label.notna().values]
    res = {}
    for m in ("random_forest", "hist_gbt"):
        mod = make_model(m).fit(t[feats], t.label.astype(str), sample_weight=t.label_weight)
        res[m] = mod
    X = d.loc[te, feats]
    P = {m: _proba(res[m], X) for m in res}
    pred = {m: P[m].idxmax(axis=1) for m in res}
    pmean = ((P["random_forest"] + P["hist_gbt"]) / 2).to_numpy()
    pred["consensus"] = pd.Series(vote(d.loc[te, "rule4"], pred["random_forest"], pred["hist_gbt"], pmean), index=X.index)
    pred["rule_ndvi"] = d.loc[te, "rule_ndvi"]
    return pred, res


# =================================================================================================== scoring
def _sc(y, p, labels=CLASSES3, pos="bare"):
    y, p = np.asarray(y, dtype=object), np.asarray(p, dtype=object)
    if not len(y):
        return None, None, None
    return (float(accuracy_score(y, p)), float(f1_score(y, p, labels=[pos], average="macro", zero_division=0)),
            float(f1_score(y, p, labels=labels, average="macro", zero_division=0)))


CDL_ORDER = ["not_covered", "covered"]   # crop-map scoring: bare or water vs covered


def _cdl(t, col):
    c = t[t.label_cdl.notna()]
    return c, np.where(c.label_cdl == "covered", "covered", "not_covered"), np.where(c[col] == "covered", "covered", "not_covered")


def score(t: pd.DataFrame, col: str, years=()) -> dict:
    """t: test rows (labelled or not) with predictions in `col` and smoothed predictions in f'{col}_sm'.

    accuracy / f1_bare (HEADLINE metrics): vs the USDA crop-map labels only (CDL fallow years and season windows),
        scored as covered vs not covered (bare or water; the crop map cannot tell flooded from dry ground). These
        labels do not come from the imagery the models read.
    *_merged: vs the training labels (mostly Sentinel-2 SCL), 3 classes.
    agreement_scl: vs Sentinel-2 scene classification (>= 80% of clear pixels); agreement, not accuracy."""
    c, y2, p2 = _cdl(t, col)
    a2, f2, _ = _sc(y2, p2, labels=CDL_ORDER, pos="not_covered")
    m = {"accuracy": a2, "f1_bare": f2, "n_test": int(len(c))}
    lab = t[t.label.notna()]
    acc, f1b, f1m = _sc(lab.label, lab[col])
    m.update({"accuracy_merged": acc, "f1_bare_merged": f1b, "f1_macro_merged": f1m, "n_merged": int(len(lab))})
    s = t[t.label_scl.notna()]
    m.update({"agreement_scl": float((s.label_scl == s[col]).mean()) if len(s) else None, "n_scl": int(len(s))})
    for y in years:
        cy = c.year.values == y
        a, f, _ = _sc(y2[cy], p2[cy], labels=CDL_ORDER, pos="not_covered")
        ly = lab[lab.year == y]
        am, _, _ = _sc(ly.label, ly[col])
        m.update({f"accuracy_{y}": a, f"f1_bare_{y}": f, f"n_{y}": int(cy.sum()), f"accuracy_merged_{y}": am})
    # transitions per cluster over the test rows (smoothed): vs the midpoint of the crop-map window gap (independent,
    # crude) and vs the transitions of the label sequence itself (ds design; mostly Sentinel-2 classes)
    errs, nref, errs_mid = [], 0, []
    for _, g in t.groupby("location_id", sort=False):
        per = _perennial_fn(g)
        if col == "rule_ndvi":
            pred = rule_transitions(g.date, g.ndvi, g.ndvi_30d_max, per)
        else:
            pred = class_transitions(g.date, g[f"{col}_sm"], per)
        lg = g[g.label.notna()]
        ref = class_transitions(lg.date, lg.label.tolist(), per)
        e, n = transition_mae(pred, ref)
        errs += e
        nref += n
        errs_mid += cdl_mid_errors(g, f"{col}_sm" if col != "rule_ndvi" else col)
    m.update({"transition_mae_days": float(np.mean(errs_mid)) if errs_mid else None, "transitions_n": len(errs_mid),
              "transition_mae_vs_labels_days": float(np.mean(errs)) if errs else None,
              "transitions_vs_labels_matched": len(errs), "transitions_vs_labels_reference": nref})
    return m


def add_smoothed(t: pd.DataFrame, cols) -> pd.DataFrame:
    t = t.sort_values(["location_id", "date"])
    for c in cols:
        t[f"{c}_sm"] = t.groupby("location_id", sort=False)[c].transform(lambda s: pd.Series(smooth3(s), index=s.index))
    return t


def run_test(d: pd.DataFrame, name: str, feats) -> tuple[pd.DataFrame, dict, dict]:
    spec = TESTS[name]
    leak = []
    preds = {m: pd.Series(index=d.index, dtype=object) for m in METHODS}
    models = None
    if name == "unseen_fields":
        te_all = np.zeros(len(d), bool)
        for k, (i_tr, i_te) in enumerate(GroupKFold(n_splits=4).split(d, groups=d.block)):
            tr = np.zeros(len(d), bool); tr[i_tr] = True
            te = np.zeros(len(d), bool); te[i_te] = True
            p, _ = fit_predict(d, tr, te, feats)
            for m in METHODS:
                preds[m][te] = p[m].values
            te_all |= te
            leak.append({"fold": k, "test_blocks": sorted(d.loc[te, "block"].unique().tolist()),
                         "block_overlap": sorted(set(d.loc[tr, "block"]) & set(d.loc[te, "block"])),
                         "cluster_overlap": len(set(d.loc[tr, "location_id"]) & set(d.loc[te, "location_id"]))})
        te = te_all
    else:
        tr, te = d.year.isin(spec["train_years"]).values, d.year.isin(spec["test_years"]).values
        p, models = fit_predict(d, tr, te, feats)
        for m in METHODS:
            preds[m][te] = p[m].values
        leak.append({"train_years": sorted(d.loc[tr, "year"].unique().tolist()),
                     "test_years": sorted(d.loc[te, "year"].unique().tolist()),
                     "year_overlap": sorted(set(d.loc[tr, "year"]) & set(d.loc[te, "year"]))})
    t = d[te].copy()
    for m in METHODS:
        t[m] = preds[m][te].values
    t = add_smoothed(t, ["random_forest", "hist_gbt", "consensus"])
    t["rule_ndvi_sm"] = t["rule_ndvi"]
    years = spec["test_years"] if name != "unseen_fields" else []
    return t, {"leakage": leak, "models": models}, {m: score(t, m, years) for m in METHODS}


# =================================================================================================== field calendar
def field_table(fid: str) -> pd.DataFrame | None:
    p = ai_cache(fid) / "obs_field.parquet"
    if not p.exists():
        return None
    o = pd.read_parquet(p)
    o = o[o.fam == "s2"].copy()     # the models were trained on Sentinel-2 L2A
    o["date"] = pd.to_datetime(o.date)
    return prepare(o)


def ml_calendar(fid: str, models: dict, feats, tpl: str) -> tuple[dict, dict, dict]:
    d = field_table(fid)
    X = d[feats]
    P = _proba(models["random_forest"], X)
    Ph = _proba(models["hist_gbt"], X)
    Ps = P.rolling(3, center=True, min_periods=1).mean()            # 3-observation smoothing (pre-merge calendar)
    d["ml_raw"], d["ml"] = P.idxmax(axis=1), Ps.idxmax(axis=1)
    d["hgb"] = Ph.idxmax(axis=1)
    d["consensus"] = vote(d.rule4, d.ml_raw, d.hgb, ((P + Ph) / 2).to_numpy())
    d["consensus_sm"] = smooth3(d.consensus)
    d["hgb_sm"] = smooth3(d.hgb)
    days = pd.date_range("2015-07-01", f"{CAL_LAST_YEAR}-12-31", freq="D")
    t = d["date"].values.astype("datetime64[D]")
    A = Ps.values
    res = []
    for day in days.values.astype("datetime64[D]"):
        i = np.searchsorted(t, day, side="right") - 1
        if i >= 0 and t[i] == day:
            res.append(CLASSES3[int(A[i].argmax())]); continue
        if i < 0 or i + 1 >= len(t):
            res.append("unknown"); continue
        gap = int((t[i + 1] - t[i]).astype(int))
        if gap > MAX_GAP:
            res.append("unknown"); continue
        a = int((day - t[i]).astype(int))
        res.append(CLASSES3[int((A[i] + (A[i + 1] - A[i]) * a / gap).argmax())])
    full = pd.Series(res, index=days)
    per = _perennial_fn(d)
    ev = {"rule_ndvi": rule_transitions(d.date, d.ndvi, d.ndvi_30d_max, per),
          "random_forest": class_transitions(d.date, d.ml, per),
          "hist_gbt": class_transitions(d.date, d.hgb_sm, per),
          "consensus": class_transitions(d.date, d.consensus_sm, per)}
    lab = d[d.label_scl.notna()]
    ev["s2_scl_reference"] = class_transitions(lab.date, lab.label_scl.tolist(), per)
    # field evaluation: this field was never in training (unseen field)
    fe = {}
    for m, col in (("rule_ndvi", "rule_ndvi"), ("random_forest", "ml"), ("hist_gbt", "hgb_sm"), ("consensus", "consensus_sm")):
        e, n = transition_mae(ev[m], ev["s2_scl_reference"])
        fe[m] = {"agreement_scl": float((lab.label_scl == lab[col]).mean()) if len(lab) else None, "n_scl": int(len(lab)),
                 "transition_mae_vs_scl_days": float(np.mean(e)) if e else None, "transitions_matched": len(e),
                 "transitions_reference": n}
        op = d[d.opera_water_frac.notna()]
        if len(op):
            yo, po = op.opera_water_frac >= 0.5, op[col] == "water"
            fe[m].update({"opera_scenes": int(len(op)), "opera_water_scenes": int(yo.sum()),
                          "opera_water_detected": int((yo & po).sum()), "opera_dry_called_water": int((~yo & po).sum()),
                          "opera_agreement": float((yo == po).mean())})
    rule = read_json(FIELD_DIR / "out" / fid / "calendar.json") if (FIELD_DIR / "out" / fid / "calendar.json").exists() \
        else {"years": [], "sources": []}
    classes = {k: dict(v) for k, v in RULE_CLASSES.items()}
    for k in ("bare", "covered", "water"):
        classes[k]["label"] = f"{k.capitalize()} (ML: random forest)"
    classes["partial"]["label"] = "Thin cover (rule only; the ML has no partial class)"
    years, dis_all = [], []
    for y in range(2016, CAL_LAST_YEAR + 1):
        s = full[str(y)]
        dy = d[d.date.dt.year == y]
        segs = segments(s, list(dy.date))
        cnt = s.value_counts().to_dict()
        dis = float((dy.ml != dy.rule_ndvi).mean()) if len(dy) else None
        if len(dy):
            dis_all.append((dy.ml != dy.rule_ndvi).values)
        rule_days = next((ry["summary"]["days_by_class"] for ry in rule["years"] if ry["year"] == y), None)
        marks = [{"date": e["date"].strftime("%Y-%m-%d"), "type": e["type"],
                  "ndvi": round(float(d.loc[d.date == e["date"], "ndvi"].iloc[0]), 3)}
                 for e in ev["random_forest"] if e["date"].year == y]
        years.append({
            "year": y, "segments": segs, "transitions": transitions(segs), "markers": marks,
            "summary": {"days_by_class": {k: int(cnt.get(k, 0)) for k in RULE_CLASSES},
                        "n_obs": int(len(dy)), "n_obs_s2": int(len(dy)), "n_obs_landsat": 0,
                        "in_training_years": False,
                        "disagreement_with_rule_obs_pct": round(100 * dis, 1) if dis is not None else None,
                        "agreement_rf_hgb_obs_pct": round(100 * float((dy.ml == dy.hgb_sm).mean()), 1) if len(dy) else None,
                        "rule_days_by_class": rule_days},
            "observations": [{
                "date": r.date.strftime("%Y-%m-%d"), "sensor": "s2", "ndvi": round(float(r.ndvi), 3),
                "ndwi": round(float(r.ndwi), 3), "bsi": None if pd.isna(r.bsi) else round(float(r.bsi), 3),
                "clear_frac": round(float(r.valid_fraction), 2), "class": r.ml, "class_unsmoothed": r.ml_raw,
                "p_bare": round(float(Ps.loc[r.Index, "bare"]), 3), "p_covered": round(float(Ps.loc[r.Index, "covered"]), 3),
                "p_water": round(float(Ps.loc[r.Index, "water"]), 3), "rule_class": r.rule4,
                "hgb_class": r.hgb_sm, "consensus_class": r.consensus_sm,
                "all_agree": bool(r.rule_ndvi == r.ml == r.hgb_sm),
                "s2_scl_class": r.label_scl if isinstance(r.label_scl, str) else None,
                "opera_water_frac": None if pd.isna(r.opera_water_frac) else round(float(r.opera_water_frac), 3)}
                for r in dy.itertuples()],
        })
    doc = {
        "preset_id": fid, "generated_at": now(), "detector": "random_forest", "classes": classes,
        "method": {"model": "RandomForestClassifier(n_estimators=300, class_weight='balanced', random_state=0); "
                            "HistGradientBoostingClassifier(class_weight='balanced', random_state=0) for hgb_class",
                   "trained_on": f"labelled Sentinel-2 dates of the 150 m clusters in the 10 km box around {tpl}, "
                                 f"years {YEARS[0]}-{YEARS[-1]}; this field is never in training (clusters >= 150 m away)",
                   "model_from": tpl, "labels": LABELS_DESC, "features": feats,
                   "observations": "Sentinel-2 L2A only (field clear >= 0.5, >= 20 clear px); the models were trained on S2",
                   "smoothing": "random forest: 3-observation centred mean of class probabilities; hgb/consensus: "
                                "3-observation mode",
                   "consensus": "majority of rule / RF / HGB (rule 'partial' abstains); no majority -> highest mean "
                                "RF+HGB probability",
                   "daily_fill": f"linear interpolation of smoothed probabilities between observations <= {MAX_GAP} "
                                 "days apart, argmax; longer gaps unknown",
                   "markers": "ds transition logic on the smoothed RF classes: green_up = first of 3 covered after "
                              "bare/water; senescence_harvest = first of 2 non-covered after cover; cutting = a drop "
                              f"with regrowth within {CUTTING_MAX_DAYS} days on alfalfa/hay years",
                   "out_of_sample_years": [], "out_of_sample_field": True,
                   "forward_years": [y for y in range(2016, CAL_LAST_YEAR + 1) if y not in YEARS],
                   "forward_years_note": "years after the CDL labels end; nothing trained on them",
                   "credit": CREDIT},
        "data_through": d["date"].max().strftime("%Y-%m-%d"),
        "sources": rule.get("sources", []) + [
            {"id": "usda_cdl_croplandcros", "title": "USDA NASS Cropland Data Layer via CroplandCROS (training labels)",
             "url": "https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer", "accessed": today(), "verified": True},
            {"id": "s2_l2a_scl", "title": "Sentinel-2 L2A scene classification (SCL) via Planetary Computer (training labels)",
             "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", "accessed": today(), "verified": True},
            {"id": "opera_dswx_hls", "title": "NASA OPERA DSWx-HLS (independent water check)",
             "url": "https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-HLS_V1", "accessed": today(), "verified": True}],
        "disagreement_with_rule_obs_pct": round(100 * float(np.concatenate(dis_all).mean()), 1) if dis_all else None,
        "field_evaluation": fe,
        "years": years,
    }
    tr_doc = {"field_id": fid, "generated_at": now(), "model_from": tpl,
              "types": {"green_up": "first of 3 covered dates after bare or water",
                        "senescence_harvest": "first of 2 non-covered dates after cover",
                        "cutting": f"alfalfa/hay: cover drops and is back within {CUTTING_MAX_DAYS} days (not a harvest)"},
              "methods": {m: [{"date": e["date"].strftime("%Y-%m-%d"), "type": e["type"],
                               **({"regrowth": e["regrowth"].strftime("%Y-%m-%d")} if "regrowth" in e else {})}
                              for e in evs] for m, evs in ev.items()},
              "reference_note": "s2_scl_reference = the same logic on this field's Sentinel-2 SCL classes (>= 80% of "
                                "clear pixels); agreement, not ground truth",
              "evaluation": {m: {k: v for k, v in fe[m].items() if k.startswith("transition")} for m in fe},
              "credit": CREDIT}
    return doc, tr_doc, fe


# =================================================================================================== run
def _items_for(fid, name, met, cm, dis, fi, feats, spec, extra_note=""):
    items = []
    for m in ("rule_ndvi", "random_forest", "hist_gbt"):
        mt = met[m]
        below = (mt["accuracy"] is None or mt["accuracy"] < TARGET_ACCURACY or mt["f1_bare"] < TARGET_F1_BARE)
        checks = {"accuracy_ge_0.85": None if mt["accuracy"] is None else bool(mt["accuracy"] >= TARGET_ACCURACY),
                  "f1_bare_ge_0.80": None if mt["f1_bare"] is None else bool(mt["f1_bare"] >= TARGET_F1_BARE)}
        if m != "rule_ndvi":
            checks["rule_vs_ml_disagreement_lt_0.15"] = bool(dis[m]["rule_ndvi"] < TARGET_DISAGREEMENT)
        vote_m = met["consensus"]
        note = (f"Test '{name}': {spec['title']}. accuracy / f1_bare and the confusion matrix (rows = crop-map label, "
                "cols = prediction, order [not_covered, covered]) are vs the USDA crop-map labels only, which do not "
                "come from the imagery; *_merged = vs the training labels (mostly Sentinel-2 SCL, 3 classes); "
                "agreement_scl = agreement with Sentinel-2 scene classification, not accuracy. transition_mae_days = "
                "vs the crop-map window midpoints (crude); transition_mae_vs_labels_days = vs the label sequence (ds). ")
        if m == "rule_ndvi":
            note += "Rule = backend/field B5.1 thresholds; its 'partial' (thin cover) is scored as covered. "
        else:
            note += (f"Majority vote of rule/RF/HGB on this test: crop-map accuracy {vote_m['accuracy']:.3f}, "
                     f"F1(bare) {vote_m['f1_bare']:.3f}; agreement with S2 classes {vote_m['agreement_scl']:.3f}. ")
        if name == "fallow_2022":
            note += "Easy test: most 2022 labels are bare (drought fallow); do not quote as the headline. "
        items.append(model_report(
            id=f"bare_{SHORT[m]}_{fid}_{name}_v2", task="bare_cover", method=m,
            features=["ndvi", "ndwi", "scl_water_frac"] if m == "rule_ndvi" else feats, labels=LABELS_DESC,
            split={"type": spec["type"], "train_years": spec["train_years"], "test_years": spec["test_years"],
                   **({"blocks": "GroupKFold(4) over 2.5 km blocks; each cluster in exactly one test fold"}
                      if name == "unseen_fields" else {})},
            metrics=mt, confusion=cm[m], feature_importance=fi.get(m, []), disagreement_with=dis[m],
            notes=note + extra_note + CREDIT, location_id=fid, test=name, test_title=spec["title"],
            headline=bool(spec.get("headline")), class_order=CDL_ORDER,
            badge=("below target" if (m != "rule_ndvi" and below) else None), checks=checks))
    return items


def run(fid: str):
    t0 = time.time()
    o = pd.read_parquet(ai_cache(fid) / "obs_clusters.parquet")
    o["date"] = pd.to_datetime(o.date)
    d = prepare(o).reset_index(drop=True)
    feats = [f for f in FEATURES if d[f].notna().any()]
    dropped = [f for f in FEATURES if f not in feats]
    lab = d[d.label.notna()]
    print(f"{fid}: {len(d)} obs, {len(lab)} labelled, {d.location_id.nunique()} clusters; labels "
          f"{lab.label.value_counts().to_dict()}; sources {lab.label_source.value_counts().to_dict()}; dropped {dropped}",
          flush=True)
    details = {"field_id": fid, "generated_at": now(), "n_obs": int(len(d)), "n_labelled": int(len(lab)),
               "n_clusters": int(d.location_id.nunique()), "n_blocks": int(d.block.nunique()),
               "labels": lab.label.value_counts().to_dict(), "label_sources": lab.label_source.value_counts().to_dict(),
               "labels_by_year": {int(y): g.label.value_counts().to_dict() for y, g in lab.groupby("year")},
               "features": feats, "features_dropped_no_data": dropped, "tests": {}}
    items = []
    for name in TESTS:
        t, info, met = run_test(d, name, feats)
        lab_t = t[t.label.notna()]
        cm3 = {m: confusion_matrix(lab_t.label.astype(str), lab_t[m].astype(str), labels=CLASSES3).tolist() for m in METHODS}
        cm = {}
        for m in METHODS:
            _, y2, p2 = _cdl(t, m)
            cm[m] = confusion_matrix(y2, p2, labels=CDL_ORDER).tolist()
        dis = {m: {o_: float((t[m] != t[o_]).mean()) for o_ in ("rule_ndvi", "random_forest", "hist_gbt") if o_ != m}
               for m in METHODS}
        fi = {}
        if info["models"] is not None and name == "unseen_years":
            samp = lab_t.sample(min(4000, len(lab_t)), random_state=0)
            for m in ("random_forest", "hist_gbt"):
                pi = permutation_importance(info["models"][m], samp[feats], samp.label.astype(str), scoring="f1_macro",
                                            n_repeats=5, random_state=0, n_jobs=-1)
                fi[m] = sorted([{"feature": f, "importance": round(float(v), 4)} for f, v in zip(feats, pi.importances_mean)],
                               key=lambda x: -x["importance"])
        if name == "fallow_2022":
            share = float((lab_t.label == "bare").mean()) if len(lab_t) else None
            for m in METHODS:
                met[m]["bare_label_share"] = share
        items += _items_for(fid, name, met, cm, dis, fi, feats, TESTS[name])
        details["tests"][name] = {"title": TESTS[name]["title"], "leakage": info["leakage"],
                                  **{m: {"metrics": met[m], "confusion_cdl": cm[m], "confusion_merged": cm3[m],
                                         "disagreement_with": dis[m],
                                         "feature_importance": fi.get(m, [])[:8]} for m in METHODS}}
        for m in METHODS:
            mt = met[m]
            print(f"  {name:13s} {m:14s} crop-map acc {mt['accuracy']:.3f} f1b {mt['f1_bare']:.3f} | merged acc "
                  f"{mt['accuracy_merged']:.3f} | S2 agreement {mt['agreement_scl'] or float('nan'):.3f} | "
                  f"MAE cdl-mid {mt['transition_mae_days']} / vs labels {mt['transition_mae_vs_labels_days']}", flush=True)
    # ablations on the headline test (RF only)
    for tag, fs, why in (("full", feats + [f for f in SPECTRAL_EXTRA if f in d], "adds EVI, NBR2 and red/NIR/SWIR "
                          "reflectance (clusters only; the field series stores no bands, so not used for the calendar)"),
                         ("noseason", [f for f in feats if f not in SEASONAL], "drops DOY, Tmax, rain and soil "
                          "moisture (seasonal proxies) to show how much of the score is spectral")):
        t, _, met = run_test(d, "unseen_fields", fs)
        mt = met["random_forest"]
        details["tests"]["unseen_fields"][f"random_forest_{tag}"] = {"metrics": mt}
        items.append(model_report(
            id=f"bare_rf_{tag}_{fid}_unseen_fields_v2", task="bare_cover", method="random_forest", features=fs,
            labels=LABELS_DESC, split={"type": "spatial_block", "train_years": YEARS, "test_years": YEARS},
            metrics=mt, disagreement_with={"rule_ndvi": float((t.random_forest != t.rule_ndvi).mean())},
            notes=f"Ablation on the unseen-fields test: {why}. Not used for the calendar or the checks. " + CREDIT,
            location_id=fid, test="unseen_fields", ablation=tag))
        print(f"  ablation {tag:9s} RF crop-map acc {mt['accuracy']:.3f} f1b {mt['f1_bare']:.3f} S2 agreement "
              f"{mt['agreement_scl']:.3f}", flush=True)
    # deployment models: every labelled cluster date (the field itself is never in the sample)
    tr = np.ones(len(d), bool)
    _, deploy = fit_predict(d, tr, np.zeros(len(d), bool) | tr, feats)
    details["deploy"] = {"train_rows": int(len(lab)), "years": YEARS, "features": feats}
    p = out(fid) / "models.json"
    doc = {"location_id": fid, "generated_at": now(), "source": "backend/ai (fieldshift_ai.bare_cover, fieldshift_ai.stress)",
           "headline_test": "unseen_fields", "credit": CREDIT, "items": items}
    if p.exists():
        doc["items"] += [i for i in read_json(p).get("items", []) if i["task"] == "stress_anomaly"]
    write_json(p, doc)
    write_json(out(fid) / "bare_cover_eval.json", details)
    print(f"  {fid} trained and tested in {time.time() - t0:.0f}s", flush=True)
    return deploy, feats, details


def write_calendar(fid: str, deploy, feats, tpl: str, details=None):
    if field_table(fid) is None:
        print(f"{fid}: no obs_field.parquet (no S2 field series yet); calendar_ml not written")
        return None
    cal, tr, fe = ml_calendar(fid, deploy, feats, tpl)
    write_json(out(fid) / "calendar_ml.json", cal)
    write_json(out(fid) / "transitions.json", tr)
    if details is not None:
        details["calendar_ml"] = {"disagreement_with_rule_obs_pct": cal["disagreement_with_rule_obs_pct"],
                                  "field_evaluation": fe,
                                  "by_year": {y["year"]: {"days": y["summary"]["days_by_class"],
                                                          "rule_days": y["summary"]["rule_days_by_class"],
                                                          "disagree_pct": y["summary"]["disagreement_with_rule_obs_pct"]}
                                              for y in cal["years"]}}
        write_json(out(fid) / "bare_cover_eval.json", details)
    rf = fe["random_forest"]
    print(f"  {fid} calendar_ml through {cal['data_through']}: rule disagreement {cal['disagreement_with_rule_obs_pct']}%, "
          f"RF agreement with field SCL {rf['agreement_scl']}, OPERA {rf.get('opera_water_detected')}/"
          f"{rf.get('opera_water_scenes')} water scenes detected", flush=True)
    return cal


def from_template(fid: str, tpl: str, deploy, feats):
    """Registry fields without their own training box: the template's deployment models, no retraining."""
    cal = write_calendar(fid, deploy, feats, tpl)
    tm = read_json(out(tpl) / "models.json")
    box = read_json(FIELD_DIR / "polygons" / f"{tpl}_training_box.json")
    x0, y0, x1, y1 = box["bbox_epsg4326"]
    c = field_polygon_centroid(fid)
    inside = x0 <= c[0] <= x1 and y0 <= c[1] <= y1
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dist_km = round(math.hypot((c[0] - cx) * 111.32 * math.cos(math.radians(c[1])), (c[1] - cy) * 110.57), 1)
    note = (f" [Models trained around {tpl}; applied to this field without retraining; field "
            f"{'inside' if inside else 'outside'} that training box ({dist_km} km from its centre).]")
    items = [dict(i, notes=(i.get("notes") or "") + note) for i in tm["items"] if i["task"] == "bare_cover"]
    p = out(fid) / "models.json"
    old = read_json(p) if p.exists() else {"items": []}
    write_json(p, {"location_id": fid, "generated_at": now(), "model_from": tpl, "field_in_training_box": inside,
                   "distance_from_training_box_centre_km": dist_km, "headline_test": "unseen_fields", "credit": CREDIT,
                   "items": items + [i for i in old["items"] if i["task"] != "bare_cover"]})
    if cal is not None:
        cal["method"].update({"field_in_training_box": inside, "distance_from_training_box_centre_km": dist_km,
                              "out_of_box_note": None if inside else (
                                  f"This field is {dist_km} km from the centre of the training box around {tpl}. The "
                                  "model was not trained on this area, so its calendar is a transfer test; read it next "
                                  "to the rule calendar.")})
        write_json(out(fid) / "calendar_ml.json", cal)


def field_polygon_centroid(fid):
    from .common import field_polygon  # noqa: PLC0415
    c = field_polygon(fid).centroid
    return c.x, c.y


def deploy_models(tpl: str):
    """Fit the deployment RF + HGB on every labelled cluster date of the template's 10 km box (deterministic, seed 0)."""
    o = pd.read_parquet(ai_cache(tpl) / "obs_clusters.parquet")
    o["date"] = pd.to_datetime(o.date)
    d = prepare(o).reset_index(drop=True)
    feats = [f for f in FEATURES if d[f].notna().any()]
    _, dep = fit_predict(d, np.ones(len(d), bool), np.ones(len(d), bool), feats)
    return dep, feats


def main(fids, calendar_only=False):
    """calendar_only: refit the deployment models (same data, same seed) and rewrite calendar_ml.json and
    transitions.json only; models.json and the test metrics are left as they are."""
    trained = {}
    for fid in fids:
        if fid in TRAINED or template(fid) == fid:
            if calendar_only:
                trained[fid] = deploy_models(fid)
                write_calendar(fid, *trained[fid], fid)
            else:
                dep, feats, det = run(fid)
                trained[fid] = (dep, feats)
                write_calendar(fid, dep, feats, fid, det)
    for fid in fids:
        tpl = template(fid)
        if fid in trained:
            continue
        if tpl not in trained:
            trained[tpl] = deploy_models(tpl)
        from_template(fid, tpl, *trained[tpl])


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")] or field_ids(), "--calendar-only" in sys.argv)
