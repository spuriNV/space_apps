"""ECCC daily climate observations for the stations nearest the BC field (no key).

Source: Environment and Climate Change Canada, MSC GeoMet OGC API, collection `climate-daily`
https://api.weather.gc.ca/collections/climate-daily . Stations (climate-stations collection, queried 2026-11-15):
  116FRMN  SALMON ARM CS   (STN_ID 6843, 350 m, daily 1991-01-01 .. present)  -- the only active station near the valley
  1167337  SILVER CREEK    (STN_ID 1327, 419 m, daily 1989-06-01 .. 2021-10-30) -- closed in 2021, in the Salmon River valley
Writes data/cache/bc_salmon_river_forage/eccc.parquet (date, station, name, tmax_c, tmin_c, tmean_c, prcp_mm, *_flag)
and eccc.meta.json. The engine's station temperature/precipitation reader uses this file the way it uses NOAA GHCN-D
(ncei.parquet) for the California fields.

Run: uv run python fetch_eccc.py
"""
from __future__ import annotations

import pandas as pd

from common import CACHE, get, now, write_json

API = "https://api.weather.gc.ca/collections/climate-daily/items"
STATIONS = [
    {"climate_id": "116FRMN", "stn_id": 6843, "name": "SALMON ARM CS", "lon": -119.29068, "lat": 50.703, "elev_m": 350.5,
     "daily": ["1991-01-01", None]},
    {"climate_id": "1167337", "stn_id": 1327, "name": "SILVER CREEK", "lon": -119.35003, "lat": 50.54519, "elev_m": 419.0,
     "daily": ["1989-06-01", "2021-10-30"]},
]
START = "1991-01-01"


def fetch(cid: str) -> pd.DataFrame:
    rows, offset = [], 0
    while True:
        r = get(API, params={"f": "json", "CLIMATE_IDENTIFIER": cid, "datetime": f"{START}/2030-01-01",
                             "limit": 10000, "offset": offset, "sortby": "LOCAL_DATE"}, timeout=180)
        feats = r.json()["features"]
        rows += [f["properties"] for f in feats]
        if len(feats) < 10000:
            break
        offset += 10000
    d = pd.DataFrame(rows)
    out = pd.DataFrame({
        "date": pd.to_datetime(d["LOCAL_DATE"]).dt.normalize(),
        "station": cid, "name": d["STATION_NAME"],
        "tmax_c": pd.to_numeric(d["MAX_TEMPERATURE"], errors="coerce"),
        "tmin_c": pd.to_numeric(d["MIN_TEMPERATURE"], errors="coerce"),
        "tmean_c": pd.to_numeric(d["MEAN_TEMPERATURE"], errors="coerce"),
        "prcp_mm": pd.to_numeric(d["TOTAL_PRECIPITATION"], errors="coerce"),
        "tmax_flag": d["MAX_TEMPERATURE_FLAG"], "tmin_flag": d["MIN_TEMPERATURE_FLAG"],
        "prcp_flag": d["TOTAL_PRECIPITATION_FLAG"],
    })
    out = out.dropna(subset=["tmax_c", "tmin_c", "prcp_mm"], how="all")   # the API pads closed stations with empty days
    return out.sort_values("date").reset_index(drop=True)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    frames, info = [], []
    for s in STATIONS:
        d = fetch(s["climate_id"])
        frames.append(d)
        cov = {str(y): round(float(g.prcp_mm.notna().mean()), 3) for y, g in d.groupby(d.date.dt.year)}
        info.append({**s, "rows": len(d), "first": str(d.date.min().date()), "last": str(d.date.max().date()),
                     "prcp_coverage_by_year": cov})
        print(f"{s['climate_id']} {s['name']}: {len(d)} rows {d.date.min().date()}..{d.date.max().date()}")
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(CACHE / "eccc.parquet", index=False)
    write_json(CACHE / "eccc.meta.json", {
        "url": API, "params": {"CLIMATE_IDENTIFIER": [s["climate_id"] for s in STATIONS], "datetime": f"{START}/..",
                               "f": "json"},
        "title": "Environment and Climate Change Canada daily climate data (MSC GeoMet OGC API, climate-daily)",
        "fetched_at": now(), "auth": "none", "units": {"tmax_c": "C", "tmin_c": "C", "tmean_c": "C", "prcp_mm": "mm/day"},
        "selected_stations": [{"station": s["climate_id"], **s} for s in info],
        "licence": "Open Government Licence - Canada (https://open.canada.ca/en/open-government-licence-canada)",
        "note": "Two stations: Salmon Arm CS is the only active one within 25 km; Silver Creek (in the Salmon River "
                "valley) closed in Oct 2021. This is the 'sparse stations' gap: California fields average 3 NOAA "
                "stations plus CIMIS."})


if __name__ == "__main__":
    main()
