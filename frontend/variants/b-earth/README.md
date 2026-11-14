# Field Shift: variant B, "Earth explorer"

Design prototype modelled on Google Earth (web) and the satellite / immersive view in Google Maps. It shows full-bleed satellite imagery with dark floating panels, a left icon rail, a search pill, a layers drawer, a timelapse-style timeline for 2016–2025, and a 3D "exploded layer stack" when you scroll into a field.

## Run

```bash
npm install
npm run dev          # http://localhost:5172 (strictPort)
npm run typecheck
npm run mock         # regenerate src/mock/*.json (deterministic)
```

Screenshots (1440x900, headless Chrome with SwiftShader WebGL). The script starts the dev server if it is not already running:

```bash
node ../../../design/tools/shoot-b.mjs            # all six
node ../../../design/tools/shoot-b.mjs b-03       # just one
```

`window.__map` exposes the MapLibre map so camera moves can be scripted.

## Structure

```
scripts/gen-mock.mjs     builds src/mock/*.json from the spec (B1, B3): real events, dates, URLs and rotation names; illustrative numbers
src/api.ts               the only data seam; each function is named after the spec B3 route it will call
src/types.ts             B3-shaped types (Location, RotationStrategy, NewsItem, SourcedNumber ...)
src/lib.ts               time index (10-day steps), colour ramps, per-cell state, dual units, tie rule (B4.12)
src/MapView.tsx          MapLibre: Esri imagery + OpenFreeMap labels, field outlines, pixel footprints,
                         fill-extrusion layer stack (HLS cells / SMAP slab / GRACE slab), wheel-driven tilt, slab labels
src/App.tsx              shell: rail, search, chips, panel routing, drill-down HUD, map controls
src/components/
  Timeline.tsx           bottom scrubber with event markers; expands into "Your field's year"
  Panels.tsx             knowledge card, Fields list + "Why not BC yet", Layers drawer, Trends, Brief preview
  Compare.tsx            baseline + 3 rotations, range bars, tie badges, irrigation need vs allocation, 2022/2023 replay
  Story.tsx              "Satellite saw vs news reported" story mode
src/mock/*.json          locations, cells (30 m grid), calendar, regional series, strategies, news, datasets, bc, story
```

## How the 3D drill-down works

The Central Valley is flat, so all height comes from data. When a field is selected and you scroll in past zoom ~12.5 near it, the camera tilts (to 58°) in step with the zoom. Three `fill-extrusion` layers spread apart through zoom-interpolated `base`/`height` values:

- top: 30 m HLS cells, coloured by cover class (or ET) for the scrubber date; height is NDVI (or ET);
- middle: one translucent slab for the SMAP 9 km root-zone moisture percentile;
- bottom: one slab for the GRACE groundwater percentile (no data during the 2017–18 mission gap).

HTML callouts are projected at each slab's altitude. Moving the timeline rebuilds the stack: in 2022 the field is bare and dry, and in January 2023 it is water.

## Data honesty

Every number in `src/mock` is illustrative and the UI carries a "Mock data" badge. The events, dates, rotation names, FAO-56 references and source URLs are copied from `planner-spec.md`. Unverified items stay marked (U) or "unverified" in the UI.
