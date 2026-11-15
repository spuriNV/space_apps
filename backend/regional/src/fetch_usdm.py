"""US Drought Monitor county weekly area-percent series 2015-2025.
Verified live: statisticsType=1 -> cumulative (d2 = % area in D2 or worse); statisticsType=2 -> categorical (exclusive bands).
Cache: data/cache/<preset>/usdm.parquet (+ .meta.json)."""
import pandas as pd
from common import *

URL = "https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
COUNTIES = {pid: p["usdm_counties"] for pid, p in PRESETS.items()}   # from the registry (CAF also has Tulare 06107 as context)

def main():
    for pid, fips_list in COUNTIES.items():
        frames, urls = [], []
        for fips in fips_list:
            for st in (1, 2):
                q = dict(aoi=fips, startdate="1/1/2015", enddate="12/31/2025", statisticsType=st)
                r = get(URL, q, headers={"Accept": "application/json"}); urls.append(r.url)
                d = pd.DataFrame(r.json())
                assert len(d) > 500, f"too few rows {fips} {st}: {len(d)}"
                d["mapDate"] = pd.to_datetime(d["mapDate"]); d["validStart"] = pd.to_datetime(d["validStart"]); d["validEnd"] = pd.to_datetime(d["validEnd"])
                d["stat"] = {1: "cumulative", 2: "categorical"}[st]
                frames.append(d)
        df = pd.concat(frames).rename(columns={"mapDate": "map_date", "validStart": "valid_start", "validEnd": "valid_end"})
        df = df[["map_date", "valid_start", "valid_end", "fips", "county", "state", "stat", "none", "d0", "d1", "d2", "d3", "d4"]].sort_values(["fips", "stat", "map_date"])
        for c in ["none", "d0", "d1", "d2", "d3", "d4"]:
            assert df[c].between(0, 100).all(), c
        df.to_parquet(cache_dir(pid) / "usdm.parquet", index=False)
        cum = df[df.stat == "cumulative"]
        write_json(cache_dir(pid) / "usdm.meta.json", {
            "urls": urls, "params": {"aoi": fips_list, "startdate": "1/1/2015", "enddate": "12/31/2025", "statisticsType": {"1": "cumulative (% area >= category)", "2": "categorical (% area in exactly that category)"}},
            "fetched_at": now(), "timestep": "weekly (map dated Tuesday, valid Tue-Mon)", "units": "percent of county area", "fill_value": None, "native_res_m": None,
            "native_res": "county polygon", "auth": "none", "counties": {f: sorted(cum[cum.fips == f].county.unique().tolist()) for f in fips_list},
            "rows_per_county_stat": {f: int((cum.fips == f).sum()) for f in fips_list},
            "date_min": str(df.map_date.min().date()), "date_max": str(df.map_date.max().date()),
            "preset_county_note": "registry county (backend/fields/registry.json)" if pid != "caf_tulare_forage" else "caf point (36.20,-119.60) is inside Kings County (06031) per Census geocoder; Tulare (06107) included as adjacent context.",
            "footprint_geojson": None})
        print(pid, {f: int((cum.fips == f).sum()) for f in fips_list}, df.map_date.min().date(), df.map_date.max().date())

if __name__ == "__main__":
    main()
