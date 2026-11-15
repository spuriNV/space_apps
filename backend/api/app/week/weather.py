"""Upstream reads for this_week: Open-Meteo forecast (NWS gridpoint + Hargreaves as the single fallback), NWS alerts,
and the soil-wetness percentile (SMAP L4 cache, else GRACE-DA cache, else a live NASA POWER GWETTOP read).
Every function returns plain data or raises; router.py turns failures into section statuses."""
from __future__ import annotations

import datetime as dt
import math
import re
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import numpy as np

UA = {"User-Agent": "CropLytics (NASA Space Apps)", "Accept": "application/geo+json"}
TIMEOUT = httpx.Timeout(8.0, connect=4.0)
OM = "https://api.open-meteo.com/v1/forecast"


def _get(url, **kw):
    r = httpx.get(url, timeout=TIMEOUT, follow_redirects=True, **kw)
    r.raise_for_status()
    return r.json()


# ------------------------------------------------------------------------------------------------ forecast
def open_meteo(lat: float, lon: float) -> dict:
    j = _get(OM, params={"latitude": lat, "longitude": lon, "forecast_days": 7, "past_days": 2, "timezone": "auto",
                         "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,et0_fao_evapotranspiration"})
    d, tz = j["daily"], j.get("timezone", "UTC")
    today = dt.datetime.now(ZoneInfo(tz)).date().isoformat()
    rows = [{"date": t, "rain_mm": d["precipitation_sum"][i], "tmax_c": d["temperature_2m_max"][i], "tmin_c": d["temperature_2m_min"][i],
             "et0_mm": d["et0_fao_evapotranspiration"][i]} for i, t in enumerate(d["time"])]
    return _split(rows, today, tz, "open_meteo", "Open-Meteo (FAO-56 Penman-Monteith ET0)")


def _split(rows, today, tz, source, et0_method):
    fut = [r for r in rows if r["date"] >= today][:7]
    past = [r for r in rows if r["date"] < today][-2:]
    if len(fut) < 7 or any(r["rain_mm"] is None or r["tmax_c"] is None or r["tmin_c"] is None for r in fut):
        raise ValueError("incomplete 7-day forecast")
    return {"days": fut, "past": past, "tz": tz, "source": source, "et0_method": et0_method, "today": today}


_DUR = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?)?")


def _slices(values, tz):
    """NWS gridpoint series -> list of (local_date, hour_fraction_value, hours)."""
    for v in values:
        if v["value"] is None:
            continue
        start, dur = v["validTime"].split("/")
        m = _DUR.fullmatch(dur)
        hours = int(m.group(1) or 0) * 24 + int(m.group(2) or 0) or 1
        t0 = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
        yield t0, hours, float(v["value"])


def nws_forecast(lat: float, lon: float) -> dict:
    pt = _get(f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}", headers=UA)["properties"]
    tz = pt.get("timeZone", "America/Los_Angeles")
    z = ZoneInfo(tz)
    g = _get(pt["forecastGridData"], headers=UA)["properties"]
    rain: dict[str, float] = {}
    for t0, hours, val in _slices(g["quantitativePrecipitation"]["values"], tz):
        for h in range(hours):
            day = (t0 + dt.timedelta(hours=h)).astimezone(z).date().isoformat()
            rain[day] = rain.get(day, 0.0) + val / hours
    tmax: dict[str, float] = {}
    tmin: dict[str, float] = {}
    for key, store, fn in (("maxTemperature", tmax, max), ("minTemperature", tmin, min)):
        for t0, hours, val in _slices(g[key]["values"], tz):
            day = t0.astimezone(z).date().isoformat()
            store[day] = fn(store[day], val) if day in store else val
    today = dt.datetime.now(z).date()
    days = [(today + dt.timedelta(days=i)).isoformat() for i in range(7)]
    if not all(d in tmax and d in tmin for d in days):
        raise ValueError("NWS grid forecast shorter than 7 days")
    tx, tn = np.array([tmax[d] for d in days]), np.array([tmin[d] for d in days])
    doy = np.array([dt.date.fromisoformat(d).timetuple().tm_yday for d in days])
    from rotation_engine.weather import hargreaves_eto  # noqa: PLC0415
    et0 = hargreaves_eto(tx, tn, lat, doy)
    rows = [{"date": d, "rain_mm": round(rain.get(d, 0.0), 1), "tmax_c": float(tx[i]), "tmin_c": float(tn[i]), "et0_mm": float(et0[i])}
            for i, d in enumerate(days)]
    past = [{"date": (today - dt.timedelta(days=k)).isoformat(), "rain_mm": round(rain.get((today - dt.timedelta(days=k)).isoformat(), 0.0), 1)} for k in (2, 1)]
    return {"days": rows, "past": past, "tz": tz, "source": "nws", "today": today.isoformat(),
            "et0_method": "Hargreaves (FAO-56 eq. 52) from NWS forecast Tmax/Tmin; Open-Meteo was unavailable"}


# ------------------------------------------------------------------------------------------------ alerts
def nws_alerts(lat: float, lon: float) -> list[dict]:
    j = _get("https://api.weather.gov/alerts/active", headers=UA, params={"point": f"{lat:.4f},{lon:.4f}"})
    out = []
    for f in j.get("features", []):
        p = f["properties"]
        out.append({"event": p.get("event"), "severity": p.get("severity"), "urgency": p.get("urgency"), "headline": p.get("headline"),
                    "onset": p.get("onset") or p.get("effective"), "ends": p.get("ends") or p.get("expires"),
                    "area": p.get("areaDesc"), "url": p.get("@id") or f.get("id")})
    return out


def in_us(lat: float, lon: float) -> bool:
    """Rough US box (CONUS, Alaska, Hawaii); NWS answers 404 outside its area, which is treated as no alerts."""
    return (24.0 <= lat <= 49.6 and -125.0 <= lon <= -66.5) or (51 <= lat <= 72 and -170 <= lon <= -129) or (18.5 <= lat <= 22.5 and -161 <= lon <= -154)


# ------------------------------------------------------------------------------------------------ soil wetness
def _pct_same_season(dates: np.ndarray, vals: np.ndarray, d_latest, v_latest, window=15) -> tuple[float, int] | None:
    """Mid-rank percentile of v_latest among earlier values within +-window days of the same day of year."""
    doy = np.array([x.timetuple().tm_yday for x in dates])
    k = d_latest.timetuple().tm_yday
    dd = np.minimum(np.abs(doy - k), 365 - np.abs(doy - k))
    older = np.array([x.year for x in dates]) < d_latest.year
    ref = vals[(dd <= window) & older & np.isfinite(vals)]
    if len(ref) < 30:
        return None
    return 100.0 * ((ref < v_latest).sum() + 0.5 * (ref == v_latest).sum()) / len(ref), len(ref)


def smap_l4_cached(cache: Path):
    """Latest SMAP L4 surface (0-5 cm) moisture against this field's own same-season history."""
    f = cache / "smap_l4.parquet"
    if not f.is_file():
        return None
    import pandas as pd  # noqa: PLC0415
    df = pd.read_parquet(f)
    if "date" in df.columns:
        df = df.set_index("date")
    if "sm_surface" not in df.columns:
        return None
    s = df["sm_surface"].astype(float).groupby(pd.to_datetime(df.index).normalize()).mean().dropna().sort_index()
    if s.empty:
        return None
    d = s.index[-1].date()
    r = _pct_same_season(np.array([x.date() for x in s.index]), s.to_numpy(), d, s.iloc[-1])
    return None if r is None else {"pct": r[0], "obs_date": d.isoformat(), "n_ref": r[1], "kind": "smap_l4", "what": "SMAP L4 surface soil moisture (0-5 cm)",
                                   "value": float(s.iloc[-1]), "unit": "m3/m3"}


def grace_cached(cache: Path):
    """GRACE-DA surface (else root-zone) soil moisture percentile; the product already is a percentile."""
    f = cache / "grace.parquet"
    if not f.is_file():
        return None
    import pandas as pd  # noqa: PLC0415
    df = pd.read_parquet(f)
    for col, what in (("sfsm_inst", "GRACE-DA surface soil moisture percentile"), ("rtzsm_inst", "GRACE-DA root-zone soil moisture percentile")):
        if col in df.columns and df[col].notna().any():
            d = df.dropna(subset=[col]).sort_values("date").iloc[-1]
            return {"pct": float(d[col]), "obs_date": pd.Timestamp(d["date"]).date().isoformat(), "n_ref": None, "kind": "grace", "what": what, "value": float(d[col]), "unit": "percentile"}
    return None


def power_gwettop(lat: float, lon: float):
    """One NASA POWER daily GWETTOP series (2015 to today) at the point; percentile of the latest value for the season."""
    end = dt.date.today()
    j = _get("https://power.larc.nasa.gov/api/temporal/daily/point", params={
        "parameters": "GWETTOP", "community": "AG", "latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}",
        "start": "20150101", "end": end.strftime("%Y%m%d"), "format": "JSON"})
    series = j["properties"]["parameter"]["GWETTOP"]
    items = [(dt.datetime.strptime(k, "%Y%m%d").date(), v) for k, v in series.items() if v is not None and v > -900]
    if not items:
        return None
    items.sort()
    d, v = items[-1]
    r = _pct_same_season(np.array([x[0] for x in items]), np.array([x[1] for x in items], dtype=float), d, v)
    return None if r is None else {"pct": r[0], "obs_date": d.isoformat(), "n_ref": r[1], "kind": "power", "what": "NASA POWER GWETTOP surface soil wetness (0-1)",
                                   "value": float(v), "unit": "fraction"}


def wetness(cache: Path | None, lat: float, lon: float, today: dt.date, max_age_days: int = 21):
    """First usable of SMAP L4 (cached), GRACE-DA (cached), POWER GWETTOP (live). A reading older than max_age_days is skipped."""
    tried = []
    for name, fn in (("smap_l4", lambda: smap_l4_cached(cache) if cache else None), ("grace", lambda: grace_cached(cache) if cache else None),
                     ("power", lambda: power_gwettop(lat, lon))):
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001
            tried.append(f"{name}: {type(e).__name__}")
            continue
        if r is None:
            tried.append(f"{name}: not available")
            continue
        age = (today - dt.date.fromisoformat(r["obs_date"])).days
        if age > max_age_days:
            tried.append(f"{name}: latest reading {r['obs_date']} is {age} days old")
            continue
        r["age_days"], r["skipped"] = age, tried
        return r
    return {"skipped": tried}
