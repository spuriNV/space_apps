"""Validation of cached NASA keyed datasets (spec B10.1 check 2, coverage, expectations). Reports, never tunes.
Run: uv run python checks/run_checks.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parents[3] / "data" / "cache"
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]
n_fail = 0


def out(ok, msg):
    global n_fail
    tag = "PASS" if ok is True else "FAIL" if ok is False else "INFO"
    n_fail += ok is False
    print(f"{tag}  {msg}")


def load(p, ds):
    f = CACHE / p / f"{ds}.parquet"
    return pd.read_parquet(f) if f.exists() else None


def rng(p, ds, df, col, lo, hi, unit):
    s = df[col].dropna()
    if s.empty:
        return out(False, f"{p}/{ds}.{col}: all NaN")
    bad = ((s < lo) | (s > hi)).sum()
    out(bool(bad == 0), f"{p}/{ds}.{col} range {s.min():.4g}..{s.max():.4g} {unit} (allowed {lo}..{hi}; {bad} outside)")


def cover(p, ds, df, tcol="date"):
    t = pd.to_datetime(df[tcol])
    out(None, f"{p}/{ds} coverage {t.min().date()}..{t.max().date()}, {len(df)} rows, {df.select_dtypes('number').isna().mean().mean():.1%} numeric NaN")


def month_pct(df, col, years):
    """Percentile (0-100) of each calendar month's mean vs the same calendar month in all other years (empirical rank)."""
    m = df.set_index("date")[col].resample("MS").mean().dropna()
    res = {}
    for ts, v in m.items():
        if ts.year in years:
            peers = m[m.index.month == ts.month]
            res[ts] = 100 * (peers < v).sum() / max(len(peers) - 1, 1)
    return pd.Series(res)


for p in PRESETS:
    print(f"\n== {p}")
    any_data = False
    d = load(p, "imerg")
    if d is not None:
        any_data = True
        cover(p, "imerg", d)
        rng(p, "imerg", d, "precipitation", 0, 500, "mm/day")
        d = d.dropna(subset=["precipitation"])
        jm = d[d.date.dt.month.isin([1, 2, 3])].groupby(d.date.dt.year)["precipitation"].sum()
        full = jm[d.groupby(d.date.dt.year)["precipitation"].count().reindex(jm.index) > 300]  # years with data
        if 2023 in jm.index and len(jm) > 1:
            rank = int((jm > jm[2023]).sum()) + 1
            out(rank <= 3, f"{p}/imerg Jan-Mar 2023 total {jm[2023]:.0f} mm ranks {rank} of {len(jm)} years {jm.index.min()}-{jm.index.max()} (spec expects top 3)")
        else:
            out(None, f"{p}/imerg Jan-Mar 2023 not in cache; cannot rank")
        w22 = d[(d.date >= "2021-10-01") & (d.date <= "2022-03-31")].precipitation.sum()
        wall = d.groupby(np.where(d.date.dt.month >= 10, d.date.dt.year, d.date.dt.year - 1))["precipitation"].apply(
            lambda s: s.sum() if len(s) > 170 else np.nan).dropna()
        out(None, f"{p}/imerg Oct 2021-Mar 2022 = {w22:.0f} mm; median full Oct-Mar season in cache = {wall.median():.0f} mm (spec: 2022 winter below climatology)")
    d = load(p, "smap_l3")
    if d is not None:
        any_data = True
        cover(p, "smap_l3", d)
        rng(p, "smap_l3", d, "sm_valid", 0.02, 0.6, "m3/m3")
        pc = month_pct(d.assign(date=pd.to_datetime(d.date)), "sm_valid", {2021, 2022})
        out(None, f"{p}/smap_l3 valid retrievals {d.sm_valid.notna().mean():.0%} of days")
        if len(pc):
            out(bool((pc < 30).mean() >= 0.5) , f"{p}/smap_l3 2021-22 monthly percentile (same-month rank, 2015+): mean {pc.mean():.0f}, {int((pc<30).sum())}/{len(pc)} months < 30")
    d = load(p, "smap_l4")
    if d is not None:
        any_data = True
        cover(p, "smap_l4", d)
        rng(p, "smap_l4", d, "sm_rootzone", 0.0, 0.9, "m3/m3")
        rng(p, "smap_l4", d, "sm_surface", 0.0, 0.9, "m3/m3")
        if "sm_rootzone_pctl" in d:
            s = d[(d.date >= "2021-01-01") & (d.date <= "2022-12-31")].sm_rootzone_pctl.dropna()
            if len(s):
                out(s.mean() < 30, f"{p}/smap_l4 2021-22 sm_rootzone_pctl mean {s.mean():.0f}, {(s<30).mean():.0%} of values < 30")
    d = load(p, "grace")
    if d is not None:
        any_data = True
        cover(p, "grace", d)
        for c in ["gws_inst", "rtzsm_inst", "sfsm_inst"]:
            rng(p, "grace", d, c, 0, 100, "percentile")
        s = d[(d.date >= "2021-01-01") & (d.date <= "2022-12-31")].gws_inst.dropna()
        if len(s):
            out(s.mean() < 30, f"{p}/grace 2021-22 groundwater percentile mean {s.mean():.0f}, {(s<30).mean():.0%} of weeks < 30 (spec: below 30)")
        gaps = pd.to_datetime(d.date).diff().dt.days
        out(None, f"{p}/grace largest gap {int(gaps.max())} days (expected ~11 months across GRACE/GRACE-FO gap 2017-18)")
    d = load(p, "modis")
    if d is not None:
        any_data = True
        cover(p, "modis", d)
        rng(p, "modis", d, "NDVI", -1, 1, "NDVI")
        out(None, f"{p}/modis good-reliability share {d.ndvi_good.notna().mean():.0%}")
    d = load(p, "ecostress")
    if d is not None:
        any_data = True
        cover(p, "ecostress", d)
        if "LST" in d:
            rng(p, "ecostress", d, "LST", 250, 340, "K")
        if "ESI" in d:
            rng(p, "ecostress", d, "ESI", 0, 1.5, "ratio")
        if "ETdaily" in d:
            rng(p, "ecostress", d, "ETdaily", 0, 400, "W/m2")
    d = load(p, "dswx")
    if d is not None:
        any_data = True
        cover(p, "dswx", d, "datetime")
        if len(d):
            rng(p, "dswx", d, "frac_water", 0, 1, "fraction")
            d["datetime"] = pd.to_datetime(d["datetime"])
            clear = d[d.frac_clear >= 0.8]
            if p == "car_colusa_rice":
                w = clear[clear.datetime.dt.month.isin([12, 1, 2])]
                out(bool(len(w) and w.frac_water.max() > 0.1),
                    f"{p}/dswx winter (Dec-Feb) clear scenes {len(w)}; max frac_water {w.frac_water.max() if len(w) else float('nan'):.2f}, mean {w.frac_water.mean() if len(w) else float('nan'):.2f} (spec: water on Colusa in winter)")
            else:
                out(None, f"{p}/dswx spring 2023 clear scenes {len(clear)}; max frac_water {clear.frac_water.max() if len(clear) else float('nan'):.2f} (spec: flag if inside 2023 water extent)")
        else:
            out(False, f"{p}/dswx cached but empty (no scenes intersected polygon)")
    if not any_data:
        print("NOT CACHED: no keyed NASA datasets yet (BLOCKED: no Earthdata credentials; run check_auth.py then the fetch_*.py scripts)")
print(f"\n{n_fail} FAIL line(s)")
sys.exit(1 if n_fail else 0)
