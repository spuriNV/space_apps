"""Bare / covered / water detector: rule (spec B5.1) vs RandomForest vs HistGradientBoosting (spec B6.1).

Unit: Sentinel-2 observation date x CDL-homogeneous 150 m cluster in the 10 km training box
(data/cache/<preset>/ai/s2_clusters.parquet from sample.py). Usable = all SCL pixels around the cluster clear.

Labels (CDL year class + calendar windows, common.CROP_WINDOWS, all U): bare / covered by window; a bare-window
observation whose water flag is set (NDWI > 0.3 or SCL water > 50%) is labelled water. Observations outside the
windows ("uncertain", planting/harvest +/- ~15 days) are not used. There is no "partial" label, so the ML models
predict 3 classes and the rule's "partial" is scored as "covered" (not bare, not water).

Splits
  year          train 2016-2021 + 2023, test 2022 (the fallow year), 2024, 2025 (spec B6.1 a)
  spatial       GroupKFold(4) over 2.5 km blocks, all years (spec B6.1 d; fields never split across folds)
  year_spatial  both at once: train years in the other blocks, test years in the held-out blocks
Models are fixed before seeing test results (no tuning): RF n_estimators=300, class_weight=balanced;
HGB defaults with class_weight=balanced; random_state=0.

Outputs backend/ai/out/<preset>/models.json (ModelReport items; stress reports are appended by stress.py),
calendar_ml.json (same shape as backend/field/out/<preset>/calendar.json) and bare_cover_eval.json (details used
by checks/run_checks.py).
Usage: uv run python -m fieldshift_ai.bare_cover [preset ...]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold

from .common import (CLASSES3, CROP_WINDOWS, FIELD_DIR, PRESETS, TEST_YEARS, TRAIN_YEARS, YEARS, ai_cache, cache,
                     now, out, read_json, today, window_label, write_json)

from fieldshift_field.detector import CLASSES as RULE_CLASSES  # noqa: E402  (backend/field, read-only import)
from fieldshift_field.detector import segments, transitions  # noqa: E402

BARE, COVER, NDWI_WATER, WATER_FRAC, MAX_GAP = 0.20, 0.35, 0.3, 0.5, 30
CORE = ["ndvi", "ndwi", "bsi", "water_frac", "ndvi_mean30", "ndvi_min30", "ndvi_max30", "ndvi_mean60",
        "ndvi_min60", "ndvi_max60", "ndvi_slope30", "doy_sin", "doy_cos", "tmax7", "prcp7"]
FULL = CORE + ["evi", "nbr2", "red", "nir", "swir1", "swir2", "days_since_last"]
LABELS_DESC = "cdl_year_class + season_rules"


# ---------------------------------------------------------------- features
def weather(preset: str) -> pd.DataFrame:
    w = pd.read_parquet(cache(preset) / "power.parquet")[["date", "T2M_MAX", "PRECTOTCORR"]]
    w["date"] = pd.to_datetime(w["date"])
    w = w.sort_values("date")
    w["tmax7"] = w.T2M_MAX.rolling(7, min_periods=4).mean()
    w["prcp7"] = w.PRECTOTCORR.rolling(7, min_periods=4).sum()
    return w[["date", "tmax7", "prcp7"]]


def _roll(g: pd.DataFrame) -> pd.DataFrame:
    s = g.set_index("date")["ndvi"]
    for d in (30, 60):
        r = s.rolling(f"{d}D")
        g[f"ndvi_mean{d}"] = r.mean().values
        g[f"ndvi_min{d}"] = r.min().values
        g[f"ndvi_max{d}"] = r.max().values
    t = (g["date"] - g["date"].iloc[0]).dt.days.values.astype(float)
    v = g["ndvi"].values
    slope = np.zeros(len(g))
    for i in range(len(g)):
        m = (t >= t[i] - 30) & (t <= t[i])
        if m.sum() >= 2 and np.ptp(t[m]) > 0:
            slope[i] = np.polyfit(t[m], v[m], 1)[0] * 30  # NDVI change per 30 days
    g["ndvi_slope30"] = slope
    g["days_since_last"] = np.r_[np.nan, np.diff(t)]
    return g


def add_features(obs: pd.DataFrame, preset: str, unit: str) -> pd.DataFrame:
    d = obs.rename(columns={"ndvi_med": "ndvi", "ndwi_med": "ndwi", "bsi_med": "bsi"}).copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values([unit, "date"])
    d = d.groupby(unit, group_keys=False)[d.columns.tolist()].apply(_roll)
    d["days_since_last"] = d["days_since_last"].fillna(60).clip(upper=120)
    doy = d["date"].dt.dayofyear
    d["doy"] = doy
    d["year"] = d["date"].dt.year
    d["doy_sin"], d["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    d["water_frac"] = d["water_frac"].fillna(0.0)
    if "red" in d:
        with np.errstate(divide="ignore", invalid="ignore"):
            d["evi"] = 2.5 * (d.nir - d.red) / (d.nir + 6 * d.red - 7.5 * d.blue + 1)
            d["nbr2"] = (d.swir1 - d.swir2) / (d.swir1 + d.swir2)
    d = d.merge(weather(preset), on="date", how="left")
    d["water_flag"] = (d.ndwi > NDWI_WATER) | (d.water_frac > WATER_FRAC)
    d["rule4"] = np.where(d.water_flag, "water", np.where(d.ndvi < BARE, "bare",
                                                         np.where(d.ndvi <= COVER, "partial", "covered")))
    d["rule3"] = d["rule4"].replace({"partial": "covered"})
    return d.reset_index(drop=True)


def training_table(preset: str) -> pd.DataFrame:
    c = ai_cache(preset)
    cl = pd.read_parquet(c / "clusters.parquet")
    s = pd.read_parquet(c / "s2_clusters.parquet")
    s = s[(s.clear_frac >= 0.99) & s.ndvi_med.notna() & (s.n_px40 >= 2)]
    d = add_features(s, preset, "cluster_id")
    d = d.merge(cl[["cluster_id", "block"] + [f"cdl_{y}" for y in YEARS]], on="cluster_id")
    d = d[d.year.isin(YEARS)]
    d["cdl"] = [r[f"cdl_{y}"] for r, y in zip(d[[f"cdl_{y}" for y in YEARS]].to_dict("records"), d.year)]
    lab = [window_label(c_, doy) if c_ >= 0 else None for c_, doy in zip(d.cdl, d.doy)]
    d["label"] = lab
    d.loc[(d.label == "bare") & d.water_flag, "label"] = "water"
    # secondary pseudo-label from SCL (2019+): >= 80% vegetation -> covered, >= 80% not-vegetated -> bare
    d["scl_pseudo"] = np.where(d.year < 2019, None, np.where(d.water_flag, "water", np.where(
        d.scl4_frac >= 0.8, "covered", np.where(d.scl5_frac >= 0.8, "bare", None))))
    d = d.drop(columns=[f"cdl_{y}" for y in YEARS])
    return d[d.label.notna()].reset_index(drop=True)


# ---------------------------------------------------------------- models / metrics
def make(method):
    if method == "random_forest":
        return RandomForestClassifier(n_estimators=300, class_weight="balanced", n_jobs=-1, random_state=0)
    return HistGradientBoostingClassifier(class_weight="balanced", random_state=0)


def scores(y, p):
    y, p = np.asarray(y), np.asarray(p)
    if len(y) == 0:
        return {"accuracy": None, "f1_bare": None, "n": 0}
    return {"accuracy": round(float(accuracy_score(y, p)), 4),
            "f1_bare": round(float(f1_score(y, p, labels=["bare"], average="macro", zero_division=0)), 4),
            "f1_macro": round(float(f1_score(y, p, labels=CLASSES3, average="macro", zero_division=0)), 4),
            "n": int(len(y))}


def split_preds(d: pd.DataFrame, split: str, method: str, feats):
    """Return (pred Series aligned to test rows, test mask, fitted model for 'year' split or None, leakage info)."""
    pred = pd.Series(index=d.index, dtype=object)
    leak = []
    if split == "year":
        tr, te = d.year.isin(TRAIN_YEARS), d.year.isin(TEST_YEARS)
        m = make(method).fit(d.loc[tr, feats], d.loc[tr, "label"])
        pred[te] = m.predict(d.loc[te, feats])
        leak.append({"train_years": sorted(d.loc[tr, "year"].unique().tolist()),
                     "test_years": sorted(d.loc[te, "year"].unique().tolist()),
                     "year_overlap": sorted(set(d.loc[tr, "year"]) & set(d.loc[te, "year"]))})
        return pred, te, m, leak
    gkf = GroupKFold(n_splits=4)
    te_all = pd.Series(False, index=d.index)
    for k, (i_tr, i_te) in enumerate(gkf.split(d, groups=d.block)):
        tr = d.index.isin(d.index[i_tr]); te = d.index.isin(d.index[i_te])
        if split == "year_spatial":
            tr &= d.year.isin(TRAIN_YEARS).values; te &= d.year.isin(TEST_YEARS).values
        m = make(method).fit(d.loc[tr, feats], d.loc[tr, "label"])
        pred[te] = m.predict(d.loc[te, feats])
        te_all |= te
        leak.append({"fold": k, "test_blocks": sorted(d.loc[te, "block"].unique().tolist()),
                     "block_overlap": sorted(set(d.loc[tr, "block"]) & set(d.loc[te, "block"])),
                     "cluster_overlap": len(set(d.loc[tr, "cluster_id"]) & set(d.loc[te, "cluster_id"])),
                     "year_overlap": sorted(set(d.loc[tr, "year"]) & set(d.loc[te, "year"])) if split == "year_spatial" else None})
    return pred, te_all, None, leak


def smooth3(cls_seq):
    """3-observation centred mode (ties -> centre value)."""
    s = list(cls_seq)
    o = s.copy()
    for i in range(1, len(s) - 1):
        a, b, c = s[i - 1], s[i], s[i + 1]
        if a == c and a != b:
            o[i] = a
    return o


def transition_mae(d: pd.DataFrame, pred_col: str):
    """Green-up / harvest date error (days) vs the midpoint of the CDL-window gap, per cluster-year."""
    errs = {"green_up": [], "harvest": []}
    for (cid, y), g in d.groupby(["cluster_id", "year"]):
        w = CROP_WINDOWS.get(int(g.cdl.iloc[0]))
        if not w or not w["covered"]:
            continue
        g = g.sort_values("doy")
        cov = np.array([c == "covered" for c in smooth3(g[pred_col])])
        doy = g.doy.values
        for a, b in w["covered"]:
            before = [be for (_, be) in w["bare"] if be < a]
            after = [bs for (bs, _) in w["bare"] if bs > b]
            if before:
                ref, lo, hi = (max(before) + a) / 2, max(before) - 30, b
                idx = [i for i in range(1, len(doy)) if lo <= doy[i] <= hi and cov[i] and not cov[i - 1]]
                if idx:
                    errs["green_up"].append(abs(doy[idx[0]] - ref))
            if after:
                ref, lo, hi = (b + min(after)) / 2, a, min(after) + 30
                idx = [i for i in range(1, len(doy)) if lo <= doy[i] <= hi and not cov[i] and cov[i - 1]]
                if idx:
                    errs["harvest"].append(abs(doy[idx[0]] - ref))
    allv = errs["green_up"] + errs["harvest"]
    return {"transition_mae_days": round(float(np.mean(allv)), 1) if allv else None,
            "transition_mae_green_up_days": round(float(np.mean(errs["green_up"])), 1) if errs["green_up"] else None,
            "transition_mae_harvest_days": round(float(np.mean(errs["harvest"])), 1) if errs["harvest"] else None,
            "transition_n": len(allv)}


def evaluate(d: pd.DataFrame, te, pred: pd.Series, split: str):
    t = d[te]
    p = pred[te]
    m = scores(t.label, p)
    out_ = {"accuracy": m["accuracy"], "f1_bare": m["f1_bare"], "f1_macro": m["f1_macro"], "n_test": m["n"]}
    if split in ("year", "year_spatial"):
        for y in TEST_YEARS:
            s = scores(t.label[t.year == y], p[t.year == y])
            out_[f"accuracy_{y}"], out_[f"f1_bare_{y}"], out_[f"n_{y}"] = s["accuracy"], s["f1_bare"], s["n"]
    sp = t.scl_pseudo.notna()
    out_["agreement_scl_pseudo"] = round(float((t.scl_pseudo[sp] == p[sp]).mean()), 4) if sp.any() else None
    out_["n_scl_pseudo"] = int(sp.sum())
    tt = t.assign(_p=p.values)
    out_.update(transition_mae(tt, "_p"))
    cm = confusion_matrix(t.label, p, labels=CLASSES3).tolist()
    return out_, cm


# ---------------------------------------------------------------- calendar for the preset field
def field_obs(preset: str) -> pd.DataFrame:
    s = pd.read_parquet(cache(preset) / "s2.parquet")
    s = s[(s.clear_frac >= 0.5) & (s.n_valid >= 20) & s.ndvi_med.notna()].copy()
    s["unit"] = preset
    s = s.sort_values(["date", "n_valid"], ascending=[True, False]).drop_duplicates("date")
    return add_features(s, preset, "unit")


def ml_calendar(preset: str, model, feats, rule_cal_path):
    d = field_obs(preset)
    proba = model.predict_proba(d[feats])
    cls = list(model.classes_)
    P = pd.DataFrame(proba, columns=cls, index=d.index).reindex(columns=CLASSES3, fill_value=0.0)  # CAF: no water label
    Ps = P.rolling(3, center=True, min_periods=1).mean()  # 3-observation smoothing
    d["ml_raw"] = P.idxmax(axis=1)
    d["ml"] = Ps.idxmax(axis=1)
    days = pd.date_range("2015-07-01", "2025-12-31", freq="D")
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
    # markers on the smoothed observation sequence
    marks = []
    seq, dates, nd = d["ml"].tolist(), d["date"].tolist(), d["ndvi"].tolist()
    for i in range(1, len(seq)):
        if (dates[i] - dates[i - 1]).days > MAX_GAP:
            continue
        if seq[i] == "covered" and seq[i - 1] != "covered":
            marks.append({"date": dates[i].strftime("%Y-%m-%d"), "type": "green_up", "ndvi": round(nd[i], 3)})
        if seq[i] == "bare" and seq[i - 1] == "covered":
            marks.append({"date": dates[i].strftime("%Y-%m-%d"), "type": "senescence_harvest", "ndvi": round(nd[i], 3)})
    rule = read_json(rule_cal_path)
    classes = {k: dict(v) for k, v in RULE_CLASSES.items()}
    classes["bare"]["label"] = "Bare (ML: random forest)"
    classes["covered"]["label"] = "Covered (ML: random forest)"
    classes["water"]["label"] = "Water (ML: random forest)"
    classes["partial"]["label"] = "Partial (not predicted: the CDL labels have no partial class)"
    years, dis_all = [], []
    for y in range(2016, 2026):
        s = full[str(y)]
        dy = d[d.date.dt.year == y]
        segs = segments(s, list(dy.date))
        cnt = s.value_counts().to_dict()
        dis = float((dy.ml != dy.rule3).mean()) if len(dy) else None
        if len(dy):
            dis_all.append((dy.ml != dy.rule3).values)
        rule_days = next((ry["summary"]["days_by_class"] for ry in rule["years"] if ry["year"] == y), None)
        years.append({
            "year": y, "segments": segs, "transitions": transitions(segs),
            "markers": [m for m in marks if m["date"].startswith(str(y))],
            "summary": {"days_by_class": {k: int(cnt.get(k, 0)) for k in RULE_CLASSES},
                        "n_obs": int(len(dy)), "n_obs_s2": int(len(dy)), "n_obs_landsat": 0,
                        "in_training_years": y in TRAIN_YEARS,
                        "disagreement_with_rule_obs_pct": round(100 * dis, 1) if dis is not None else None,
                        "rule_days_by_class": rule_days},
            "observations": [{"date": r.date.strftime("%Y-%m-%d"), "sensor": "s2", "ndvi": round(float(r.ndvi), 3),
                              "ndwi": round(float(r.ndwi), 3), "bsi": round(float(r.bsi), 3),
                              "clear_frac": round(float(r.clear_frac), 2), "class": r.ml, "class_unsmoothed": r.ml_raw,
                              "p_bare": round(float(Ps.loc[r.Index, "bare"]), 3),
                              "p_covered": round(float(Ps.loc[r.Index, "covered"]), 3),
                              "p_water": round(float(Ps.loc[r.Index, "water"]), 3), "rule_class": r.rule4}
                             for r in dy.itertuples()],
        })
    doc = {
        "preset_id": preset, "generated_at": now(), "detector": "random_forest",
        "classes": classes,
        "method": {"model": "RandomForestClassifier(n_estimators=300, class_weight='balanced', random_state=0)",
                   "trained_on": f"CDL-labelled clusters in the 10 km box (preset field excluded), years {TRAIN_YEARS}",
                   "features": feats, "observations": "Sentinel-2 only (field clear >= 0.5, >= 20 clear px); the model "
                   "was trained on S2, so Landsat dates used by the rule calendar are not classified",
                   "smoothing": "3-observation centred mean of class probabilities",
                   "daily_fill": f"linear interpolation of smoothed probabilities between observations <= {MAX_GAP} days "
                                 "apart, argmax; longer gaps unknown",
                   "markers": "green_up = smoothed class becomes covered; senescence_harvest = covered -> bare",
                   "out_of_sample_years": TEST_YEARS},
        "sources": rule.get("sources", []) + [
            {"id": "usda_cdl_croplandcros", "title": "USDA NASS Cropland Data Layer via CroplandCROS (training labels)",
             "url": "https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer", "accessed": today(),
             "verified": True}],
        "disagreement_with_rule_obs_pct": round(100 * float(np.concatenate(dis_all).mean()), 1) if dis_all else None,
        "years": years,
    }
    write_json(out(preset) / "calendar_ml.json", doc)
    return doc


# ---------------------------------------------------------------- report
def run(preset: str):
    d = training_table(preset)
    print(f"{preset}: {len(d)} labelled obs, {d.cluster_id.nunique()} clusters, labels {d.label.value_counts().to_dict()}",
          flush=True)
    items, details = [], {"preset_id": preset, "generated_at": now(), "n_obs": len(d),
                          "n_clusters": int(d.cluster_id.nunique()), "n_blocks": int(d.block.nunique()),
                          "labels": d.label.value_counts().to_dict(),
                          "labels_by_year": {int(y): g.label.value_counts().to_dict() for y, g in d.groupby("year")},
                          "splits": {}}
    year_models = {}
    for split in ("year", "spatial", "year_spatial"):
        details["splits"][split] = {}
        preds = {}
        for method in ("random_forest", "hist_gbt"):
            pr, te, m, leak = split_preds(d, split, method, CORE)
            preds[method] = pr
            if m is not None:
                year_models[method] = m
            details["splits"][split]["leakage"] = leak
        te = preds["random_forest"].notna()
        preds["rule_ndvi"] = d["rule3"].where(te)
        for method in ("rule_ndvi", "random_forest", "hist_gbt"):
            met, cm = evaluate(d, te, preds[method], split)
            others = [o for o in ("rule_ndvi", "random_forest", "hist_gbt") if o != method]
            dis = {o: round(float((preds[method][te] != preds[o][te]).mean()), 4) for o in others}
            fi = []
            if split == "year" and method != "rule_ndvi":
                t = d[te]
                samp = t.sample(min(4000, len(t)), random_state=0)
                pi = permutation_importance(year_models[method], samp[CORE], samp.label, scoring="f1_macro",
                                            n_repeats=5, random_state=0, n_jobs=-1)
                fi = sorted([{"feature": f, "importance": round(float(v), 4)} for f, v in zip(CORE, pi.importances_mean)],
                            key=lambda x: -x["importance"])
            if split == "year":
                spl = {"type": "year", "train_years": TRAIN_YEARS, "test_years": TEST_YEARS}
            elif split == "spatial":
                spl = {"type": "spatial_block", "train_years": YEARS, "test_years": YEARS,
                       "blocks": "GroupKFold(4) over 2.5 km blocks; each cluster in exactly one test fold"}
            else:
                spl = {"type": "year_and_spatial_block", "train_years": TRAIN_YEARS, "test_years": TEST_YEARS,
                       "blocks": "GroupKFold(4) over 2.5 km blocks; test clusters never seen in training"}
            short = {"rule_ndvi": "rule", "random_forest": "rf", "hist_gbt": "hgb"}[method]
            items.append({
                "id": f"bare_{short}_{preset}_{split}_v1", "task": "bare_cover", "method": method,
                "features": ["ndvi"] if method == "rule_ndvi" else CORE,
                "labels": LABELS_DESC, "split": spl, "metrics": {k: v for k, v in met.items()},
                "confusion": cm, "feature_importance": fi, "disagreement_with": dis,
                "notes": ("Confusion rows = CDL-window label, cols = prediction, order [bare, covered, water]. "
                          + ("Rule = backend/field B5.1 thresholds (NDVI < 0.20 bare, NDWI > 0.3 or SCL water > 50% "
                             "water); its 'partial' is scored as covered. " if method == "rule_ndvi" else
                             "Permutation importance (f1_macro drop, 5 repeats, <= 4000 test rows). " if fi else "")
                          + "Labels are CDL year classes plus calendar windows (U); in-season bare periods are not "
                            "labelled; 2022 is the only true held-out bare year. Unit: S2 date x 150 m CDL-homogeneous "
                            "cluster in the 10 km box; the preset field is excluded from training."),
            })
            details["splits"][split][method] = {"metrics": met, "confusion": cm, "disagreement_with": dis,
                                                "feature_importance": fi[:8]}
            print(f"  {split:13s} {method:14s} acc {met['accuracy']}  f1_bare {met['f1_bare']}  "
                  f"acc22 {met.get('accuracy_2022')}  f1b22 {met.get('f1_bare_2022')}  mae {met['transition_mae_days']}",
                  flush=True)
    # ablation: full spectral feature set (EVI, NBR2, reflectances, days since last obs), year split, RF only
    pr, te, m_full, _ = split_preds(d, "year", "random_forest", FULL)
    met, cm = evaluate(d, te, pr, "year")
    items.append({"id": f"bare_rf_full_{preset}_year_v1", "task": "bare_cover", "method": "random_forest",
                  "features": FULL, "labels": LABELS_DESC,
                  "split": {"type": "year", "train_years": TRAIN_YEARS, "test_years": TEST_YEARS},
                  "metrics": met, "confusion": cm, "feature_importance": [],
                  "disagreement_with": {"rule_ndvi": round(float((pr[te] != d.rule3[te]).mean()), 4)},
                  "notes": "Ablation: adds EVI, NBR2, red/NIR/SWIR1/SWIR2 reflectance and days since last obs. Not used "
                           "for the calendar because backend/field's field series stores only NDVI/NDWI/BSI medians."})
    details["splits"]["year"]["random_forest_full"] = {"metrics": met, "confusion": cm}
    print(f"  year (full)   random_forest  acc {met['accuracy']}  f1_bare {met['f1_bare']}  acc22 {met['accuracy_2022']}")
    # diagnostic ablation: drop the seasonal proxies (DOY sin/cos, 7-day Tmax) to see how much the models lean on
    # the calendar windows that define the labels. Diagnostic only; the headline models are unchanged.
    noseason = [f for f in CORE if f not in ("doy_sin", "doy_cos", "tmax7")]
    pr, te, _, _ = split_preds(d, "year", "random_forest", noseason)
    met, cm = evaluate(d, te, pr, "year")
    items.append({"id": f"bare_rf_noseason_{preset}_year_v1", "task": "bare_cover", "method": "random_forest",
                  "features": noseason, "labels": LABELS_DESC,
                  "split": {"type": "year", "train_years": TRAIN_YEARS, "test_years": TEST_YEARS},
                  "metrics": met, "confusion": cm, "feature_importance": [],
                  "disagreement_with": {"rule_ndvi": round(float((pr[te] != d.rule3[te]).mean()), 4)},
                  "notes": "Diagnostic ablation without DOY sin/cos and 7-day Tmax (seasonal proxies). Because the labels "
                           "are built from calendar windows, a model can score well by learning the calendar; this "
                           "shows how much of the score is spectral. Not used for the calendar or the checks."})
    details["splits"]["year"]["random_forest_noseason"] = {"metrics": met, "confusion": cm,
                                                           "disagreement_with_rule": items[-1]["disagreement_with"]["rule_ndvi"]}
    print(f"  year (noseas) random_forest  acc {met['accuracy']}  f1_bare {met['f1_bare']}  acc22 {met['accuracy_2022']}  "
          f"f1b22 {met['f1_bare_2022']}")
    cal = ml_calendar(preset, year_models["random_forest"], CORE, FIELD_DIR / "out" / preset / "calendar.json")
    details["calendar_ml"] = {"disagreement_with_rule_obs_pct": cal["disagreement_with_rule_obs_pct"],
                              "by_year": {y["year"]: {"days": y["summary"]["days_by_class"],
                                                      "rule_days": y["summary"]["rule_days_by_class"],
                                                      "disagree_pct": y["summary"]["disagreement_with_rule_obs_pct"]}
                                          for y in cal["years"]}}
    doc = {"location_id": preset, "generated_at": now(),
           "source": "backend/ai (fieldshift_ai.bare_cover, fieldshift_ai.stress)", "items": items}
    p = out(preset) / "models.json"
    if p.exists():  # keep stress reports written by stress.py
        doc["items"] += [i for i in read_json(p).get("items", []) if i["task"] == "stress_anomaly"]
    write_json(p, doc)
    write_json(out(preset) / "bare_cover_eval.json", details)
    print(f"  calendar_ml: rule-vs-ML disagreement {cal['disagreement_with_rule_obs_pct']}% of S2 obs")


if __name__ == "__main__":
    for p in (sys.argv[1:] or PRESETS):
        run(p)
