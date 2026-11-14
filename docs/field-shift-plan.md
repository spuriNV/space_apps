# Field Shift: Team Plan

NASA Space Apps Challenge 2026, Vancouver local event (SFU Burnaby).
Challenge: **Field Shift: Adapting Farms with NASA Data**.

Companion files:
- `planner-spec.md`: detailed build spec.
- `research-findings.md`: data sources, news and the problem research.
- `brief-coverage.md`: a line-by-line check against the official brief.

---

## 1. Rules and facts

- **Brief:** https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/
- **Judging guide:** https://www.spaceappschallenge.org/resources/judging-awards-guide/
- **Local event:** https://www.spaceappschallenge.org/2026/local-events/vancouver/
- **Max 6 people per team**, all registered to the same local event. A bigger group splits into teams.
- **Submission:** 7 slides or a 30-second video, due Sunday 11:59 pm.
- **Global judging (1–5 each):**
  - Impact.
  - Creativity.
  - Validity: scientifically sound, feasible, usable.
  - Relevance: NASA data central, not an add-on.
  - Presentation.
- **Local awards** are judged separately. The Vancity prize isn't on the event page, so ask the organizers.

### What the official brief asks for
- **Core task:** a decision-support tool that uses NASA Earth observations plus local soil information, crop characteristics and farmer priorities to explore crop rotations for soil health and resilience.
- **Datasets named:** SMAP, ECOSTRESS, GPM, Landsat, MODIS, NASA POWER, GRACE/GRACE-FO, SRTM. GEDI is also named, under data fusion.
- **Analyze:** temperature, heat stress, rainfall, soil moisture, evaporation, frost risk, extreme precipitation, vegetation stress, long-term water trends.
- **Farmer priorities:** water use, forage value, nitrogen-fixing potential, erosion reduction, organic matter, market suitability.
- **Highlight:**
  - when fields are typically bare;
  - when current crops are most vulnerable;
  - rotations that interrupt pest cycles, reduce water demand, improve infiltration or add supplemental income.
- **Compare at least 3 rotations including the existing one.** For each, give:
  - why it was suggested;
  - the evidence;
  - the benefits;
  - where information is missing;
  - risks needing local review.
- **AI:** the brief's "SI" appears to be its spelling of AI. It asks teams to compare AI or statistical approaches, highlight seasonal transitions, bare periods and crop stress, explain uncertainty, and put datasets onto a common analysis grid.
- **Maps and visuals:**
  - long-term trend maps (soil moisture, heat waves, water storage);
  - field-level vulnerability zones (erosion, water stress, frost-prone areas);
  - timelines, dataset overlays and scenario sliders for rainfall and temperature.
- **Farmer-centred design:**
  - plain language;
  - explanations of ET, soil-moisture anomalies, NDVI, frost risk and water balance;
  - farmer inputs for water, equipment and market;
  - reminders that the tool supports local expertise and doesn't replace it.
- **Inspiration:** "multigenerational farming experience." The hero photo is a Nevada alfalfa field.

### Judges
- **NASA (Johnson Space Center):**
  - Sadie Burnett Boudro: challenge author, Artemis engineer.
  - Mani Deep Gogineni: data architect who builds web apps.
  - William Stefanov: Earth scientist, ISS imagery for disaster response.
  - Alex Stoken: ML on astronaut photography.
- **Local (best-guess identities):**

| Judge | Background | What will land |
|---|---|---|
| Amr Marzouk | SFU Mechatronics lecturer, P.Eng. | A demo that works |
| Shahbano Farooq | SFU PhD student, HCI | Farmer-friendly design |
| Sohan Seemakurthy | SFU Mechatronics; agricultural data work in the ReSEC Lab | A sound data pipeline |
| Dawn Zheng | UBC Physics; Canadian Space Agency intern | Correct satellite use and scale |
| Ebrahim Al-Yousefi | ISSofBC communications | A clear human story |

---

## 2. The problem

**One rotation planner for two water extremes.** Drought and flood are the lens, and every screen ends in a rotation comparison.

### Drought preset (lead story): Shuswap / Salmon River forage growers
- In 2023, about 398 Salmon River/Bessette Creek and about 108 Koksilah licence holders were ordered to stop irrigating forage mid-season.
- Hay went from $75 to $190 a bale.
- **Decision:** in March–April, how much land stays in irrigated alfalfa or hay versus a drought-tolerant or early-harvest mix.
- **Gap:** the orders arrive mid-summer with no warning for one field.
- **NASA adds:**
  - SMAP soil moisture, GRACE storage, and MODIS/HLS vegetation in spring, compared with past cut-off years;
  - POWER-based crop water need for each rotation.

### Wet preset: Fraser Valley / Sumas Prairie dairy fields
- **Decision:** which cover or relay crop to plant, and when, before the October–December atmospheric-river season.
- **Gap:** silage-corn ground sits bare from about October to April under the heaviest rain of the year.
- **Evidence:** an Italian ryegrass relay crop cut runoff 53% and sediment 74% (find the primary paper).
- Don't pitch this as flood prevention. The 2021 flood came from a dyke failure.

### California preset: Sacramento Valley rice
- This is the data-rich ceiling. The valley had a 2021–22 drought that fallowed about half the rice, then the 2023 floods.
- **Extra data:**
  - OpenET measured water use;
  - SSURGO field soils;
  - 15+ years of crop history (CDL), which gives labels for the AI;
  - crop-insurance loss history.
- **Pitch framing:** "California shows the tool with full ground data; BC shows it running on NASA data alone, like most of the world."

### Why a Google search fails
- Orders, drought levels and prices are spread across dozens of releases.
- Nothing is tied to one field.
- Reports come after the event, never at planting time.
- Nothing weighs the trade-offs.

### Users
**A farmer and a regional agrologist working together.** The agrologist is the person most likely to open the tool.

---

## 3. The tool

### Screens
1. **Pick a field:** a preset or a drawn boundary. Includes a satellite pixel-size overlay and an **in-field zone map**:
   - erosion zones from slope;
   - frost-prone low spots;
   - stress hotspots from ECOSTRESS and NDVI.
2. **Your field's year:** the bare-field calendar for 2019–2025, with:
   - rain, frost, heat and dry-spell ticks;
   - a current-crop vulnerability strip;
   - green-up and senescence dates detected by the AI model;
   - the AAFC/CDL crop history.
3. **Trends:** long-term SMAP anomaly, heatwave days per year and GRACE water storage, with a year slider.
4. **Priorities and constraints:**
   - six sliders;
   - irrigation licence volume;
   - livestock;
   - equipment;
   - market preference (sell hay / feed own herd / none).
5. **Compare:** the baseline plus 3 rotations, with range whiskers and ties.
   - Extra lines for pest-cycle break, infiltration, nitrogen scavenging and supplemental income.
   - **Climate scenario sliders** (+°C, ±% rain) re-score everything live.
   - Replay toggles for 2021 and 2023.
6. **Rotation brief:** a printable page with why, evidence, benefits, gaps and a local-review checklist.
   - An LLM writes the text using only sourced numbers.
   - Crop-role explainer cards cover nitrogen-fixing, cover, deep-rooting and drought-tolerant crops.
7. **Satellite vs. ground:**
   - station rain vs. IMERG;
   - the model comparison panel (rule vs. ML accuracy, feature importance);
   - the news timeline: dated BC orders and headlines next to the NASA signal, with SMAP lead time computed from data.
8. **Glossary:** ET, soil-moisture anomaly, NDVI, frost risk and water balance in plain language, linked from every chart label.

### AI component (the brief's "SI")
1. **Bare-field and season detection:**
   - Compare an NDVI threshold rule with a random forest or gradient-boosted classifier on HLS/Sentinel-2 bands and time-series features.
   - Labels come from CDL (California) and AAFC ACI (BC).
   - Train and test on different years, and report accuracy and where the two methods disagree.
2. **Crop-stress anomaly detection:** compare a z-score against the field's own climatology with an isolation forest. Inputs: NDVI, ECOSTRESS land-surface temperature and ET, and SMAP.
3. **Explanation layer:** an LLM writes the brief text from sourced numbers only. A check rejects any number that isn't in the data.

### Uncertainty, three ways
1. **Sources disagree:** IMERG vs. POWER vs. station, and SMAP vs. a model.
2. **Scale mismatch:** a pixel-size badge showing pixel area divided by field area.
3. **Agronomic gaps:** a count of assumed and unverified values per rotation, listed on the brief.

### Common analysis grid
- **Field and zone grid:** fine data (Sentinel-2, Landsat, ECOSTRESS, SRTM, MODIS) is averaged to the field and its zones.
- **Regional grid:** coarse data (SMAP 9 km grid; IMERG, POWER, GRACE resampled to it).
- Both are shown on the Satellite vs. ground page.

### Cut
- The ISS photo classifier.
- The Arduino probe.
- Flood extents, dykes and evacuation layers.

---

## 4. Data (full list in `research-findings.md`)

- **NASA:**
  - POWER;
  - SMAP L3/L4;
  - GPM IMERG;
  - Landsat / HLS;
  - **MODIS MOD13Q1**;
  - **ECOSTRESS** (land-surface temperature and ET);
  - **GRACE-DA**;
  - SRTM / NASADEM;
  - optional: OPERA DSWx and GEDI.
  - Use AppEEARS for subsetting. Everything needs an Earthdata login.
- **ESA:** Sentinel-2 L2A via STAC.
- **BC ground:**
  - AAFC Crop Inventory and Crop Rotations;
  - ECCC stations;
  - SoilGrids;
  - BC Data Catalogue;
  - BC drought levels (website only).
- **California ground:**
  - OpenET;
  - SSURGO Soil Data Access;
  - CDL;
  - CIMIS;
  - CDEC, DWR and USGS;
  - USDA RMA cause of loss.
- **Planting decisions:**
  - FAO-56 crop coefficients;
  - BC cover-crop factsheets;
  - Open-Meteo;
  - NASS / StatCan;
  - USDA AMS hay prices;
  - NOAA seasonal outlook;
  - funding: BC IAF, USDA EQIP.
- **News:**
  - BC Gov News RSS;
  - Google News RSS (cached);
  - GDELT (pre-fetched archive).
- **Cache everything locally.** The demo never calls a live server.

---

## 5. Team (6 per team)

This split matches `planner-spec.md` section B10.3.

| # | Stream | Owns |
|---|---|---|
| 1 | Regional data + news | POWER, IMERG, SMAP, GRACE for all 3 presets; reference ET; risk days; news feeds cached and ranked; SMAP lead-time computation; Trends layers |
| 2 | Field data + zones | HLS, Sentinel-2, MODIS, ECOSTRESS, elevation, AAFC/CDL crop history; weekly feature table; rule-based detector; in-field zones |
| 3 | AI | Rule vs. ML bare/season detectors with accuracy reports; z-score vs. isolation-forest stress model; LLM brief text with a number checker |
| 4 | Rotation engine + adapters | crops.json; 12 strategies; scoring with ranges, scenario sliders, pest break, infiltration, N scavenging, income; BC and California data adapters; API |
| 5 | Frontend | All 8 screens; glossary and crop-role cards; printable brief; phone width |
| 6 | Integration, validation, story | Repo, schemas, fixtures, source check, validation scripts; demo laptop and offline cache; farmer story, slides, 30-second video, submit |

### First-hour agreements
1. Shared JSON schemas: SourcedNumber, Location, Crop, RotationStrategy, plus API routes.
2. Preset IDs and field boundaries for the Salmon River, Sumas and Sacramento presets.
3. Cache paths and fixture files, so the frontend starts immediately.
4. Earthdata logins and AppEEARS authorization; STAC reachable on the venue Wi-Fi.
5. A number is "done" only with value, unit, low, high, method and source URL.

### Must-have vs. stretch
- **Must-have:**
  - the two BC presets;
  - bare-field calendar;
  - compare with ranges;
  - rotation brief;
  - scenario sliders;
  - rule vs. ML season detection;
  - Satellite vs. ground page;
  - glossary.
- **Next:**
  - the California preset;
  - Trends map;
  - in-field zones;
  - stress anomaly model;
  - news timeline;
  - LLM brief text.
- **Stretch:**
  - GEDI;
  - OPERA;
  - drawing your own field with full data.

### Schedule
- **Sat, first hour:** register teams, agree on schemas, set up Earthdata accounts.
- **Sat, day:** streams build in parallel and merge every 3 hours.
- **Sat 22:00:** stop adding features, integrate, cache all demo data.
- **Sun morning:**
  - validation;
  - compute the SMAP lead time;
  - polish;
  - record the video;
  - rehearse 3+ times.
- **Sun 23:59:** submit.

---

## 6. Pitch (3 min)
1. **Story (20s):** a family three generations on the Salmon River. "In 2023 the province told them to stop irrigating in July. Hay went from $75 to $190 a bale."
2. **Problem (20s):** bare or thirsty fields meet a water extreme, and soil, nitrogen and water are lost.
3. **Live demo (1:50):**
   - calendar with risk ticks;
   - AI-detected seasons;
   - set priorities;
   - compare with ranges and a tie;
   - scenario slider set to +2 °C;
   - open a brief;
   - Satellite vs. ground page with the news timeline;
   - switch to Sumas and replay November 2021.
4. **Close (30s):** "It supports the farmer and agrologist, it doesn't replace them. Every number has a source. Built on SMAP, GPM, POWER, Landsat, MODIS, ECOSTRESS and GRACE."

**Submission slides:**
1. Title.
2. Problem.
3. What it does.
4. Compare and scenario.
5. AI and validation.
6. Data and scale.
7. Limits and next steps.

---

## 7. Verify before pitching
- The 398 and 108 licence counts, against the primary BC release.
- The SMAP lead time before the 2023 orders, computed from real data.
- The primary paper for the −53% runoff / −74% sediment result.
- The team-size limit and submission format.
- The Vancity prize, and the judge names, with the organizers.
- The BC IAF fund cap ($100k vs. $30k).
- Everything marked "U" in `planner-spec.md`.
