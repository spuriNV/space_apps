"""Hargreaves ETo (FAO-56 eq. 52) + risk-day flags (spec B5.3) from POWER daily.
Writes backend/regional/out/<id>/{daily_derived.parquet,risk_days_by_year.json,eto_monthly.json}"""
import numpy as np, pandas as pd
from common import *

GSC = 0.0820  # MJ m-2 min-1

def ra_mj(lat_deg, doy):
    """Extraterrestrial radiation, FAO-56 eq. 21 (MJ m-2 day-1)."""
    phi = np.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    return (24 * 60 / np.pi) * GSC * dr * (ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))

def hargreaves_eto(tmax, tmin, lat_deg, doy):
    """FAO-56 eq. 52, mm/day. Tmean=(Tmax+Tmin)/2 as FAO-56 specifies; Ra converted with 0.408."""
    tmean = (tmax + tmin) / 2
    ra = 0.408 * ra_mj(lat_deg, doy)
    return np.maximum(0.0023 * (tmean + 17.8) * np.sqrt(np.maximum(tmax - tmin, 0)) * ra, 0)

def runs_ge3(flag):
    """True for every day belonging to a run of >=3 consecutive True days."""
    s = flag.astype(int); g = (s != s.shift()).cumsum()
    return flag & (s.groupby(g).transform("size") >= 3)

def main():
    for pid, p in PRESETS.items():
        d = pd.read_parquet(cache_dir(pid) / "power.parquet").set_index("date")
        d["doy"] = d.index.day_of_year
        d["ra_mm_day"] = 0.408 * ra_mj(p["lat"], d["doy"].values)
        d["eto_hargreaves_mm"] = hargreaves_eto(d.T2M_MAX, d.T2M_MIN, p["lat"], d["doy"].values)
        d["eto_hargreaves_plus2C_mm"] = hargreaves_eto(d.T2M_MAX + 2, d.T2M_MIN + 2, p["lat"], d["doy"].values)
        pr = d.PRECTOTCORR
        base = d.index.year <= 2025   # thresholds and climatologies stay on the 1981-2025 baseline; 2026 is a partial year
        wet = pr[(pr >= 1.0) & base]
        p95 = float(wet.quantile(0.95))
        d["frost"] = d.T2M_MIN <= 0
        d["hard_frost"] = d.T2M_MIN <= -2
        d["heat"] = d.T2M_MAX >= 35
        d["severe_heat"] = d.T2M_MAX >= 40
        d["heatwave_day"] = runs_ge3(d["heat"])
        d["extreme_rain_25mm"] = pr >= 25
        d["rain_3day_75mm"] = pr.rolling(3).sum() >= 75
        d["extreme_rain_p95wet"] = pr >= p95
        flags = ["frost", "hard_frost", "heat", "severe_heat", "heatwave_day", "extreme_rain_25mm", "rain_3day_75mm", "extreme_rain_p95wet"]
        out = OUT / pid; out.mkdir(parents=True, exist_ok=True)
        d.drop(columns="doy").reset_index().to_parquet(out / "daily_derived.parquet", index=False)

        yr = d.index.year
        byyear = {}
        for y in sorted(set(yr)):
            m = d[yr == y]
            row = {f: int(m[f].sum()) for f in flags}
            # heatwave events = number of runs starting that year
            hw = m["heat"].astype(int); starts = ((hw == 1) & (hw.shift(fill_value=0) == 0))
            row["heatwave_events"] = int((starts & m["heatwave_day"]).sum())
            row["precip_mm"] = round(float(m.PRECTOTCORR.sum()), 1)
            row["eto_hargreaves_mm"] = round(float(m.eto_hargreaves_mm.sum()), 1)
            row["days_with_data"] = int(len(m))
            if len(m) < 365 + int(y % 4 == 0):
                row["partial_year_through"] = str(m.index.max().date())  # not a full calendar year: counts are year-to-date
            byyear[str(y)] = row
        write_json(out / "risk_days_by_year.json", {
            "preset_id": pid, "source": "NASA POWER daily point (MERRA-2/SYN1DEG, 0.5 deg), data/cache/%s/power.parquet" % pid,
            "definitions": {
                "frost": "T2M_MIN <= 0 C", "hard_frost": "T2M_MIN <= -2 C (spec U)",
                "heat": "T2M_MAX >= 35 C", "severe_heat": "T2M_MAX >= 40 C",
                "heatwave_day": "day inside a run of >= 3 consecutive days with T2M_MAX >= 35 C",
                "extreme_rain_25mm": "PRECTOTCORR >= 25 mm/day (our definition, spec U)",
                "rain_3day_75mm": "3-day PRECTOTCORR sum >= 75 mm",
                "extreme_rain_p95wet": "PRECTOTCORR >= 95th percentile of wet days (>=1 mm), 1981-2025; threshold below",
                "p95_wet_day_threshold_mm": round(p95, 2)},
            "caveat": "POWER rain is a coarse (~50 km) reanalysis product and smooths convective/extreme rain; extreme-rain counts are likely low-biased vs gauges. Calendar years. POWER time standard is LST.",
            "by_year": byyear})
        em = d.groupby([yr, d.index.month]).eto_hargreaves_mm.sum().round(1)
        clim = em[em.index.get_level_values(0) <= 2025].groupby(level=1).mean().round(1)
        write_json(out / "eto_monthly.json", {
            "preset_id": pid, "unit": "mm/month", "method": "Hargreaves, FAO-56 eq. 52 (Tmean=(Tmax+Tmin)/2, Ra from latitude %.2f and day of year)" % p["lat"],
            "source": "NASA POWER T2M_MAX/T2M_MIN", "caveat": "Hargreaves is a temperature-only estimate (+/-15%% planning range per spec B4.12); validate against CIMIS when key available.",
            "climatology_1981_2025": {str(m): float(v) for m, v in clim.items()},
            "partial_year_note": "2026 months after the last POWER day are null; the last month with data is a partial month.",
            "by_year": {str(y): [(None if np.isnan(em.get((y, m), np.nan)) else float(em.get((y, m)))) for m in range(1, 13)] for y in sorted(set(yr))}})
        print(pid, len(d), d.index.max().date(), "p95wet", round(p95, 1), "annual ETo mean 1981-2025", round(d.eto_hargreaves_mm[base].groupby(yr[base]).sum().mean()))

if __name__ == "__main__":
    main()
