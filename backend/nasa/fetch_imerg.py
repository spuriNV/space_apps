"""GPM IMERG daily point series at the field centroid. Earthaccess (GES DISC).
Final run (GPM_3IMERGDF v07, research grade) where it exists, then Late run (GPM_3IMERGDL v07, ~14 h latency, no gauge
correction) for the days after the last Final granule. Column `run` says which."""
from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C

ap = C.common_args("IMERG daily precipitation point series")
ap.add_argument("--from2000", action="store_true", help="start 2000-06-01 instead of 2015-01-01 (~2.3x more files)")
ap.add_argument("--no-late", action="store_true", help="Final run only")
a = ap.parse_args()
C.require_creds()
import pandas as pd
from fieldshift_nasa.granules import point_series, latest_granule_date

start = a.start or ("2000-06-01" if a.from2000 else "2015-01-01")
end = a.end or C.today()
V = ["precipitation", "randomError"]
F = {v: -9999.9 for v in V}
final_end = latest_granule_date("GPM_3IMERGDF", "07")  # e.g. 2025-09-30
for p in a.preset or C.PRESETS:
    lon, lat = C.field_point(p)
    parts, info = [], {}
    fe = min(end, final_end)
    if start <= fe:
        df, i1 = point_series("GPM_3IMERGDF", "07", V, lon, lat, start, fe, F, a.limit)
        parts.append(df.assign(run="final"))
        info["final"] = {**i1, "start": start, "end": fe}
    late_start = (pd.Timestamp(final_end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    if not a.no_late and end >= late_start:
        ls = max(start, late_start)
        df, i2 = point_series("GPM_3IMERGDL", "07", V, lon, lat, ls, end, F, a.limit)
        parts.append(df.assign(run="late"))
        info["late"] = {**i2, "start": ls, "end": end}
    df = pd.concat(parts, ignore_index=True).sort_values("date").reset_index(drop=True)
    C.write_cache(p, "imerg", df, {
        "url": "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGDF&version=07 and "
               "short_name=GPM_3IMERGDL&version=07 (data.gesdisc.earthdata.nasa.gov, streamed via earthaccess)",
        "collection": ["GPM_3IMERGDF.07 (Final run, C2723754864-GES_DISC)", "GPM_3IMERGDL.07 (Late run)"],
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end, "final_run_last_granule": final_end,
                   "variables": V, "selection": "nearest 0.1 deg cell centre"},
        "timestep": "daily (UTC)", "units": {"precipitation": "mm/day", "randomError": "mm/day (as labelled; see quality)"},
        "native_res_m": 11000, "fill_value": -9999.9,
        "quality_handling": "fill -> NaN. run='final' = research-grade Final run (gauge-adjusted); run='late' = Late run "
                            "(near-real-time, satellite only) used only after the last Final granule. randomError is kept raw "
                            "but its daily values are far larger than the rain (e.g. 5206 on a 37.7 mm day) so it is not used. "
                            "grid_lon/grid_lat give the cell actually sampled.", **info})
