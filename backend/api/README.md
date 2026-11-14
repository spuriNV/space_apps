# Field Shift API (`backend/api`)

FastAPI app serving the spec B3 routes. No database. Each route returns a real output file if one exists, otherwise a fixture from `fixtures/`.

## Run

```
cd backend/api
uv run uvicorn app.main:app --port 8000 --reload     # http://localhost:8000/docs
uv run python checks/check_api.py                     # PASS/FAIL per route, exit 1 on failure
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
| `GET /api/locations/{id}` | `location.json` | `data/cache/{id}/location.json`, `backend/field/out/{id}/location.json`, `backend/engine/out/{id}/location.json` |
| `GET .../daily?from&to` | `daily.json` | `data/cache/{id}/daily.json`, `backend/regional/out/{id}/daily.json` |
| `GET .../features/weekly` | `features_weekly.json` | `data/cache/{id}/features_weekly.json`, `backend/field/out/{id}/features_weekly.json` |
| `GET .../strategies` | `strategies.json` | `backend/engine/out/{id}/strategies.json`, `data/cache/{id}/strategies.json` |
| `POST .../score` | re-weights the strategies | same source as strategies; `_source` follows it |
| `GET .../models` | `models.json` | `data/cache/{id}/models.json`, `backend/ai/out/{id}/models.json`, `backend/field/out/{id}/models.json` |
| `GET .../zones` | `zones.json` | `data/cache/{id}/zones.json`, `backend/field/out/{id}/zones.json` |
| `GET .../trends?layer&year` | `trends_{layer}.json` | `backend/regional/out/{id}/trends_{layer}.json`, `data/cache/{id}/trends_{layer}.json` |
| `GET .../news?from&to` | `news.json` | `backend/news/out/{id}.json`, `data/cache/{id}/news.json` |
| `GET .../validation` | `validation.json` | `backend/regional/out/{id}/validation.json`, `backend/field/out/{id}/validation.json`, `data/cache/{id}/validation.json` |
| `GET /api/bc/news` | `bc_news.json` | `backend/news/out/bc_opener.json`, `backend/news/out/bc_news.json`, `data/cache/bc/news.json` |
| `GET /api/bc/signal` | `bc_signal.json` | `backend/regional/out/bc_signal.json`, `data/cache/bc/signal.json` |
| `GET /api/glossary` | `glossary.json` | `backend/engine/out/glossary.json`, `data/cache/glossary.json` |
| `GET /api/crops/{cid}` | `crops/{cid}.json` | `backend/engine/out/crops/{cid}.json`, or the entry with that `id` in `backend/engine/crops.json` (`{"crops": [...]}`) |
| `GET /api/health` | | not in spec; shows root and presets |

`trends` layers: `smap_anomaly|heatwave_days|grace_gw_pct|precip_anomaly|modis_ndvi_anomaly`. `from`/`to` filter `rows`/`items` by their `date` string.

`POST .../score` body: `{weights, constraints, market_preference, allocation, replay_year, scenario:{dT_c, dP_pct}}`. Scored by the rotation engine (`rotation_engine.score`, path dependency `../engine`); all request fields apply. **Fallback placeholder** (engine import/run fails): composite = sum(w_i * s_i) / sum(w_i) over stored per-criterion scores (value, low, high), plus a tie flag (interval overlap > 50%). Weights in [0,4]; unknown keys give 422. Defaults: 1 for water_use, forage_value, n_fixation, erosion, organic_matter, market; 0 for the rest. The scenario is echoed into `exposure.scenario`; in fallback mode constraints, allocation, replay_year and the scenario do not change numbers.

## Schemas (`schemas/`)

`sourced_number, location, crop, rotation_strategy, model_report, news_item, feature_row` (`*.schema.json`) per spec B3 / B2.14, plus `responses.schema.json` with one `$defs` envelope per route. Draft 2020-12, `$id` base `https://fieldshift.local/schemas/`.

## Mismatches with other chunks (checked on disk)

- `backend/news/out/{id}.json` matches (bare array, wrapped). BC items are written to `bc_opener.json`; that path was added. Items must match `news_item.schema.json` (check on first real run).
- `backend/regional/out/{id}/` holds `eto_monthly.json`, `risk_days_by_year.json`, `daily_derived.parquet`: none is a B3 payload. The API needs `daily.json`, `trends_{layer}.json`, `validation.json`, `bc_signal.json` there. JSON only, no parquet reader.
- `data/cache/{id}/` holds parquet + `*.meta.json` + `soil.json`; no `location.json`. `backend/engine/out/` and `backend/field/out/` do not exist yet. No chunk owns `models.json` (AI workstream) or `glossary.json`.

## Open questions

- Default weights: spec says six brief priorities plus pest_break, infiltration, income (default 0); I took the six as water_use, forage_value, n_fixation, erosion, organic_matter, market and also defaulted n_scavenging to 0.
- Who fills `Location.datasets` entries (shape is free: `{status, meta_path, ...}`)?
- Fixture polygons are placeholder squares around the preset centres, not CDL-checked fields.
