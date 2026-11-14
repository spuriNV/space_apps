# Field Shift API (`backend/api`)

FastAPI app serving the spec B3 routes. No database. Each route returns a real output file if one exists, otherwise a fixture from `fixtures/`.

**Real data:** `uv run python build_real.py` (no network, offline) converts the other chunks' outputs into the API's lookup files in `backend/api/out/<id>/` (committed): `location, daily, features_weekly, zones, validation, trends_<layer>`. It reads `data/cache/<id>/*` (POWER, NCEI, USDM, CDEC, soil), `backend/regional/out`, `backend/field/{polygons,out}` and the engine's observed-cover consensus. Re-run it after any of those change. The engine strategies, crops, news, calendar and grid are served straight from their chunks' outputs.

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

Paths are relative to the repo root; first existing file wins. `{id}` is `car_colusa_rice` or `caf_tulare_forage` (else 404). Fixtures live in `fixtures/{id}/<name>.json` (or `fixtures/<name>.json` for global routes).

| Route | Fixture | Real lookup |
|---|---|---|
| `GET /api/locations` | `fixtures/locations.json` (static copy; API assembles from per-preset locations) | assembled from per-preset location; `real` only if both are real |
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
| `GET /api/bc/signal` | `bc_signal.json` | `backend/regional/out/bc_signal.json`, `data/cache/bc/signal.json` |
| `GET /api/glossary` | `glossary.json` | `backend/engine/out/glossary.json`, `data/cache/glossary.json` |
| `GET /api/crops/{cid}` | `crops/{cid}.json` | `backend/engine/out/crops/{cid}.json`, or the entry with that `id` in `backend/engine/crops.json` (`{"crops": [...]}`) |
| `GET .../calendar?year=` | none (404 if backend/field has not run) | `backend/field/out/{id}/calendar.json` + `crop_history.json` |
| `GET .../grid?layer=` | none (404 if backend/field has not run) | `backend/field/out/{id}/grid.geojson` |
| `GET /api/health` | | not in spec; shows root and presets |

`trends` layers: `smap_anomaly|heatwave_days|grace_gw_pct|precip_anomaly|modis_ndvi_anomaly|usdm_d2_weeks|reservoir_storage`. `from`/`to` filter `rows`/`items` by their `date` string.

`POST .../score` body: `{weights, constraints, market_preference, allocation, replay_year, scenario:{dT_c, dP_pct}}`. Scored by the rotation engine (`rotation_engine.score`, path dependency `../engine`); all request fields apply. **Fallback placeholder** (engine import/run fails): composite = sum(w_i * s_i) / sum(w_i) over stored per-criterion scores (value, low, high), plus a tie flag (interval overlap > 50%). Weights in [0,4]; unknown keys give 422. Defaults: 1 for water_use, forage_value, n_fixation, erosion, organic_matter, market; 0 for the rest. The scenario is echoed into `exposure.scenario`; in fallback mode constraints, allocation, replay_year and the scenario do not change numbers.

## Real data per route (frontend: read this)

`X-Data-Source` / `_source` says `real` or `fixture` per response. After `build_real.py`:

| Route | Source | Notes |
|---|---|---|
| `GET /api/locations`, `/api/locations/{id}` | real | field polygon (DWR/Land IQ 2023 outline, ~60 ha CAR / ~29 ha CAF), SSURGO soil, NOAA stations, `county_fips` 011 (Colusa) / **031 (Kings)**, `crop_history` (CDL 2008-2025), `observed_cover.typically_bare_doy_ranges` (satellite consensus), `datasets` status. `terrain.*` is `value: null` ("blocked: no DEM"), except `elev_m` = POWER cell elevation (flagged in its note). `water.*`, `market_preference`, `regime`, `events` are spec statements (U) copied from the fixtures. `regional_cell.grid` is `POWER_MERRA2_0.5x0.625` (no SMAP EASE grid yet) |
| `GET .../daily?from&to` | real | 2015-2025 daily: POWER `tmax_c/tmin_c/precip_mm`, Hargreaves `eto_mm`, `cover_class` from the satellite calendar (`unknown` before 2016 and across gaps), `ndvi` only on observation days, plus `ncei_tmax_c/ncei_tmin_c/ncei_precip_mm` (station mean), `heatwave_day`, `severe_heat_40c`. `smap_sm_pct` is always null (blocked) |
| `GET .../features/weekly` | real | 2016-2025 weeks (Monday start): NDVI/BSI from S2+Landsat observations, POWER Tmax/Tmin/ETo, `usdm_category`. Everything needing Earthdata/OpenET is null |
| `GET .../strategies`, `POST .../score` | real | rotation engine, real SSURGO soil, baseline exposure uses observed consensus cover (see backend/engine/README) |
| `GET .../zones` | real, partial | `stress_hotspot` features = lowest-decile mean Jul-Sep NDVI 30 m cells (2016-2025, U). `slope` and `low_spot` are present with `meaningful:false` and a "blocked: no DEM" note; `openet_zone` absent (OpenET key) |
| `GET .../trends?layer=&year=` | real for `heatwave_days`, `precip_anomaly`, `usdm_d2_weeks`, `reservoir_storage`; fixture for `smap_anomaly`, `grace_gw_pct`, `modis_ndvi_anomaly` (Earthdata) | real layers have **one cell** (`cells` has a single `{row:0,col:0}`; `grid` is `POWER_MERRA2_0.5x0.625`, `county_<fips>` or `cdec_<stations>`), not an 11x11 neighbourhood. Real files hold every year; `year` omitted -> `default_year` (2025; 2022 for USDM/reservoir), a year with no data -> 404. `field_cell_series` is the per-year value (POWER 1981-2025, USDM/CDEC 2015-2025). `note` explains each layer. Units: `days/yr`, `% of 1991-2020 mean`, `weeks/yr` (>= 50% of county in D2+), `thousand acre-ft (annual mean)` |
| `GET .../validation` | real | `power_vs_ncei_precip`, `power_vs_ncei_tmax`, `power_vs_ncei_tmin` (monthly bias/RMSE/R2 plus `by_calendar_month`), `power_vs_ncei_heat40` (days >= 40 C per year, POWER vs each station). `openet_vs_etc`, `cimis_vs_power`, `station_vs_imerg` are `status: "blocked"` ("needs OpenET API key" / "needs CIMIS appKey" / "needs Earthdata login") |
| `GET .../calendar?year=` | real (new) | backend/field `calendar.json` as documented in backend/field/README (classes, per-year `segments` tiling every day, `transitions`, `markers`, `observations`) plus `crop_history` (`by_year`, `years` with purity). `year` keeps one year |
| `GET .../grid?layer=` | real (new) | 30 m GeoJSON (EPSG:4326), top-level `layers` metadata and `source`; ~1.8 MB for CAR with all 52 NDVI layers, so pass repeatable `layer=ndvi_2023_q3` to slim it (`layer` keys are listed in `layers[].key`) |
| `GET .../news`, `GET /api/bc/news` | real | backend/news |
| `GET /api/crops/{cid}` | real | engine crops.json |
| `GET .../models`, `GET /api/bc/signal`, `GET /api/glossary` | fixture | no producer (AI workstream) / SMAP+GRACE blocked / no producer |

Known data caveats the UI should not hide: POWER overstates rain vs the NCEI stations (+54% CAR, +68% CAF in monthly totals) and runs warm in summer (JJA Tmax about +3.4 C CAR, +3.8 C CAF), so `heatwave_days`, `severe_heat_40c` and the engine's heat/dry-day counts are high-biased. See `backend/regional/README.md`.

## Schemas (`schemas/`)

`sourced_number, location, crop, rotation_strategy, model_report, news_item, feature_row` (`*.schema.json`) per spec B3 / B2.14, plus `responses.schema.json` with one `$defs` envelope per route. Draft 2020-12, `$id` base `https://fieldshift.local/schemas/`.

## Mismatches with other chunks (resolved by `build_real.py`)

- `backend/regional/out/{id}/` has `eto_monthly.json`, `risk_days_by_year.json`, `daily_derived.parquet`, none a B3 payload; the builder turns them (plus POWER/NCEI/USDM/CDEC caches) into `backend/api/out/{id}/`. The API still has no parquet reader, only JSON.
- `backend/news/out/{id}.json` matches (bare array, wrapped). BC items are in `bc_opener.json`.
- Schema changes made for real data: `trends.layer` gained `usdm_d2_weeks`, `reservoir_storage`; `trends.grid` and `location.regional_cell.grid` are free strings (were const `EASE2_G9km`); `validation.checks[].id` gained `power_vs_ncei_{precip,tmax,tmin,heat40}`.
- No chunk owns `models.json` (AI workstream) or `glossary.json`; both stay fixtures.

## Open questions

- Default weights: spec says six brief priorities plus pest_break, infiltration, income (default 0); I took the six as water_use, forage_value, n_fixation, erosion, organic_matter, market and also defaulted n_scavenging to 0.
- Who fills `Location.datasets` entries (shape is free: `{status, meta_path, ...}`)?
- Fixture polygons are placeholder squares around the preset centres, not CDL-checked fields.

## Static export and Pages deploy

`uv run python export_static.py` (from `backend/api`) calls every GET route in-process with FastAPI's TestClient and writes the responses to `frontend/app/public/api/` (git-ignored), mirroring the URL path with `.json` appended: `locations.json`, `locations/{id}.json`, `locations/{id}/{daily,features/weekly,strategies,models,zones,validation,news,calendar,calendar_ml,grid,outlook}.json`, `locations/{id}/trends/{layer}.json` (default year) and `trends/{layer}/{year}.json`, `crops/{cid}.json`, `bc/news.json`, `bc/signal.json`, `glossary.json`. `POST /score` is precomputed per preset to `locations/{id}/score/{variant}.json` for `default`, `replay-2022`, `replay-2023` and `dT{0,2,4}_dP{-20,0,20}` (default weights). `manifest.json` lists files, sizes and generation time; routes that fail are printed and recorded under `skipped`. Total is about 11 MB (grids ~1.8 MB / 0.9 MB, daily ~1 MB each). It reads only committed files; no keys, no `.env`.

`.github/workflows/deploy-pages.yml` runs the exporter, then `VITE_BASE=/space_apps/ npm run build:static` in `frontend/app`, and deploys `dist` with GitHub Pages on pushes to main touching `frontend/`, `backend/`, `data/` or `fixtures/`, or by manual dispatch. One-time repo setup: Settings -> Pages -> Source: GitHub Actions. Site URL: https://spurinv.github.io/space_apps/. Local check: `VITE_BASE=/space_apps/ npm run build:static && npx vite preview --base /space_apps/`.
