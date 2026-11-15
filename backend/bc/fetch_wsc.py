"""Water Survey of Canada (WSC) river flow and water temperature for the Salmon River (Shuswap), no key.

Stations (MSC GeoMet `hydrometric-stations`, queried 2026-11-15, bbox around the field):
  08LE021  SALMON RIVER NEAR SALMON ARM  1,555 km2, active, real-time; the lower-river gauge, 6 km downstream (north-east)
           of the field and above Shuswap Lake. Daily discharge 1911 on (with gaps).
  08LE020  SALMON RIVER AT FALKLAND      1,049 km2, active, real-time; upper river, about 25 km upstream. The only one of
           the two that reports water temperature (WSC parameter 5).

Sources:
  * Approved daily means (HYDAT): https://api.weather.gc.ca/collections/hydrometric-daily-mean (to 2025-12-31 now).
  * Provisional 5-minute/hourly data for about the last 18 months (discharge param 47, water temperature param 5):
    https://wateroffice.ec.gc.ca/services/real_time_data/csv/inline . Averaged to daily means here (UTC days).
  * Latest real-time reading: https://api.weather.gc.ca/collections/hydrometric-realtime (last 30 days kept by MSC).

Writes data/cache/bc_salmon_river_forage/:
  wsc_daily.parquet   date, station, discharge_m3s, level_m, symbol, approval ("approved" HYDAT | "provisional"),
                      water_temp_c (daily mean), water_temp_max_c, n_obs
  wsc.meta.json       stations, URLs, ranges, latest real-time readings
Run (any venv with requests + pandas + pyarrow): cd backend/api && uv run python ../bc/fetch_wsc.py
"""
from __future__ import annotations

import datetime as dt
import io

import pandas as pd

from common import CACHE, get, now, write_json

OGC = "https://api.weather.gc.ca/collections"
WO = "https://wateroffice.ec.gc.ca/services/real_time_data/csv/inline"
STATIONS = {
    "08LE021": {"name": "SALMON RIVER NEAR SALMON ARM", "lon": -119.33053, "lat": 50.69251, "drainage_km2": 1555.0,
                "operator": "B.C. Ministry of Environment (WSC network)", "role": "lower river, downstream of the field"},
    "08LE020": {"name": "SALMON RIVER AT FALKLAND", "lon": -119.55864, "lat": 50.49853, "drainage_km2": 1049.0,
                "operator": "Water Survey of Canada", "role": "upper river, about 25 km upstream; reports water temperature"},
}
PROV_FROM = dt.date(2025, 5, 1)   # the wateroffice service returned nothing before ~mid-2025 on 2026-11-15


def hydat(stn: str) -> pd.DataFrame:
    rows, off = [], 0
    while True:
        r = get(f"{OGC}/hydrometric-daily-mean/items", params={"f": "json", "STATION_NUMBER": stn, "limit": 10000,
                                                               "offset": off, "sortby": "DATE"}, timeout=180)
        feats = r.json()["features"]
        rows += [f["properties"] for f in feats]
        if len(feats) < 10000:
            break
        off += 10000
    d = pd.DataFrame(rows)
    return pd.DataFrame({"date": pd.to_datetime(d.DATE), "station": stn,
                         "discharge_m3s": pd.to_numeric(d.DISCHARGE, errors="coerce"),
                         "level_m": pd.to_numeric(d.LEVEL, errors="coerce"),
                         "symbol": d.DISCHARGE_SYMBOL_EN, "approval": "approved"})


def provisional(stn: str, param: int, start: dt.date, end: dt.date) -> pd.DataFrame:
    out, a = [], start
    while a <= end:
        b = min(a + dt.timedelta(days=60), end + dt.timedelta(days=1))
        r = get(WO, params={"stations[]": stn, "parameters[]": param, "start_date": f"{a} 00:00:00",
                            "end_date": f"{b} 00:00:00"}, timeout=180)
        txt = r.content.decode("utf-8-sig")
        if txt.count("\n") > 1:
            d = pd.read_csv(io.StringIO(txt))
            d.columns = ["id", "datetime", "param", "value", "qualifier", "symbol", "approval", "grade", "qualifiers"][:len(d.columns)]
            out.append(d[["datetime", "value"]])
        a = b
    if not out:
        return pd.DataFrame(columns=["datetime", "value"])
    d = pd.concat(out).drop_duplicates("datetime")
    d["datetime"] = pd.to_datetime(d.datetime, utc=True)
    d["value"] = pd.to_numeric(d.value, errors="coerce")
    return d[(d.value > -50) & (d.value < 9000)]   # the service pads gaps with 99999


def latest(stn: str) -> dict | None:
    r = get(f"{OGC}/hydrometric-realtime/items", params={"f": "json", "STATION_NUMBER": stn, "limit": 1, "sortby": "-DATETIME"})
    f = r.json()["features"]
    if not f:
        return None
    p = f[0]["properties"]
    return {"datetime_utc": p["DATETIME"], "datetime_local": p["DATETIME_LST"], "discharge_m3s": p["DISCHARGE"], "level_m": p["LEVEL"]}


def main():
    today = dt.date.today()
    frames, info = [], {}
    for stn, s in STATIONS.items():
        h = hydat(stn)
        hd = h.dropna(subset=["discharge_m3s"])
        q = provisional(stn, 47, PROV_FROM, today)
        t = provisional(stn, 5, PROV_FROM, today)
        last_approved = hd.date.max()
        pq = pd.DataFrame(columns=["date", "discharge_m3s"])
        if len(q):
            q["date"] = q.datetime.dt.tz_convert(None).dt.normalize()
            pq = q.groupby("date").value.agg(["mean", "size"]).reset_index().rename(columns={"mean": "discharge_m3s", "size": "n_obs"})
            pq = pq[pq.date > last_approved]
            pq["station"], pq["approval"], pq["symbol"], pq["level_m"] = stn, "provisional", None, None
        d = pd.concat([h, pq], ignore_index=True)
        if len(t):
            t["date"] = t.datetime.dt.tz_convert(None).dt.normalize()
            tt = t.groupby("date").value.agg(water_temp_c="mean", water_temp_max_c="max").reset_index()
            d = d.merge(tt, on="date", how="outer")
            d["station"] = stn
            d["approval"] = d.approval.fillna("provisional")
        else:
            d["water_temp_c"], d["water_temp_max_c"] = None, None
        d = d.sort_values("date").reset_index(drop=True)
        frames.append(d)
        dq = d.dropna(subset=["discharge_m3s"])
        info[stn] = {**s, "station": stn,
                     "hydat_first": str(hd.date.min().date()), "hydat_last": str(last_approved.date()),
                     "provisional_first": str(pq.date.min().date()) if len(pq) else None,
                     "provisional_last": str(pq.date.max().date()) if len(pq) else None,
                     "discharge_first": str(dq.date.min().date()), "discharge_last": str(dq.date.max().date()),
                     "water_temp_first": str(t.datetime.min().date()) if len(t) else None,
                     "water_temp_last": str(t.datetime.max().date()) if len(t) else None,
                     "latest_realtime": latest(stn)}
        print(stn, {k: v for k, v in info[stn].items() if k.endswith(("first", "last"))}, info[stn]["latest_realtime"])
    df = pd.concat(frames, ignore_index=True)
    for c in ("discharge_m3s", "level_m", "water_temp_c", "water_temp_max_c", "n_obs"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["symbol"] = df.symbol.astype("string")
    df.to_parquet(CACHE / "wsc_daily.parquet", index=False)
    write_json(CACHE / "wsc.meta.json", {
        "title": "Water Survey of Canada hydrometric data, Salmon River (Shuswap): HYDAT daily means + provisional real-time",
        "urls": {"hydat_daily_mean": f"{OGC}/hydrometric-daily-mean", "realtime": f"{OGC}/hydrometric-realtime",
                 "provisional_csv": WO, "station_page": "https://wateroffice.ec.gc.ca/report/real_time_e.html?stn=08LE021"},
        "fetched_at": now(), "auth": "none", "stations": info,
        "units": {"discharge_m3s": "m3/s", "level_m": "m (assumed datum)", "water_temp_c": "degC (daily mean of hourly)",
                  "water_temp_max_c": "degC (daily max of hourly)"},
        "notes": ["approval 'approved' = HYDAT; 'provisional' = real-time data averaged to UTC days, subject to revision "
                  "(WSC: provisional data have not been checked and may change).",
                  "Water temperature is published for 08LE020 (Falkland) only, from about May 2025."],
        "licence": "Open Government Licence - Canada (https://open.canada.ca/en/open-government-licence-canada)"})


if __name__ == "__main__":
    main()
