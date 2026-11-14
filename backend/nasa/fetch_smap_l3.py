"""SMAP Enhanced L3 daily 9 km (SPL3SMP_E v006) via AppEEARS point request, with quality flags."""
from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C

a = C.common_args("SMAP L3 9 km soil moisture").parse_args()
C.require_creds()
P = "SPL3SMP_E.006"
AM = "Soil_Moisture_Retrieval_Data_AM_"
LAY = [AM + "soil_moisture", AM + "retrieval_qual_flag", AM + "surface_flag", AM + "static_water_body_fraction",
       AM + "vegetation_opacity", AM + "soil_moisture_error"]
start, end = a.start or "2015-03-31", a.end or C.today()
ae = C.AppEEARS()
presets = a.preset or C.PRESETS
pts = {p: C.field_point(p) for p in presets}
raws, extra = ae.multi_point("smap_l3", pts, start, end, [(P, l) for l in LAY])
for p in presets:
    lon, lat = pts[p]
    raw = raws[p]
    df = C.clean_appeears_df(raw, LAY, {l: -9999 for l in LAY})
    df = df.rename(columns={l: l.replace(AM, "") for l in LAY})
    q = df["retrieval_qual_flag"]
    # SMAP L3 retrieval_qual_flag bit 0 == 0 means "retrieval has recommended quality"
    df["sm_recommended"] = (q.notna() & ((q.fillna(65534).astype("int64") & 1) == 0))
    df["sm_valid"] = df["soil_moisture"].where(df["sm_recommended"])
    C.write_cache(p, "smap_l3", df, {
        "url": f"{C.APPEEARS}/task (point) product {P}", "collection": P,
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end, "layers": LAY},
        "timestep": "daily (AM overpass ~06:00 local)", "units": {"soil_moisture": "m3/m3", "static_water_body_fraction": "1",
                                                                    "soil_moisture_error": "m3/m3"},
        "native_res_m": 9000, "fill_value": -9999,
        "quality_handling": "soil_moisture kept raw; sm_valid = soil_moisture where retrieval_qual_flag bit0==0 "
                            "(recommended quality). Flooded rice / 2023 Tulare Lake water corrupt retrievals: gaps are kept, "
                            "not interpolated. surface_flag + static_water_body_fraction provided for masking.", **extra})
