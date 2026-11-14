"""OPERA DSWx-HLS (OPERA_L3_DSWX-HLS_V1) reduced to fraction of field polygon classed water per scene.
Windows: Colusa every winter Nov 1-Apr 15 from 2016-17 to the current one (CMR has no scenes for the 2020-21 and
2021-22 winters over this field) and Kings/Tulare spring 2023 (Mar 1-Jun 30). Reprocessed scenes (v1.0 and v1.1 of
the same tile and overpass) are de-duplicated, keeping the newest production."""
import tempfile
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
# WTR band classes (OPERA DSWx-HLS product spec): 0 not water, 1 open water, 2 partial surface water,
# 252 snow/ice, 253 cloud/cloud shadow, 254 ocean masked, 255 fill
earthaccess.login(strategy="environment")
for p in a.preset or C.PRESETS:
    geom = C.field_geometry(p)
    rows = []
    for (s, e) in WINDOWS[p]:
        if a.start:
            s = max(s, a.start)
        if a.end:
            e = min(e, a.end)
        grans = earthaccess.search_data(short_name="OPERA_L3_DSWX-HLS_V1", version="1.0",
                                        bounding_box=geom.bounds, temporal=(s, e), count=a.limit or -1)
        print(f"[{p}] {s}..{e}: {len(grans)} granules")
        links, gmeta = [], {}
        for g in grans:
            for l in g.data_links():
                if l.endswith("_B01_WTR.tif"):
                    links.append(l)
                    gmeta[Path(l).name] = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
        with tempfile.TemporaryDirectory() as td:
            files = earthaccess.download(links, td, show_progress=False, threads=8) if links else []
            for f in files:
                f = str(f)
                with rasterio.open(f) as ds:
                    tr = pyproj.Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True).transform
                    try:
                        arr, _ = rmask(ds, [mapping(transform(tr, geom))], crop=True, nodata=255)
                    except ValueError:  # polygon outside this tile
                        Path(f).unlink(missing_ok=True)
                        continue
                a0 = arr[0]
                # pixels inside polygon only: rmask fills outside with 255 same as product fill -> fine, both excluded
                inside = a0 != 255
                n = int(inside.sum())
                if n:
                    rows.append({"scene": Path(f).name.split("_B01")[0], "datetime": gmeta.get(Path(f).name),
                                 "n_pixels": n, "frac_open_water": float((a0 == 1).sum() / n),
                                 "frac_partial_water": float((a0 == 2).sum() / n),
                                 "frac_cloud_snow": float(np.isin(a0, [252, 253]).sum() / n)})
                Path(f).unlink(missing_ok=True)
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
        "params": {"windows": WINDOWS[p], "bbox": geom.bounds},
        "timestep": "per HLS scene (Landsat/Sentinel-2 overpass)", "units": {"frac_*": "fraction of field polygon pixels"},
        "native_res_m": 30, "fill_value": 255,
        "quality_handling": "Class 1 open water + class 2 partial surface water = frac_water; cloud/shadow and snow/ice "
                            "(253/252) reported as frac_cloud_snow, not counted as water or dry; filter on frac_clear "
                            "(>= 0.8 suggested). Label as WATER, never as bare."})
