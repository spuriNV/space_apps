"""Build the B6.1 observation table for the California preset (ca_colusa_rice) from real data:
Sentinel-2 C1 L2A field medians + SCL fractions, NASA POWER daily, USDA CDL classes."""
import sys
import pandas as pd

D = "data/"
LOC = "ca_colusa_rice"

s2 = pd.read_csv(D + "fs_s2_ca_colusa_rice_merged.csv", parse_dates=["date"])
pw = pd.read_csv(D + "fs_power_ca_colusa_rice.csv", dtype={"date": str})
pw["date"] = pd.to_datetime(pw["date"], format="%Y%m%d")
pw = pw.set_index("date").sort_index()
pw7 = pd.DataFrame({
    "power_tmax_7d_c": pw["T2M_MAX"].rolling(7, min_periods=7).mean(),
    # stand-in for IMERG 7-day total until GPM IMERG is pulled (needs Earthdata login)
    "imerg_7d_mm": pw["PRECTOTCORR"].rolling(7, min_periods=7).sum(),
})
cdl = pd.read_csv(D + "fs_cdl_ca_colusa_rice.csv").set_index("year")
cdl_major = cdl.mode(axis=1)[0].astype(int)

obs = s2.rename(columns={"scl_snow_frac": "snow_frac"}).copy()
obs["location_id"] = LOC
obs["snow_flag"] = (obs["snow_frac"] > 0.5).astype(int)
obs = obs.merge(pw7, left_on="date", right_index=True, how="left")
obs["cdl_class"] = obs["date"].dt.year.map(cdl_major)
obs["crop_type"] = obs["cdl_class"].map({3: "rice", 61: "fallow"})

# Regional rice windows (planner-spec B1 CA0 calendar, U): flood/seed late Apr-May, harvest Sep-Oct.
# Weak labels: core season Jul 1-Aug 31 -> covered (1); Dec 1-Mar 31 -> outside season (0); else NaN.
m = obs["date"].dt.month
obs["in_season"] = float("nan")
rice = obs["cdl_class"] == 3
obs.loc[rice & m.isin([7, 8]), "in_season"] = 1.0
obs.loc[rice & m.isin([12, 1, 2, 3]), "in_season"] = 0.0
# MODIS 250 m same-DOY NDVI climatology 2000-2025 (MOD13Q1 via Planetary Computer; QA good/marginal)
import numpy as np
mo = pd.read_csv(D + "fs_modis_ca_colusa_rice.csv").drop_duplicates("start")
mo = mo[mo["pixel_reliability"].isin([0, 1])]
mo["doy"] = pd.to_datetime(mo["start"]).dt.dayofyear + 8  # composite mid-point
clim = mo.groupby(mo["doy"].clip(upper=366))["ndvi_raw"].mean() * 0.0001
clim = clim.reindex(range(1, 367)).interpolate(limit_direction="both")
clim = pd.concat([clim.iloc[-15:], clim, clim.iloc[:15]]).rolling(15, center=True).mean().iloc[15:-15]  # circular smooth
obs["modis_ndvi_clim"] = obs["date"].dt.dayofyear.map(clim)
# smap_pct: SMAP that week when AppEEARS delivers; until then NASA POWER GWETTOP same-week percentile (stand-in)
sw = pd.read_csv(D + "fs_power_soilwet_ca_colusa_rice.csv", dtype={"date": str})
sw["date"] = pd.to_datetime(sw["date"], format="%Y%m%d")
g = sw.set_index("date")["GWETTOP"].replace(-999, np.nan).resample("W-MON").mean()
pct = g.groupby(g.index.isocalendar().week.clip(upper=52).values).rank(pct=True) * 100
obs["smap_pct"] = pct.reindex(obs["date"], method="ffill").values

out = sys.argv[1] if len(sys.argv) > 1 else D + "obs_ca.csv"
obs.to_csv(out, index=False)
print(out, obs.shape, "valid>=0.5:", (obs.valid_fraction >= 0.5).sum())
