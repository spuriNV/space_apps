"""OPERA DSWx-HLS (OPERA_L3_DSWX-HLS_V1) reduced to fraction of field polygon classed water per scene.
Windows: Colusa every winter Nov 1-Apr 15 from 2016-17 to the current one (CMR has no scenes for the 2020-21 and
2021-22 winters over this field) and Kings/Tulare spring 2023 (Mar 1-Jun 30). Reprocessed scenes (v1.0 and v1.1 of
the same tile and overpass) are de-duplicated, keeping the newest production."""
import tempfile
import time
from pathlib import Path

from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C

ap = C.common_args("OPERA DSWx field water fraction")
a = ap.parse_args()
C.require_creds()
import earthaccess
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask as rmask
from shapely.geometry import mapping
import pyproj
from shapely.ops import transform

WINDOWS = {
    "car_colusa_rice": [(f"{y}-11-01", f"{y + 1}-04-15") for y in range(2016, 2027)],
    "caf_tulare_forage": [("2023-03-01", "2023-06-30")],
}
# Registry fields (backend/fields/registry.json): rice = the last three winters plus the current one (2022-23 is the
# wet winter after the 2022 drought); forage = spring 2023 (Tulare Lake re-flooding). Kept short because DSWx is
# read by downloading whole WTR tiles.
FAMILY_WINDOWS = {"rice": [(f"{y}-11-01", f"{y + 1}-04-15") for y in range(2022, 2027)],
                  "forage": [("2023-03-01", "2023-06-30")]}


def windows(p):
    return WINDOWS.get(p) or FAMILY_WINDOWS[C.fieldreg.get(p)["family"]]


# WTR band classes (OPERA DSWx-HLS product spec): 0 not water, 1 open water, 2 partial surface water,
# 252 snow/ice, 253 cloud/cloud shadow, 254 ocean masked, 255 fill
earthaccess.login(strategy="environment")
presets = a.preset or C.PRESETS
geoms = {p: C.field_geometry(p) for p in presets}
# 1. search per field and window; a WTR tile that covers several fields is downloaded once and masked for each
need, gmeta = {}, {}
for p in presets:
    for (s, e) in windows(p):
        if a.start:
            s = max(s, a.start)
        if a.end:
            e = min(e, a.end)
        if s > e:
            continue
        for attempt in range(5):   # CMR search sometimes drops the connection; retry
            try:
                grans = earthaccess.search_data(short_name="OPERA_L3_DSWX-HLS_V1", version="1.0",
                                                bounding_box=geoms[p].bounds, temporal=(s, e), count=a.limit or -1)
                break
            except Exception as ex:  # noqa: BLE001
                print(f"  search retry {attempt + 1}: {type(ex).__name__}", flush=True)
                time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(f"CMR search failed for {p} {s}..{e}")
        print(f"[{p}] {s}..{e}: {len(grans)} granules", flush=True)
        for g in grans:
            for l in g.data_links():
                if l.endswith("_B01_WTR.tif"):
                    need.setdefault(l, set()).add(p)
                    gmeta[Path(l).name] = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
print(f"{len(need)} distinct WTR tiles for {len(presets)} fields", flush=True)
rows_by = {p: [] for p in presets}
links = sorted(need)
for i in range(0, len(links), 200):
    batch = links[i:i + 200]
    with tempfile.TemporaryDirectory() as td:
        files = earthaccess.download(batch, td, show_progress=False, threads=8)
        for f in files:
            f = str(f)
            with rasterio.open(f) as ds:
                tr = pyproj.Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True).transform
                for p in need.get(next(l for l in batch if l.endswith(Path(f).name)), ()):
                    try:
                        arr, _ = rmask(ds, [mapping(transform(tr, geoms[p]))], crop=True, nodata=255)
                    except ValueError:  # polygon outside this tile
                        continue
                    a0 = arr[0]
                    inside = a0 != 255
                    n = int(inside.sum())
                    if n:
                        rows_by[p].append({"scene": Path(f).name.split("_B01")[0], "datetime": gmeta.get(Path(f).name),
                                           "n_pixels": n, "frac_open_water": float((a0 == 1).sum() / n),
                                           "frac_partial_water": float((a0 == 2).sum() / n),
                                           "frac_cloud_snow": float(np.isin(a0, [252, 253]).sum() / n)})
            Path(f).unlink(missing_ok=True)
    print(f"  {min(i + 200, len(links))}/{len(links)} tiles read", flush=True)
for p in presets:
    geom = geoms[p]
    rows = rows_by[p]
    df = pd.DataFrame(rows)
    if len(df):
        df["datetime"] = pd.to_datetime(df["datetime"])
        df["frac_water"] = df["frac_open_water"] + df["frac_partial_water"]
        df["frac_clear"] = 1 - df["frac_cloud_snow"]
        # scene = OPERA_L3_DSWx-HLS_<tile>_<sensing>_<production>_<sensor>_30_<ver>: keep newest production per tile+sensing+sensor
        parts = df.scene.str.split("_")
        df["_key"] = parts.str[3] + "_" + parts.str[4] + "_" + parts.str[6]
        df["_prod"] = parts.str[5]
        df = df.sort_values("_prod").drop_duplicates("_key", keep="last").drop(columns=["_key", "_prod"])
        df = df.sort_values("datetime").reset_index(drop=True)
    C.write_cache(p, "dswx", df, {
        "url": "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=OPERA_L3_DSWX-HLS_V1 "
               "(archive.podaac.earthdata.nasa.gov, B01_WTR.tif only)",
        "collection": "OPERA_L3_DSWX-HLS_V1 v1.0 (C2617126679-POCLOUD); NOT available in AppEEARS",
        "params": {"windows": windows(p), "bbox": geom.bounds},
        "timestep": "per HLS scene (Landsat/Sentinel-2 overpass)", "units": {"frac_*": "fraction of field polygon pixels"},
        "native_res_m": 30, "fill_value": 255,
        "quality_handling": "Class 1 open water + class 2 partial surface water = frac_water; cloud/shadow and snow/ice "
                            "(253/252) reported as frac_cloud_snow, not counted as water or dry; filter on frac_clear "
                            "(>= 0.8 suggested). Label as WATER, never as bare."})
