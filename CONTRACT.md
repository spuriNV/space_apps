# Field Shift: build contract (v0)

Shared rules for everyone (people and agents) building in this repo. The product spec is `docs/planner-spec.md` (Part B); the team plan is `docs/field-shift-plan.md`. This file only fixes what parallel work needs to agree on.

## Scope
- **California only.** Two presets: `car_colusa_rice` (centre 39.15 N, -122.10 W) and `caf_tulare_forage` (centre 36.20 N, -119.60 W). BC appears only as the "Why not BC yet" card and the opener news timeline.
- Working CRS EPSG:32610; GeoJSON in EPSG:4326 (lon, lat order).

## Layout (one owner per directory; do not write outside yours)
```
frontend/variants/a-maps/      design variant A (Vite + React + TS + MapLibre), port 5171
frontend/variants/b-earth/     design variant B, port 5172
frontend/variants/c-split/     design variant C, port 5173
design/screenshots/            <variant>-<nn>-<name>.png, 1440x900
design/tools/                  shared playwright-core install for screenshots
backend/api/                   FastAPI app serving spec B3 routes from fixtures/cache, port 8000
backend/regional/              POWER, CDEC, USDM, SSURGO, NOAA fetchers + ETo + risk days
backend/field/                 Sentinel-2 / Landsat / CDL field series, polygons, rule detector
backend/engine/                crops.json, 8 strategies, scoring (spec B4)
backend/news/                  news timeline cache (spec B9)
schemas/                       JSON Schemas for spec B3 types (owned by backend/api)
fixtures/                      example JSON per preset (owned by backend/api)
data/cache/<preset_id>/        <dataset>.parquet + <dataset>.meta.json (spec B2 general rules)
```
Each `backend/<chunk>/` is its own `uv` project (own `pyproject.toml`, Python 3.12 via `uv`), with a `README.md` (what it does, how to run, what is verified) and a `checks/` script that prints PASS/FAIL lines so a human can validate the chunk alone.

## Data honesty (non-negotiable)
- Backend: never invent a data value. If an endpoint fails or needs a key we don't have (Earthdata, OpenET, CIMIS, NASS, AMS), record that in the chunk README under "Blocked" and move on. Every number is a `SourcedNumber` (spec B3) with a source URL; spec items marked **U** stay `verified: false`.
- Frontend mocks: illustrative numbers are fine, but they live in `src/mock/` shaped like the spec B3 schemas, and the UI shows a visible "Mock data" badge. Real, cited facts from the spec (dates, events, URLs) may be used as-is.

## Frontend conventions
- No API keys. Map: MapLibre GL JS. Streets style: OpenFreeMap (`https://tiles.openfreemap.org/styles/liberty`). Satellite: Esri World Imagery raster (`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`). Terrain DEM: AWS Terrarium (`https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`, encoding `terrarium`).
- All data access goes through `src/api.ts`, which today reads `src/mock/*.json` and later calls `http://localhost:8000/api/...` (routes in spec B3).
- Plain language, dual units, "supports, doesn't replace" tone (spec B8).

## Judging
Everything we build is scored on Impact, Creativity, Validity, Relevance and Presentation (1–5 each). `docs/judging-rubric.md` quotes each criterion, says where we stand and lists the gaps; check your work against the criterion it serves and update the file when a gap closes.
