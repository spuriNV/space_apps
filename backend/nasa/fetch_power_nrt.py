"""NASA POWER daily point, near-real-time extension: 2026-01-01..today (backend/regional's power.parquet stops at
2025-12-31). Same point, community and parameters as backend/regional/src/fetch_power.py, so the series join.
Writes data/cache/<id>/power_nrt.parquet + .meta.json. No login."""
import json

import numpy as np
import pandas as pd
import requests

from fieldshift_nasa import common as C

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR"
ap = C.common_args("NASA POWER near-real-time daily extension")
a = ap.parse_args()
start, end = a.start or "2026-01-01", a.end or C.today()
for p in a.preset or C.PRESETS:
    pm = json.loads((C.CACHE / p / "power.meta.json").read_text())["params"]
    q = dict(parameters=PARAMS, community="AG", longitude=pm["longitude"], latitude=pm["latitude"],
             start=start.replace("-", ""), end=end.replace("-", ""), format="JSON")
    r = requests.get(URL, params=q, timeout=300)
    r.raise_for_status()
    j = r.json()
    fill = j["header"]["fill_value"]
    df = pd.DataFrame(j["properties"]["parameter"])
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.replace(fill, np.nan).astype("float64")
    df = df.dropna(how="all")  # trailing days not yet processed come back as fill
    out = df.reset_index()
    out.to_parquet(C.CACHE / p / "power_nrt.parquet", index=False)
    meta = {"url": r.url, "params": q, "fetched_at": C.now_iso(), "timestep": "daily",
            "units": {k: v["units"] for k, v in j["parameters"].items()}, "native_res_m": 50000, "fill_value": fill,
            "rows": len(out), "date_min": str(out.date.min().date()), "date_max": str(out.date.max().date()),
            "per_column_last_date": {c: (str(df[c].dropna().index.max().date()) if df[c].notna().any() else None) for c in df.columns},
            "auth": "none", "sources": j["header"].get("sources"),
            "quality_handling": "fill -> NaN; trailing all-fill days dropped. Recent days are POWER's near-real-time "
                                "(GEOS-IT / IMERG-based) values and can be revised; same caveats as power.parquet."}
    (C.CACHE / p / "power_nrt.meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print(p, len(out), meta["date_min"], meta["date_max"], meta["per_column_last_date"])
