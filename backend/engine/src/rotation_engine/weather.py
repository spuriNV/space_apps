"""Weather input: NASA POWER daily + reference ETo (default FAO-56 Penman-Monteith eq. 6 with NOAA station
Tmax/Tmin; Hargreaves eq. 52 kept as an alternative method).

Order of preference:
1. data/cache/<preset_id>/power.parquet  (regional chunk; fills already NaN)
2. backend/engine/.cache/<preset_id>/power.parquet  (our own fetch)
3. fetch POWER daily point (no auth) into (2).
"""
from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

CHUNK = Path(__file__).resolve().parents[2]
REPO = CHUNK.parents[1]
PRESETS = {
    "car_colusa_rice": {"lat": 39.15, "lon": -122.10, "name": "Colusa County rice check (example)"},
    "caf_tulare_forage": {"lat": 36.20, "lon": -119.60, "name": "Tulare/Kings dairy forage field (example)"},
}
# The other registry fields (backend/fields/registry.json; FIELDSHIFT_FIELDS limits the list)
import sys as _sys
_sys.path.insert(0, str(REPO / "backend" / "fields"))
import fieldreg  # noqa: E402
for _id in fieldreg.selected():
    if _id not in PRESETS:
        _lon, _lat = fieldreg.point(_id)
        PRESETS[_id] = {"lat": _lat, "lon": _lon, "name": fieldreg.get(_id)["name"]}
PRESETS = {k: v for k, v in PRESETS.items() if k in fieldreg.selected()}
POWER_PARAMS = "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR"
POWER_BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"
ELEV_M = {"car_colusa_rice": 57.4, "caf_tulare_forage": 106.1}  # POWER cell elevation (regional power.meta.json)


def power_url(lat: float, lon: float, start="19810101", end="20251231") -> str:
    q = dict(parameters=POWER_PARAMS, community="AG", longitude=lon, latitude=lat, start=start, end=end,
             format="JSON")
    return POWER_BASE + "?" + urllib.parse.urlencode(q)


def _fetch_power(preset_id: str, dest: Path) -> None:
    p = PRESETS[preset_id]
    url = power_url(p["lat"], p["lon"])
    with urllib.request.urlopen(url, timeout=300) as resp:
        js = json.load(resp)
    par = js["properties"]["parameter"]
    df = pd.DataFrame(par)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.replace(-999.0, np.nan)
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index().to_parquet(dest, index=False)
    dest.with_suffix(".meta.json").write_text(json.dumps(
        {"url": url, "fetched_at": pd.Timestamp.utcnow().isoformat(), "fill_value": -999.0, "auth": "none",
         "units": js.get("parameters", {})}, indent=1))


@dataclass
class Weather:
    preset_id: str
    lat: float
    df: pd.DataFrame  # index date; T2M, T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR
    path: str
    url: str
    provenance: str
    elev_m: float = 0.0
    notes: list[str] = field(default_factory=list)

    def source(self) -> dict:
        return {"id": "nasa_power_daily", "title": f"NASA POWER daily point ({self.provenance})", "url": self.url,
                "accessed": "2026-11-14", "verified": True, "cache_path": self.path}


_CACHE: dict[str, Weather] = {}


def load_weather(preset_id: str) -> Weather:
    if preset_id in _CACHE:
        return _CACHE[preset_id]
    p = PRESETS[preset_id]
    regional = REPO / "data" / "cache" / preset_id / "power.parquet"
    own = CHUNK / ".cache" / preset_id / "power.parquet"
    if regional.exists():
        path, prov = regional, "regional chunk cache data/cache"
        meta_p = regional.with_name("power.meta.json")
    else:
        if not own.exists():
            _fetch_power(preset_id, own)
        path, prov = own, "engine fetch backend/engine/.cache"
        meta_p = own.with_suffix(".meta.json")
    url = power_url(p["lat"], p["lon"])
    elev = ELEV_M.get(preset_id)
    if elev is None:   # registry fields: POWER cell elevation from the regional cache meta
        mp = REPO / "data" / "cache" / preset_id / "power.meta.json"
        elev = json.loads(mp.read_text()).get("elevation_m", 0.0) if mp.exists() else 0.0
    if meta_p.exists():
        meta = json.loads(meta_p.read_text())
        url = meta.get("url", url)
        elev = float(meta.get("elevation_m") or elev)
    df = pd.read_parquet(path)
    if "date" in df.columns:
        df = df.set_index(pd.to_datetime(df["date"])).drop(columns=["date"])
    df.index = pd.to_datetime(df.index)
    df = df.replace(-999.0, np.nan).sort_index()
    w = Weather(preset_id, p["lat"], df, str(path.relative_to(REPO)), url, prov, elev_m=elev)
    _CACHE[preset_id] = w
    return w


# ----------------------------------------------------------- FAO-56 radiation / ETo
def ra_mj(lat_deg: float, doy: np.ndarray) -> np.ndarray:
    """Extraterrestrial radiation Ra [MJ m-2 day-1], FAO-56 eqs. 21-25."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    return (24 * 60 / np.pi) * 0.0820 * dr * (ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))


def hargreaves_eto(tmax: np.ndarray, tmin: np.ndarray, lat_deg: float, doy: np.ndarray) -> np.ndarray:
    """FAO-56 eq. 52: ETo = 0.0023 (Tmean + 17.8) (Tmax - Tmin)^0.5 Ra, Ra as mm/day (x 0.408)."""
    tmean = (tmax + tmin) / 2.0
    return 0.0023 * (tmean + 17.8) * np.sqrt(np.clip(tmax - tmin, 0, None)) * 0.408 * ra_mj(lat_deg, doy)


def sat_vp(t: np.ndarray) -> np.ndarray:
    """FAO-56 eq. 11, kPa."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def power_ea(df: pd.DataFrame) -> np.ndarray:
    """Actual vapour pressure from POWER daily mean RH2M (FAO-56 eq. 19, the RHmean form), kPa."""
    es = (sat_vp(df["T2M_MAX"].to_numpy(dtype=float)) + sat_vp(df["T2M_MIN"].to_numpy(dtype=float))) / 2
    return np.clip(df["RH2M"].to_numpy(dtype=float), 0, 100) / 100 * es


def pm_eto(tmax, tmin, ea, rs, u2, lat_deg: float, elev_m: float, doy: np.ndarray) -> np.ndarray:
    """FAO-56 Penman-Monteith grass reference ETo (eq. 6), daily, soil heat flux G = 0 (eq. 42).

    Tmean = (Tmax+Tmin)/2; es eq. 12; Delta eq. 13; P eq. 7; gamma eq. 8; Rso eq. 37; Rns eq. 38 (albedo 0.23);
    Rnl eq. 39 with Rs/Rso capped at 1.0. https://www.fao.org/4/x0490e/x0490e06.htm (ch. 2) and x0490e07.htm (ch. 3)
    """
    t = (tmax + tmin) / 2
    es = (sat_vp(tmax) + sat_vp(tmin)) / 2
    vpd = np.clip(es - ea, 0, None)
    delta = 4098 * sat_vp(t) / (t + 237.3) ** 2
    gamma = 0.665e-3 * 101.3 * ((293 - 0.0065 * elev_m) / 293) ** 5.26
    rso = (0.75 + 2e-5 * elev_m) * ra_mj(lat_deg, doy)
    ratio = np.clip(rs / rso, 0.25, 1.0)
    rnl = 4.903e-9 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * ratio - 0.35)
    rn = 0.77 * rs - rnl
    eto = (0.408 * delta * rn + gamma * 900 / (t + 273) * u2 * vpd) / (delta + gamma * (1 + 0.34 * u2))
    return np.clip(eto, 0, None)


# ETo methods. Default: FAO-56 Penman-Monteith (eq. 6, the FAO-56 standard; Hargreaves eq. 52 is its fallback when
# radiation/humidity/wind are missing) with NOAA station Tmax/Tmin (POWER reads +3.4 C (CAR) / +3.8 C (CAF) warm in
# Jul-Aug vs the 3 nearest GHCN-D stations, backend/regional/README.md) and POWER radiation, humidity (ea) and wind.
ETO_METHODS = ("pm_station_t", "pm_power", "harg_station", "harg_power")
DEFAULT_ETO = "pm_station_t"


@dataclass
class YearWeather:
    year: int
    tmax: np.ndarray
    tmin: np.ndarray
    p: np.ndarray
    eto: np.ndarray
    p_30d: np.ndarray       # trailing 30-day precipitation (incl. previous Dec)
    p_30d_clim: np.ndarray  # 1991-2020 mean of the same trailing sums by day-of-year (365)


def _no_leap(df: pd.DataFrame) -> pd.DataFrame:
    return df[~((df.index.month == 2) & (df.index.day == 29))]


def eto_series(w: Weather, cur: pd.DataFrame, method: str = DEFAULT_ETO, dT_c: float = 0.0) -> np.ndarray:
    """Daily ETo (mm) for the rows of `cur` (non-leap POWER rows of one year). dT_c shifts Tmax/Tmin; ea is held
    fixed (constant absolute humidity under the scenario shift, our assumption)."""
    doy = np.arange(1, len(cur) + 1)
    ptx = cur["T2M_MAX"].to_numpy(dtype=float)
    ptn = cur["T2M_MIN"].to_numpy(dtype=float)
    if method.endswith("station") or method == "pm_station_t":
        st = station_temps(w.preset_id)
        if st is not None:
            t = st.reindex(cur.index)
            ptx = t["tmax"].fillna(cur["T2M_MAX"]).to_numpy(dtype=float)
            ptn = t["tmin"].fillna(cur["T2M_MIN"]).to_numpy(dtype=float)
    tx, tn = ptx + dT_c, ptn + dT_c
    if method.startswith("harg"):
        return hargreaves_eto(tx, tn, w.lat, doy)
    rs = cur["ALLSKY_SFC_SW_DWN"].to_numpy(dtype=float)
    u2 = cur["WS2M"].to_numpy(dtype=float)
    if np.isnan(rs).any() or np.isnan(u2).any():
        raise ValueError(f"POWER radiation/wind gaps for {w.preset_id}")
    return pm_eto(tx, tn, power_ea(cur), rs, u2, w.lat, w.elev_m, doy)


def year_weather(w: Weather, year: int, dT_c: float = 0.0, dP_pct: float = 0.0,
                 eto_method: str = DEFAULT_ETO) -> YearWeather:
    """365-day arrays for one calendar year, with a uniform scenario shift (spec B4.12).
    tmax/tmin stay POWER (risk days); only ETo uses the station temperatures."""
    df = _no_leap(w.df)
    clim = _p30_climatology(w)
    sl = df.loc[f"{year - 1}-12-01":f"{year}-12-31"]
    pscale = 1 + dP_pct / 100.0
    p_all = sl["PRECTOTCORR"].to_numpy(dtype=float) * pscale
    p30_all = pd.Series(p_all).rolling(30, min_periods=30).sum().to_numpy()
    cur = sl.loc[f"{year}-01-01":]
    n = len(cur)
    if n != 365:
        raise ValueError(f"POWER year {year} has {n} non-leap days for {w.preset_id}")
    tmax = cur["T2M_MAX"].to_numpy(dtype=float) + dT_c
    tmin = cur["T2M_MIN"].to_numpy(dtype=float) + dT_c
    if np.isnan(tmax).any() or np.isnan(tmin).any():
        raise ValueError(f"POWER temperature gaps in {year} for {w.preset_id}")
    eto = eto_series(w, cur, eto_method, dT_c)
    return YearWeather(year, tmax, tmin, p_all[-365:], eto, p30_all[-365:], clim)


_CLIM: dict[str, np.ndarray] = {}


def _p30_climatology(w: Weather) -> np.ndarray:
    if w.preset_id in _CLIM:
        return _CLIM[w.preset_id]
    df = _no_leap(w.df).loc["1990-12-01":"2020-12-31"]
    s = df["PRECTOTCORR"].rolling(30, min_periods=30).sum()
    s = s.loc["1991-01-01":]
    doy = np.tile(np.arange(365), len(s) // 365 + 1)[: len(s)]
    clim = pd.Series(s.to_numpy()).groupby(doy).mean().to_numpy()
    _CLIM[w.preset_id] = clim
    return clim


# ----------------------------------------------------------- second precipitation source
@dataclass
class StationPrecip:
    series: pd.Series   # daily mean over the selected stations, mm (NaN where none reported)
    url: str
    path: str
    stations: list


_ST: dict[str, StationPrecip | None] = {}


def station_cache(preset_id: str) -> Path | None:
    """The station cache for a field: NOAA NCEI (data/cache/<id>/ncei.parquet, CA) or, when that is absent,
    ECCC daily climate (data/cache/<id>/eccc.parquet, BC; same columns date/station/tmax_c/tmin_c/prcp_mm)."""
    for name in ("ncei", "eccc"):
        p = REPO / "data" / "cache" / preset_id / f"{name}.parquet"
        if p.exists():
            return p
    return None


def station_network(preset_id: str) -> str | None:
    """'ncei', 'eccc' or None (no station cache)."""
    p = station_cache(preset_id)
    return p.stem if p else None


def load_station_precip(preset_id: str) -> StationPrecip | None:
    """Station daily PRCP (NOAA NCEI, or ECCC for BC) from data/cache, mean over its selected stations."""
    if preset_id in _ST:
        return _ST[preset_id]
    path = station_cache(preset_id)
    if path is None:
        _ST[preset_id] = None
        return None
    meta_p = path.with_name(path.stem + ".meta.json")
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    s = df.groupby("date")["prcp_mm"].mean()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))
    sp = StationPrecip(s, meta.get("url", "https://www.ncei.noaa.gov/access/services/data/v1"),
                       str(path.relative_to(REPO)), [x.get("station") for x in meta.get("selected_stations", [])])
    _ST[preset_id] = sp
    return sp


def station_year_precip(sp: StationPrecip, power_year: YearWeather, year: int, dP_pct: float = 0.0,
                        min_coverage: float = 0.95) -> np.ndarray | None:
    """365-day station precipitation; None if coverage < 95%. Remaining gaps take the POWER value that day."""
    s = sp.series
    s = s[~((s.index.month == 2) & (s.index.day == 29))]
    cur = s.loc[f"{year}-01-01":f"{year}-12-31"].reindex(
        [d for d in pd.date_range(f"{year}-01-01", f"{year}-12-31") if not (d.month == 2 and d.day == 29)])
    if len(cur) != 365 or cur.notna().mean() < min_coverage:
        return None
    arr = cur.to_numpy(dtype=float) * (1 + dP_pct / 100.0)
    gaps = np.isnan(arr)
    arr[gaps] = power_year.p[gaps]
    return arr


_STT: dict[str, pd.DataFrame | None] = {}


def station_temps(preset_id: str) -> pd.DataFrame | None:
    """Station daily Tmax/Tmin (C; NOAA NCEI, or ECCC for BC), mean over the selected stations that report both
    that day."""
    if preset_id in _STT:
        return _STT[preset_id]
    path = station_cache(preset_id)
    if path is None:
        _STT[preset_id] = None
        return None
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["tmax_c", "tmin_c"])
    df = df[df.tmax_c >= df.tmin_c]
    out = df.groupby("date")[["tmax_c", "tmin_c"]].mean().rename(columns={"tmax_c": "tmax", "tmin_c": "tmin"})
    _STT[preset_id] = out
    return out
