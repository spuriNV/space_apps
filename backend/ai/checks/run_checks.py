"""PASS/FAIL lines for spec B10.1 checks 8 (bare/cover ML) and 9 (crop stress) (the ds branch numbers them 7 and 8),
plus leakage and input-coverage checks. Local files only.

Usage (from backend/ai): uv run python checks/run_checks.py [fid ...]
Targets are the spec's; models were not tuned on any test set to meet them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator
from pyproj import Transformer
from referencing import Registry, Resource
from shapely.geometry import Point, shape
from shapely.ops import transform

AI = Path(__file__).resolve().parents[1]
REPO = AI.parents[1]
sys.path.insert(0, str(AI))
from fieldshift_ai.common import TRAINED, field_ids, template  # noqa: E402

counts = {"PASS": 0, "FAIL": 0, "INFO": 0}
TESTS = ("unseen_fields", "unseen_years", "fallow_2022")


def line(status, name, msg):
    counts[status] += 1
    print(f"{status} | {name} | {msg}")


def load(p):
    return json.loads(Path(p).read_text())


def validator():
    reg = Registry()
    for f in (REPO / "schemas").glob("*.json"):
        s = load(f)
        res = Resource.from_contents(s)
        reg = reg.with_resource(f.name, res)
        if "$id" in s:
            reg = reg.with_resource(s["$id"], res)
    return Draft202012Validator(load(REPO / "schemas" / "model_report.schema.json"), registry=reg)


def f3(x):
    return "n/a" if x is None else f"{x:.3f}"


def field_distance_to_clusters(fid, tpl):
    cl = pd.read_parquet(REPO / "data" / "cache" / tpl / "ai" / "clusters.parquet")
    fc = load(REPO / "backend" / "field" / "polygons" / f"{fid}.geojson")
    t = Transformer.from_crs("EPSG:4326", "EPSG:32610", always_xy=True)
    fld = transform(t.transform, shape(fc["features"][0]["geometry"]))
    return min(fld.distance(Point(x, y)) for x, y in zip(cl.x32610, cl.y32610))


def check_trained(fid, o, v):
    ev = load(o / "bare_cover_eval.json")
    line("INFO", f"training data {fid}", f"{ev['n_labelled']} labelled S2 dates of {ev['n_clusters']} clusters in "
         f"{ev['n_blocks']} blocks; labels {ev['labels']}; label sources {ev['label_sources']}")
    # ---- leakage
    feats = ev["features"]
    bad = [f for f in feats if f.startswith("scl_") or f in ("label", "label_cdl", "cdl_class", "water_frac")]
    line("PASS" if not bad else "FAIL", f"leakage {fid} features exclude the label sources",
         f"features {feats}; label-source columns among them: {bad or 'none'}")
    lk = ev["tests"]["unseen_fields"]["leakage"]
    badf = [f for f in lk if f["block_overlap"] or f["cluster_overlap"]]
    line("PASS" if not badf else "FAIL", f"leakage {fid} unseen_fields: no block or cluster in both train and test",
         f"{len(lk)} folds, test blocks {[f['test_blocks'] for f in lk]}")
    for t in ("unseen_years", "fallow_2022"):
        ly = ev["tests"][t]["leakage"][0]
        line("PASS" if not ly["year_overlap"] else "FAIL", f"leakage {fid} {t}: no year in both train and test",
             f"train {ly['train_years']} test {ly['test_years']}")
    dmin = field_distance_to_clusters(fid, fid)
    line("PASS" if dmin >= 140 else "FAIL", f"leakage {fid} the field itself is never training data",
         f"nearest training-cluster centre {dmin:.0f} m from the field outline (cluster radius 75 m)")
    # ---- check 8
    uf = ev["tests"]["unseen_fields"]
    for m in ("random_forest", "hist_gbt", "consensus", "rule_ndvi"):
        mt = uf[m]["metrics"]
        ok = mt["accuracy"] >= 0.85 and mt["f1_bare"] >= 0.80
        st = "INFO" if m in ("rule_ndvi", "consensus") else ("PASS" if ok else "FAIL")
        line(st, f"check 8 {fid} {m} HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80",
             f"vs crop-map labels: acc {f3(mt['accuracy'])}, F1(bare) {f3(mt['f1_bare'])}, n {mt['n_test']}; vs merged "
             f"labels (mostly S2 classes): acc {f3(mt['accuracy_merged'])}, F1(bare) {f3(mt['f1_bare_merged'])}"
             + ("" if ok or st == "INFO" else " -> 'below target' badge"))
    f22 = ev["tests"]["fallow_2022"]
    for m in ("random_forest", "hist_gbt", "rule_ndvi"):
        mt = f22[m]["metrics"]
        ok = mt["accuracy_2022"] is not None and mt["accuracy_2022"] >= 0.85 and mt["f1_bare_2022"] >= 0.80
        line("INFO" if m == "rule_ndvi" else ("PASS" if ok else "FAIL"),
             f"check 8 {fid} {m} 2022 hold-out (spec wording; EASY test, {100 * (mt.get('bare_label_share') or 0):.0f}% "
             "bare labels)", f"acc {f3(mt['accuracy_2022'])}, F1(bare) {f3(mt['f1_bare_2022'])}, n {mt['n_2022']}")
    uy = ev["tests"]["unseen_years"]
    line("INFO", f"check 8 {fid} unseen years 2023-2025 (rule / RF / HGB / vote)",
         " / ".join(f"{f3(uy[m]['metrics']['accuracy'])}" for m in ("rule_ndvi", "random_forest", "hist_gbt", "consensus"))
         + " accuracy; per year RF " + ", ".join(f"{y} {f3(uy['random_forest']['metrics'].get(f'accuracy_{y}'))}"
                                               for y in (2023, 2024, 2025)))
    line("INFO", f"check 8 {fid} agreement with Sentinel-2 classification (unseen fields; agreement, not accuracy)",
         " / ".join(f"{m} {f3(uf[m]['metrics']['agreement_scl'])}" for m in ("rule_ndvi", "random_forest", "hist_gbt", "consensus")))
    maes = {m: uf[m]["metrics"]["transition_mae_days"] for m in ("rule_ndvi", "random_forest", "hist_gbt", "consensus")}
    labs = {m: uf[m]["metrics"]["transition_mae_vs_labels_days"] for m in maes}
    line("PASS" if all(x is not None for x in maes.values()) else "FAIL", f"check 8 {fid} transition MAE reported (days)",
         "vs crop-map window midpoints: " + ", ".join(f"{m} {x:.1f}" for m, x in maes.items())
         + "; vs the label sequence (mostly S2 classes, ds design): " + ", ".join(f"{m} {x:.1f}" for m, x in labs.items()
                                                                                 if x is not None))
    dis = uf["random_forest"]["disagreement_with"]["rule_ndvi"]
    cal = ev.get("calendar_ml", {}).get("disagreement_with_rule_obs_pct")
    line("PASS" if dis < 0.15 else "FAIL", f"check 8 {fid} rule-vs-ML disagreement < 15% (or explained)",
         f"RF vs rule on unseen-field test dates {100 * dis:.1f}%; on the field's own S2 dates {cal}%"
         + ("" if dis < 0.15 else " (explained in README: rule 'thin cover' vs ML bare on weedy fallow and stubble)"))
    for tag in ("full", "noseason"):
        k = f"random_forest_{tag}"
        if k in uf:
            mt = uf[k]["metrics"]
            line("INFO", f"check 8 {fid} ablation {tag} (RF, unseen fields)", f"acc {f3(mt['accuracy'])}, F1(bare) "
                 f"{f3(mt['f1_bare'])}, agreement with S2 classes {f3(mt['agreement_scl'])}")


def check_field(fid, o, v):
    if not (o / "models.json").exists():
        line("FAIL", f"outputs {fid}", "models.json missing")
        return
    models = load(o / "models.json")
    errs = [f"{it['id']}: {e.message}" for it in models["items"] for e in v.iter_errors(it)]
    line("PASS" if not errs else "FAIL", f"ModelReport schema {fid}",
         f"{len(models['items'])} items valid" if not errs else "; ".join(errs[:3]))
    head = [i for i in models["items"] if i.get("headline") and i["method"] == "random_forest"]
    line("PASS" if head else "FAIL", f"models.json {fid} has the headline (unseen fields) RF report",
         head[0]["id"] if head else "missing" + (f" (model from {models.get('model_from')})" if models.get("model_from") else ""))
    if fid in TRAINED:
        check_trained(fid, o, v)
    else:
        tpl = template(fid)
        dmin = field_distance_to_clusters(fid, tpl)
        line("PASS" if dmin >= 140 else "FAIL", f"leakage {fid} field is not among {tpl}'s training clusters",
             f"nearest training-cluster centre {dmin / 1000:.1f} km away; model applied without retraining "
             f"(field {'inside' if models.get('field_in_training_box') else 'outside'} the training box)")
    # calendar_ml + transitions
    if (o / "calendar_ml.json").exists():
        c = load(o / "calendar_ml.json")
        bad = []
        for y in c["years"]:
            segs = y["segments"]
            n = sum(s["days"] for s in segs)
            nd = 366 if pd.Timestamp(f"{y['year']}-12-31").dayofyear == 366 else 365
            cont = all(pd.Timestamp(a["end"]) + pd.Timedelta(days=1) == pd.Timestamp(b["start"]) for a, b in zip(segs, segs[1:]))
            if n != nd or not cont or segs[0]["start_doy"] != 1:
                bad.append(y["year"])
        line("PASS" if not bad else "FAIL", f"calendar_ml shape {fid}", f"{len(c['years'])} years "
             f"{c['years'][0]['year']}-{c['years'][-1]['year']}, segments tile Jan 1-Dec 31: {not bad}; data through "
             f"{c['data_through']}")
        fe = c.get("field_evaluation", {})
        rf = fe.get("random_forest", {})
        line("INFO", f"field {fid} (never in training): agreement with its own Sentinel-2 classes",
             " / ".join(f"{m} {f3(fe[m]['agreement_scl'])}" for m in fe) + f" (n {rf.get('n_scl')}); transition MAE vs "
             f"those classes: " + ", ".join(f"{m} {fe[m]['transition_mae_vs_scl_days']:.1f} d" for m in fe
                                            if fe[m]["transition_mae_vs_scl_days"] is not None))
        if rf.get("opera_scenes"):
            line("INFO", f"field {fid} water vs NASA OPERA DSWx (independent; the model never sees OPERA)",
                 " / ".join(f"{m} {fe[m]['opera_water_detected']}/{fe[m]['opera_water_scenes']} water scenes found, "
                            f"{fe[m]['opera_dry_called_water']} dry called water" for m in ("rule_ndvi", "random_forest", "consensus")))
        tp = o / "transitions.json"
        if tp.exists():
            t = load(tp)
            types = {e["type"] for evs in t["methods"].values() for e in evs}
            ok = types <= {"green_up", "senescence_harvest", "cutting"}
            nc = sum(e["type"] == "cutting" for e in t["methods"]["random_forest"])
            line("PASS" if ok else "FAIL", f"transitions.json {fid}", f"methods {sorted(t['methods'])}; types {sorted(types)}; "
                 f"RF cuttings {nc}")
        else:
            line("FAIL", f"transitions.json {fid}", "missing")
    else:
        line("INFO", f"calendar_ml {fid}", "not written: no Sentinel-2 field series cached for this field yet")
    # ---- check 9: stress
    sw_p, ss_p = o / "stress_weekly.json", o / "stress_summary.json"
    if not sw_p.exists() or not ss_p.exists():
        line("FAIL", f"stress outputs {fid}", "stress_weekly.json / stress_summary.json missing")
        return
    sw, ss = load(sw_p), load(ss_p)
    need = {"iso_year", "iso_week", "week_start", "status", "drivers", "reasons", "flag_zscore", "flag_iforest", "evaluated"}
    badw = [w["week_start"] for w in sw["weeks"] if not need <= set(w)]
    line("PASS" if not badw and sw["weeks"] else "FAIL", f"stress_weekly shape {fid}",
         f"{len(sw['weeks'])} weeks; statuses {pd.Series([w['status'] for w in sw['weeks']]).value_counts().to_dict()}")
    cov = ss["input_coverage_scored_weeks"]
    n = ss["evaluation"]["weeks_scored"]
    missing = [k for k, x in cov.items() if x == 0]
    line("PASS" if cov["z_ndvi"] > 0.8 * n else "FAIL", f"coverage {fid} stress inputs on scored weeks",
         f"{n} weeks; non-missing z: {cov}; sources {ss['inputs']}" + (f"; missing entirely: {missing}" if missing else ""))
    ch = ss["checks"]
    for k in ("julaug_2021", "julaug_2022"):
        c = ch[k]
        if not c["applicable"]:
            line("INFO", f"check 9 {fid} {k.replace('_', ' ')} >= 2 flagged weeks (both methods)", "not applicable: " + c["note"])
        else:
            line("PASS" if c["pass"] else "FAIL", f"check 9 {fid} {k.replace('_', ' ')} >= 2 flagged weeks (both methods)",
                 f"zscore {c['flagged_zscore']}, iforest {c['flagged_iforest']} of {c['weeks']} weeks")
    c = ch["flood_2023_water_not_stress"]
    line("PASS" if c["pass"] else "FAIL", f"check 9 {fid} 2023 water weeks are water, not stress",
         f"{c['water_weeks']} in-season water weeks in 2023, {c['flagged']} shown as stress")
    e = ss["evaluation"]
    for m in ("zscore", "iforest"):
        rec, base = e[f"recall_usdm_d3_{m}"], e[f"flag_rate_no_drought_{m}"]
        if rec is None or base is None:
            line("INFO", f"check 9 {fid} {m} Drought Monitor D3+ weeks", f"{e['usdm_d3_weeks']} D3+ crop weeks; "
                 f"no-drought weeks {e['usdm_no_d3_weeks']}: not testable")
            continue
        line("PASS" if rec > base else "FAIL", f"check 9 {fid} {m} flags D3+ drought weeks more often than no-drought weeks",
             f"recall {rec:.2f} of {e['usdm_d3_weeks']} D3+ crop weeks vs {base:.2f} of {e['usdm_no_d3_weeks']} weeks with "
             f"no D3; wet-cool weeks flagged {e[f'false_positive_proxy_{m}']}")
    fl = ch["fallow_not_stress"]
    line("INFO", f"check 9 {fid} fallow is not stress", f"fallow years {fl['fallow_years']} ({fl['weeks']} weeks) scored "
         f"(flag rates z {fl['flag_rate_zscore']}, IF {fl['flag_rate_iforest']}) but shown as fallow, out of the evidence")
    line("INFO", f"check 9 {fid} evidence", f"{ss['evidence']} | agreement {e['agreement']:.2f}")


def main():
    v = validator()
    fids = sys.argv[1:] or field_ids()
    for fid in fids:
        o = AI / "out" / fid
        meta = REPO / "data" / "cache" / fid / "ai" / "inputs.meta.json"
        if meta.exists():
            m = load(meta)
            wk = m["tables"]["weekly"]["coverage"]
            line("INFO", f"coverage {fid} weekly inputs", ", ".join(f"{k} {x['n']} ({x.get('first')}..{x.get('last')})"
                                                                    for k, x in wk.items()))
        else:
            line("FAIL", f"coverage {fid}", "inputs.meta.json missing: run fieldshift_ai.inputs")
        check_field(fid, o, v)
    print(f"---- {counts['PASS']} PASS, {counts['FAIL']} FAIL, {counts['INFO']} INFO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
