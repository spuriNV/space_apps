"""SMAP L4 surface/root-zone soil moisture (SPL4SMGP v008) via Cloud OPeNDAP: daily means of the 3-hourly granules.

Same columns as fetch_smap_l4.py (AppEEARS), which has been stuck in the AppEEARS queue for hours; this route streams
one DAP2 .ascii hyperslab per 3-hourly granule covering every field's 9 km EASE-Grid 2.0 cell (opendap.earthdata.nasa.gov,
Earthdata login from the repo-root .env), then averages the 8 granules of each UTC day (granule centre time).

Granule values are kept per year in data/cache/_smap_l4_opendap/<batch>/<year>.parquet, so a rerun after a timeout or a
crash only fetches the years still missing (and always refreshes the current year).

Usage: uv run python fetch_smap_l4_opendap.py [--preset id ...] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--workers 16]
"""
from __future__ import annotations

import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from pyproj import Transformer

from fieldshift_nasa import common as C

ap = C.common_args("SMAP L4 soil moisture via Cloud OPeNDAP")
ap.add_argument("--workers", type=int, default=16)
a = ap.parse_args()
C.require_creds()
import earthaccess  # noqa: E402

SHORT, VER = "SPL4SMGP", "008"
VARS = ["sm_surface", "sm_rootzone", "sm_profile", "sm_rootzone_pctl", "sm_rootzone_wetness", "precipitation_total_surface_flux"]
FILL = -9999.0
start, end = a.start or "2015-03-31", a.end or C.today()
presets = a.preset or C.PRESETS
pts = {p: C.field_point(p) for p in presets}
batch = "fields_" + hashlib.sha1(",".join(sorted(pts)).encode()).hexdigest()[:8]
RAW = C.CACHE / "_smap_l4_opendap" / batch
RAW.mkdir(parents=True, exist_ok=True)
(RAW.parent / ".gitignore").write_text("*\n")   # raw granule values stay local (like data/cache/_appeears)

earthaccess.login(strategy="environment")
sess = earthaccess.get_requests_https_session()


def opendap_url(g):
    for u in g["umm"].get("RelatedUrls", []):
        if u.get("Subtype") == "OPENDAP DATA":
            return u["URL"]
    return None


def centre_time(g):
    m = re.search(r"_gph_(\d{8}T\d{6})_", g["umm"]["GranuleUR"])
    return pd.Timestamp(m.group(1)) if m else pd.Timestamp(g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:19]) + pd.Timedelta(minutes=90)


def get(url, tries=5):
    err = None
    for k in range(tries):
        try:
            r = sess.get(url, timeout=120)
            if r.status_code == 200:
                return r.text
            err = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"[:200]
        time.sleep(3 * (k + 1))
    raise RuntimeError(err)


def ascii_rows(text, name):
    rows = [ln.split(",", 1)[1] for ln in text.splitlines() if ln.startswith(f"{name}[")]
    return np.array([[float(x) for x in ln.split(",")] for ln in rows])


# grid index of each field's cell, from the x/y coordinate vectors of one granule (EASE-Grid 2.0 global, EPSG:6933)
first = earthaccess.search_data(short_name=SHORT, version=VER, temporal=(end, end), count=1) or \
    earthaccess.search_data(short_name=SHORT, version=VER, temporal=(start, start), count=1)
txt = get(opendap_url(first[0]) + ".ascii?x,y")
xs = np.array([float(v) for v in re.search(r"^x, (.*)$", txt, re.M).group(1).split(",")])
ys = np.array([float(v) for v in re.search(r"^y, (.*)$", txt, re.M).group(1).split(",")])
tf = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
idx = {}
for p, (lon, lat) in pts.items():
    x, y = tf.transform(lon, lat)
    idx[p] = (int(np.abs(ys - y).argmin()), int(np.abs(xs - x).argmin()))   # (row, col)
r0, r1 = min(v[0] for v in idx.values()), max(v[0] for v in idx.values())
c0, c1 = min(v[1] for v in idx.values()), max(v[1] for v in idx.values())
print(f"  {len(pts)} fields -> rows {r0}..{r1}, cols {c0}..{c1} of the 9 km EASE2 grid", flush=True)
G = "%2FGeophysical_Data%2F"
CE = ",".join(f"{G}{v}%5B{r0}:{r1}%5D%5B{c0}:{c1}%5D" for v in VARS)


def one(g):
    t = centre_time(g)
    u = opendap_url(g)
    if not u:
        return t, None, "no OPENDAP link"
    try:
        text = get(f"{u}.ascii?{CE}")
        grids = {v: ascii_rows(text, f"/Geophysical_Data/{v}") for v in VARS}
        for v, gr in grids.items():
            if gr.shape != (r1 - r0 + 1, c1 - c0 + 1):
                raise RuntimeError(f"unexpected shape {gr.shape} for {v}")
        return t, grids, None
    except Exception as e:  # noqa: BLE001
        return t, None, str(e)[:200]


def fetch_year(y):
    s, e = max(start, f"{y}-01-01"), min(end, f"{y}-12-31")
    grans = earthaccess.search_data(short_name=SHORT, version=VER, temporal=(s, e + "T23:59:59"), count=-1)
    t0, res = time.time(), []
    with ThreadPoolExecutor(a.workers) as ex:
        for n, r in enumerate(ex.map(one, grans), 1):
            res.append(r)
            if n % 500 == 0:
                print(f"  {y}: {n}/{len(grans)} ({time.time() - t0:.0f}s)", flush=True)
    rows = []
    for t, grids, err in res:
        for p, (ri, ci) in idx.items():
            row = {"field": p, "time": t, "error": err}
            for v in VARS:
                x = float("nan") if grids is None else float(grids[v][ri - r0, ci - c0])
                row[v] = float("nan") if (x == FILL or x < -990) else x
            rows.append(row)
    df = pd.DataFrame(rows)
    nerr = int(sum(1 for _, g, _ in res if g is None))
    print(f"  {y}: {len(grans)} granules, {nerr} failed, {time.time() - t0:.0f}s", flush=True)
    return df, len(grans), nerr


years = range(int(start[:4]), int(end[:4]) + 1)
parts, n_gran, n_err = [], 0, 0
for y in years:
    f = RAW / f"{y}.parquet"
    if f.exists() and y < int(end[:4]):
        d = pd.read_parquet(f)
        if d.error.isna().all():
            parts.append(d)
            n_gran += d.time.nunique()
            print(f"  {y}: cached ({d.time.nunique()} granules)", flush=True)
            continue
    d, ng, ne = fetch_year(y)
    if not d.empty:
        d.to_parquet(f, index=False)
    parts.append(d)
    n_gran, n_err = n_gran + ng, n_err + ne

raw = pd.concat(parts, ignore_index=True)
raw = raw[raw.error.isna()].drop_duplicates(["field", "time"])   # a granule ending at 00:00 is found by both years' searches
raw["date"] = raw.time.dt.normalize()
for p, (ri, ci) in idx.items():
    d = raw[raw.field == p]
    day = d.groupby("date")[VARS].mean()
    day["n_granules"] = d.groupby("date").size()
    day = day.reset_index()
    day["grid_row"], day["grid_col"] = ri, ci
    lon, lat = pts[p]
    C.write_cache(p, "smap_l4", day, {
        "url": f"https://opendap.earthdata.nasa.gov (CMR {SHORT}.{VER}, provider NSIDC_CPRD)", "collection": f"{SHORT}.{VER}",
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end, "variables": [f"/Geophysical_Data/{v}" for v in VARS],
                   "ease2_row_col": [ri, ci]},
        "timestep": "daily mean of the 3-hourly granules (UTC day of granule centre time); n_granules per day",
        "units": {"sm_surface": "m3/m3", "sm_rootzone": "m3/m3", "sm_profile": "m3/m3", "sm_rootzone_pctl": "percent",
                  "sm_rootzone_wetness": "1", "precipitation_total_surface_flux": "kg m-2 s-1"},
        "native_res_m": 9000, "fill_value": FILL,
        "quality_handling": "SPL4SMGP is a gap-free model-assimilation product with no per-cell quality flag; only fill "
                            "(-9999) -> NaN. Surface soil moisture over flooded rice is model-based, not retrieved.",
        "access": "Cloud OPeNDAP DAP2 ascii hyperslab, one request per granule for all fields",
        "n_granules": int(n_gran), "n_read_errors": int(n_err), "raw_dir": str(RAW.relative_to(C.REPO))})
