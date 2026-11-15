"""British Columbia post-pass (region "bc", e.g. bc_salmon_river_forage).

score() builds every record the California way, then, for a BC field only, `adapt()` rewrites the US-only parts:
RMA insurance, EQIP funding, NASS/AMS income notes, OpenET, CIMIS/NOAA labels, the ETo note and the
district/GSA review item. The "not available" reasons come from the field registry (backend/fields/registry.json,
`not_available`). California output never passes through this module.
"""
from __future__ import annotations

import json
import math

from .sources import blocked
from .weather import REPO, fieldreg

ETO_NOTE_BC = ("ETo = FAO-56 Penman-Monteith (eq. 6) with ECCC station Tmax/Tmin (mean of Salmon Arm CS 116FRMN and "
               "Silver Creek 1167337, which closed in 2021; POWER on days neither reports) and POWER radiation, "
               "humidity (ea, eq. 19) and wind. The POWER cell sits at about 1,025 m against a field at about 450 m, "
               "so POWER temperatures read cold; that is why the station temperatures drive ETo. CIMIS is a "
               "California network and does not apply in BC. Risk days (frost, heat) still use POWER Tmax/Tmin and "
               "therefore overstate frost and understate heat here.")
DRY_CA = (" In the dry Central Valley summer nearly every day qualifies, so this mostly counts bare summer days.")


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
    inc["note"] = ("BLOCKED: NASS/AMS prices not available in BC (USDA Quick Stats and My Market News cover the US). "
                   f"No BC hay or silage price series was read. Seed cost alone (assumed, U) would be "
                   f"~{seed['value']:.0f} USD/ha/yr.")
    inc["components"]["price_range"] = blocked("USD/unit", "ams_mymarketnews",
                                               "NASS/AMS prices not available in BC")
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
