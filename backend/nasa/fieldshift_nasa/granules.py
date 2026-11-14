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
