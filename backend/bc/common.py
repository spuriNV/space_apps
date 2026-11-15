"""Shared paths and helpers for the BC chunk (backend/bc). Stdlib + pandas only."""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FID = "bc_salmon_river_forage"
CACHE = REPO / "data" / "cache" / FID
POLY = REPO / "backend" / "field" / "polygons" / f"{FID}.geojson"
FIELD_OUT = REPO / "backend" / "field" / "out" / FID
API_OUT = REPO / "backend" / "api" / "out" / FID
OUT = HERE / "out"
ACCESSED = dt.date.today().isoformat()
UA = {"User-Agent": "CropLytics NASA Space Apps 2026 (backend/bc; research use)"}

sys.path.insert(0, str(REPO / "backend" / "fields"))
import fieldreg  # noqa: E402


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str, params=None, timeout=120, retries=4, **kw) -> requests.Response:
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers=UA, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code} {r.text[:120]}")
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (i + 1))
    raise last


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str) + "\n")


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def field_entry() -> dict:
    return fieldreg.get(FID)


def polygon():
    """(shapely geometry EPSG:4326, properties) of the BC field outline."""
    from shapely.geometry import shape
    f = read_json(POLY)["features"][0]
    return shape(f["geometry"]), f["properties"]
