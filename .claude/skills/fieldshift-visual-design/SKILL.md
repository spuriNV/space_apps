---
name: fieldshift-visual-design
description: Design language and farmer-first content rules for CropLytics (the California crop-rotation planner built for the NASA Space Apps challenge "Field Shift"). Use whenever anyone builds, restyles or reviews CropLytics UI (frontend/app, design variants, map overlays, the field panel), charts, the printable rotation brief, judges pages or slides, or writes labels, units and copy for them. Covers typefaces, palette tokens, text over satellite imagery, units and sources, data status, and the AI-default patterns to avoid.
---

# CropLytics visual design

One look only: the "Extension bulletin" style: paper panels, slab headings, black ink and one spot green used as ink
(a 3px band under the top bar, the one primary button, links, the focus ring), never as a large fill. Controls are
rounded and calm; text, data and map marks stay crisp like print. There are no theme options and no `?theme=` switch on
the web. The native apps may follow the OS dark mode with the dark tokens in section 3.

**The user's verdict (Nov 2026), which wins over anything below:** square 2px buttons, the dark-green header slab and
solid-green selected states felt "flat, boring, square and bad", and the app had no motion. Never bring them back.
Controls are pills, panels are rounded floating cards, selection is a pale tonal fill, and every panel, sheet and
reading moves with purpose (section 6, Motion).

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
- **Order of a field view:** what this field is -> a visual summary (thumbnail, season strip, small bars) -> 4 answers for the viewing date -> what you
  can do next (normal buttons, the grower's words: "See this field's past 10 years", "Compare
  other rotations", "Print a summary for your adviser") -> about the field (soil, water, salt,
  when it is usually bare) -> crops grown -> what happened here -> "Where every number comes
  from" (collapsed).
- **Overview is a pick list a grower recognises**, not an attribute table.
- **One fact once.** Say a fact in one place (not a headline, a sentence and a note). A number gets its unit and nothing
  else ("1.9 in since 1 Oct. Normal: 3.0 in."). Hints, ranges and sources go behind More detail. No sentence over about
  12 words in the farmer default; More detail teasers are about three words ("Outlooks, reservoirs, every rotation").
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

- **Extension bulletin:** paper `#f7f6f0` (`--panel`), sunken paper `#efeee7` (`--panel-2`), white `#ffffff` for the one
  card per screen (`--raised`), black ink `#191c16`, one spot green `#2f5d34` (`--accent`), brown `#8a5a00` only for
  "example numbers" and "over the limit", red `#a12a1c` for problems.
- **Green has three strengths, one job each:**
  - filled `--accent` = the single primary action on a panel ("Print for your adviser");
  - tonal `--accent-container` `#e3ecdd` with `--on-accent-container` `#1d3a21` text = **selected** (filter chip on,
    current field row, active phone tab, an open top-bar control, the picked month or quick date, the chosen Compare
    option) and secondary buttons;
  - green text or a 2px green ring = links and keyboard focus. The 3px band under the top bar is the only green band.
  Never use solid green as a selected state, a panel or sheet header, a sheet handle or a segmented-control thumb.
- **States are ink layers:** hover = ink at 5% over the element's own fill, pressed = 10%, pressed on an already tinted
  fill = 14%. Focus-visible = `0 0 0 2px var(--panel), 0 0 0 4px var(--accent)` on every interactive element; never
  `outline: none` without a replacement.
- **Single-choice controls** (segmented: Typical / Dry / Wet year, Low / Medium / High, Rule / Model) show the choice
  with a raised white thumb (`--raised` + `--e1`) on a `--panel-2` track, not with green. Use `components/ui/Seg.tsx`
  (radio group, arrow keys).
- **Dark tokens** (native apps only, for now): panel `#171a15`, panel-2 `#20241d`, raised `#23281f`, ink `#ecebe3`,
  muted `#a3a69a`, accent `#9fcb9b` (ink on it `#10260f`), container `#2b3f2b` / `#cfe6c9`, warn `#e0b04a`,
  bad `#f08a7a`. Data colours do not change.
- **Data colours are fixed** (`lib.ts`): bare soil `#a8703f`, partial `#b7d77a`, covered `#2f9e4b`, water `#3d97e8`, no clear
  view = hatched grey. Soil texture (`SOIL_COLOR`): sand `#d9b46a`, silt `#e9e3d3`, clay `#7a4a2b`. Crop record: rice blue, alfalfa green, corn yellow, fallow tan. Never reuse a data colour for chrome.
- **Contrast:** body text >= 7:1 on its panel, muted text >= 4.5:1 (muted 6.1:1; example-data brown 5.6:1). Never put text
  straight on imagery: map labels sit in a solid paper label box with a 1px ink border and a 1-2px shadow. Field selection on
  imagery is yellow `#ffd166` corner ticks with a dark drop shadow; footprints are dashed outlines, not fills.
  Non-text boundaries that carry meaning (chip outline `#84877d`, check icon `#5f8a5c`, focus ring) are at least 3:1.
  Selected states never rely on colour alone: chips add a check icon, the current row adds a ring on its thumbnail, the
  active phone tab adds a pill.

## 4. Labels, units and sources

- Headings: sentence case, heading face, 22px (`--fs-head`). No eyebrow above a heading. If a group needs
  a name, the heading is the name.
- Label/value rows: label in `--muted` at the left, value in `--text`. Units always shown.
- Dates in the grower's terms: "mid July 2023", "16 Apr 2024". Avoid dekad, DOY, ISO.
- Every answer has one `cite` line (shown under More detail): the instrument in plain words ("NASA GRACE-FO"). Scale in miles, method and caveats go on the Sources sheet.
- Maps: say what a footprint means ("Soil moisture: one reading covers this square"), not "pixel".

## 5. Data status and uncertainty, without badge soup

- Live data carries no status word. Example data is flagged in words, not a pill: "Example numbers." in italics, the warn
  colour and a small hatched square with 2px corners (`.status.example`); model estimates say "Estimated." in italics in
  `--muted` with a dashed square (`.status.estimate`). Hatching = "not measured" across the product, as on the season
  strips. When the whole server is down, one `.notice` (warn-container fill, 12px corners) says so once per panel.
- No global live/example indicator and no status word on every source line. Sources live on one "Sources" sheet (link at
  the bottom of the field panel), grouped NASA / other satellites / ground data / models, one line each. Only a part that is
  genuinely missing says so, once, where it is used ("water district not looked up yet").
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

## 5b. Farmer default, adviser detail

- Each screen opens on the decision: Field now = visual summary + 5 short answers (what's growing, rain vs normal, water
  need vs limit, soil and groundwater, what the soil is like: sand/silt/clay bar, three plain facts, one rotation sentence); Coming season = 3 sentences (winter rain, water supply, next season's need); Compare =
  today vs the top 2 alternatives in acre-feet and days.
- Everything else (NASA list and sources, ML comparison, stress weeks, standing water, 3D, percentiles and ranges, glossary,
  insurance, earlier years, every rotation, priorities and what-ifs) sits behind one inline "More detail" disclosure at the
  end of the screen, remembered for the session (`components/ui/Detail.tsx`, class `.d-only`).
- Each answer renders as soon as its own data arrives: a thin skeleton line while loading, "Not available right now" after a
  timeout. Never one loading box for the whole panel.

## 5c. Phone (up to 640 px)

Top bar = wordmark, field switcher, menu (date control and map layers inside). Sections become a bottom tab bar (64px;
the active tab gets a 32px tonal pill behind its label). The field panel is a non-modal paper bottom sheet over a live
map: 20px top corners, a 36x4 grey grabber (not a green bar), snap points peek 128px (name and facts), half 52% (plus a
sideways row of action pills, primary first) and full. It follows the finger by transform only; on release it goes to the
nearest snap point, or to the next one in the direction of a fling faster than 0.5 px/ms, with a 320ms iOS drawer curve;
tap the grabber to cycle, arrow keys on it step. Below full, a drag anywhere on the sheet moves the sheet; at full the
content scrolls. The map's bottom inset follows the sheet. Wide sheets become full-screen pages between the bars, one
column. Touch targets at least 44 px (visual 36-40px controls grow their hit area); nothing scrolls sideways except
inside a table, the filter-chip row and the sheet's action row.

## 6. Density, shape, iconography

- Solid panels (`--panel`), no blur/glass, no border on floating panels (the shadow is the edge).
- **Radius scale** (tokens `--r-*`): 4 strips, swatches, status squares (2-3); 8 thumbnails, event rows, tooltips;
  12 cards, list rows, the More detail row, notices, menu items; 16 floating panels, popovers, menus; 20 the phone
  sheet's top corners; full (pill) for buttons, chips, segmented controls, the search field, icon buttons, the top-bar
  date and Map layers controls and the phone tab indicator. Square (0-4px) stays for map label boxes, field-selection
  ticks, data cells and the printable brief. Rule of thumb: rounded where the grower touches, crisp where they read.
- **Elevation** (tokens `--e*`, shadow colour = ink, never pure black): `--e1` the one card per screen and the
  segmented thumb; `--e2` a panel over the map; `--e3` menus, pickers and the date banner; `--e-sheet` the phone sheet;
  `--e-stuck` a sticky header or footer once content scrolls under it.
- **Separation:** sections are separated by 24px of space, not by rules. Hairlines (ink 14%) only between answer rows,
  fact rows and list rows where the eye tracks across. No 2px ink rules in panels, no dashed boxes, no side stripes.
- **Type scale** (tokens at the top of `styles.css`; components use the tokens, not literal sizes):
  `--fs-fine` 13px (floor: source lines, chart ticks, map scale and labels, legends), `--fs-small` 14.5px (labels,
  meter notes, secondary lines), `--fs-body` 16px (body, rows, buttons, tabs; also stops iOS zooming on inputs),
  `--fs-answer` 20px (Zilla Slab 600: the answer sentence, option names), `--fs-head` 22px (section and sheet headings),
  `--fs-title` 28px (field name in the panel, sheet titles, wordmark). **Nothing below 13px** on screen, including SVG
  chart text and MapLibre label layers. Only the printable brief keeps its own print sizes (one Letter page).
- Widths that go with it: field panel and pick list about 460px (max 46vw); Compare drops to two columns below
  1280px wide (water against the limit moves under Gain / Give up); Coming season's three summary cells stack below
  1180px; the top bar shortens tab labels below 1500px and 1300px. On a phone (390px) nothing scrolls sideways and
  every touch target is at least 44px.
- Rows separated by hairlines, not cards in cards.
- **Navigation is a top bar, not an icon rail.** Wordmark "CropLytics" at the left (heading face, spot green), then a field
  switcher (county and acres small, field name in the heading face; click to change or search), then the sections as text tabs
  (Field now, Coming season, This field's year, Compare, Print for your adviser; the active tab gets a 3px spot-green underline),
  then the "Viewing" date control (quick picks and a month picker; whenever the date is not today a floating pill under
  the bar, centred over the map, says "Showing Jul 2022" with a tonal "Back to today" button; it never sits under the bar
  and hides while a wide sheet is open) and "Map layers" at the right. There is no bottom timeline: the year strips, events and the
  replay live on the "This field's year" tab, and the map, panels and 3D view use the full height. The bar is solid paper with a hairline bottom rule, a 3px
  spot-green band under it and a soft two-step shadow so it sits above the map. No stacked icon+label buttons, no flat grey slab.
- Icons: the existing line set in `Icons.tsx`, 16-20px, only next to a text label (map layers, play, close, zoom).
  Logo is the wordmark "CropLytics" in the heading face; no initials tile, no gradient.
- **Buttons** are pills, 44px tall (36px "small" with a 44px hit area), label 16px Libre Franklin 600, sentence case,
  the grower's words, press = `scale(0.97)`. Four kinds only: primary (filled green, one per panel: "Print for your
  adviser"), secondary (tonal green: the other next steps on a phone, "Back to today"), outline (neutral: "Show all",
  dialogs), text (green text: "Sources", "Look under the field in 3D", "What's this?"). Icon buttons are 40px circles
  with a faint ink disc (close, play). An icon is 18-20px and sits before a label, never stacked above it.
- **Next steps** in the field panel: the footer holds only the primary pill, full width. The other three ("What's
  likely this winter", "This field's year", "Compare rotations") are tappable rows with a chevron, title only, grouped on
  `--panel-2` after the answers and before More detail. Never a 2x2 block of buttons at the bottom of the panel (the
  user called it out). On a phone they are one sideways pill row under the sheet header, primary first.
- **Filter chips** are 36px pills with a 1px outline; selected = tonal fill + leading check icon, never solid green.
  Counts stay on the same line in a lighter weight. Header facts (acres, crop with its record swatch, county) are quiet
  28px neutral chips on `--panel-2`, not pressable and never tonal green.
- **List rows** (pick list, events, next steps) are 12px-corner rows with a flat ink hover; the current field gets the
  tonal fill and a ring on its thumbnail. No lift-on-hover, no shadows on rows. Chevron at the right only for things
  that open a view.
- **Panel header** is paper, not green: field name (heading face, 28px; 22px on a phone), close icon button, a row of
  fact chips, one id line. It scrolls with the content; once the name passes under the top, a one-line 20px title bar
  with a soft edge fades in (opacity and transform, no font-size or height animation).
- **More detail** is a full-width 12px-corner row on `--panel-2` with the label in green, the three-word teaser in
  muted text and a chevron that turns when open; the field panel's detail opens with a height and fade.
- **Motion** (Emil Kowalski's rules; tokens `--dur-*`, `--ease-*` in `styles.css`): every motion has a job (where a
  panel came from, what changed, that a press registered). 120ms hover and press colour, 160ms press scale, 180ms
  selection (chip check, segmented thumb, chevron), 240ms title bar and detail fade, 320ms panel entry, More detail
  height and sheet snaps. Enter with a strong ease-out (`--ease-enter` `cubic-bezier(0.23,1,0.32,1)` or `--ease-out`),
  never ease-in; the phone sheet uses the iOS drawer curve (`--ease-drawer`). Panels slide 12-14px and fade from their
  side (never from scale 0); switching fields cross-fades the panel content; readings count up once when they first
  appear and glide when the date changes; meter fills and soil/groundwater dots move by `transform`; loading is a
  shimmer that moves by `transform`; the picked map pin gives one short bounce; camera flights ease in and out.
  Animate only opacity and transform (colour and shadow for states); no `transition: all`; hover styles only inside
  `@media (hover: hover) and (pointer: fine)`; nothing animates on keyboard-repeated actions; everything collapses to
  1ms under `prefers-reduced-motion` (MapLibre then jumps instead of flying). No bounce on panels, no parallax, no
  decorative loops.

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
10. Cards inside cards; side-stripe accent cards; 24px+ radii on boxes (pills on buttons and chips are fine); solid
    brand-colour fills as a selected state; square 2px buttons and chips; controls with no hover, pressed or focus state;
    a solid green header slab; UI that appears or changes with no motion at all, or motion with no job.
11. Warm beige "tasteful" background picked by default (paper colours here are neutral and argued).
12. Invented precision or invented metrics; numbers without units or meaning.

## Where things are

- Tokens: top of `frontend/app/src/styles.css`. One look; no theme switch.
- Field panel and pick list: `frontend/app/src/components/ui/Options.tsx`, `FieldNow.tsx`, `NasaSection.tsx`, `shared.tsx`.
- Screenshots: `node design/tools/shoot-app.mjs [overview|field-now|kings|coming-season|year|compare|brief|drilldown|phone]`
  (APP_URL=... to shoot a dev server that is already running; OUT_DIR=... to write elsewhere). `motion` records
  `design/screenshots/app/panel-motion.webm` (panel entry, field switch, title collapse, More detail).
- Rounded controls, tonal selection and motion: the "Redesign, Nov 2026" block at the end of `styles.css`; spec and
  reasons in `docs/ui-redesign-spec.md`, tokens and component CSS with every state in `docs/ui-redesign/mock/`.
  Segmented control: `components/ui/Seg.tsx`; count-up and reduced-motion check: `components/ui/motion.tsx`.
- Native mapping (Compose `colorScheme` roles, `Shapes`, SwiftUI assets, sheet detents): `docs/ui-redesign-spec.md` section 3.8.
- Tap anywhere (`pt_` ids, `api.analyzeSpot`, `components/ui/FieldNow.tsx` spot mode): a tap, click or long-press on open
  map drops a pin and opens the field panel at once with skeletons, labelled "Tapped spot · live data". Only `ready`
  sections show data; `not_computed` parts are hidden (no example numbers borrowed); `unavailable` gets one quiet line.
  A 200 m square says so on the map and in the id line; non-farmland gets one notice. `#spot=<id>` links reopen it.
