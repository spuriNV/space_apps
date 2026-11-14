"""Baseline ETc vs OpenET: bias decomposition (ETo source, Kc/calendar, comparison method).

Run from backend/engine:  uv run python checks/validate_et.py
Needs: data/cache/<id>/{power,ncei,openet}.parquet, backend/field/out/<id>/crop_history.json and, for the gridMET
row, backend/engine/.cache/<id>/gridmet_eto.parquet (checks/fetch_gridmet_eto.py, 1 OpenET query per preset).

OpenET is an INDEPENDENT check: nothing here feeds a coefficient back into the engine. The engine's ETo and Kc
come from FAO-56 and NASA POWER only; this script only reports how far apart the two are and why.
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
import pandas as pd

from rotation_engine.engine import load_crops, load_strategies
from rotation_engine.timeline import build_timeline
from rotation_engine.weather import CHUNK, DEFAULT_ETO, ETO_METHODS, PRESETS, REPO, eto_series, load_weather

BASE_CDL = {"car_colusa_rice": "Rice", "caf_tulare_forage": "Alfalfa"}
OLD_YEARS = range(2015, 2026)          # engine default weather years
OLD_OE_YEARS = range(2019, 2025)       # what backend/ground/checks compares against
DAYS = pd.date_range("2001-01-01", "2001-12-31")


def _no_leap(s: pd.Series) -> pd.Series:
    return s[~((s.index.month == 2) & (s.index.day == 29))]


def daily_eto(preset: str) -> dict[str, pd.Series]:
    w = load_weather(preset)
    df = _no_leap(w.df.loc["2015-01-01":"2025-12-31"])
    out = {}
    for m in ETO_METHODS:
        parts = [pd.Series(eto_series(w, df.loc[str(y)], m), df.loc[str(y)].index) for y in range(2015, 2026)]
        out[m] = pd.concat(parts)
    return out


def monthly(s: pd.Series) -> pd.Series:
    return s.groupby([s.index.year, s.index.month]).sum()


def kc_daily(preset: str, shift_rice_days: int = 0) -> np.ndarray:
    base = next(s for s in load_strategies(preset) if s["is_baseline"])
    if shift_rice_days:  # sensitivity only: move the spring flood + rice season later
        for e in base["calendar"]:
            if e["crop_id"] in ("rice_medium_grain",) or e["plant"] == "04-25":
                for k in ("plant", "harvest", "flooded_until"):
                    if k in e:
                        d = pd.Timestamp("2001-" + e[k]) + pd.Timedelta(days=shift_rice_days)
                        e[k] = d.strftime("%m-%d")
    return build_timeline(base, load_crops()).kc["value"][:365]


def etc_monthly(kc: np.ndarray, eto: pd.Series, years) -> pd.Series:
    """Monthly ETc (year, month) with the 365-day Kc applied to each calendar year's ETo."""
    parts = []
    for y in years:
        e = eto.loc[str(y)]
        parts.append(pd.Series(kc[: len(e)] * e.values, e.index))
    return monthly(pd.concat(parts))


def clim(m: pd.Series, years) -> np.ndarray:
    m = m[m.index.get_level_values(0).isin(list(years))]
    return m.groupby(level=1).mean().reindex(range(1, 13)).to_numpy()


def stats(eng: np.ndarray, obs: np.ndarray) -> tuple[float, float, float, float]:
    d = eng - obs
    return eng.sum(), obs.sum(), d.sum() / obs.sum() * 100, math.sqrt((d ** 2).mean())


def run(preset: str) -> dict:
    hist = json.loads((REPO / "backend/field/out" / preset / "crop_history.json").read_text())["by_year"]
    oe = pd.read_parquet(REPO / "data/cache" / preset / "openet.parquet")
    oe = oe[oe.model == "Ensemble"]
    oe = pd.Series(oe.et_mm.values, pd.to_datetime(oe.date))
    oe_m = oe.groupby([oe.index.year, oe.index.month]).sum()
    matched = [y for y in range(2016, 2026) if hist.get(str(y)) == BASE_CDL[preset]]
    other = [y for y in range(2016, 2026) if y not in matched]
    etos = daily_eto(preset)
    gp = CHUNK / ".cache" / preset / "gridmet_eto.parquet"
    grid_m = None
    if gp.exists():
        g = pd.read_parquet(gp); g = pd.Series(g.eto_mm.values, pd.to_datetime(g.date))
        grid_m = g.groupby([g.index.year, g.index.month]).sum()
    kc = kc_daily(preset)
    rows = []

    def add(label, eng_m, eng_years, oe_years):
        e, o, b, r = stats(clim(eng_m, eng_years), clim(oe_m, oe_years))
        rows.append((label, e, o, b, r))

    old = etc_monthly(kc, etos["harg_power"], OLD_YEARS)
    add("A. as before: Harg-POWER, engine 2015-25 vs OpenET 2019-24 (all crops)", old, OLD_YEARS, OLD_OE_YEARS)
    add("B. same ETo, both on CDL-matched years", etc_monthly(kc, etos["harg_power"], matched), matched, matched)
    for k, lab in (("harg_station", "C1. Hargreaves on NOAA station Tmax/Tmin"),
                   ("pm_power", "C2. Penman-Monteith (FAO-56 eq. 6), all POWER"),
                   ("pm_station_t", "C3. PM, station Tmax/Tmin + POWER Rs/RH/wind (new default)")):
        add(lab + ", matched years", etc_monthly(kc, etos[k], matched), matched, matched)
    if grid_m is not None:
        # gridMET is monthly: spread Kc as the monthly mean Kc
        kcm = pd.Series(kc, DAYS).groupby(DAYS.month).mean()
        gm = grid_m * np.array([kcm[m] for m in grid_m.index.get_level_values(1)])
        add("C4. gridMET ETo (OpenET's own reference), matched years", gm, matched, matched)
    new = etc_monthly(kc, etos[DEFAULT_ETO], matched)
    diff = clim(new, matched) - clim(oe_m, matched)
    season = {"Nov-Apr": float(diff[[10, 11, 0, 1, 2, 3]].sum()), "May-Oct": float(diff[4:10].sum())}
    if preset == "car_colusa_rice":
        add("D. sensitivity: spring flood + rice 10 d later (observed flood onset ~mid-May), C3 ETo",
            etc_monthly(kc_daily(preset, 10), etos[DEFAULT_ETO], matched), matched, matched)
    # ETo annual means, matched years
    eto_tab = {k: float(np.nanmean([v.loc[str(y)].sum() for y in matched])) for k, v in etos.items()}
    if grid_m is not None:
        eto_tab["gridmet"] = float(np.mean([grid_m.loc[y].sum() for y in matched]))
    # implied Kc (OpenET ET / gridMET ETo) vs engine monthly mean Kc, matched years
    kc_tab = None
    if grid_m is not None:
        kcm = pd.Series(kc, DAYS).groupby(DAYS.month).mean()
        imp = clim(oe_m, matched) / clim(grid_m, matched)
        kc_tab = [(m, float(kcm[m]), float(imp[m - 1])) for m in range(1, 13)]
    nonmatch = clim(oe_m, other).sum() if other else None
    return {"rows": rows, "matched": matched, "other": other, "eto": eto_tab, "kc": kc_tab,
            "openet_other_years_mm": nonmatch, "diff_new": diff, "season": season, "openet_matched_monthly": clim(oe_m, matched)}


def main():
    for p in PRESETS:
        r = run(p)
        print(f"\n== {p}  (CDL-matched years {r['matched']}; other years {r['other']}, OpenET there "
              f"{r['openet_other_years_mm']:.0f} mm/yr)")
        print("ETo annual mean, matched years (mm): " + ", ".join(f"{k} {v:.0f}" for k, v in r["eto"].items()))
        print(f"{'step':86s} {'engine':>7s} {'OpenET':>7s} {'bias%':>7s} {'RMSE':>6s}")
        for lab, e, o, b, rm in r["rows"]:
            print(f"{lab:86s} {e:7.0f} {o:7.0f} {b:+7.1f} {rm:6.1f}")
        print("new default, engine - OpenET by month (mm): " + ", ".join(f"{i + 1}:{x:+.0f}" for i, x in enumerate(r["diff_new"]))
              + "  | season sums: " + ", ".join(f"{k} {v:+.0f}" for k, v in r["season"].items()))
        if r["kc"]:
            print("month: engine mean Kc | OpenET ET / gridMET ETo (implied Kc, matched years)")
            print("  " + "  ".join(f"{m}:{a:.2f}|{b:.2f}" for m, a, b in r["kc"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
