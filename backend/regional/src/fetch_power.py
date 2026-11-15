"""NASA POWER daily point, 1981 through today (last days may be missing), both presets -> data/cache/<id>/power.parquet + power.meta.json"""
import datetime as dt
import pandas as pd, numpy as np
from common import *

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR"
RANGES = {"T2M": (-50, 50), "T2M_MAX": (-45, 55), "T2M_MIN": (-55, 45), "RH2M": (0, 100),
          "WS2M": (0, 40), "ALLSKY_SFC_SW_DWN": (0, 40), "PRECTOTCORR": (0, 500)}   # cold limits widened for the BC field (Shuswap winters)

def main():
    import shutil
    done_cells = {}
    for pid, p in PRESETS.items():
        cell = power_cell(p["lat"], p["lon"])
        if cell in done_cells:   # same 0.5 x 0.625 deg cell as a field fetched in this run: reuse, don't refetch
            src = done_cells[cell]
            for f in ("power.parquet", "power.meta.json"):
                shutil.copy(cache_dir(src) / f, cache_dir(pid) / f)
            m = json.loads((cache_dir(pid) / "power.meta.json").read_text())
            m["shared_cell_with"] = src; m["field_point"] = [p["lon"], p["lat"]]
            write_json(cache_dir(pid) / "power.meta.json", m)
            print(pid, "same POWER cell as", src, "- copied")
            continue
        q = dict(parameters=PARAMS, community="AG", longitude=p["lon"], latitude=p["lat"],
                 start="19810101", end=dt.date.today().strftime("%Y%m%d"), format="JSON")
        r = get(URL, q)
        j = r.json()
        fill = j["header"]["fill_value"]
        par = j["properties"]["parameter"]
        df = pd.DataFrame(par)
        df.index = pd.to_datetime(df.index, format="%Y%m%d"); df.index.name = "date"
        n_fill = int((df == fill).sum().sum())
        df = df.replace(fill, np.nan).astype("float64")
        # POWER publishes with a lag of a few days; trailing days with no data at all are dropped
        df = df[df[["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"]].notna().any(axis=1)]
        for c, (lo, hi) in RANGES.items():
            v = df[c].dropna()
            assert v.between(lo, hi).all(), f"{pid} {c} out of range {v.min()} {v.max()}"
        df.reset_index().to_parquet(cache_dir(pid) / "power.parquet", index=False)
        meta = {"url": r.url, "params": q, "fetched_at": now(), "timestep": "daily",
                "time_standard": j["header"].get("time_standard"),
                "units": {k: v["units"] for k, v in j["parameters"].items()},
                "native_res": "0.5 deg lat x 0.625 deg lon (MERRA-2 / SYN1DEG); point request returns the containing grid cell",
                "native_res_m": 50000, "fill_value": fill, "n_fill_values_found": n_fill,
                "footprint_geojson": {"type": "Point", "coordinates": j["geometry"]["coordinates"][:2]},
                "elevation_m": j["geometry"]["coordinates"][2], "sources": j["header"].get("sources"),
                "api_version": j["header"]["api"]["version"], "auth": "none",
                "rows": len(df), "date_min": str(df.index.min().date()), "date_max": str(df.index.max().date()),
                "missing_note": "ALLSKY_SFC_SW_DWN is -999 (NaN here) for 1981-01-01..1983-12-31 (1095 days); all other parameters complete.", "caveat": "PRECTOTCORR is MERRA-2 gauge-corrected reanalysis on a ~50 km grid; coarse for convective/extreme rain."}
        write_json(cache_dir(pid) / "power.meta.json", meta)
        done_cells[cell] = pid
        print(pid, len(df), meta["date_min"], meta["date_max"], "fills", n_fill, "elev", meta["elevation_m"])

if __name__ == "__main__":
    main()
