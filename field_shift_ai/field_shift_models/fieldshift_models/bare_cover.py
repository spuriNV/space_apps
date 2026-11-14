"""B6.1 Bare-cover and transition detection: rule vs ML (planner-spec.md B6.1, rule from B5.1).

Input: one row per field x HLS observation date (field-median values, cloud/shadow already masked
upstream). See README.md for the column list.

Output: per-date predictions (rule / random forest / hist-GBT / consensus, raw + smoothed),
transition dates per method, and ModelReports (B3 schema) per location.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from .common import CLASSES, CLASS_TO_ORD, model_report, write_json

# ---- B5.1 rule thresholds -------------------------------------------------------------------
RULE_BARE_NDVI = 0.20      # bare if NDVI < 0.20 (U rule of thumb, tunable 0.15-0.30)
RULE_COVERED_NDVI = 0.35   # covered if NDVI > 0.35
GREENUP_RUN = 3            # green-up = first of 3 consecutive obs NDVI > 0.35 after a bare period
SENESCENCE_RUN = 2         # senescence = first of 2 consecutive obs with NDVI drop > 0.2 from 30-day max
SENESCENCE_DROP = 0.2
MIN_VALID_FRACTION = 0.5   # drop observation if valid fraction < 0.5

# ---- B6.1 labels ----------------------------------------------------------------------------
SCL_AGREEMENT = 0.80       # train only on scenes with >= 80% agreement across pixels
CDL_FALLOW_CLASS = 61      # CDL 61 Fallow/Idle -> bare all year
WEAK_LABEL_WEIGHT = 0.5    # assumption: CDL window labels are "weak"; down-weighted in training

# ---- targets (B10.1 check 7) ----------------------------------------------------------------
TARGET_ACCURACY = 0.80
TARGET_F1_BARE = 0.75
TARGET_DISAGREEMENT = 0.20

SHORT = {"rule": "rule", "random_forest": "rf", "hist_gbt": "hgb"}

TRANSITION_MATCH_DAYS = 60  # assumption: a predicted transition matches a reference one within 60 d

FEATURES = [
    # spectral
    "ndvi", "evi", "ndwi", "bsi", "nbr2", "red", "nir", "swir1",
    # temporal
    "ndvi_30d_mean", "ndvi_30d_min", "ndvi_30d_max",
    "ndvi_60d_mean", "ndvi_60d_min", "ndvi_60d_max",
    "ndvi_30d_slope", "days_since_last_obs", "ndvi_anom_modis",
    # calendar
    "doy_sin", "doy_cos",
    # context
    "smap_pct", "imerg_7d_mm", "power_tmax_7d_c", "snow_flag",
]

REQUIRED_COLS = ["location_id", "date", "blue", "green", "red", "nir", "swir1", "swir2"]
OPTIONAL_COLS = {
    "valid_fraction": 1.0, "snow_flag": 0, "modis_ndvi_clim": np.nan,
    "smap_pct": np.nan, "imerg_7d_mm": np.nan, "power_tmax_7d_c": np.nan,
    "scl_bare_frac": np.nan, "scl_veg_frac": np.nan, "cdl_class": np.nan,
    "in_season": np.nan, "is_agricultural": True, "crop_type": None,
}


# =============================================================================================
# Features
# =============================================================================================
def _prepare(obs: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in obs.columns]
    if missing:
        raise ValueError(f"observation table missing columns: {missing}")
    df = obs.copy()
    for c, default in OPTIONAL_COLS.items():
        if c not in df.columns:
            df[c] = default
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["valid_fraction"] >= MIN_VALID_FRACTION]
    df = df[df["is_agricultural"].fillna(True).astype(bool)]  # BC: ACI used to exclude non-ag
    return df.sort_values(["location_id", "date"]).reset_index(drop=True)


def add_indices(df: pd.DataFrame) -> pd.DataFrame:
    b, g, r, n, s1, s2 = (df[c] for c in ["blue", "green", "red", "nir", "swir1", "swir2"])
    with np.errstate(divide="ignore", invalid="ignore"):
        df["ndvi"] = (n - r) / (n + r)
        df["evi"] = 2.5 * (n - r) / (n + 6 * r - 7.5 * b + 1)
        df["ndwi"] = (g - n) / (g + n)
        df["bsi"] = ((s1 + r) - (n + b)) / ((s1 + r) + (n + b))
        df["nbr2"] = (s1 - s2) / (s1 + s2)
    for c in ["ndvi", "evi", "ndwi", "bsi", "nbr2"]:
        df[c] = df[c].replace([np.inf, -np.inf], np.nan)
    return df


def _slope_per_day(s: pd.Series) -> float:
    if s.notna().sum() < 2:
        return np.nan
    s = s.dropna()
    x = (s.index - s.index[0]).days.astype(float)
    if np.ptp(x) == 0:
        return np.nan
    return float(np.polyfit(x, s.values, 1)[0])


def add_temporal(df: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for _, g in df.groupby("location_id", sort=False):
        g = g.set_index("date")
        nd = g["ndvi"]
        for w in (30, 60):
            roll = nd.rolling(f"{w}D", min_periods=1)  # trailing window, includes current obs
            g[f"ndvi_{w}d_mean"] = roll.mean()
            g[f"ndvi_{w}d_min"] = roll.min()
            g[f"ndvi_{w}d_max"] = roll.max()
        g["ndvi_30d_slope"] = nd.rolling("30D", min_periods=2).apply(_slope_per_day, raw=False)
        g["days_since_last_obs"] = g.index.to_series().diff().dt.days.astype(float)
        parts.append(g.reset_index())
    out = pd.concat(parts, ignore_index=True)
    out["ndvi_anom_modis"] = out["ndvi"] - out["modis_ndvi_clim"]
    doy = out["date"].dt.dayofyear
    out["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    return out


def build_features(obs: pd.DataFrame) -> pd.DataFrame:
    return add_temporal(add_indices(_prepare(obs)))


# =============================================================================================
# Labels (pseudo-labels; not ground truth)
# =============================================================================================
def make_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Adds `label`, `label_source`, `label_weight`. Priority: S2 SCL > CDL fallow > CDL window."""
    label = pd.Series(pd.NA, index=df.index, dtype="object")
    source = pd.Series(pd.NA, index=df.index, dtype="object")
    weight = pd.Series(np.nan, index=df.index)

    # (ii) CA: CDL crop class + regional planting/harvest windows -> weak labels.
    # Reading of the spec (ambiguous): outside the season -> bare, inside the season -> covered.
    ins = pd.to_numeric(df["in_season"], errors="coerce")
    for val, cls in ((0, "bare"), (1, "covered")):
        m = ins == val
        label[m], source[m], weight[m] = cls, "cdl_window", WEAK_LABEL_WEIGHT

    # (ii) CA: CDL 61 Fallow/Idle year -> bare all year
    m = pd.to_numeric(df["cdl_class"], errors="coerce") == CDL_FALLOW_CLASS
    label[m], source[m], weight[m] = "bare", "cdl_fallow", 1.0

    # (i) Sentinel-2 SCL on clear days: majority SCL 5 -> bare, SCL 4 -> covered, >= 80% agreement
    m = df["scl_bare_frac"] >= SCL_AGREEMENT
    label[m], source[m], weight[m] = "bare", "s2_scl_pseudo", 1.0
    m = df["scl_veg_frac"] >= SCL_AGREEMENT
    label[m], source[m], weight[m] = "covered", "s2_scl_pseudo", 1.0

    df = df.copy()
    df["label"], df["label_source"], df["label_weight"] = label, source, weight
    return df


# =============================================================================================
# Rule detector (B5.1) and transitions
# =============================================================================================
def rule_classify(ndvi: pd.Series, bare_thr: float = RULE_BARE_NDVI) -> pd.Series:
    out = pd.Series("partial", index=ndvi.index, dtype="object")
    out[ndvi < bare_thr] = "bare"
    out[ndvi > RULE_COVERED_NDVI] = "covered"
    out[ndvi.isna()] = pd.NA
    return out


def rule_transitions(dates: pd.Series, ndvi: pd.Series, ndvi_30d_max: pd.Series) -> list[dict]:
    """Green-up: first of 3 consecutive obs NDVI > 0.35 after a bare period.
    Senescence/harvest: first of 2 consecutive obs with NDVI drop > 0.2 from the 30-day max."""
    d, v, mx = list(dates), ndvi.to_numpy(), ndvi_30d_max.to_numpy()
    events, seen_bare = [], False
    in_cover = bool(len(v) and v[0] > RULE_COVERED_NDVI)
    for i in range(len(v)):
        if v[i] < RULE_BARE_NDVI:
            seen_bare = True
        if seen_bare and i + GREENUP_RUN <= len(v) and np.all(v[i:i + GREENUP_RUN] > RULE_COVERED_NDVI):
            events.append({"type": "green_up", "date": d[i]})
            seen_bare, in_cover = False, True
        elif in_cover and i + SENESCENCE_RUN <= len(v) and np.all(
                (mx[i:i + SENESCENCE_RUN] - v[i:i + SENESCENCE_RUN]) > SENESCENCE_DROP):
            events.append({"type": "senescence", "date": d[i]})
            in_cover = False
    return events


def class_transitions(dates: pd.Series, classes: pd.Series) -> list[dict]:
    """Same logic applied to a class sequence (used for ML output and pseudo-labels):
    green-up = first of 3 consecutive `covered` after a `bare`; senescence = first of 2
    consecutive non-`covered` after a covered period (class analogue of the NDVI-drop rule)."""
    d = list(dates)
    c = classes.map(CLASS_TO_ORD).to_numpy(dtype=float)
    events, seen_bare = [], False
    in_cover = bool(len(c) and c[0] == 2)
    for i in range(len(c)):
        if c[i] == 0:
            seen_bare = True
        if seen_bare and i + GREENUP_RUN <= len(c) and np.all(c[i:i + GREENUP_RUN] == 2):
            events.append({"type": "green_up", "date": d[i]})
            seen_bare, in_cover = False, True
        elif in_cover and i + SENESCENCE_RUN <= len(c) and np.all(c[i:i + SENESCENCE_RUN] < 2):
            events.append({"type": "senescence", "date": d[i]})
            in_cover = False
    return events


def smooth_classes(classes: pd.Series) -> pd.Series:
    """3-observation centred median on the ordinal class (bare=0, partial=1, covered=2)."""
    ords = classes.map(CLASS_TO_ORD).astype(float)
    sm = ords.rolling(3, center=True, min_periods=1).median().round()
    return sm.map(lambda x: CLASSES[int(x)] if pd.notna(x) else pd.NA)


def transition_mae(pred: list[dict], ref: list[dict]) -> tuple[float, int, int]:
    """MAE (days) of each reference transition vs nearest predicted of the same type within
    TRANSITION_MATCH_DAYS. Returns (mae, matched, reference_count)."""
    errs = []
    for r in ref:
        cands = [abs((p["date"] - r["date"]).days) for p in pred if p["type"] == r["type"]]
        cands = [x for x in cands if x <= TRANSITION_MATCH_DAYS]
        if cands:
            errs.append(min(cands))
    return (float(np.mean(errs)) if errs else np.nan), len(errs), len(ref)


# =============================================================================================
# Splits
# =============================================================================================
@dataclass
class Split:
    name: str
    train_years: list[int]
    test_years: list[int]
    train_locations: list[str] | None = None  # None = all
    test_locations: list[str] | None = None
    notes: str = ""

    def as_dict(self):
        d = {"train_years": self.train_years, "test_years": self.test_years}
        if self.train_locations:
            d["train_locations"] = self.train_locations
        if self.test_locations:
            d["test_locations"] = self.test_locations
        return d


SPLITS = {
    "year": Split("year", [2019, 2020, 2021, 2022], [2023, 2024, 2025]),
    "ca_fallow": Split("ca_fallow", [2019, 2020, 2021, 2023, 2024], [2022],
                       test_locations=["ca_colusa_rice"], notes="CA: test on the 2022 fallow year"),
    "cross_site": Split("cross_site", list(range(2019, 2026)), list(range(2019, 2026)),
                        train_locations=["fv_sumas_dairy", "ca_colusa_rice"],
                        test_locations=["sr_salmon_river_hay"], notes="[S] train FV+CA, test SR"),
}


def _mask(df, years, locs):
    m = df["date"].dt.year.isin(years)
    if locs:
        m &= df["location_id"].isin(locs)
    return m


# =============================================================================================
# Main
# =============================================================================================
@dataclass
class BareCoverResult:
    predictions: pd.DataFrame
    transitions: pd.DataFrame
    reports: list[dict] = field(default_factory=list)


def _metrics(y_true, y_pred):
    y_true, y_pred = list(y_true), list(y_pred)
    if not y_true:
        return {"accuracy": np.nan, "f1_bare": np.nan, "n_labelled": 0}, None
    return ({
        "accuracy": accuracy_score(y_true, y_pred),
        "f1_bare": f1_score(y_true, y_pred, labels=["bare"], average="macro", zero_division=0),
        "n_labelled": len(y_true),
    }, confusion_matrix(y_true, y_pred, labels=CLASSES).tolist())


def run_bare_cover(obs: pd.DataFrame, split: Split | str = "year", out_dir: str | Path | None = None,
                   seed: int = 0) -> BareCoverResult:
    if isinstance(split, str):
        split = SPLITS[split]
    df = make_labels(build_features(obs))
    df["rule"] = rule_classify(df["ndvi"])

    train = df[_mask(df, split.train_years, split.train_locations) & df["label"].notna()]
    test_m = _mask(df, split.test_years, split.test_locations)
    if train.empty:
        raise ValueError("no labelled training rows for this split")
    if train["label"].nunique() < 2:
        raise ValueError("training labels contain a single class")

    # drop features with no data in the training rows (e.g. SMAP/MODIS not pulled yet)
    feats = [f for f in FEATURES if train[f].notna().any()]
    dropped = [f for f in FEATURES if f not in feats]
    X_tr, y_tr, w_tr = train[feats], train["label"].astype(str), train["label_weight"]
    models = {
        "random_forest": RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                                random_state=seed, n_jobs=-1),
        "hist_gbt": HistGradientBoostingClassifier(random_state=seed),
    }
    for m in models.values():
        m.fit(X_tr, y_tr, sample_weight=w_tr)  # sklearn >= 1.4: RF handles NaN natively

    train_metrics = {}  # in-sample, to show over-fitting against the test score
    for loc, g in train.groupby("location_id", sort=False):
        train_metrics[loc] = {"rule": _metrics(g["label"].astype(str), g["rule"].astype(str))[0]}
        for name, m in models.items():
            train_metrics[loc][name] = _metrics(g["label"].astype(str), m.predict(g[feats]))[0]

    test = df[test_m].copy()
    for name, m in models.items():
        test[name] = m.predict(test[feats])

    # consensus = majority of rule / RF / HGB; if all three differ, fall back to the rule
    def _vote(row):
        votes = [row["rule"], row["random_forest"], row["hist_gbt"]]
        votes = [v for v in votes if isinstance(v, str)]
        for v in votes:
            if votes.count(v) >= 2:
                return v
        return row["rule"]
    test["consensus"] = test.apply(_vote, axis=1)

    methods = ["rule", "random_forest", "hist_gbt", "consensus"]
    trans_rows = []
    for loc, g in test.groupby("location_id", sort=False):
        idx = g.index
        for meth in methods:
            test.loc[idx, f"{meth}_smoothed"] = smooth_classes(g[meth]).values
        ev = {"rule": rule_transitions(g["date"], g["ndvi"], g["ndvi_30d_max"])}
        for meth in ["random_forest", "hist_gbt", "consensus"]:
            ev[meth] = class_transitions(g["date"], test.loc[idx, f"{meth}_smoothed"])
        lab = g[g["label"].notna()]
        ev["pseudo_label"] = class_transitions(lab["date"], lab["label"])
        for meth, evs in ev.items():
            for e in evs:
                trans_rows.append({"location_id": loc, "method": meth, **e})
    transitions = pd.DataFrame(trans_rows, columns=["location_id", "method", "type", "date"])

    # ---- reports, one per method per test location ---------------------------------------
    labels_used = "+".join(sorted(df["label_source"].dropna().unique())) or "none"
    reports = []
    for loc, g in test.groupby("location_id", sort=False):
        lab = g[g["label"].notna()]
        ref = [r for r in transitions[(transitions.location_id == loc) &
                                      (transitions.method == "pseudo_label")].to_dict("records")]
        for meth, method_name, feats in [
            ("rule", "rule_ndvi", ["ndvi"]),
            ("random_forest", "random_forest", feats),
            ("hist_gbt", "hist_gbt", feats),
        ]:
            met, conf = _metrics(lab["label"].astype(str), lab[meth].astype(str))
            pred = [r for r in transitions[(transitions.location_id == loc) &
                                           (transitions.method == meth)].to_dict("records")]
            mae, matched, nref = transition_mae(pred, ref)
            tm = train_metrics.get(loc, {}).get(meth)
            if tm:
                met.update({"train_accuracy": tm["accuracy"], "train_f1_bare": tm["f1_bare"],
                            "train_n_labelled": tm["n_labelled"]})
            met.update({"transition_mae_days": mae, "transitions_matched": matched,
                        "transitions_reference": nref})
            disagree = {}
            for other in ["rule", "random_forest", "hist_gbt"]:
                if other != meth:
                    disagree[{"rule": "rule_ndvi"}.get(other, other)] = float(
                        (g[meth].astype(str) != g[other].astype(str)).mean())

            fi = []
            if meth != "rule" and len(lab) >= 10:
                pi = permutation_importance(models[meth], lab[feats], lab["label"].astype(str),
                                            n_repeats=5, random_state=seed, scoring="accuracy")
                imp = pd.Series(pi.importances_mean, index=feats).sort_values(ascending=False)
                pos = imp.clip(lower=0).sum()
                fi = [{"feature": f, "importance": v, "share": (max(v, 0) / pos if pos else 0.0)}
                      for f, v in imp.items()]

            below = (met["accuracy"] < TARGET_ACCURACY or met["f1_bare"] < TARGET_F1_BARE) \
                if met["n_labelled"] else True
            notes = "pseudo-labels from Sentinel-2 SCL / crop-inventory rules; not ground truth"
            if split.notes:
                notes += f"; {split.notes}"
            reports.append(model_report(
                id=f"bare_{SHORT[meth]}_v1_{split.name}",
                task="bare_cover", method=method_name, features=feats, labels=labels_used,
                split=split.as_dict(), metrics=met, confusion=conf, feature_importance=fi,
                disagreement_with=disagree, notes=notes, location_id=loc,
                features_dropped_no_data=dropped if meth != "rule" else [],
                class_order=CLASSES,
                badge=("below target" if (meth != "rule" and below) else None),
                checks={
                    "accuracy_ge_0.80": bool(met["accuracy"] >= TARGET_ACCURACY) if met["n_labelled"] else None,
                    "f1_bare_ge_0.75": bool(met["f1_bare"] >= TARGET_F1_BARE) if met["n_labelled"] else None,
                    "rule_vs_ml_disagreement_lt_0.20": (bool(disagree.get("rule_ndvi", 0) < TARGET_DISAGREEMENT)
                                                        if meth != "rule" else None),
                },
            ))

    keep = ["location_id", "date", "ndvi", "label", "label_source", "crop_type"] + methods + \
           [f"{m}_smoothed" for m in methods]
    preds = test[keep].copy()
    preds["rule_ml_disagree"] = preds["rule"].astype(str) != preds["random_forest"].astype(str)
    res = BareCoverResult(preds, transitions, reports)

    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        preds.to_csv(out / f"bare_cover_predictions_{split.name}.csv", index=False)
        transitions.to_csv(out / f"bare_cover_transitions_{split.name}.csv", index=False)
        write_json(out / f"bare_cover_model_reports_{split.name}.json", reports)
    return res
