"""score(): the single entry point (spec B3 RotationStrategy output, B4 scoring)."""
from __future__ import annotations

import copy
import itertools
import json
from functools import lru_cache

import numpy as np

from . import bc, model
from .model import WYear, cover_metrics, water_metrics
from .observed import observed_timeline
from .sources import assumed, blocked, sn, src
from .timeline import build_timeline, doy0
from .validation import openet_matched
from .weather import (CHUNK, DEFAULT_ETO, REPO, fieldreg, load_station_precip, load_weather, station_network,
                      station_year_precip, year_weather)

MM_PER_AF_AC = 304.8                      # 1 acre-ft/acre = 1 ft depth (exact)
DEFAULT_YEARS = tuple(range(2015, 2026))  # spec B2 daily master table 2015-2025
REPLAY_YEARS = (2022, 2023)               # spec B5.4
SCORE_KEYS = ("water_use", "forage_value", "n_fixation", "erosion", "organic_matter", "market",
              "pest_break", "infiltration", "n_scavenging", "income")
# spec B4.12: sliders 0-4; six brief priorities default to the slider midpoint (2, our choice), extras default 0
DEFAULT_WEIGHTS = {"water_use": 2, "forage_value": 2, "n_fixation": 2, "erosion": 2, "organic_matter": 2,
                   "market": 2, "pest_break": 0, "infiltration": 0, "income": 0, "n_scavenging": 0}
BARE_THR = (0.20, 0.15, 0.30)   # nominal (spec B5.1 bare < 0.20), range 0.15-0.30 (B4.12)
RAIN_THR = (25.0, 25.0, 50.0)   # nominal 25 mm (B5.3), range 25-50 (B4.12)
ETO_F = (1.0, 0.85, 1.15)       # +/-15% (B4.12) around the PM/station-T ETo; kept (CIMIS still blocked)
ETO_NOTE = ("ETo = FAO-56 Penman-Monteith (eq. 6) with NOAA GHCN-D station Tmax/Tmin (mean of the 3 regional-chunk "
            "stations; POWER on days none report) and POWER radiation, humidity (ea, eq. 19) and wind. Hargreaves "
            "(eq. 52) on POWER was the previous default; FAO-56 ch. 3 gives eq. 52 only as the alternative when "
            "radiation/humidity/wind are missing, and POWER Tmax reads +3.4-3.8 C warm in Jul-Aug vs the stations "
            "(backend/regional/README.md). CIMIS station ETo still blocked (key rejected).")
SLOPE_PCT = {
    "car_colusa_rice": assumed(0.0, "%", low=0.0, high=0.5,
                               note="Laser-levelled rice check (spec B4.4); NASADEM slope not yet supplied by "
                                    "backend/field. Cancels in E/E_baseline."),
    "caf_tulare_forage": assumed(0.5, "%", low=0.0, high=1.0,
                                 note="Flat SJV field placeholder; NASADEM slope not yet supplied by backend/field. "
                                      "Cancels in E/E_baseline."),
    "bc_salmon_river_forage": assumed(1.0, "%", low=0.0, high=3.0,
                                      note="Salmon River valley-floor hay field placeholder (assumed); the NASADEM "
                                           "slope is pending (backend/nasa_open terrain not run for BC). Cancels in "
                                           "E/E_baseline."),
}
RULE = "rule of thumb, not a model"


# ------------------------------------------------------------------ data
@lru_cache(maxsize=1)
def load_crops() -> dict:
    return {c["id"]: c for c in json.loads((CHUNK / "crops.json").read_text())["crops"]}


@lru_cache(maxsize=1)
def _strategies_raw() -> tuple:
    return tuple(json.loads((CHUNK / "strategies.json").read_text())["strategies"])


def load_strategies(preset_id: str) -> list[dict]:
    """The location's strategies. Registry fields reuse their family's set (rice -> CAR0-CAR3 of car_colusa_rice,
    forage -> CAF0-CAF3 of caf_tulare_forage) with location_id set to the field."""
    own = [copy.deepcopy(s) for s in _strategies_raw() if s["location_id"] == preset_id]
    if own:
        return own
    tpl = fieldreg.template(preset_id)
    out = [copy.deepcopy(s) for s in _strategies_raw() if s["location_id"] == tpl]
    for s in out:
        s["location_id"] = preset_id
        s["template_location_id"] = tpl
    return out


def _region(preset_id: str) -> str:
    try:
        return fieldreg.region(preset_id)
    except KeyError:
        return "ca"


def slope_pct(preset_id: str) -> dict:
    if preset_id in SLOPE_PCT:
        return SLOPE_PCT[preset_id]
    base = SLOPE_PCT[fieldreg.template(preset_id)]
    v = fieldreg.get(preset_id).get("slope_pct", base["value"])
    return assumed(v, "%", low=base.get("low"), high=base.get("high"),
                   note=f"Family placeholder from the registry ({'laser-levelled rice' if v == 0 else 'flat SJV field'}); "
                        "NASADEM slope not yet supplied. Cancels in E/E_baseline.")


def load_soil(preset_id: str) -> dict | None:
    p = REPO / "data" / "cache" / preset_id / "soil.json"
    return json.loads(p.read_text()) if p.exists() else None


def af_to_mm(af_per_acre: float) -> float:
    return af_per_acre * MM_PER_AF_AC


def mm_to_af(mm: float) -> float:
    return mm / MM_PER_AF_AC


# ------------------------------------------------------------------ weather years
@lru_cache(maxsize=64)
def weather_years(preset_id: str, years: tuple, dT_c: float, dP_pct: float) -> tuple:
    w = load_weather(preset_id)
    sp = load_station_precip(preset_id)
    out = []
    for y in years:
        yw = year_weather(w, y, dT_c, dP_pct)
        dry = yw.p_30d < 0.5 * yw.p_30d_clim
        p = {"power": yw.p, "noaa": station_year_precip(sp, yw, y, dP_pct) if sp else None}
        out.append(WYear(y, yw.tmax, yw.tmin, yw.eto, p, dry))
    return tuple(out)


# ------------------------------------------------------------------ combos (spec B4.12)
def _water_combos(rice_F: dict):
    nominal = ("value", ETO_F[0], rice_F["value"], "power")
    corners = list(itertools.product(("low", "high"), ETO_F[1:], (rice_F["low"], rice_F["high"]), ("power", "noaa")))
    return nominal, [nominal] + corners


def _cover_combos():
    nominal = (BARE_THR[0], RAIN_THR[0], "power")
    corners = list(itertools.product(BARE_THR[1:], sorted(set(RAIN_THR[1:])), ("power", "noaa")))
    return nominal, [nominal] + corners


def _evaluate(tl, wys, crops, cov_tl=None):
    rice_F = crops["rice_medium_grain"]["flood_percolation_mm"]
    wn, wcs = _water_combos(rice_F)
    cn, ccs = _cover_combos()
    water = {}
    for c in wcs:
        r = water_metrics(tl, list(wys), kc_var=c[0], eto_f=c[1], F=c[2], psrc=c[3])
        if r is not None:
            water[c] = r
    cover = {}
    for c in ccs:
        r = cover_metrics(cov_tl or tl, list(wys), bare_thr=c[0], rain_thr=c[1], psrc=c[2])
        if r is not None:
            cover[c] = r
    return {"water": water, "water_nominal": wn, "cover": cover, "cover_nominal": cn}


def _rng(d: dict, nominal, fn):
    vals = {k: fn(v) for k, v in d.items()}
    allv = [v for v in vals.values() if v is not None]
    return vals[nominal], min(allv), max(allv)


@lru_cache(maxsize=8)
def _imax(preset_id: str) -> float:
    """I_max for water_use = 100 x clamp(1 - I/I_max): the largest I (high end) among this location's
    strategies under default conditions. Spec B4.1 does not define I_max (open question)."""
    crops = load_crops()
    wys = weather_years(preset_id, DEFAULT_YEARS, 0.0, 0.0)
    best = 0.0
    for s in load_strategies(preset_id):
        ev = _evaluate(build_timeline(s, crops), wys, crops)
        best = max(best, max(r["I"] for r in ev["water"].values()))
    return best


# ------------------------------------------------------------------ helpers
def _clamp(x, lo=0.0, hi=100.0):
    return float(min(hi, max(lo, x)))


def _psources(preset_id, wys):
    if station_network(preset_id) == "eccc":
        return bc.psources(preset_id, wys)
    used = ["NASA POWER PRECTOTCORR"]
    if any(w.p.get("noaa") is not None for w in wys):
        used.append("NOAA NCEI GHCN-Daily station mean (regional cache)")
    missing = ["GPM IMERG (Earthdata login not set up)", "CIMIS (API key)"]
    if "NOAA NCEI GHCN-Daily station mean (regional cache)" not in used:
        missing.append("NOAA NCEI (no station cache for this preset yet)")
    return used, missing


def _sn_c(v3, unit, source, note, rnd=1, **extra):
    return sn(v3[0], unit, low=v3[1], high=v3[2], method="computed", source=source, note=note, rnd=rnd, **extra)


def _ratings_mean(tl, crops, key, var="value"):
    return model.crop_day_mean(tl, model.rating_day_array(tl, crops, key, var))


def _root_mean(tl, crops, var="value"):
    arr = np.array([crops[c]["root_depth_class"][var] for c in tl.crop_id], dtype=float)
    return model.crop_day_mean(tl, arr)


RVARS = ("value", "low", "high")  # rating/yield range ends; every rating-based score is non-decreasing in them


def _host_crop(tl) -> str:
    """The baseline's main crop: the cash/forage crop with the most days in the cycle."""
    days = {}
    for sp in tl.spans:
        if set(sp.crop["role"]) & {"cash", "forage"}:
            days[sp.crop["id"]] = days.get(sp.crop["id"], 0) + len(sp.idx)
    return max(days, key=days.get)


# Pest-break scale: years out of the host crop for a full break. UC IPM alfalfa "Crop rotation impacts on pests":
# "a 3- to 4-year nonhost crop rotation is ideal", at least 1 year for weeds and clover root curculio, 2-3 years for
# root-knot nematode. We use 3 years (range 2-4); applying it to rice is our assumption (UC IPM rice gives no years).
PEST_FULL_BREAK_YEARS = (3.0, 4.0, 2.0)   # value, low-score end, high-score end


@lru_cache(maxsize=8)
def _openet_years(preset_id: str):
    base = next(s for s in load_strategies(preset_id) if s["is_baseline"])
    return openet_matched(preset_id, base)


def _openet_check(preset_id: str, strategy: dict, tl, crops):
    """Spec B4.1 validation line: baseline annual ETc vs OpenET Ensemble actual ET, on the SAME years (those whose
    CDL crop is the baseline crop), default weather (no scenario). Reported only; never a score input, never fitted."""
    m = _openet_years(preset_id)
    if m is None:
        return None
    ev = _evaluate(tl, weather_years(preset_id, tuple(m["years"]), 0.0, 0.0), crops)
    e = _rng(ev["water"], ev["water_nominal"], lambda r: r["etc_year"])
    o = m["mean"]
    osrc = {**src("openet"), "cache_path": m["cache_path"]}
    yrs = ", ".join(map(str, m["years"]))
    et = sn(o, "mm/yr", low=m["low"], high=m["high"], method="measured", source=osrc, rnd=0,
            note=f"OpenET Ensemble v2.1 annual ET, field polygon, mean of the years whose CDL crop is "
                 f"{m['crop']} ({yrs}); low/high = driest/wettest of those years. Independent check only.")
    pct = sn(100 * (e[0] - o) / o, "%", low=100 * (e[1] - o) / o, high=100 * (e[2] - o) / o, method="computed",
             source=osrc, rnd=1,
             note=f"(engine annual ETc - OpenET) / OpenET, both on years {yrs}. Engine {e[0]:.0f} mm "
                  f"(range {e[1]:.0f}-{e[2]:.0f}) vs OpenET {o:.0f} mm. Positive = engine higher. Default weather; "
                  f"no engine coefficient is fitted to OpenET. Main remaining gap is May-Oct (FAO-56 Kc above "
                  f"OpenET's ET/ETo); see backend/engine/README.md.")
    return et, pct


# ------------------------------------------------------------------ main
def score(preset_id: str, weights: dict | None = None, constraints: dict | None = None,
          market_preference: str = "no_preference", allocation=None, replay_year: int | None = None,
          scenario: dict | None = None) -> list[dict]:
    """Score the baseline and alternatives for a preset. Returns RotationStrategy dicts (spec B3).

    allocation: None, a number (acre-ft/acre per year) or {"value": x, "unit": "acre-ft/acre"}.
    scenario: {"dT_c": float in [-1, 4], "dP_pct": float in [-30, 30]}.
    """
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    for k, v in weights.items():
        if k not in DEFAULT_WEIGHTS:
            raise ValueError(f"unknown weight {k}")
        if not 0 <= v <= 4:
            raise ValueError(f"weight {k}={v} outside [0,4] (spec B4.12)")
    constraints = constraints or {}
    scenario = {"dT_c": 0.0, "dP_pct": 0.0, **(scenario or {})}
    dT, dP = float(scenario["dT_c"]), float(scenario["dP_pct"])
    if not (-1 <= dT <= 4 and -30 <= dP <= 30):
        raise ValueError("scenario outside spec B4.12 bounds (dT -1..+4 C, dP -30..+30 %)")
    if market_preference not in ("sell", "feed_own_herd", "no_preference"):
        raise ValueError("market_preference must be sell | feed_own_herd | no_preference")
    alloc_af = allocation.get("value") if isinstance(allocation, dict) else allocation

    crops = load_crops()
    strategies = load_strategies(preset_id)
    w = load_weather(preset_id)
    wsrc = w.source()
    years = (int(replay_year),) if replay_year else DEFAULT_YEARS
    wys = weather_years(preset_id, years, dT, dP)
    replay_wys = {y: weather_years(preset_id, (y,), dT, dP) for y in REPLAY_YEARS}
    imax = _imax(preset_id)
    soil = load_soil(preset_id)
    psrc_used, psrc_missing = _psources(preset_id, wys)

    tls = {s["id"]: build_timeline(s, crops) for s in strategies}
    # spec B5.4: the baseline's exposure/erosion use observed consensus cover (backend/field) when available
    ctls, obs_info = {}, {}
    for s in strategies:
        if s["is_baseline"]:
            ctl, info = observed_timeline(tls[s["id"]], preset_id, s)
            if ctl is not None:
                ctls[s["id"]], obs_info[s["id"]] = ctl, info
    evs = {sid: _evaluate(tl, wys, crops, ctls.get(sid)) for sid, tl in tls.items()}
    revs = {y: {sid: _evaluate(tl, rw, crops, ctls.get(sid)) for sid, tl in tls.items()} for y, rw in replay_wys.items()}
    base = next(s for s in strategies if s["is_baseline"])
    base_crops = {sp.crop["id"] for sp in tls[base["id"]].spans}
    host = _host_crop(tls[base["id"]])                       # pest-break host (today's main crop)
    host_gap_b = model.longest_gap_days(tls[base["id"]].crop_id == host)

    years_note = (f"replay year {replay_year}" if replay_year else
                  f"mean of {years[0]}-{years[-1]} weather years") + \
                 (f"; scenario dT={dT:+g} C, dP={dP:+g}%" if (dT or dP) else "")

    out = []
    for s in strategies:
        tl, ev = tls[s["id"]], evs[s["id"]]
        wn, cn = ev["water_nominal"], ev["cover_nominal"]
        W, C = ev["water"], ev["cover"]
        Wb = evs[base["id"]]["cover"]
        N = tl.n_years

        # ---------------- water (B4.1)
        etc_season = _rng(W, wn, lambda r: r["etc_season"])
        etc_year = _rng(W, wn, lambda r: r["etc_year"])
        I = _rng(W, wn, lambda r: r["I"])
        I_cy_max = _rng(W, wn, lambda r: float(r["I_cyear"].max()))
        wnote = (f"{years_note}. ETc = Kc(d) x ETo (FAO-56 eq. 6 PM, station Tmax/Tmin + POWER Rs/RH/wind; Kc FAO-56 "
                 f"Table 12 where V); range = "
                 f"min/max over Kc low/high, ETo +/-15%, rice F 300-600 mm, precip sources {psrc_used}.")
        water = {
            "etc_mm_season": _sn_c(etc_season, "mm/yr", wsrc, wnote + " Crop, cover and flood days; bare days excluded."),
            "etc_mm_year": _sn_c(etc_year, "mm/yr", wsrc, wnote + " All days incl. bare soil at Kc 0.15 (U)."),
            "irrigation_need_mm": _sn_c(I, "mm/yr", wsrc, wnote + " I = sum over irrigated seasons of monthly "
                                        "max(0, ETc - 0.8 P) (0.8 U) + rice F (U); averaged per cycle year."),
            "irrigation_need_af_ac": _sn_c(tuple(mm_to_af(x) for x in I), "acre-ft/acre/yr", src("unit_definition"),
                                           "irrigation_need_mm / 304.8", rnd=2),
            "irrigation_need_max_cycle_year_mm": _sn_c(I_cy_max, "mm/yr", wsrc,
                                                       "Largest single cycle-year I (used for the allocation check)"),
            "etc_by_month_mm": [
                _sn_c(_rng(W, wn, lambda r, m=m: r["etc_month"][m]), "mm/month", wsrc, f"Month {m + 1}; per cycle year")
                for m in range(12)],
            "openet_et_mm_season": blocked("mm/yr", "openet", "OpenET measures the crop actually grown on the field "
                                           "(the baseline); this alternative was not grown there.", method="measured"),
            "etc_vs_openet_pct": blocked("%", "openet", "Only the baseline can be checked against OpenET."),
            "eto_source_note": ETO_NOTE,
            "by_crop": [],
        }
        if s["is_baseline"]:
            oe = _openet_check(preset_id, s, tl, crops)
            if oe:
                water["openet_et_mm_season"], water["etc_vs_openet_pct"] = oe
        for k, sp in enumerate(tl.spans):
            water["by_crop"].append({
                "crop_id": sp.crop["id"], "year": sp.entry["year"], "plant": sp.entry["plant"],
                "harvest": sp.entry["harvest"], "irrigated": sp.entry["irrigated"],
                "etc_mm": _sn_c(_rng(W, wn, lambda r, k=k: r["spans"][k]["etc"]), "mm/season", wsrc, years_note),
                "etc_jun_aug_mm": _sn_c(_rng(W, wn, lambda r, k=k: r["spans"][k]["etc_jja"]), "mm/season", wsrc,
                                        "ETc of this crop falling in Jun-Aug"),
                "irrigation_need_mm": _sn_c(_rng(W, wn, lambda r, k=k: r["spans"][k]["I"]), "mm/season", wsrc,
                                            "0 for rain-fed entries (cover)"),
            })
        # allocation check
        if alloc_af is None:
            ac = {"status": "no_allocation_entered", "allocation_mm": None}
        else:
            amm = af_to_mm(float(alloc_af))
            status = ("exceeds_allocation" if I_cy_max[0] > amm else
                      "may_exceed_allocation" if I_cy_max[2] > amm else "within_allocation")
            ac = {"status": status,
                  "allocation_af_ac": sn(float(alloc_af), "acre-ft/acre/yr", method="lookup",
                                         source={"id": "user_input", "title": "User-entered allocation",
                                                 "url": "planner-spec.md#b41-water-use-m", "accessed": "2026-11-14",
                                                 "verified": False}, note="User input"),
                  "allocation_mm": sn(amm, "mm/yr", method="computed", source=src("unit_definition"),
                                      note="acre-ft/acre x 304.8", rnd=1)}
        water["allocation_check"] = ac

        # ---------------- exposure (B5.3/B5.4)
        if s["id"] in obs_info:
            oi = obs_info[s["id"]]
            cover_note = (f"Observed consensus cover from backend/field (Sentinel-2/Landsat rule classes, calendar years "
                          f"{oi['years'][0]}-{oi['years'][-1]} whose CDL crop is the baseline crop: {oi['years']}; "
                          f"class->cover bare 0.10 / partial 0.35 / covered 0.80 is our assumption, U; "
                          f"{oi['n_unknown_days']} days with no observation keep modelled cover)")
        else:
            cover_note = "Modelled cover from the calendar"
        enote = f"{years_note}. {cover_note}. Exposed = cover < 0.5 and not water."

        def exposure_block(Cd, nominal):
            return {
                "bare_days_per_year": _sn_c(_rng(Cd, nominal, lambda r: r["bare_days"]), "days/yr",
                                            src("field_shift_engine"), "cover < bare threshold (0.20; range 0.15-0.30) "
                                            "and not water; modelled from the calendar"),
                "exposed_days_per_year": _sn_c(_rng(Cd, nominal, lambda r: r["exposed_days"]), "days/yr",
                                               src("field_shift_engine"), "cover < 0.5 and not water"),
                "exposed_rain_days": _sn_c(_rng(Cd, nominal, lambda r: r["rain"]), "days/yr", wsrc,
                                           enote + " Extreme rain: P >= 25 mm/day or 3-day >= 75 mm (U); range: "
                                           "threshold 25-50 mm (3-day = 3x) and precip sources."),
                "exposed_frost_days": _sn_c(_rng(Cd, nominal, lambda r: r["frost"]), "days/yr", wsrc,
                                            enote + " Frost: POWER T2M_MIN <= 0 C."),
                "exposed_heat_days": _sn_c(_rng(Cd, nominal, lambda r: r["heat"]), "days/yr", wsrc,
                                           enote + " Heat: POWER T2M_MAX >= 35 C."),
                "exposed_dry_days": _sn_c(_rng(Cd, nominal, lambda r: r["dry"]), "days/yr", wsrc,
                                          enote + " Dry-spell PROXY: POWER 30-day P < 50% of its 1991-2020 "
                                          "climatology (spec rule uses IMERG/SMAP, both blocked). In the dry "
                                          "Central Valley summer nearly every day qualifies, so this mostly counts "
                                          "bare summer days."),
            }

        exposure = exposure_block(C, cn)
        exposure["replay"] = {}
        for y in REPLAY_YEARS:
            rev = revs[y][s["id"]]
            if not rev["cover"]:
                exposure["replay"][str(y)] = None
                continue
            blk = exposure_block(rev["cover"], rev["cover_nominal"])
            blk["irrigation_need_mm"] = _sn_c(_rng(rev["water"], rev["water_nominal"], lambda r: r["I"]), "mm/yr",
                                              wsrc, f"Replay {y}")
            blk["etc_mm_season"] = _sn_c(_rng(rev["water"], rev["water_nominal"], lambda r: r["etc_season"]),
                                         "mm/yr", wsrc, f"Replay {y}")
            exposure["replay"][str(y)] = blk
        exposure["scenario"] = {"dT_c": dT, "dP_pct": dP}
        slope = slope_pct(preset_id)
        sf = 1 + slope["value"] / 5
        exposure["erosion_index_E"] = _sn_c(_rng(C, cn, lambda r: r["E"] * sf), "rain-weighted bare days/yr", wsrc,
                                            "spec B4.4 E = sum_d (1-cover) x rain_risk x (1 + slope%/5); water days "
                                            "excluded", rnd=2)

        # ---------------- scores (B4.2-B4.10)
        scores = {}
        # water use
        scores["water_use"] = _sn_c(tuple(100 * _clamp(1 - x / imax, 0, 1) for x in (I[0], I[2], I[1])),
                                    "score_0_100", wsrc,
                                    f"spec B4.1 100 x clamp(1 - I/I_max); I_max = {imax:.0f} mm = largest I (high "
                                    f"end) among this location's strategies, default years (our choice; spec does "
                                    f"not define I_max). {RULE}")
        # forage (B4.2)
        def forage(var):
            fsum = 0.0
            for sp in tl.spans:
                rat = sp.crop["ratings_0_4"]["forage_harvest_value"][var]
                yv = sp.crop["yield_range"][var]
                if rat and yv and sp.entry.get("harvest_months"):
                    # harvestable share = months this harvested forage crop is in the field / 12 (our reading of
                    # "harvestable_months_share"; counting harvest months penalised one-cut crops, see README)
                    fsum += rat / 4 * len(sp.idx) / 365 * min(yv / 10000, 1)
            return 100 * fsum / N

        scores["forage_value"] = sn(forage("value"), "score_0_100", low=forage("low"), high=forage("high"),
                                    method="computed", source=src("field_shift_engine"),
                                    note=f"spec B4.2 100 x sum(rating/4 x months in field/12 x min(yield/10000,1)) / "
                                         f"cycle_years, over harvested forage crops. Months in field replaces the "
                                         f"count of harvest months (that count scored a one-cut silage crop below "
                                         f"a multi-cut hay of similar dry matter). Range = rating and yield ranges "
                                         f"(both U). {RULE}", rnd=1)
        # N fixation (B4.3)
        leg = np.array([crops[c]["legume"] for c in tl.crop_id])
        nfx = [100 * float((model.rating_day_array(tl, crops, "nitrogen_fixation", v) * leg).sum()) / 4 / 365 / N
               for v in RVARS]
        scores["n_fixation"] = sn(nfx[0], "score_0_100", low=nfx[1], high=nfx[2], method="computed",
                                  source=src("field_shift_engine"),
                                  note=f"spec B4.3 100 x sum(rating_nfix/4 x months growing/12)/cycle_years, "
                                       f"legumes only; ratings U, range = rating range. {RULE}", rnd=1)
        # erosion (B4.4)
        resid3 = [_ratings_mean(tl, crops, "lasting_residue", v) for v in RVARS]
        resid = resid3[0]

        def ero(c):
            return model.erosion_relative(C[c]["E"], Wb[c]["E"])

        def ero_raw(c):
            return model.erosion_change_pct(C[c]["E"], Wb[c]["E"])

        er = (ero(cn), min(ero(c) for c in C), max(ero(c) for c in C))
        raws = [x for x in (ero_raw(c) for c in C) if x is not None]
        raw = ero_raw(cn)
        scores["erosion"] = _sn_c(er, "score_0_100", wsrc,
                                  f"Relative to today's rotation (fix of spec B4.4, see backend/engine/README.md): "
                                  f"100 x E_baseline / (E_baseline + E). Today's rotation = 50; less rain-weighted "
                                  f"bare exposure scores above 50 (no exposure = 100), more scores below 50 (twice "
                                  f"today's = 33). Not clamped. Change in E vs today: "
                                  f"{'undefined (E_baseline = 0)' if raw is None else f'{raw:+.1f}%'}. The 30% "
                                  f"residue-rating blend was dropped from the score (it made today's rotation score "
                                  f"non-zero and mixed an absolute rating into a relative score); it is reported as "
                                  f"residue_component. {RULE}",
                                  exposure_component=sn(raw, "% vs baseline",
                                                        low=min(raws) if raw is not None and raws else None,
                                                        high=max(raws) if raw is not None and raws else None,
                                                        method="computed", source=wsrc, rnd=1,
                                                        note="100 x (1 - E/E_baseline), NOT clamped: 0 for today's "
                                                             "rotation, negative = more rain-weighted bare exposure "
                                                             "than today; null if E_baseline = 0"),
                                  residue_component=sn(100 * resid / 4, "score_0_100", low=100 * resid3[1] / 4,
                                                       high=100 * resid3[2] / 4, method="computed",
                                                       source=src("field_shift_engine"), rnd=1,
                                                       note="100 x lasting_residue/4, crop-day mean rating (U). Shown "
                                                            "for context, not part of the erosion score: residue "
                                                            "would belong inside the cover term (RUSLE soil-loss-"
                                                            "ratio subfactors, USDA Agriculture Handbook 703), which "
                                                            "needs daily residue cover we do not have"),
                                  slope_pct=slope)
        # organic matter (B4.5)
        sb3 = [_ratings_mean(tl, crops, "soil_builder", v) for v in RVARS]
        sb = sb3[0]
        perennial_years = sum(len(sp.idx) for sp in tl.spans if sp.crop.get("perennial")) / 365

        def om(c, i=0):
            return 100 * (0.5 * (sb3[i] + resid3[i]) / 2 / 4 + 0.3 * perennial_years / N
                          + 0.2 * (1 - C[c]["bare_days"] / 365))

        scores["organic_matter"] = _sn_c((om(cn), min(om(c, 1) for c in C), max(om(c, 2) for c in C)),
                                         "score_0_100", src("field_shift_engine"),
                                         f"spec B4.5; soil_builder {sb:.2f}, lasting_residue {resid:.2f} (crop-day "
                                         f"means, U), perennial years {perennial_years:.2f}/{N}. Range = bare "
                                         f"threshold/rain/precip combos and the rating ranges. {RULE}")
        # market (B4.6)
        classes = [sp.crop["market_class"] for sp in tl.spans if sp.crop["market_class"] != "none"]
        if market_preference == "no_preference" or not classes:
            mv = 50.0
        else:
            want = "sell" if market_preference == "sell" else "feed"
            match = sum(c in (want, "either") for c in classes) / len(classes)
            mv = 50 + 25 * (match - (1 - match))
        scores["market"] = assumed(round(mv, 1), "score_0_100", low=round(mv, 1), high=round(mv, 1),
                                   note=f"spec B4.6 table rule: 50 +/- 25 by share of products matching "
                                        f"'{market_preference}' (sell: rice/hay/wheat; feed: silage/sorghum-sudan). "
                                        f"Base 50 and the linear rule are ours. No uncertainty model. Always a "
                                        f"local-review item. {RULE}")
        scores["market"]["method"] = "computed"
        # pest break (B4.7)
        fy = model.families_by_year(tl, crops)
        fams = sorted(set().union(*fy))
        distinct = len(fams)
        gap = model.longest_gap_days(tl.crop_id == host)
        extra_y = 1e9 if np.isinf(gap) else max(0.0, (gap - host_gap_b) / 365)
        pb = [100 * min(1, distinct / 3) * min(1.0, extra_y / yrs) for yrs in PEST_FULL_BREAK_YEARS]
        gap_txt = (f"{crops[host]['name']} never grown in the modelled cycle (counted as a full break; the real "
                   f"break depends on the years around it)" if np.isinf(gap) else
                   f"longest stretch without {crops[host]['name']} {gap:.0f} d vs {host_gap_b:.0f} d today "
                   f"= {extra_y:.2f} extra host-free years")
        scores["pest_break"] = sn(pb[0], "score_0_100", low=pb[1], high=pb[2], method="computed",
                                  source=src("uc_ipm_alfalfa_rotation"),
                                  note=f"Fix of spec B4.7 (see README): 100 x min(1, distinct families/3) x "
                                       f"min(1, extra host-free years / 3). Host = today's main crop "
                                       f"({crops[host]['name']}); extra host-free years = (longest circular "
                                       f"stretch without the host - today's) / 365, so today's rotation scores 0 "
                                       f"and the normal winter gap earns nothing. 3 years for a full break from UC IPM "
                                       f"alfalfa ('a 3- to 4-year nonhost crop rotation is ideal'); range 2-4 years; "
                                       f"using it for rice is our assumption (U); UC IPM rice "
                                       f"({src('uc_ipm_rice_weeds')['url']}) names cereals, safflower and dry fallow "
                                       f"as rotations out of rice. Families {fams}; {gap_txt}. No pest dataset "
                                       f"exists. {RULE}", rnd=1)
        # infiltration (B4.8)
        comp3 = [_ratings_mean(tl, crops, "compaction_reduction", v) for v in RVARS]
        root3 = [_root_mean(tl, crops, v) for v in RVARS]
        comp, rootc = comp3[0], root3[0]
        cover_months = float((tl.cover >= 0.5).sum()) / N / model.DAYS_PER_MONTH
        hg = (soil or {}).get("hydrologic_group")
        inf3 = [100 * (0.5 * comp3[i] / 4 + 0.3 * root3[i] / 2 + 0.2 * min(cover_months, 12) / 12) for i in range(3)]
        scores["infiltration"] = sn(inf3[0], "score_0_100", low=inf3[1], high=inf3[2],
                                    method="computed", source=src("field_shift_engine"),
                                    note=f"spec B4.8; compaction {comp:.2f}, root class {rootc:.2f} (U), cover months "
                                         f"{cover_months:.1f}; range = rating/root-class ranges. SSURGO hydrologic group {hg or 'unknown'}"
                                         f"{': low intrinsic infiltration; rotation effect limited' if hg == 'D' else ''}"
                                         f". {RULE}", rnd=1)
        # N scavenging (B4.9)
        fw = np.isin(tl.month, model.FW_MONTHS) & (tl.cover >= 0.5)
        fw_months = float(fw.sum()) / N / model.DAYS_PER_MONTH
        nsv = [min(100.0, 100 * float((model.rating_day_array(tl, crops, "nitrogen_scavenging", v) * fw).sum())
                   / N / model.DAYS_PER_MONTH / 4 / 6) for v in RVARS]
        scores["n_scavenging"] = sn(nsv[0], "score_0_100", low=nsv[1], high=nsv[2], method="computed",
                                    source=src("field_shift_engine"),
                                    note=f"spec B4.9 100 x rating/4 x fall-winter cover months/6, computed day by "
                                         f"day over Oct-Mar with cover >= 0.5 ({fw_months:.1f} months); ratings U, range = rating range. "
                                         f"{RULE}", rnd=1)
        # income (B4.10) - blocked
        seed_cost = sum(sp.crop["seed_cost_per_ha"]["value"] for sp in tl.spans) / N
        scores["income"] = blocked("USD/ha/yr", "nass_quickstats",
                                   "Needs rice/wheat prices (NASS Quick Stats key), hay prices (AMS My Market News "
                                   "key, report slug U) and the EQIP 340 California rate (schedule not transcribed). "
                                   f"Seed cost alone (assumed, U) would be ~{seed_cost:.0f} USD/ha/yr.",
                                   method="computed")
        scores["income"]["components"] = {
            "price_range": blocked("USD/unit", "ams_mymarketnews", "AMS/NASS keys missing"),
            "seed_cost_per_ha": assumed(round(seed_cost, 0), "USD/ha/yr",
                                        low=round(sum(sp.crop["seed_cost_per_ha"]["low"] for sp in tl.spans) / N, 0),
                                        high=round(sum(sp.crop["seed_cost_per_ha"]["high"] for sp in tl.spans) / N, 0),
                                        note="Sum of crop seed-cost placeholders per cycle year (U)"),
            "eqip_340_rate": blocked("USD/acre", "eqip_340", "California EQIP 340 rate not transcribed (U)"),
        }

        # ---------------- composite (B4.12)
        active = {k: v for k, v in weights.items() if v > 0 and scores[k]["value"] is not None}
        ignored = [k for k, v in weights.items() if v > 0 and scores[k]["value"] is None]
        tw = sum(active.values())
        if tw == 0:
            comp_sn = sn(None, "score_0_100", method="computed", source=src("field_shift_engine"),
                         note="All weights zero or on blocked scores")
        else:
            cv = sum(active[k] * scores[k]["value"] for k in active) / tw
            cl = sum(active[k] * scores[k]["low"] for k in active) / tw
            ch = sum(active[k] * scores[k]["high"] for k in active) / tw
            comp_sn = sn(cv, "score_0_100", low=cl, high=ch, method="computed", source=src("field_shift_engine"),
                         note="sum(W_i s_i) with W_i = w_i / sum(w); low/high = same weights on score lows/highs"
                              + (f"; ignored (blocked): {ignored}" if ignored else "") + f". {RULE}", rnd=1)
        comp_sn["weights_used"] = dict(weights)

        # ---------------- constraints (filters, not scores)
        cchk = []
        filtered = False
        if constraints.get("no_new_perennials"):
            new_per = [c for c in {sp.crop["id"] for sp in tl.spans if sp.crop.get("perennial")} if c not in base_crops]
            if new_per:
                filtered = True
            cchk.append({"constraint": "no_new_perennials", "status": "conflict" if new_per else "ok",
                         "detail": f"new perennials: {new_per}" if new_per else "no new perennials"})
        if constraints.get("has_seed_drill") is False:
            need = sorted({sp.crop["id"] for sp in tl.spans if sp.crop.get("needs_drill")})
            if need:
                filtered = True
            cchk.append({"constraint": "seed_drill", "status": "conflict" if need else "ok",
                         "detail": f"needs a grain drill for {need}" if need else "no drill needed"})
        if soil and soil.get("drainage_class"):
            dc = soil["drainage_class"].lower()
            bad = sorted({sp.crop["id"] for sp in tl.spans
                          if "any" not in sp.crop["drainage_classes_ok"]["value"]
                          and dc not in [x.lower() for x in sp.crop["drainage_classes_ok"]["value"]]})
            cchk.append({"constraint": "soil_drainage", "status": "check" if bad else "ok",
                         "detail": f"SSURGO '{soil['drainage_class']}' ({soil.get('muname')}) outside the assumed "
                                   f"(U) tolerance list for {bad}" if bad else
                                   f"SSURGO '{soil['drainage_class']}' within assumed tolerance lists",
                         "source": src("ssurgo_sda")})
        for sp in tl.spans:
            sw = sp.crop.get("seeding_window")
            if not sw or sp.entry["role"] in ("water",) or sp.entry.get("note", "").startswith("Carried"):
                continue
            if (sp.entry["plant"] == "12-01" or sp.entry.get("season_boundary")) and sp.crop.get("perennial") \
                    and sp.entry["role"] == "forage":
                continue  # stand season boundary, not a seeding
            d, a, b = doy0(sp.entry["plant"]), doy0(sw["start"]), doy0(sw["end"])
            ok = a <= d <= b
            cchk.append({"constraint": "seeding_window", "status": "ok" if ok else "check",
                         "detail": f"{sp.crop['id']} planted {sp.entry['plant']}, window {sw['start']}-{sw['end']} "
                                   f"({'V' if sw.get('verified') else 'U'})"})

        # ---------------- local review / brief scaffolding (text filled by the AI chunk)
        lr = [{"item": "Every alternative rotation needs review by the grower and an adviser before anything is "
                       "seeded (spec B11).", "severity": "high"},
              {"item": "Market suitability is a table rule: confirm buyers, contracts, equipment and district/GSA "
                       "rules locally.", "severity": "medium"}]
        if ac["status"] in ("exceeds_allocation", "may_exceed_allocation"):
            lr.append({"item": f"Irrigation need {I_cy_max[0]:.0f} mm (high {I_cy_max[2]:.0f}) in the peak cycle "
                               f"year vs allocation {ac['allocation_mm']['value']:.0f} mm: "
                               f"{ac['status'].replace('_', ' ')}.",
                       "severity": "high" if ac["status"] == "exceeds_allocation" else "medium"})
        for sp in tl.spans:
            for pn in sp.crop.get("pest_notes", []):
                lr.append({"item": f"Pest note ({sp.crop['name']}): {pn}", "severity": "low"})
            for cn_ in sp.crop.get("cautions", []):
                lr.append({"item": f"{sp.crop['name']}: {cn_}", "severity": "medium"})
        if s.get("calendar_note"):
            lr.append({"item": s["calendar_note"], "severity": "medium"})
        lr = list({x["item"]: x for x in lr}.values())

        u_inputs = _count_unverified(tl, crops)
        rec = {
            "id": s["id"], "location_id": preset_id, "name": s["name"],
            **({"short_name": s["short_name"]} if s.get("short_name") else {}), "is_baseline": s["is_baseline"],
            "cycle_years": N, "calendar": s["calendar"], "allocation_rule": s.get("allocation_rule"),
            "exposure": exposure, "water": water, "scores": scores, "composite": comp_sn,
            "risk_profile": {
                "rma_share_drought": blocked("share", "rma_col", "RMA cause-of-loss files not processed yet"),
                "rma_share_excess_moisture": blocked("share", "rma_col", "RMA cause-of-loss files not processed yet"),
                "rma_share_heat": blocked("share", "rma_col", "RMA cause-of-loss files not processed yet"),
                "rma_share_other": blocked("share", "rma_col", "RMA cause-of-loss files not processed yet"),
                "rma_years": [2010, 2024], "note": "insurance history, not a forecast; not in the composite"},
            "funding": [{"program": "USDA EQIP practice 340 Cover Crop",
                         "rate_per_acre_usd": blocked("USD/acre", "eqip_340", "rate not transcribed (U)",
                                                      method="assumed"),
                         "url": src("eqip_340")["url"], "verified": False,
                         "applies": any("cover" in sp.crop["role"] for sp in tl.spans)}],
            "constraints_check": cchk, "filtered_out": filtered and not s["is_baseline"],
            "brief": {"why": [], "evidence": [], "benefits": [],
                      "gaps": ["Yield or profit modelling", "Pest or disease data", "Tile drainage",
                               "A real soil test"],
                      "local_review": lr, "explainer_cards": sorted({sp.crop["explainer_card"] for sp in tl.spans
                                                                     if sp.crop.get("explainer_card")}),
                      "llm_report": None},
            "uncertainty": {
                "dataset_disagreement": {"precip_sources_used": psrc_used, "precip_sources_missing": psrc_missing},
                "scale": {"weather": "POWER 0.5 deg cell (~50 km); NOAA stations within ~25 km where cached"},
                "agronomic_gap_count": u_inputs, "detector_disagreement_pct": None,
                "range_inputs": "Kc low/high, ETo +/-15%, precip sources, bare threshold 0.15-0.30, rain threshold "
                                "25-50 mm, rice F 300-600 mm (spec B4.12); rating, root-class and yield ranges (U) for the "
                                "rating-based scores; 2-4 years for a full pest break."},
            "model_assumptions": {
                "effective_rain_fraction": assumed(0.8, "fraction", low=0.8, high=0.8, note="spec B4.1 0.8 P (U)"),
                "i_max_mm": sn(imax, "mm/yr", method="computed", source=src("field_shift_engine"),
                               note="Normaliser for water_use (our choice)", rnd=0),
                "weather_years": list(years),
            },
        }
        if _region(preset_id) == "bc":
            bc.adapt(rec, preset_id)   # US-only text -> BC wording (rotation_engine/bc.py); CA never enters
        out.append(rec)

    _apply_ranks(out)
    return out


def _count_unverified(tl, crops) -> int:
    n = 0
    for cid in sorted(set(tl.crop_id)):
        c = crops[cid]

        def walk(x):
            nonlocal n
            if isinstance(x, dict):
                if x.get("method") == "assumed" and "value" in x:
                    n += 1
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(c)
        if c.get("stage_lengths_days") and not c["stage_lengths_days"].get("verified"):
            n += 1
    return n


def intervals_tie(a: tuple, b: tuple) -> bool:
    """Spec B4.12 tie rule: interval overlap > 50%. Our reading: overlap length / shorter interval length.
    Zero-width intervals tie when the point lies inside the other interval."""
    (la, ha), (lb, hb) = a, b
    ov = min(ha, hb) - max(la, lb)
    shorter = min(ha - la, hb - lb)
    if shorter <= 0:
        return ov >= 0
    return ov / shorter > 0.5


def _apply_ranks(recs: list[dict]) -> None:
    valid = [r for r in recs if r["composite"]["value"] is not None]
    order = sorted(valid, key=lambda r: -r["composite"]["value"])
    for i, r in enumerate(order):
        r["composite"]["rank"] = i + 1
    for r in valid:
        r["composite"]["ties_with"] = [
            o["id"] for o in valid if o is not r and intervals_tie(
                (r["composite"]["low"], r["composite"]["high"]), (o["composite"]["low"], o["composite"]["high"]))]
        r["composite"]["tie_note"] = "tie within uncertainty" if r["composite"]["ties_with"] else ""
