"""Shared paths, presets and small helpers for the field-data chunk."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from pyproj import Transformer

FIELD_DIR = Path(__file__).resolve().parents[1]
REPO = FIELD_DIR.parents[1]
POLY_DIR = FIELD_DIR / "polygons"
OUT_DIR = FIELD_DIR / "out"
CACHE_DIR = REPO / "data" / "cache"

WORK_CRS = "EPSG:32610"  # contract: working CRS UTM 10N
CDL_CRS = "EPSG:5070"  # CDL native CONUS Albers

PRESETS = {
    "car_colusa_rice": {
        "name": "Colusa County rice check (example)",
        "centre": (-122.10, 39.15),
        "target_ha": 60.0,
    },
    "caf_tulare_forage": {
        "name": "Tulare/Kings forage field (example)",
        "centre": (-119.60, 36.20),
        "target_ha": 32.0,
    },
}


def today() -> str:
    return dt.date.today().isoformat()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def cache(preset: str) -> Path:
    p = CACHE_DIR / preset
    (p / "rasters").mkdir(parents=True, exist_ok=True)
    return p


def out(preset: str) -> Path:
    p = OUT_DIR / preset
    p.mkdir(parents=True, exist_ok=True)
    return p


def to_crs(src: str, dst: str) -> Transformer:
    return Transformer.from_crs(src, dst, always_xy=True)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def load_polygon(preset: str):
    """Return (shapely geometry in EPSG:4326, feature properties)."""
    from shapely.geometry import shape

    fc = read_json(POLY_DIR / f"{preset}.geojson")
    f = fc["features"][0]
    return shape(f["geometry"]), f["properties"]


def polygon_in(preset: str, crs: str):
    from shapely.ops import transform

    g, _ = load_polygon(preset)
    t = to_crs("EPSG:4326", crs)
    return transform(t.transform, g)
