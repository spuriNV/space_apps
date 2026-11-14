"""score(): the single entry point (spec B3 RotationStrategy output, B4 scoring)."""
from __future__ import annotations

import copy
import itertools
import json
from functools import lru_cache

import numpy as np

from . import model
from .model import WYear, cover_metrics, water_metrics
from .observed import observed_timeline
from .sources import assumed, blocked, sn, src
from .timeline import build_timeline, doy0
from .weather import CHUNK, REPO, load_station_precip, load_weather, station_year_precip, year_weather

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
ETO_F = (1.0, 0.85, 1.15)       # +/-15% (B4.12); POWER-CIMIS bias unknown (CIMIS key blocked)
SLOPE_PCT = {
    "car_colusa_rice": assumed(0.0, "%", low=0.0, high=0.5,
                               note="Laser-levelled rice check (spec B4.4); NASADEM slope not yet supplied by "
                                    "backend/field. Cancels in E/E_baseline."),
    "caf_tulare_forage": assumed(0.5, "%", low=0.0, high=1.0,
                                 note="Flat SJV field placeholder; NASADEM slope not yet supplied by backend/field. "
                                      "Cancels in E/E_baseline."),
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
    return [copy.deepcopy(s) for s in _strategies_raw() if s["location_id"] == preset_id]


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
    used = ["NASA POWER PRECTOTCORR"]
    if any(w.p.get("noaa") is not None for w in wys):
        used.append("NOAA NCEI GHCN-Daily station mean (regional cache)")
    missing = ["GPM IMERG (Earthdata login not set up)", "CIMIS (API key)"]
    if "NOAA NCEI GHCN-Daily station mean (regional cache)" not in used:
        missing.append("NOAA NCEI (no station cache for this preset yet)")
    return used, missing


def _sn_c(v3, unit, source, note, rnd=1, **extra):
    return sn(v3[0], unit, low=v3[1], high=v3[2], method="computed", source=source, note=note, rnd=rnd, **extra)


def _ratings_mean(tl, crops, key):
    return model.crop_day_mean(tl, model.rating_day_array(tl, crops, key))


def _root_mean(tl, crops):
    arr = np.array([crops[c]["root_depth_class"]["value"] for c in tl.crop_id], dtype=float)
    return model.crop_day_mean(tl, arr)


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
        wnote = (f"{years_note}. ETc = Kc(d) x Hargreaves ETo (FAO-56 eq. 52, Kc FAO-56 Table 12 where V); range = "
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
            "openet_et_mm_season": blocked("mm/yr", "openet", "OpenET API key not available; validation line "
                                           "(spec B4.1) cannot be computed. Never a score input.", method="measured"),
            "etc_vs_openet_pct": blocked("%", "openet", "Needs OpenET season ET (key)."),
            "eto_source_note": "POWER Hargreaves only; CIMIS station ETo (key) and PM ETo [S] not used, so the "
                               "POWER-CIMIS bias that could widen the +/-15% band is unknown.",
            "by_crop": [],
        }
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
        slope = SLOPE_PCT[preset_id]
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
        fsum = 0.0
        for sp in tl.spans:
            rat = sp.crop["ratings_0_4"]["forage_harvest_value"]["value"]
            yv = sp.crop["yield_range"]["value"]
            hm = len(sp.entry.get("harvest_months", []))
            if rat and yv and hm:
                fsum += rat / 4 * hm / 12 * min(yv / 10000, 1)
        scores["forage_value"] = sn(100 * fsum / N, "score_0_100", method="computed", source=src("field_shift_engine"),
                                    note=f"spec B4.2 100 x sum(rating/4 x harvest months/12 x min(yield/10000,1)) / "
                                         f"cycle_years; ratings and yields U. {RULE}", rnd=1)
        # N fixation (B4.3)
        nf = model.rating_day_array(tl, crops, "nitrogen_fixation")
        leg = np.array([crops[c]["legume"] for c in tl.crop_id])
        scores["n_fixation"] = sn(100 * float((nf * leg).sum()) / 4 / 365 / N, "score_0_100", method="computed",
                                  source=src("field_shift_engine"),
                                  note=f"spec B4.3 100 x sum(rating_nfix/4 x months growing/12)/cycle_years, "
                                       f"legumes only; ratings U. {RULE}", rnd=1)
        # erosion (B4.4)
        resid = _ratings_mean(tl, crops, "lasting_residue")

        def ero(c):
            E, Eb = C[c]["E"], Wb[c]["E"]
            expo = 0.0 if (Eb == 0 and E == 0) else (-np.inf if Eb == 0 else 100 * (1 - E / Eb))
            return _clamp(0.7 * _clamp(expo) + 0.3 * 100 * resid / 4)

        def ero_raw(c):
            E, Eb = C[c]["E"], Wb[c]["E"]
            return None if Eb == 0 else 100 * (1 - E / Eb)

        er = (ero(cn), min(ero(c) for c in C), max(ero(c) for c in C))
        raw = ero_raw(cn)
        scores["erosion"] = _sn_c(er, "score_0_100", wsrc,
                                  f"spec B4.4: 0.7 x 100 x (1 - E/E_baseline) [clamped 0-100; unclamped nominal = "
                                  f"{'undefined (E_baseline = 0)' if raw is None else f'{raw:.1f}'}] + 0.3 x 100 x "
                                  f"lasting_residue/4 (crop-day mean {resid:.2f}, U). {RULE}",
                                  exposure_component=_sn_c(
                                      tuple(_clamp(x) if x is not None else None for x in
                                            (raw, min((ero_raw(c) for c in C if ero_raw(c) is not None), default=None),
                                             max((ero_raw(c) for c in C if ero_raw(c) is not None), default=None))),
                                      "score_0_100", wsrc, "100 x (1 - E/E_baseline), clamped; 0 for the baseline"),
                                  slope_pct=slope)
        # organic matter (B4.5)
        sb = _ratings_mean(tl, crops, "soil_builder")
        perennial_years = sum(len(sp.idx) for sp in tl.spans if sp.crop.get("perennial")) / 365

        def om(c):
            return 100 * (0.5 * (sb + resid) / 2 / 4 + 0.3 * perennial_years / N + 0.2 * (1 - C[c]["bare_days"] / 365))

        scores["organic_matter"] = _sn_c((om(cn), min(map(om, C)), max(map(om, C))), "score_0_100",
                                         src("field_shift_engine"),
                                         f"spec B4.5; soil_builder {sb:.2f}, lasting_residue {resid:.2f} (crop-day "
                                         f"means, U), perennial years {perennial_years:.2f}/{N}. {RULE}")
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
        distinct = len(set().union(*fy))
        run = model.max_consecutive_run(fy)
        scores["pest_break"] = sn(100 * min(1, distinct / 3) * (1 - run / N), "score_0_100", method="computed",
                                  source=src("field_shift_engine"),
                                  note=f"spec B4.7: families {sorted(set().union(*fy))}, longest same-family run "
                                       f"{run}/{N} years. Any family present every cycle year scores 0. No pest "
                                       f"dataset exists. {RULE}", rnd=1)
        # infiltration (B4.8)
        comp = _ratings_mean(tl, crops, "compaction_reduction")
        rootc = _root_mean(tl, crops)
        cover_months = float((tl.cover >= 0.5).sum()) / N / model.DAYS_PER_MONTH
        hg = (soil or {}).get("hydrologic_group")
        scores["infiltration"] = sn(100 * (0.5 * comp / 4 + 0.3 * rootc / 2 + 0.2 * min(cover_months, 12) / 12),
                                    "score_0_100", method="computed", source=src("field_shift_engine"),
                                    note=f"spec B4.8; compaction {comp:.2f}, root class {rootc:.2f} (U), cover months "
                                         f"{cover_months:.1f}. SSURGO hydrologic group {hg or 'unknown'}"
                                         f"{': low intrinsic infiltration; rotation effect limited' if hg == 'D' else ''}"
                                         f". {RULE}", rnd=1)
        # N scavenging (B4.9)
        ns = model.rating_day_array(tl, crops, "nitrogen_scavenging")
        fw = np.isin(tl.month, model.FW_MONTHS) & (tl.cover >= 0.5)
        fw_months = float(fw.sum()) / N / model.DAYS_PER_MONTH
        nsv = 100 * float((ns * fw).sum()) / N / model.DAYS_PER_MONTH / 4 / 6
        scores["n_scavenging"] = sn(min(100, nsv), "score_0_100", method="computed", source=src("field_shift_engine"),
                                    note=f"spec B4.9 100 x rating/4 x fall-winter cover months/6, computed day by "
                                         f"day over Oct-Mar with cover >= 0.5 ({fw_months:.1f} months); ratings U. "
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
            if sp.entry["plant"] == "12-01" and sp.crop.get("perennial") and sp.entry["role"] == "forage":
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
            "id": s["id"], "location_id": preset_id, "name": s["name"], "is_baseline": s["is_baseline"],
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
                                "25-50 mm, rice F 300-600 mm (spec B4.12). Rating/yield ranges are NOT propagated."},
            "model_assumptions": {
                "effective_rain_fraction": assumed(0.8, "fraction", low=0.8, high=0.8, note="spec B4.1 0.8 P (U)"),
                "i_max_mm": sn(imax, "mm/yr", method="computed", source=src("field_shift_engine"),
                               note="Normaliser for water_use (our choice)", rnd=0),
                "weather_years": list(years),
            },
        }
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
