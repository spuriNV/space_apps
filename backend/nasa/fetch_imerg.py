"""GPM IMERG daily (GPM_3IMERGDF v07) point series at the field centroid. Earthaccess (GES DISC)."""
from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C

ap = C.common_args("IMERG daily precipitation point series")
ap.add_argument("--from2000", action="store_true", help="start 2000-06-01 instead of 2015-01-01 (~2.3x more files)")
a = ap.parse_args()
C.require_creds()
from fieldshift_nasa.granules import point_series

start = a.start or ("2000-06-01" if a.from2000 else "2015-01-01")
end = a.end or "2025-12-31"
for p in a.preset or C.PRESETS:
    lon, lat = C.field_point(p)
    df, info = point_series("GPM_3IMERGDF", "07", ["precipitation", "randomError"], lon, lat, start, end,
                            {"precipitation": -9999.9, "randomError": -9999.9}, a.limit)
    C.write_cache(p, "imerg", df, {
        "url": "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGDF&version=07 "
               "(data.gesdisc.earthdata.nasa.gov, streamed via earthaccess)",
        "collection": "GPM_3IMERGDF.07 (C2723754864-GES_DISC)",
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end,
                   "variables": ["precipitation", "randomError"], "selection": "nearest 0.1 deg cell centre"},
        "timestep": "daily (UTC)", "units": {"precipitation": "mm/day", "randomError": "mm/day"},
        "native_res_m": 11000, "fill_value": -9999.9,
        "quality_handling": "fill -> NaN; CMR lists data to 2025-09-30 so later dates are absent (not zero). "
                            "grid_lon/grid_lat give the cell actually sampled.", **info})
