# British Columbia field (`backend/bc`)

Builds the one field outside California, `bc_salmon_river_forage`: a forage (alfalfa-grass hay) field in the lower Salmon River valley near Salmon Arm (Columbia-Shuswap regional district). On 16 Aug 2023, fish population protection orders stopped about 398 licence holders on this river and on Bessette Creek from irrigating forage. The registry entry is `fields_other_regions[0]` in `backend/fields/registry.json` (region `bc`). `fieldreg.ids()` still returns California only; use `fieldreg.ids(region=None)` for every region.

## Steps

| Script | Writes | Notes |
|---|---|---|
| `select_field.py` | `backend/field/polygons/bc_salmon_river_forage.geojson` (+ `_training_box.json`) | ParcelMap BC parcel in the ALR, clipped to AAFC ACI Pasture / Forages pixels. Off reserve land (see `docs/bc-first-nations.md`). |
| `aci.py`, `crop_history.py` | `data/cache/<id>/aci*`, `backend/field/out/<id>/crop_history.json` | AAFC Annual Crop Inventory by year. ACI has no alfalfa class. |
| `fetch_eccc.py` | `data/cache/<id>/eccc.parquet` | ECCC daily climate for Salmon Arm CS and Silver Creek (Silver Creek closed in 2021). Same columns as `ncei.parquet`. |
| `fetch_slc.py` | `data/cache/<id>/slc.json` | AAFC Soil Landscapes of Canada v3.2 (1:1,000,000): the polygon under the field (1004019, 39.8 km2), its 5 soils with their share, drainage, AWHC class and 0-100 cm layer data, plus a share-weighted summary. Preferred soil source. |
| `fetch_soilgrids.py` | `data/cache/<id>/soilgrids.json` | ISRIC SoilGrids v2 at 5 points in the field. Fallback soil source, used only when `slc.json` is missing (the REST API returned 503 for hours in Nov 2026). |
| `fetch_reserves.py` | `data/cache/<id>/reserves_nearby.geojson` | Reserve outlines within 20 km, each with `band` and `nation` (display name from `nations.py`, the same mapping as first_nations.json) (BC WFS `WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP`, simplified to 20 m). For the map, as context only. Run in the bc venv: `cd backend/bc && uv run python fetch_reserves.py`. |
| `fetch_wsc.py` | `data/cache/<id>/wsc_daily.parquet`, `wsc.meta.json` | Water Survey of Canada gauges 08LE021 (Salmon River near Salmon Arm, lower river) and 08LE020 (at Falkland): HYDAT daily means (MSC GeoMet `hydrometric-daily-mean`, approved to 2025-12-31), provisional real-time discharge and water temperature averaged to days (wateroffice `real_time_data/csv`, about 18 months online), latest reading (`hydrometric-realtime`). No key. |
| `fetch_snow.py` | `data/cache/<id>/modis_snow.parquet`, `modis_snow.meta.json`, `salmon_watershed.geojson` | NASA MOD10A2 v061 8-day snow extent (Planetary Computer COGs, anonymous SAS) over the Salmon River watershed (BC FWA watershed group SALR), Feb-Jun 2001-2026. |
| `salmon.py` | `backend/api/out/<id>/salmon.json` | `GET /api/locations/<id>/salmon` (schema `schemas/salmon.schema.json`): flow vs the order thresholds (M311 2026: 0.625 m3/s; M238 2023: 1.27 m3/s) and BC %MAD rules, day-of-year percentiles 1991-2020, gauge water temperature vs 18/20 C (DFO, BC guidelines), run timing over the irrigation months, a spring early-warning table (rule of thumb), and each rotation's Aug-Sep irrigation draw vs a low August flow. Runs in the backend/api venv (uses the engine). No network. |
| `build_api.py` | `backend/api/out/<id>/*.json`, `backend/news/out/<id>.json` | API payloads. No network. |
| `checks/run_checks.py` | stdout | PASS/FAIL/INFO lines. Exits 1 on any FAIL. |

Other chunks write BC outputs too:
- `backend/nasa`: IMERG, SMAP and GRACE caches.
- `backend/field`: the S2/Landsat calendar and the 30 m grid.
- `backend/engine`: `out/<id>/strategies.json` and the `*_bc` crops.

## Rerun the API payloads

```
cd backend/api
uv run python ../bc/build_api.py          # rebuild backend/api/out/bc_salmon_river_forage/ from whatever is cached
uv run python ../bc/checks/run_checks.py  # BC checks
uv run python checks/check_api.py         # every API route, CA and BC
```

Both scripts run in the `backend/api` venv. They need pandas plus the API's `nasa_build.py` and `build_real.py` helpers, and the checks also need jsonschema.

Every input is optional except the registry entry, the polygon, POWER and ECCC. The builder ends by printing what it **used** and what it **skipped**. Skipped inputs are still downloading or not built: SMAP L3/L4, MODIS, ECOSTRESS, HLS, NASADEM, the S2/Landsat calendar and grid, and engine strategies. When one of them lands, rerun the same command. Nothing needs to change in the code.

## What the payloads contain

- `location.json` follows `schemas/location.schema.json`:
  - `region: "bc"` and `region_adapter: "bc"`.
  - `county_name` Columbia-Shuswap, with `state_fips` 59 and `county_fips` 39 (Statistics Canada census division 5939).
  - `stations[]` with network `ECCC`.
  - A `soil` block from AAFC SLC v3.2 when `slc.json` exists (else SoilGrids, else a placeholder). `mukey` is `slc_v3.2_<poly_id>`. Sand/silt/clay, AWC ((KP33 - KP1500) over 0-100 cm) and `om_pct` (OC × 1.724) are weighted by each soil's share of the polygon; low/high are the lowest and highest soil. `drainage_class` and `hydrologic_group` are the dominant condition (largest share). The hydrologic group is derived (NRCS NEH 630 ch. 7 Table 7-1 on SLC Ksat, water-table depth assumed from the drainage class). `components` lists the 5 soils. SLC is 1:1,000,000: which soil is in the field is not mapped.
  - With SoilGrids instead: `mukey` is `soilgrids_v2`, `om_pct` = SOC × 1.724, `texture_class` from the USDA triangle on 0-30 cm, drainage class and hydrologic group `unknown`, AWC blocked.
  - `water` has no district, SGMA basin or CDEC stations. It carries `example_limit_af_ac`: 3.0 acre-ft/acre for forage, assumed (U). The same helper (`build_real.example_limit`) gives rice 5.0 to California fields when `build_real.py` is next run.
  - `water_context` is copied from the registry: watershed, the orders (16 Aug 2023; 28 Jul 2026; the 8 Aug 2026 rescission with `kind: "rescission"`; 19 Aug 2026, 458 licences) and the licensing note. Facts and URLs are those of first_nations.json `water_timeline`.
  - `data_gaps[]` has one entry per registry `not_available` key, as `{id, what, reason, routes, filled_with}`; `filled_with` says what estimate replaces the source.
  - `events[]` holds the orders (type `water_order`) and the rescission (type `water_order_rescinded`).
  - `crop_history` comes from the ACI.
- `daily.json`:
  - POWER plus Hargreaves ETo (FAO-56 eq. 52, the same as backend/regional), from 2015 to the latest POWER day.
  - Station columns are `eccc_tmax_c`, `eccc_tmin_c` and `eccc_precip_mm`. The `ncei_*` columns are null.
  - IMERG and GRACE columns are filled where cached.
  - `cover_class` comes from the S2/Landsat calendar when it is built.
- `features_weekly.json`: as for California. `usdm_category` and `openet_et_mm_month` are null.
- `validation.json`:
  - `power_vs_eccc_{precip,tmax,tmin}`, IMERG vs ECCC stations, and IMERG vs POWER.
  - OpenET and CIMIS are blocked, with the BC reason.
- `trends_*`: `heatwave_days` and `precip_anomaly` (POWER), plus `grace_gw_pct`, `smap_anomaly` and `modis_ndvi_anomaly` when cached. `usdm_d2_weeks` and `reservoir_storage` are estimates (below).
- Estimates for the California-only routes (`estimates.py`), each in the California shape with `estimate_note`; every estimated SourcedNumber has method `assumed` and a note:

| File | Route | Estimated from |
|---|---|---|
| `openet.json` | `/openet` | The engine's FAO-56 ETc of today's rotation (`bc0_alfalfa`) per month, 2015-2025, on station weather. OpenET does not cover BC. |
| `outlook.json` | `/outlook` | ECCC 1991-2020 station climatology for the next 10 seasons ("equal chances"); a station rain-percentile drought index (D0-D4 by the USDM percentile guide) now and at the 2023 and 2026 orders; engine irrigation need under climatology. |
| `trends_usdm_d2_weeks.json` | `/trends?layer=usdm_d2_weeks` | Weeks per year with the station 90-day rain at or below the 10th percentile. |
| `trends_reservoir_storage.json` | `/trends?layer=reservoir_storage` | No reservoir: Salmon River water orders per year, with the orders as event markers. |
| `insurance.json` | `/insurance` | Peril shares from station summers 1991-2025: drought (Jun-Aug rain < 50% of normal), rain at haying (> 150%), heat (Tmax >= 38 C), frost (Tmin <= -1 C, 10 May-15 Sep). Dollar fields are null. |
| `calendar_ml.json`, `transitions.json` | `/calendar_ml`, `/transitions` | A two-class NDVI rule (0.275) on the backend/field S2/Landsat observations; no ML model was run. Transitions also list the rule and an S2 scene-class reference. |
| `stress.json` | `/stress` | z-scores of this field's NDVI, GRACE-DA soil moisture, ETo and IMERG 30-day rain (no isolation forest). |
| `models.json` | `/models` | Reports for the above, scored against this field's Sentinel-2 scene classes. |
| `water_seen.json` | `/water_seen` | Sentinel-2 SCL water and Landsat QA water shares per spring scene, plus NDWI; not OPERA DSWx. |
- `nasa_series.json`: from `nasa_build.nasa_series`.
- `zones.json`: when the 30 m grid exists.
- `backend/news/out/bc_salmon_river_forage.json`: the `bc_salmon_2023` items of `bc_opener.json`. Because this file exists, the API's family-template news fallback never serves California news for the field. The Fraser Valley (Sumas 2021) items stay on `GET /api/bc/news`.

## API behaviour for BC

These routes work as for California: location, daily, features/weekly, strategies, score, news, validation, nasa_series, nasa_now, calendar, grid, zones, and the trends `heatwave_days`, `precip_anomaly` and `grace_gw_pct`.

The California-only routes (`/openet`, `/insurance`, `/outlook`, `/calendar_ml`, `/stress`, `/transitions`, `/models`, `/water_seen`, and the trends `usdm_d2_weeks` and `reservoir_storage`) serve the estimates above with `_source: "estimate"` and `X-Data-Source: estimate` (`REGION_GAPS` / `ESTIMATE_FILE` in `backend/api/app/main.py`). If an estimate file is missing they fall back to **404** `"<kind> not available in BC: <registry not_available reason>"`.

The engine (`backend/engine/src/rotation_engine/bc.py`) also uses BC-only values: the extreme-rain threshold for erosion is the 99th percentile of daily ECCC station rain (13.5 mm; range 11.1-16.0, the 98th-99.5th percentiles) instead of California's 25 mm, and `income.components.price_range` is a California hay price stand-in (USDA AMS North Inter-Mountains alfalfa and alfalfa-grass hay, 2021-2025) in CAD/t at an assumed 1.37 CAD per USD.

`GET /api/locations/{id}/first_nations` serves `out/<id>/first_nations.json` (schema `schemas/first_nations.schema.json`). It holds the nearby reserves, the lower-river Nation (Splatsin), `field_on_reserve: false` with `nearest_km`, the statement, engagement steps, principles (OCAP®, CARE, TCPS 2 Ch. 9), public department contacts and the Salmon River water timeline. Every fact and URL comes from `docs/bc-first-nations.md`; the reserve list comes from `reserves_nearby.json`. `GET .../first_nations/reserves.geojson` serves the reserve outlines. `location.json` carries a `first_nations` summary. California fields get 404 "First Nations context is built for the BC example field only".

`GET /api/locations` lists every region and takes `?region=ca|bc`. Each item has `region`, and `facets.region` counts fields per region.
