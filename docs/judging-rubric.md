# Judging rubric: where Field Shift stands

The judging sheet scores five criteria, 1–5 each, 25 total. This file quotes each criterion, says honestly where the project is today (14 Nov 2026), and lists what would raise the score. Update it as gaps close. Every agent or teammate building a screen, a data chunk, a slide or the video should check their work against the criterion it serves.

## 1. Impact
> What is the project's potential for significant impact in both quality and quantity? Does it address a major problem or a minor one? To what extent does it inspire or help others?

**Where we are**
- The problem is real and documented with sources:
  - BC's 2023 order stopping about 398 licence holders irrigating forage, and the 2021 Sumas flood.
  - Colusa rice planting down 84% in the 2022 drought.
  - $248M in Colusa rice crop-insurance payouts 2010–2024, 84% of it for drought or failed irrigation supply (USDA RMA, in `backend/ground/out/`).
  - The Tulare Lake subbasin on groundwater probation since 2024.
- It helps a grower and adviser make a real decision: what to plant in the open window, and how much thirsty acreage to keep under a water limit.

**Gaps**
- **Quantity:** no sourced number yet for how many fields, acres or growers the tool could serve. Candidates: California rice acres and Kings/Tulare alfalfa and silage acres from NASS, and the number of growers in SGMA-critical basins. Source them; don't estimate.
- **Inspiration:** the farmer story (Rosa in Colusa, Miguel in Kings) is in the spec but not yet on screen or in a slide.
- **Reach:** say plainly how it would extend to BC and beyond, and what that needs (ground data), without overclaiming.

## 2. Creativity
> How well does the project demonstrate originality and innovation in its approach? Does it introduce a novel concept that has not been attempted before, or present an improvement upon existing ideas in a meaningful way? To what extent does the level of creativity distinguish it from conventional methods, showcasing a fresh perspective or inventive execution?

**Where we are.** Distinct ideas, each already built or half-built:
- **Exposure:** days when the field is bare *and* bad weather hits, instead of "risk" in general.
- **The 3D stack:** surface, then soil moisture, then groundwater under one field, with each satellite's real pixel size drawn to scale.
- **Rule vs machine learning on the same calendar,** tested on the 2022 drought year, with where each fails.
- **Satellite vs news:** the satellite signal set beside dated headlines.
- **Satellite vs ground:** NASA data checked against stations and measured field water use on the same screen.

**Gaps**
- No single sentence yet that names the novel concept. Draft: "It shows when your field is bare and exposed, what that will cost in water and soil under each rotation, and how sure we are, checked against the ground."
- The existing-tools table (spec A4) should become one slide.

## 3. Validity
> Does the project present a method that is grounded in scientific principles? Does it demonstrate technical feasibility? How effectively would it achieve its intended purpose in real-world applications? How usable or user-friendly is the project? To what extent does this influence its practicality and accessibility?

**Where we are**
- Every number carries a source, and each backend chunk has a check script.
- FAO-56 crop water method; real Cropland Data Layer labels; an honest machine-learning test with 2022 held out and fields held out.
- POWER compared against NOAA stations.
- A working app that runs on real data.

**Gaps (most important first)**
1. **Measured-water check: done (14 Nov).** On years the baseline crop was actually grown, our FAO-56 estimate runs +16% above OpenET for Colusa rice and +21% for Kings alfalfa, inside the ±25% target and on the high side as expected for a fully watered crop. Nothing was fitted to OpenET. Details in `backend/engine/README.md` ("Validation against OpenET").
2. **POWER runs hot and wet** compared with the stations: about +3.5 °C summer highs, 54–68% more rain, and 51 vs 12–30 days at or above 40 °C at Colusa in 2022. Heat-day and rain counts must use stations or show both sources.
3. **Scoring-formula problems: fixed (14 Nov), one honest exception** (`backend/engine/README.md`, "Scoring fixes"):
   - Erosion is now relative to today's rotation: today scores 50, and worse rotations score below 50 instead of being clamped (Kings break year 41, rice-wheat 49.6).
   - Pest-break counts extra years out of today's crop, using UC IPM's "3- to 4-year nonhost rotation" rule of thumb. Continuous rice and alfalfa score 0, and rotations out of them score above 0.
   - The rice-then-wheat bare days were checked and are real: an 11-month fallow after the wheat harvest, not a bug.
   - Forage no longer penalises one-cut silage, and rating and yield ranges now widen the score ranges.
   - **Still open:** with FAO-56 coefficients and our calendar, sorghum-sudan uses slightly more water than silage corn (720 vs 708 mm), because it is in the field longer. We say so rather than adjust it. The spec's "lower water" claim is uncited.
4. **Machine-learning accuracy is inflated at Colusa:** about 99%, mostly because the models learned how the labels were made. Quote the Kings result (83%, below target) and the comparison against the simple rule instead.
5. **Usability is unproven.** The farmer-first panel is new; the printable brief is still jargon. A 10-minute session with a real grower or farm adviser (UC Cooperative Extension, NRCS, an irrigation district) would be the strongest evidence here.

## 4. Relevance
> Does this project fully and directly address the challenge for which it was submitted, demonstrating a strong alignment with the intended objectives? How meaningfully does it integrate NASA data, utilizing it as a core component of the proposed method rather than a superficial addition? The depth of engagement with the data enhances the project's credibility and effectiveness.

**Where we are**
- **Covers the brief's asks** (`docs/brief-coverage.md`):
  - at least 3 rotations compared with today's;
  - the six farmer priorities;
  - bare periods;
  - AI or statistical approaches compared;
  - uncertainty shown;
  - maps and timelines.
- **NASA data in use today:**
  - NASA POWER;
  - Landsat (NASA/USGS).

**Gaps (biggest risk on the sheet)**
- **Live NASA data is still thin.** Most of the field imagery is Sentinel-2 (ESA), and SMAP, GPM IMERG, GRACE, MODIS, ECOSTRESS, HLS and OPERA are all blocked on the Earthdata login. The 3D stack's soil-moisture and groundwater layers are still example numbers. **Getting the Earthdata login is the single most valuable step for this criterion.**
- **No-login NASA data we can add now:**
  - NASADEM elevation from Microsoft Planetary Computer, for slope and low spots.
  - HLS (NASA's harmonised Landsat-Sentinel product) where an anonymous mirror exists.
  - ISS astronaut photographs of the two areas from NASA's Gateway to Astronaut Photography of Earth. Two NASA judges work with this collection.
- **Make NASA data the core of each screen** (exposure, the 3D stack, the calendar), and name the dataset in each screen's source line.

## 5. Presentation
> How effectively did the team communicate their project? How clearly did they convey the challenge, their proposed method, and its significance? How engaging and well-structured was the storytelling? How did the clarity, organization, and delivery of their presentation play a role in making their ideas compelling and accessible, ensuring the audience understood the project's purpose and impact?

**Where we are**
- A pitch outline and 7-slide plan (`docs/field-shift-plan.md` section 6).
- Strong real material:
  - the BC opener;
  - the 2022 drought and 2023 flood at the same Colusa field;
  - the satellite-vs-news story mode;
  - the "Two hard years" Year design.
- The app's plain-language rewrite helps.

**Gaps**
- **Not built yet:** no slides, no 30-second video, no demo script tied to the actual app screens.
- **The printable brief** still reads as adviser jargon.
- **Rehearsal:** time the demo and rehearse it at least three times; record a backup video of the demo in case the live one fails.

## Top actions by points at stake
1. **Earthdata login, then run `backend/nasa`:** relevance and validity.
2. ~~OpenET key~~ done: model within +16% / +21% of measured water use. Fix the CIMIS key next for the station ET check.
3. **NASADEM, HLS and ISS photos without a login:** relevance and creativity.
4. **Settle and fix the scoring-formula problems:** validity.
5. **Show the app to one real grower or adviser and note what confused them:** validity and impact.
6. **Source the "how many acres and growers" number:** impact.
7. **Build the slides, the 30-second video and the demo script from the chosen screens:** presentation.
