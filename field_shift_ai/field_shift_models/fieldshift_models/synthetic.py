"""FAKE but physically-flavoured data for testing the pipeline. Not NASA data; never use in the demo
or pitch. Labels are NOT derived from NDVI thresholds: a hidden daily cover fraction drives a
linear-mixing reflectance model (soil / vegetation / water / snow / haze) and, separately, a
simulated Sentinel-2 SCL pixel vote with misclassification, so neither the rule nor the ML gets
the answer for free.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# endmember surface reflectance: blue, green, red, nir, swir1, swir2
SOIL = np.array([0.08, 0.11, 0.15, 0.22, 0.32, 0.26])
VEG = np.array([0.03, 0.07, 0.04, 0.42, 0.20, 0.10])
RESIDUE = np.array([0.07, 0.10, 0.13, 0.25, 0.30, 0.22])  # dry stubble/residue
WATER = np.array([0.04, 0.05, 0.03, 0.02, 0.01, 0.01])
SNOW = np.array([0.80, 0.78, 0.75, 0.70, 0.10, 0.06])
HAZE = np.array([0.08, 0.06, 0.05, 0.03, 0.01, 0.0])
BANDS = ["blue", "green", "red", "nir", "swir1", "swir2"]

PRESETS = ["fv_sumas_dairy", "sr_salmon_river_hay", "ca_colusa_rice"]
CROP = {"fv_sumas_dairy": "silage_corn", "sr_salmon_river_hay": "alfalfa", "ca_colusa_rice": "rice"}


def _ramp(d, a, b):
    return np.clip((d - a) / max(b - a, 1), 0, 1)


def daily_state(loc: str, year: int, rng) -> pd.DataFrame:
    """Hidden truth per day: green cover, residue, water, snow fractions."""
    d = np.arange(1, 367 if pd.Timestamp(year, 12, 31).dayofyear == 366 else 366)
    green = np.zeros(len(d)); residue = np.zeros(len(d)); water = np.zeros(len(d)); snow = np.zeros(len(d))
    j = lambda x: x + rng.integers(-12, 13)
    if loc == "fv_sumas_dairy":
        plant, harvest = j(135), j(265)
        green = 0.92 * _ramp(d, plant + 15, plant + 60) * (d < harvest)
        residue[(d >= harvest)] = 0.35
        residue[d < plant] = 0.15
        if year in (2020, 2024):  # relay ryegrass cover crop in those winters
            green = np.maximum(green, 0.55 * _ramp(d, harvest + 10, harvest + 50) * (d >= harvest))
            green = np.maximum(green, 0.5 * (d < plant - 10) * (d < 100))
        if year == 2021:  # Nov 2021 flood
            water[(d >= 318) & (d <= 335)] = 0.7
        snow[(d < 40) | (d > 350)] = rng.random() * 0.4 * (rng.random() < 0.3)
    elif loc == "sr_salmon_river_hay":
        start, end = j(100), j(290)
        g = 0.35 + 0.6 * _ramp(d, start, start + 45)
        for cut in (j(165), j(215), j(262)):
            g = np.where((d >= cut) & (d < cut + 35), 0.25 + 0.6 * _ramp(d, cut, cut + 35), g)
        green = np.where((d >= start) & (d <= end), g, 0.12)
        if year == 2023:  # drought: no 3rd regrowth
            green = np.where(d > 230, np.minimum(green, 0.25), green)
        residue = 0.25 * (green < 0.3)
        sn = (d < 70) | (d > 330)
        snow[sn] = rng.uniform(0.3, 1.0, sn.sum()) * (rng.random(sn.sum()) < 0.6)
    else:  # rice
        if year == 2022:  # fallow
            green = 0.18 * _ramp(d, 60, 100) * (d < 160)
            residue[:] = 0.2
        else:
            flood, harvest = j(120), j(275)
            water[(d >= flood) & (d < flood + 50)] = 0.8 * (1 - _ramp(d, flood + 10, flood + 50))[(d >= flood) & (d < flood + 50)]
            green = 0.9 * _ramp(d, flood + 15, flood + 70) * (d < harvest)
            residue[d >= harvest] = 0.6
            residue[d < flood] = 0.4
    green = np.clip(green + rng.normal(0, 0.03, len(d)), 0, 1)
    return pd.DataFrame({"doy": d, "green": green, "residue": residue, "water": water, "snow": snow})


def _reflectance(st, soil_wet, haze, rng):
    g, r, w, s = st["green"], st["residue"], st["water"], st["snow"]
    r = min(r, 1 - g)
    w = min(w, 1 - g - r)
    s = min(s, 1 - g - r - w)
    soil = max(0.0, 1 - g - r - w - s)
    soil_em = SOIL * (1 - 0.35 * soil_wet)  # wet soil darker
    refl = g * VEG + r * RESIDUE + w * WATER + s * SNOW + soil * soil_em + haze * HAZE
    return refl + rng.normal(0, 0.008, 6)


def synthetic_observations(seed: int = 0, years=range(2019, 2026)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (obs table in the B6.1 input format, hidden truth per obs for diagnostics)."""
    rng = np.random.default_rng(seed)
    rows, truth = [], []
    clim = {loc: np.mean([daily_state(loc, y, np.random.default_rng(100 + y))["green"].values[:365]
                          for y in range(2000, 2019)], axis=0) for loc in PRESETS}
    for loc in PRESETS:
        for yr in years:
            st = daily_state(loc, yr, rng)
            for _, s in st.iloc[::3].iterrows():  # HLS revisit ~2-3 days
                doy = int(s.doy)
                winter = doy < 90 or doy > 300
                p_cloud = (0.75 if winter else 0.45) if loc != "ca_colusa_rice" else (0.5 if winter else 0.1)
                if rng.random() < p_cloud:
                    continue
                date = pd.Timestamp(yr, 1, 1) + pd.Timedelta(days=doy - 1)
                haze = rng.uniform(0.3, 1.0) if rng.random() < 0.12 else 0.0  # missed by Fmask
                wet = np.clip(rng.beta(2, 3) + (0.3 if winter else 0), 0, 1)
                refl = np.clip(_reflectance(s, wet, haze, rng), 0.001, 1)
                cover = s.green
                # Sentinel-2 SCL on the same day (~40% of dates): 400-pixel vote
                scl_b = scl_v = np.nan
                if rng.random() < 0.4:
                    n = 400
                    pix_veg = rng.random(n) < cover
                    pix_snow = rng.random(n) < s.snow
                    pix_water = rng.random(n) < s.water
                    flip = rng.random(n) < 0.08  # SCL misclassification
                    veg = np.where(flip, ~pix_veg, pix_veg) & ~pix_snow & ~pix_water
                    bare = ~veg & ~pix_snow & ~pix_water
                    if haze > 0:  # haze pushes SCL towards "not vegetated"
                        veg &= rng.random(n) > 0.25 * haze
                        bare = ~veg & ~pix_snow & ~pix_water
                    scl_b, scl_v = bare.mean(), veg.mean()
                in_season = np.nan
                if loc == "ca_colusa_rice" and yr != 2022:
                    in_season = 1.0 if 175 <= doy <= 255 else (0.0 if doy < 100 or doy > 300 else np.nan)
                rows.append({
                    "location_id": loc, "date": date.strftime("%Y-%m-%d"),
                    **dict(zip(BANDS, refl)),
                    "valid_fraction": rng.uniform(0.45, 1.0),
                    "snow_flag": int(s.snow > 0.3 and rng.random() < 0.85),
                    "modis_ndvi_clim": 0.1 + 0.7 * clim[loc][min(doy, 365) - 1],
                    "smap_pct": float(np.clip(100 * wet + rng.normal(0, 10), 0, 100)),
                    "imerg_7d_mm": float(rng.gamma(1.2, 18 if winter else 6)),
                    "power_tmax_7d_c": float(8 + 18 * np.sin(np.pi * np.clip(doy - 20, 0, 345) / 345) + rng.normal(0, 2)),
                    "scl_bare_frac": scl_b, "scl_veg_frac": scl_v,
                    "cdl_class": (61 if yr == 2022 else 3) if loc == "ca_colusa_rice" else np.nan,
                    "in_season": in_season, "crop_type": CROP[loc],
                })
                truth.append({"location_id": loc, "date": date.strftime("%Y-%m-%d"),
                              "true_green_cover": cover, "true_class": "bare" if cover < 0.2 else ("covered" if cover > 0.5 else "partial"),
                              "haze": haze > 0, "snow": s.snow})
    return pd.DataFrame(rows), pd.DataFrame(truth)


def synthetic_weekly(seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Weekly B6.2 input + hidden truth (injected stress, and non-stress wet/cold anomalies)."""
    rng = np.random.default_rng(seed)
    weeks = pd.date_range("2000-01-03", "2025-12-29", freq="W-MON")
    events = {
        "fv_sumas_dairy": [("2021-06-21", "2021-07-04", 2.5), ("2023-07-10", "2023-08-27", 1.3), ("2015-07-01", "2015-08-15", 1.0)],
        "sr_salmon_river_hay": [("2021-06-21", "2021-07-04", 2.5), ("2023-06-26", "2023-08-31", 1.8), ("2017-07-15", "2017-08-20", 1.2)],
        "ca_colusa_rice": [("2021-05-01", "2021-09-30", 1.4), ("2022-05-01", "2022-09-30", 1.6), ("2015-06-01", "2015-08-31", 1.2)],
    }
    season = {"fv_sumas_dairy": (140, 265), "sr_salmon_river_hay": (100, 290), "ca_colusa_rice": (130, 275)}
    rows, truth = [], []
    for loc in PRESETS:
        s, e = season[loc]
        doy = weeks.dayofyear.values
        seas = np.clip(np.sin(np.pi * (doy - s) / (e - s)), 0, 1)
        stress = np.zeros(len(weeks))
        for a, b, mag in events[loc]:
            m = (weeks >= a) & (weeks <= b)
            stress[m] = mag * rng.uniform(0.7, 1.2, m.sum())
        # non-stress anomalies: cold, wet weeks (should NOT be called stress)
        coldwet = (rng.random(len(weeks)) < 0.04) & (seas > 0)
        # slowly varying weather noise (AR(1))
        ar = np.zeros(len(weeks))
        for i in range(1, len(weeks)):
            ar[i] = 0.6 * ar[i - 1] + rng.normal(0, 0.5)
        t_anom = 1.5 * ar + 3.0 * stress - 4.0 * coldwet
        sm_anom = -0.6 * ar - 1.0 * stress + 1.5 * coldwet + rng.normal(0, 0.6, len(weeks))
        ndvi = 0.15 + 0.65 * seas - 0.06 * stress * seas + 0.01 * ar + rng.normal(0, 0.035, len(weeks))
        t2m = 4 + 22 * np.sin(np.pi * np.clip(doy - 30, 0, 330) / 330) + t_anom
        has_eco = (weeks.year >= 2018) & (rng.random(len(weeks)) < 0.45)
        has_smap = weeks.year >= 2015
        has_hls = (weeks.year >= 2015) & (rng.random(len(weeks)) < 0.6)
        for i, w in enumerate(weeks):
            rows.append({
                "location_id": loc, "week_start": w.strftime("%Y-%m-%d"),
                "in_season": int(s <= doy[i] <= e),
                "ndvi_modis": ndvi[i],
                "ndvi_hls": ndvi[i] + 0.03 + rng.normal(0, 0.025) if has_hls[i] else np.nan,
                "lst_k": 273.15 + t2m[i] + 1.5 + 2.0 * stress[i] + rng.normal(0, 1.8) if has_eco[i] else np.nan,
                "t2m_max_c": t2m[i],
                "esi": float(np.clip(0.85 - 0.12 * stress[i] + rng.normal(0, 0.08), 0, 1.2)) if has_eco[i] else np.nan,
                "smap_pct": float(np.clip(50 + 22 * sm_anom[i], 1, 99)) if has_smap[i] else np.nan,
                "eto_mm": max(0.0, 28 * seas[i] + 6 + 1.2 * t_anom[i] + rng.normal(0, 2.5)),
                "imerg_30d_mm": max(0.0, 55 + 18 * sm_anom[i] + rng.normal(0, 15)),
            })
            truth.append({"location_id": loc, "week_start": w.strftime("%Y-%m-%d"),
                          "true_stress": stress[i] > 0, "cold_wet": bool(coldwet[i])})
    return pd.DataFrame(rows), pd.DataFrame(truth)
