# Critical review: how Field Shift would lose points

This is a hostile pre-judging review, done on 14 Nov 2026 against the repo as it stands. Two agents are editing `backend/engine` and `frontend/app` right now, so items marked **(in flux)** may already be moving.

**What was checked:**
- Every backend check, run here:
  - api: ALL PASS, but 5 routes are fixtures;
  - regional: 37 pass, 1 fail;
  - field: 23 pass, 1 fail;
  - engine: 41 pass, 2 fail;
  - ground: ALL PASS (CIMIS skipped);
  - ai: 20 pass, 5 fail;
  - outlook: ALL PASS;
  - nasa: 0 fail, but almost no data;
  - nasa_open: all pass;
  - news: 1 fail.
- The 7 screenshots in `design/screenshots/app/`.
- The app source in `frontend/app/src`.
- Spot checks against `data/cache/`.

**Numbers that do match their raw source:**
- Rain Oct 2024–Sep 2025 is 14.0 in, against a 9-season normal of 17.1 in (82%).
- Mid-July 2025 had 0 days at or above 100 °F.
- OpenET on the CDL rice years averages 1108 mm, and 1112 mm on the alfalfa years.
- Shasta storage is 2.24 MAF of 4.552 MAF, 49% full.
- RMA rice indemnity in Colusa is $247.8M.

The numbers are mostly honest. The problems are what the screens leave out, how old the data is, and how the screens contradict each other.

---

## 1. Predicted score (as it stands tonight)

| Criterion | Score | Why |
|---|---|---|
| Impact | **3** | Real, sourced problem, but the tool works for two hard-coded fields. A grower can't add their own field, the scale is never quantified, and no grower has seen it. |
| Creativity | **3** | Exposure (bare soil × bad weather), the 3D pixel-footprint stack and gain/give-up are fresh. But what's on screen reads as OpenET + CPC outlook + a cover-crop selector, and the novel AI work is invisible. |
| Validity | **3** | Strong method and an honest OpenET check. But the screens disagree on bare days, the data stops in Dec 2025 while the screen says "Today, mid Nov 2026", placeholder scores (pest break 0, market 50) are shown as results, and the printed page contradicts itself. |
| Relevance | **2** | The two pure-NASA layers (SMAP, GRACE) are labelled "example numbers". The coming-season screen is 100% NOAA/CDEC/USDM. NASA POWER is mostly cited as "runs 6 °F hot". The brief's AI section, glossary, scenario sliders, priority inputs and trend maps are not in the app. |
| Presentation | **2** | No slides, no 30-second video, no demo script, no recorded backup. Due Sunday 23:59. The UI itself is clean and would score 4 if a story were wrapped around it. |
| **Total** | **13 / 25** | Realistic ceiling after the must-fix list: about 18–19. |

---

## 2. Must fix before judging (ranked by points at stake)

### 1. SMAP and GRACE are shown as fake numbers (Relevance −1 to −2)

**Evidence:**
- `frontend/app/src/components/ui/FieldNow.tsx:97`: "Example numbers until the NASA Earthdata login is in."
- `MapView.tsx:226,232`: "SMAP satellite · example numbers" and "GRACE-FO satellites · example numbers".
- Screenshot `drilldown-3d.png` shows both tags. The header badge says "4 parts are examples".
- `check_api.py`:
  - `trends?layer=smap_anomaly`, `grace_gw_pct` and `modis_ndvi_anomaly` are `[fixture]`;
  - `/api/bc/signal` and `/api/glossary` are fixtures.
- The login now works:
  - `data/cache/car_colusa_rice/grace.parquet` exists;
  - `imerg.parquet` exists;
  - `dswx.parquet` covers 2016-11 to 2026-11-04;
  - AppEEARS tasks for SMAP L3/L4, MODIS and ECOSTRESS are in `data/cache/_appeears/`.
- But the fetches are stubs:
  - GRACE has 5 rows (Dec 2020–Jan 2021);
  - IMERG has 8 rows (28 Sep–5 Oct 2025).

**Why a judge marks it down:** The 3D stack is the signature visual, and its two NASA layers are made up. A NASA data architect reads "example numbers" and stops trusting the rest.

**Fix:**
- Run the full GRACE-DA 2015–2026 and SMAP L4 fetches tonight, and wire them into `regional` and `/trends`.
- If they aren't in by freeze, delete the SMAP/GRACE slabs and the Field-now soil/groundwater answer rather than show fakes.

### 2. The AI section of the brief is built but not shown (Relevance −1, Creativity −1)

**Evidence:**
- `App.tsx:47`: `const detector = 'rule' as const;`.
- `api.ts:222`: the ML provenance says "not trained yet: toggle shows the rule".
- `backend/ai/out/<id>/calendar_ml.json`, `models.json` and `stress_weekly.json` exist, and the API has an ML calendar route (commit 3dae3de).
- Nothing in the UI shows:
  - rule vs RF vs HGB;
  - the z-score vs isolation-forest stress weeks;
  - any accuracy number.

**Why a judge marks it down:** The brief gives "SI, Modeling and Data Fusion" its own section ("compare different SI or statistical approaches", "highlight seasonal transitions, bare periods and crop stress"). Alex Stoken is an ML judge. Right now the submission has no visible AI.

**Fix:**
- Add a second strip under "This field's year": the ML calendar, with disagreement cells marked.
- Add one "How sure are we" card. Kings RF hits 0.83 accuracy on the 2022 hold-out, below target, against 0.78 for the rule. For Colusa, explain that its 0.99 mostly reflects the label rules.
- Add stress-week dots on the season strip.
- Keep the PLAN wording: "a comparison, not the answer".

### 3. "Today, mid Nov 2026" shows data from Dec 2025 (Validity −1)

**Evidence:**
- `field-now.png`:
  - "Latest clear view late Dec 2025; 2026 imagery not processed yet";
  - "No readings for this winter yet. Last season was… Oct 2024 to Sep 2025".
- `year.png`: 2026 is all hatched.
- The cache already holds 2026:

| Source | Through | 2026 rows |
|---|---|---|
| `s2.parquet` | 2026-11-11 | 75 scenes at Colusa, 72 at Kings |
| `power_nrt.parquet` | 2026-11-11 | |
| `dswx.parquet` | 2026-11-04 | |
| `cdec_2026`, `usdm_2026` | Nov 2026 | |

- The Colusa field's NDVI on 11 Nov 2026 is 0.18; the screen shows 0.21 from Dec 2025.
- `backend/field/out/*/calendar.json` stops at 2025.
- `ncei.parquet` ends 2025-12-31.

**Why a judge marks it down:** The product is "what's happening on my field now" and "what's likely this coming season". Showing the 2025 water year as "last season" in Nov 2026 is wrong; it skips water year 2026. Any judge who reads the date will notice.

**Fix:**
- Re-run the backend/field calendar for 2026 from the cached S2 and Landsat.
- Re-fetch GHCN-D through Nov 2026, falling back to POWER NRT and labelling it.
- Then rain-so-far becomes "since 1 Oct 2026" and "last season" becomes water year 2026.

### 4. Nothing to submit yet (Presentation −2)

**Evidence:**
- No slides, video or demo script anywhere in the repo.
- `docs/judging-rubric.md` §5 admits this.
- The PLAN pitch relies on "story mode", but `components/Story.tsx` is not mounted in `App.tsx`.

**Fix:**
- Make the 7 slides from the existing screenshots. Order:
  1. BC opener;
  2. data gap;
  3. Colusa field now;
  4. exposure + coming season;
  5. compare;
  6. how we checked it (OpenET bar chart + ML comparison);
  7. limits / next.
- Record a 2-minute screen capture of the demo path as the backup.
- Rehearse three times against a stopwatch.

### 5. Bare days contradict each other on every screen (Validity −1; bare periods are a named brief ask)

**Evidence for the Colusa baseline (rice + winter flood):**

| Where | What it says about bare time |
|---|---|
| Compare: engine `bare_days_per_year` | 120 days (modelled calendar) |
| Compare header | Safflower is "bare about 85 more days" (205 − 120) |
| `year.png` | "Typical year: days bare or thin 240"; 2025 is 220 (observed satellite) |
| Brief and the "About the ground" panel | "Bare mid-Oct to late Apr" (about 190 days) |
| `coming-season.png` | "Usually bare from mid Feb to early Apr, about 49 days" |

The engine README also says the observed baseline sees winter flooding in only 3 of 6 winters (field check FAIL). So "today" is observed for exposure but modelled for bare days and every other score: two different baselines.

**Why a judge marks it down:** A grower sees 120, 240, about 190 and 49 for the same thing. That alone sinks the usability part of Validity.

**Fix:**
- Pick one definition: bare = cover < 0.2 and not water, counted in days a year.
- Use the observed satellite value for "today" everywhere.
- Show the modelled value only for alternatives, labelled "estimated".
- Rename the coming-season number to "longest bare stretch in winter".

### 6. The default water limit makes today's rotation "over your limit" (Validity −0.5)

**Evidence:**
- `frontend/app/src/mock/locations.json:168` sets Colusa to 3.5 acre-ft/acre, and `:472` sets Kings to 3.0.
- PLAN (14 Nov afternoon) decided Colusa 5.0 and Kings 3.0, "clearly labelled example, change to yours".
- On screen:
  - Coming season says "Your limit: 3.5", and rice at 5.2 is shown in "brown means over".
  - Compare says "Rice + winter cover 5.4 · over your limit".
  - Kings alfalfa needs 3.9 against 3.0.
- No "example" label appears in `compare.png`.

**Why a judge marks it down:** The grower has grown rice on this field for 7 of the last 10 years under a Glenn-Colusa ID supply (CVP settlement contractors got 100% in most years; see the app's own table). Telling them their current practice is over their limit is visibly wrong.

**Fix:**
- Set Colusa to 5.0.
- Label the slider "Example limit, change to yours".
- For Kings, cite where 3.0 comes from (the GSA allocation), or label it as an example too.

### 7. The printed page contradicts itself on water (Validity −0.5)

**Evidence (`brief.png`):**
- Section 3: "Irrigation need about 2.0 acre-feet per acre" for safflower.
- Section 5, same page: "Safflower: often grown on stored soil water with 0–1 irrigations."
- Directly under the 2.0, it says "Checked against OpenET… our estimate runs about 16% high."
- But OpenET checks only the baseline's ET (1108 mm). It does not check irrigation need, which for rice adds an assumed 450 mm (300–600) F term. It does not check safflower at all.
- `backend/engine/README.md` admits "Safflower and wheat I are upper bounds… no stored-soil-water term".

**Why a judge marks it down:** An Earth scientist reading the printout sees a validation badge stuck on an unvalidated number that the same page disputes.

**Fix:**
- Move the OpenET line next to the crop-water-use number for today's crop only.
- Add "upper bound: no stored soil water counted" to the safflower and wheat water lines.
- Or subtract a soil-water credit from SSURGO AWC: 2.1 in/ft × root depth is already in `soil.json`.

### 8. Placeholder scores are shown as results (Validity −0.5, Relevance −0.5) (in flux)

**Evidence (`backend/engine/out/*/strategies.json`):**
- `pest_break` is 0.0 for all 8 strategies, including safflower, which does break the rice cycle.
- `market` is 50.0 for all 8. Market suitability is one of the brief's six priorities, and it is constant.
- Baseline `erosion` is 15 and 7.5 (engine check FAIL).
- Kings alfalfa erosion is 7.5, against 4.6 for silage corn with 127 bare days.
- Compare (`compare.png`) shows "Water soaks in better 67 vs 6" as a gain on a hydrologic group D clay. The engine itself notes the rotation effect is limited there.

**Why a judge marks it down:** Constant or zero scores are a sign the six priorities aren't actually being scored.

**Fix (if the engine fix doesn't land by freeze):**
- Hide any score that is constant across a field's strategies.
- Show "not scored yet" for pest break and market.
- Add a "group D soil: limited" qualifier to infiltration.

### 9. Brief items missing that are cheap to add (Relevance −0.5, Validity/usability −0.5)

**Evidence:**
- **Glossary:** none in the UI (no "glossary", "evapotranspiration" or "water balance" anywhere in `src`), and `/api/glossary` is a fixture. The brief explicitly asks for plain-language explanations of ET, soil-moisture anomaly, NDVI, frost risk and water balance.
- **Scenario sliders:** none. The brief asks for "rainfall or temperature" sliders. The engine already accepts `scenario={"dT_c","dP_pct"}` (`backend/engine/README.md`), but there is no UI.
- **Farmer priorities as inputs:** none. The engine accepts `weights`, but Compare has no priority control. The brief: "farmers enter their own priorities and constraints".
- **Missing from the plan's own must-haves:**
  - trends map;
  - field-level vulnerability zones (NASADEM low spots and slope);
  - the satellite-vs-ground page.

**Fix:**
- Five "What this means" cards linked from the matching labels.
- A ±°C / ±% rain control on Compare that POSTs to `/score`.
- Six 0–4 priority chips that re-rank.

All three are API-ready.

### 10. Three different heat thresholds (Validity −0.25)

**Evidence:**
- Field now uses 100 °F (`season.ts:73`).
- Compare uses "Hot days on bare soil (95 °F or more)" (`ComparePanel.tsx:24`; engine Heat = 35 °C).
- PLAN decided "104 °F (40 °C) everywhere".

The counts differ a lot. For Colusa 2022 from the station data: 39 days at ≥ 100 °F against 13 at ≥ 104 °F.

**Fix:** One threshold, one label, everywhere.

### 11. Wrong facts on the first screen and in the README (Validity, credibility)

**Evidence:**
- **Field picker:** "Rice every year since 2016, fallowed in 2022" (`mock/locations.json:283`). CDL (`backend/field/out/car_colusa_rice/crop_history.json`) says fallow in 2016, 2020 and 2022. OpenET agrees: 310, 246 and 328 mm in those years.
- **README:** says the field is "west of Williams". The app says "4 miles east". The coordinates (39.141 N, 122.083 W against Williams at about 122.149 W) give about 3.5 mi east.

**Fix:**
- Change the picker to "Rice in 7 of the last 10 years; fallowed 2016, 2020, 2022."
- Fix the README.
- The 2020 fallow is a good story beat: ask why.

### 12. NASA assets already fetched but not shown (Relevance +0.5 almost for free)

**Evidence:**
- **ISS photos:** `nasa_open` downloaded 3 per field (URLs resolve). There is no ISS or photo reference anywhere in `frontend/app/src`, despite the PLAN decision "ISS photos: used". Two NASA judges work on that collection.
- **HLS:**
  - `hls.parquet` has 857 and 1,297 scenes, cross-checked against S2 (r = 0.995) and Landsat (r = 1.000);
  - but the calendar is built from MPC Sentinel-2 + Landsat, and the 3D tag says "Sentinel-2 satellite".
- **NASADEM slope:** computed (1.83% and 0.95%), but the engine uses a hard-coded slope of 0% / 0.5%.
- **OPERA DSWx:** 336 Colusa scenes. It could settle the "winter flood seen in only 3/6 winters" failure.

**Fix:**
- One ISS photo on Field now, with NASA's credit line.
- Relabel the calendar and grid as "Landsat (NASA/USGS) + Sentinel-2, cross-checked with NASA HLS", or switch to HLS.
- Feed NASADEM slope to erosion.
- Use DSWx water days in the calendar.

### 13. Crop-insurance numbers hidden behind "not counted yet" (Impact −0.5)

**Evidence:**
- Compare says "Not counted yet: … crop-insurance loss history."
- `backend/ground/out/car_colusa_rice/rma_profile.json` has:
  - $247,816,322 in Colusa rice indemnity, 2014–2024;
  - $145.6M of it in 2022;
  - an 84% drought/irrigation-failure share.

**Fix:** One line on Field now or Coming season, and one slide: "$248M paid out on Colusa rice since 2014; $146M in 2022 alone (USDA RMA)."

### 14. Impact isn't quantified, and nobody can try their own field (Impact −0.5)

**Evidence:**
- There is no acreage or grower count anywhere.
- The search box ("Find a field by town, county or crop") only finds two presets.
- Your own NASS cache has numbers ready:
  - Colusa rice harvested acres were 125,348 in 2017 and 36,907 in 2022 (Census of Agriculture);
  - Colusa had 10 rice operations in the 2022 census.

**Fix:**
- One sourced statewide number per crop: California rice acres and Central Valley alfalfa acres from NASS.
- One sentence on what adding a field takes: a polygon, then the same automated pipeline. Show the pipeline is per-field, not hand-built.

### 15. The demo path is fragile (Presentation −0.5) (in flux)

**Evidence:**
- `npx tsc --noEmit` fails right now. In `src/api.ts`, `nasa_datasets` is not on `Location`, and there is an `ImportMeta.env` typing error.
- The demo needs two servers.
- If the API is down, the app silently switches to "Example data only".

**Fix:**
- Freeze at 22:00 with a green type-check.
- Build a static bundle that reads the saved backend JSON directly (the `file(...)` fallback already exists).
- Record the backup video.

### 16. Personal data in the repo root (risk, not points)

**Evidence:** `Run_the_numbers.gpx` is a Strava GPS track, untracked, sitting next to `x.json` (a stray AppEEARS layer dump).

**Fix:** Delete or move both before anyone runs `git add -A` or shares the repo link.

---

## 3. Should fix

- **The GRACE square is drawn as "17 miles across"** (`overview`/`year` screenshots). That is the 0.25° GRACE-DA model grid. The real GRACE signal is about 300 km. The dataset's own caveat says so, but the map square implies field-adjacent precision, and Stefanov or Gogineni will catch it. Label it "model grid 17 mi; satellite signal ~190 mi".
- **NASA POWER is mostly cited as an error source** on screen: "the satellite weather model (which runs about 6 °F hot in summer)". It is MERRA-2 reanalysis, not a satellite reading. Reframe: "NASA POWER supplies the sunlight, humidity and wind for crop water use; stations supply temperature." That is true (Penman-Monteith inputs) and it credits NASA.
- **"About 61% with this winter's outlook"** (Coming season) re-weights historical 1-inch rain days by CPC tercile probabilities for *seasonal total* precipitation. That is a shaky step, and the 54% → 61% looks precise. Show the 54% (past record), say "outlook leans wetter", and drop the derived number, or explain the method in one sentence.
- **The 2023 atmospheric rivers at this field:** the regional check FAILs. At the field, Jan–Mar 2023 ranks only 8th of 45 years (POWER). The ai README finds 0 water weeks in the 2023 crop season. Pitch 2023 as the delayed-planting year (true at county scale), not "this field flooded".
- **The README headline "within +16% (rice) and +21% (alfalfa)":** "within +16%" hides that it is a one-sided overestimate. OpenET also falls *outside* the engine range for alfalfa (+3% to +39%). Say: "our water model runs 16–21% above OpenET's satellite measurement on the same fields and years; we didn't tune it." The ground chunk still prints +54% / +33% with the old method; fix or remove it before a judge runs it.
- **Jargon left for growers:**
  - "8 vs 0 on a 0–100 rule of thumb";
  - "45th percentile";
  - "Greenness 0.21 on a 0 to 1 scale";
  - "acre-ft/acre" next to inches.

  Replace score pairs with words ("a little", "a lot") and keep the number in the tooltip.
- **The "Live data" pill is green** while 4 parts are examples. Make the count the primary text once fixes 1–2 land, or drop it once it is 0.
- **The brief prints one option at a time.** The challenge asks for at least 3 strategies, each with why, evidence, benefits, gaps and risks. Add a half-page table of all four on the printout, with a "Why" and an "Information gaps" line each.
- **Year view label truncates:** "most common since 20…" (`year.png`).
- **News check FAIL:** one URL ("Drought putting a dent in California rice crop") doesn't resolve. Remove it or replace it.
- **Rice − wheat shows 3.0 acre-ft/acre** (the 2-year average). The rice year itself needs about 5.1, so in a 3.5 allocation year the rice year is definitely over, not "may go over". Show the worst year, not the cycle mean, against the limit.
- **Sorghum-sudan uses slightly more water than corn** (engine). If you can't fix the calendar, don't present sorghum-sudan as the "water-saving" option for Kings.
- **BC card:** "Salmon Arm CS is the only active daily weather station in its valley" is an absolute claim that a CSA intern or local agri-data judge may know is wrong. The BC Ag weather network, Farmwest, ECCC and BC Wildfire stations exist. Soften it to "few long-record daily stations".
- **Hold Kings's ML "below target" badge** in plain words, as decided. Do not show Colusa's 0.99 without the caveat.
- **The 84% Colusa planting cut:** make sure it is quoted exactly as NASA Earth Observatory states it (year pair, planted vs harvested). Your own NASS census numbers say harvested acres fell 71% from 2017 to 2022. Two different "drop" figures in one pitch invites a question.

---

## 4. Genuinely strong (lead with these)

- **An independent, untuned water check.** On the years the field actually grew the crop, the model runs +16% (rice) and +21% (alfalfa) above OpenET, with a published bias decomposition showing why. Most teams won't have any ground check.
- **Honest provenance.** Every number has a source line and a status, the ML README states its own leakage risks, and the checks print PASS/FAIL. The data architect will like this.
- **Grower-unit, plain-sentence field panel.** It reads "inches, acre-feet, days, then the source", with no score dashboards. Done right.
- **The 3D stack with real pixel footprints.** "One reading covers about 134 fields this size" is the best single explanation of satellite scale in the app.
- **The coming-season allocation history table.** Shasta in mid-November against next year's allocation since 2019 is genuinely useful context for a grower decision. No other tool puts it next to a rotation choice.
- **Exposure as a concept.** "When is the field bare and what weather lands on it" is a clear, novel framing, once the bare-day numbers are consistent.

---

## 5. Claims we must not make (as things stand)

- "Validated" or "accurate to 16%". It is a +16–21% overestimate of ET, on the baseline only, against another model-based product. Say "checked against OpenET; runs 16–21% high".
- That irrigation need, alternatives or safflower water use were checked against OpenET. They weren't.
- "Our AI is 99% accurate" (Colusa). The labels are rule-generated. Water labels reuse a feature, and day-of-year drives most of the result.
- "Uses SMAP, GRACE, MODIS, ECOSTRESS, IMERG" until real data is on screen. Right now they are example numbers or not shown.
- "NASA data at the core of every screen." Coming season has no NASA data, and the calendar is half ESA.
- "Real-time" or "this season's data." The calendar and stations end Dec 2025.
- "A forecast." Keep "outlook, not forecast", as the screen already does.
- "Saves 3.4 acre-feet per acre" as a promise. It's a typical-year model difference, and the safflower figure is an upper bound.
- "Scores all six farmer priorities." Market is constant and pest break is zero for all strategies; income is blocked.
- "The 2023 floods hit this field." Field data shows no water weeks in the 2023 crop season, and Jan–Mar 2023 ranks 8th of 45 years.
- "BC has no data" or "BC can't be done." Say instead that BC lacks field-scale measured ET (OpenET doesn't cover Canada) and long crop-label history, so we couldn't check it there yet.
- "Works for any farm." It works for two hand-set-up fields.
- "Every number is sourced." True for data. But the ratings, yields, calendar dates and seed costs are team assumptions (marked U), so say "every number is sourced or marked as our assumption".
