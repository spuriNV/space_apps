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

1. **Pick your field** (`ui/Options.tsx` `FieldPicker`): every field `GET /api/locations` serves (a map pin for each; names show on hover at state zoom), a search box (town, county, crop, district) and Rice / Forage chips over one list with a satellite thumbnail (outline drawn, `public/thumbs/`), a 2023–2026 season strip, one line of facts and one of what is notable.
2. **Field now** (`ui/FieldNow.tsx`): a visual summary (thumbnail, this year's strip with a today tick, small bars for rain vs normal, water need vs limit, greenness, soil and groundwater percentiles) and five short answers (what's growing, rain, water need vs limit, soil and groundwater vs usual, and what the soil is like: a sand/silt/clay bar, water held, drainage, salt and one rotation sentence; rows with no value are hidden). Each answer loads on its own (skeleton, then "Not available right now" after 15 s). More detail: green cover, crop water use (OpenET measured, model alongside), crop stress and standing water (NASA OPERA), heat and frost, the ISS photo and NASA dataset list, soil, slope, water, insurance, bare days, last seasons, sources.
3. **Coming season** (`season/ComingSeason.tsx`): three sentences (winter rain, water supply, next season's need for today's rotation); More detail has the outlooks, drought, reservoirs, ground water, allocations, snowpack, bare stretch and every rotation.
4. **This field's year** (`year/YearSheet.tsx`): typical year and 2023–2026 strips, events, "Replay on the map". More detail: ML comparison with a plain verdict, crop-stress weeks (hover for why), OPERA standing water, earlier years.
5. **Compare** (`compare/ComparePanel.tsx`): today vs the two best-scoring alternatives in acre-feet and days; "See all options" for the full table. More detail: every rotation, soil and feed scores, priorities and rain/heat what-ifs (`POST /score`).
6. **Print** (`brief/RotationBrief.tsx`): one Letter page from fixed templates.

## British Columbia

The API's `region` ("ca" or "bc") drives the BC field (`bc_salmon_river_forage`). It sits under a "British Columbia" heading and chip in the pick list; the old "not set up yet" row, pins and card show only when the API serves no BC field.

- **Gaps:** `data_gaps` on the location route. A route that answers with `_source: "estimate"` renders normally with an "Estimated." tag, and the gap's reason and `filled_with` sit under More detail. A route that still answers 404 gets one quiet "Not available in BC" line in its place.
- **Weather:** `season.ts` falls back to the ECCC station columns (`eccc_*`) when the NOAA ones are null.
- **Soil:** "unknown" values are hidden.
- **Water:** the watershed and irrigation orders from `water_context` replace the California water district line.
- **Working with First Nations:** a field-panel card from `GET .../first_nations` (`ui/FirstNations.tsx`).
- **Map layer:** "Reserve boundaries (context)" draws `GET .../first_nations/reserves.geojson`. It is offered only for BC and is off by default.

## One definition per number

- **Bare** = satellite greenness below 0.2 and not under water (`src/bare.ts`). Today's rotation: what the satellites saw over the last 3 processed years. Alternatives: the rotation model, labelled "est.".
- **Hot days** = NOAA station highs of 104 °F (40 °C) or more (`season.ts` `HOT_C`). On Compare, hot days that land in months the rotation leaves the field bare.
- **Water limit**: pre-filled example per field (Colusa 5.0, Kings 3.0 acre-ft/acre, `api.ts` `EXAMPLE_LIMIT`), labelled "example, change to yours" until the grower moves it.

## My fields (draw a field)

"Draw a field" (a pill at the top right of the map, and a button in the pick list's **My fields** group) outlines a field with `terra-draw` (pinned, lazy-loaded: a separate chunk, not in the first download). **Rectangle** (drag, or tap two corners) or **Shape** (tap each corner, tap the first point to finish); handles then let you reshape it, with live acres. **Name it** opens a rounded dialog with "My field N" filled in; saving shows the field panel at once in its skeleton state, then fills it from `POST /api/my-fields`. A 422 shows the API's `detail` verbatim with "Fix the outline"; 429, 504 and network errors show a message and "Try again".

- **State:** `localStorage["myFields"] = [{id, name}]` (every read and write guarded). The id (`my_...`) is the field: it carries the name and the outline. `src/myFields.ts` holds the calls, the hook (`useMyFields`) and the `Location` conversion; the list and outlines come from one cheap `GET /api/my-fields?ids=...`, the full analysis from `GET /api/my-fields/{id}` when a field is picked.
- **Panel:** header "Your field" and an **Options** menu (Rename, Redraw the outline, Copy share link, Delete with an in-page confirm). Rename and Redraw post again and swap the id. A drawn field reuses the tapped-spot sections (only `ready` parts show; `unavailable` gets one quiet line, which is what BC outlines get for now), plus a "This field spans..." line, the crop-map mix, the state map's overlapping fields (More detail) and the API's `simplified.reason` as a quiet note. Only `/locations/{id}`, `/strategies`, `/daily` and `POST /score` are called for `my_` ids.
- **Map:** drawn fields have a solid light-green outline and tint ("yours"), presets keep their white lines.
- **Share:** `#field=my_...` links. Opening one asks "Add this field to yours?" before it joins the list.
- **Code:** `src/components/draw/` (`DrawLayer.tsx` the drawing session and dialogs, `terraDraw.ts` the library wiring, `MyFieldBits.tsx` panel and list pieces, `Modal.tsx`, `draw.css`). Screenshots: `node ../../design/tools/shoot-draw.mjs`.

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

The water row shows the looked-up district, GSA and basin status (`water.district`, `water.gsa`, `water.sgma_status` with its link), leaving out empty values; "not looked up yet" only when the API does not answer. A field whose `/outlook` or `/calendar_ml` is not built yet (404) says "not ready for this field yet" instead of showing another field's example; a new field borrows the bundled rice or forage example only while the API is down. Nothing else is example data when the API answers.

## API fields still wanted

- `GET .../stress`, `GET .../insurance`, real `GET /api/glossary` (the app falls back without them).
- A looked-up water district / GSA in `GET /api/locations/{id}` `water`.
