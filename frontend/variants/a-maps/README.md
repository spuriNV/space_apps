# Field Shift: design variant A, "Maps classic"

A Google-Maps-style front end for Field Shift: a light streets map, a search pill with category chips, fields treated as "places" with a left place card, and a 3D drill-down where the field's 30 m cells rise as you scroll in.

## Run

```bash
npm install
npm run dev          # http://127.0.0.1:5171 (strictPort)
npm run mock         # regenerate src/mock/*.json (illustrative data)
npx tsc --noEmit     # type check
```

Screenshots (the dev server must be running):

```bash
cd ../../../design/tools && node shoot-a.mjs     # writes design/screenshots/a-0*.png
node shoot-a.mjs --extras /some/dir              # also saves extra states (search, soil layer, BC, Tulare, brief...)
```

Deep links: `#field=car_colusa_rice&tab=compare`, `#field=caf_tulare_forage`, `#field=bc`.
`window.__map` exposes the MapLibre map so camera moves can be scripted.

## Structure

```
scripts/gen-mock.mjs        generates src/mock/*.json (shaped like planner-spec.md B3; numbers illustrative)
src/api.ts                  the only data access layer; each function names the backend route it will call
src/types.ts                B3 types (Location, RotationStrategy, SourcedNumber, NewsItem, ModelReport, ...)
src/App.tsx                 shell: search pill + suggestions, chips, legends, map controls, replay bar, brief dialog
src/components/MapView.tsx  MapLibre map: OpenFreeMap liberty + Esri imagery toggle, pins, field polygons,
                            30 m fill-extrusion cells, SMAP 9 km / MODIS 250 m footprints, SMAP/GRACE trend grid,
                            zoom-driven pitch (transformCameraUpdate) for the drill-down
src/components/PlacePanel.tsx  place card (hero imagery, badges, actions, tabs), Overview, Sources, "Why not BC yet"
src/components/YearTab.tsx  "Your field's year" calendar 2016-2025, rule vs ML toggle, risk ticks, news pins
src/components/CompareTab.tsx  baseline + 3 rotations: range bars, tie rule (B4.12), irrigation need vs allocation
src/util.ts, styles.css     unit conversions, colour ramps, Google-like tokens
```

## Data honesty

Every field-level number is mock data (a "Mock data" badge is always visible). Rotation names, calendars, dates, events and URLs come from `planner-spec.md`. Unverified items are labelled "unverified" or "(U)".
