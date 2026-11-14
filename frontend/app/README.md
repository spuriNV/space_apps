# CropLytics: main frontend (`frontend/app`)

One product, one look, four screens (see `PLAN.md`). A top bar (wordmark, field switcher, section tabs, data status, map layers), satellite map, field panel on the left, timeline along the bottom, 3D stack when you scroll in. The look is the "Extension bulletin" style only (Zilla Slab + Libre Franklin, spot-green header band, paper panel; tokens at the top of `src/styles.css`, rules in `.claude/skills/fieldshift-visual-design/`).

## Run

```bash
cd backend/api && uv run uvicorn app.main:app --port 8000     # the API (live data)
cd frontend/app && npm install && npm run dev                 # http://localhost:5170, reads http://localhost:8000/api
npm run typecheck
VITE_API_BASE=/api npm run build                              # production build; the backend serves it at / with the API at /api
node ../../design/tools/shoot-app.mjs                         # screenshots -> design/screenshots/app/
```

`VITE_API_BASE` sets where the API is: default `http://localhost:8000/api` in dev and same-origin `/api` in a build. There is no file bridge: everything real comes through the API. If the API does not answer, the app shows the bundled examples in `src/mock` and says so (top-right indicator and a note on the pick list).

## Layout

- **Top bar:** CropLytics wordmark, field switcher (search inside), section tabs (Field now · Coming season · This field's year · Compare · Print), the **Viewing** date control (quick picks, month picker, "Back to today"; a banner shows the date when it is not today) and Map layers. No bottom timeline; the map and panels use the full height.
- **Farmer default, adviser detail:** each screen opens on the decision; one inline **More detail** disclosure (remembered for the session, `ui/Detail.tsx`, class `.d-only`) adds sources, the NASA list, ML comparison, stress weeks, standing water, 3D, percentiles and ranges, glossary, insurance, earlier years, every rotation, priorities and what-ifs.
- **Phone (≤ 640 px):** wordmark, field switcher and a menu on top; bottom tab bar; the field panel is a bottom sheet (peek / half / full); sheets become full-screen pages. Mobile shell build: `VITE_API_BASE=https://croplytics-app.onrender.com/api VITE_BASE=./ npm run build`.

## Screens

1. **Pick your field** (`ui/Options.tsx` `FieldPicker`): one list with a satellite thumbnail (outline drawn, `public/thumbs/`), a 2023–2026 season strip, one line of facts and one of what is notable.
2. **Field now** (`ui/FieldNow.tsx`): a visual summary (thumbnail, this year's strip with a today tick, small bars for rain vs normal, water need vs limit, greenness, soil and groundwater percentiles) and four one-sentence answers. Each answer loads on its own (skeleton, then "Not available right now" after 15 s). More detail: green cover, crop water use (OpenET measured, model alongside), crop stress and standing water (NASA OPERA), heat and frost, the ISS photo and NASA dataset list, soil, slope, water, insurance, bare days, last seasons, sources.
3. **Coming season** (`season/ComingSeason.tsx`): three sentences (winter rain, water supply, next season's need for today's rotation); More detail has the outlooks, drought, reservoirs, ground water, allocations, snowpack, bare stretch and every rotation.
4. **This field's year** (`year/YearSheet.tsx`): typical year and 2023–2026 strips, events, "Replay on the map". More detail: ML comparison with a plain verdict, crop-stress weeks (hover for why), OPERA standing water, earlier years.
5. **Compare** (`compare/ComparePanel.tsx`): today vs the two best-scoring alternatives in acre-feet and days; "See all options" for the full table. More detail: every rotation, soil and feed scores, priorities and rain/heat what-ifs (`POST /score`).
6. **Print** (`brief/RotationBrief.tsx`): one Letter page from fixed templates.

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
| ISS photo, field thumbnails | static files in `public/iss/<id>/`, `public/thumbs/` |
| Crop stress, standing water, measured water use, insurance, glossary | `GET .../stress`, `.../water_seen` (else the OPERA column of `nasa_series`), `.../openet`, `.../insurance`, `GET /api/glossary` |
| Crop-insurance totals until `/insurance` answers | `src/mock/field_extra.json` (copied from backend/ground) |

The water district shows "not looked up yet" until the location route carries a looked-up district. Nothing else is example data when the API answers.

## API fields still wanted

- `GET .../stress`, `GET .../insurance`, real `GET /api/glossary` (the app falls back without them).
- A looked-up water district / GSA in `GET /api/locations/{id}` `water`.
