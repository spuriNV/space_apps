"""BC minimal NASA-only signal (spec B2.13): SMAP L4 root-zone percentile, GRACE-DA groundwater percentile and POWER Tmax
at 50.62 N, -119.33 W (lower Salmon River; representative point, U) for Mar-Oct 2023.
Writes data/cache/bc/signal_raw.parquet + signal.meta.json (backend/api builds data/cache/bc/signal.json from it)."""
import json

import pandas as pd
import requests

from fieldshift_nasa import common as C

C.require_creds()
from fieldshift_nasa.granules import opendap_points  # noqa: E402

LON, LAT = -119.33, 50.62
S, E = "2023-03-01", "2023-10-31"
out = C.CACHE / "bc"
out.mkdir(parents=True, exist_ok=True)
ae = C.AppEEARS()
G = "Geophysical_Data_"
LAY = [G + "sm_rootzone", G + "sm_rootzone_pctl"]
raws, extra = ae.multi_point("bc_smap_l4", {"bc": (LON, LAT)}, S, E, [("SPL4SMGP.008", l) for l in LAY])
sm = C.clean_appeears_df(raws["bc"], LAY, {l: -9999 for l in LAY}).rename(columns={l: l.replace(G, "") for l in LAY})
sm = sm.groupby(sm.date.dt.normalize()).mean(numeric_only=True).reset_index()
grf, ginfo = opendap_points("GRACEDADM_CLSM025GL_7D", "3.0", {"bc": (LON, LAT)}, S, E, ["gws_inst", "rtzsm_inst"],
                            -179.875, -59.875, 0.25, "latlon", -999.0)
gr = grf["bc"]
pw = requests.get("https://power.larc.nasa.gov/api/temporal/daily/point",
                  params=dict(parameters="T2M_MAX", community="AG", longitude=LON, latitude=LAT,
                              start=S.replace("-", ""), end=E.replace("-", ""), format="JSON"), timeout=300).json()
tx = pd.Series(pw["properties"]["parameter"]["T2M_MAX"])
tx.index = pd.to_datetime(tx.index, format="%Y%m%d")
tx = tx.where(tx != pw["header"]["fill_value"])
df = pd.DataFrame({"date": pd.date_range(S, E)})
df = df.merge(sm.rename(columns={"sm_rootzone_pctl": "smap_rootzone_pctl"}), on="date", how="left")
df = df.merge(gr[["date", "gws_inst", "rtzsm_inst"]].rename(columns={"gws_inst": "grace_gw_pct", "rtzsm_inst": "grace_rtzsm_pct"}),
              on="date", how="left")
df["power_tmax_c"] = df.date.map(tx)
df.to_parquet(out / "signal_raw.parquet", index=False)
(out / "signal.meta.json").write_text(json.dumps({
    "point_lon_lat": [LON, LAT], "start": S, "end": E, "fetched_at": C.now_iso(),
    "sources": {"smap": "SPL4SMGP.008 via AppEEARS point (sm_rootzone_pctl, percent)", "grace": "GRACEDADM_CLSM025GL_7D.3.0 gws_inst (percentile, weekly)",
                "power": "NASA POWER daily T2M_MAX (AG)"},
    "appeears": extra, "grace_info": ginfo, "note": "representative point (U); SMAP L4 rows are daily means of the 3-hourly values"},
    indent=1))
print("bc signal rows", len(df), df.notna().sum().to_dict())
