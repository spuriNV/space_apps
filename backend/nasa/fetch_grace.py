"""GRACE/GRACE-FO data assimilation drought indicators (GRACEDADM_CLSM025GL_7D v3.0): percentiles at the field cell."""
from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C

ap = C.common_args("GRACE-DA weekly percentile series")
a = ap.parse_args()
C.require_creds()
from fieldshift_nasa.granules import point_series

V = ["gws_inst", "rtzsm_inst", "sfsm_inst"]
start = a.start or "2003-02-01"
end = a.end or "2025-12-31"
for p in a.preset or C.PRESETS:
    lon, lat = C.field_point(p)
    df, info = point_series("GRACEDADM_CLSM025GL_7D", "3.0", V, lon, lat, start, end, {v: -999.0 for v in V}, a.limit)
    C.write_cache(p, "grace", df, {
        "url": "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GRACEDADM_CLSM025GL_7D&version=3.0 "
               "(data.gesdisc.earthdata.nasa.gov, streamed via earthaccess)",
        "collection": "GRACEDADM_CLSM025GL_7D.3.0 (C2283200566-GES_DISC)",
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end, "variables": V,
                   "selection": "nearest 0.25 deg cell centre"},
        "timestep": "weekly (granule date = start of week; GRACE gap Jun 2017-May 2018 appears as missing weeks)",
        "units": {"gws_inst": "percentile 0-100 (groundwater)", "rtzsm_inst": "percentile 0-100 (root-zone soil moisture)",
                  "sfsm_inst": "percentile 0-100 (surface soil moisture)"},
        "native_res_m": 25000, "fill_value": -999.0,
        "quality_handling": "fill -> NaN. Values are percentiles per CMR variable metadata (units '%'); "
                            "confirm against the first fetched file. 3-6 month latency.", **info})
