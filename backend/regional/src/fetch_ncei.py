"""NOAA NCEI GHCN-Daily (daily-summaries) for the nearest long-record stations -> data/cache/<id>/ncei.parquet + meta.
Station discovery: NCEI search service over a bbox; candidates must list PRCP+TMAX+TMIN; we then download 1981-2025 for the
12 nearest and keep up to 3 nearest with >=70% daily coverage of PRCP, TMAX and TMIN over 1981-2025."""
import io, math
import pandas as pd, numpy as np
from common import *

SEARCH = "https://www.ncei.noaa.gov/access/services/search/v1/data"
DATA = "https://www.ncei.noaa.gov/access/services/data/v1"
START, END = "1981-01-01", "2025-12-31"

def hav(lat1, lon1, lat2, lon2):
    r = 6371.0; p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def candidates(p, half=0.8):
    bbox = f"{p['lat']+half},{p['lon']-half},{p['lat']-half},{p['lon']+half}"
    out = {}
    for off in (0, 100, 200):
        r = get(SEARCH, dict(dataset="daily-summaries", bbox=bbox, startDate=START, endDate=END, dataTypes="PRCP,TMAX,TMIN", limit=100, offset=off)).json()
        for x in r["results"]:
            sid = x["name"].replace(".csv", "")
            lon, lat = x["centroid"]
            ids = {d["id"] for d in x["dataTypes"]}
            if {"PRCP", "TMAX", "TMIN"} <= ids and x["startDate"][:4] <= "1985":
                out[sid] = {"lat": lat, "lon": lon, "dist_km": hav(p["lat"], p["lon"], lat, lon), "first_date": x["startDate"][:10]}
        if len(r["results"]) < 100: break
    return out

def main():
    for pid, p in PRESETS.items():
        cands = candidates(p)
        near = sorted(cands, key=lambda s: cands[s]["dist_km"])[:12]
        assert near, "no candidate stations"
        r = get(DATA, dict(dataset="daily-summaries", stations=",".join(near), startDate=START, endDate=END, dataTypes="PRCP,TMAX,TMIN",
                           units="metric", includeStationName="true", includeStationLocation="true", format="csv"))
        df = pd.read_csv(io.StringIO(r.text), dtype={"STATION": str})
        df["DATE"] = pd.to_datetime(df["DATE"])
        ndays = (pd.Timestamp(END) - pd.Timestamp(START)).days + 1
        info = []
        for s in near:
            d = df[df.STATION == s]
            cov = {v: round(float(d[v].notna().sum() / ndays), 3) for v in ("PRCP", "TMAX", "TMIN")}
            nm = d["NAME"].iloc[0] if len(d) else None
            info.append({"station": s, "name": nm, **{k: round(v, 4) if isinstance(v, float) else v for k, v in cands[s].items()}, "coverage_1981_2025": cov,
                         "first_obs": str(d.DATE.min().date()) if len(d) else None, "last_obs": str(d.DATE.max().date()) if len(d) else None})
        keep = [i for i in info if min(i["coverage_1981_2025"].values()) >= 0.70][:3]
        keep_ids = [i["station"] for i in keep]
        out = df[df.STATION.isin(keep_ids)][["STATION", "DATE", "PRCP", "TMAX", "TMIN"]].rename(columns={"STATION": "station", "DATE": "date", "PRCP": "prcp_mm", "TMAX": "tmax_c", "TMIN": "tmin_c"})
        if keep:
            assert out.prcp_mm.dropna().between(0, 600).all() and out.tmax_c.dropna().between(-30, 60).all() and out.tmin_c.dropna().between(-40, 45).all()
        out.sort_values(["station", "date"]).to_parquet(cache_dir(pid) / "ncei.parquet", index=False)
        write_json(cache_dir(pid) / "ncei.meta.json", {
            "url": r.url, "search_url": SEARCH, "params": {"dataset": "daily-summaries", "stations": keep_ids, "startDate": START, "endDate": END, "dataTypes": "PRCP,TMAX,TMIN", "units": "metric"},
            "fetched_at": now(), "timestep": "daily (local station time, observation-day convention varies by station; compare monthly or +/-1 day)",
            "units": {"prcp_mm": "mm", "tmax_c": "degC", "tmin_c": "degC"}, "fill_value": "blank/absent rows -> NaN", "native_res": "point stations", "native_res_m": None,
            "auth": "none", "selected_stations": keep, "all_candidates_checked_nearest_12": info, "rows": int(len(out)),
            "selection_rule": "nearest 3 of the 12 nearest candidate GHCN-D stations (bbox +/-0.8 deg, record starting <=1985) with >=70% daily coverage of PRCP,TMAX,TMIN over 1981-2025",
            "footprint_geojson": None})
        print(pid, len(out)); [print("  ", i) for i in info]; print("  KEEP", keep_ids)

if __name__ == "__main__":
    main()
