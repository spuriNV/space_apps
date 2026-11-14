"""NASS Quick Stats county acres/yield 2010-2024. GET https://quickstats.nass.usda.gov/api/api_GET/ (key=...). Param names per
https://quickstats.nass.usda.gov/api . short_desc values are U: discovered with short_desc__LIKE and logged, not assumed."""
import requests, pandas as pd
from common import *
URL = "https://quickstats.nass.usda.gov/api/api_GET/"
Q = {"car_colusa_rice": [("RICE", "Colusa")],
     "caf_tulare_forage": [("HAY", "Kings"), ("HAY", "Tulare"), ("CORN", "Kings"), ("CORN", "Tulare")]}
LIKE = {"RICE": ["RICE - ACRES%", "RICE - YIELD%", "RICE - PRODUCTION%"],
        "HAY": ["HAY, ALFALFA - ACRES%", "HAY, ALFALFA - YIELD%", "HAY, ALFALFA - PRODUCTION%"],
        "CORN": ["CORN, SILAGE - ACRES%", "CORN, SILAGE - YIELD%", "CORN, SILAGE - PRODUCTION%"]}
def main():
    key = need_key("NASS_API_KEY")
    for preset, qs in Q.items():
        frames = []
        for com, county in qs:
            for like in LIKE[com]:
                p = {"key": key, "commodity_desc": com, "short_desc__LIKE": like, "agg_level_desc": "COUNTY", "state_alpha": "CA",
                     "county_name": county.upper(), "year__GE": 2010, "year__LE": 2024, "format": "JSON"}
                r = requests.get(URL, params=p, timeout=120)
                if r.status_code != 200: print(f"{preset} {county} {like}: HTTP {r.status_code} {r.text[:150]}"); continue
                d = r.json().get("data", [])
                print(f"{preset} {county} {like}: {len(d)} rows")
                frames.append(pd.DataFrame(d))
        frames = [f for f in frames if len(f)]
        if not frames: continue
        df = pd.concat(frames, ignore_index=True)[["year", "county_name", "commodity_desc", "short_desc", "source_desc", "unit_desc", "Value", "domain_desc", "freq_desc"]]
        df["value_num"] = pd.to_numeric(df["Value"].str.replace(",", ""), errors="coerce")
        meta, path = write_cache(preset, "nass", df, URL, {"qs": qs, "like": LIKE, "years": "2010-2024"})
        save_meta(meta, path, verified=True, note="rows with Value '(D)'/'(NA)' have value_num NaN (withheld)")
        print(f"{preset}: {len(df)} rows -> nass.parquet")
if __name__ == "__main__": main()
