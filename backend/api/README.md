# Field Shift API (`backend/api`)

FastAPI app serving the spec B3 routes. No database. Each route returns a real output file if one exists, otherwise a fixture from `fixtures/`.

**Real data:** `uv run python build_real.py` (no network, offline) converts the other chunks' outputs into the API's lookup files in `backend/api/out/<id>/` (committed): `location, daily, features_weekly, zones, validation, trends_<layer>`. It reads `data/cache/<id>/*` (POWER, NCEI, USDM, CDEC, soil, and the NASA caches from `backend/nasa` and `backend/nasa_open`: IMERG, SMAP L3/L4, GRACE-DA, MODIS, ECOSTRESS, OPERA DSWx, HLS, POWER near-real-time), `backend/regional/out`, `backend/field/{polygons,out}`, `backend/nasa_open/out` (NASADEM terrain) and the engine's observed-cover consensus. The NASA part lives in `nasa_build.py`; it also writes `out/<id>/nasa_series.json` and `out/bc_signal.json`. A NASA dataset that is not cached yet stays null / `pending`; nothing is filled in. Re-run it after any of those change. The engine strategies, crops, news, calendar and grid are served straight from their chunks' outputs.

## Run

```
cd backend/api
uv run uvicorn app.main:app --port 8000 --reload     # http://localhost:8000/docs
uv run python build_real.py                           # rebuild backend/api/out/<id>/*.json from chunk outputs
uv run python checks/check_api.py                     # PASS/FAIL per route + real/fixture table, exit 1 on failure
python3 ../../fixtures/build_fixtures.py              # regenerate fixtures (stdlib only)
```
CORS is open for `http://localhost:*` and `127.0.0.1:*`. Override the repo root with `FIELDSHIFT_ROOT`.

## fixture vs real

Every response has header `X-Data-Source: fixture|real` and a top-level `"_source"` field with the same value. Fixture files also carry `"_fixture": true` (kept in responses served from fixtures, dropped for real). Collections are always objects (`{"items": [...]}` or `{"rows": [...]}`); a real file that is a bare JSON array is wrapped as `{"items": array}`. Real files are served as found and are **not** validated by the API (validate with `schemas/`).

Fixture numbers are placeholders (`method: assumed`, `verified: false`, source `urn:fieldshift:fixture-placeholder`) except values the spec marks V with a URL: rice Kc (FAO-56 Table 12), rice stage lengths, the 2022 rice-acreage event (NASA URL), the Farm Progress news item, the SSURGO endpoint. Events the spec calls V but gives no URL for (2023 Tulare floods, 2024 SGMA probation) have `url: null, verified: false`.

## Routes

Paths are relative to the repo root; first existing file wins. `{id}` is any field in `backend/fields/registry.json` of any region (14 California fields plus `bc_salmon_river_forage`; else 404). The BC field's payloads are built by `backend/bc/build_api.py`. Its California-only routes (`openet`, `insurance`, `outlook`, `calendar_ml`, `stress`, `transitions`, `models`, `water_seen`, and the trends `usdm_d2_weeks` and `reservoir_storage`) return estimates in the California shape with `_source: "estimate"` / `X-Data-Source: estimate`; only when an estimate file is missing do they return 404 `"<kind> not available in BC: <registry not_available reason>"` (see `backend/bc/README.md`). Fixtures live in `fixtures/{id}/<name>.json` (or `fixtures/<name>.json` for global routes) and exist only for the original two; a registry field without a built output gets 404, never another field's fixture. `/news` for a registry field falls back to its family template's news (same valley).

| Route | Fixture | Real lookup |
|---|---|---|
| `GET /api/locations?family=&county=&region=` | `fixtures/locations.json` (static copy) | one location payload per registry field, every region (originals first). `family=rice|forage`, `county=` name or FIPS (`Tulare`, `06107`, `107`), `region=ca|bc`. Each item has `region`. Response adds `count`, `filters` and `facets` (field counts by family, county and region over the whole registry) |
| `GET /api/locations/{id}` | `location.json` | `backend/api/out/{id}/location.json`, `data/cache/{id}/location.json`, `backend/field/out/{id}/location.json`, `backend/engine/out/{id}/location.json` |
| `GET .../daily?from&to` | `daily.json` | `backend/api/out/{id}/daily.json`, `data/cache/{id}/daily.json`, `backend/regional/out/{id}/daily.json` |
| `GET .../features/weekly` | `features_weekly.json` | `backend/api/out/{id}/features_weekly.json`, `data/cache/{id}/features_weekly.json`, `backend/field/out/{id}/features_weekly.json` |
| `GET .../strategies` | `strategies.json` | `backend/engine/out/{id}/strategies.json`, `data/cache/{id}/strategies.json` |
| `POST .../score` | re-weights the strategies | same source as strategies; `_source` follows it |
| `GET .../models` | `models.json` | `data/cache/{id}/models.json`, `backend/ai/out/{id}/models.json`, `backend/field/out/{id}/models.json` |
| `GET .../zones` | `zones.json` | `backend/api/out/{id}/zones.json`, `data/cache/{id}/zones.json`, `backend/field/out/{id}/zones.json` |
| `GET .../trends?layer&year` | `trends_{layer}.json` | `backend/api/out/{id}/trends_{layer}.json`, `backend/regional/out/{id}/trends_{layer}.json`, `data/cache/{id}/trends_{layer}.json` |
| `GET .../news?from&to` | `news.json` | `backend/news/out/{id}.json`, `data/cache/{id}/news.json` |
| `GET .../validation` | `validation.json` | `backend/api/out/{id}/validation.json`, `backend/regional/out/{id}/validation.json`, `backend/field/out/{id}/validation.json`, `data/cache/{id}/validation.json` |
| `GET /api/bc/news` | `bc_news.json` | `backend/news/out/bc_opener.json`, `backend/news/out/bc_news.json`, `data/cache/bc/news.json` |
| `GET /api/bc/signal` | `bc_signal.json` | `backend/api/out/bc_signal.json` (from `data/cache/bc/signal_raw.parquet`), `backend/regional/out/bc_signal.json`, `data/cache/bc/signal.json` |
| `GET /api/glossary` | `glossary.json` | `backend/api/glossary.json` (17 plain-language entries, <= 60 words, one source URL each), `backend/engine/out/glossary.json`, `data/cache/glossary.json` |
| `GET /api/crops/{cid}` | `crops/{cid}.json` | `backend/engine/out/crops/{cid}.json`, or the entry with that `id` in `backend/engine/crops.json` (`{"crops": [...]}`) |
| `GET .../calendar?year=&source=` | none (404 if not built) | `source=s2_landsat` (default): `backend/field/out/{id}/calendar.json`; `source=hls`: `backend/nasa/out/{id}/calendar_hls.json` (same detector on NASA HLS only); both + `crop_history.json` |
| `GET .../openet?from&to` | none | `data/cache/{id}/openet.parquet`: monthly measured ET (mm and inches) plus annual totals |
| `GET .../nasa_now?date=` | none | `backend/api/out/{id}/nasa_series.json`: NASA readings for the 10-day step containing `date` (default today) |
| `GET .../nasa_series?from&to` | none | same file, one row per 10-day step (1st/11th/21st) |
| `GET .../water_seen?from&to` | none | `backend/api/out/{id}/water_seen.json` (built from `data/cache/{id}/dswx.parquet`); `from/to` filter `scenes` |
| `GET .../insurance` | none | `backend/ground/out/{id}/rma_profile.json` (USDA RMA cause of loss), served as is |
| `GET .../stress` | none | `backend/ai/out/{id}/stress_weekly.json` + API-computed `summary.by_year`, + `stress_summary`/`stress_eval(uation)` if backend/ai writes them |
| `GET .../grid?layer=` | none (404 if backend/field has not run) | `backend/field/out/{id}/grid.geojson` |
| `GET .../transitions` | none (404 if not built) | `backend/ai/out/{id}/transitions.json`: green-up, harvest and alfalfa cutting dates per detector method |
| `GET .../first_nations` | none | BC only: `backend/api/out/{id}/first_nations.json` (backend/bc/build_api.py). California fields: 404 "First Nations context is built for the BC example field only" |
| `GET .../first_nations/reserves.geojson` | none | BC only: `data/cache/{id}/reserves_nearby.geojson` (backend/bc/fetch_reserves.py), reserve outlines as map context |
| `GET /api/health` | | not in spec; shows root and presets |

`trends` layers: `smap_anomaly|heatwave_days|grace_gw_pct|precip_anomaly|modis_ndvi_anomaly|usdm_d2_weeks|reservoir_storage`. `from`/`to` filter `rows`/`items` by their `date` string.

`POST .../score` body: `{weights, constraints, market_preference, allocation, replay_year, scenario:{dT_c, dP_pct}}`. Scored by the rotation engine (`rotation_engine.score`, path dependency `../engine`); all request fields apply. **Fallback placeholder** (engine import/run fails): composite = sum(w_i * s_i) / sum(w_i) over stored per-criterion scores (value, low, high), plus a tie flag (interval overlap > 50%). Weights in [0,4]; unknown keys give 422. Defaults: 1 for water_use, forage_value, n_fixation, erosion, organic_matter, market; 0 for the rest. The scenario is echoed into `exposure.scenario`; in fallback mode constraints, allocation, replay_year and the scenario do not change numbers.

## Real data per route (frontend: read this)

`X-Data-Source` / `_source` says `real` or `fixture` per response. After `build_real.py`:

| Route | Source | Notes |
|---|---|---|
| `GET /api/locations`, `/api/locations/{id}` | real | registry fields add `family`, `farmer_name`, `acres`, `county_name`, `template`, `why_chosen`; **`water`** is now looked up (backend/fields/water_sources.py): `district` (DWR i03 Water Districts, null if none at the centroid), `other_agencies`, `sgma_subbasin` + `_number`, `sgma_priority` (2019), `critically_overdrafted`, `gsa`, `sgma_status.text` (subbasin, priority, State Water Board status, DWR GSP assessment) with source URL, `cdec_stations` (registry reservoirs) and `lookup` (every layer's raw answer, URL and date); `water.source` stays the spec statement (U) for the original two and null elsewhere. As before, plus: `dwr_unique_id` (DWR/Land IQ field ID from backend/field/polygons); `soil.ec_ds_per_m` and `soil.texture_detail` (SSURGO, data/cache/<id>/soil.json); **`nasa_datasets`** (list: `id, name, tells_you` (plain words), `resolution, date_range, rows, status` live/pending/blocked, `used_in, source_url, note`) for the "NASA data behind this field" panel; `terrain.*` now **NASADEM** (smoothed slope, elevation, low-spot fraction) from backend/nasa_open; `datasets.*` statuses updated (`real` for IMERG, GRACE, HLS, DEM, OpenET once cached) |
| `GET .../daily?from&to` | real | **2015-01-01 to the latest POWER near-real-time day (2026-11-11)**. New columns: `imerg_precip_mm` + `imerg_run` (GPM IMERG Final, Late after 2025-09-30; to 2026-11-13), `smap_sm_pct` (SMAP L4 root-zone percentile), `smap_rootzone_m3m3`, `smap_l3_sm_m3m3`, `grace_gw_pct` (weekly), `power_run` (`archive`/`nrt`), `cover_source` (`s2_landsat` or `hls`). NCEI station columns stay null after the station cache ends |
| `GET .../features/weekly` | real | weeks through 2026; `imerg_7d_mm`, `smap_sm`, `smap_sm_pct`, `grace_*_pct`, `modis_ndvi_anomaly`, `esi` filled where the dataset is cached |
| `GET .../trends?layer=&year=` | real for all 7 layers once SMAP/MODIS are cached | `grace_gw_pct` (annual mean GRACE-DA groundwater percentile, 2003-2026), `smap_anomaly` (SMAP L4 root-zone standardized anomaly, sd), `modis_ndvi_anomaly` (MOD13Q1 NDVI minus 2000-2025 same-period mean). Still one cell (`row 0, col 0`) |
| `GET .../validation` | real | adds `station_vs_imerg` (IMERG vs NOAA station monthly rain, with `by_water_year` IMERG / POWER / stations totals) and `imerg_vs_power_precip`; `openet_vs_etc` now computed (copied from the engine baseline). `cimis_vs_power` still blocked |
| `GET .../nasa_now?date=` | real (new) | `readings.{smap_rootzone_pct, smap_rootzone_m3m3, smap_surface_m3m3, smap_l3_sm_m3m3, grace_gw_pct, grace_rootzone_pct, imerg_rain_mm, imerg_wy_to_date_mm, imerg_wy_to_date_normal_mm, modis_ndvi, modis_ndvi_anomaly, ecostress_esi, ecostress_et_mm_day, dswx_water_frac, hls_ndvi}` each `{value, step, obs_date, stale_steps}`; `plain_language` lines for SMAP and GRACE; `latest_by_dataset`; values older than ~6 months are omitted |
| `GET .../nasa_series?from&to` | real (new) | the same fields per 10-day step from 2015, for the 3D soil-moisture and groundwater slabs |
| `GET .../openet` | real (new) | 120 monthly rows 2016-2025 (OpenET Ensemble v2.1, field polygon), `annual` totals |
| `GET .../calendar?source=hls` | real (new) | NASA-native calendar: backend/field's rule detector on HLS v2.0 (Planetary Computer 2017-08..2025 + LP DAAC 2016-2019 and 2026) |
| `POST .../score` | real | items now carry `water.etc_vs_openet_pct` and `water.openet_et_mm_season` (copied from GET /strategies; default weather, not recomputed per scenario) |
| `GET .../strategies`, `zones`, `calendar`, `grid`, `news`, `crops` | real | unchanged |
| `GET /api/bc/signal` | real once `fetch_bc_signal.py` finishes | SMAP L4 root-zone percentile, GRACE-DA groundwater percentile and POWER Tmax at 50.62 N -119.33 W, Mar-Oct 2023, weekly; markers from the spec with `lead_days` (rule ours, U) |
| `GET .../water_seen` | real (new) | OPERA DSWx per scene: `water_frac` (open + partial), `open_water_frac`, `partial_water_frac`, `cloud_snow_frac`, `clear` (>= 80% clear); `seasons` (Colusa: winters Nov-Apr; Kings: spring 2023) with `clear_scenes`, `max_water_frac`, `scenes_over_half_water`, first/last wet date; `summary` in plain words |
| `GET .../insurance` | real (new) | RMA 2010-2024 county profile by peril group; keeps `share_peril_unattributed` (forage/alfalfa indemnity RMA does not tie to a peril) |
| `GET .../stress` | real (new) | weekly in-season stress flags (z-score, isolation forest) per crop year, with `summary.by_year` counts |
| `GET /api/glossary` | real (new) | `backend/api/glossary.json`: ETo, ETc/Kc, ET, soil-moisture percentile, NDVI, bare/partial/covered, frost, heat days, water balance, acre-foot vs mm, GRACE groundwater, SGMA, pixel size, OpenET, rule vs ML detector, IMERG, DSWx |
| `GET .../models` | real | backend/ai |

Known data caveats the UI should not hide: POWER overstates rain vs the NCEI stations (+54% CAR, +68% CAF in monthly totals) and runs warm in summer (JJA Tmax about +3.4 C CAR, +3.8 C CAF), so `heatwave_days`, `severe_heat_40c` and the engine's heat/dry-day counts are high-biased. See `backend/regional/README.md`.

## Response clean-up (`app/sanitize.py`, applied in `send()` to real and estimate responses)

- **Text:** internal markers are stripped from user-facing strings (names, notes, labels, `brief.local_review[].item`, source titles, timing notes): `(U)`, `(V)`, `U:`/`V:` inside brackets, `spec B11`, `(spec B4.4)`, `planner-spec B4`, bare section refs such as `B4.10`, plus a few repo-only phrases (table `PHRASES`). Source files keep their markers. `method`, `verified`, ids, units, dates and URLs are never rewritten, so the data status still comes from `method`/`verified`. Fixtures are served unchanged.
- **Links:** a `url`/`source_url` that is a repo path (`backend/...`, `data/cache/...`, `planner-spec.md#...`), an internal `urn:fieldshift:*` id or a GitHub blob path becomes the dataset's public page when `PUBLIC_URLS` has one (e.g. `data/cache/<id>/cdec.parquet` -> https://cdec.water.ca.gov/, `.../ncei.parquet` -> NOAA GHCN-Daily, `power` -> NASA POWER). Otherwise the link is kept and its object gets **`internal: true`**: show the title, do not link it. A bare domain (`colusagroundwater.org`) gets `https://`.

## Fields added for the apps

- `location.water.example_limit_af_ac`: SourcedNumber, example seasonal water limit by family (rice 5.0, forage 3.0 acre-ft/acre, `method: assumed`, source `internal: true`). A starting value for the allocation control, not the field's allocation.
- `strategies[].short_name` (GET `/strategies` and POST `/score`): short farmer-facing label from `backend/engine/build_data.py` (CA: "Rice + winter flood (current)", "Rice + winter cover", "Dry-year safflower", "Rice–wheat", "Alfalfa (current)", "Grain silage + corn", "Grain silage + sorghum-sudan", "Alfalfa with break year").
- `Source.internal` (see above).
- `/transitions` is served for every CA field with `backend/ai/out/<id>/transitions.json` (currently car_colusa_rice, caf_tulare_forage, car_glenn_rice, car_grimes_rice, car_zamora_rice, caf_tipton_forage); other CA fields get 404 until backend/ai builds theirs; BC gets the estimate.

## Schemas (`schemas/`)

`sourced_number, location, crop, rotation_strategy, model_report, news_item, feature_row` (`*.schema.json`) per spec B3 / B2.14, plus `responses.schema.json` with one `$defs` envelope per route. Draft 2020-12, `$id` base `https://fieldshift.local/schemas/`.

## Mismatches with other chunks (resolved by `build_real.py`)

- `backend/regional/out/{id}/` has `eto_monthly.json`, `risk_days_by_year.json`, `daily_derived.parquet`, none a B3 payload; the builder turns them (plus POWER/NCEI/USDM/CDEC caches) into `backend/api/out/{id}/`. The API still has no parquet reader, only JSON.
- `backend/news/out/{id}.json` matches (bare array, wrapped). BC items are in `bc_opener.json`.
- Schema changes made for real data: `trends.layer` gained `usdm_d2_weeks`, `reservoir_storage`; `trends.grid` and `location.regional_cell.grid` are free strings (were const `EASE2_G9km`); `validation.checks[].id` gained `power_vs_ncei_{precip,tmax,tmin,heat40}` and `imerg_vs_power_precip`.
- `models.json` comes from backend/ai; `glossary.json` is `backend/api/glossary.json` (committed, copied into the image by `COPY backend/api/`). The fixtures remain only as the fallback when those files are missing.

## Open questions

- Default weights: spec says six brief priorities plus pest_break, infiltration, income (default 0); I took the six as water_use, forage_value, n_fixation, erosion, organic_matter, market and also defaulted n_scavenging to 0.
- Who fills `Location.datasets` entries (shape is free: `{status, meta_path, ...}`)?
- Fixture polygons are placeholder squares around the preset centres, not CDL-checked fields.

## Analyse any location (`app/anyloc/`)

Tap anywhere: `GET /api/analyze?lat=&lon=` (or `POST /api/analyze {lat, lon}`) builds a location payload for that spot live, in the same shape as `/api/locations/{id}` (schema-valid), with `_source: "live"` / `X-Data-Source: live`. The id is `pt_<n|s><lat x 1e4>_<e|w><lon x 1e4>` (4 decimals, e.g. `pt_n391894_w1220276`). Code: `app/anyloc/` (`fetch.py` upstream calls, `build.py` payload, `engine_bridge.py` engine run, `__init__.py` routes, cache, guards); `main.py` only includes the router (before the preset routes; its routes match `pt_*` ids only).

Tier 1 (computed on the tap, 2-5 s cold, ~10 ms cached): NASA POWER daily (per 0.5 x 0.625 deg cell, cached 24 h), DWR/Land IQ 2023 field outline containing the point (else a 200 m square), county (FCC census API), SSURGO via SDA over the footprint, CDL 2008-2025 at up to 10 points in the field (CroplandCROS `getSamples`), family from CDL (rice: rice in >= 3 of the last 10 years; forage: alfalfa in >= 2 or forage classes in >= 5; else `other`), DWR water layers (California only: district, B118 subbasin, SGMA priority, critically overdrafted, GSA, GSP, adjudicated, State Water Board list), and the engine (`score()` with the family's rotation set: rice -> CAR0-3, forage/other -> CAF0-3; POWER only, no NOAA stations, family slope placeholder). Tier 2 (IMERG, SMAP, GRACE, S2/Landsat/HLS, NASADEM, calendar, zones, grid, insurance, outlook, news, ...) is `not_computed` for points; OpenET is never queried (`unavailable`).

Extra keys on the payload: `sections.<name> = {status, reason?, ...}` with status `ready | not_computed | unavailable | error` (tier 1: `boundary, county, weather, daily, crop_history, family, soil, water, strategies`; tier 2: `imerg, smap, grace, satellite_cover, terrain, openet, calendar, zones, grid, insurance, outlook, stress, news, models, transitions, water_seen, nasa_series`), `analysis = {id, point, computed_at, expires_at, cache: miss|hit|hit_shared, timings_ms, matches_preset, section_statuses}`, `region` (`ca` or `other`), `region_adapter` (`ca` or `other`), `family` (`rice|forage|other`), `template`, `crop_history_purity`, `dwr_2023`. `matches_preset` is the registry id when the tap falls inside a preset field's outline (show the preset instead).

| Route (pt_* ids) | Answer |
|---|---|
| `GET /api/analyze?lat&lon[&refresh=1]`, `POST /api/analyze` | payload above; 422 for lat/lon out of range; 429 + `Retry-After` when busy or rate-limited; 504 if the whole analysis exceeds 45 s |
| `GET /api/analyze/{pid}/status` | `{id, point, in_flight, cached, computed_at?, expires_at?, sections?, timings_ms?}`; never computes |
| `GET /api/locations/{pid}` | same as `/api/analyze` for the id's point (computes on a miss) |
| `GET /api/locations/{pid}/daily?from&to` | `Daily` envelope from 2015: POWER tmax/tmin/precip, Hargreaves ETo, heat flags; the other preset columns are null |
| `GET /api/locations/{pid}/strategies` | `Strategies` envelope (engine, family rotation set, default weights) |
| `POST /api/locations/{pid}/score` | `Score` envelope, same body as the preset route |
| `GET /api/locations/{pid}/<other>` | 404 `"<route> is not computed for tapped points ..."` |

Guards (env vars, defaults sized for Render's 512 MB free instance): `ANYLOC_MAX_CONCURRENT=2` engine runs at once (cold analyses and re-scores), `ANYLOC_PER_IP_MIN=6` and `ANYLOC_PER_IP_HOUR=40` new spots per client IP, `ANYLOC_GLOBAL_HOUR=400` new spots per hour for the instance, `ANYLOC_READS_PER_MIN=120` cached reads per IP; every upstream call has its own timeout (4-5 s connect, 6-25 s read) and a size cap. Cache: `ANYLOC_CACHE_DIR` (default `data/cache/_points/`, git- and docker-ignored, gzip JSON + one parquet per POWER cell), `ANYLOC_TTL_H=168` (15 min when a tier-1 section errored), `ANYLOC_MAX_POINTS=1500` points kept. On Render the disk resets on deploy/restart; nothing depends on it. Measured: process peak RSS 137 MB idle, 191 MB after a cold analysis, 213 MB after 7.

## My fields (`app/myfields/`)

Users draw a rectangle or polygon, name it, and get the tap-anywhere analysis over the whole polygon. Nothing has to persist server-side (Render's disk is wiped on deploy): the id **is** the field. `my_<base64url(zlib(JSON))>` carries the name and the outline (corners in 1e-5 degree units, delta-coded; if the id would pass 1,800 characters the outline is simplified with Douglas-Peucker, 5 m doubling, and `id_note` says so). Any server decodes an id and recomputes, so share links survive deploys. Rename or redraw = a new id; "delete" is the client forgetting the id. `MYFIELDS_DIR` (default `data/user_fields/`, git- and docker-ignored) is an optional cache only; `MYFIELDS_TTL_H=168`, `MYFIELDS_MAX_CACHED=5000`.

| Route | Answer |
|---|---|
| `POST /api/my-fields {name, geometry}` | location payload (schema-valid) + `field_id`, `_source: "user"`, `sections`, `analysis`, `user_field`; 422 for a bad outline (not a single Polygon, holes, over 200 corners, self-crossing, under 0.5 ha or over 2,000 ha, empty name); 429 + `Retry-After`; 504 past 50 s |
| `GET /api/my-fields/{id}` | same payload, from cache or recomputed; 400 for a bad/corrupt id |
| `GET /api/my-fields?ids=a,b,c` | `{items: [{id, name, acres, area_ha, centroid, bbox, geometry, computed, family?, county_name?, last_crop?}], invalid: [{id, reason}]}`; decoded from the ids, no upstream calls (max 100) |
| `GET /api/locations/{my_id}`, `/strategies`, `/daily`, `POST /score` | same as the tapped-point routes; other sub-routes 404 "not computed for user-drawn fields" |

Analysis: acres from the spherical (authalic radius) area of the polygon; CDL majority class per year over a grid of up to 25 sample points inside it (`crop_history`, `crop_history_purity` = share of points in that class, `user_field.crop_mix` top 3 per year); SSURGO via SDA polygon intersection, map units weighted by area inside it (`soil.map_units[].area_share`); county, SGMA subbasin, GSA, water district and POWER at the interior point nearest the centroid, with `user_field.spans = {counties, districts, gsas, subbasins}` listing everything the polygon touches (counties from the centroid plus up to 4 extreme sample points); `user_field.dwr_fields` = DWR/Land IQ 2023 fields intersecting the polygon (id, crop, class, acres; up to 100); engine strategies by family (rice -> CAR0-3, else CAF0-3). Non-California or non-US outlines get the section statuses anyloc uses (`unavailable`); there is no BC tier 1 in anyloc yet, so BC polygons get the same `unavailable` sections.

Guards (env): `MYFIELDS_MAX_CONCURRENT=2`, `MYFIELDS_PER_IP_MIN=4`, `MYFIELDS_PER_IP_HOUR=30`, `MYFIELDS_GLOBAL_HOUR=300`, `MYFIELDS_READS_PER_MIN=120`. Cache hits only count against the read limit. `schemas/` accept `my_*` ids and `_source: "user"`.

## Deploy (Render)

One Docker service serves the API and the built frontend from the same origin (`/api/...` plus the app at `/`). The root `Dockerfile` builds `frontend/app` (`VITE_API_BASE=/api`), installs `backend/api` with the engine, copies the committed outputs and `data/cache`, and runs uvicorn on `$PORT` with `FRONTEND_DIST` set (the API mounts the built app, SPA fallback for non-`/api` paths). The image is about 500 MB. No keys are needed: the app serves the committed cache.

Local: `docker build -t fieldshift . && docker run -p 8000:8000 fieldshift` then open http://localhost:8000. Without Docker: `(cd frontend/app && npm ci && npm run build)` then `cd backend/api && FRONTEND_DIST=../../frontend/app/dist uv run uvicorn app.main:app --port 8000`.

Render setup (new account): sign up at render.com, connect GitHub (or skip it: New -> Web Service -> "Public Git Repository" and paste https://github.com/spuriNV/space_apps), choose Language/Runtime = Docker, branch `main`, plan Free, health check path `/api/health`, Create. Alternatively New -> Blueprint and pick the repo; `render.yaml` sets all of this. Optional env vars (EARTHDATA_USERNAME, EARTHDATA_PASSWORD, OPENET_API_KEY, CIMIS_APP_KEY, NASS_API_KEY, AMS_API_KEY) are set in the dashboard under Environment; the app does not need them. The Free plan sleeps after idle (first request is slow); Starter stays awake. Redeploy: push to `main` (auto-deploy) or Manual Deploy -> Deploy latest commit in the dashboard.
