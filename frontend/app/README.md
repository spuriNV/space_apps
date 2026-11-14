# Field Shift: main frontend (`frontend/app`)

Built from design variant B (Earth explorer): satellite map, timeline scrubber 2016–2025, and the 3D drill-down stack (surface → soil → groundwater). The field selection and field panel were redone so they read like an analysis tool instead of a place card. The printable rotation brief comes from variant C.

## Run

```bash
cd backend/api && uv run uvicorn app.main:app --port 8000     # optional: live data
cd frontend/app && npm install && npm run dev                 # http://localhost:5170 (strictPort)
npm run typecheck
node ../../design/tools/shoot-app.mjs                         # screenshots -> design/screenshots/app/
```

One farmer-first field panel (the old `?ui=1|2|3` dossier / mission strip / analysis rail options were removed). With no field picked, the left column shows **Pick your field** ("Alfalfa field 6 miles south of Hanford, Kings County, 73 acres"). A picked field shows what it is, then plain answers for the timeline date (ground cover, soil moisture vs usual, basin groundwater vs usual, water the current rotation needs vs your limit), then the next actions, soil and water facts, crop record, events and sources.

`?theme=1|2|3` switches the visual theme (tokens in `src/themes.css`; rules in `.claude/skills/fieldshift-visual-design/SKILL.md`):

| `theme` | Name | Fonts | Idea |
|---|---|---|---|
| 1 (default) | Survey sheet | Source Serif 4 + Overpass | USGS quad / soil-survey print: paper panels, black ink, map inks |
| 2 | Extension bulletin | Zilla Slab + Libre Franklin | Two-colour farm bulletin: spot-green header band, black text |
| 3 | Field desk | Barlow Semi Condensed + Barlow | Quiet GIS workstation: solid warm graphite, survey-yellow actions |

`window.__map` (MapLibre) and `window.__app.setT(t)` are exposed for scripted screenshots.

## Structure

```
src/api.ts                    only data seam: API -> repo file bridge -> bundled mock, with per-part provenance
vite.config.ts                dev-only /repo/ bridge (allow-listed backend output files the API had no route for)
src/components/ui/            field panel + pick list (Options.tsx); farmer wording helpers, answers, soil, record (shared.tsx)
src/themes.css                theme tokens (?theme=1|2|3)
src/components/brief/         printable rotation brief (from variant C), fed from the strategies
src/components/year/          "Your field's year" (B's version, isolated: swap this folder for the redesign)
src/components/compare/       "Compare rotations" (B's version, isolated: swap this folder for the redesign)
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
| **Mock** | SMAP and GRACE slabs + Trends panel, ET ("Water use" metric), risk ticks, ML detector (the toggle shows the rule output), water district/stations/events text, Story chapters |

If an API route is missing, `api.ts` reads the documented output file through `/repo/` and labels it "Live · file".

## API routes still needed

- `GET .../trends` with real SMAP root-zone percentile and GRACE groundwater percentile at 10-day steps for the slabs. Today they are fixtures because Earthdata is blocked. The real `heatwave_days` and `precip_anomaly` layers are not wired into the Trends panel yet.
- A risk-days series per 10-day step (heavy rain, frost, heat, dry) for the year-sheet ticks. `daily` has the inputs.
- ML detector cover classes (`models` / `features/weekly`) to make the Rule/ML toggle real.
- Soil texture split (`texture_detail`) and `ec_ds_per_m` in `location.soil`, so the bridge can be dropped.
- `dwr_unique_id` in `location` (shown as the field ID). Today it is read from `backend/field/polygons/<id>.geojson`.
- Brief text: `brief.why` / `brief.evidence` are empty in the engine output. The brief fills in template sentences built from the engine's numbers and labels them "template".

