"""PASS/FAIL checks for the ground-data chunk. Run: uv run python checks/run_checks.py"""
import json, sys, math
from pathlib import Path
G = Path(__file__).resolve().parents[1]; ROOT = G.parents[1]
sys.path.insert(0, str(G / "src"))
sys.path.insert(0, str(ROOT / "backend" / "fields"))
import fieldreg  # noqa: E402
import numpy as np, pandas as pd
IDS = fieldreg.selected()   # every registry field
fails = 0
def line(ok, msg):
    global fails
    print(("PASS " if ok else "FAIL ") + msg); fails += (not ok)
def info(msg): print("INFO " + msg)
def skip(msg): print("SKIP " + msg)

# ---- RMA
for preset in IDS:
    p = G / "out" / preset / "rma_profile.json"
    if not p.exists(): line(False, f"RMA profile missing for {preset}"); continue
    d = json.load(open(p))
    for k, pr in d["profiles"].items():
        if "shares" not in pr: line(False, f"RMA {preset} {k}: {pr}"); continue
        s = sum(v["value"] for v in pr["shares"].values())
        yrs = pr["years_with_indemnity"]
        line(abs(s - 1) < 0.01, f"RMA {preset} {k}: shares sum {s:.4f}")
        line(len(yrs) >= 8 and min(yrs) <= 2015 and max(yrs) >= 2022, f"RMA {preset} {k}: indemnity years {min(yrs)}-{max(yrs)} ({len(yrs)} yrs)")
        line(all(v["source"]["url"] and v["source"]["verified"] for v in pr["shares"].values()), f"RMA {preset} {k}: sources present, verified")
        if pr["share_peril_unattributed"] > 0.5: info(f"RMA {preset} {k}: {pr['share_peril_unattributed']:.0%} of indemnity is index-plan with no peril; split not meaningful")
# ---- EQIP
p = G / "out" / "eqip_340_ca.json"
if p.exists():
    e = json.load(open(p)); r = e["usd_per_acre"]
    line(0 < r["low"] <= r["high"] < 1000 and r["source"]["url"].startswith("https://"), f"EQIP 340 CA ${r['low']}-{r['high']}/ac, source {r['source']['url']}")
else: line(False, "EQIP 340 file missing")

# ---- keyed data
def load(preset, name):
    f = ROOT / "data" / "cache" / preset / f"{name}.parquet"
    return pd.read_parquet(f) if f.exists() else None
for preset in IDS:
    oe = load(preset, "openet"); ci = load(preset, "cimis")
    if oe is not None and not (ROOT / "backend/engine/out" / preset / "strategies.json").exists():
        skip(f"{preset} OpenET cached; engine strategies not built yet"); oe = None
    elif oe is None: skip(f"{preset} OpenET not fetched (BLOCKED: no OPENET_API_KEY)")
    else:
        e = oe[oe["model"] == "Ensemble"] if "model" in oe else oe
        v = e["et_mm"]; line(v.min() >= 0 and v.max() <= 400, f"{preset} OpenET monthly range {v.min():.1f}-{v.max():.1f} mm (0-400)")
        # vs engine ETc, monthly climatology 2019-2024
        sj = json.load(open(ROOT / "backend/engine/out" / preset / "strategies.json")); b = [x for x in sj if x["is_baseline"]][0]
        eng = np.array([m["value"] for m in b["water"]["etc_by_month_mm"]])
        # CDL-matched years only (same rule as backend/engine/checks/validate_et.py): years whose CDL majority crop is the baseline crop
        BASE_CDL = {preset: {"rice": "Rice", "forage": "Alfalfa"}[fieldreg.get(preset)["family"]]}
        hist = json.load(open(ROOT / "backend/field/out" / preset / "crop_history.json"))["by_year"]
        matched = [y for y in range(2016, 2026) if hist.get(str(y)) == BASE_CDL[preset]]
        e = e.assign(date=pd.to_datetime(e["date"])); e = e[e.date.dt.year.isin(matched)]
        info(f"{preset} CDL-matched years ({BASE_CDL[preset]}): {matched}")
        clim = e.groupby(e.date.dt.month)["et_mm"].mean().reindex(range(1, 13)).values
        ok = ~np.isnan(clim); diff = eng[ok] - clim[ok]
        bias = diff.sum() / clim[ok].sum() * 100; rmse = math.sqrt((diff ** 2).mean())
        lo = sum(m["low"] for m in b["water"]["etc_by_month_mm"]); hi = sum(m["high"] for m in b["water"]["etc_by_month_mm"])
        line(abs(bias) <= 25, f"{preset} engine ETc vs OpenET Ensemble CDL-matched years monthly: annual bias {bias:+.1f}% (target |bias|<=25%), monthly RMSE {rmse:.1f} mm; engine {eng.sum():.0f} (range {lo:.0f}-{hi:.0f}) vs OpenET {clim[ok].sum():.0f} mm")
        info(f"{preset} per-month engine-OpenET (mm): " + ", ".join(f"{i+1}:{x:+.0f}" for i, x in zip(np.where(ok)[0], diff)))
    if ci is None: skip(f"{preset} CIMIS not fetched (BLOCKED: no CIMIS_APP_KEY)")
    else:
        for st, g in ci.groupby("station"):
            v = g["eto_mm"].dropna(); line(v.min() >= 0 and v.max() <= 15, f"{preset} CIMIS stn {st} ETo range {v.min():.2f}-{v.max():.2f} mm/day (0-15)")
            dd = pd.read_parquet(ROOT / "backend/regional/out" / preset / "daily_derived.parquet")[["date", "eto_hargreaves_mm"]]
            m = g.assign(date=pd.to_datetime(g["date"])).merge(dd.assign(date=pd.to_datetime(dd["date"])), on="date").dropna(subset=["eto_mm", "eto_hargreaves_mm"])
            if len(m) < 100: line(False, f"{preset} stn {st}: only {len(m)} overlap days"); continue
            mon = m.groupby(m.date.dt.to_period("M"))[["eto_mm", "eto_hargreaves_mm"]].sum()
            bias_pct = (mon.eto_hargreaves_mm.sum() - mon.eto_mm.sum()) / mon.eto_mm.sum() * 100
            rm = math.sqrt(((mon.eto_hargreaves_mm - mon.eto_mm) ** 2).mean())
            dr = math.sqrt(((m.eto_hargreaves_mm - m.eto_mm) ** 2).mean())
            line(True, f"{preset} stn {st} Hargreaves(POWER) vs CIMIS ETo, {m.date.min().date()}..{m.date.max().date()}, n={len(m)} d: bias {bias_pct:+.1f}%, monthly RMSE {rm:.1f} mm/month, daily RMSE {dr:.2f} mm/day (reported, no target)")
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAIL'}")
sys.exit(1 if fails else 0)
