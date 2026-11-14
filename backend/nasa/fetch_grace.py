"""GRACE/GRACE-FO data assimilation drought indicators (GRACEDADM_CLSM025GL_7D v3.0): percentiles at the field cell."""
from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C

ap = C.common_args("GRACE-DA weekly percentile series")
a = ap.parse_args()
C.require_creds()
from fieldshift_nasa.granules import opendap_points

V = ["gws_inst", "rtzsm_inst", "sfsm_inst"]
start = a.start or "2003-02-01"
end = a.end or C.today()
presets = a.preset or C.PRESETS
pts = {p: C.field_point(p) for p in presets}
# GRACE-DA 0.25 deg grid: 600 lat rows from -59.875, 1440 lon columns from -179.875 (checked against the DDS and the
# streamed read of 2021-01: cell -122.125 / 39.125 for the Colusa field)
frames, info = opendap_points("GRACEDADM_CLSM025GL_7D", "3.0", pts, start, end, V, -179.875, -59.875, 0.25, "latlon",
                              -999.0, a.limit)
for p in presets:
    lon, lat = pts[p]
    df = frames[p]
    C.write_cache(p, "grace", df, {
        "url": "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GRACEDADM_CLSM025GL_7D&version=3.0 "
               "(Cloud OPeNDAP hyperslab per granule)",
        "collection": "GRACEDADM_CLSM025GL_7D.3.0 (C2283200566-GES_DISC)",
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end, "variables": V,
                   "selection": "nearest 0.25 deg cell centre"},
        "timestep": "weekly (granule date = start of week; GRACE gap Jun 2017-May 2018 appears as missing weeks)",
        "units": {"gws_inst": "percentile 0-100 (groundwater)", "rtzsm_inst": "percentile 0-100 (root-zone soil moisture)",
                  "sfsm_inst": "percentile 0-100 (surface soil moisture)"},
        "native_res_m": 25000, "fill_value": -999.0,
        "quality_handling": "fill -> NaN. Values are percentiles per CMR variable metadata (units '%'); "
                            "confirm against the first fetched file. 3-6 month latency.", **info})
