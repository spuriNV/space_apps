"""Rule-based bare / partial / covered / water detector (spec B5.1) -> out/<preset>/calendar.json.

Observations: field-median values from data/cache/<preset>/s2.parquet and landsat.parquet
(scenes with clear_frac >= MIN_CLEAR and >= MIN_PIXELS clear pixels). If Sentinel-2 and
Landsat both have a usable scene on the same date, the Sentinel-2 row is used.

Per observation class
  water    : NDWI median > 0.3, or > 50% of clear pixels flagged water (S2 SCL 6 / Landsat QA bit 7)
  bare     : NDVI median < 0.20
  partial  : 0.20 <= NDVI median <= 0.35
  covered  : NDVI median > 0.35
Daily fill: a day between two observations at most 30 days apart gets the class of the
linearly interpolated NDVI (or the nearer observation's class if either is water); a day
inside a longer gap is "unknown".
Markers (on the observation sequence, only across gaps <= 30 days):
  green_up            : first of 3 consecutive observations with NDVI > 0.35, following one <= 0.35
  senescence_harvest  : first of 2 consecutive observations each more than 0.2 below the
                        maximum NDVI of the preceding 30 days (that window includes itself)
Thresholds are the spec's rule of thumb (U), not tuned to this field.

Usage: uv run python -m fieldshift_field.detector [preset ...]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from .common import PRESETS, cache, now, out, today, write_json

MIN_CLEAR = 0.5
MIN_PIXELS = 20
BARE, COVER = 0.20, 0.35
NDWI_WATER, WATER_FRAC = 0.3, 0.5
MAX_GAP = 30
GREENUP_N, DROP, DROP_N, DROP_WIN = 3, 0.2, 2, 30
YEARS = range(2016, 2026)

CLASSES = {
    "unknown": {"label": "No clear observation within 30 days", "color": "#bdbdbd", "pattern": "hatched"},
    "bare": {"label": f"Bare (NDVI < {BARE})", "color": "#8c6d46"},
    "partial": {"label": f"Partial cover ({BARE}-{COVER})", "color": "#b8d98b"},
    "covered": {"label": f"Covered (NDVI > {COVER})", "color": "#2e7d32"},
    "water": {"label": "Water (NDWI > 0.3 or water mask)", "color": "#2b7bba"},
}


def load_obs(preset: str) -> pd.DataFrame:
    frames = []
    for src in ("s2", "landsat"):
        p = cache(preset) / f"{src}.parquet"
        if p.exists():
            d = pd.read_parquet(p)
            d["sensor"] = src if src == "landsat" else "s2"
            frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d = d[(d.clear_frac >= MIN_CLEAR) & (d.n_valid >= MIN_PIXELS) & d.ndvi_med.notna()].copy()
    d["date"] = pd.to_datetime(d["date"])
    d["prio"] = (d.sensor != "s2").astype(int)
    d = d.sort_values(["date", "prio", "n_valid"], ascending=[True, True, False]).drop_duplicates("date")
    d["is_water"] = (d.ndwi_med > NDWI_WATER) | (d.water_frac.fillna(0) > WATER_FRAC)
    d["cls"] = np.where(d.is_water, "water", np.where(d.ndvi_med < BARE, "bare",
                                                      np.where(d.ndvi_med <= COVER, "partial", "covered")))
    return d.reset_index(drop=True)


def ndvi_class(v):
    return "bare" if v < BARE else ("partial" if v <= COVER else "covered")


def daily(d: pd.DataFrame, start, end) -> pd.Series:
    days = pd.date_range(start, end, freq="D")
    t = d["date"].values.astype("datetime64[D]")
    nd, cl = d["ndvi_med"].values, d["cls"].values
    res = []
    for day in days.values.astype("datetime64[D]"):
        i = np.searchsorted(t, day, side="right") - 1  # last obs <= day
        if i >= 0 and t[i] == day:
            res.append(cl[i]); continue
        if i < 0 or i + 1 >= len(t):
            res.append("unknown"); continue
        gap = int((t[i + 1] - t[i]).astype(int))
        if gap > MAX_GAP:
            res.append("unknown"); continue
        a = int((day - t[i]).astype(int))
        if cl[i] == "water" or cl[i + 1] == "water":
            res.append(cl[i] if a <= gap - a else cl[i + 1])
        else:
            res.append(ndvi_class(nd[i] + (nd[i + 1] - nd[i]) * a / gap))
    return pd.Series(res, index=days)


def markers(d: pd.DataFrame):
    t, v = d["date"].tolist(), d["ndvi_med"].tolist()
    gap_ok = lambda i, j: all((t[k + 1] - t[k]).days <= MAX_GAP for k in range(i, j))
    out_ = []
    for i in range(1, len(v) - GREENUP_N + 1):
        if v[i - 1] <= COVER and all(x > COVER for x in v[i:i + GREENUP_N]) and gap_ok(i - 1, i + GREENUP_N - 1):
            out_.append({"date": t[i].strftime("%Y-%m-%d"), "type": "green_up", "ndvi": round(v[i], 3)})
    win_max = [max(v[j] for j in range(len(v)) if 0 <= (t[i] - t[j]).days <= DROP_WIN) for i in range(len(v))]
    dropped = [v[i] < win_max[i] - DROP for i in range(len(v))]
    for i in range(len(v) - DROP_N + 1):
        if all(dropped[i:i + DROP_N]) and (i == 0 or not dropped[i - 1]) and gap_ok(i, i + DROP_N - 1):
            out_.append({"date": t[i].strftime("%Y-%m-%d"), "type": "senescence_harvest", "ndvi": round(v[i], 3),
                         "from_30d_max": round(win_max[i], 3)})
    return sorted(out_, key=lambda m: m["date"])


def segments(s: pd.Series, obs_dates):
    segs = []
    for cls, grp in s.groupby((s != s.shift()).cumsum()):
        c = grp.iloc[0]
        a, b = grp.index[0], grp.index[-1]
        segs.append({"start": a.strftime("%Y-%m-%d"), "end": b.strftime("%Y-%m-%d"),
                     "start_doy": int(a.day_of_year), "end_doy": int(b.day_of_year), "days": len(grp), "class": c,
                     "n_obs": int(sum(a <= x <= b for x in obs_dates))})
    return segs


def transitions(segs):
    tr, last = [], None
    for sg in segs:
        if sg["class"] == "unknown":
            continue
        if last is not None and sg["class"] != last["class"]:
            tr.append({"date": sg["start"], "from": last["class"], "to": sg["class"],
                       "after_unknown_gap": last["end"] != (pd.Timestamp(sg["start"]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")})
        last = sg
    return tr


def build(preset: str):
    d = load_obs(preset)
    full = daily(d, "2015-07-01", "2025-12-31")
    marks = markers(d)
    years = []
    for y in YEARS:
        s = full[str(y)]
        dy = d[d.date.dt.year == y]
        segs = segments(s, list(dy.date))
        counts = s.value_counts().to_dict()
        years.append({
            "year": y,
            "segments": segs,
            "transitions": transitions(segs),
            "markers": [m for m in marks if m["date"].startswith(str(y))],
            "summary": {"days_by_class": {k: int(counts.get(k, 0)) for k in CLASSES},
                        "n_obs": int(len(dy)), "n_obs_s2": int((dy.sensor == "s2").sum()),
                        "n_obs_landsat": int((dy.sensor == "landsat").sum())},
            "observations": [{"date": r.date.strftime("%Y-%m-%d"), "sensor": r.sensor,
                              "ndvi": round(float(r.ndvi_med), 3), "ndwi": round(float(r.ndwi_med), 3),
                              "bsi": round(float(r.bsi_med), 3), "clear_frac": round(float(r.clear_frac), 2),
                              "class": r.cls} for r in dy.itertuples()],
        })
    doc = {
        "preset_id": preset, "generated_at": now(), "detector": "rule_ndvi",
        "classes": CLASSES,
        "method": {"bare_lt": BARE, "covered_gt": COVER, "water": f"NDWI > {NDWI_WATER} or water mask > {WATER_FRAC}",
                   "max_interp_gap_days": MAX_GAP, "min_clear_frac": MIN_CLEAR, "min_clear_pixels": MIN_PIXELS,
                   "green_up": f"{GREENUP_N} consecutive obs NDVI > {COVER}",
                   "senescence_harvest": f"{DROP_N} consecutive obs > {DROP} below {DROP_WIN}-day max",
                   "same_day_priority": "Sentinel-2 over Landsat",
                   "thresholds_status": "U rule of thumb (spec B5.1), not tuned"},
        "sources": [
            {"id": "s2_l2a_mpc", "title": "Sentinel-2 L2A (Microsoft Planetary Computer)",
             "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", "accessed": today(), "verified": True},
            {"id": "landsat_c2_l2_mpc", "title": "Landsat Collection 2 Level-2 (Microsoft Planetary Computer)",
             "url": "https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2", "accessed": today(), "verified": True},
            {"id": "usgs_ndvi_phenology", "title": "USGS NDVI, the foundation for remote sensing phenology",
             "url": "https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology",
             "accessed": today(), "verified": False}],
        "years": years,
    }
    write_json(out(preset) / "calendar.json", doc)
    print(preset)
    for y in years:
        print(f"  {y['year']}: obs {y['summary']['n_obs']:3d} (s2 {y['summary']['n_obs_s2']}, ls {y['summary']['n_obs_landsat']}) "
              f"days {y['summary']['days_by_class']}  markers {len(y['markers'])}")
    return doc


if __name__ == "__main__":
    for p in (sys.argv[1:] or list(PRESETS)):
        build(p)
