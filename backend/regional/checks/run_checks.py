"""Prints PASS/FAIL/SKIP lines for the regional-data chunk. Thresholds come from the spec; none are tuned to pass.
Run: cd backend/regional && uv run python checks/run_checks.py"""
import sys, json
from pathlib import Path
import pandas as pd, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common import CACHE, OUT, PRESETS
from derive import hargreaves_eto

res = []
def rep(ok, name, detail=""):
    res.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  | {detail}" if detail else ""))
def info(name, detail): print(f"INFO  {name}  | {detail}")
def skip(name, why): print(f"SKIP  {name}  | {why}")

def load(pid, name, **kw):
    p = CACHE / pid / name
    return pd.read_parquet(p) if p.exists() else None

for pid, pr in PRESETS.items():
    print(f"\n== {pid} ==")
    pw = load(pid, "power.parquet")
    if pw is None: rep(False, "power.parquet exists"); continue
    pw = pw.set_index("date")
    meta = json.loads((CACHE / pid / "power.meta.json").read_text())

    # 1. ranges / units
    rng = {"T2M": (-30, 50), "T2M_MAX": (-30, 55), "T2M_MIN": (-40, 45), "RH2M": (0, 100), "WS2M": (0, 40), "ALLSKY_SFC_SW_DWN": (0, 40), "PRECTOTCORR": (0, 500)}
    bad = [c for c, (lo, hi) in rng.items() if not pw[c].dropna().between(lo, hi).all()]
    rep(not bad, "POWER values within physical ranges", f"out of range: {bad}" if bad else "")
    rep(meta["units"]["PRECTOTCORR"] == "mm/day" and meta["units"]["T2M"] == "C" and meta["units"]["ALLSKY_SFC_SW_DWN"].startswith("MJ"), "POWER units mm/day, C, MJ/m^2/day", str(meta["units"]))
    rep(bool((pw.T2M_MAX >= pw.T2M_MIN).all()), "POWER Tmax >= Tmin every day")
    # 2. rows / coverage
    # POWER now runs from 1981-01-01 through the latest published day (a few days behind today), with no gaps
    exp = pd.date_range("1981-01-01", pw.index.max())
    rep(len(pw) == len(exp) and pw.index.equals(exp) and pw.index.max() >= pd.Timestamp("2026-01-01"),
        f"POWER row count and daily coverage 1981-01-01..{pw.index.max().date()} (no gaps, includes 2026)", f"{len(pw)} rows vs {len(exp)} expected")
    # 3. fill values
    rep(not (pw == -999).any().any(), "POWER fill value -999 replaced by NaN", f"NaN counts: { {k:int(v) for k,v in pw.isna().sum().items() if v} }")
    na_other = int(pw.drop(columns="ALLSKY_SFC_SW_DWN").isna().sum().sum())
    rep(na_other == 0, "No missing values outside ALLSKY (which has no data before 1984)")
    d = load(pid, "../../../backend/regional/out/%s/daily_derived.parquet" % pid) if False else pd.read_parquet(OUT / pid / "daily_derived.parquet").set_index("date")
    rep(d.eto_hargreaves_mm.between(0, 15).all() and d.eto_hargreaves_mm.notna().all(), "Hargreaves ETo 0-15 mm/day, no NaN", f"max {d.eto_hargreaves_mm.max():.2f}")
    # 4. Jan-Mar 2023 rank
    p = pw.PRECTOTCORR[pw.index.year <= 2025]   # 2026 is a partial year; rank stays on 1981-2025
    jm = p[p.index.month <= 3].groupby(p[p.index.month <= 3].index.year).sum().sort_values(ascending=False)
    rank = list(jm.index).index(2023) + 1
    info("Jan-Mar precip by year (top 5)", ", ".join(f"{y}:{v:.0f}mm" for y, v in jm.head(5).items()) + f"; 2023 = {jm[2023]:.0f} mm")
    rep(rank <= 3, "Jan-Mar 2023 precipitation is top-3 of 1981-2025 (POWER)", f"rank {rank} of {len(jm)}")
    # NCEI cross check
    nc = load(pid, "ncei.parquet")
    if nc is not None and len(nc):
        for s, g in nc.groupby("station"):
            g = g.set_index("date").prcp_mm; q1 = g[g.index.month <= 3]
            yy = q1.groupby(q1.index.year).agg(["sum", "count"]); yy = yy[yy["count"] >= 80].sort_values("sum", ascending=False)
            if 2023 in yy.index: info(f"NCEI {s} Jan-Mar 2023 rank", f"{list(yy.index).index(2023)+1} of {len(yy)} complete years ({yy.loc[2023,'sum']:.0f} mm)")
    else: skip("NCEI Jan-Mar 2023 rank", "ncei.parquet missing/empty")
    # 5. water years
    wy = p.groupby(np.where(p.index.month >= 10, p.index.year + 1, p.index.year)).sum()
    wy = wy[(wy.index >= 1982) & (wy.index <= 2025)]
    clim = wy.mean(); med = wy.median()
    for y in (2021, 2022):
        pct = 100 * wy[y] / clim; r = int((wy < wy[y]).sum()) + 1
        rep(wy[y] < clim, f"WY{y} precipitation below 1982-2025 mean (POWER)", f"{wy[y]:.0f} mm = {pct:.0f}% of mean {clim:.0f} mm (median {med:.0f}); rank {r} driest of {len(wy)}")
    info("WY2023", f"{wy[2023]:.0f} mm = {100*wy[2023]/clim:.0f}% of mean")
    # 6. +2 C raises ETo
    ra_doy = d.index.day_of_year.values
    base = hargreaves_eto(pw.T2M_MAX, pw.T2M_MIN, pr["lat"], ra_doy); warm = hargreaves_eto(pw.T2M_MAX + 2, pw.T2M_MIN + 2, pr["lat"], ra_doy)
    rep(float(warm.sum()) > float(base.sum()) and bool((warm >= base).all()), "+2 C raises Hargreaves ETo", f"annual {base.sum()/45:.0f} -> {warm.sum()/45:.0f} mm (+{100*(warm.sum()/base.sum()-1):.1f}%)")
    # sanity: seasonal ETo shape
    mo = d.eto_hargreaves_mm.groupby(d.index.month).sum() / 45
    rep(mo.idxmax() in (6, 7, 8) and mo.idxmin() in (12, 1), "ETo peaks Jun-Aug, lowest Dec-Jan", f"peak month {mo.idxmax()} ({mo.max():.0f} mm), low month {mo.idxmin()} ({mo.min():.0f} mm)")

    # USDM
    us = load(pid, "usdm.parquet")
    if us is None: skip("USDM D3+ weeks 2021-22", "usdm.parquet missing")
    else:
        cum = us[us.stat == "cumulative"]
        for fips, g in cum.groupby("fips"):
            g = g.set_index("map_date")
            n = int(((g.d3 > 0) & (g.index.year.isin([2021, 2022]))).sum()); nw = int(g.index.year.isin([2021, 2022]).sum())
            full = int(((g.d3 >= 50) & (g.index.year.isin([2021, 2022]))).sum())
            rep(n > 0, f"USDM {fips} {g.county.iloc[0]} has D3+ weeks in 2021-22", f"{n} of {nw} weeks with any D3+ area; {full} weeks with >=50% of county in D3+")
        rep(cum.groupby("fips").size().min() >= 570, "USDM weekly rows ~575 per county (2015-2025)", str(cum.groupby("fips").size().to_dict()))
    # CDEC
    cd = load(pid, "cdec.parquet")
    if cd is None: skip("Reservoir storage", "cdec.parquet missing")
    else:
        cd = cd.set_index("date")
        stns = ["SHA", "ORO"] if pid.startswith("car") else ["PNF"]
        rep(all((cd.station == s).sum() == 4018 for s in ["SHA", "ORO", "PNF"]), "CDEC 4018 daily rows per station 2015-2025", f"missing values: {cd.storage_af.isna().sum()}")
        for s in stns:
            x = cd[cd.station == s].storage_af
            def sub(a, b): return x[a:b].mean()
            # 'low in 2021-22 vs 2023': mean storage over Jun-Oct (end of irrigation season) and annual mean
            lo = x["2021-01-01":"2022-12-31"].mean(); hi23 = x["2023-01-01":"2023-12-31"].mean()
            m21 = x["2021-09-01":"2021-09-30"].mean(); m22 = x["2022-09-01":"2022-09-30"].mean(); m23 = x["2023-09-01":"2023-09-30"].mean()
            clim = x["2015-01-01":"2025-12-31"].mean()
            rep(lo < hi23, f"{s} storage lower in 2021-22 than in 2023", f"mean 2021-22 {lo:,.0f} AF vs 2023 {hi23:,.0f} AF; Sept: 2021 {m21:,.0f}, 2022 {m22:,.0f}, 2023 {m23:,.0f}; 2015-25 mean {clim:,.0f}")
    # NCEI
    if nc is not None and len(nc):
        rep(True, "NCEI stations present", ", ".join(f"{s}:{(nc.station==s).sum()} rows" for s in nc.station.unique()))
    # soil
    sj = CACHE / pid / "soil.json"
    if sj.exists():
        s = json.loads(sj.read_text())
        rep(20 <= s["awc_mm_per_m"]["value"] <= 250 and 0 <= s["om_pct"]["value"] <= 30 and s["hydrologic_group"] in list("ABCD") + ["A/D", "B/D", "C/D"], "SSURGO soil block in range", f"{s['muname']} | {s['drainage_class']} | HSG {s['hydrologic_group']} | AWC {s['awc_mm_per_m']['value']} mm/m | OM {s['om_pct']['value']}%")
    else: skip("SSURGO", "soil.json missing")

print(f"\n{sum(res)} PASS / {len(res)-sum(res)} FAIL")
