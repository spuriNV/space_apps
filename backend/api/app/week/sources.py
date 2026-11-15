"""SourcedNumber / Source helpers for this package (schemas/sourced_number.schema.json)."""
from __future__ import annotations

import datetime as dt


def today() -> str:
    return dt.date.today().isoformat()


SOURCES = {
    "open_meteo": ("open_meteo_forecast", "Open-Meteo forecast API (daily precipitation, temperature, FAO-56 ET0)", "https://open-meteo.com/en/docs"),
    "nws": ("nws_gridpoint_forecast", "US National Weather Service forecast (api.weather.gov gridpoint data)", "https://www.weather.gov/documentation/services-web-api"),
    "nws_alerts": ("nws_alerts", "US National Weather Service active alerts", "https://www.weather.gov/documentation/services-web-api"),
    "hargreaves": ("fao56_hargreaves", "FAO-56 eq. 52 (Hargreaves) reference evapotranspiration from forecast Tmax/Tmin", "https://www.fao.org/4/x0490e/x0490e07.htm"),
    "kc": ("fao56_kc", "FAO-56 crop coefficients (Table 12), by day from the rotation engine's baseline calendar", "https://www.fao.org/4/x0490e/x0490e0b.htm"),
    "kc_bare": ("fao56_kc_bare", "FAO-56 bare soil Kc, 0.15 (observed bare or fallow field)", "https://www.fao.org/4/x0490e/x0490e0b.htm"),
    "rule": ("croplytics_this_week_rule", "CropLytics rule of thumb (not a model)", "urn:fieldshift:assumed"),
    "smap_l4": ("nasa_smap_l4", "NASA SMAP L4 surface soil moisture (SPL4SMGP)", "https://nsidc.org/data/spl4smgp"),
    "grace": ("nasa_grace_da", "NASA GRACE-FO data assimilation, surface / root-zone soil moisture percentile", "https://disc.gsfc.nasa.gov/datasets/GRACEDADM_CLSM0125US_7D_4.0/summary"),
    "power": ("nasa_power_gwettop", "NASA POWER GWETTOP (MERRA-2 surface soil wetness)", "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"),
    "nass": ("usda_nass_quickstats", "USDA NASS Quick Stats", "https://quickstats.nass.usda.gov/"),
}


def src(key: str, verified: bool = True, url: str | None = None, title: str | None = None) -> dict:
    i, t, u = SOURCES[key]
    return {"id": i, "title": title or t, "url": url or u, "accessed": today(), "verified": verified}


def sn(value, unit: str, source: dict, method: str = "computed", note: str | None = None, low=None, high=None) -> dict:
    d = {"value": None if value is None else round(float(value), 3), "unit": unit, "method": method, "source": source}
    if low is not None:
        d["low"] = round(float(low), 3)
    if high is not None:
        d["high"] = round(float(high), 3)
    if note:
        d["note"] = note
    return d
