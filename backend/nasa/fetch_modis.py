"""MODIS MOD13Q1.061 NDVI/EVI 250 m 16-day via AppEEARS point request (pixel containing centroid)."""
from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C

a = C.common_args("MODIS NDVI").parse_args()
C.require_creds()
P = "MOD13Q1.061"
L = "_250m_16_days_"
LAY = [L + n for n in ["NDVI", "EVI", "pixel_reliability", "VI_Quality", "composite_day_of_the_year"]]
start, end = a.start or "2000-02-18", a.end or C.today()
ae = C.AppEEARS()
presets = a.preset or C.PRESETS
pts = {p: C.field_point(p) for p in presets}
raws, extra = ae.multi_point("modis", pts, start, end, [(P, l) for l in LAY])
for p in presets:
    lon, lat = pts[p]
    raw = raws[p]
    df = C.clean_appeears_df(raw, LAY, {L + "NDVI": -3000, L + "EVI": -3000, L + "pixel_reliability": -1})
    df = df.rename(columns={l: l.replace(L, "") for l in LAY})
    # pixel_reliability: 0 good, 1 marginal, 2 snow/ice, 3 cloudy; -1 fill
    df["ndvi_good"] = df["NDVI"].where(df["pixel_reliability"].isin([0, 1]))
    C.write_cache(p, "modis", df, {
        "url": f"{C.APPEEARS}/task (point) product {P}", "collection": P,
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end, "layers": LAY,
                   "note": "250 m pixel at the polygon centroid (field series = one pixel; polygon-mean needs an area request)"},
        "timestep": "16-day composite", "units": {"NDVI": "1 (-0.2..1, scaled by AppEEARS)", "EVI": "1"},
        "native_res_m": 250, "fill_value": -3000,
        "quality_handling": "fill -> NaN; ndvi_good keeps pixel_reliability 0/1 only (drops snow/ice, cloud); "
                            "raw NDVI and VI_Quality kept. Rice-check pixels mix field edges/ditches at 250 m.", **extra})
