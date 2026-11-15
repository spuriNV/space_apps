"""British Columbia post-pass (region "bc", e.g. bc_salmon_river_forage).

score() builds every record the California way, then, for a BC field only, `adapt()` rewrites the US-only parts:
RMA insurance, EQIP funding, NASS/AMS income notes, OpenET, CIMIS/NOAA labels, the ETo note and the
district/GSA review item. The "not available" reasons come from the field registry (backend/fields/registry.json,
`not_available`). California output never passes through this module.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache

from .sources import assumed, blocked
from .weather import REPO, fieldreg, load_station_precip

ETO_NOTE_BC = ("ETo = FAO-56 Penman-Monteith (eq. 6) with ECCC station Tmax/Tmin (mean of Salmon Arm CS 116FRMN and "
               "Silver Creek 1167337, which closed in 2021; POWER on days neither reports) and POWER radiation, "
               "humidity (ea, eq. 19) and wind. The POWER cell sits at about 1,025 m against a field at about 450 m, "
               "so POWER temperatures read cold; that is why the station temperatures drive ETo. CIMIS is a "
               "California network and does not apply in BC. Risk days (frost, heat) still use POWER Tmax/Tmin and "
               "therefore overstate frost and understate heat here.")
DRY_CA = (" In the dry Central Valley summer nearly every day qualifies, so this mostly counts bare summer days.")
RAIN_CA = ("Extreme rain: P >= 25 mm/day or 3-day >= 75 mm (U); range: threshold 25-50 mm (3-day = 3x) and precip "
           "sources.")
RAIN_FALLBACK = (13.5, 11.1, 16.0)   # Salmon Arm CS + Silver Creek, 1991-2026, if the station cache is missing

# California hay price stand-in (no BC hay price series is wired in). USDA AMS report slug 2904 is cached for the
# Kings/Tulare field; "North Inter-Mountains" (Modoc/Siskiyou/Lassen) is the coolest California hay region, the
# closest climate analogue to the Shuswap. All of this is an assumption (U).
AMS_FILE = "data/cache/caf_tulare_forage/ams.parquet"
AMS_REGION = "North Inter-Mountains"
AMS_CLASSES = ("Alfalfa", "Alfalfa/Orchard Mix", "Alfalfa/Grass Mix")
AMS_YEARS = (2021, 2025)
CAD_PER_USD = 1.37        # assumed: about the Bank of Canada 2024 annual average (1.3698 CAD per USD), not today's rate
SHORT_TON_T = 0.907185    # tonnes per US short ton


def _na(preset_id: str, kind: str) -> str:
    return (fieldreg.get(preset_id).get("not_available") or {}).get(kind, f"{kind} is not available in BC.")


def _eccc_meta(preset_id: str) -> dict:
    p = REPO / "data" / "cache" / preset_id / "eccc.meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def station_labels(preset_id: str) -> list[str]:
    """'SALMON ARM CS (116FRMN, 9 km, 1991-2026)' style labels from eccc.meta.json."""
    lon, lat = fieldreg.point(preset_id)
    out = []
    for st in _eccc_meta(preset_id).get("selected_stations", []):
        d = _km(lat, lon, st["lat"], st["lon"]) if st.get("lat") is not None else None
        yrs = f"{str(st.get('first', ''))[:4]}-{str(st.get('last', ''))[:4]}"
        out.append(f"{st.get('name', st['station']).title().replace(' Cs', ' CS')} ({st['station']}"
                   + (f", {d:.0f} km" if d is not None else "") + f", {yrs})")
    return out


@lru_cache(maxsize=8)
def rain_thr(preset_id: str) -> tuple[float, float, float]:
    """BC extreme-rain threshold (nominal, low, high) in mm/day: the 99th percentile of daily ECCC station
    precipitation (all days with a report), range the 98th-99.5th percentiles (assumed, U). The California rule
    (25 mm) fires on about 13 days in 35 years at Salmon Arm, so every BC rotation scored the same erosion (50)."""
    sp = load_station_precip(preset_id)
    if sp is None:
        return RAIN_FALLBACK
    p = sp.series.dropna()
    if len(p) < 3650:
        return RAIN_FALLBACK
    q = lambda x: round(float(p.quantile(x)), 1)  # noqa: E731
    return (q(0.99), q(0.98), q(0.995))


def rain_note(preset_id: str) -> str:
    t = rain_thr(preset_id)
    return (f"Extreme rain (BC): P >= {t[0]:g} mm/day or 3-day >= {3 * t[0]:g} mm, where {t[0]:g} mm is the 99th "
            f"percentile of daily ECCC station precipitation (Salmon Arm CS + Silver Creek, 1991 on); range: "
            f"{t[1]:g}-{t[2]:g} mm (98th-99.5th percentiles, assumed U) and precip sources. The California 25 mm "
            f"threshold almost never triggers here.")


@lru_cache(maxsize=1)
def hay_price_cad_t() -> dict | None:
    """California hay price stand-in, CAD per tonne: median / 10th / 90th percentile of the AMS weighted-average
    F.O.B. prices for alfalfa and alfalfa-grass hay in North Inter-Mountains, 2021-2025."""
    import pandas as pd  # noqa: PLC0415

    f = REPO / AMS_FILE
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    meta_f = f.with_name("ams.meta.json")
    meta = json.loads(meta_f.read_text()) if meta_f.exists() else {}
    df["p"] = pd.to_numeric(df["wtd_Avg_Price"], errors="coerce")
    df["y"] = pd.to_datetime(df["report_end_date"], errors="coerce").dt.year
    a = df[df["class"].isin(AMS_CLASSES) & (df["freight"] == "F.O.B.") & (df["region"] == AMS_REGION)
           & (df["price_Unit"] == "Per Ton") & df["y"].between(*AMS_YEARS) & df["p"].notna()]
    if len(a) < 20:
        return None
    conv = CAD_PER_USD / SHORT_TON_T
    usd = {k: float(a["p"].quantile(q)) for k, q in (("value", 0.5), ("low", 0.1), ("high", 0.9))}
    return {"cad_t": {k: round(v * conv, 0) for k, v in usd.items()}, "usd_ton": usd, "n": int(len(a)),
            "url": meta.get("url", "https://marsapi.ams.usda.gov/services/v1.2/reports"),
            "accessed": str(meta.get("fetched_at", ""))[:10]}


def psources(preset_id: str, wys) -> tuple[list, list]:
    used = ["NASA POWER PRECTOTCORR"]
    if any(w.p.get("noaa") is not None for w in wys):
        used.append("ECCC daily station mean: " + "; ".join(station_labels(preset_id)))
    missing = ["GPM IMERG (Earthdata login not set up)",
               "CIMIS (not applicable in BC: " + _na(preset_id, "cimis") + ")",
               "NOAA NCEI GHCN-Daily (not applicable in BC)"]
    if len(used) == 1:
        missing.insert(1, "ECCC daily stations (no year with >= 95% coverage)")
    return used, missing


def _replace_text(x, old: str, new: str):
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(v, str) and old in v:
                x[k] = v.replace(old, new)
            else:
                _replace_text(v, old, new)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            if isinstance(v, str) and old in v:
                x[i] = v.replace(old, new)
            else:
                _replace_text(v, old, new)


def adapt(rec: dict, preset_id: str) -> None:
    """Rewrite one RotationStrategy record for a BC field, in place."""
    rec["region"] = "bc"
    ins = _na(preset_id, "insurance")
    rp = rec["risk_profile"]
    for k in [k for k in rp if k.startswith("rma_share_")]:
        rp[k] = blocked("share", "rma_col", "Not available in BC. " + ins)
    rp["rma_years"] = []
    rp["note"] = "Not available in BC: " + ins

    rec["funding"] = [{"program": "BC programs (unverified)", "rate_per_acre_usd": None, "url": None,
                       "verified": False, "applies": None,
                       "note": "USDA EQIP is a US program and does not apply in BC. Provincial and federal programs "
                               "(for example the BC Environmental Farm Plan and its Beneficial Management Practices "
                               "funding) were not checked for eligibility or rates."}]

    inc = rec["scores"]["income"]
    seed = inc["components"]["seed_cost_per_ha"]
    hp = hay_price_cad_t()
    if hp:
        c = hp["cad_t"]
        price_note = (f"ESTIMATE, California stand-in: USDA AMS California hay report (slug 2904), {AMS_REGION} region, "
                      f"F.O.B. weighted-average prices for {', '.join(AMS_CLASSES)}, {AMS_YEARS[0]}-{AMS_YEARS[1]} "
                      f"({hp['n']} quotes): median {hp['usd_ton']['value']:.0f} USD/short ton (10th-90th percentile "
                      f"{hp['usd_ton']['low']:.0f}-{hp['usd_ton']['high']:.0f}). Converted at an assumed "
                      f"{CAD_PER_USD} CAD per USD (about the Bank of Canada 2024 annual average, 1.3698; rate as of "
                      f"2024, not checked for Nov 2026) and {SHORT_TON_T} t per short ton. Not a BC price: no BC hay "
                      "price series is wired in.")
        inc["components"]["price_range"] = assumed(c["value"], "CAD/t", low=c["low"], high=c["high"], note=price_note)
        inc["components"]["price_range"]["source"] = {
            "id": "ams_mymarketnews", "title": "USDA AMS My Market News California hay report (slug 2904), used as a "
            "stand-in for BC", "url": hp["url"], "accessed": hp["accessed"], "verified": False}
        price_txt = (f"Hay price stand-in: about {c['value']:.0f} CAD/t ({c['low']:.0f}-{c['high']:.0f}), from "
                     "California AMS prices (estimate, see price_range).")
    else:
        inc["components"]["price_range"] = blocked("CAD/t", "ams_mymarketnews", "No hay price series for BC")
        price_txt = "No BC hay or silage price series was read."
    inc["note"] = ("Income not computed (as for the California fields): NASS/AMS do not cover BC and no BC yield-price "
                   f"series is wired in. {price_txt} Seed cost alone (assumed, U) would be "
                   f"~{seed['value']:.0f} USD/ha/yr.")
    inc["components"].pop("eqip_340_rate", None)

    oe = _na(preset_id, "openet")
    w = rec["water"]
    w["openet_et_mm_season"] = blocked("mm/yr", "openet", "OpenET not available in BC. " + oe, method="measured")
    w["etc_vs_openet_pct"] = blocked("%", "openet", "OpenET not available in BC. " + oe)
    w["eto_source_note"] = ETO_NOTE_BC

    labels = "; ".join(station_labels(preset_id)) or "ECCC stations"
    rec["uncertainty"]["scale"] = {
        "weather": f"POWER 0.5 deg cell (~50 km; cell elevation ~1,025 m vs the field's ~450 m); ECCC stations "
                   f"{labels}. Sparse stations: Salmon Arm CS is the only active daily station near the valley."}

    _replace_text(rec, DRY_CA, "")
    _replace_text(rec, RAIN_CA, rain_note(preset_id))
    t = rain_thr(preset_id)
    _replace_text(rec, "rain threshold 25-50 mm", f"rain threshold {t[1]:g}-{t[2]:g} mm (BC: station 98th-99.5th "
                                                  "percentile)")
    _replace_text(rec, "SSURGO hydrologic group unknown",
                  "Hydrologic group unknown (" + _na(preset_id, "soil_survey") + ")")
    for it in rec["brief"]["local_review"]:
        it["item"] = it["item"].replace(
            "district/GSA rules",
            "the field's water licence terms under BC's Water Sustainability Act (including fish population "
            "protection orders such as the Aug 2023 Salmon River order)")
    rec["brief"]["gaps"] = rec["brief"]["gaps"] + ["Field-scale measured water use (no OpenET in BC)",
                                                   "Crop insurance history (no public BC loss data)"]
    rec["brief"]["not_available_in_bc"] = dict(fieldreg.get(preset_id).get("not_available") or {})
