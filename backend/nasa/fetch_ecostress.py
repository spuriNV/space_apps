"""ECOSTRESS LST (ECO_L2T_LSTE.002), ET (ECO_L3T_JET.002), ESI (ECO_L4T_ESI.002) via AppEEARS point request, 70 m tile pixel at centroid."""
from fieldshift_nasa.common import *  # noqa: F401,F403
from fieldshift_nasa import common as C
import pandas as pd

a = C.common_args("ECOSTRESS LST/ET/ESI").parse_args()
C.require_creds()
PRODS = {
    "ECO_L2T_LSTE.002": ["LST", "LST_err", "cloud", "water"],
    "ECO_L3T_JET.002": ["ETdaily", "cloud"],
    "ECO_L4T_ESI.002": ["ESI", "PET", "cloud"],
}
start, end = a.start or "2018-07-09", a.end or C.today()
ae = C.AppEEARS()
presets = a.preset or C.PRESETS
pts = {p: C.field_point(p) for p in presets}
from concurrent.futures import ThreadPoolExecutor
by_prod, extra = {}, {"task_ids": []}
with ThreadPoolExecutor(3) as ex_:  # submit all three products at once, then wait
    futs = {prod: ex_.submit(ae.multi_point, "ecostress_" + prod.split(".")[0], pts, start, end, [(prod, l) for l in lays])
            for prod, lays in PRODS.items()}
    for prod, f in futs.items():
        raws, ex = f.result()
        by_prod[prod] = raws
        extra["task_ids"] += ex["task_ids"]
for p in presets:
    lon, lat = pts[p]
    parts = []
    for prod, lays in PRODS.items():
        df = C.clean_appeears_df(by_prod[prod][p], lays, {"cloud": 255})
        if "LST" in df:
            df.loc[~df["LST"].between(150, 400), "LST"] = float("nan")
        df.insert(0, "product", prod)
        parts.append(df)
    allp = pd.concat(parts, ignore_index=True)
    C.write_cache(p, "ecostress", allp, {
        "url": f"{C.APPEEARS}/task (point), products " + ", ".join(PRODS), "collection": list(PRODS),
        "params": {"point_lon_lat": [lon, lat], "start": start, "end": end, "layers": PRODS},
        "timestep": "irregular ISS overpasses (long format: one row per scene per product)",
        "units": {"LST": "K", "LST_err": "K", "ETdaily": "W m-2 (AppEEARS-listed unit; daily-mean latent heat flux; "
                                                             "convert to mm/day with lambda ~2.45e6 J/kg: x 0.0353)",
                  "ESI": "ratio 0-1", "PET": "W m-2"},
        "native_res_m": 70, "fill_value": "NaN / cloud=255",
        **extra, "quality_handling": "cloud and water mask columns kept raw (1 = cloud / water); LST outside 150-400 K -> NaN. "
                            "Use clear scenes only (cloud==0). Irregular overpass times: use anomalies, not absolutes. "
                            "Point pixel at centroid, not field mean."})
