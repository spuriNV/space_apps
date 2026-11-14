# CropLytics: main frontend (`frontend/app`)

One product, one look, four screens (see `PLAN.md`). Satellite map, field panel on the left, timeline along the bottom, 3D stack when you scroll in. The look is the "Extension bulletin" style only (Zilla Slab + Libre Franklin, spot-green header band, paper panel; tokens at the top of `src/styles.css`, rules in `.claude/skills/fieldshift-visual-design/`).

## Run

```bash
cd backend/api && uv run uvicorn app.main:app --port 8000     # the API (live data)
cd frontend/app && npm install && npm run dev                 # http://localhost:5170, reads http://localhost:8000/api
npm run typecheck
VITE_API_BASE=/api npm run build                              # production build; the backend serves it at / with the API at /api
node ../../design/tools/shoot-app.mjs                         # screenshots -> design/screenshots/app/
```

`VITE_API_BASE` sets where the API is: default `http://localhost:8000/api` in dev and same-origin `/api` in a build. There is no file bridge: everything real comes through the API. If the API does not answer, the app shows the bundled examples in `src/mock` and says so (top-right indicator and a note on the pick list).

## Screens

1. **Pick your field** (`ui/Options.tsx` `FieldPicker`): two fields, named the way a grower would ("Rice field 3.5 miles east of Williams"), with the crop record in one line.
2. **Your field now** (`ui/Options.tsx` `FieldPanel`, `ui/FieldNow.tsx`, `ui/NasaSection.tsx`): crop and stage, green cover, rain since 1 Oct (NASA GPM IMERG), crop water use so far (rotation model with NASA POWER weather, OpenET check), irrigation need against the water limit, soil moisture and groundwater (NASA GRACE-FO; SMAP when cached), hot days (104 °F) and frost nights (NOAA stations); then **NASA data behind this field** (ISS photo with NASA's credit line, every NASA dataset with what it tells the grower, its footprint and whether it is live); then soil, slope (NASADEM), salt, water, crop-insurance payouts, bare days; the last 3 seasons. "What's this?" links explain greenness, crop water use, water balance, soil-moisture percentiles, frost and bare days.
3. **Coming season** (`season/ComingSeason.tsx`): NOAA outlooks, drought, reservoirs, water in the ground going into winter (NASA IMERG and GRACE-FO), allocations, snowpack, the longest bare stretch this winter, irrigation need per rotation. "Outlooks, not forecasts".
4. **Compare and print**: `compare/ComparePanel.tsx` (gain / give up against today; priorities and a drier/hotter what-if re-scored by `POST /score`; the side-by-side table) and `brief/RotationBrief.tsx` (one Letter page from fixed templates, with all four rotations at a glance).

**This field's year** (`year/YearSheet.tsx`, from the timeline): typical year plus one strip per season, 2023–2026 (earlier years behind a link). "Compare with machine learning" adds the ML calendar under each season with a plain verdict: Kings is below the accuracy target (83% in the 2022 hold-out against 85%); Colusa's 99% is flagged as too good to take at face value.

## One definition per number

- **Bare** = satellite greenness below 0.2 and not under water (`src/bare.ts`). Today's rotation: what the satellites saw over the last 3 processed years. Alternatives: the rotation model, labelled "est.".
- **Hot days** = NOAA station highs of 104 °F (40 °C) or more (`season.ts` `HOT_C`). On Compare, hot days that land in months the rotation leaves the field bare.
- **Water limit**: pre-filled example per field (Colusa 5.0, Kings 3.0 acre-ft/acre, `api.ts` `EXAMPLE_LIMIT`), labelled "example, change to yours" until the grower moves it.

## Data: what each part reads

| Part | Route |
|---|---|
| Outline, area, soil, crop record, `nasa_datasets`, NASADEM terrain | `GET /api/locations`, `GET /api/locations/{id}` |
| Field calendar | `GET .../calendar?source=hls` (NASA HLS) when served, else `GET .../calendar` |
| ML calendar and its accuracy | `GET .../calendar_ml`, `GET .../models` |
| 3D top layer | `GET .../grid` |
| Soil moisture, groundwater per 10 days | `GET .../nasa_series` |
| Rain since 1 Oct today | `GET .../nasa_now` |
| Rain, heat, frost, reference ET by day | `GET .../daily` |
| Rotations; priorities and what-ifs | `GET .../strategies`, `POST .../score` |
| Coming season | `GET .../outlook` |
| News | `GET .../news` |
| ISS photo | static files in `public/iss/<id>/` (copied and resized from `data/cache/<id>/iss/`) |
| DWR field number, soil EC and texture, NASADEM fallback, crop-insurance totals | `src/mock/field_extra.json`: real values copied from backend outputs the API does not serve yet |

Still example numbers: the 3D "water use" view and its risk ticks, the water district text.

## API fields still wanted

- `dwr_unique_id`, `soil.ec_ds_per_m`, `soil.texture_detail` in `GET /api/locations/{id}` (today from `field_extra.json`).
- A crop-insurance route (`backend/ground/out/<id>/rma_profile.json`).
- A stress-weeks route (`backend/ai/out/<id>/stress_weekly.json`) to mark crop-stress weeks on the year strips.
- `GET /api/glossary` with real content (the "What's this?" text lives in `ui/What.tsx` for now).
