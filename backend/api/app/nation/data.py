"""Loaders and calculations shared by the Nation routes (no web objects here)."""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NATION_DIR = ROOT / "backend" / "nation"
CUTOFF_RE = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
SCENARIO_CUTOFFS = ["07-15", "08-01", "08-15", "09-01"]
DIM = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
BC_BOX = (-139.1, 48.2, -114.0, 60.0)


def read_json(p: Path):
    return json.loads(p.read_text())


def programs() -> dict:
    return read_json(NATION_DIR / "programs.json")


def place_names() -> list:
    return read_json(NATION_DIR / "place_names.json")["names"]


def km_between(lon1, lat1, lon2, lat2) -> float:
    kx = math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lon1 - lon2) * kx, lat1 - lat2) * 111.32


def water_year(d: str) -> int:
    y, m = int(d[:4]), int(d[5:7])
    return y + 1 if m >= 10 else y


def after_cutoff_mm(monthly: list[float], mmdd: str) -> float:
    """Sum of the monthly crop water use from the cutoff day (inclusive) to the end of the year, month prorated by days."""
    m, d = int(mmdd[:2]), int(mmdd[3:])
    left = (DIM[m - 1] - min(d, DIM[m - 1]) + 1) / DIM[m - 1]
    return monthly[m - 1] * left + sum(monthly[m:])


def _v(x):
    return x.get("value") if isinstance(x, dict) else x


def rotations(items: list[dict], acres: float | None, cutoff: str) -> list[dict]:
    out = []
    for st in items:
        w, ex, sc = st.get("water", {}), st.get("exposure", {}), st.get("scores", {})
        monthly = [(_v(m) or 0.0) for m in w.get("etc_by_month_mm", [])]
        tot = sum(monthly)
        aft = after_cutoff_mm(monthly, cutoff) if len(monthly) == 12 else None
        irr = _v(w.get("irrigation_need_mm"))
        share = round(100 * aft / tot, 1) if aft is not None and tot > 0 else None
        bare = _v(ex.get("bare_days_per_year"))
        out.append({
            "id": st["id"], "name": st.get("short_name") or st.get("name"), "is_baseline": bool(st.get("is_baseline")),
            "water_mm_season": _r(_v(w.get("etc_mm_season"))),
            "water_mm_after_cutoff": _r(aft),
            "share_after_cutoff_pct": share,
            "irrigation_need_mm_season": _r(irr),
            "irrigation_need_mm_after_cutoff": _r(irr * share / 100) if irr is not None and share is not None else None,
            "irrigation_need_af_ac": _r(_v(w.get("irrigation_need_af_ac")), 2),
            "erosion_index": _r(_v(ex.get("erosion_index_E")), 2),
            "erosion_score": _r(_v((sc.get("erosion") or {}))),
            "bare_days_per_year": _r(bare),
            "soil_cover_pct": _r(100 * (1 - bare / 365)) if bare is not None else None,
            "n_fixation_score": _r(_v(sc.get("n_fixation"))),
            "n_scavenging_score": _r(_v(sc.get("n_scavenging"))),
            "n_balance_kg_ha": None,
            "dry_year_rank": None,
        })
    ranked = sorted((r for r in out if r["water_mm_after_cutoff"] is not None), key=lambda r: r["water_mm_after_cutoff"])
    for i, r in enumerate(ranked, 1):
        r["dry_year_rank"] = i
    return out


def _r(x, n=1):
    return None if x is None else round(float(x), n)


def cutoff_scenarios(items: list[dict], cutoff: str) -> list[dict]:
    dates = sorted(set(SCENARIO_CUTOFFS + [cutoff]))
    res = []
    for c in dates:
        rows = []
        for r in rotations(items, None, c):
            rows.append({"id": r["id"], "water_mm_after_cutoff": r["water_mm_after_cutoff"], "unmet_water_share_pct": r["share_after_cutoff_pct"],
                         "yield_loss_pct": None})
        res.append({"cutoff_date": c, "is_requested": c == cutoff, "rotations": rows})
    return res


def drought_history(daily_rows: list[dict], series: list[dict] | None, last_n: int = 15) -> list[dict]:
    """One row per water year (1 Oct to 30 Sep). daily_rows: keys date, eto_mm, grace_gw_pct, smap_sm_pct. series: nasa_series rows."""
    by: dict[int, dict] = {}
    for r in daily_rows:
        y = water_year(r["date"])
        b = by.setdefault(y, {"n": 0, "eto": 0.0, "g": [], "s": []})
        b["n"] += 1
        b["eto"] += r.get("eto_mm") or 0.0
        if r.get("grace_gw_pct") is not None:
            b["g"].append(r["grace_gw_pct"])
        if r.get("smap_sm_pct") is not None:
            b["s"].append(r["smap_sm_pct"])
    im: dict[int, dict] = {}
    for r in series or []:
        if r.get("imerg_wy_to_date_mm") is not None and r.get("imerg_wy_to_date_normal_mm"):
            y = water_year(r["date"])
            if y not in im or r["date"] > im[y]["date"]:
                im[y] = r
    out = []
    for y in sorted(by)[-last_n:]:
        b = by[y]
        i = im.get(y)
        out.append({
            "year": y, "partial": b["n"] < 360,
            "imerg_precip_anom_pct": _r(100 * (i["imerg_wy_to_date_mm"] / i["imerg_wy_to_date_normal_mm"] - 1)) if i else None,
            "smap_rootzone_pctl": _r(statistics.fmean(b["s"])) if b["s"] else None,
            "gracedadm_gw_pctl": _r(statistics.fmean(b["g"])) if b["g"] else None,
            "power_et0_mm": _r(b["eto"]) if b["n"] else None})
    return out


def doy(d: str) -> int:
    return dt.date.fromisoformat(d[:10]).timetuple().tm_yday


def phenology(rows: list[dict]) -> dict:
    """Green-up / peak / senescence DOY from weekly field NDVI per calendar year (50% of the year's amplitude, linear interpolation).
    A proxy for the timing of green vegetation on this polygon only."""
    byy: dict[int, list[tuple[int, float]]] = {}
    for r in rows:
        if r.get("ndvi") is None:
            continue
        byy.setdefault(int(r["week_start"][:4]), []).append((doy(r["week_start"]) + 3, r["ndvi"]))
    years = []
    for y, pts in sorted(byy.items()):
        pts.sort()
        if len(pts) < 20:
            continue
        vals = [v for _, v in pts]
        lo, hi = min(vals), max(vals)
        if hi - lo < 0.15:
            continue
        thr = lo + 0.5 * (hi - lo)
        ip = max(range(len(pts)), key=lambda i: pts[i][1])

        def cross(a, b):
            (d0, v0), (d1, v1) = pts[a], pts[b]
            return d0 if v1 == v0 else round(d0 + (thr - v0) / (v1 - v0) * (d1 - d0))
        up = next((cross(i - 1, i) for i in range(1, ip + 1) if pts[i - 1][1] < thr <= pts[i][1]), None)
        dn = next((cross(i - 1, i) for i in range(ip + 1, len(pts)) if pts[i - 1][1] >= thr > pts[i][1]), None)
        years.append({"year": y, "greenup_doy": up, "peak_doy": pts[ip][0], "senescence_doy": dn, "ndvi_peak": round(hi, 2), "weeks_with_data": len(pts)})
    def med(k):
        v = [x[k] for x in years if x[k] is not None]
        return round(statistics.median(v)) if v else None
    return {"by_year": years[-8:], "greenup_doy": med("greenup_doy"), "peak_doy": med("peak_doy"), "senescence_doy": med("senescence_doy")}
