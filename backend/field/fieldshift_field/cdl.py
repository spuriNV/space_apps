"""USDA NASS Cropland Data Layer (CDL) for a box around each preset.

Source: USDA CroplandCROS ArcGIS ImageServer `CDL_WM` (no account). It holds the
national CDL mosaics 1997-2025 (30 m to 2023, 10 m for 2024 and 2025). We lock
the mosaic to one year's raster and export a clipped GeoTIFF in the CDL's native
CONUS Albers (EPSG:5070), on the CDL pixel grid, nearest-neighbour, so pixel
values are the original class codes. Class names come from the service's raster
attribute table (read from the product, not from the spec).

Microsoft Planetary Computer `usda-cdl` was checked first: it only covers
2008-2021, which misses the 2022 fallow year, so it is not used.

Usage: uv run python -m fieldshift_field.cdl [preset ...]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import rasterio
from rasterio.io import MemoryFile

from .common import CDL_CRS, PRESETS, cache, now, to_crs, write_json

SERVICE = "https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer"
FIRST_YEAR = 2008
HALF_BOX_M = 8000  # 16 km box around the preset centre (covers the 10 km training box)
GRID_ORIGIN = 15.0  # CDL Albers pixel edges sit at 15 + 30k metres (also 5 + 10k for 10 m years)


def _get(url: str, params: dict, timeout=180) -> bytes:
    full = url + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(full, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # network hiccups: retry with backoff
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"GET failed {full}: {last}")


def catalog() -> dict[int, dict]:
    """Year -> {id, name, res_m} for 30 m / 10 m national CDLs."""
    d = json.loads(_get(SERVICE + "/query", {
        "where": "1=1", "outFields": "OBJECTID,Name,Year", "returnGeometry": "false", "f": "json"}))
    out = {}
    for f in d["features"]:
        a = f["attributes"]
        name = a["Name"]
        if "_56m_" in name:
            continue
        res = 10 if "_10m_" in name else 30
        out[int(a["Year"])] = {"id": a["OBJECTID"], "name": name, "res_m": res}
    return out


def legend() -> dict[int, dict]:
    d = json.loads(_get(SERVICE + "/rasterAttributeTable", {"f": "json"}))
    leg = {}
    for f in d["features"]:
        a = f["attributes"]
        if a.get("Class_Names"):
            leg[int(a["Value"])] = {"name": a["Class_Names"], "rgb": [a["Red"], a["Green"], a["Blue"]]}
    return leg


def box_5070(preset: str, half=HALF_BOX_M):
    lon, lat = PRESETS[preset]["centre"]
    x, y = to_crs("EPSG:4326", CDL_CRS).transform(lon, lat)
    snap = lambda v: GRID_ORIGIN + 30 * round((v - GRID_ORIGIN) / 30)
    return snap(x - half), snap(y - half), snap(x + half), snap(y + half)


def export_year(bbox, year_info) -> tuple[np.ndarray, dict]:
    xmin, ymin, xmax, ymax = bbox
    res = year_info["res_m"]
    w, h = int(round((xmax - xmin) / res)), int(round((ymax - ymin) / res))
    params = {
        "bbox": f"{xmin},{ymin},{xmax},{ymax}", "bboxSR": 5070, "imageSR": 5070,
        "size": f"{w},{h}", "format": "tiff", "pixelType": "U8",
        "interpolation": "RSP_NearestNeighbor", "noData": 0,
        "mosaicRule": json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [year_info["id"]]}),
        "f": "image",
    }
    raw = _get(SERVICE + "/exportImage", params)
    with MemoryFile(raw) as mf, mf.open() as src:
        arr = src.read(1)
        prof = src.profile
    return arr, {"crs": str(prof["crs"]), "transform": list(prof["transform"])[:6], "res_m": res}


def fetch(preset: str, years=None):
    c = cache(preset)
    cat = catalog()
    leg = legend()
    write_json(c / "cdl_legend.json", {
        "source": SERVICE + "/rasterAttributeTable", "fetched_at": now(),
        "classes": {str(k): v for k, v in sorted(leg.items())}})
    years = years or [y for y in sorted(cat) if y >= FIRST_YEAR]
    bbox = box_5070(preset)
    files = {}
    for y in years:
        dst = c / "rasters" / f"cdl_{y}.tif"
        if not dst.exists():
            arr, info = export_year(bbox, cat[y])
            res = info["res_m"]
            transform = rasterio.Affine(res, 0, bbox[0], 0, -res, bbox[3])
            assert abs(info["transform"][2] - bbox[0]) < 1e-6 and abs(info["transform"][5] - bbox[3]) < 1e-6, info
            with rasterio.open(dst, "w", driver="COG", width=arr.shape[1], height=arr.shape[0], count=1,
                               dtype="uint8", crs=CDL_CRS, transform=transform, nodata=0,
                               compress="deflate") as d:
                d.write(arr, 1)
            print(f"{preset} CDL {y}: {arr.shape} res {res} m, classes {len(np.unique(arr))}")
        files[y] = {"file": f"rasters/cdl_{y}.tif", "raster_id": cat[y]["id"], "raster_name": cat[y]["name"],
                    "res_m": cat[y]["res_m"]}
    meta = {
        "dataset": "cdl", "url": SERVICE + "/exportImage",
        "params": {"bbox_epsg5070": bbox, "interpolation": "RSP_NearestNeighbor",
                   "mosaicRule": "esriMosaicLockRaster per year", "years": years},
        "fetched_at": now(), "native_res_m": {str(y): f["res_m"] for y, f in files.items()},
        "timestep": "year", "units": "CDL class code (see cdl_legend.json)", "fill_value": 0,
        "auth": "none", "crs": CDL_CRS, "files": {str(k): v for k, v in files.items()},
        "provider": "USDA NASS Cropland Data Layer via USDA ARS SCINet CroplandCROS image service",
        "note": "Planetary Computer usda-cdl stops at 2021, so not used.",
    }
    write_json(c / "cdl.meta.json", meta)
    return meta


if __name__ == "__main__":
    for p in (sys.argv[1:] or list(PRESETS)):
        fetch(p)
