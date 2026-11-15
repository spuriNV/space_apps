# BC data gaps: California sources and their BC equivalents

This doc covers every data source the California fields use (for example `car_colusa_rice`) and what the BC example field (`bc_salmon_river_forage`, 50.6434 N, -119.3826 W) uses in its place. Some sources are a gap in BC.

- **Checked:** 15 Nov 2026.
- **Status:** as of about 07:40 UTC that day. Some NASA fetches were still running then, so "not cached yet" may already be out of date. `ls data/cache/bc_salmon_river_forage/` shows the current state.
- **Background:** the field and the reasons behind each gap are in [handoff-bc.md](handoff-bc.md) and in the `not_available` block of `backend/fields/registry.json`.

**Status words:**
- **Works**: the BC source was fetched for this field and is cached.
- **Live, not cached**: the source answered for this point, but nothing is stored yet.
- **Not run**: the source covers BC, but the pipeline has not been run for this field.
- **Gap**: no BC equivalent is used.

## NASA and satellite sources

| California source | BC equivalent used | Status | How verified |
|---|---|---|---|
| NASA POWER daily (`backend/regional`) | Same (POWER covers the globe) | **Works.** 16,752 days, 1981-01-01 to 2026-11-12 (`power.parquet`) | Cache meta `power.meta.json`, fetched 2026-11-15. See the elevation caveat below. |
| NASA POWER near-real-time (`backend/nasa`) | Same | **Works.** 316 rows for 2026 (`power_nrt.parquet`) | Cache meta, fetched 2026-11-15 |
| GPM IMERG daily, 0.1° (Final + Late) | Same (IMERG covers 60 S–60 N) | **Works.** 4,335 rows from 2015 (`imerg.parquet`) | Cache meta, fetched 2026-11-15 |
| SMAP L3 (SPL3SMP_E, 9 km) | Same (global) | Not run | Not checked for this point. Winter freeze and snow will flag many BC retrievals. |
| SMAP L4 (SPL4SMGP, 9 km) | Same (global) | Not run (started, then stopped for the move) | Not checked for this point |
| GRACE-DA (GRACEDADM_CLSM025GL_7D, 0.25°) | Same (the "GL" product is global) | **Works.** 1,231 weekly rows (`grace.parquet`) | Cache meta, fetched 2026-11-15 |
| MODIS MOD13Q1 NDVI, 250 m | Same (global) | Not run | Needs the field's Sentinel-2 cache and grid first |
| HLS v2.0 (HLSL30/HLSS30, 30 m) | Same (global) | Not run | Same as MODIS |
| Sentinel-2 L2A / Landsat C2 L2 field series (`backend/field`) | Same, via Planetary Computer | Sentinel-2 cached: 715 scenes from 1,590 items found (`s2.parquet`). Landsat not yet cached. | Cache meta `s2.meta.json`, fetched 2026-11-15. Winter snow is masked, so Dec–Feb will be mostly "unknown". |
| ECOSTRESS (LST, ET, ESI; 70 m) | Same. The ISS orbit reaches about 52° N, so 50.6° N is inside, but revisits are sparse. | Not run | Not checked for this point |
| OPERA DSWx-HLS (water on the field) | Same (built from HLS) | Not run | No `dswx.parquet` for BC, so `/water_seen` has no BC data |
| NASADEM (30 m terrain, slope) | Same. SRTM-based NASADEM covers 56 S–60 N. | Not run | Would give the field elevation, which is about 450 m (handoff estimate) |

## Crop, soil and weather station sources

| California source | BC equivalent used | Status | How verified |
|---|---|---|---|
| USDA Cropland Data Layer (CDL) | AAFC Annual Crop Inventory (ACI), 30 m, per-year BC zips | **Works.** 2009–2025 crop history in `backend/field/out/bc_salmon_river_forage/crop_history.json` | **Live 2026-11-15:** the 2025 directory lists `aci_2025_bc_v1.zip`. The AAFC spec gives BC crop-class accuracy as 88.34% (2024) and 89.02% (2025), per the handoff. See the class 122 caveat below. |
| USDA SSURGO (field-scale soil survey) | ISRIC SoilGrids v2 (250 m global model) | Script written (`backend/bc/fetch_soilgrids.py`); not cached | **Not verified:** on 2026-11-15 the REST properties endpoint (`rest.isric.org/soilgrids/v2.0/properties/query`, lon -119.3826, lat 50.6434) returned HTTP 503 twice. The first reply was non-JSON; the second, 20 s later, showed the 503 page. ISRIC allows at most 5 requests per minute. Drainage class, hydrologic group and AWC stay "unknown" in any case. |
| NOAA GHCN-Daily stations (`ncei.parquet`) | ECCC daily climate (MSC GeoMet OGC API `climate-daily`): Salmon Arm CS `116FRMN`, 350 m elevation, active; Silver Creek `1167337`, 1991 to Oct 2021, then closed | **Works** (`eccc.parquet`, same columns as `ncei.parquet`) | **Live 2026-11-15:** `api.weather.gc.ca/collections/climate-daily/items?CLIMATE_IDENTIFIER=116FRMN&limit=1` returned HTTP 200 with 13,102 records; the latest day was 2026-11-14 (SALMON ARM CS). |
| CIMIS (California stations, reference ET) | None. Reference ET comes from Hargreaves on station or POWER temperatures. | **Gap** | Registry `not_available.cimis` |
| OpenET (field-scale measured ET) | None | **Gap** | Registry `not_available.openet`. OpenET covers the western United States only. |
| DWR / Land IQ field outlines | ParcelMap BC legal parcel, at least 90% inside the ALR, clipped to stable ACI "Pasture / Forages" pixels | **Works** (`backend/field/polygons/bc_salmon_river_forage.geojson`). Labelled a parcel-and-pixel outline, not a mapped field. | **Live 2026-11-15:** BC WFS `openmaps.gov.bc.ca/geo/pub/wfs` (with `sortBy=OBJECTID`) answered for parcels (`WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW`, 2,501,898 features), ALR (`WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS`, 3,226) and reserves (`WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP`, 1,686) |

## Water, outlook, insurance, market and funding sources

| California source | BC equivalent used | Status | How verified |
|---|---|---|---|
| US Drought Monitor (county weekly) | None. AAFC's Canadian Drought Monitor exists but is not built in. | **Gap** | Registry `not_available.outlook` |
| NOAA CPC 90-day and drought outlooks | None. ECCC seasonal forecasts exist but are not built in. | **Gap** | Registry `not_available.outlook` |
| CDEC reservoirs, snow, Bulletin 120; CVP/SWP allocations | None. The Salmon River is not storage-fed like the CA projects. Water Survey of Canada gauges and the BC River Forecast Centre are possible future sources, not built. | **Gap** | Registry `not_available.sgma` and `outlook` |
| Water district, groundwater subbasin, SGMA priority, GSA/GSP (DWR layers) | BC context instead: the 16 Aug 2023 fish population protection order (M0238_2023, lower Salmon River) in `water_context`. Water licences are issued under the Water Sustainability Act. This field's licence is not looked up, because the lookup would identify the owner. | **Gap** (context only) | Registry `water_context`. The 2023 release (https://news.gov.bc.ca/releases/2023FOR0052-001305) was re-checked live 2026-11-15. |
| USDA RMA cause-of-loss (crop insurance) | None. BC Production Insurance loss data is not public at field or county level. | **Gap** | Registry `not_available.insurance` |
| USDA NASS county yields and acres | None built. Statistics Canada census data exists for the census division (5939), but it is not wired in. | **Gap** | Handoff: engine `income` text becomes "not available" for BC |
| USDA AMS hay prices | None | **Gap** | Same as NASS |
| NRCS EQIP payment schedule | BC programs, **unverified** | **Gap** | Handoff: engine `funding` text names BC programs and marks them unverified |
| ML bare-field calendar and stress models (`backend/ai`) | None; they were trained on California fields | **Gap** (not run) | Registry `not_available.ml_calendar` |

## Caveats

- **POWER is cold here.** The POWER grid cell's elevation is 1,025 m (`elevation_m: 1024.77` in `power.meta.json`), while the field is about 450 m. The cell takes in the hills around the valley, so POWER temperatures run below the valley floor.
  - For ETo and frost dates, use ECCC station Tmax/Tmin (Salmon Arm CS at 350 m) where available.
  - POWER fills gaps only, and is labelled as such.
  - The CA-tuned POWER range check (−30 °C) had to be widened to −50 °C for Shuswap winters.
- **ACI class 122 lumps forages.** "Pasture / Forages" covers alfalfa, clover, grass hay and pasture; ACI has no alfalfa class. The field's history therefore shows "a forage field", not "alfalfa".
  - The engine's `alfalfa_hay_bc` baseline is an assumption flagged as such.
  - 2009–2010 do not cover this area, and 2011–2013 and 2021 are "Agriculture (undifferentiated)" only.
- **Sparse stations.** Only one active ECCC station serves the valley. Silver Creek closed in Oct 2021. The ECCC API pads closed stations with empty days, which `fetch_eccc.py` drops.
- **SoilGrids is a 250 m model**, not a survey. Treat texture as indicative, and drainage and hydrologic group as unknown.

## What the app shows

Every California-only route is meant to answer for the BC field with a 404 that says "not available in BC", using the registry's `not_available` text. The table below shows the planned mapping. When this doc was written, the wiring in `backend/api/app/main.py` (`_real_only`) was not yet done; see the handoff, step 5.

| Route | Registry key | Reason text (from `backend/fields/registry.json`) |
|---|---|---|
| `/openet` | `openet` | "OpenET covers the western United States only; there is no field-scale measured water use for BC." |
| `/insurance` | `insurance` | "USDA RMA crop-insurance records cover the United States only; BC Production Insurance loss data is not public at field or county level." |
| `/outlook` | `outlook` | "The coming-season outlooks (NOAA CPC, US Drought Monitor, CDEC) are US products; not built for BC." |
| `/calendar_ml` | `ml_calendar` | "The machine-learning calendar and stress models were trained on California fields and were not run here." |
| `/stress` | `ml_calendar` | Same text as `/calendar_ml` |
| `/water_seen` | none yet | The registry has no reason for this route; one needs to be added. Suggested text: "OPERA DSWx water-on-field scenes were not processed for this BC field." DSWx itself does cover BC; it is a pipeline gap, not a data gap. |

The other `not_available` keys (`cimis`, `sgma`, `cdl`, `soil_survey`) have no route of their own. They belong in `location.json` `data_gaps`.
