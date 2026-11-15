"""Coming-season outlook for a freeform point: nearest prepared CA field that has outlook.json.

CPC seasonal outlooks are regional (tens of miles), so the nearest prepared field's file is a fair stand-in
for a tapped or drawn field in California. BC and points outside CA return None (caller shows the region gap).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "backend" / "outlook" / "out"
CA_BOX = (-124.5, 32.4, -114.0, 42.1)  # lon/lat


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def nearest_ca_outlook(lat: float, lon: float) -> dict | None:
    """Return outlook.json for the nearest CA prepared field, or None if outside CA / nothing built."""
    if not (CA_BOX[0] <= lon <= CA_BOX[2] and CA_BOX[1] <= lat <= CA_BOX[3]):
        return None
    cpc_path = OUT / "cpc.json"
    if not cpc_path.is_file():
        return None
    cpc = json.loads(cpc_path.read_text())
    best_pid, best_km = None, 1e99
    for pid, p in (cpc.get("presets") or {}).items():
        f = OUT / pid / "outlook.json"
        if not f.is_file():
            continue
        pt = p.get("point") or {}
        plat, plon = pt.get("lat"), pt.get("lon")
        if plat is None or plon is None:
            continue
        km = _haversine_km(lat, lon, float(plat), float(plon))
        if km < best_km:
            best_km, best_pid = km, pid
    if not best_pid:
        return None
    d = dict(json.loads((OUT / best_pid / "outlook.json").read_text()))
    d["nearest_preset"] = best_pid
    d["nearest_km"] = round(best_km, 1)
    d["for_freeform"] = True
    d["note"] = (
        f"Winter outlook from the nearest prepared field ({best_pid}, about {best_km * 0.621:.0f} mi away). "
        "CPC outlooks cover a wide area, not one field."
    )
    d["_source"] = "real"
    return d
