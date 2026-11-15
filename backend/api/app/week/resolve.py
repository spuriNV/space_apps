"""resolve_location(id): one place that turns any location id into what this_week needs.

Returns a dict {id, kind, lat, lon, region ("ca"|"bc"|"other"), family ("rice"|"forage"|"other"), template (the engine
location whose rotation set is the baseline), acres, name, tz_hint} or None.

Hook for other id families (the `my_` fields): call `register_resolver(fn)` once at import time, where `fn(id) -> dict | None`
returns the same keys (None = not mine). Custom resolvers run first. Nothing else in this package needs to change."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(os.environ.get("FIELDSHIFT_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "backend" / "fields"))
import fieldreg  # noqa: E402

_RESOLVERS: list[Callable[[str], dict | None]] = []
TEMPLATES = {"rice": "car_colusa_rice", "forage": "caf_tulare_forage", "other": "caf_tulare_forage"}


def register_resolver(fn: Callable[[str], dict | None]) -> None:
    """Add a resolver for another id family. It must return None for ids that are not its own."""
    if fn not in _RESOLVERS:
        _RESOLVERS.append(fn)


def _preset(pid: str) -> dict | None:
    if not fieldreg.has(pid):
        return None
    f = fieldreg.get(pid)
    lon, lat = fieldreg.point(pid)
    return {"id": pid, "kind": "preset", "lat": lat, "lon": lon, "region": fieldreg.region(pid), "family": f["family"],
            "template": fieldreg.template(pid), "acres": f.get("acres"), "name": f.get("name") or pid}


def _point(pid: str) -> dict | None:
    if not pid.startswith("pt_"):
        return None
    from ..anyloc import build as B, load_point  # noqa: PLC0415  (anyloc is imported, never modified)
    p = B.parse_id(pid)
    if p is None:
        return None
    lat, lon = p
    fam, region, name, acres = "other", "other", f"Spot at {lat:.4f}, {lon:.4f}", None
    try:
        hit = load_point(pid)            # the analysed spot's cached location, if someone already tapped it
    except Exception:  # noqa: BLE001
        hit = None
    if hit:
        loc = hit[0]
        fam, region = loc.get("family", fam), loc.get("region", region)
        name, acres = loc.get("farmer_name") or name, loc.get("acres")
    return {"id": pid, "kind": "point", "lat": lat, "lon": lon, "region": region, "family": fam,
            "template": TEMPLATES.get(fam, TEMPLATES["other"]), "acres": acres, "name": name,
            "crop_known": bool(hit) and fam != "other"}


def resolve_location(pid: str) -> dict | None:
    for fn in (*_RESOLVERS, _preset, _point):
        try:
            r = fn(pid)
        except Exception:  # noqa: BLE001  a broken resolver must not take the others down
            r = None
        if r:
            r.setdefault("kind", "custom")
            r.setdefault("crop_known", True)
            r.setdefault("template", TEMPLATES.get(r.get("family"), TEMPLATES["other"]))
            return r
    return None
