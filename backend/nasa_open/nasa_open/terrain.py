"""NASADEM (MPC `nasadem`, anonymous) -> elevation, slope %, low spots on the 32610 30 m lattice used by backend/field grid.
Usage: uv run python -m nasa_open.terrain [preset ...]"""
from __future__ import annotations
import json, sys, math
import numpy as np, planetary_computer as pc, pystac_client, rasterio
from rasterio.warp import reproject, Resampling
from rasterio.features import geometry_mask
from rasterio.merge import merge
from pyproj import Transformer
from shapely.geometry import shape
from scipy.ndimage import convolve
from .common import *

SRC = {"id": "nasadem_mpc", "title": "NASADEM HGT v001 (NASA JPL/LP DAAC), via Microsoft Planetary Computer",
       "url": "https://planetarycomputer.microsoft.com/dataset/nasadem", "accessed": today(), "verified": True}
RES = 30.0
BOX_HALF = 1000.0   # ~2 km box
PAD = 300.0         # extra for the 300 m focal mean + slope edge
LOW_M = 1.0
FOCAL_R = 150.0     # 300 m diameter window

def dem_on_lattice(cx, cy, half):
    """Return elevation (m) on 30 m 32610 lattice around (cx,cy) of half-width `half`, plus the affine origin."""
    x0 = math.floor((cx - half) / RES) * RES; x1 = math.ceil((cx + half) / RES) * RES
    y0 = math.floor((cy - half) / RES) * RES; y1 = math.ceil((cy + half) / RES) * RES
    w, h = int((x1 - x0) / RES), int((y1 - y0) / RES)
    dst_tr = rasterio.Affine(RES, 0, x0, 0, -RES, y1)
    lon0, lat0 = Transformer.from_crs(WORK, "EPSG:4326", always_xy=True).transform(cx, cy)
    cat = pystac_client.Client.open(MPC)
    d = half / 111000 * 1.6
    items = list(cat.search(collections=["nasadem"], bbox=[lon0 - d, lat0 - d, lon0 + d, lat0 + d]).items())
    out = np.full((h, w), np.nan, "float32")
    with rasterio.Env(**GDAL_ENV):
        for it in items:
            it = pc.sign(it)
            with rasterio.open(it.assets["elevation"].href) as s:
                arr = s.read(1).astype("float32"); arr[arr == s.nodata] = np.nan
                tmp = np.full((h, w), np.nan, "float32")
                reproject(arr, tmp, src_transform=s.transform, src_crs=s.crs, dst_transform=dst_tr, dst_crs=WORK,
                          resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
                out = np.where(np.isnan(out), tmp, out)
    return out, dst_tr, [i.id for i in items]

def slope_pct(z):
    """Horn (1981) 3x3 slope in percent on a 30 m grid."""
    k1 = np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]]) / (8 * RES)
    k2 = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]]) / (8 * RES)
    zf = np.where(np.isnan(z), np.nanmean(z), z)
    dx = convolve(zf, k1, mode="nearest"); dy = convolve(zf, k2, mode="nearest")
    return 100 * np.hypot(dx, dy)

def focal_mean(z):
    r = int(FOCAL_R // RES)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = ((xx * RES) ** 2 + (yy * RES) ** 2 <= FOCAL_R ** 2).astype("float32")
    zf = np.where(np.isnan(z), 0, z); m = (~np.isnan(z)).astype("float32")
    num = convolve(zf, k, mode="constant"); den = convolve(m, k, mode="constant")
    return num / np.maximum(den, 1)

def smooth(z, n=5):
    k = np.ones((n, n), "float32"); zf = np.where(np.isnan(z), 0, z); m = (~np.isnan(z)).astype("float32")
    return convolve(zf, k, mode="constant") / np.maximum(convolve(m, k, mode="constant"), 1)

def run(preset):
    gp = polygon_in(preset, WORK); cx, cy = gp.centroid.x, gp.centroid.y
    z, tr, ids = dem_on_lattice(cx, cy, BOX_HALF + PAD)
    sl = slope_pct(z); fm = focal_mean(z); rel = z - fm
    low = rel <= -LOW_M
    # NASADEM over flat farmland is noise-dominated (+-2-4 m per 30 m pixel): also derive on a 5x5 (150 m) mean DEM
    zs = smooth(z); zs[np.isnan(z)] = np.nan
    sl_s = slope_pct(zs); rel_s = zs - focal_mean(zs); low_s = rel_s <= -LOW_M
    h, w = z.shape
    inside = ~geometry_mask([gp], (h, w), tr, all_touched=False)
    # crop to the ~2 km box
    pc_ = int(PAD // RES)
    crop = (slice(pc_, h - pc_), slice(pc_, w - pc_))
    vals = lambda a, m: a[m & ~np.isnan(a)]
    fz, fs, fl = vals(z, inside), vals(sl, inside), low[inside & ~np.isnan(z)]
    def stats(zz, ss, ll, ss2=None, ll2=None):
        d = {"slope_pct_smoothed_mean": float(ss2.mean()), "slope_pct_smoothed_p90": float(np.percentile(ss2, 90)),
             "low_spot_fraction_smoothed": float(ll2.mean())} if ss2 is not None else {}
        return {**d, "elevation_m_mean": float(zz.mean()), "elevation_m_min": float(zz.min()), "elevation_m_max": float(zz.max()),
                "slope_pct_mean": float(ss.mean()), "slope_pct_p90": float(np.percentile(ss, 90)),
                "low_spot_fraction": float(ll.mean()), "n_cells": int(zz.size)}
    fv = inside & ~np.isnan(z)
    field_stats = stats(fz, fs, fl, sl_s[fv], low_s[fv])
    boxm = np.zeros_like(inside); boxm[crop] = True
    bv = boxm & ~np.isnan(z)
    box_stats = stats(vals(z, boxm), vals(sl, boxm), low[bv], sl_s[bv], low_s[bv])
    # join to grid cells
    g = json.load(open(FIELD / "out" / preset / "grid.geojson"))
    cells, miss = [], 0
    for f in g["features"]:
        c = shape(f["geometry"]).centroid
        tx = Transformer.from_crs("EPSG:4326", WORK, always_xy=True).transform(c.x, c.y)
        col = int((tx[0] - tr.c) // RES); row = int((tr.f - tx[1]) // RES)
        if 0 <= row < h and 0 <= col < w and not np.isnan(z[row, col]):
            cells.append({"cell_id": f["properties"]["cell_id"], "elevation_m": round(float(z[row, col]), 1),
                          "slope_pct": round(float(sl[row, col]), 2), "slope_pct_smoothed": round(float(sl_s[row, col]), 2),
                          "rel_elev_m_smoothed": round(float(rel_s[row, col]), 2), "low_spot_smoothed": bool(low_s[row, col]), "rel_elev_m": round(float(rel[row, col]), 2),
                          "low_spot": bool(low[row, col])})
        else:
            miss += 1; cells.append({"cell_id": f["properties"]["cell_id"], "elevation_m": None, "slope_pct": None, "slope_pct_smoothed": None, "rel_elev_m_smoothed": None, "low_spot_smoothed": None, "rel_elev_m": None, "low_spot": None})
    r = lambda a: np.round(a[crop], 1).tolist()
    nanto = lambda a: [[None if np.isnan(v) else v for v in row] for row in a]
    box = {"epsg": WORK, "cell_m": RES, "origin_x": tr.c + pc_ * RES, "origin_y_top": tr.f - pc_ * RES,
           "shape": [h - 2 * pc_, w - 2 * pc_], "elevation_m": nanto(np.round(z[crop], 1)),
           "slope_pct": nanto(np.round(sl[crop], 2)), "slope_pct_smoothed": nanto(np.round(sl_s[crop], 2)),
           "low_spot_smoothed": low_s[crop].astype(int).tolist(), "low_spot": low[crop].astype(int).tolist()}
    S = SRC
    mk = lambda v, u, note="": sn(v, u, S, note=note)
    nf = ("Headline value is from a 5x5 (150 m) mean DEM because raw NASADEM pixels over flat farmland carry +-2-4 m radar noise; raw-pixel value is in slope_*_raw.")
    summary = {"slope_mean_pct": mk(field_stats["slope_pct_smoothed_mean"], "%", nf),
               "slope_p90_pct": mk(field_stats["slope_pct_smoothed_p90"], "%", nf),
               "slope_mean_pct_raw": mk(field_stats["slope_pct_mean"], "%", "Raw 30 m NASADEM pixels; noise-dominated on levelled fields."),
               "slope_p90_pct_raw": mk(field_stats["slope_pct_p90"], "%", "Raw 30 m NASADEM pixels; noise-dominated on levelled fields."),
               "elev_m": mk(field_stats["elevation_m_mean"], "m", "NASADEM is a surface model (SRTM radar), vertical error several metres; use relative values."),
               "low_spot_fraction": mk(field_stats["low_spot_fraction_smoothed"], "fraction",
                   "Cells >= 1 m below the mean within 150 m radius (300 m window), on the 150 m-smoothed DEM; spec B7.3 (U). NASADEM is whole metres, so treat as candidates."),
               "low_spot_fraction_raw": mk(field_stats["low_spot_fraction"], "fraction", "Same rule on raw pixels; mostly noise.")}
    for v in summary.values(): v["verified"] = True
    summary["low_spot_fraction"]["verified"] = False; summary["low_spot_fraction_raw"]["verified"] = False
    res = {"preset_id": preset, "generated_at": now(), "source": S, "items": ids,
           "method": {"grid": "EPSG:32610, 30 m, edges on multiples of 30 m (same lattice as backend/field grid.geojson)",
                      "resample": "bilinear from 1 arc-second NASADEM", "slope": "Horn 3x3, percent = 100*tan(angle)",
                      "low_spot": f"elev - mean(elev within {FOCAL_R:.0f} m radius) <= -{LOW_M} m",
                      "cell_join": "30 m lattice pixel containing the centroid of each grid.geojson cell"},
           "field_summary": summary, "field_stats": field_stats, "box_stats": box_stats,
           "cells": cells, "cells_without_value": miss, "box_2km": box}
    write_json(OUT / preset / "terrain.json", res)
    print(preset, "field", {k: round(v, 3) for k, v in field_stats.items()}, "box", {k: round(v, 3) for k, v in box_stats.items()}, "cells", len(cells), "missing", miss)

if __name__ == "__main__":
    for p in sys.argv[1:] or PRESETS: run(p)
