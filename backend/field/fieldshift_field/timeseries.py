"""Per-scene field statistics from Sentinel-2 L2A and Landsat C2 L2 (Planetary Computer, anonymous).

For each STAC item intersecting the polygon, only the polygon window is read
from the COGs (HTTP range reads via GDAL /vsicurl/). Per scene we store the
field median and p10/p90 of NDVI, NDWI and BSI over clear pixels, plus the
clear-pixel fraction of the polygon.

  NDVI = (NIR - Red) / (NIR + Red)
  NDWI = (Green - NIR) / (Green + NIR)                      (McFeeters 1996, open water)
  BSI  = ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))

Masks
  Sentinel-2: SCL classes 2 (dark area), 4 (vegetation), 5 (not vegetated), 6 (water) are
  "clear"; 0,1,3,7,8,9,10,11 are not. Class 2 is kept because winter-flooded checks in
  this flat valley can read as dark area; per-class SCL fractions are stored so this
  choice can be revisited. Processing baseline >= 04.00 (from 2022-01-25): DN offset
  of -1000 removed before scaling by 1e-4.
  Landsat: QA_PIXEL clear (bit 6) or water (bit 7), and not fill/dilated cloud/cloud/
  shadow/snow (bits 0,1,3,4,5). Collection 2 L2 scaling 2.75e-5 * DN - 0.2.
  Only Tier 1 Landsat scenes are used.

Outputs
  data/cache/<preset>/s2.parquet + s2.meta.json, landsat.parquet + landsat.meta.json
  data/cache/<preset>/rasters/s2_ndvi_stack.npz  (per-scene 10 m NDVI windows, float16, for grid.py)

Usage: uv run python -m fieldshift_field.timeseries [s2|landsat|all] [preset ...] [--start YYYY-MM-DD] [--end YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import math
import time
import warnings

import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping

from .common import PRESETS, cache, load_polygon, now, polygon_in, write_json

warnings.filterwarnings("ignore", category=RuntimeWarning)

MPC = "https://planetarycomputer.microsoft.com/api/stac/v1"
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", VSI_CACHE="TRUE",
                GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2")
S2_CLEAR = (2, 4, 5, 6)
WORKERS = 12

SOURCES = {
    "s2": {"collection": "sentinel-2-l2a", "start": "2015-06-23",
           "bands": {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "swir1": "B11"}, "mask": "SCL",
           "native_res_m": 10},
    "landsat": {"collection": "landsat-c2-l2", "start": "2016-01-01",
                "bands": {"blue": "blue", "green": "green", "red": "red", "nir": "nir08", "swir1": "swir16"},
                "mask": "qa_pixel", "native_res_m": 30},
}


def search(source: str, geom4326, start: str, end: str):
    cat = pystac_client.Client.open(MPC)
    items = list(cat.search(collections=[SOURCES[source]["collection"]], intersects=mapping(geom4326),
                            datetime=f"{start}/{end}").items())
    if source == "landsat":
        items = [i for i in items if i.properties.get("landsat:collection_category") == "T1"
                 and i.properties.get("platform") in ("landsat-7", "landsat-8", "landsat-9")]
    return items


def _stats(v):
    v = v[np.isfinite(v)]
    if v.size == 0:
        return (math.nan,) * 3
    p10, p50, p90 = np.percentile(v, [10, 50, 90])
    return float(p50), float(p10), float(p90)


def _indices(b):
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (b["nir"] - b["red"]) / (b["nir"] + b["red"])
        ndwi = (b["green"] - b["nir"]) / (b["green"] + b["nir"])
        bsi = ((b["swir1"] + b["red"]) - (b["nir"] + b["blue"])) / ((b["swir1"] + b["red"]) + (b["nir"] + b["blue"]))
    return ndvi, ndwi, bsi


def _read(href, bounds, shape, resampling=Resampling.nearest):
    for attempt in range(4):
        try:
            with rasterio.open(href) as src:
                win = from_bounds(*bounds, src.transform)
                return src.read(1, window=win, out_shape=shape, resampling=resampling, boundless=True, fill_value=0)
        except Exception as e:  # noqa: BLE001 - transient HTTP errors
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"read failed {href.split('?')[0]}: {last}")


def process_s2(item, preset):
    item = pc.sign(item)
    epsg = item.properties["proj:epsg"] if "proj:epsg" in item.properties else int(str(item.properties["proj:code"]).split(":")[1])
    g = polygon_in(preset, f"EPSG:{epsg}")
    minx, miny, maxx, maxy = g.bounds
    s = 60.0
    b = (math.floor((minx - 20) / s) * s, math.floor((miny - 20) / s) * s,
         math.ceil((maxx + 20) / s) * s, math.ceil((maxy + 20) / s) * s)
    w, h = int((b[2] - b[0]) / 10), int((b[3] - b[1]) / 10)
    tr = rasterio.Affine(10, 0, b[0], 0, -10, b[3])
    inside = ~geometry_mask([g], (h, w), tr, all_touched=False)
    with rasterio.Env(**GDAL_ENV):
        scl = _read(item.assets["SCL"].href, b, (h, w))
        n_poly = int(inside.sum())
        scl_in = scl[inside]
        scl_frac = {f"scl_{k}": float(np.mean(scl_in == k)) for k in range(12)}
        clear = inside & np.isin(scl, S2_CLEAR)
        row = {"scene_id": item.id, "datetime": item.datetime, "platform": item.properties.get("platform"),
               "tile": item.properties.get("s2:mgrs_tile"), "epsg": epsg,
               "processing_baseline": item.properties.get("s2:processing_baseline"),
               "scene_cloud_pct": item.properties.get("eo:cloud_cover"), "n_pixels_poly": n_poly, **scl_frac}
        ndvi_img = None
        if clear.sum() > 0:
            base = float(item.properties.get("s2:processing_baseline") or 0)
            off = 1000 if base >= 4.0 else 0
            bands = {}
            for k, a in SOURCES["s2"]["bands"].items():
                dn = _read(item.assets[a].href, b, (h, w)).astype("float32")
                valid_dn = dn > 0
                clear &= valid_dn
                bands[k] = (dn - off) / 10000.0
            ndvi, ndwi, bsi = _indices(bands)
            ndvi_img = np.where(clear, ndvi, np.nan).astype("float16")
        else:
            ndvi = ndwi = bsi = np.full((h, w), np.nan)
    n_valid = int(clear.sum())
    row.update({"n_valid": n_valid, "clear_frac": n_valid / n_poly if n_poly else 0.0,
                "water_frac": float(np.mean(scl[clear] == 6)) if n_valid else math.nan})
    for name, arr in (("ndvi", ndvi), ("ndwi", ndwi), ("bsi", bsi)):
        p50, p10, p90 = _stats(arr[clear]) if n_valid else (math.nan,) * 3
        row.update({f"{name}_med": p50, f"{name}_p10": p10, f"{name}_p90": p90})
    stack = {"ndvi": ndvi_img, "transform": list(tr)[:6], "epsg": epsg} if ndvi_img is not None else None
    return row, stack


def process_landsat(item, preset):
    item = pc.sign(item)
    epsg = item.properties.get("proj:epsg") or int(str(item.properties["proj:code"]).split(":")[1])
    g = polygon_in(preset, f"EPSG:{epsg}")
    with rasterio.Env(**GDAL_ENV):
        for attempt in range(4):
            try:
                with rasterio.open(item.assets["qa_pixel"].href) as src:
                    tr0 = src.transform
                    win = from_bounds(*[g.bounds[0] - 45, g.bounds[1] - 45, g.bounds[2] + 45, g.bounds[3] + 45], tr0)
                    win = Window(math.floor(win.col_off), math.floor(win.row_off),
                                 math.ceil(win.width) + 1, math.ceil(win.height) + 1)
                    qa = src.read(1, window=win, boundless=True, fill_value=1)
                    tr = src.window_transform(win)
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"read failed {item.id}: {last}")
        h, w = qa.shape
        inside = ~geometry_mask([g], (h, w), tr, all_touched=False)
        bit = lambda k: (qa >> k) & 1 == 1
        bad = bit(0) | bit(1) | bit(3) | bit(4) | bit(5)
        clear = inside & ~bad & (bit(6) | bit(7))
        n_poly = int(inside.sum())
        row = {"scene_id": item.id, "datetime": item.datetime, "platform": item.properties.get("platform"),
               "path_row": f"{item.properties.get('landsat:wrs_path')}/{item.properties.get('landsat:wrs_row')}",
               "epsg": epsg, "scene_cloud_pct": item.properties.get("eo:cloud_cover"), "n_pixels_poly": n_poly,
               "fill_frac": float(np.mean(bit(0)[inside])), "cloud_frac": float(np.mean((bit(3) | bit(1))[inside])),
               "shadow_frac": float(np.mean(bit(4)[inside]))}
        if clear.sum() > 0:
            bounds = rasterio.transform.array_bounds(h, w, tr)
            bands = {}
            for k, a in SOURCES["landsat"]["bands"].items():
                dn = _read(item.assets[a].href, (bounds[0], bounds[1], bounds[2], bounds[3]), (h, w)).astype("float32")
                clear &= dn > 0
                bands[k] = dn * 2.75e-5 - 0.2
            ndvi, ndwi, bsi = _indices(bands)
        else:
            ndvi = ndwi = bsi = np.full((h, w), np.nan)
    n_valid = int(clear.sum())
    row.update({"n_valid": n_valid, "clear_frac": n_valid / n_poly if n_poly else 0.0,
                "water_frac": float(np.mean(bit(7)[clear])) if n_valid else math.nan})
    for name, arr in (("ndvi", ndvi), ("ndwi", ndwi), ("bsi", bsi)):
        p50, p10, p90 = _stats(arr[clear]) if n_valid else (math.nan,) * 3
        row.update({f"{name}_med": p50, f"{name}_p10": p10, f"{name}_p90": p90})
    return row, None


def run(source: str, preset: str, start=None, end=None):
    cfg = SOURCES[source]
    start = start or cfg["start"]
    end = end or pd.Timestamp.now("UTC").strftime("%Y-%m-%d")
    g4326, _ = load_polygon(preset)
    t0 = time.time()
    items = search(source, g4326, start, end)
    print(f"{preset} {source}: {len(items)} items {start}..{end} (search {time.time()-t0:.0f}s)", flush=True)
    fn = process_s2 if source == "s2" else process_landsat
    rows, stacks, errors = [], {}, []
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(fn, it, preset): it.id for it in items}
        for n, f in enumerate(cf.as_completed(futs), 1):
            try:
                row, st = f.result()
                rows.append(row)
                if st is not None:
                    stacks[row["scene_id"]] = st
            except Exception as e:  # noqa: BLE001 - keep going, log
                errors.append({"scene_id": futs[f], "error": str(e)[:300]})
            if n % 100 == 0:
                print(f"  {n}/{len(items)} done ({time.time()-t0:.0f}s, {len(errors)} errors)", flush=True)
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit(f"{preset} {source}: no rows; errors: {errors[:3]}")
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["date"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df["source"] = source
    n_raw = len(df)
    # same acquisition can appear twice (overlapping tiles / reprocessed items): keep the one with most valid pixels
    df = df.sort_values(["date", "n_valid", "n_pixels_poly"], ascending=[True, False, False])
    dupes = df[df.duplicated("date", keep="first")]["scene_id"].tolist() if source == "s2" else []
    if source == "s2":
        df = df.drop_duplicates("date", keep="first")
    else:  # Landsat: two platforms can share a date only if different sensors; dedupe per platform+date
        df = df.drop_duplicates(["date", "platform"], keep="first")
    df = df.sort_values("datetime").reset_index(drop=True)
    c = cache(preset)
    df.to_parquet(c / f"{source}.parquet", index=False)
    if source == "s2":
        keep = set(df["scene_id"])
        np.savez_compressed(c / "rasters" / "s2_ndvi_stack.npz", **{
            sid: st["ndvi"] for sid, st in stacks.items() if sid in keep})
        write_json(c / "rasters" / "s2_ndvi_stack.json", {
            sid: {"transform": st["transform"], "epsg": st["epsg"],
                  "date": df.loc[df.scene_id == sid, "date"].iloc[0]} for sid, st in stacks.items() if sid in keep})
    meta = {
        "dataset": source, "url": f"{MPC}/collections/{cfg['collection']}",
        "params": {"collection": cfg["collection"], "datetime": f"{start}/{end}", "intersects": "polygons/" + preset + ".geojson",
                   "bands": cfg["bands"], "mask": cfg["mask"],
                   "clear_rule": ("SCL in {2,4,5,6}" if source == "s2" else
                                  "QA_PIXEL (bit6 clear or bit7 water) and not bits 0,1,3,4,5; Tier 1 only"),
                   "dedupe": "one row per date (S2) / per date+platform (Landsat), keeping most valid pixels"},
        "fetched_at": now(), "footprint_geojson": mapping(g4326), "native_res_m": cfg["native_res_m"],
        "timestep": "per scene (irregular)", "units": {"ndvi": "unitless", "ndwi": "unitless", "bsi": "unitless",
                                                       "clear_frac": "fraction of polygon pixels"},
        "fill_value": "NaN", "auth": "none (Planetary Computer anonymous SAS token via planetary-computer package)",
        "n_items_found": len(items), "n_rows_raw": n_raw, "n_rows": len(df), "duplicates_dropped": len(dupes),
        "errors": errors, "seconds": round(time.time() - t0),
    }
    write_json(c / f"{source}.meta.json", meta)
    print(f"{preset} {source}: {len(df)} rows, {len(errors)} errors, {time.time()-t0:.0f}s", flush=True)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=["s2", "landsat", "all"])
    ap.add_argument("presets", nargs="*")
    ap.add_argument("--start")
    ap.add_argument("--end")
    a = ap.parse_args()
    for p in (a.presets or list(PRESETS)):
        for s in (["s2", "landsat"] if a.source == "all" else [a.source]):
            run(s, p, a.start, a.end)
