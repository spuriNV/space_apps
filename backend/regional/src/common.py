"""Shared helpers for the regional-data chunk."""
import json, datetime as dt
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "cache"
OUT = Path(__file__).resolve().parents[1] / "out"
# Field list from backend/fields/registry.json (FIELDSHIFT_FIELDS limits it). lat/lon = point for POWER and the NOAA
# station search: the spec centre for the original two, the polygon centroid for the others.
import sys as _sys
_sys.path.insert(0, str(ROOT / "backend" / "fields"))
import fieldreg  # noqa: E402
PRESETS = {}
for _id in fieldreg.selected():
    _f = fieldreg.get(_id)
    _lon, _lat = fieldreg.point(_id)
    PRESETS[_id] = {"lat": _lat, "lon": _lon, "counties": [(_f["county"]["fips"], _f["county"]["name"])],
                    "usdm_counties": _f["usdm_counties"], "reservoirs": _f["reservoirs"],
                    "ncei_stations": _f.get("ncei_stations"), "family": _f["family"]}


def power_cell(lat, lon):
    """POWER point requests return the containing MERRA-2 cell (0.5 deg lat x 0.625 deg lon); fields in the same
    cell get identical series, so the series is fetched once per cell."""
    import math
    return (math.floor((lat + 90) / 0.5), math.floor((lon + 180) / 0.625))
UA = {"User-Agent": "field-shift-hackathon/0.1 (regional data fetch)"}

def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get(url, params=None, retries=3, timeout=180, headers=None, **kw):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={**UA, **(headers or {})}, **kw)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
    raise last

def write_json(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str))

def cache_dir(pid):
    d = CACHE / pid; d.mkdir(parents=True, exist_ok=True); return d
