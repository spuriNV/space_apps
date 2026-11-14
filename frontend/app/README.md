# Field Shift: main frontend (`frontend/app`)

One product, one look, four screens (see `PLAN.md`). Satellite map, field panel on the left, timeline along the bottom, 3D stack when you scroll in. The look is the "Extension bulletin" style only (Zilla Slab + Libre Franklin, spot-green header band, paper panel; tokens in `src/themes.css`, rules in `.claude/skills/fieldshift-visual-design/`). The theme switcher and the other two looks are gone.

## Run

```bash
cd backend/api && uv run uvicorn app.main:app --port 8000     # live data
cd frontend/app && npm install && npm run dev                 # http://localhost:5170 (strictPort)
npm run typecheck
node ../../design/tools/shoot-app.mjs                         # screenshots -> design/screenshots/app/
```

## Screens

1. **Pick your field** (`ui/Options.tsx` `FieldPicker`).
2. **Your field now** (`ui/Options.tsx` `FieldPanel`, `ui/FieldNow.tsx`): crop and stage, green cover, rain so far this season vs normal (NOAA stations), crop water use so far vs normal (rotation model scaled by this year's weather, with the OpenET check line), irrigation need vs your limit (acre-feet), soil moisture and groundwater (example numbers until Earthdata), hot days and frost nights (stations), soil, drainage, salt, the last 3 seasons. Answers follow the timeline date, which opens on today (mid Nov 2026); past the end of the processed data they fall back to the latest season and say so. The next steps sit in a fixed footer.
3. **Coming season** (`season/ComingSeason.tsx`): NOAA 3-month rain/temperature outlooks, drought now and outlook, reservoir storage vs average, allocations (and Shasta storage vs the next year's CVP allocation), snowpack, this winter's bare window and the chance of a 1-inch rain day in it, next season's irrigation need per rotation. Labelled "outlooks, not forecasts".
4. **Compare and print**: `compare/ComparePanel.tsx` (gain / give up vs today, "See all side by side" table) and `brief/RotationBrief.tsx` (one page for the adviser, no scores as headlines).

The timeline and the year view (`year/YearSheet.tsx`: typical year + one strip per season) show 2023–2026 by default; "Show earlier years" adds 2016–2022. 2026 is hatched: imagery not processed yet.

## Structure

```
src/api.ts                    only data seam: API -> repo file bridge -> bundled mock, with per-part provenance
vite.config.ts                dev-only /repo/ bridge (allow-listed backend output files the API had no route for)
src/components/ui/            field panel + pick list (Options.tsx); farmer wording helpers, answers, soil, record (shared.tsx)
src/themes.css                the one set of design tokens
src/components/brief/         printable rotation brief (from variant C), fed from the strategies
src/components/year/          "This field's year": typical year + one strip per season
src/components/compare/       gain / give up vs today, plus the side-by-side table
src/components/season/        coming season (outlooks)
src/season.ts                 rain, heat/frost, crop water use so far, bare window: computed from GET .../daily and the calendar
src/components/Timeline.tsx   scrubber; imports year/YearSheet
src/MapView.tsx, lib.ts       map + 3D stack; the top layer uses the real 30 m grid when it is loaded
```

## Data: live vs mock

The top-right indicator says **Live data** when `GET /api/health` answers, otherwise **Example data**, meaning everything comes from `src/mock`. Click it to see where each part comes from. Parts that are still illustrative say **Example numbers, not live yet.** in their source line.

| Part | Source when live |
|---|---|
| Field outline, area, county | `GET /api/locations`: DWR/Land IQ 2023 outline. Kings County field 1603054, 29.5 ha |
| Soil | `GET /api/locations` (SSURGO): Kimberlina fine sandy loam, saline-alkali, group C. Texture split and EC come from `data/cache/<id>/soil.json` via the bridge |
| Crop on record | `GET /api/locations` (CDL 2008–2025) |
| Bare/covered/water calendar (timeline strip, year sheet, readout) | `GET .../calendar`: Sentinel-2 + Landsat NDVI rule, resampled to 10-day steps |
| 3D top layer | `GET .../grid`: per-cell Sentinel-2 NDVI. Uses a single clear scene if one is within 12 days of the scrubber date, else the quarterly median |
| Rotations, scores, brief numbers | `GET .../strategies`; `POST .../score` when the water allocation slider moves |
| News | `GET .../news` (cached headlines) |
| Rain, hot days, frost nights, weather for crop water use so far | `GET .../daily` (NOAA station means; POWER reference ET). Runs to 31 Dec 2025, so 2026 answers fall back to the last full season |
| OpenET check line | `GET .../strategies` baseline `water.etc_vs_openet_pct` (kept when `POST /score` drops it) |
| Coming season | `backend/outlook/out/<id>/outlook.json` through the bridge (no API route yet); else `backend/outlook/out/{cpc,water_now}.json`; else `src/mock/outlook.example.json` (example, labelled) |
| **Mock** | SMAP and GRACE (field panel answer and 3D slabs), the 3D "Water use" metric, water district/events text, the GSA note on the coming-season screen |

If an API route is missing, `api.ts` reads the documented output file through `/repo/` and labels it "Live · file".

## API routes still needed

- `GET /api/locations/{id}/outlook` serving `backend/outlook/out/<id>/outlook.json` (today read through the dev bridge).
- `GET .../daily` extended through today (NOAA stations for Oct–Nov 2026), so "rain so far this season" and heat/frost can answer for this season instead of last season.
- 2026 satellite calendar (`GET .../calendar` for 2026), so "what is growing now" is not stuck at Dec 2025.
- `POST .../score` should return `water.etc_vs_openet_pct` and `openet_et_mm_season` like `GET .../strategies` does.
- A monthly measured water-use route (OpenET, `data/cache/<id>/openet.parquet`) so "crop water use so far" can show measured, not modelled, use.

- `GET .../trends` with real SMAP root-zone percentile and GRACE groundwater percentile at 10-day steps for the slabs. Today they are fixtures because Earthdata is blocked. The real `heatwave_days` and `precip_anomaly` layers are not wired into the Trends panel yet.
- A risk-days series per 10-day step (heavy rain, frost, heat, dry) for the year-sheet ticks. `daily` has the inputs.
- ML detector cover classes (`models` / `features/weekly`) to make the Rule/ML toggle real.
- Soil texture split (`texture_detail`) and `ec_ds_per_m` in `location.soil`, so the bridge can be dropped.
- `dwr_unique_id` in `location` (shown as the field ID). Today it is read from `backend/field/polygons/<id>.geojson`.
- Brief text: `brief.why` / `brief.evidence` are empty in the engine output. The brief fills in template sentences built from the engine's numbers and labels them "template".

