"""Item 6 (bare window + heavy-rain chance, conditional climatology) and scenario shifts for item 7.
Conditional climatology, NOT a forecast: terciles from 1991-2020 station seasons; weights from the CPC favoured-category probability."""
import datetime as dt, statistics as st
import numpy as np, pandas as pd
from common import *

CURRENT_CROP = {"car_colusa_rice": "Rice", "caf_tulare_forage": "Alfalfa"}
MIN_RUN = 14
SEAS = {"NDJ": (11, 12, 1), "DJF": (12, 1, 2), "JFM": (1, 2, 3), "FMA": (2, 3, 4)}
NCEI_URL = "https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries (cached in data/cache/<id>/ncei.parquet)"

def winter_windows(pid):
    cal = read_json(ROOT / f"backend/field/out/{pid}/calendar.json")
    hist = read_json(ROOT / f"backend/field/out/{pid}/crop_history.json")["by_year"]
    yrs = {y["year"]: y for y in cal["years"]}
    cls = {}
    for y in cal["years"]:
        for s in y["segments"]:
            d0, d1 = dt.date.fromisoformat(s["start"]), dt.date.fromisoformat(s["end"])
            for i in range((d1 - d0).days + 1): cls[d0 + dt.timedelta(i)] = s["class"]
    out = []
    for Y in range(2016, 2025):
        if hist.get(str(Y)) != CURRENT_CROP[pid] or (Y + 1) not in yrs: continue
        d, end, best, run = dt.date(Y, 10, 1), dt.date(Y + 1, 4, 30), None, None
        while d <= end:
            if cls.get(d) == "bare":
                run = (run[0], d) if run else (d, d)
                if best is None or (run[1] - run[0]) > (best[1] - best[0]): best = run
            else: run = None
            d += dt.timedelta(1)
        ok = best is not None and (best[1] - best[0]).days + 1 >= MIN_RUN
        out.append({"winter": f"{Y}-{Y+1}", "Y": Y, "start": str(best[0]) if ok else None, "end": str(best[1]) if ok else None,
                    "days": (best[1] - best[0]).days + 1 if ok else 0})
    return out

def med_date(dates, Ys):
    offs = [(dt.date.fromisoformat(d) - dt.date(Y, 10, 1)).days for d, Y in zip(dates, Ys)]
    m = int(round(st.median(offs))); return dt.date(2026, 10, 1) + dt.timedelta(m)   # 2026 = this winter's start year

def stations(pid):
    d = pd.read_parquet(CACHE / pid / "ncei.parquet"); d["date"] = pd.to_datetime(d.date); return d

def season_stats(d, months_seq, Y, col):
    """season of months starting in calendar year Y (months >=7 in year Y else Y+1)."""
    parts = []
    for m in months_seq:
        yr = Y if m >= 7 else Y + 1
        parts.append(d[(d.date.dt.year == yr) & (d.date.dt.month == m)])
    x = pd.concat(parts); n_exp = sum(pd.Period(f"{Y if m>=7 else Y+1}-{m:02d}").days_in_month for m in months_seq)
    if x[col].notna().sum() < 0.9 * n_exp: return None
    return x[col].sum() if col == "prcp_mm" else x[col].mean()

def terciles(vals_by_Y):
    base = [v for Y, v in vals_by_Y.items() if 1991 <= Y <= 2019 and v is not None]
    return np.percentile(base, [100 / 3, 200 / 3])

def cat_of(v, t): return "below" if v <= t[0] else ("above" if v > t[1] else "near")

def weights(favoured, p):
    if favoured is None: return {"below": 1/3, "near": 1/3, "above": 1/3}
    p = p / 100
    if favoured == "near": return {"near": p, "below": (1 - p) / 2, "above": (1 - p) / 2}
    other = "below" if favoured == "above" else "above"
    return {favoured: p, "near": 1 / 3, other: 2 / 3 - p}

def fav(cat):
    return {"above normal": "above", "below normal": "below", "near normal": "near"}.get(cat)

def main():
    fetched = now(); cpc = read_json(OUT / "cpc.json"); res = {"fetched_at": fetched, "label": "Conditional climatology, not a forecast", "presets": {}}
    for pid in PRESETS:
        d_all = stations(pid); stns = sorted(d_all.station.unique()); cp = cpc["presets"][pid]["seasons"]
        # ---- bare window
        ww = winter_windows(pid); okw = [w for w in ww if w["start"]]
        r = {"current_crop": CURRENT_CROP[pid], "crop_note": "2025 CDL crop assumed again in 2026 (2026 CDL not published)",
             "winters_with_current_crop": [w["winter"] for w in ww], "winters_with_bare_window": len(okw), "per_winter": ww}
        cal_url = f"backend/field/out/{pid}/calendar.json"
        has = len(okw) >= 3
        if not has:
            r["bare_window"] = {"note": f"Only {len(okw)} of {len(ww)} winters with this crop had a bare run of {MIN_RUN}+ days: no typical window can be stated"}
        else:
            s0 = med_date([w["start"] for w in okw], [w["Y"] for w in okw]); e0 = med_date([w["end"] for w in okw], [w["Y"] for w in okw])
            if e0 <= s0: e0 = s0
            r["bare_window"] = {
                "start": sn(None, "date", cal_url, "Median bare-window start", fetched, True, method="computed"),
                "median_start": f"{s0.month:02d}-{s0.day:02d}", "median_end": f"{e0.month:02d}-{e0.day:02d}",
                "median_days": sn(float(st.median([w['days'] for w in okw])), "days", cal_url, "Median length of the longest bare run, winters with the current crop", fetched, True, method="computed",
                                  low=float(min(w['days'] for w in okw)), high=float(max(w['days'] for w in okw)),
                                  note=f"{len(okw)} winters of {len(ww)} with {CURRENT_CROP[pid]} had a run of >= {MIN_RUN} consecutive satellite-class 'bare' days between 1 Oct and 30 Apr (calendar.json classes, rule detector); median of start/end offsets from 1 Oct"),
                "method": "Longest consecutive run of class 'bare' in backend/field calendar.json, 1 Oct to 30 Apr, for winters following a year whose CDL crop equals the current crop (2016-2024 starts; CDL 2025 crop assumed again for 2026)."}
            del r["bare_window"]["start"]
            # ---- rain chance in window
            ev = {}
            win = lambda Y: (dt.date(Y, s0.month, s0.day) if s0.month >= 7 else dt.date(Y + 1, s0.month, s0.day), dt.date(Y, e0.month, e0.day) if e0.month >= 7 else dt.date(Y + 1, e0.month, e0.day))
            ov = {k: len(set(m for m in range(1, 13) if True) & set()) for k in SEAS}
            wm = set(); dd = s0
            while dd <= e0: wm.add(dd.month); dd += dt.timedelta(1)
            best = max(SEAS, key=lambda k: (len(wm & set(SEAS[k])), k == "DJF")); season = best
            crow = next(x for x in cp if x["season"] == season); pc = crow["precipitation"]
            favp, pp = fav(pc["category"]), pc["probability"]["value"]
            per_station = []
            for s in stns:
                d = d_all[d_all.station == s]
                tot = {Y: season_stats(d, SEAS[season], Y, "prcp_mm") for Y in range(1981, 2025)}
                tot = {Y: v for Y, v in tot.items() if v is not None}
                t = terciles(tot); events = {}
                for Y in tot:
                    a, b = win(Y); x = d[(d.date >= str(a)) & (d.date <= str(b))]
                    if x.prcp_mm.notna().sum() < 0.9 * ((b - a).days + 1): continue
                    events[Y] = bool((x.prcp_mm >= 25).any())
                cats = {Y: cat_of(tot[Y], t) for Y in events}
                clim = np.mean(list(events.values()))
                cond = {c: (np.mean([events[Y] for Y in events if cats[Y] == c]) if any(cats[Y] == c for Y in events) else None) for c in ("below", "near", "above")}
                ncat = {c: sum(1 for Y in events if cats[Y] == c) for c in cond}
                w = weights(favp, pp or 0)
                blended = sum(w[c] * cond[c] for c in w) if all(cond[c] is not None for c in w) else None
                full = cond.get(favp) if favp else clim
                per_station.append({"station": s, "n_winters": len(events), "climatology": clim, "by_category": cond, "n_by_category": ncat, "blended": blended, "favoured_category_only": full})
            mean = lambda k: float(np.mean([p[k] for p in per_station if p[k] is not None]))
            clim, bl, fo = mean("climatology"), mean("blended"), mean("favoured_category_only")
            vals = [clim, bl, fo]
            srcurl = "data/cache/%s/ncei.parquet (NOAA GHCN-Daily via NCEI, https://www.ncei.noaa.gov/access/services/data/v1)" % pid
            r["heavy_rain_in_window"] = {
                "threshold_mm": 25, "window": f"{r['bare_window']['median_start']} to {r['bare_window']['median_end']}", "outlook_season_used": season,
                "cpc_precip_category": pc["category"], "cpc_probability_percent": pp,
                "chance_any_day_ge_25mm_climatology": sn(round(100 * clim, 1), "percent of winters", srcurl, "Share of 1981-2024 winters with at least one >= 25 mm day in the window (mean of 3 NOAA stations)", fetched, True, method="computed",
                    low=round(100 * min(p["climatology"] for p in per_station), 1), high=round(100 * max(p["climatology"] for p in per_station), 1), note="low/high = station range"),
                "chance_given_cpc_outlook": sn(round(100 * bl, 1), "percent of winters", srcurl, "Conditional climatology weighted by CPC category probabilities", fetched, True, method="computed",
                    low=round(100 * min(vals), 1), high=round(100 * max(vals), 1),
                    note="Outlook, not a forecast. value = sum over terciles of CPC probability x historical event rate in that tercile; low/high = range of climatology, blended, and favoured-category-only."),
                "method": (f"Terciles of {season} station precipitation totals (1991-2020 base) classify each winter 1981-2024 as below/near/above. Event = any day >= 25 mm inside the window dates. "
                           "CPC weights: favoured category gets CPC's probability; near-normal 33.3%; the opposite category the remainder (the CPC convention for small tilts; our assumption). "
                           "About 13 winters per tercile: noisy. Station gauges, not POWER (POWER rain runs ~50-70% wet)."),
                "per_station": per_station}
        # ---- scenario shifts for item 7
        shifts = {"temperature_c": [], "precip_mm": []}
        def season_shift(var, sn_name):
            row = next(x for x in cp if x["season"] == sn_name)[var]; f = fav(row["category"]); p = row["probability"]["value"]; w = weights(f, p or 0)
            outs = []
            for s in stns:
                d = d_all[d_all.station == s].copy(); d["tmean"] = (d.tmax_c + d.tmin_c) / 2
                col = "tmean" if var == "temperature" else "prcp_mm"
                months = {"NDJ": (11, 12, 1), "FMA": (2, 3, 4), "MJJ": (5, 6, 7), "ASO": (8, 9, 10)}[sn_name]
                tv = {}
                for Y in range(1981, 2025):
                    y0 = Y if months[0] >= 7 or sn_name in ("NDJ",) else Y   # season start year
                    tv[Y] = season_stats_any(d, months, Y, col)
                tv = {Y: v for Y, v in tv.items() if v is not None}; t = terciles(tv); cats = {Y: cat_of(v, t) for Y, v in tv.items()}
                allm = np.mean(list(tv.values()))
                cm = {c: np.mean([tv[Y] for Y in tv if cats[Y] == c]) for c in ("below", "near", "above")}
                outs.append((sum(w[c] * cm[c] for c in w) - allm if f else 0.0, (cm[f] - allm) if f else 0.0))
            return float(np.mean([o[0] for o in outs])), float(np.mean([o[1] for o in outs])), row["category"], p
        T = [season_shift("temperature", s) for s in ("NDJ", "FMA", "MJJ", "ASO")]
        P = [season_shift("precipitation", s) for s in ("NDJ", "FMA")]
        wy = []
        for s in stns:
            d = d_all[d_all.station == s]
            v = [season_stats_any(d, (10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9), Y, "prcp_mm") for Y in range(1981, 2025)]
            wy.append(np.mean([x for x in v if x is not None]))
        annual = float(np.mean(wy))
        dT_mid, dT_hi = float(np.mean([t[0] for t in T])), float(np.mean([t[1] for t in T]))
        dP_mid, dP_hi = 100 * sum(p[0] for p in P) / annual, 100 * sum(p[1] for p in P) / annual
        r["scenario"] = {"method": ("CPC-weighted conditional climatology: for each non-overlapping outlook season (temperature NDJ, FMA, MJJ, ASO; precipitation NDJ, FMA) the shift = sum of CPC probability x (tercile mean - all-year mean) at the 3 NOAA stations, "
                                    "averaged. Temperature shift = mean of the 4 seasons (applied all year). Precip shift = NDJ+FMA mm change / mean water-year total (other months unchanged). "
                                    "Range: climatology (0, 0) to the favoured category fully realised. Outlook scenario, not a forecast."),
                         "seasons_used": {"temperature": [dict(season=s, category=t[2], prob=t[3], shift_c=round(t[0], 2)) for s, t in zip(("NDJ", "FMA", "MJJ", "ASO"), T)],
                                          "precipitation": [dict(season=s, category=t[2], prob=t[3], shift_mm=round(t[0], 1)) for s, t in zip(("NDJ", "FMA"), P)]},
                         "mean_water_year_precip_mm": round(annual, 0),
                         "dT_c": {"low": 0.0, "mid": round(max(-1, min(4, dT_mid)), 2), "high": round(max(-1, min(4, dT_hi)), 2)},
                         "dP_pct": {"low": 0.0, "mid": round(max(-30, min(30, dP_mid)), 1), "high": round(max(-30, min(30, dP_hi)), 1)}}
        res["presets"][pid] = r
        print(pid, len(okw), "/", len(ww), r["scenario"]["dT_c"], r["scenario"]["dP_pct"])
    write_json(OUT / "history.json", res)

def season_stats_any(d, months, Y, col):
    """months in order; those >= the first month's year Y, wrapping into Y+1 when the month number is smaller than the first."""
    parts, n_exp = [], 0
    for m in months:
        yr = Y if m >= months[0] else Y + 1
        if months[0] > 9 and m < 7: yr = Y + 1
        if months[0] <= 9 and False: pass
        parts.append(d[(d.date.dt.year == yr) & (d.date.dt.month == m)]); n_exp += pd.Period(f"{yr}-{m:02d}").days_in_month
    x = pd.concat(parts)
    if x[col].notna().sum() < 0.9 * n_exp: return None
    return float(x[col].sum() if col == "prcp_mm" else x[col].mean())

if __name__ == "__main__":
    main()
