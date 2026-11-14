"""CIMIS daily ETo/precip/Tmin/Tmax 2015-2025. Docs: https://et.water.ca.gov/Rest/Index ; GET /api/data?appKey&targets&startDate&endDate&dataItems&unitOfMeasure=M
Stations: 250 Williams (Colusa); 15 Stratford (Kings, ~22 km from the field; nearest ACTIVE CIMIS station). Fetch by year (record cap ERR2112)."""
import requests, pandas as pd
from common import *
URL = "https://et.water.ca.gov/api/data"
STATIONS = {"car_colusa_rice": [250], "caf_tulare_forage": [15]}
ITEMS = "day-eto,day-precip,day-air-tmp-min,day-air-tmp-max"
F = {"DayEto": "eto_mm", "DayPrecip": "precip_mm", "DayAirTmpMin": "tmin_c", "DayAirTmpMax": "tmax_c"}

def main():
    key = need_key("CIMIS_APP_KEY")
    if len(key) == 32 and "-" not in key: key = f"{key[:8]}-{key[8:12]}-{key[12:16]}-{key[16:20]}-{key[20:]}"  # WAF rejects undashed form
    for preset, sts in STATIONS.items():
        rows = []
        for st in sts:
            for y in range(2015, 2026):
                p = {"appKey": key, "targets": st, "startDate": f"{y}-01-01", "endDate": f"{y}-12-31", "dataItems": ITEMS, "unitOfMeasure": "M"}
                r = requests.get(URL, params=p, headers={"Accept": "application/json"}, timeout=120)
                if r.status_code != 200 or "json" not in r.headers.get("content-type", "") and not r.text.lstrip().startswith("{"): print(f"{preset} stn {st} {y}: HTTP {r.status_code} {r.text[:200].replace(key, "KEY")}"); continue
                for prov in r.json().get("Data", {}).get("Providers", []):
                    for rec in prov.get("Records", []):
                        d = {"date": rec["Date"], "station": st}
                        for k, n in F.items():
                            v = (rec.get(k) or {}).get("Value"); d[n] = float(v) if v not in (None, "") else None
                            d[n + "_qc"] = (rec.get(k) or {}).get("Qc", "").strip()
                        rows.append(d)
        if not rows: continue
        df = pd.DataFrame(rows); df["date"] = pd.to_datetime(df["date"])
        meta, path = write_cache(preset, "cimis", df, URL, {"targets": sts, "dataItems": ITEMS, "unitOfMeasure": "M", "years": "2015-2025"})
        save_meta(meta, path, stations={"250": "Williams, Colusa (39.2107,-122.1689)", "15": "Stratford, Kings (36.1581,-119.8514), ~22 km from field"}, verified=True)
        print(f"{preset}: {len(df)} daily rows -> data/cache/{preset}/cimis.parquet")
if __name__ == "__main__": main()
