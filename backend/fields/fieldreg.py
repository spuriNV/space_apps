"""Field registry: the list of real fields every chunk works on (stdlib only).

backend/fields/registry.json holds one entry per field. Chunks read it with

    sys.path.insert(0, str(REPO / "backend" / "fields")); import fieldreg
    fieldreg.ids()                    # every field id, registry order (the original two first)
    fieldreg.ids(family="rice")       # rice | forage
    fieldreg.get(fid)                 # the entry (dict)
    fieldreg.template(fid)            # the original field whose rotation set / trained model this field reuses

Field ids keep the original prefixes: car_* = rice (CAR rotation set), caf_* = forage (CAF rotation set).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REGISTRY = HERE / "registry.json"
TEMPLATES = {"rice": "car_colusa_rice", "forage": "caf_tulare_forage"}


@lru_cache(maxsize=1)
def _load() -> tuple:
    return tuple(json.loads(REGISTRY.read_text())["fields"])


def fields(family: str | None = None, county: str | None = None) -> list[dict]:
    """Entries, optionally filtered by family (rice|forage) and county (name or 5-digit FIPS, case-insensitive)."""
    out = []
    for f in _load():
        if family and f["family"] != family.lower():
            continue
        if county:
            c = county.strip().lower().removesuffix(" county")
            if c not in (f["county"]["name"].lower(), f["county"]["fips"], f["county"]["fips"][2:]):
                continue
        out.append(f)
    return out


def ids(family: str | None = None) -> list[str]:
    return [f["id"] for f in fields(family)]


def selected(family: str | None = None) -> list[str]:
    """Registry ids, limited to the comma-separated FIELDSHIFT_FIELDS env var when it is set (run_all.py sets it so a
    chunk script only works on the fields that still need a step). Unknown ids are an error."""
    env = os.environ.get("FIELDSHIFT_FIELDS", "").strip()
    all_ids = ids(family)
    if not env:
        return all_ids
    want = [x.strip() for x in env.split(",") if x.strip()]
    bad = [x for x in want if not has(x)]
    if bad:
        raise KeyError(f"FIELDSHIFT_FIELDS has ids not in the registry: {bad}")
    return [x for x in all_ids if x in want]


def get(fid: str) -> dict:
    for f in _load():
        if f["id"] == fid:
            return f
    raise KeyError(f"{fid} is not in {REGISTRY}")


def has(fid: str) -> bool:
    return any(f["id"] == fid for f in _load())


def template(fid: str) -> str:
    return TEMPLATES[get(fid)["family"]]


def is_original(fid: str) -> bool:
    return fid in TEMPLATES.values()


def point(fid: str) -> tuple[float, float]:
    """(lon, lat) used for point weather requests (POWER, NOAA station search). For the original two this is the
    spec centre their caches were fetched at; for the others it is the polygon centroid."""
    f = get(fid)
    return tuple(f.get("weather_point") or (f["centroid"]["lon"], f["centroid"]["lat"]))
