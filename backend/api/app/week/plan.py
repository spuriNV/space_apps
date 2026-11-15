"""The week's irrigation number and field-access calls from the forecast. Pure functions, no network."""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path

from .sources import sn, src

BARE_KC = 0.15
FLOODED_CROPS = {"rice_medium_grain", "open_water_flood"}
MM_PER_IN = 25.4
RULE = ("Too wet to work if the soil-wetness percentile is 80 or higher, or the rain over the previous 48 hours is 12 mm (0.5 in) or more. "
        "Marginal if the percentile is 65 to 80, or the 48-hour rain is 6 to 12 mm (0.25 to 0.5 in). Otherwise OK. "
        "48-hour rain for a day = that day's forecast rain plus the day before's, so it rolls forward through the forecast. "
        "The wetness percentile is the latest NASA reading compared with this field's own history for the same time of year; it is applied to "
        "today and tomorrow only (after that, only forecast rain decides). Rule of thumb, not a model.")
IN_MM = 25.4


# ------------------------------------------------------------------------------------------------ engine baseline
@lru_cache(maxsize=1)
def _crops():
    from rotation_engine.engine import load_crops  # noqa: PLC0415
    return load_crops()


@lru_cache(maxsize=16)
def baseline(template: str):
    """(strategy, timeline, {cycle-day: span}) of the baseline rotation for an engine location id."""
    from rotation_engine.engine import load_strategies  # noqa: PLC0415
    from rotation_engine.timeline import build_timeline  # noqa: PLC0415
    st = load_strategies(template)
    base = next((s for s in st if s.get("is_baseline")), st[0])
    tl = build_timeline(base, _crops())
    by_day = {}
    for sp in tl.spans:
        for i in sp.idx:
            by_day[int(i)] = sp
    return base, tl, by_day


def cycle_index(d: dt.date, n_years: int) -> int:
    doy0 = min((d.replace(year=2001, day=28) if (d.month, d.day) == (2, 29) else d.replace(year=2001)).timetuple().tm_yday - 1, 364)
    return (d.year % n_years) * 365 + doy0


def observed_cover(root: Path, pid: str, today: dt.date):
    """Latest observed class from backend/field's calendar (None if none, or older than 30 days)."""
    f = root / "backend" / "field" / "out" / pid / "calendar.json"
    if not f.is_file():
        return None
    try:
        cal = json.loads(f.read_text())
        seg = cal["years"][-1]["segments"][-1]
        end = dt.date.fromisoformat(seg["end"])
    except Exception:  # noqa: BLE001
        return None
    return {"class": seg["class"], "as_of": seg["end"], "stale": (today - end).days > 30,
            "source": {"id": "croplytics_observed_cover", "title": "Observed cover from Sentinel-2 / Landsat (backend/field calendar)",
                       "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", "accessed": today.isoformat(), "verified": True}}


# ------------------------------------------------------------------------------------------------ irrigation
def irrigation(root: Path, loc: dict, days: list[dict], today: dt.date, fsrc: dict, eff_rain: float) -> dict:
    base, tl, by_day = baseline(loc["template"])
    obs = observed_cover(root, loc["id"], today)
    obs_bare = bool(obs and not obs["stale"] and obs["class"] == "bare")
    rows, need, crops_seen, rainfed_days = [], 0.0, [], 0
    for r in days:
        d = dt.date.fromisoformat(r["date"])
        i = cycle_index(d, tl.n_years)
        sp = by_day.get(i)
        crop = str(tl.crop_id[i])
        irrigated = True if sp is None else sp.entry.get("irrigated", True) is not False
        kc, flag = float(tl.kc["value"][i]), None
        if obs_bare:
            kc, flag = BARE_KC, "observed bare: Kc 0.15"
        elif crop == "fallow_bare":
            flag = "fallow in the baseline rotation: Kc 0.15"
        crops_seen.append(crop)
        rainfed_days += not irrigated
        et0, rain = r["et0_mm"], r["rain_mm"]
        n = max(0.0, kc * et0 - eff_rain * rain)
        need += n
        ksrc = src("kc_bare" if flag else "kc")
        rows.append({"date": r["date"], "crop": crop, "kc": sn(kc, "Kc", ksrc, "lookup", flag or f"baseline rotation '{base['id']}', {crop}", ),
                     "need_mm": sn(n, "mm", src("rule"), "computed", f"max(0, Kc x ET0 - {eff_rain:g} x rain)"), "flag": flag})
    flooded = any(c in FLOODED_CROPS for c in crops_seen)
    fallow = obs_bare or all(c == "fallow_bare" for c in crops_seen)
    rainfed = rainfed_days >= 4
    acres = loc.get("acres")
    need_in = need / MM_PER_IN
    rule_src = src("rule")
    if fallow:
        verdict, kind = "Field is fallow/bare — no irrigation", "fallow"
    elif rainfed:
        verdict, kind = "Rain-fed", "rainfed"
    elif flooded:
        verdict, kind = "Flooded paddy: keep water at depth", "flooded"
    elif need_in < 0.1:
        verdict, kind = "Rain should cover it", "rain_covers"
    else:
        verdict, kind = f"Irrigate about {need_in:.1f} in this week", "irrigate"
    out = {"verdict": verdict, "kind": kind, "baseline": {"strategy_id": base["id"], "name": base.get("short_name") or base.get("name"), "crops_this_week": sorted(set(crops_seen))},
           "observed_cover": obs, "effective_rain_fraction": sn(eff_rain, "fraction", rule_src, "assumed", "rotation engine's effective-rain factor (spec B4.1, U)"),
           "days": rows}
    if kind == "flooded":
        out["note"] = "Flooded paddy: keep water at depth. No sprinkler number: the paddy is held flooded and the engine counts only the water the crop uses."
        out["etc_mm"] = sn(sum(rw["kc"]["value"] * d["et0_mm"] for rw, d in zip(rows, days)), "mm", src("kc"), "computed", "crop water use over the week (Kc x ET0), not an irrigation depth")
    else:
        out["need_mm"] = sn(need, "mm", rule_src, "computed", "sum over the 7 days of max(0, Kc x ET0 - effective rain)")
        out["need_in"] = sn(need_in, "in", rule_src, "computed")
        out["acre_in_per_acre"] = sn(need_in, "acre-in/acre", rule_src, "computed", "1 acre-inch per acre is 1 inch of water over the field")
        if acres and kind == "irrigate":
            out["field_acre_in"] = sn(need_in * acres, "acre-in", rule_src, "computed", f"{acres:g} acres x {need_in:.2f} in")
    return out


# ------------------------------------------------------------------------------------------------ field access
def _rank(s):
    return {"ok": 0, "marginal": 1, "too_wet": 2}[s]


def field_access(days: list[dict], past: list[dict], wet: dict | None, rain_src: dict) -> dict:
    rain = [p["rain_mm"] or 0.0 for p in past[-1:]] + [d["rain_mm"] or 0.0 for d in days]   # rain[0] = yesterday
    rule_src = src("rule")
    pct = wet.get("pct") if wet else None
    out = []
    for i, d in enumerate(days):
        r48 = rain[i] + rain[i + 1]
        p = pct if (pct is not None and i < 2) else None
        s = "ok"
        why = []
        if (p is not None and p >= 80) or r48 >= 12:
            s = "too_wet"
        elif (p is not None and p >= 65) or r48 >= 6:
            s = "marginal"
        if r48 >= 6:
            why.append(f"{r48:.0f} mm of rain in 48 h")
        if p is not None and p >= 65:
            why.append(f"soil wetter than {p:.0f}% of past years")
        out.append({"date": d["date"], "status": s, "rain_48h_mm": sn(r48, "mm", rain_src, "computed", "rain on this day plus the day before (forecast)"),
                    "why": why})
    return {"days": out}


def _wd(date: str) -> str:
    return dt.date.fromisoformat(date).strftime("%a")


def access_line(days: list[dict]) -> str:
    st = [d["status"] for d in days]
    if all(s == "ok" for s in st):
        return "Workable all week"
    if st[0] != "ok":
        w = "Too wet to work" if "too_wet" in st[:next((i for i, s in enumerate(st) if s == "ok"), 7)] else "Marginal"
        nxt = next((i for i, s in enumerate(st) if s == "ok"), None)
        return f"{w} all week" if nxt is None else f"{w} until {_wd(days[nxt]['date'])}"
    i = next(i for i, s in enumerate(st) if s != "ok")
    j = i
    while j + 1 < 7 and st[j + 1] != "ok":
        j += 1
    w = "Too wet" if "too_wet" in st[i:j + 1] else "Marginal"
    span = _wd(days[i]["date"]) if i == j else f"{_wd(days[i]['date'])}–{_wd(days[j]['date'])}"
    return f"{w} {span} after rain"
