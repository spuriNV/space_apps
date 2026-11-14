"""Engine checks: spec B10.1 check 12 + structural checks + sanity table.

Run from backend/engine:  uv run python checks/run_checks.py
Prints PASS/FAIL lines. Formulas are NOT tuned to pass; a FAIL with an
explanation means the spec formula and the check disagree (see README).
"""
from __future__ import annotations

import copy
import json
import random
import sys

import numpy as np

from rotation_engine import af_to_mm, mm_to_af, score
from rotation_engine.engine import DEFAULT_YEARS, intervals_tie, load_crops, load_strategies, weather_years
from rotation_engine.model import cover_metrics
from rotation_engine.timeline import build_timeline
from rotation_engine.weather import CHUNK, PRESETS

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))


def by_id(recs):
    return {r["id"]: r for r in recs}


def main():
    out = {p: score(p) for p in PRESETS}
    car, caf = by_id(out["car_colusa_rice"]), by_id(out["caf_tulare_forage"])

    print("== Spec B10.1 check 12 ==")
    for p, recs in out.items():
        b = next(r for r in recs if r["is_baseline"])
        e = b["scores"]["erosion"]
        check(f"baseline erosion 0 ({p}, blended score as specified)", e["value"] == 0,
              f"value={e['value']}. Spec B4.4 blends 70% exposure term with 30% crop residue rating, so the "
              f"baseline gets 0.3 x 100 x residue/4 > 0 unless its residue rating is 0. Formula/check conflict; "
              f"not tuned.")
        check(f"baseline erosion exposure component 0 ({p})", e["exposure_component"]["value"] == 0,
              f"100 x (1 - E/E_baseline) = {e['exposure_component']['value']}")

    crops = load_crops()
    full_cover = {"id": "synthetic_full_cover", "cycle_years": 1, "calendar": [
        {"year": 1, "crop_id": "cereal_vetch_cover", "plant": "01-01", "harvest": "01-01", "role": "cover",
         "irrigated": False, "stage_mode": "stretch_mid", "cover_override": {"ini": 1, "dev": 1, "mid": 1, "late": 1}}]}
    for p in PRESETS:
        tl = build_timeline(full_cover, crops)
        cm = cover_metrics(tl, list(weather_years(p, DEFAULT_YEARS, 0.0, 0.0)))
        check(f"full-year cover -> exposed rain days ~ 0 ({p})", cm["rain"] < 0.5,
              f"exposed_rain_days={cm['rain']:.2f} (unexposed field still sees {cm['rain_days_total']:.1f} "
              f"extreme-rain days/yr)")

    alf = next(b for b in caf["caf0_alfalfa"]["water"]["by_crop"] if b["crop_id"] == "alfalfa_hay")
    sg = next(b for b in caf["caf1_smallgrain_corn"]["water"]["by_crop"] if b["crop_id"] == "small_grain_silage")
    check("alfalfa summer (Jun-Aug) ETc > small-grain season ETc",
          alf["etc_jun_aug_mm"]["value"] > sg["etc_mm"]["value"],
          f"alfalfa JJA {alf['etc_jun_aug_mm']['value']} mm vs small grain {sg['etc_mm']['value']} mm")

    bc = {b["crop_id"]: b for b in car["car3_rice_wheat"]["water"]["by_crop"]}
    check("rice irrigation need > wheat irrigation need (CAR3 by crop)",
          bc["rice_medium_grain"]["irrigation_need_mm"]["value"] > bc["winter_wheat"]["irrigation_need_mm"]["value"],
          f"rice {bc['rice_medium_grain']['irrigation_need_mm']['value']} mm vs wheat "
          f"{bc['winter_wheat']['irrigation_need_mm']['value']} mm")

    for p in PRESETS:
        e0 = np.mean([w.eto.sum() for w in weather_years(p, DEFAULT_YEARS, 0.0, 0.0)])
        e2 = np.mean([w.eto.sum() for w in weather_years(p, DEFAULT_YEARS, 2.0, 0.0)])
        check(f"+2 C raises ETo ({p})", e2 > e0, f"{e0:.0f} -> {e2:.0f} mm/yr")
        hot = by_id(score(p, scenario={"dT_c": 2.0, "dP_pct": 0}))
        for r in out[p]:
            i0, i2 = r["water"]["irrigation_need_mm"]["value"], hot[r["id"]]["water"]["irrigation_need_mm"]["value"]
            check(f"+2 C raises irrigation need ({r['id']})", i2 > i0, f"{i0} -> {i2} mm/yr")
        dry = by_id(score(p, scenario={"dT_c": 0, "dP_pct": -30}))
        r0 = out[p][0]
        check(f"-30% rain raises irrigation need ({r0['id']})",
              dry[r0["id"]]["water"]["irrigation_need_mm"]["value"] >= r0["water"]["irrigation_need_mm"]["value"],
              f"{r0['water']['irrigation_need_mm']['value']} -> "
              f"{dry[r0['id']]['water']['irrigation_need_mm']['value']} mm/yr")

    for p in PRESETS:
        b = next(r for r in out[p] if r["is_baseline"])
        imax = b["water"]["irrigation_need_max_cycle_year_mm"]["value"]
        low_alloc = mm_to_af(imax * 0.5)
        hi_alloc = mm_to_af(b["water"]["irrigation_need_max_cycle_year_mm"]["high"] * 2)
        st_low = by_id(score(p, allocation=low_alloc))[b["id"]]["water"]["allocation_check"]["status"]
        st_hi = by_id(score(p, allocation={"value": hi_alloc, "unit": "acre-ft/acre"}))[b["id"]]["water"][
            "allocation_check"]["status"]
        check(f"allocation check triggers when I > allocation ({p})", st_low == "exceeds_allocation",
              f"I={imax:.0f} mm, allocation {low_alloc:.2f} af/ac -> {st_low}")
        check(f"allocation check silent when allocation >> I ({p})", st_hi == "within_allocation",
              f"allocation {hi_alloc:.2f} af/ac -> {st_hi}")

    print("== Structure ==")
    bad_leaf, no_url, bad_order, n_sn, n_unv = [], [], [], 0, 0
    STRUCT = {"cycle_years", "year", "rank", "harvest_months", "rma_years", "weather_years", "dT_c", "dP_pct",
              "stage_override", "cover_override", "weights_used", "agronomic_gap_count"}

    def walk(x, path, parent_is_sn=False):
        nonlocal n_sn, n_unv
        if isinstance(x, dict):
            is_sn = "value" in x and "unit" in x and "source" in x
            if is_sn:
                n_sn += 1
                if not (x["source"] or {}).get("url"):
                    no_url.append(path)
                if not (x["source"] or {}).get("verified"):
                    n_unv += 1
                v, lo, hi = x["value"], x["low"], x["high"]
                if v is not None and not (lo is not None and hi is not None and lo - 1e-9 <= v <= hi + 1e-9):
                    bad_order.append(f"{path}: {lo} <= {v} <= {hi}")
            for k, v in x.items():
                if k in STRUCT:
                    continue
                walk(v, f"{path}.{k}", is_sn and k in ("value", "low", "high"))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            if not parent_is_sn:
                bad_leaf.append(path)

    for p, recs in out.items():
        walk(recs, p)
    check("every numeric leaf in strategy output is inside a SourcedNumber", not bad_leaf, f"{bad_leaf[:5]}")
    check("every SourcedNumber has a source URL", not no_url, f"{n_sn} SourcedNumbers; missing: {no_url[:5]}")
    check("low <= value <= high everywhere", not bad_order, f"{bad_order[:5]}")
    print(f"INFO  verified:false SourcedNumbers in output: {n_unv} of {n_sn}")
    for p, recs in out.items():
        for r in recs:
            print(f"INFO  {r['id']}: agronomic U inputs used {r['uncertainty']['agronomic_gap_count']}")

    crops_js = json.loads((CHUNK / "crops.json").read_text())
    bad_leaf.clear(), no_url.clear(), bad_order.clear()
    STRUCT.update({"stage_lengths_days", "cover_by_stage"})  # plain ints/floats per spec B3 Crop example
    walk(crops_js, "crops.json")
    check("crops.json: numeric leaves are SourcedNumbers (except stage_lengths_days/cover_by_stage, plain per B3)",
          not bad_leaf, f"{bad_leaf[:5]}")
    check("crops.json: low <= value <= high and URLs present", not bad_order and not no_url,
          f"{bad_order[:3]} {no_url[:3]}")
    unv = [c["id"] + ".kc." + s for c in crops_js["crops"] for s in ("ini", "mid", "end")
           if c["kc"][s]["source"]["verified"] and c["kc"][s]["method"] != "lookup"]
    check("crops.json: only spec-V Kc values are verified:true", not unv, f"{unv}")

    rnd = random.Random(12)
    sym = True
    for _ in range(20000):
        a = sorted([rnd.uniform(0, 100), rnd.uniform(0, 100)])
        b = sorted([rnd.uniform(0, 100), rnd.uniform(0, 100)])
        if rnd.random() < 0.1:
            a[1] = a[0]
        if intervals_tie(tuple(a), tuple(b)) != intervals_tie(tuple(b), tuple(a)):
            sym = False
    for recs in out.values():
        for r in recs:
            for o in r["composite"]["ties_with"]:
                if r["id"] not in by_id(recs)[o]["composite"]["ties_with"]:
                    sym = False
    check("tie rule symmetric (20,000 random interval pairs + output ties_with)", sym)
    check("tie rule: 60% overlap ties, 40% does not",
          intervals_tie((0, 10), (4, 14)) and not intervals_tie((0, 10), (6, 16)))

    rt = all(abs(mm_to_af(af_to_mm(x)) - x) < 1e-12 for x in np.linspace(0, 10, 101)) and \
        all(abs(af_to_mm(mm_to_af(x)) - x) < 1e-9 for x in np.linspace(0, 3000, 101))
    check("unit conversion round-trips (acre-ft/acre <-> mm)", rt and af_to_mm(1) == 304.8,
          "1 acre-ft/acre = 304.8 mm")

    for p in PRESETS:
        r = out[p][0]
        check(f"replay 2022 and 2023 present ({p})", all(r["exposure"]["replay"].get(y) for y in ("2022", "2023")))
        rep = score(p, replay_year=2022)
        check(f"replay_year=2022 runs on one weather year ({p})",
              rep[0]["model_assumptions"]["weather_years"] == [2022])

    print("\n== OpenET independent check (baseline, CDL-matched years; reported, never tuned) ==")
    for p, recs in out.items():
        b = next(r for r in recs if r["is_baseline"])
        pct, oe = b["water"]["etc_vs_openet_pct"], b["water"]["openet_et_mm_season"]
        if pct["value"] is None:
            print(f"SKIP  {p}: {pct['note']}")
            continue
        check(f"baseline ETc vs OpenET |bias| <= 25% ({p})", abs(pct["value"]) <= 25,
              f"{pct['value']:+.1f}% (engine range {pct['low']:+.1f}..{pct['high']:+.1f}%), OpenET {oe['value']:.0f} mm")
        check(f"OpenET source is measured and not a score input ({p})",
              oe["method"] == "measured" and "never a score input" in oe["source"]["title"])
        others = [r for r in recs if not r["is_baseline"]]
        check(f"alternatives carry no OpenET number ({p})",
              all(r["water"]["etc_vs_openet_pct"]["value"] is None for r in others))

    print("\n== Sanity table: default weather years "
          f"{DEFAULT_YEARS[0]}-{DEFAULT_YEARS[-1]}, POWER precip nominal; value [low-high] ==")
    hdr = f"{'strategy':30s} {'ETc crop days mm/yr':>22s} {'ETc all days mm/yr':>20s} {'I mm/yr':>20s} {'I af/ac/yr':>17s}"
    print(hdr)
    print("-" * len(hdr))
    for recs in out.values():
        for r in recs:
            w = r["water"]
            f = lambda x, d=0: f"{x['value']:.{d}f} [{x['low']:.{d}f}-{x['high']:.{d}f}]"
            print(f"{r['id']:30s} {f(w['etc_mm_season']):>22s} {f(w['etc_mm_year']):>20s} "
                  f"{f(w['irrigation_need_mm']):>20s} {f(w['irrigation_need_af_ac'], 1):>17s}")
    print("\nBy crop (one season, per cycle year it occurs):")
    print(f"{'strategy':30s} {'crop':22s} {'yr':>2s} {'ETc mm':>8s} {'I mm':>8s} {'I af/ac':>8s}")
    for recs in out.values():
        for r in recs:
            for b in r["water"]["by_crop"]:
                i = b["irrigation_need_mm"]["value"]
                print(f"{r['id']:30s} {b['crop_id']:22s} {b['year']:>2d} {b['etc_mm']['value']:>8.0f} "
                      f"{i:>8.0f} {mm_to_af(i):>8.2f}")

    n_fail = RESULTS.count(False)
    print(f"\n{len(RESULTS) - n_fail} PASS, {n_fail} FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
