"""Training sample for the bare/cover detector (spec B6.1): CDL-homogeneous clusters in the 10 km box
and their Sentinel-2 L2A medians per scene.

1. Clusters: 30 m CDL cells (cached rasters from backend/field, EPSG:5070) whose 5 x 5 neighbourhood
   (150 m) is one class in a year; a cell is a candidate if that holds in >= 8 of 2016-2025 with a class
   that has calendar windows (common.CROP_WINDOWS). N_CLUSTERS are drawn at random (seed 0) with
   >= 250 m spacing, at most 40% from cells that are fallow in some year, and none within 150 m of the
   preset field (the preset field is never training data). Spatial block = 2.5 km square of the box.
2. Scenes: Planetary Computer sentinel-2-l2a over the box, one MGRS tile that contains the whole box,
   scene cloud < 50%, thinned to the clearest scene per half-month. For each scene only the box window is
   read: SCL at native 20 m, B02 B03 B04 B08 B11 B12 at 40 m from the COG overviews (keeps the download
   at ~1-2 blocks per band). Per cluster: SCL clear/water/vegetation/not-vegetated fractions over 20 m
   pixels within 55 m, and medians of reflectance and per-pixel NDVI/NDWI/BSI over 40 m pixels within 45 m.

Outputs data/cache/<preset>/ai/{clusters.parquet, s2_clusters.parquet, s2_clusters.meta.json}.
Usage: uv run python -m fieldshift_ai.sample [preset ...] [--n 250]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import math
import time
import warnings
from collections import defaultdict

import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
from numpy.lib.stride_tricks import sliding_window_view
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import array_bounds
from rasterio.windows import from_bounds
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform as shp_transform

from .common import CROP_WINDOWS, FIELD_DIR, PRESETS, YEARS, ai_cache, cache, now, read_json, write_json

warnings.filterwarnings("ignore", category=RuntimeWarning)
MPC = "https://planetarycomputer.microsoft.com/api/stac/v1"
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", VSI_CACHE="TRUE",
                GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2")
BANDS = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "swir1": "B11", "swir2": "B12"}
S2_CLEAR = (2, 4, 5, 6)  # same clear rule as backend/field
HOMOG, MIN_YEARS, SPACING, FIELD_BUFFER, BLOCK = 5, 8, 250.0, 150.0, 2500.0
WORKERS = 12


def tr(a, b):
    return Transformer.from_crs(a, b, always_xy=True)


def select_clusters(preset: str, n: int, seed: int = 0) -> pd.DataFrame:
    box = read_json(FIELD_DIR / "polygons" / f"{preset}_training_box.json")
    g4326 = shape(box["geometry_epsg4326"])
    g5070 = shp_transform(tr("EPSG:4326", "EPSG:5070").transform, g4326)
    fc = read_json(FIELD_DIR / "polygons" / f"{preset}.geojson")
    field5070 = shp_transform(tr("EPSG:4326", "EPSG:5070").transform, shape(fc["features"][0]["geometry"]))
    excl = field5070.buffer(FIELD_BUFFER)
    rdir = cache(preset) / "rasters"
    with rasterio.open(rdir / "cdl_2016.tif") as src:
        win = from_bounds(*g5070.bounds, src.transform).round_offsets().round_lengths()
        T = src.window_transform(win)
        H, W = int(win.height), int(win.width)
    gb = array_bounds(H, W, T)  # (west, south, east, north)
    stack = {}
    for y in YEARS:
        with rasterio.open(rdir / f"cdl_{y}.tif") as src:
            w = from_bounds(gb[0], gb[1], gb[2], gb[3], src.transform)
            stack[y] = src.read(1, window=w, out_shape=(H, W), resampling=Resampling.mode, boundless=True, fill_value=0)
    r = HOMOG // 2
    good_years = np.zeros((H - 2 * r, W - 2 * r), dtype=int)
    codes = {}
    labelled = np.array(sorted(CROP_WINDOWS))
    for y, a in stack.items():
        sw = sliding_window_view(a, (HOMOG, HOMOG))
        a = a.astype(np.int16)
        c = a[r:-r, r:-r]
        hom = (sw == c[:, :, None, None]).all(axis=(2, 3)) & np.isin(c, labelled)
        codes[y] = np.where(hom, c, -1)
        good_years += hom
    rows, cols = np.nonzero(good_years >= MIN_YEARS)
    xs = T.c + (cols + r + 0.5) * T.a
    ys = T.f + (rows + r + 0.5) * T.e
    keep = np.array([g5070.contains(Point(x, yv)) and not excl.contains(Point(x, yv)) for x, yv in zip(xs, ys)], bool)
    rows, cols, xs, ys = rows[keep], cols[keep], xs[keep], ys[keep]
    has_fallow = np.zeros(len(rows), bool)
    for y in YEARS:
        has_fallow |= codes[y][rows, cols] == 61
    rng = np.random.default_rng(seed)
    order_f = rng.permutation(np.nonzero(has_fallow)[0])
    order_o = rng.permutation(np.nonzero(~has_fallow)[0])
    chosen, grid = [], defaultdict(list)

    def ok(i):
        gx, gy = int(xs[i] // SPACING), int(ys[i] // SPACING)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid[(gx + dx, gy + dy)]:
                    if math.hypot(xs[i] - xs[j], ys[i] - ys[j]) < SPACING:
                        return False
        return True

    def take(order, cap):
        k = 0
        for i in order:
            if len(chosen) >= n or k >= cap:
                break
            if i in chosen_set:
                continue
            if ok(i):
                chosen.append(i); chosen_set.add(i); k += 1
                grid[(int(xs[i] // SPACING), int(ys[i] // SPACING))].append(i)

    chosen_set: set = set()
    take(order_f, int(0.4 * n))
    take(order_o, n)
    take(order_f, n)
    idx = np.array(chosen)
    to4326 = tr("EPSG:5070", "EPSG:4326")
    to32610 = tr("EPSG:5070", "EPSG:32610")
    lon, lat = to4326.transform(xs[idx], ys[idx])
    x6, y6 = to32610.transform(xs[idx], ys[idx])
    bb = box["bbox_epsg32610"]
    bx = np.clip(((np.array(x6) - bb[0]) // BLOCK).astype(int), 0, 3)
    by = np.clip(((np.array(y6) - bb[1]) // BLOCK).astype(int), 0, 3)
    df = pd.DataFrame({"cluster_id": [f"{preset[:3]}_{k:03d}" for k in range(len(idx))], "lon": lon, "lat": lat,
                       "x5070": xs[idx], "y5070": ys[idx], "x32610": x6, "y32610": y6, "block": by * 4 + bx,
                       "has_fallow_year": has_fallow[idx]})
    for y in YEARS:
        df[f"cdl_{y}"] = codes[y][rows[idx], cols[idx]]
    print(f"{preset}: {len(rows)} candidate cells, {len(df)} clusters chosen "
          f"({int(df.has_fallow_year.sum())} with a fallow year), {df.block.nunique()} blocks", flush=True)
    return df


def search(preset: str):
    box = read_json(FIELD_DIR / "polygons" / f"{preset}_training_box.json")
    g = shape(box["geometry_epsg4326"])
    cat = pystac_client.Client.open(MPC)
    items = list(cat.search(collections=["sentinel-2-l2a"], intersects=mapping(g), datetime="2015-07-01/2025-12-31",
                            query={"eo:cloud_cover": {"lt": 50}}).items())
    by_tile = defaultdict(list)
    for it in items:
        if shape(it.geometry).contains(g):
            by_tile[it.properties["s2:mgrs_tile"]].append(it)
    tile = max(by_tile, key=lambda t: len(by_tile[t]))
    best = {}
    for it in by_tile[tile]:
        d = it.datetime
        key = (d.year, d.month, d.day > 15)
        if key not in best or it.properties["eo:cloud_cover"] < best[key].properties["eo:cloud_cover"]:
            best[key] = it
    sel = sorted(best.values(), key=lambda i: i.datetime)
    print(f"{preset}: {len(items)} items (cloud<50), tile {tile} covers box in {len(by_tile[tile])}; "
          f"{len(sel)} kept (clearest per half-month)", flush=True)
    return sel, tile, len(items)


def _read(href, win, shape_, resampling):
    last = None
    for attempt in range(4):
        try:
            with rasterio.open(href) as src:
                return src.read(1, window=win, out_shape=shape_, resampling=resampling, boundless=True, fill_value=0)
        except Exception as e:  # noqa: BLE001 - transient HTTP errors
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"read failed {href.split('?')[0]}: {last}")


def process(item, clusters: pd.DataFrame, box4326):
    item = pc.sign(item)
    p = item.properties
    epsg = p.get("proj:epsg") or int(str(p["proj:code"]).split(":")[1])
    crs = f"EPSG:{epsg}"
    t = tr("EPSG:4326", crs)
    cx, cy = t.transform(clusters.lon.values, clusters.lat.values)
    cx, cy = np.asarray(cx), np.asarray(cy)
    bx = shp_transform(t.transform, box4326).bounds
    with rasterio.Env(**GDAL_ENV):
        with rasterio.open(item.assets["SCL"].href) as src:
            T0 = src.transform  # 20 m grid; snap the window to 120 m (multiple of 10/20/40 m) from the tile origin
        x0 = T0.c + math.floor((bx[0] - 200 - T0.c) / 120) * 120
        y1 = T0.f - math.floor((T0.f - (bx[3] + 200)) / 120) * 120
        x1 = T0.c + math.ceil((bx[2] + 200 - T0.c) / 120) * 120
        y0 = T0.f - math.ceil((T0.f - (bx[1] - 200)) / 120) * 120
        W20, H20 = int(round((x1 - x0) / 20)), int(round((y1 - y0) / 20))
        W40, H40 = W20 // 2, H20 // 2
        scl_win = from_bounds(x0, y0, x1, y1, T0)
        scl = _read(item.assets["SCL"].href, scl_win, (H20, W20), Resampling.nearest)
        base = float(p.get("s2:processing_baseline") or 0)
        off = 1000 if base >= 4.0 else 0
        bands = {}
        for k, a in BANDS.items():
            with rasterio.open(item.assets[a].href) as src:
                win = from_bounds(x0, y0, x1, y1, src.transform)
            dn = _read(item.assets[a].href, win, (H40, W40), Resampling.average).astype("float32")
            bands[k] = np.where(dn > 0, (dn - off) / 10000.0, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (bands["nir"] - bands["red"]) / (bands["nir"] + bands["red"])
        ndwi = (bands["green"] - bands["nir"]) / (bands["green"] + bands["nir"])
        bsi = ((bands["swir1"] + bands["red"]) - (bands["nir"] + bands["blue"])) / (
            (bands["swir1"] + bands["red"]) + (bands["nir"] + bands["blue"]))
    # pixel centre coordinates
    xs20 = x0 + (np.arange(W20) + 0.5) * 20; ys20 = y1 - (np.arange(H20) + 0.5) * 20
    xs40 = x0 + (np.arange(W40) + 0.5) * 40; ys40 = y1 - (np.arange(H40) + 0.5) * 40
    rows = []
    date = item.datetime.strftime("%Y-%m-%d")
    for cid, x, y in zip(clusters.cluster_id.values, cx, cy):
        c20 = np.nonzero(np.abs(xs20 - x) <= 55)[0]; r20 = np.nonzero(np.abs(ys20 - y) <= 55)[0]
        s = scl[np.ix_(r20, c20)]
        dd = (xs20[c20][None, :] - x) ** 2 + (ys20[r20][:, None] - y) ** 2 <= 55 ** 2
        s = s[dd]
        clear = np.isin(s, S2_CLEAR)
        n = s.size
        c40 = np.nonzero(np.abs(xs40 - x) <= 45)[0]; r40 = np.nonzero(np.abs(ys40 - y) <= 45)[0]
        d40 = (xs40[c40][None, :] - x) ** 2 + (ys40[r40][:, None] - y) ** 2 <= 45 ** 2
        row = {"cluster_id": cid, "date": date, "scene_id": item.id, "n_scl": n,
               "clear_frac": float(clear.mean()) if n else 0.0,
               "water_frac": float(np.mean(s[clear] == 6)) if clear.any() else math.nan,
               "scl4_frac": float(np.mean(s[clear] == 4)) if clear.any() else math.nan,
               "scl5_frac": float(np.mean(s[clear] == 5)) if clear.any() else math.nan,
               "n_px40": int(d40.sum())}
        for k, arr in list(bands.items()) + [("ndvi_med", ndvi), ("ndwi_med", ndwi), ("bsi_med", bsi)]:
            v = arr[np.ix_(r40, c40)][d40]
            v = v[np.isfinite(v)]
            row[k] = float(np.median(v)) if v.size else math.nan
        rows.append(row)
    return rows


def run(preset: str, n: int):
    t0 = time.time()
    c = ai_cache(preset)
    clusters = select_clusters(preset, n)
    clusters.to_parquet(c / "clusters.parquet", index=False)
    items, tile, n_found = search(preset)
    box4326 = shape(read_json(FIELD_DIR / "polygons" / f"{preset}_training_box.json")["geometry_epsg4326"])
    rows, errors = [], []
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(process, it, clusters, box4326): it.id for it in items}
        for k, f in enumerate(cf.as_completed(futs), 1):
            try:
                rows += f.result()
            except Exception as e:  # noqa: BLE001
                errors.append({"scene_id": futs[f], "error": str(e)[:300]})
            if k % 25 == 0:
                print(f"  {k}/{len(items)} scenes ({time.time()-t0:.0f}s, {len(errors)} errors)", flush=True)
    df = pd.DataFrame(rows).sort_values(["cluster_id", "date"]).reset_index(drop=True)
    df.to_parquet(c / "s2_clusters.parquet", index=False)
    write_json(c / "s2_clusters.meta.json", {
        "dataset": "s2_clusters", "url": f"{MPC}/collections/sentinel-2-l2a",
        "params": {"collection": "sentinel-2-l2a", "datetime": "2015-07-01/2025-12-31", "eo:cloud_cover": "< 50",
                   "tile": tile, "thinning": "clearest scene per half-month",
                   "intersects": f"backend/field/polygons/{preset}_training_box.json",
                   "bands": BANDS, "read_res_m": {"SCL": 20, "reflectance": 40},
                   "cluster": f"{HOMOG}x{HOMOG} CDL 30 m homogeneous in >= {MIN_YEARS} years; reflectance median of 40 m "
                              "pixels within 45 m, SCL fractions over 20 m pixels within 55 m",
                   "clear_rule": "SCL in {2,4,5,6}", "dn_offset": "-1000 for processing baseline >= 04.00"},
        "fetched_at": now(), "footprint_geojson": mapping(box4326), "native_res_m": {"B02-B08": 10, "B11,B12,SCL": 20},
        "timestep": "per scene (thinned)", "units": {"reflectance": "unitless 0-1", "indices": "unitless"},
        "fill_value": "NaN", "auth": "none (Planetary Computer anonymous SAS token)",
        "n_items_found": n_found, "n_scenes_read": len(items) - len(errors), "n_clusters": len(clusters),
        "n_rows": len(df), "errors": errors, "seconds": round(time.time() - t0)})
    print(f"{preset}: {len(df)} rows from {len(items)-len(errors)} scenes, {len(errors)} errors, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("presets", nargs="*")
    ap.add_argument("--n", type=int, default=250)
    a = ap.parse_args()
    for p in (a.presets or PRESETS):
        run(p, a.n)
