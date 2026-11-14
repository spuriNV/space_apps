"""Shared helpers for the outlook chunk."""
import json, datetime as dt
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
RAW = HERE / "raw"
OUT = HERE / "out"
CACHE = ROOT / "data" / "cache"
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]
COUNTY = {"car_colusa_rice": ("06011", "Colusa"), "caf_tulare_forage": ("06031", "Kings")}
RESERVOIRS = {"car_colusa_rice": ["SHA", "ORO"], "caf_tulare_forage": ["PNF"]}
UA = {"User-Agent": "field-shift-hackathon/0.1 (outlook fetch)"}
LABEL = "Outlook, not a forecast"

def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get(url, params=None, retries=3, timeout=120, headers=None, **kw):
    last = None
    for _ in range(retries):
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

def read_json(path):
    return json.loads(Path(path).read_text())

def sn(value, unit, url, title, fetched_at, verified=True, low=None, high=None,
       method="lookup", note=None, sid=None):
    """SourcedNumber (schemas/sourced_number.schema.json) plus a top-level fetched_at."""
    d = {"value": value, "unit": unit, "method": method, "fetched_at": fetched_at, "verified": verified,
         "source": {"id": sid or title.lower().replace(" ", "_")[:40], "title": title, "url": url,
                    "accessed": fetched_at, "verified": verified}}
    if low is not None: d["low"] = low
    if high is not None: d["high"] = high
    if note: d["note"] = note
    return d

def centroid(pid):
    g = read_json(ROOT / "backend/field/polygons" / f"{pid}.geojson")
    c = g["features"][0]["properties"]["centroid"]
    return c["lon"], c["lat"]
