"""HLS v2.0 (NASA/USGS Harmonized Landsat Sentinel-2) from Planetary Computer `hls2-l30` / `hls2-s30`, anonymous.
Field-median NDVI/NDWI per scene, same definitions as backend/field timeseries.py. Only the polygon window is read.
Usage: uv run python -m nasa_open.hls [preset ...] [--start 2016-01-01] [--end YYYY-MM-DD, default today]"""
from __future__ import annotations
import argparse, concurrent.futures as cf, math, time, warnings
import numpy as np, pandas as pd, planetary_computer as pc, pystac_client, rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping
from .common import *
warnings.filterwarnings("ignore")
# HLS band names: L30 NIR narrow = B05, SWIR1 = B06; S30 NIR narrow = B8A, SWIR1 = B11
BANDS = {"hls2-l30": {"green": "B03", "red": "B04", "nir": "B05"}, "hls2-s30": {"green": "B03", "red": "B04", "nir": "B8A"}}

def scene(item, preset):
    item = pc.sign(item)
    coll = item.collection_id
    # Some 2017-2021 items carry proj:code EPSG:327xx (southern hemisphere) although the COGs are in 326xx; trust the file CRS.
    with rasterio.Env(**GDAL_ENV), rasterio.open(item.assets["Fmask"].href) as s0:
        wkt = s0.crs.to_wkt(); epsg = s0.crs.to_epsg()
    g = polygon_in(preset, wkt)
    with rasterio.Env(**GDAL_ENV):
        for attempt in range(4):
            try:
                with rasterio.open(item.assets["Fmask"].href) as src:
                    win = from_bounds(*g.bounds, src.transform)
                    win = Window(math.floor(win.col_off) - 1, math.floor(win.row_off) - 1, math.ceil(win.width) + 3, math.ceil(win.height) + 3)
                    fm = src.read(1, window=win, boundless=True, fill_value=255); tr = src.window_transform(win)
                    bands = {}
                for k, a in BANDS[coll].items():
                    with rasterio.open(item.assets[a].href) as s:
                        bands[k] = s.read(1, window=win, boundless=True, fill_value=-9999).astype("float32")
                break
            except Exception as e:
                last = e; time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"{item.id}: {last}")
    h, w = fm.shape
    inside = ~geometry_mask([g], (h, w), tr, all_touched=False)
    bit = lambda k: ((fm >> k) & 1) == 1
    clear = inside & ~(bit(1) | bit(2) | bit(3) | bit(4)) & (fm != 255)   # not cloud, adjacent, shadow, snow/ice
    for v in bands.values(): clear &= v > -9999
    n_poly, n_valid = int(inside.sum()), int(clear.sum())
    row = {"scene_id": item.id, "datetime": item.datetime, "platform": "HLSL30" if coll == "hls2-l30" else "HLSS30",
           "sensor": item.properties.get("platform"), "tile": item.id.split(".")[2], "epsg": epsg,
           "scene_cloud_pct": item.properties.get("eo:cloud_cover"), "n_pixels_poly": n_poly, "n_valid": n_valid,
           "clear_frac": n_valid / n_poly if n_poly else 0.0, "water_frac": float(np.mean(bit(5)[clear])) if n_valid else math.nan}
    if n_valid:
        b = {k: v[clear] * 1e-4 for k, v in bands.items()}
        with np.errstate(divide="ignore", invalid="ignore"):
            idx = {"ndvi": (b["nir"] - b["red"]) / (b["nir"] + b["red"]), "ndwi": (b["green"] - b["nir"]) / (b["green"] + b["nir"])}
        for n, v in idx.items():
            v = v[np.isfinite(v)]
            p10, p50, p90 = np.percentile(v, [10, 50, 90]) if v.size else (math.nan,) * 3
            row.update({f"{n}_med": float(p50), f"{n}_p10": float(p10), f"{n}_p90": float(p90)})
    else:
        for n in ("ndvi", "ndwi"): row.update({f"{n}_med": math.nan, f"{n}_p10": math.nan, f"{n}_p90": math.nan})
    return row

def run(preset, start, end):
    g, _ = load_polygon(preset); t0 = time.time()
    cat = pystac_client.Client.open(MPC)
    items = list(cat.search(collections=["hls2-l30", "hls2-s30"], intersects=mapping(g), datetime=f"{start}/{end}").items())
    print(preset, len(items), "items", flush=True)
    rows, errors = [], []
    with cf.ThreadPoolExecutor(12) as ex:
        futs = {ex.submit(scene, it, preset): it.id for it in items}
        for n, f in enumerate(cf.as_completed(futs), 1):
            try: rows.append(f.result())
            except Exception as e: errors.append({"scene_id": futs[f], "error": str(e)[:300]})
            if n % 100 == 0: print(f"  {n}/{len(items)} {time.time()-t0:.0f}s", flush=True)
    df = pd.DataFrame(rows); df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["date"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df = df.sort_values("datetime").reset_index(drop=True)
    c = CACHE / preset; c.mkdir(parents=True, exist_ok=True)
    df.to_parquet(c / "hls.parquet", index=False)
    by = df.groupby("platform").agg(n=("date", "size"), first=("date", "min"), last=("date", "max")).reset_index().to_dict("records")
    write_json(c / "hls.meta.json", {
        "dataset": "hls", "url": f"{MPC}/collections/hls2-l30 + hls2-s30",
        "params": {"collections": ["hls2-l30 (HLSL30 v2.0)", "hls2-s30 (HLSS30 v2.0)"], "datetime": f"{start}/{end}", "intersects": f"backend/field/polygons/{preset}.geojson",
                   "bands": BANDS, "mask": "Fmask: clear = not bit1 cloud, bit2 adjacent cloud/shadow, bit3 shadow, bit4 snow/ice (water bit5 kept)",
                   "scale": "reflectance = DN * 1e-4, fill -9999", "indices": "NDVI=(NIR-Red)/(NIR+Red) with narrow NIR (B05 / B8A); NDWI=(Green-NIR)/(Green+NIR)"},
        "fetched_at": now(), "footprint_geojson": mapping(g), "native_res_m": 30, "timestep": "per scene (irregular; ~2-3 day combined revisit)",
        "units": {"ndvi": "unitless", "ndwi": "unitless", "clear_frac": "fraction of polygon pixels"}, "fill_value": "NaN",
        "auth": "none (Planetary Computer anonymous SAS token; NASA LP DAAC copy needs Earthdata login)",
        "credit": "HLS v2.0, NASA/USGS (Masek et al. 2021, doi:10.5067/HLS/HLSL30.002 and HLSS30.002); hosted by Microsoft Planetary Computer",
        "availability_note": "PC collections start 2020-01-01 (hls2-s30) and 2017-08 (first L30 item over these fields); nothing earlier exists there",
        "n_items_found": len(items), "n_rows": len(df), "by_platform": by, "errors": errors, "seconds": round(time.time() - t0)})
    print(preset, len(df), "rows", len(errors), "errors", f"{time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("presets", nargs="*"); ap.add_argument("--start", default="2016-01-01"); ap.add_argument("--end", default=__import__("datetime").date.today().isoformat())
    a = ap.parse_args()
    for p in a.presets or PRESETS: run(p, a.start, a.end)
