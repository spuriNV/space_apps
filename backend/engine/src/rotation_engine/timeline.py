"""Daily cycle timeline from a strategy calendar: Kc(d), cover(d), water(d), crop(d).

A cycle of N years is N x 365 days (no leap days). Calendar entries are
[plant, harvest) in day-of-cycle; an end date on/before the start date falls in
the next cycle year, and the cycle wraps (a crop sown in the last year's autumn
continues into year 1's spring). Days not covered by an entry are fallow/bare.

Kc curve: FAO-56 single-coefficient shape (ini flat, dev linear, mid flat,
late linear to Kc end). Stage lengths come from the crop record; stage_mode:
  fixed       - season length must equal the stage total (checked)
  scale       - stage lengths scaled proportionally to the season (FAO-56 advice)
  stretch_mid - ini/dev/late fixed, mid stretched to fill the season
  truncate    - crop stage lengths (or stage_override), cut at harvest
Cover uses the same shape with cover_by_stage.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np

STAGES = ("ini", "dev", "mid", "late")


def doy0(mmdd: str) -> int:
    """0-based day of a non-leap year."""
    m, d = map(int, mmdd.split("-"))
    return (dt.date(2001, m, d) - dt.date(2001, 1, 1)).days


@dataclass
class Span:
    entry: dict
    crop: dict
    idx: np.ndarray      # cycle day indices (wrapped)
    kc: dict             # variant -> np.ndarray (len = len(idx))
    cover: np.ndarray
    stage: np.ndarray    # 0..3 per day


@dataclass
class Timeline:
    n_years: int
    kc: dict              # variant ("value","low","high") -> array N*365
    cover: np.ndarray
    water: np.ndarray     # bool
    crop_id: np.ndarray   # object array
    spans: list
    month: np.ndarray     # 1..12 per cycle day
    cyear: np.ndarray     # 0..N-1


def _stage_lengths(crop: dict, entry: dict, L: int) -> list[int]:
    if entry.get("stage_override"):
        base = [int(entry["stage_override"][s]) for s in STAGES]
    elif crop.get("stage_lengths_days"):
        base = [int(crop["stage_lengths_days"][s]) for s in STAGES]
    else:  # constant crops (fallow, water)
        return [0, 0, L, 0]
    mode = entry.get("stage_mode", "fixed")
    tot = sum(base)
    if mode == "fixed":
        if tot != L:
            raise ValueError(f"{entry['crop_id']}: season {L} d != stage total {tot} d (use scale/truncate)")
        return base
    if mode == "scale":
        f = L / tot
        out = [int(round(b * f)) for b in base]
        out[2] += L - sum(out)
        return out
    if mode == "stretch_mid":
        mid = L - (base[0] + base[1] + base[3])
        if mid < 0:
            raise ValueError(f"{entry['crop_id']}: season too short for stretch_mid")
        return [base[0], base[1], mid, base[3]]
    if mode == "truncate":
        if L > tot:
            raise ValueError(f"{entry['crop_id']}: truncate season {L} longer than stages {tot}")
        return base
    raise ValueError(mode)


def _curve(vals: tuple, lens: list[int], L: int) -> tuple[np.ndarray, np.ndarray]:
    ini, mid, end = vals
    li, ld, lm, ll = lens
    out = np.empty(sum(lens))
    stage = np.empty(sum(lens), dtype=int)
    o = 0
    out[o:o + li] = ini; stage[o:o + li] = 0; o += li
    if ld:
        out[o:o + ld] = ini + (mid - ini) * (np.arange(1, ld + 1) / ld)
    stage[o:o + ld] = 1; o += ld
    out[o:o + lm] = mid; stage[o:o + lm] = 2; o += lm
    if ll:
        out[o:o + ll] = mid + (end - mid) * (np.arange(1, ll + 1) / ll)
    stage[o:o + ll] = 3
    return out[:L], stage[:L]


def _cover_curve(cov: dict, lens: list[int], L: int) -> np.ndarray:
    li, ld, lm, ll = lens
    parts = [np.full(li, cov["ini"]),
             cov["ini"] + (cov["mid"] - cov["ini"]) * (np.arange(1, ld + 1) / max(ld, 1)),
             np.full(lm, cov["mid"]),
             cov["mid"] + (cov["late"] - cov["mid"]) * (np.arange(1, ll + 1) / max(ll, 1))]
    return np.concatenate(parts)[:L]


def build_timeline(strategy: dict, crops: dict) -> Timeline:
    N = int(strategy["cycle_years"])
    T = N * 365
    fallow = crops["fallow_bare"]
    kc = {v: np.full(T, fallow["kc"]["mid"][v], dtype=float) for v in ("value", "low", "high")}
    cover = np.zeros(T)
    water = np.zeros(T, dtype=bool)
    crop_id = np.array(["fallow_bare"] * T, dtype=object)
    taken = np.zeros(T, dtype=bool)
    spans = []
    for entry in strategy["calendar"]:
        crop = crops[entry["crop_id"]]
        s = (entry["year"] - 1) * 365 + doy0(entry["plant"])
        e_ = (entry["year"] - 1) * 365 + doy0(entry["harvest"])
        if e_ <= s:
            e_ += 365
        L = e_ - s
        idx = np.arange(s, e_) % T
        if taken[idx].any():
            raise ValueError(f"{strategy['id']}: overlapping calendar entries at {entry['crop_id']}")
        taken[idx] = True
        lens = _stage_lengths(crop, entry, L)
        span_kc = {}
        stage = None
        for v in ("value", "low", "high"):
            vals = tuple(crop["kc"][s_][v] for s_ in ("ini", "mid", "end"))
            span_kc[v], stage = _curve(vals, lens, L)
            kc[v][idx] = span_kc[v]
        cov_def = entry.get("cover_override") or crop["cover_by_stage"]
        cv = _cover_curve(cov_def, lens, L)
        cover[idx] = cv
        crop_id[idx] = crop["id"]
        if "water" in crop["role"]:
            water[idx] = True
        if entry.get("flooded_until"):
            fe = (entry["year"] - 1) * 365 + doy0(entry["flooded_until"])
            if fe <= s:
                fe += 365
            water[np.arange(s, fe) % T] = True
        spans.append(Span(entry, crop, idx, span_kc, cv, stage))
    days = np.arange(T)
    base = dt.date(2001, 1, 1)
    month_of_doy = np.array([(base + dt.timedelta(days=int(i))).month for i in range(365)])
    return Timeline(N, kc, cover, water, crop_id, spans, month_of_doy[days % 365], days // 365)
