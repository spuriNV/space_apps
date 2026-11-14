"""Point time series from gridded netCDF granules via earthaccess (streamed range reads, no full downloads)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd


def point_series(short_name: str, version: str, variables: list[str], lon: float, lat: float,
                 start: str, end: str, fills: dict[str, float], limit: int | None = None,
                 workers: int = 8) -> tuple[pd.DataFrame, dict]:
    import earthaccess
    import xarray as xr

    earthaccess.login(strategy="environment")
    grans = earthaccess.search_data(short_name=short_name, version=version,
                                    temporal=(start, end), count=limit or -1)
    if not grans:
        raise RuntimeError(f"CMR returned 0 granules for {short_name}.{version} {start}..{end}")
    print(f"  {len(grans)} granules for {short_name}.{version}")
    files = earthaccess.open(grans)
    info: dict = {}

    def one(i: int):
        g = grans[i]
        date = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]
        for attempt in range(3):
            try:
                with xr.open_dataset(files[i], engine="h5netcdf", decode_times=False) as ds:
                    pt = ds[variables].sel(lon=lon, lat=lat, method="nearest")
                    row = {"date": date, "grid_lon": float(pt["lon"]), "grid_lat": float(pt["lat"])}
                    for v in variables:
                        row[v] = float(np.asarray(pt[v]).squeeze())
                        if v in fills and row[v] == fills[v]:
                            row[v] = float("nan")
                        elif row[v] < -990:  # any residual fill
                            row[v] = float("nan")
                    return row
            except Exception as e:  # noqa: BLE001
                err = e
        return {"date": date, "error": f"{type(err).__name__}: {err}"[:200]}

    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, range(len(grans))))
    df = pd.DataFrame(rows)
    errs = df["error"].notna().sum() if "error" in df else 0
    info["n_granules"] = len(grans)
    info["n_read_errors"] = int(errs)
    if errs:
        print(f"  WARNING {errs} granules failed to read (kept as rows with 'error')")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True), info


def latest_granule_date(short_name: str, version: str) -> str:
    """Start date (YYYY-MM-DD) of the newest granule in CMR (no auth)."""
    import requests
    r = requests.get("https://cmr.earthdata.nasa.gov/search/granules.json",
                     params={"short_name": short_name, "version": version, "sort_key": "-start_date", "page_size": 1},
                     timeout=60)
    r.raise_for_status()
    return r.json()["feed"]["entry"][0]["time_start"][:10]


def opendap_points(short_name: str, version: str, points: dict[str, tuple[float, float]], start: str, end: str,
                   variables: list[str], lon0: float, lat0: float, step: float, order: str, fill: float,
                   limit: int | None = None, workers: int = 16) -> tuple[dict[str, pd.DataFrame], dict]:
    """Point values for several points from a regular lon/lat grid via Cloud OPeNDAP (DAP2 .ascii): ONE hyperslab request
    per granule covering all points. Cell centres lon0 + step*i, lat0 + step*j. order = 'lonlat' (dims time, lon, lat:
    IMERG) or 'latlon' (dims time, lat, lon: GRACE-DA). Returns ({key: DataFrame(date, grid_lon, grid_lat, *variables)}, info)."""
    import time
    import earthaccess

    earthaccess.login(strategy="environment")
    sess = earthaccess.get_requests_https_session()
    grans = earthaccess.search_data(short_name=short_name, version=version, temporal=(start, end), count=limit or -1)
    if not grans:
        raise RuntimeError(f"CMR returned 0 granules for {short_name}.{version} {start}..{end}")
    print(f"  {len(grans)} granules for {short_name}.{version} (OPeNDAP)", flush=True)
    idx = {k: (int(round((lo - lon0) / step)), int(round((la - lat0) / step))) for k, (lo, la) in points.items()}
    i0, i1 = min(v[0] for v in idx.values()), max(v[0] for v in idx.values())
    j0, j1 = min(v[1] for v in idx.values()), max(v[1] for v in idx.values())
    sl = f"%5B{i0}:{i1}%5D%5B{j0}:{j1}%5D" if order == "lonlat" else f"%5B{j0}:{j1}%5D%5B{i0}:{i1}%5D"
    ce = ",".join(f"{v}%5B0%5D{sl}" for v in variables)
    shape = (i1 - i0 + 1, j1 - j0 + 1) if order == "lonlat" else (j1 - j0 + 1, i1 - i0 + 1)

    def url(g):
        for u in g["umm"].get("RelatedUrls", []):
            if u.get("Subtype") == "OPENDAP DATA":
                return u["URL"]
        return None

    def one(g):
        date = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]
        u = url(g)
        if not u:
            return date, None, "no OPENDAP link"
        err = None
        for attempt in range(4):
            try:
                r = sess.get(f"{u}.ascii?{ce}", timeout=120)
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                grids = {}
                for v in variables:
                    rows = [ln.split(",", 1)[1] for ln in r.text.splitlines() if ln.startswith(f"{v}.{v}[")]
                    grid = np.array([[float(x) for x in ln.split(",")] for ln in rows])
                    if grid.shape != shape:
                        raise RuntimeError(f"unexpected shape {grid.shape} for {v}")
                    grids[v] = grid
                return date, grids, None
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {e}"[:200]
                time.sleep(2 * (attempt + 1))
        return date, None, err

    res, done, t0 = [], 0, time.time()
    with ThreadPoolExecutor(workers) as ex:
        for out in ex.map(one, grans):
            res.append(out)
            done += 1
            if done % 250 == 0:
                print(f"  {done}/{len(grans)} ({time.time() - t0:.0f}s)", flush=True)
    frames, nerr = {}, sum(1 for _, g, e in res if e)
    for k, (i, j) in idx.items():
        rows = []
        for date, grids, e in res:
            row = {"date": date, "grid_lon": round(lon0 + step * i, 4), "grid_lat": round(lat0 + step * j, 4)}
            for v in variables:
                x = float("nan") if grids is None else float(grids[v][i - i0, j - j0] if order == "lonlat" else grids[v][j - j0, i - i0])
                row[v] = float("nan") if (x == fill or x < -990) else x
            if e:
                row["error"] = e
            rows.append(row)
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        frames[k] = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    if nerr:
        print(f"  WARNING {nerr} granules failed (rows kept with NaN and 'error')", flush=True)
    return frames, {"n_granules": len(grans), "n_read_errors": nerr, "access": "Cloud OPeNDAP (opendap.earthdata.nasa.gov) DAP2 ascii hyperslab"}


def imerg_opendap_points(short_name: str, version: str, points: dict[str, tuple[float, float]], start: str, end: str,
                         var: str = "precipitation", fill: float = -9999.9, limit: int | None = None,
                         workers: int = 16) -> tuple[dict[str, pd.DataFrame], dict]:
    """IMERG 0.1 deg daily point values for several points via Cloud OPeNDAP (DAP2 .ascii), ONE hyperslab request per
    granule covering all points (dims time, lon, lat; lon/lat centres at -179.95 + 0.1 i / -89.95 + 0.1 j).
    Returns ({key: DataFrame(date, grid_lon, grid_lat, var)}, info)."""
    import time
    import earthaccess

    earthaccess.login(strategy="environment")
    sess = earthaccess.get_requests_https_session()
    grans = earthaccess.search_data(short_name=short_name, version=version, temporal=(start, end), count=limit or -1)
    if not grans:
        raise RuntimeError(f"CMR returned 0 granules for {short_name}.{version} {start}..{end}")
    print(f"  {len(grans)} granules for {short_name}.{version} (OPeNDAP)", flush=True)
    idx = {k: (int(round((lo + 179.95) / 0.1)), int(round((la + 89.95) / 0.1))) for k, (lo, la) in points.items()}
    i0, i1 = min(v[0] for v in idx.values()), max(v[0] for v in idx.values())
    j0, j1 = min(v[1] for v in idx.values()), max(v[1] for v in idx.values())
    ce = f"{var}%5B0%5D%5B{i0}:{i1}%5D%5B{j0}:{j1}%5D"

    def url(g):
        for u in g["umm"].get("RelatedUrls", []):
            if u.get("Subtype") == "OPENDAP DATA":
                return u["URL"]
        return None

    def one(g):
        date = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]
        u = url(g)
        if not u:
            return date, None, "no OPENDAP link"
        err = None
        for attempt in range(4):
            try:
                r = sess.get(f"{u}.ascii?{ce}", timeout=120)
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                rows = [ln.split(",", 1)[1] for ln in r.text.splitlines() if ln.startswith(f"{var}.{var}[")]
                grid = np.array([[float(x) for x in ln.split(",")] for ln in rows])
                if grid.shape != (i1 - i0 + 1, j1 - j0 + 1):
                    raise RuntimeError(f"unexpected shape {grid.shape}")
                return date, grid, None
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {e}"[:200]
                time.sleep(2 * (attempt + 1))
        return date, None, err

    res, done, t0 = [], 0, time.time()
    with ThreadPoolExecutor(workers) as ex:
        for out in ex.map(one, grans):
            res.append(out)
            done += 1
            if done % 250 == 0:
                print(f"  {done}/{len(grans)} ({time.time() - t0:.0f}s)", flush=True)
    frames, nerr = {}, sum(1 for _, g, e in res if e)
    for k, (i, j) in idx.items():
        rows = []
        for date, grid, e in res:
            v = float("nan") if grid is None else float(grid[i - i0, j - j0])
            if v == fill or v < -990:
                v = float("nan")
            row = {"date": date, "grid_lon": round(-179.95 + 0.1 * i, 2), "grid_lat": round(-89.95 + 0.1 * j, 2), var: v}
            if e:
                row["error"] = e
            rows.append(row)
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        frames[k] = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    if nerr:
        print(f"  WARNING {nerr} granules failed (rows kept with NaN and 'error')", flush=True)
    return frames, {"n_granules": len(grans), "n_read_errors": nerr, "access": "Cloud OPeNDAP (opendap.earthdata.nasa.gov) DAP2 ascii hyperslab"}
