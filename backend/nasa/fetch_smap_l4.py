"""SMAP L4 surface/root-zone soil moisture (SPL4SMGP v008) via AppEEARS point request."""
from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C

a = C.common_args("SMAP L4 soil moisture").parse_args()
C.require_creds()
P = "SPL4SMGP.008"
G = "Geophysical_Data_"
LAY = [G + "sm_surface", G + "sm_rootzone", G + "sm_profile", G + "sm_rootzone_pctl", G + "sm_rootzone_wetness",
       G + "precipitation_total_surface_flux"]
start, end = a.start or "2015-03-31", a.end or C.today()
ae = C.AppEEARS()
presets = a.preset or C.PRESETS
pts = {p: C.field_point(p) for p in presets}
raws, extra = ae.multi_point("smap_l4", pts, start, end, [(P, l) for l in LAY])
for p in presets:
    lon, lat = pts[p]
    raw = raws[p]
    df = C.clean_appeears_df(raw, LAY, {l: -9999 for l in LAY})
    df = df.rename(columns={l: l.replace(G, "") for l in LAY})
    C.write_cache(p, "smap_l4", df, {
        "url": f"{C.APPEEARS}/task (point) product {P}", "collection": P,
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end, "layers": LAY},
        "timestep": "as returned by AppEEARS (product listed Daily; native 3-hourly)",
        "units": {"sm_surface": "m3/m3", "sm_rootzone": "m3/m3", "sm_profile": "m3/m3", "sm_rootzone_pctl": "percent",
                  "sm_rootzone_wetness": "1", "precipitation_total_surface_flux": "kg m-2 s-1"},
        "native_res_m": 9000, "fill_value": -9999,
        "quality_handling": "AppEEARS exposes NO quality-flag layer for SPL4SMGP.008 (model-assimilation product, "
                            "gap-free). Only fill -> NaN. Surface soil moisture over flooded rice is model-based, not retrieved.",
        **extra})
