"""Raw per-strategy metrics for one parameter combination (spec B4.1, B4.4, B5.3, B5.4).

All "per year" numbers are averaged over the cycle years and over the weather
years supplied (default 2015-2025; one year for a replay).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .timeline import Timeline

EFFECTIVE_RAIN = 0.8        # spec B4.1 `0.8 P` (U)
DAYS_PER_MONTH = 365 / 12
EXPOSED_COVER = 0.5         # spec B5.4: cover(d) < 0.5 and not water(d)
FROST_C, HEAT_C = 0.0, 35.0  # spec B5.3
FW_MONTHS = (10, 11, 12, 1, 2, 3)  # fall-winter for N scavenging (our reading, U)


@dataclass
class WYear:
    """One weather year as the model consumes it (365 days)."""
    year: int
    tmax: np.ndarray
    tmin: np.ndarray
    eto: np.ndarray
    p: dict          # precip source -> array
    dry: np.ndarray  # bool dry-spell proxy (POWER)


# ------------------------------------------------------------------- water
def water_metrics(tl: Timeline, wys: list[WYear], *, kc_var="value", eto_f=1.0, F=450.0, psrc="power") -> dict:
    N = tl.n_years
    kc = tl.kc[kc_var]
    nonfallow = tl.crop_id != "fallow_bare"
    agg = {"etc_year": 0.0, "etc_season": 0.0, "I": 0.0, "etc_month": np.zeros(12),
           "I_cyear": np.zeros(N), "spans": [dict(etc=0.0, I=0.0, etc_jja=0.0) for _ in tl.spans]}
    used = 0
    for wy in wys:
        if wy.p.get(psrc) is None:
            continue
        used += 1
        eto = np.tile(wy.eto, N) * eto_f
        p = np.tile(wy.p[psrc], N)
        etc = kc * eto
        agg["etc_year"] += etc.sum() / N
        agg["etc_season"] += etc[nonfallow].sum() / N
        agg["etc_month"] += np.bincount(tl.month - 1, weights=etc, minlength=12) / N
        for k, sp in enumerate(tl.spans):
            e_sp = etc[sp.idx]
            jja = np.isin(tl.month[sp.idx], (6, 7, 8))
            agg["spans"][k]["etc"] += e_sp.sum()
            agg["spans"][k]["etc_jja"] += e_sp[jja].sum()
            if not sp.entry.get("irrigated"):
                continue
            # monthly balance inside the season: max(0, ETc - 0.8 P) per (cycle-year, month) segment
            key = tl.cyear[sp.idx] * 12 + (tl.month[sp.idx] - 1)
            uk, inv = np.unique(key, return_inverse=True)
            need = np.maximum(0.0, np.bincount(inv, weights=e_sp) - EFFECTIVE_RAIN * np.bincount(inv, weights=p[sp.idx]))
            i_sp = need.sum()
            np.add.at(agg["I_cyear"], uk // 12, need)
            if sp.crop.get("flood_percolation_mm"):
                i_sp += F
                agg["I_cyear"][sp.entry["year"] - 1] += F
            agg["spans"][k]["I"] += i_sp
            agg["I"] += i_sp / N
    if used == 0:
        return None
    for k in ("etc_year", "etc_season", "I", "etc_month", "I_cyear"):
        agg[k] = agg[k] / used
    for s in agg["spans"]:
        for k in s:
            s[k] /= used
    agg["years_used"] = used
    return agg


# ------------------------------------------------------------------- exposure / cover
def rain_risk(p: np.ndarray, thr: float) -> np.ndarray:
    """Spec B5.3 extreme rain: P >= thr mm/day, or 3-day total >= 3 x thr (75 mm at 25)."""
    three = np.convolve(p, np.ones(3), mode="full")[: len(p)]
    return (p >= thr) | (three >= 3 * thr)


def cover_metrics(tl: Timeline, wys: list[WYear], *, bare_thr=0.20, rain_thr=25.0, psrc="power") -> dict:
    N = tl.n_years
    exposed = (tl.cover < EXPOSED_COVER) & ~tl.water
    bare = (tl.cover < bare_thr) & ~tl.water
    out = {"bare_days": bare.sum() / N, "exposed_days": exposed.sum() / N,
           "rain": 0.0, "frost": 0.0, "heat": 0.0, "dry": 0.0, "E": 0.0, "rain_days_total": 0.0}
    used = 0
    for wy in wys:
        if wy.p.get(psrc) is None:
            continue
        used += 1
        rr = np.tile(rain_risk(wy.p[psrc], rain_thr), N)
        out["rain"] += (exposed & rr).sum() / N
        out["rain_days_total"] += rr.sum() / N
        out["frost"] += (exposed & np.tile(wy.tmin <= FROST_C, N)).sum() / N
        out["heat"] += (exposed & np.tile(wy.tmax >= HEAT_C, N)).sum() / N
        out["dry"] += (exposed & np.tile(wy.dry, N)).sum() / N
        # spec B4.4 E = sum_d (1 - cover) x rain_risk x slope_factor; water days excluded (our reading)
        out["E"] += ((1 - tl.cover) * (~tl.water) * rr).sum() / N
    if used == 0:
        return None
    for k in ("rain", "frost", "heat", "dry", "E", "rain_days_total"):
        out[k] /= used
    out["years_used"] = used
    return out


# ------------------------------------------------------------------- calendar-only metrics
def rating_day_array(tl: Timeline, crops: dict, key: str, var: str = "value") -> np.ndarray:
    """Daily 0-4 rating; var = "value" | "low" | "high" (the rating's own U range)."""
    vals = {cid: (crops[cid]["ratings_0_4"][key][var] if key in crops[cid]["ratings_0_4"] else 0)
            for cid in set(tl.crop_id)}
    return np.array([vals[c] for c in tl.crop_id], dtype=float)


def crop_day_mean(tl: Timeline, arr: np.ndarray) -> float:
    m = (tl.crop_id != "fallow_bare") & (tl.crop_id != "open_water_flood")
    return float(arr[m].mean()) if m.any() else 0.0


def erosion_relative(E: float, E_b: float) -> float:
    """Erosion score relative to the baseline (fix of spec B4.4, see README).

    score = 100 x E_b / (E_b + E): the baseline scores exactly 50, E = 0 scores 100, twice the baseline's
    rain-weighted exposure scores 33.3 and half scores 66.7. Monotonic in E, bounded 0-100 without clamping,
    symmetric in the ratio E/E_b (x2 and /2 sit equally far from 50). Both zero -> 50 (same as baseline);
    E_b = 0 and E > 0 -> 0."""
    if E_b + E <= 0:
        return 50.0
    return 100.0 * E_b / (E_b + E)


def erosion_change_pct(E: float, E_b: float) -> float | None:
    """Unclamped change in rain-weighted exposure vs the baseline, % (positive = less exposure than today;
    negative = more). None when E_b = 0 (undefined)."""
    return None if E_b <= 0 else 100.0 * (1 - E / E_b)


def longest_gap_days(present: np.ndarray) -> float:
    """Longest circular run of days on which `present` is False (np.inf if never present)."""
    if not present.any():
        return float("inf")
    if present.all():
        return 0.0
    k = int(np.argmax(present))          # rotate so the series starts on a present day
    p = np.roll(present, -k)
    best = run = 0
    for v in p:
        run = 0 if v else run + 1
        best = max(best, run)
    return float(best)


def families_by_year(tl: Timeline, crops: dict) -> list[set]:
    out = []
    for y in range(tl.n_years):
        fams = set()
        for cid in set(tl.crop_id[tl.cyear == y]):
            c = crops[cid]
            if c["family"] == "none":
                continue
            fams.update(c.get("families", [c["family"]]))
        out.append(fams)
    return out
