"""HLS v2.0 (HLSL30 + HLSS30, NASA LP DAAC) field-median NDVI/NDWI per scene, read with the Earthdata login.
Same method as backend/nasa_open/nasa_open/hls.py (which reads the anonymous Planetary Computer copy, 2017-08..2025):
only the polygon window of each COG is read; Fmask clear = not cloud / adjacent / shadow / snow-ice (water kept);
NDVI with narrow NIR (B05 on L30, B8A on S30), NDWI = (Green-NIR)/(Green+NIR).
Default windows fill what the Planetary Computer copy lacks (it is sparse before 2020): 2016-01-01..2019-12-31 and 2026-01-01..today.
Writes data/cache/<id>/hls_lpdaac.parquet + .meta.json (columns match hls.parquet)."""
import concurrent.futures as cf
import math
import os
import time
import warnings

import numpy as np
import pandas as pd

from fieldshift_nasa import common as C

warnings.filterwarnings("ignore")
ap = C.common_args("HLS v2.0 from LP DAAC")
a = ap.parse_args()
C.require_creds()
import earthaccess  # noqa: E402
import pyproj  # noqa: E402
import rasterio  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402
from rasterio.windows import Window, from_bounds  # noqa: E402
from shapely.ops import transform  # noqa: E402

BANDS = {"HLSL30": {"green": "B03", "red": "B04", "nir": "B05"}, "HLSS30": {"green": "B03", "red": "B04", "nir": "B8A"}}
WINDOWS = [(a.start, a.end)] if a.start else [("2016-01-01", "2019-12-31"), ("2026-01-01", a.end or C.today())]
earthaccess.login(strategy="environment")
# GDAL follows the LP DAAC -> URS -> S3 redirect with netrc credentials and a cookie jar. The netrc is a temporary
# file (mode 600) outside the repo, deleted at exit; credentials come from repo-root .env and are never printed.
import atexit, tempfile  # noqa: E401,E402
_td = tempfile.mkdtemp(prefix="fs_hls_")
_netrc = os.path.join(_td, "netrc")
with open(os.open(_netrc, os.O_WRONLY | os.O_CREAT, 0o600), "w") as fh:
    fh.write(f"machine urs.earthdata.nasa.gov login {os.environ['EARTHDATA_USERNAME']} password {os.environ['EARTHDATA_PASSWORD']}\n")
atexit.register(lambda: __import__("shutil").rmtree(_td, ignore_errors=True))
GDAL = dict(GDAL_HTTP_NETRC="YES", GDAL_HTTP_NETRC_FILE=_netrc, GDAL_HTTP_COOKIEFILE=os.path.join(_td, "cookies"),
            GDAL_HTTP_COOKIEJAR=os.path.join(_td, "cookies"), GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2",
            GDAL_HTTP_UNSAFESSL="NO", VSI_CACHE="TRUE")


def scene(g, geom):
    links = {l.rsplit(".", 2)[-2]: l for l in g.data_links(access="external") if l.endswith(".tif")}
    gid = g["umm"]["GranuleUR"]
    plat = gid.split(".")[1]
    plat = "HLSL30" if plat == "L30" else "HLSS30"
    dt = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
    last = None
    with rasterio.Env(**GDAL):
        for attempt in range(4):
            try:
                with rasterio.open("/vsicurl/" + links["Fmask"]) as src:
                    tr_ = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
                    gg = transform(tr_, geom)
                    l, b, r, t = src.bounds
                    if gg.bounds[2] < l or gg.bounds[0] > r or gg.bounds[3] < b or gg.bounds[1] > t:
                        return None
                    win = from_bounds(*gg.bounds, src.transform)
                    win = Window(math.floor(win.col_off) - 1, math.floor(win.row_off) - 1, math.ceil(win.width) + 3, math.ceil(win.height) + 3)
                    fm = src.read(1, window=win, boundless=True, fill_value=255)
                    tr = src.window_transform(win)
                    epsg = src.crs.to_epsg()
                bands = {}
                for k, bn in BANDS[plat].items():
                    with rasterio.open("/vsicurl/" + links[bn]) as s:
                        bands[k] = s.read(1, window=win, boundless=True, fill_value=-9999).astype("float32")
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"{gid}: {last}")
    h, w = fm.shape
    inside = ~geometry_mask([gg], (h, w), tr, all_touched=False)
    bit = lambda k: ((fm >> k) & 1) == 1  # noqa: E731
    clear = inside & ~(bit(1) | bit(2) | bit(3) | bit(4)) & (fm != 255)
    for v in bands.values():
        clear &= v > -9999
    n_poly, n_valid = int(inside.sum()), int(clear.sum())
    if not n_poly:
        return None
    cc = next((x["Values"][0] for x in g["umm"].get("AdditionalAttributes", []) if x["Name"] == "CLOUD_COVERAGE"), None)
    row = {"scene_id": gid, "datetime": dt, "platform": plat, "sensor": None, "tile": gid.split(".")[2], "epsg": epsg,
           "scene_cloud_pct": float(cc) if cc is not None else math.nan, "n_pixels_poly": n_poly, "n_valid": n_valid,
           "clear_frac": n_valid / n_poly, "water_frac": float(np.mean(bit(5)[clear])) if n_valid else math.nan}
    if n_valid:
        bb = {k: v[clear] * 1e-4 for k, v in bands.items()}
        with np.errstate(divide="ignore", invalid="ignore"):
            idx = {"ndvi": (bb["nir"] - bb["red"]) / (bb["nir"] + bb["red"]), "ndwi": (bb["green"] - bb["nir"]) / (bb["green"] + bb["nir"])}
        for n, v in idx.items():
            v = v[np.isfinite(v)]
            p10, p50, p90 = np.percentile(v, [10, 50, 90]) if v.size else (math.nan,) * 3
            row.update({f"{n}_med": float(p50), f"{n}_p10": float(p10), f"{n}_p90": float(p90)})
    else:
        for n in ("ndvi", "ndwi"):
            row.update({f"{n}_med": math.nan, f"{n}_p10": math.nan, f"{n}_p90": math.nan})
    return row


for p in a.preset or C.PRESETS:
    geom = C.field_geometry(p)
    t0 = time.time()
    grans = []
    for s, e in WINDOWS:
        for sn in ("HLSL30", "HLSS30"):
            grans += earthaccess.search_data(short_name=sn, version="2.0", bounding_box=geom.bounds, temporal=(s, e),
                                             count=a.limit or -1)
    print(p, len(grans), "granules", flush=True)
    rows, errors = [], []
    with cf.ThreadPoolExecutor(12) as ex:
        futs = {ex.submit(scene, g, geom): g["umm"]["GranuleUR"] for g in grans}
        for n, f in enumerate(cf.as_completed(futs), 1):
            try:
                rr = f.result()
                if rr:
                    rows.append(rr)
            except Exception as e:  # noqa: BLE001
                errors.append({"scene_id": futs[f], "error": str(e)[:300]})
            if n % 100 == 0:
                print(f"  {n}/{len(grans)} {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["date"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df = df.sort_values("datetime").reset_index(drop=True)
    C.write_cache(p, "hls_lpdaac", df, {
        "url": "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=HLSL30|HLSS30&version=2.0 "
               "(data.lpdaac.earthdatacloud.nasa.gov COGs, polygon window read over HTTPS with an Earthdata bearer token)",
        "collection": ["HLSL30.002", "HLSS30.002"], "params": {"windows": WINDOWS, "bands": BANDS},
        "credit": "HLS v2.0, NASA/USGS (Masek et al. 2021), doi:10.5067/HLS/HLSL30.002 and 10.5067/HLS/HLSS30.002, NASA LP DAAC",
        "timestep": "per scene", "native_res_m": 30, "fill_value": "NaN",
        "units": {"ndvi": "unitless", "ndwi": "unitless", "clear_frac": "fraction of polygon pixels"},
        "quality_handling": "same as backend/nasa_open hls.parquet: Fmask bits 1-4 masked (cloud, adjacent, shadow, snow/ice), "
                            "water bit 5 kept and reported as water_frac. Scenes whose tile misses the polygon are dropped.",
        "n_granules_found": len(grans), "errors": errors[:50], "n_errors": len(errors), "seconds": round(time.time() - t0)})
