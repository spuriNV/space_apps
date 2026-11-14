# Field Shift: Team Plan

NASA Space Apps Challenge 2026, Vancouver local event (SFU Burnaby).
Challenge: **Field Shift: Adapting Farms with NASA Data**.

**Decision:** California is the product; BC is the motivation.
- The pitch opens with BC's 2023 Salmon River irrigation order and the 2021 Sumas flood, and points out that BC lacks the ground data to prove a tool works.
- It then shifts: "so we built and validated it where the data is rich."
- The whole demo runs on two California example farms.

**Companion files:**
- `planner-spec.md`: build spec v3.
- `rotation-factors.md`: what the planner scores.
- `brief-coverage.md`: a check against the official brief.
- `research-findings.md`: data sources and APIs.

---

## 1. Rules and facts

- **Brief:** https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/
- **Judging guide:** https://www.spaceappschallenge.org/resources/judging-awards-guide/
- **Local event:** https://www.spaceappschallenge.org/2026/local-events/vancouver/
- **Max 6 people per team.** The submission is 7 slides or a 30-second video, due Sunday 11:59 pm.
- **Global judging, 1–5 each:**
  - Impact.
  - Creativity.
  - Validity: scientifically sound, feasible, usable.
  - Relevance: NASA data central.
  - Presentation.
- **Local awards** are judged separately. Ask the organizers about the Vancity prize.

### What the official brief asks for
- **Core task:** a decision-support tool using NASA Earth observations plus local soil, crop characteristics and farmer priorities to explore crop rotations for soil health and resilience.
- **NASA datasets named:** SMAP, ECOSTRESS, GPM, Landsat, MODIS, NASA POWER, GRACE/GRACE-FO, SRTM; GEDI under data fusion.
- **Farmer priorities:** water use, forage value, nitrogen fixing, erosion reduction, organic matter, market suitability.
- **Highlight:** bare periods, when current crops are vulnerable, pest-cycle breaks, lower water demand, infiltration, supplemental income.
- **Compare at least 3 rotations including the existing one,** each with why, evidence, benefits, gaps and risks needing local review.
- **AI:** "SI" appears to be the brief's spelling of AI. Compare AI or statistical approaches; detect seasonal transitions, bare periods and crop stress; explain uncertainty; harmonize data onto a common grid.
- **Maps and visuals:** long-term trend maps, field-level vulnerability zones, timelines, dataset overlays, rainfall and temperature scenario sliders.
- **Farmer-centred design:** plain-language explanations of ET, soil-moisture anomaly, NDVI, frost risk and water balance; farmer inputs; "supports, doesn't replace" reminders.
- **The brief's own facts:** it's inspired by "multigenerational farming experience," and its hero photo is a Nevada alfalfa field.

### Judges
- **NASA (Johnson Space Center):**
  - Sadie Burnett Boudro: challenge author.
  - Mani Deep Gogineni: data architect.
  - William Stefanov: Earth scientist, ISS imagery.
  - Alex Stoken: ML on astronaut photography.
- **Local (best-guess identities):**
  - Amr Marzouk: SFU Mechatronics.
  - Shahbano Farooq: SFU HCI.
  - Sohan Seemakurthy: SFU; agricultural data work.
  - Dawn Zheng: UBC Physics; CSA intern.
  - Ebrahim Al-Yousefi: ISSofBC communications.

---

## 2. The problem

### Motivation: BC (pitch opener only)
- **16 Aug 2023:** about 398 licence holders on the lower Salmon River and Bessette Creek were ordered to stop irrigating forage. Mid-June letters had already asked for up to 50% cuts.
  - Source: https://news.gov.bc.ca/releases/2023FOR0052-001305
- **Nov 2021:** the Sumas Prairie atmospheric-river flood.
- **BC's data gap:**
  - no OpenET field-level water use;
  - no field-scale soil API;
  - about one weather station per valley;
  - crop labels only from 2011.
- **Takeaway:** BC has the problem and NASA's data, but not the ground data to prove a tool works.

### Product: California, two example farms
1. **Colusa County rice (Sacramento Valley):**
   - The 2022 drought cut Colusa rice planting by 84%.
   - The 2023 atmospheric rivers then delayed planting and harvest.
   - Source: NASA Earth Observatory, https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/
2. **Tulare/Kings dairy forage (San Joaquin Valley):**
   - Alfalfa and silage corn grown under groundwater limits.
   - Tulare Lake re-flooded to about 114,000 acres in 2023.
   - The basin was put on SGMA probation in April 2024 for over-pumping.
   - Alfalfa matches the brief's photo.

### Users
**A grower and an adviser working together.** The adviser is a UCCE farm advisor, NRCS planner, or water district/GSA staff member, and is the person most likely to open the tool.

### Why a Google search fails
- Allocations, drought status, prices and news are spread across dozens of sources.
- Nothing is tied to one field.
- Reports come after the event.
- Nothing weighs the trade-offs.
- Nothing shows how accurate it is against measured data.

---

## 3. The tool

### Screens
1. **Pick a field:**
   - two California example cards (rich ground data);
   - a **"Why not BC yet"** card;
   - pixel-size overlay and in-field zones.
2. **Your field's year:**
   - bare / covered / water calendar for 2016–2025;
   - rule vs. ML detector toggle;
   - risk ticks;
   - current-crop vulnerability strip;
   - CDL crop history;
   - news timeline.
3. **Trends:** long-term SMAP soil moisture, heatwave days, GRACE groundwater vs. DWR wells, MODIS vegetation.
4. **Priorities and constraints:**
   - six sliders;
   - water source and allocation (acre-ft/acre);
   - livestock;
   - equipment;
   - market preference;
   - climate scenario sliders.
5. **Compare:**
   - baseline + 3 rotations with ranges and ties;
   - irrigation need vs. allocation;
   - OpenET check badge;
   - crop-insurance loss history;
   - replays of 2022 and 2023.
6. **Rotation brief:** printable, with AI-written text checked against sources, cover-crop funding (EQIP 340) as a range, and a local-review checklist.
7. **Satellite vs. ground:**
   - **OpenET measured ET vs. our modelled crop water use (headline chart)**;
   - CIMIS vs. POWER;
   - rain sources compared;
   - GRACE vs. wells;
   - the model comparison panel.
8. **Limits:** includes "BC is out of scope; transferability is a claim to test."

### AI component (the brief's "SI")
1. **Bare-field and season detection:**
   - Compare an NDVI threshold rule with random forest / gradient boosting.
   - Trained on **real CDL crop labels** across thousands of fields near each example farm.
   - 2022 (the fallow year) is held out as the test year.
   - Spatial hold-out by field, so the test isn't just neighbouring pixels.
2. **Crop-stress anomaly detection:** compare a z-score with an isolation forest. Inputs: MODIS and HLS vegetation, ECOSTRESS, SMAP and OpenET anomalies.
3. **Explanation layer:** an LLM writes the brief text using only sourced numbers. A checker rejects any number that isn't in the data.

### Rotations compared
| Colusa rice | Tulare/Kings forage |
|---|---|
| **Baseline:** continuous rice with winter flooding | **Baseline:** alfalfa, 7–8 cuts, 4–5 year stand |
| Rice + winter cover crop instead of winter flood | Winter small-grain silage + silage corn |
| Dry-year plan: fallow with cover or safflower when water allocation is under 50% | Winter small-grain silage + sorghum-sudan (less water than corn) |
| Rice–winter wheat | Shorter alfalfa stand + winter-cereal break + unirrigated summer |

### Scoring
See `rotation-factors.md`. In brief:
- the brief's six priorities;
- pest break, infiltration, nitrogen scavenging and income;
- exposure (bare days × risky weather);
- every score shown as a range, with ties when ranges overlap.

---

## 4. Data
- **NASA:**
  - POWER;
  - SMAP L3/L4;
  - GPM IMERG;
  - HLS / Landsat;
  - MODIS;
  - ECOSTRESS;
  - GRACE-DA;
  - SRTM / NASADEM;
  - optional: OPERA DSWx (2023 flood extent).
  - All need an Earthdata login; use AppEEARS for subsetting.
- **ESA:** Sentinel-2.
- **California ground data:**
  - CDL crop history (the AI labels);
  - SSURGO soils;
  - **OpenET (validation)**;
  - CIMIS;
  - CDEC;
  - DWR wells and SGMA status;
  - USDA RMA cause of loss;
  - NASS and AMS prices;
  - EQIP 340;
  - US Drought Monitor;
  - NOAA outlooks.
- **News:**
  - Google News RSS (US and Canada);
  - GDELT archive;
  - DWR and State Water Board releases;
  - Ag Alert;
  - BC Gov News for the opener.
- **Cache everything.** The demo never calls a live server.

---

## 5. Team (6 per team; matches spec B10.3)

| # | Stream | Owns |
|---|---|---|
| 1 | Regional data + news | POWER, IMERG, SMAP, GRACE, USDM; reference ET; risk days; California and BC news cached; lead-time computation; Trends |
| 2 | Field data + zones | HLS, Sentinel-2, MODIS, ECOSTRESS, elevation, CDL, OpenET; weekly feature table; rule detector; in-field zones |
| 3 | AI | CDL labels; RF/HGB detectors with accuracy reports; z-score vs. isolation forest; LLM brief + number checker |
| 4 | Rotation engine + CA adapter | crops.json (FAO-56, UC ANR, cover-crop selector); 8 strategies; scoring, scenarios, allocation check; SSURGO, OpenET, CIMIS, CDEC, DWR, RMA, prices, EQIP |
| 5 | Frontend | 8 screens, glossary and crop-role cards, "Why not BC yet" card, printable brief |
| 6 | Integration, validation, story | Repo, schemas, fixtures, checks (OpenET headline first); BC opener story and news; slides, video, submit |

### First-hour agreements
1. Shared schemas and API routes, plus the California adapter interface.
2. Preset IDs `car_colusa_rice` and `caf_tulare_forage`; field boundaries and 10 km training boxes.
3. Fixtures, so the frontend starts at hour 2.
4. **Keys:** Earthdata (GES DISC, NSIDC, AppEEARS), OpenET, CIMIS, USDA NASS, USDA AMS, an LLM API. Start the GDELT pre-fetch and download the RMA files.
5. **Definitions of done:**
   - every number has a source;
   - every model has an accuracy report;
   - every AI sentence is checked;
   - nobody writes a water slide until the OpenET-vs-model check produces a number.

### Must-have vs. stretch
- **Must-have:**
  - both California presets end to end;
  - the CA data adapter;
  - calendar with both detectors;
  - stress model;
  - OpenET validation;
  - compare with ranges and scenarios;
  - rotation brief with AI check;
  - Satellite vs. ground page;
  - glossary;
  - the BC news timeline for the opener.
- **Stretch:**
  - the Trends map with year slider;
  - zone maps per 30 m cell;
  - cross-valley ML test;
  - OPERA flood extent;
  - the BC NASA-only chart.

### Schedule
- **Sat, first hour:** register teams, agree on schemas, set up keys.
- **Sat, day:** build in parallel and merge every 3 hours.
- **Sat 22:00:** feature freeze; integrate and cache.
- **Sun morning:**
  - run all checks;
  - polish;
  - record the video;
  - rehearse 3+ times.
- **Sun 23:59:** submit.

---

## 6. Pitch (3 min)
1. **BC opener (30 s):**
   - "Three generations on the lower Salmon River. On 16 August 2023, about 398 licence holders were told to stop irrigating forage. Two years earlier, Sumas Prairie went under."
   - Show the BC news timeline.
   - "BC has the problem and NASA's satellites see it, but there's no ground data to prove a tool works. So we built and validated it where the data is rich."
2. **California demo (2 min):**
   - Colusa calendar: 2022 fallow, 2023 storms, rule vs. ML.
   - OpenET vs. modelled chart.
   - Priorities with allocation.
   - Compare with ties, insurance history and the scenario slider.
   - One brief.
   - 15 seconds on Tulare/Kings: alfalfa under a pumping cap.
3. **Close (30 s):** "Supports the grower and adviser, never replaces them. Every number has a source; every model shows its accuracy; water numbers are checked against measured ET. Next step: bring it home to BC."

**Slides:**
1. Title.
2. BC motivation and data gap.
3. Built where data is rich: California.
4. Calendar, detectors, validation.
5. Compare and scenarios.
6. Brief, AI check, uncertainty.
7. Limits and next step (BC).

---

## 7. Verify before pitching
- The 398 count and the 16 Aug 2023 date (release 2023FOR0052-001305; Fable checked it, but confirm).
- The hay price ($75 → $190), if used.
- California calendars, CIMIS station IDs, CDL class codes, rice flood-water term, sorghum-sudan water savings, EQIP rates. All are marked "U" in the spec.
- The OpenET-vs-model bias and the lead times, produced by the pipeline before anyone quotes them.
- Team size, submission format, the Vancity prize and the judges, with the organizers.
