# backend/nasa: Earthdata-keyed NASA datasets

Fetchers for the NASA datasets that need an Earthdata Login. Output goes to `data/cache/<preset_id>/<dataset>.parquet` + `.meta.json`
(url, params, fetched_at, footprint, units, native_res_m, timestep, fill_value, quality_handling). Point series use the **polygon centroid**
from `backend/field/polygons/<id>.geojson` (lon, lat order).

## Status (14 Nov 2026): BLOCKED, no `.env` yet
Every script prints `BLOCKED: no Earthdata credentials in .env` and exits 0 until repo-root `.env` has `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`.
Nothing has been fetched; the network-dependent code paths are written from the API docs and verified only up to the CMR/AppEEARS metadata
below. Expect one round of fixes on first real run (most likely: AppEEARS CSV column names, h5netcdf streaming).

## Run order
```
cd backend/nasa && uv sync
uv run python check_auth.py            # PASS/FAIL per DAAC with the fix
uv run python fetch_grace.py           # smallest, quick test; or add --limit 5 to any fetcher for a smoke test
uv run python fetch_imerg.py [--from2000]
uv run python fetch_smap_l3.py ; uv run python fetch_smap_l4.py
uv run python fetch_modis.py ; uv run python fetch_ecostress.py
uv run python fetch_dswx.py
uv run python checks/run_checks.py     # units/ranges, coverage, spec expectations; reports, never tunes
```
All fetchers accept `--preset car_colusa_rice|caf_tulare_forage` (repeatable), `--start`, `--end`, `--limit N`.

## Datasets
| Script | Cache file | Product (verified in CMR) | Route | Columns |
|---|---|---|---|---|
| fetch_imerg.py | imerg | GPM_3IMERGDF **07** (V07B), 0.1 deg, daily, CMR range 1998-01-01..2025-09-30 | earthaccess, streamed point read per granule (GES DISC) | date, precipitation, randomError (mm/day), grid_lon/lat |
| fetch_smap_l3.py | smap_l3 | SPL3SMP_E **006**, 9 km daily, 2015-03-31.. | AppEEARS point | soil_moisture, retrieval_qual_flag, surface_flag, static_water_body_fraction, vegetation_opacity, soil_moisture_error, sm_recommended, sm_valid |
| fetch_smap_l4.py | smap_l4 | SPL4SMGP **008**, 9 km | AppEEARS point | sm_surface, sm_rootzone, sm_profile, sm_rootzone_pctl, sm_rootzone_wetness, precipitation_total_surface_flux |
| fetch_modis.py | modis | MOD13Q1 **061**, 250 m, 16-day, 2000-02-18.. | AppEEARS point | NDVI, EVI, pixel_reliability, VI_Quality, composite_day_of_the_year, ndvi_good |
| fetch_ecostress.py | ecostress | ECO_L2T_LSTE / ECO_L3T_JET / ECO_L4T_ESI **002**, 70 m, 2018-07-09.. | AppEEARS point, long format | product, LST, LST_err, cloud, water, ETdaily, ESI, PET |
| fetch_grace.py | grace | GRACEDADM_CLSM025GL_7D **3.0**, 0.25 deg weekly, 2003-02-03.. | earthaccess, streamed point read | gws_inst, rtzsm_inst, sfsm_inst (percentiles, units "%") |
| fetch_dswx.py | dswx | OPERA_L3_DSWX-HLS_V1 **1.0**, 30 m | earthaccess download of `B01_WTR.tif`, polygon-masked | frac_open_water, frac_partial_water, frac_water, frac_cloud_snow, frac_clear, per scene |

Quality handling is written into each meta.json. Highlights: SMAP L3 keeps the raw value and flag and adds `sm_valid` (bit 0 of
`retrieval_qual_flag` == 0, recommended quality); gaps over flooded rice / the 2023 Tulare Lake are kept, never interpolated. MODIS `ndvi_good`
keeps pixel_reliability 0/1. ECOSTRESS keeps cloud/water masks, LST outside 150-400 K -> NaN.

## Corrections to the spec (from CMR and AppEEARS, no auth)
1. **IMERG, GRACE-DA and OPERA are NOT in AppEEARS** (product list has 193 products; none of these). The spec's SMAP/MODIS/ECOSTRESS-via-AppEEARS is right.
   IMERG/GRACE go through earthaccess (GES DISC); OPERA through earthaccess (PO.DAAC).
2. IMERG: variable is `precipitation` (mm/day, fill -9999.9) in V07; also `MWprecipitation`, `randomError`, `probabilityLiquidPrecipitation`.
   In V07 daily files dims are (time, lon, lat). CMR coverage ends **2025-09-30** (the spec's 2025-12-31 end will be short by a quarter). The old Data Rods URL in B2.2 was not tested (needs login; the `GPM:GPM_3IMERGDF_07:precipitation` variable string is unverified); we use earthaccess instead.
3. SMAP L3 layer names are confirmed: `Soil_Moisture_Retrieval_Data_AM_soil_moisture` (valid 0.02-0.5, fill -9999) and `..._AM_retrieval_qual_flag` (fill 65534). Only 006 exists in CMR/AppEEARS for SPL3SMP_E.
4. SMAP L4 `SPL4SMGP.008`: `sm_rootzone`, `sm_surface` confirmed (m3/m3, fill -9999, valid 0-0.9), plus `sm_rootzone_pctl` (percent). **AppEEARS exposes no quality-flag layer for L4** (it is a gap-free model product), so "quality flags" applies to L3 only.
5. MOD13Q1.061 layers are prefixed `_250m_16_days_` (NDVI, EVI, pixel_reliability, VI_Quality, composite_day_of_the_year). AppEEARS applies the 0.0001 scale (valid -0.2..1.0, fill -3000).
6. ECOSTRESS: **v002 and v003 both exist in CMR**; AppEEARS only lists 002 (use 002). LST layer is `LST` (K) from ECO_L2T_LSTE; the ET layer in ECO_L3T_JET.002 is `ETdaily` and AppEEARS lists its unit as **W/m2** (not mm/day; x0.0353 for mm/day), with ensemble members PTJPLSMinst, STICinst, MOD16inst, BESSinst. ECO_L4T_ESI.002 gives `ESI` and `PET`. A mm/day ET exists as `ECO_L3T_ET_ALEXI.002` (`ETdaily`). Rule: ECOSTRESS can only be queried via AppEEARS for 2018-07 onward and only for scenes that exist.
7. GRACE-DA 3.0 variables are `gws_inst`, `rtzsm_inst`, `sfsm_inst` (units "%", fill -999) i.e. percentiles; weekly granules, latest in CMR is 2026-08-31 (so the 2003-2025 span is covered).
8. OPERA: `OPERA_L3_DSWX-HLS_V1` v1.0 (2016-01-01..); a Sentinel-1 variant `OPERA_L3_DSWX-S1_V1` starts 2023-12-01 (not used). CMR already shows 36 HLS scenes intersecting the Colusa field for Dec 2022-Mar 2023 and 183 tile hits for the Kings field Mar-Jun 2023. WTR classes: 0 not water, 1 open, 2 partial, 252 snow/ice, 253 cloud, 254 ocean, 255 fill.

## Earthdata approvals needed
Profile at https://urs.earthdata.nasa.gov -> Applications -> Authorized Apps -> Approve More Applications. Hosts seen in CMR and the app that must be approved for each:
| Dataset | Download host | Approve |
|---|---|---|
| IMERG, GRACE-DA | data.gesdisc.earthdata.nasa.gov (GES DISC) | NASA GESDISC DATA ARCHIVE |
| SMAP L3/L4 | NSIDC cloud (CMR provider NSIDC_CPRD, host data.nsidc.earthdatacloud.nasa.gov) | NSIDC DAAC app(s) (names vary: "NSIDC_DATAPOOL_OPS", "NSIDC DAAC Data Pool"; app names are unverified, approve the closest match) |
| MODIS, ECOSTRESS | LP DAAC cloud (data.lpdaac.earthdatacloud.nasa.gov) | LP DAAC Data Pool |
| SMAP, MODIS, ECOSTRESS via AppEEARS | appeears.earthdatacloud.nasa.gov (AppEEARS pulls from the DAACs on your behalf) | AppEEARS (log in once at the site to accept terms) |
| OPERA DSWx | archive.podaac.earthdata.nasa.gov (PO.DAAC) | PO.DAAC Data Website / "Earthdata Cloud" if offered |
`check_auth.py` tests each and prints the HTTP error plus this fix.

## Estimated download size and time (estimates, not measured)
| Script | Volume | Time |
|---|---|---|
| fetch_imerg (2015-2025, ~3,900 files, ~30 MB each but only a pixel is range-read) | tens of MB transferred | 15-40 min with 8 threads; from 2000: ~9,500 files, 1-1.5 h |
| fetch_grace (~1,200 weekly files) | small | 5-15 min |
| fetch_smap_l3 / l4 | KB per task, point CSV | AppEEARS queue 5-60 min each (3 and 6 chunked tasks per preset) |
| fetch_modis | KB | 5-20 min |
| fetch_ecostress | KB | 10-60 min (3 products) |
| fetch_dswx | ~3-8 MB per WTR tile, deleted after masking; a few hundred scenes | 15-45 min, ~1-2 GB transferred in total |

## Known limits
- MODIS and ECOSTRESS series are one pixel at the centroid, not a polygon mean (an AppEEARS area request would need rasters; deferred).
- IMERG/GRACE streaming reads over HTTPS range requests; if GES DISC rate-limits, lower `workers` in `granules.py` or switch to OPeNDAP.
- DSWx windows (in `fetch_dswx.py`): Colusa Nov 1-Apr 15 for winters starting 2022, 2023, 2024; Kings Mar 1-Jun 30 2023.
- `checks/run_checks.py` percentile rule for SMAP L3 is our own same-month rank 2015+; the SMAP L4 and GRACE checks use the product percentiles.
