---
name: fieldshift-visual-design
description: Design language and farmer-first content rules for CropLytics (the California crop-rotation planner built for the NASA Space Apps challenge "Field Shift"). Use whenever anyone builds, restyles or reviews CropLytics UI (frontend/app, design variants, map overlays, the field panel), charts, the printable rotation brief, judges pages or slides, or writes labels, units and copy for them. Covers typefaces, palette tokens, text over satellite imagery, units and sources, data status, and the AI-default patterns to avoid.
---

# CropLytics visual design

One look only: the "Extension bulletin" style (spot-green header band, slab headings, paper panel). There are no theme options and no `?theme=` switch.

CropLytics is used by California growers and their advisers. The reader knows their ground,
their crop, their water allocation and their town. They do not know NDVI, SMAP, GRACE or
percentile maths. Real tools they trust (John Deere Operations Center, FieldView, CropX,
CIMIS, Web Soil Survey, irrigation-district letters, a USGS quad) speak in fields, acres,
inches and acre-feet. CropLytics should feel like it belongs on that shelf, made by people
who print maps, not like a generated dashboard. Sources: `references.md`.

## 1. Farmer-first content (do this before any styling)

- **Name things the way the grower does.** A field is "Alfalfa field 6 miles south of Hanford",
  then "73 acres, alfalfa in 2025, Kings County". The DWR / Land IQ ID and coordinates are small
  secondary text ("State field no. 1603054"). Helpers: `fieldName`, `nearTown`, `acres`,
  `latestCrop`, `cropName` in `frontend/app/src/components/ui/shared.tsx`.
- **Answer questions in sentences.** Section content is a question the grower would ask and a
  plain answer: "Is the soil wetter or drier than usual?" -> "Wetter than usual for mid July".
  "How much water does the current rotation need?" -> "About 4.1 acre-feet per acre a year.
  Your limit is 3.0, so 1.1 short."
- **Never a bare number.** Every number says what it means: "84th percentile (100 = wettest mid
  July since 2015)", "Greenness 0.84 (0 to 1; above 0.6 is a full canopy)".
- **Grower units first, metric second if at all:** acres, inches, inches per foot of soil,
  acre-feet per acre, °F, miles. Hectares, mm and km go in the source line or a tooltip.
- **Instruments go in the source line, not the heading.** Satellite name, pixel size, method and
  data status sit in one small `cite` line under the answer: "SMAP satellite, one 6-mile square
  around the field. Example numbers, not live yet." Translate pixel sizes to miles.
- **Order of a field view:** what this field is -> 3-4 answers for the timeline date -> what you
  can do next (normal buttons, the grower's words: "See this field's past 10 years", "Compare
  other rotations", "Print a summary for your adviser") -> about the field (soil, water, salt,
  when it is usually bare) -> crops grown -> what happened here -> "Where every number comes
  from" (collapsed).
- **Overview is a pick list a grower recognises**, not an attribute table.
- **10-second test** for every screen: write what a grower who has never seen the app would
  understand in 10 seconds. If the answer needs a dataset name, rewrite the screen.
- Copy: sentence case everywhere; plain verbs; no em dashes in UI copy; no marketing words.

## 2. Typefaces (SIL OFL, Google Fonts)

| Use | Face | Why |
|---|---|---|
| Headings, place names, answers | Zilla Slab 500/600 | Slab like the farm bulletins, seed lists and county newspapers growers already read |
| UI, data, source lines | Libre Franklin 400/600/700 | Franklin Gothic, the workhorse of farm print; base of USWDS Public Sans |

Fallbacks: Zilla Slab -> Rockwell, Georgia; Libre Franklin -> Franklin Gothic Book, Arial.
Never a monospace for labels; use `font-variant-numeric: tabular-nums lining-nums` for columns of numbers.
Avoid the default-attractor faces: Inter, Geist, Space Grotesk, IBM Plex, Instrument Serif, Roboto/Google Sans, any mono.

## 3. Palette: two-colour print, not "tech"

Tokens live at the top of `frontend/app/src/styles.css` (`--panel`, `--panel-2`, `--head-band`, `--text`, `--text-2`, `--muted`,
`--line`, `--accent`, `--link`, `--good`, `--warn`, `--bad`, `--mark`, `--font-ui`, `--font-head`). Components read tokens only;
no hex in components except data colours.

- **Extension bulletin:** paper `#f7f6f0`, black ink `#191c16`, one spot green `#2f5d34` (header band, primary action, links,
  "live"), brown `#8a5a00` only for "example numbers" and "over the limit", red `#a12a1c` for problems.
- **Data colours are fixed** (`lib.ts`): bare soil `#a8703f`, partial `#b7d77a`, covered `#2f9e4b`, water `#3d97e8`, no clear
  view = hatched grey. Crop record: rice blue, alfalfa green, corn yellow, fallow tan. Never reuse a data colour for chrome.
- **Contrast:** body text >= 7:1 on its panel, muted text >= 4.5:1 (muted 6.1:1; example-data brown 5.6:1). Never put text
  straight on imagery: map labels sit in a solid paper label box with a 1px ink border and a 1-2px shadow. Field selection on
  imagery is yellow `#ffd166` corner ticks with a dark drop shadow; footprints are dashed outlines, not fills.

## 4. Labels, units and sources

- Headings: sentence case, heading face, 15-17px. No eyebrow above a heading. If a group needs
  a name, the heading is the name.
- Label/value rows: label in `--muted` at the left, value in `--text`. Units always shown.
- Dates in the grower's terms: "mid July 2023", "16 Apr 2024". Avoid dekad, DOY, ISO.
- Every answer has one `cite` line: instrument in plain words + scale in miles + status.
- Maps: say what a footprint means ("Soil moisture: one reading covers this square"), not "pixel".

## 5. Data status and uncertainty, without badge soup

- Status is words at the end of the source line, not a pill: "Live." / "Live, from a saved
  run." / "Example numbers, not live yet." Example data gets italics, the warn colour and a small
  hatched square (hatching = "not measured" across the product, as on the timeline).
- One global indicator top right: "Live data | 2 parts are examples". Clicking it lists sources.
- **NASA first.** Name the NASA source first in every source line (HLS, Landsat, SMAP, GRACE-FO, GPM IMERG, MODIS, ECOSTRESS,
  NASA POWER, NASADEM, ISS), then the others. The field panel has a "NASA data behind this field" list: what each dataset
  tells the grower, its footprint in feet or miles, and whether it is live.
- **One definition per quantity, everywhere.** Bare = satellite greenness below 0.2 and not under water (`src/bare.ts`).
  Hot days = NOAA station highs of 104 °F (40 °C) or more. Today's rotation uses what the satellites saw; alternatives use the
  model, labelled "estimated".
- Example inputs (the water limit) say "example, change to yours" next to the number.
- Jargon a grower may not know gets a small "What's this?" link with a plain explanation (`components/ui/What.tsx`).
- Ranges are words plus numbers: "2.7-4.1 acre-ft/acre", "about 4.1". Show a range bar only when
  comparing options. Do not add a progress bar under a single reading.
- Say when a reading is not about the field: "Whole basin, not your own well."

## 6. Density, shape, iconography

- Solid panels (`--panel`), 1px rules, radius 2-4px, one modest shadow. No blur/glass.
- Dense but readable: 13px body, 12-12.5px secondary, 11.5px source lines, 15-17px answers.
  Rows separated by hairlines, not cards in cards.
- Icons: the existing line set in `Icons.tsx`, 16-20px, always with a text label in the rail.
  Logo is the wordmark "CropLytics" in the heading face; no initials tile, no gradient.
- Actions: full-width rows with a title and one-line description; one primary per panel
  (the printable summary). Chevron at the right only for things that open a view.

## 7. Do not (AI-default patterns)

1. Monospace ALL-CAPS letter-spaced eyebrows ("FIELD DOSSIER", "READOUT") or kickers on every section.
2. Numbered rows or section markers (01 02 03 04, A-G) without a real sequence.
3. Inter / IBM Plex / Geist / Space Grotesk / Google Sans as the one face for everything.
4. Teal or cyan accent on near-black blue slate; neon glows; purple-blue gradients; gradient text.
5. Pill badges for status ("LIVE", "MOCK DATA") repeated on every row.
6. A thin progress/gauge bar under every number, or a hero metric with three small stats.
7. Glassmorphism (backdrop blur + hairline border + big soft shadow) as the default surface.
8. Rounded initials logo tile ("FS") or icon tiles above every heading.
9. Dataset names, pixel sizes or percentiles as the headline instead of the answer.
10. Cards inside cards; side-stripe accent cards; 24px+ radii on small boxes.
11. Warm beige "tasteful" background picked by default (paper colours here are neutral and argued).
12. Invented precision or invented metrics; numbers without units or meaning.

## Where things are

- Tokens: top of `frontend/app/src/styles.css`. One look; no theme switch.
- Field panel and pick list: `frontend/app/src/components/ui/Options.tsx`, `FieldNow.tsx`, `NasaSection.tsx`, `shared.tsx`.
- Screenshots: `node design/tools/shoot-app.mjs [overview|field-now|kings|coming-season|year|compare|brief|drilldown]`
  (APP_URL=... to shoot a dev server that is already running).
