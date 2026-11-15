"""Shared paths, presets and small helpers for the field-data chunk."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from pyproj import Transformer

FIELD_DIR = Path(__file__).resolve().parents[1]
REPO = FIELD_DIR.parents[1]
POLY_DIR = FIELD_DIR / "polygons"
OUT_DIR = FIELD_DIR / "out"
CACHE_DIR = REPO / "data" / "cache"

WORK_CRS = "EPSG:32610"  # contract: working CRS UTM 10N
CDL_CRS = "EPSG:5070"  # CDL native CONUS Albers

# Field list from the registry (backend/fields/registry.json); the original two keep their spec centres.
sys.path.insert(0, str(REPO / "backend" / "fields"))
import fieldreg  # noqa: E402

PRESETS = {
    f["id"]: {
        "name": f["name"],
        "centre": tuple(f["search_centre"] or (f["centroid"]["lon"], f["centroid"]["lat"])),
        "target_ha": f["target_ha"] or f["area_ha"],
        "half_box_m": f["cdl_half_box_m"],
        "family": f["family"],
        "dwr_unique_id": f["dwr_unique_id"],
        "original": f["original"],
    }
    for f in fieldreg.fields(region=None) if f["id"] in fieldreg.selected()   # BC only when FIELDSHIFT_FIELDS names it
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
