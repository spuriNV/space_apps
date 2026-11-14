"""Shared helpers for the regional-data chunk."""
import json, datetime as dt
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "cache"
OUT = Path(__file__).resolve().parents[1] / "out"
PRESETS = {
    "car_colusa_rice": {"lat": 39.15, "lon": -122.10, "counties": [("06011", "Colusa")]},
    "caf_tulare_forage": {"lat": 36.20, "lon": -119.60, "counties": []},  # filled by county lookup
}
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
