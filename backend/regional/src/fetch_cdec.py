"""CDEC daily reservoir storage (sensor 15 = STORAGE, AF, verified live) SHA/ORO/PNF 2015-2025.
Written to data/cache/<preset>/cdec.parquet. CAR gets SHA+ORO (spec cdec_stations); CAF gets PNF (Pine Flat, Kings River).
Storage is statewide-system context, so all three are also kept in each preset's file for simplicity of the allocation strip."""
import pandas as pd, numpy as np
from common import *

URL = "https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet"
BASE = ["SHA", "ORO", "PNF"]   # every field's file keeps these three (state system context) plus its own reservoirs
STATIONS = BASE + sorted({s for p in PRESETS.values() for s in p["reservoirs"]} - set(BASE))
NAMES = {"SHA": "Shasta", "ORO": "Oroville", "PNF": "Pine Flat", "TRM": "Terminus (Lake Kaweah)", "SCC": "Success",
         "EXC": "New Exchequer (Lake McClure)", "SNL": "San Luis", "MIL": "Millerton", "DNP": "Don Pedro", "NML": "New Melones"}

def main():
    q = dict(Stations=",".join(STATIONS), SensorNums=15, dur_code="D", Start="2015-01-01", End="2025-12-31")
    r = get(URL, q); rows = r.json()
    df = pd.DataFrame(rows)
    assert (df.SENSOR_NUM == 15).all() and (df.sensorType == "STORAGE").all() and (df.units == "AF").all(), "sensor 15 is not STORAGE/AF"
    df["date"] = pd.to_datetime(df["date"].str.split(" ").str[0], format="%Y-%m-%d")
    df["storage_af"] = pd.to_numeric(df["value"], errors="coerce")   # CDEC uses '---' / -9999 for missing
    n_missing = int(df.storage_af.isna().sum() + (df.storage_af <= 0).sum())
    df.loc[df.storage_af <= 0, "storage_af"] = np.nan
    assert df.storage_af.dropna().between(1e3, 6e6).all(), "storage out of plausible AF range"
    out = df[["stationId", "date", "storage_af", "dataFlag"]].rename(columns={"stationId": "station", "dataFlag": "flag"})
    out = out.sort_values(["station", "date"]).drop_duplicates(["station", "date"])
    stats = {s: {"rows": int((out.station == s).sum()), "date_min": str(out[out.station == s].date.min().date()),
                 "date_max": str(out[out.station == s].date.max().date()),
                 "n_missing": int(out[out.station == s].storage_af.isna().sum())} for s in STATIONS}
    for pid, p in PRESETS.items():
        keep = BASE + [s for s in p["reservoirs"] if s not in BASE]
        o = out[out.station.isin(keep)]
        o.to_parquet(cache_dir(pid) / "cdec.parquet", index=False)
        write_json(cache_dir(pid) / "cdec.meta.json", {
            "url": r.url, "params": q, "fetched_at": now(), "timestep": "daily", "units": {"storage_af": "acre-feet"},
            "native_res_m": None, "native_res": "point (reservoir gauge)", "fill_value": "missing values returned as non-numeric strings or <=0; set to NaN",
            "n_missing_or_nonpositive": n_missing, "auth": "none", "stations": {k: v for k, v in stats.items() if k in keep}, "field_reservoirs": p["reservoirs"],
            "sensor": {"number": 15, "type": "STORAGE", "units": "AF", "verified_live": True, "also_seen": "sensor 6 = RES ELE (feet)"},
            "station_names": {k: NAMES.get(k, k) for k in keep},
            "notes": "Rows keyed on the 'date' field of the response (for some records obsDate is a day later). Reservoir capacity not fetched here; use relative comparisons only.",
            "footprint_geojson": None})
    print(stats)

if __name__ == "__main__":
    main()
