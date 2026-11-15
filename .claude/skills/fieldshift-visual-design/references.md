# References for fieldshift-visual-design

Collected Nov 2026. "Checked" means the point was confirmed on the linked page; "Unconfirmed"
means it is common knowledge we could not confirm in this pass. Treat those as hypotheses.

## Tools growers and advisers use (content and wording)

- **John Deere Operations Center**: organised as Client / Farm / Field; a field card shows dates, acres worked and the machine; crops are assigned per field per season. The grower's vocabulary is field, acres, crop, season. Checked.
  https://www.rands.com/blog/john-deere-operations-center-tm-pre-season-checklist-for-2026 ·
  https://support.koenigequipment.com/understanding-john-deere-operations-center-field-overview
- **Yield-map legends (FieldView, Ops Center, FBN)**: the legend is "the most relevant information"; ag software adds average and range; FBN shows a histogram of how much of the field falls in each class. Checked.
  https://grdc.com.au/resources-and-publications/grdc-update-papers/tab-content/grdc-update-papers/2018/07/how-to-make-use-of-your-yield-maps ·
  https://www.fbn.com/community/faq/how-do-yield-maps-work-in-fbn-maps
- **CropX**: soil moisture shown as a status in plain words (Refill / Optimal / Full) with a recommendation on when and how much to irrigate. Status words beat raw readings. Checked.
  https://cropx.com/cropx-system/irrigation-planning/ ·
  https://pir.sa.gov.au/regions-and-support/programs-and-initiatives/agtech/agtech-solutions/products/cropx
- **CIMIS (California DWR)**: reference ET in inches per day (about 0.3 in/day in July in non-desert sites); crop water use = ETo x Kc. Inches are the grower's unit for water. Checked.
  https://cimis.water.ca.gov/Content/PDF/Irrigation_Scheduling_Using_CIMIS.pdf ·
  https://www.lawr.ucdavis.edu/water-balance-irrigation-scheduling-using-cimis-eto
- **Irrigation districts and GSAs**: allocations are stated in acre-feet per acre. Unconfirmed in this pass (district sites not fetched); consistent with the engine input `allocation_input.unit = acre-ft/acre`.

## Earth-observation and GIS tools (visual language)

- **NASA Worldview / GIBS**: layer list on the left; each colormap carries legend entries with units, a no-data entry and labels for classes; hovering the colour bar shows the value. Checked.
  https://nasa-gibs.github.io/gibs-api-docs/access-advanced-topics/ ·
  https://www.earthdata.nasa.gov/news/feature-articles/layer-layer-nasa-worldview-continues-improve
- **Esri Calcite (ArcGIS Online, Field Maps)**: Avenir Next (Frutiger/Kobayashi), fallback Avenir, Helvetica Neue; quiet neutral panels, one blue for actions. Checked.
  https://developers.arcgis.com/calcite-design-system/foundations/typography ·
  https://developers.arcgis.com/calcite-design-system/foundations/tokens/reference/
- **Copernicus Browser, Planet Explorer, Windy, Felt, USGS EarthExplorer, Web Soil Survey, OpenET**: not fetched in this pass. From use: solid (not blurred) panels, legends next to the layer toggle, sources at the foot. Unconfirmed.

## Printed references

- **USGS topographic map colours**: black = culture and names, brown = contours, blue = water, green = vegetation, red = major roads and land grid, purple = revisions. Used for the ink roles (the earlier "survey sheet" look, now retired). Checked.
  https://www.usgs.gov/ngp-standards-and-specifications/us-topo-map-symbol-guide ·
  https://people.cas.sc.edu/ajames/201/_1.USGS.How2Read/reading.html
- **Ordnance Survey adapted Univers for maps** (tails on l and t to separate lettering from linework): map type is tuned for legibility over detail. Checked.
  https://en.wikipedia.org/wiki/Univers
- **swisstopo national maps**: redesign moved to sans-serif lettering, new colours and symbols; Imhof-style relief shading. Typeface name not confirmed.
  https://www.swisstopo.admin.ch/en/modernisation-of-the-national-maps-2001-2021 · https://mapdesign.icaci.org/?p=1933
- **USDA Farmers' Bulletins and seed catalogues**: free, widely mailed farm print; chromolithography arrived in seed catalogues around 1870. Inspiration for the two-colour print of the one look we kept. Typeface claims (Clarendon, Franklin Gothic) are common knowledge, not confirmed here.
  https://scuablog.lib.vt.edu/2014/09/11/seeds-of-the-past/ ·
  https://eyeondesign.aiga.org/these-gorgeous-19th-century-seed-catalogs-were-a-prescient-form-of-advertising/

## Typefaces chosen

- **Overpass**: interpretation of FHWA Highway Gothic, by Delve Withrington for Red Hat, OFL. https://fonts.google.com/specimen/Overpass/about
- **Barlow**: Jeremy Tribby; shares qualities with California plates, highway signs, buses and trains; OFL; Semi Condensed and Condensed widths. https://fonts.google.com/specimen/Barlow/about
- **Public Sans / Libre Franklin**: USWDS's Public Sans is adapted from Libre Franklin, OFL. https://github.com/uswds/public-sans
- **Source Serif 4**, **Zilla Slab**: OFL on Google Fonts.
- **Atkinson Hyperlegible Next** (Braille Institute, 2025, OFL) was tried and dropped for the slashed zero. https://fontsource.org/fonts/atkinson-hyperlegible-next/about

## What reads as AI-generated (2025-26 design writing)

These are community lists, not studies. Shared tells: Inter everywhere, purple-blue gradients,
uppercase mono eyebrows on every section, "01 / EXAMPLES" numbering, cyan-on-dark, neon glow,
glassmorphism, hairline border + big soft shadow, side-stripe cards, cards in cards, icon tiles,
hero metric blocks, beige "tasteful" default, em-dash-heavy copy, invented metrics.
- https://924b8765.impeccable-2rv.pages.dev/slop (impeccable "visible tells")
- https://instagit.com/Nutlope/hallmark/hallmark-anti-patterns-detected/ (Hallmark anti-pattern catalogue)
- https://www.thefountaininstitute.com/blog/signs-vibe-coded-ui
- https://github.com/Laith0003/ux-skill/wiki/Anti-AI-slop-ban-list
- https://noqta.tn/en/blog/ai-design-slop-overused-ui-patterns-fix-2026

## Controls, selection states and motion (Nov 2026)

The redesign after the user found the square buttons, the green header slab and the solid-green selected states "flat,
boring" and asked for real motion. Spec: `docs/ui-redesign-spec.md` (section 9 has the full notes).
- Material 3 token files (material-web `tokens/versions/v0_192`; androidx compose material3 tokens): corner scale
  4/8/12/16/20/28/full, filter chip selected = secondary container with no outline, segmented 40px full corner, state
  layers 0.08 hover / 0.10 pressed, standard easing (0.2,0,0,1), decelerate (0.05,0.7,0.1,1).
- Apple HIG (buttons, sheets, segmented controls, accessibility): 44pt targets, sheet detents (medium, large, custom),
  non-modal sheets over live content.
- Radix Themes and shadcn/ui new-york-v4: selection as a translucent tint or a raised neutral thumb; brand colour kept
  for the primary action.
- Linear, "Behind the latest design refresh": fewer separators, softer contrast.
- Google Maps place panel and Places UI Kit (250-460px panels): paper header, close in the corner, pill actions, sticky
  compressed title.
- Emil Kowalski, design-engineering and animation skills (emilkowalski/skills: emil-design-eng, animate,
  animation-performance): animate only transform and opacity, strong custom ease-out to enter (0.23,1,0.32,1), iOS
  drawer curve (0.32,0.72,0,1), press scale 0.97, never from scale(0), hover only on hover devices, fling with velocity
  for sheets, reduced motion respected, motion only when it has a job.
- Impeccable (pbakaus/impeccable): critique rubric (cognitive load, Nielsen heuristics) and polish checklist used to
  audit the before state; Taste skill (Leonxlnx/taste-skill) motion and card references.
