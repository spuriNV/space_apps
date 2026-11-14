"""CDL zonal statistics: majority class and purity inside a polygon."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

from .common import cache


@lru_cache(maxsize=None)
def _raster(preset: str, year: int):
    p = cache(preset) / "rasters" / f"cdl_{year}.tif"
    if not p.exists():
        return None
    with rasterio.open(p) as src:
        return src.read(1), src.transform, src.res[0]


def cdl_year_stats(preset: str, geom_5070, year: int):
    """Pixels whose centre is inside the polygon (EPSG:5070 geometry). None if raster missing/outside."""
    r = _raster(preset, year)
    if r is None:
        return None
    arr, tr, res = r
    minx, miny, maxx, maxy = geom_5070.bounds
    win = from_bounds(minx - res, miny - res, maxx + res, maxy + res, tr).round_offsets().round_lengths()
    r0, c0 = max(win.row_off, 0), max(win.col_off, 0)
    r1, c1 = min(win.row_off + win.height, arr.shape[0]), min(win.col_off + win.width, arr.shape[1])
    if r1 <= r0 or c1 <= c0:
        return None
    sub = arr[r0:r1, c0:c1]
    sub_tr = tr * rasterio.Affine.translation(c0, r0)
    inside = ~geometry_mask([geom_5070], sub.shape, sub_tr, all_touched=False)
    vals = sub[inside]
    vals = vals[vals != 0]
    if vals.size == 0:
        return None
    codes, counts = np.unique(vals, return_counts=True)
    frac = {int(c): float(n) / vals.size for c, n in zip(codes, counts)}
    maj = int(codes[np.argmax(counts)])
    return {"majority": maj, "purity": frac[maj], "fractions": frac, "n_pixels": int(vals.size), "res_m": res}
