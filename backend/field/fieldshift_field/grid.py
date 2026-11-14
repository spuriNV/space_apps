"""30 m field grid (spec B2.14) with per-cell Sentinel-2 NDVI -> out/<preset>/grid.geojson.

Cells: 30 m squares in EPSG:32610 on a grid whose edges are multiples of 30 m (this matches the
HLS/Sentinel-2 30 m tiling in UTM 10N; the CAF field lies in UTM zone 11 for HLS, so there the
cells are not HLS-aligned), clipped to the polygon, output in EPSG:4326.

Per cell value = mean of the Sentinel-2 10 m NDVI pixels (clear pixels only, pixel centre inside the
polygon) whose centre falls in the cell (10 -> 30 m mean, as spec B2.14 says). Coarser data is never
resampled down to this grid.

Layers
  ndvi_<year>_q<1-4>   median over scenes (field clear_frac >= 0.5) of the cell's NDVI, calendar quarters
  ndvi_d_<YYYYMMDD>    single clear scenes near 15 Jan / Apr / Jul / Oct of 2021, 2022, 2023
A layer value is null when the cell had no clear pixel; n_<layer> holds the number of scenes/pixels used.

Usage: uv run python -m fieldshift_field.grid [preset ...]
"""
from __future__ import annotations

import json
import math
import sys
import warnings

import numpy as np
import pandas as pd
from shapely import transform as shp_transform
from shapely.geometry import box, mapping

from .common import PRESETS, WORK_CRS, cache, now, out, polygon_in, to_crs, today, write_json

CELL = 30.0
KEY_YEARS = (2021, 2022, 2023)
KEY_DAYS = ("01-15", "04-15", "07-15", "10-15")
SEASON_YEARS = range(2016, 2026)


def _tf(t):
    return lambda xy: np.column_stack(t.transform(xy[:, 0], xy[:, 1]))


def cells(preset):
    g = polygon_in(preset, WORK_CRS)
    minx, miny, maxx, maxy = g.bounds
    x0, y1 = math.floor(minx / CELL) * CELL, math.ceil(maxy / CELL) * CELL
    nc, nr = math.ceil((maxx - x0) / CELL), math.ceil((y1 - miny) / CELL)
    cl = []
    for r in range(nr):
        for c in range(nc):
            sq = box(x0 + c * CELL, y1 - (r + 1) * CELL, x0 + (c + 1) * CELL, y1 - r * CELL)
            inter = sq.intersection(g)
            if inter.is_empty or inter.area < 1.0:
                continue
            cl.append({"row": r, "col": c, "geom": inter, "frac": inter.area / (CELL * CELL)})
    return cl, (x0, y1, nr, nc)


def scene_cell_means(ndvi, tr, epsg, grid):
    x0, y1, nr, nc = grid
    rows, cols = np.nonzero(np.isfinite(ndvi))
    if rows.size == 0:
        return None
    a, b_, c, d, e, f = tr
    xs = c + (cols + 0.5) * a
    ys = f + (rows + 0.5) * e
    if f"EPSG:{epsg}" != WORK_CRS:
        xs, ys = to_crs(f"EPSG:{epsg}", WORK_CRS).transform(xs, ys)
    ci = np.floor((xs - x0) / CELL).astype(int)
    ri = np.floor((y1 - ys) / CELL).astype(int)
    ok = (ci >= 0) & (ci < nc) & (ri >= 0) & (ri < nr)
    idx = ri[ok] * nc + ci[ok]
    v = ndvi[rows, cols][ok].astype("float64")
    s = np.bincount(idx, weights=v, minlength=nr * nc)
    n = np.bincount(idx, minlength=nr * nc)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = s / n
    m[n == 0] = np.nan
    return m, n


def build(preset):
    c = cache(preset)
    stack = np.load(c / "rasters" / "s2_ndvi_stack.npz")
    info = json.loads((c / "rasters" / "s2_ndvi_stack.json").read_text())
    s2 = pd.read_parquet(c / "s2.parquet").set_index("scene_id")
    cl, grid = cells(preset)
    nr, nc = grid[2], grid[3]
    per_scene = {}
    for sid in stack.files:
        r = scene_cell_means(stack[sid].astype("float32"), info[sid]["transform"], info[sid]["epsg"], grid)
        if r is not None:
            per_scene[sid] = r
    layers, counts, layer_meta = {}, {}, []
    # seasonal composites
    ok_scenes = [sid for sid in per_scene if s2.loc[sid, "clear_frac"] >= 0.5]
    dates = {sid: pd.Timestamp(s2.loc[sid, "date"]) for sid in ok_scenes}
    for y in SEASON_YEARS:
        for q in range(1, 5):
            sel = [sid for sid in ok_scenes if dates[sid].year == y and dates[sid].quarter == q]
            if not sel:
                continue
            arr = np.vstack([per_scene[s][0] for s in sel])
            key = f"ndvi_{y}_q{q}"
            with np.errstate(all="ignore"), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                layers[key] = np.nanmedian(arr, axis=0)
            counts[key] = np.sum(np.isfinite(arr), axis=0)
            layer_meta.append({"key": key, "kind": "quarter_median", "year": y, "quarter": q, "n_scenes": len(sel)})
    # key dates
    for y in KEY_YEARS:
        for md in KEY_DAYS:
            target = pd.Timestamp(f"{y}-{md}")
            cand = [(abs((pd.Timestamp(s2.loc[sid, "date"]) - target).days), sid) for sid in per_scene
                    if s2.loc[sid, "clear_frac"] >= 0.95 and abs((pd.Timestamp(s2.loc[sid, "date"]) - target).days) <= 20]
            if not cand:
                layer_meta.append({"key": None, "kind": "scene", "target": str(target.date()),
                                   "note": "no scene with clear_frac >= 0.95 within 20 days"})
                continue
            _, sid = min(cand)
            dt = s2.loc[sid, "date"].replace("-", "")
            key = f"ndvi_d_{dt}"
            layers[key], counts[key] = per_scene[sid]
            layer_meta.append({"key": key, "kind": "scene", "target": str(target.date()), "date": s2.loc[sid, "date"],
                               "scene_id": sid, "field_clear_frac": round(float(s2.loc[sid, "clear_frac"]), 3)})
    back = to_crs(WORK_CRS, "EPSG:4326")
    feats = []
    for cell in cl:
        i = cell["row"] * nc + cell["col"]
        props = {"cell_id": f"r{cell['row']:03d}c{cell['col']:03d}", "row": cell["row"], "col": cell["col"],
                 "area_m2": round(cell["geom"].area, 1), "frac_in_field": round(cell["frac"], 3)}
        for k, v in layers.items():
            props[k] = None if not np.isfinite(v[i]) else round(float(v[i]), 3)
            props[f"n_{k}"] = int(counts[k][i])
        feats.append({"type": "Feature", "properties": props,
                      "geometry": mapping(shp_transform(cell["geom"], _tf(back)))})
    fc = {"type": "FeatureCollection", "name": f"{preset}_field_grid_30m",
          "crs_note": "Coordinates EPSG:4326 (lon, lat). Cells built in EPSG:32610, 30 m, edges at multiples of 30 m.",
          "generated_at": now(),
          "source": {"id": "s2_l2a_mpc", "title": "Sentinel-2 L2A NDVI (B08, B04), SCL-masked, 10 m -> 30 m cell mean",
                     "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", "accessed": today(), "verified": True},
          "layers": layer_meta, "n_cells": len(feats), "features": feats}
    (out(preset) / "grid.geojson").write_text(json.dumps(fc, separators=(",", ":")))
    print(f"{preset}: {len(feats)} cells, {len(layers)} layers "
          f"({sum(m['kind']=='scene' and m.get('key') is not None for m in layer_meta)} dates)")
    return fc


if __name__ == "__main__":
    for p in (sys.argv[1:] or list(PRESETS)):
        build(p)
