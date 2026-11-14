"""USDM county weekly (extend cache to latest) + CDEC reservoir storage to latest and CDEC's own historical average.
Writes data/cache/<id>/usdm_2026.parquet(+meta), data/cache/<id>/cdec_2026.parquet(+meta), out/water_now.json."""
import re, datetime as dt
import pandas as pd, numpy as np
from common import *

USDM = "https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
USDM_PAGE = "https://droughtmonitor.unl.edu/CurrentMap/StateDroughtMonitor.aspx?CA"
CDEC_JSON = "https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet"
CDEC_RES = "https://cdec.water.ca.gov/reportapp/javareports?name=RES"
CATS = {"d0": "D0 abnormally dry", "d1": "D1 moderate drought", "d2": "D2 severe drought", "d3": "D3 extreme drought", "d4": "D4 exceptional drought"}

def usdm(pid, fetched):
    fips, name = COUNTY[pid]
    today = dt.date.today()
    frames, urls = [], []
    for st in (1, 2):
        q = dict(aoi=fips, startdate="1/1/2026", enddate=f"{today.month}/{today.day}/{today.year}", statisticsType=st)
        r = get(USDM, q, headers={"Accept": "application/json"}); urls.append(r.url)
        d = pd.DataFrame(r.json())
        for c in ("mapDate", "validStart", "validEnd"): d[c] = pd.to_datetime(d[c])
        d["stat"] = {1: "cumulative", 2: "categorical"}[st]; frames.append(d)
    df = pd.concat(frames).rename(columns={"mapDate": "map_date", "validStart": "valid_start", "validEnd": "valid_end"})
    df = df[["map_date", "valid_start", "valid_end", "fips", "county", "state", "stat", "none", "d0", "d1", "d2", "d3", "d4"]].sort_values(["stat", "map_date"])
    df.to_parquet(CACHE / pid / "usdm_2026.parquet", index=False)
    write_json(CACHE / pid / "usdm_2026.meta.json", {"urls": urls, "fetched_at": fetched, "units": "percent of county area", "auth": "none",
        "timestep": "weekly (map dated Tuesday)", "date_min": str(df.map_date.min().date()), "date_max": str(df.map_date.max().date()),
        "note": "extends usdm.parquet (2015-2025) from 2026-01-01; same column meanings"})
    cum = df[df.stat == "cumulative"].sort_values("map_date"); cat = df[df.stat == "categorical"].sort_values("map_date")
    last, lc = cum.iloc[-1], cat.iloc[-1]
    # worst category present (any area): highest d-level with cumulative >0
    worst = None
    for k in ("d4", "d3", "d2", "d1", "d0"):
        if last[k] > 0: worst = k; break
    prev = cum.iloc[-5] if len(cum) >= 5 else None
    u = urls[0]
    out = {"county": f"{name} County", "fips": fips, "map_date": str(last.map_date.date()), "valid_end": str(last.valid_end.date()),
        "worst_category": CATS[worst] if worst else "None (no D0-D4 area)",
        "worst_category_code": worst.upper() if worst else "None",
        "area_in_category_percent": {k.upper(): sn(float(last[k]), "% of county area", u, f"US Drought Monitor, {name} County, cumulative (area in category or worse)", fetched, True, note=f"map dated {last.map_date.date()}") for k in ("d0", "d1", "d2", "d3", "d4")},
        "area_none_percent": sn(float(lc["none"]), "% of county area", urls[1], f"US Drought Monitor, {name} County, categorical", fetched, True, note=f"map dated {last.map_date.date()}"),
        "map_date_sn_url": USDM_PAGE, "weeks_ago_4_cumulative_D0": None if prev is None else float(prev.d0),
        "history_2026": [{"map_date": str(r["map_date"].date()), **{k.upper(): float(r[k]) for k in ("d0", "d1", "d2", "d3", "d4")}} for _, r in cum.iterrows()][-12:],
        "source_url": u, "fetched_at": fetched, "verified": True}
    return out

def parse_res():
    html = get(CDEC_RES).text
    m = re.search(r"Ending at midnight\s*-\s*(\d+/\d+/\d+)", html); asof = dt.datetime.strptime(m.group(1), "%m/%d/%Y").date()
    rows = {}
    for sid in ("SHA", "ORO", "PNF"):
        tr = re.search(r"<tr[^>]*>(?:(?!</tr>).)*station_id=%s\"(?:(?!</tr>).)*</tr>" % sid, html, re.S).group(0)
        cells = [re.sub(r"<[^>]*>", "", c).replace(",", "").strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        f = lambda s: None if s in ("---", "") else float(s)
        rows[sid] = dict(name=cells[0], capacity_af=f(cells[2]), elevation_ft=f(cells[3]), storage_af=f(cells[4]), change_af=f(cells[5]),
                         pct_capacity=f(cells[6]), avg_af=f(cells[7]), pct_avg=f(cells[8]), outflow_cfs=f(cells[9]), inflow_cfs=f(cells[10]), year_ago_af=f(cells[11]))
    return asof, rows

def cdec(fetched):
    asof, rows = parse_res()
    r = get(CDEC_JSON, dict(Stations="SHA,ORO,PNF", SensorNums=15, dur_code="D", Start="2026-01-01", End=dt.date.today().isoformat()))
    d = pd.DataFrame(r.json()); d["date"] = pd.to_datetime(d["date"]); d["storage_af"] = pd.to_numeric(d["value"], errors="coerce")
    d = d.rename(columns={"stationId": "station", "dataFlag": "flag"})[["station", "date", "storage_af", "flag"]]
    d.loc[d.storage_af <= 0, "storage_af"] = np.nan
    res = {}
    for pid, sts in RESERVOIRS.items():
        d.to_parquet(CACHE / pid / "cdec_2026.parquet", index=False)
        write_json(CACHE / pid / "cdec_2026.meta.json", {"url": r.url, "fetched_at": fetched, "units": {"storage_af": "acre-feet"}, "auth": "none", "timestep": "daily",
            "date_min": str(d.date.min().date()), "date_max": str(d.date.max().date()), "note": "extends cdec.parquet (2015-2025) with 2026; also reads the CDEC Daily Reservoir Storage Summary for historical average",
            "summary_url": CDEC_RES})
        res[pid] = {}
        for s in sts:
            hist = pd.read_parquet(CACHE / pid / "cdec.parquet"); hist = hist[hist.station == s]
            allx = pd.concat([hist[["date", "storage_af"]], d[d.station == s][["date", "storage_af"]]])
            allx["date"] = pd.to_datetime(allx.date)
            last = allx.dropna().sort_values("date").iloc[-1]
            # own average: mean storage on the same calendar day 2015-2025 (cached series)
            h = hist.copy(); h["date"] = pd.to_datetime(h.date)
            same = h[(h.date.dt.month == last.date.month) & (h.date.dt.day == last.date.day) & h.storage_af.notna()]
            own_avg = float(same.storage_af.mean())
            x = rows[s]; u = CDEC_RES
            res[pid][s] = {"name": x["name"], "cdec_report_date": str(asof), "latest_daily_date": str(last.date.date()),
                "storage_af": sn(x["storage_af"], "acre-feet", u, f"CDEC Daily Reservoir Storage Summary, {s}", fetched, True, note=f"report 'Ending at midnight {asof}'"),
                "capacity_af": sn(x["capacity_af"], "acre-feet", u, f"CDEC reservoir capacity, {s}", fetched, True),
                "pct_of_capacity": sn(x["pct_capacity"], "percent", u, f"CDEC % of capacity, {s}", fetched, True),
                "cdec_average_storage_af": sn(x["avg_af"], "acre-feet", u, f"CDEC historical average storage for this date, {s}", fetched, True,
                    note="CDEC's published average for the date; CDEC does not state the averaging period on this page (its long-term record, not our 2015-2025 cache)"),
                "pct_of_cdec_average": sn(x["pct_avg"], "percent", u, f"CDEC % of average for this date, {s}", fetched, True),
                "storage_year_ago_af": sn(x["year_ago_af"], "acre-feet", u, f"CDEC storage a year ago, {s}", fetched, True),
                "inflow_cfs": sn(x["inflow_cfs"], "cfs", u, f"CDEC inflow, {s}", fetched, True), "outflow_cfs": sn(x["outflow_cfs"], "cfs", u, f"CDEC outflow, {s}", fetched, True),
                "daily_series_latest_af": sn(float(last.storage_af), "acre-feet", r.url, f"CDEC daily storage sensor 15, {s}", fetched, True, note=f"date {last.date.date()}"),
                "own_average_2015_2025_af": sn(own_avg, "acre-feet", "data/cache/%s/cdec.parquet" % pid, f"Mean of {s} storage on {last.date.strftime('%b %d')} over 2015-2025 (our cache)", fetched, True, method="computed",
                    note=f"{len(same)} years; short, drought-heavy window, so it reads lower than CDEC's long-term average"),
                "pct_of_own_average": sn(round(100 * float(last.storage_af) / own_avg, 1), "percent", "data/cache/%s/cdec.parquet" % pid, f"{s} vs own 2015-2025 same-day mean", fetched, True, method="computed"),
                "source_url": u}
    return res

def main():
    fetched = now()
    out = {"label": "Current conditions (observations)", "fetched_at": fetched, "presets": {}}
    cd = cdec(fetched)
    for pid in PRESETS:
        out["presets"][pid] = {"drought_monitor": usdm(pid, fetched), "reservoirs": cd[pid]}
    write_json(OUT / "water_now.json", out)
    for pid, p in out["presets"].items():
        u = p["drought_monitor"]; print(pid, u["map_date"], u["worst_category"], {k: v["value"] for k, v in u["area_in_category_percent"].items()})
        for s, r in p["reservoirs"].items():
            print("  ", s, r["latest_daily_date"], r["storage_af"]["value"], r["pct_of_cdec_average"]["value"], r["own_average_2015_2025_af"]["value"], r["pct_of_own_average"]["value"], r["capacity_af"]["value"])

if __name__ == "__main__":
    main()
