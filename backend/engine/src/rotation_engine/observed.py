"""Observed consensus cover for the baseline (spec B5.4: "baseline uses observed consensus cover").

Reads backend/field/out/<preset>/calendar.json (rule-based NDVI/NDWI classes per day, 2016-2025) and
backend/field/out/<preset>/crop_history.json (CDL majority crop per year). For every day of the year the
consensus class is the most common known class over the calendar years whose CDL crop matches the baseline
crop (so CAR's 2016/2020/2022 fallow years do not enter the rice baseline). Unknown days are ignored; a day
with no known class in any used year keeps the modelled cover.

Class -> cover is OUR mapping (assumed, U): bare 0.10, partial 0.35, covered 0.80, water -> water flag, cover 0.
The detector classes are NDVI bands (bare < 0.2, partial <= 0.35, covered > 0.35), not fractional cover.
"""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
COVER_OF = {"bare": 0.10, "partial": 0.35, "covered": 0.80, "water": 0.0}
ORDER = ["covered", "partial", "bare", "water"]  # tie-break order
BASELINE_CDL = {"rice_medium_grain": {"Rice"}, "alfalfa_hay": {"Alfalfa"}}


def _base_crop(strategy: dict) -> str | None:
    cs = [e["crop_id"] for e in strategy["calendar"] if e["crop_id"] in BASELINE_CDL]
    return cs[0] if cs else None


def consensus(preset_id: str, strategy: dict) -> dict | None:
    d = REPO / "backend" / "field" / "out" / preset_id
    try:
        cal = json.loads((d / "calendar.json").read_text())
        hist = json.loads((d / "crop_history.json").read_text())["by_year"]
    except (OSError, ValueError, KeyError):
        return None
    base = _base_crop(strategy)
    if base is None:
        return None
    names = BASELINE_CDL[base]
    years = [y for y in cal["years"] if hist.get(str(y["year"])) in names]
    if not years:
        return None
    votes = [Counter() for _ in range(365)]
    for y in years:
        for seg in y["segments"]:
            if seg["class"] not in COVER_OF:
                continue
            a, b = dt.date.fromisoformat(seg["start"]), dt.date.fromisoformat(seg["end"])
            for k in range((b - a).days + 1):
                day = a + dt.timedelta(days=k)
                if day.month == 2 and day.day == 29:
                    continue
                votes[(dt.date(2001, day.month, day.day) - dt.date(2001, 1, 1)).days][seg["class"]] += 1
    cls = np.array([None] * 365, dtype=object)
    for i, c in enumerate(votes):
        if c:
            cls[i] = max(ORDER, key=lambda k: (c[k], -ORDER.index(k)))
    return {"classes": cls, "years": [y["year"] for y in years], "baseline_crop": base,
            "n_unknown_days": int(sum(c is None for c in cls))}


def observed_timeline(tl, preset_id: str, strategy: dict):
    """Return (timeline with observed cover/water, info) for a baseline strategy, or (None, None)."""
    cons = consensus(preset_id, strategy)
    if cons is None:
        return None, None
    N = tl.n_years
    cover, water = tl.cover.copy(), tl.water.copy()
    for i, c in enumerate(cons["classes"]):
        if c is None:
            continue
        idx = np.arange(i, N * 365, 365)
        cover[idx] = COVER_OF[c]
        water[idx] = c == "water"
    return replace(tl, cover=cover, water=water), cons
