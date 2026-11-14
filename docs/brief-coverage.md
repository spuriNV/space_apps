# Brief Coverage: Field Shift vs. the Official Challenge Text

Every statement in the official brief, checked against our plan. Brief: https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/

**Status key:**
- ✅ **Covered:** the plan already does it.
- 🟡 **Partial:** started, needs a specific fix.
- 🔴 **Gap:** missing; add it.

## The biggest gap: AI ("SI")

The brief mentions "SI techniques" in the Background and gives AI its own section, "SI, Modeling, and Data Fusion" ("SI" appears to be the site's spelling of AI). We cut ML when we dropped the ISS classifier. Bring it back, and keep it on-brief:

1. **Compare two approaches for bare-field and season-transition detection** (the brief: "compare different SI or statistical approaches", "highlight seasonal transitions, bare-field periods"):
   - **(A) Rule-based:** an NDVI threshold.
   - **(B) ML:** a random forest or gradient-boosted classifier on HLS/Sentinel-2 bands plus NDVI time-series features.
   - **Labels:** USDA CDL (California preset) and AAFC Annual Crop Inventory (BC).
   - **Report:** accuracy of both side by side, plus where they disagree.
2. **Crop-stress anomaly detection** (the brief: "times when current crops show increased stress"):
   - Compare a z-score against the field's own 2015–2025 climatology with an isolation forest.
   - Inputs: NDVI, ECOSTRESS land-surface temperature and evapotranspiration, and SMAP.
3. **Plain-language explanation layer:** an LLM writes the "why" and "evidence" text of each rotation brief using only the sourced numbers in the strategy's data. Every sentence keeps its source chip. If the model states a number that isn't in the data, the sentence is rejected.

## Objectives

| Brief statement | Status | What we do / what to add |
|---|---|---|
| Combine NASA Earth observations with local agricultural information | ✅ | NASA layers plus BC factsheets, AAFC, soil survey, stations |
| App, model, interactive map or other decision-support tool | ✅ | Web app with maps, calendar and compare view |
| Help farmers explore rotations that improve soil health and resilience to weather and water | ✅ | Two water-extreme presets; rotation compare |
| Datasets: SMAP, GPM, Landsat, NASA POWER, SRTM | ✅ | In the pipeline |
| Dataset: **ECOSTRESS** | 🟡 | Was optional. Promote it: land-surface temperature for heat stress and ET for crop water stress in the stress model |
| Dataset: **MODIS** | 🔴 | Add MODIS NDVI (MOD13Q1, 250 m, 2000–present) for a 25-year vegetation-stress baseline that Sentinel-2 (2019+) can't give |
| Dataset: **GRACE / GRACE-FO** | 🟡 | Was optional. Make it a feature: the long-term water-storage trend chart on the Trends map |
| Analyze temperature, heat stress, frost risk | ✅ | POWER frost and heat days; add ECOSTRESS land-surface temperature for heat stress |
| Analyze rainfall and extreme precipitation | ✅ | IMERG extreme-rain days |
| Analyze soil moisture | ✅ | SMAP dryness anomaly |
| Analyze evaporation | ✅ | Reference ET from POWER; ECOSTRESS and OpenET as checks |
| Analyze **vegetation stress** | 🔴 | NDVI was only used for bare vs. covered. Add a crop-stress anomaly for the current crop (AI section, item 2) |
| Analyze **long-term water trends** | 🔴 | Add a Trends view: GRACE storage, SMAP and precipitation anomalies by year |
| Priorities: water use, forage value, nitrogen fixing, erosion reduction, organic matter, market suitability | ✅ | Six sliders and scores |
| Highlight times when fields are typically bare | ✅ | Bare-field calendar (core screen) |
| Highlight **seasons when current crops are more vulnerable** | 🔴 | Add a "current crop vulnerability" strip under the calendar: stress-anomaly weeks for the existing crop |
| Opportunities to **interrupt pest cycles** | 🔴 | Add a pest-cycle-break score: years since the same crop family, plus factsheet notes (e.g. ergot on rye). Rule of thumb, sent for local review |
| Opportunities to **reduce water demand** | ✅ | Water-use score; irrigation need per rotation |
| Opportunities to **improve infiltration** | 🟡 | Mentioned only for the wet preset. Add an infiltration benefit line from root type (deep or fibrous) and cover months, rated from factsheets |
| Opportunities to **add supplemental income** | 🔴 | Add an income line: forage sold or grazed (hay prices from StatCan or USDA AMS) plus cover-crop funding (BC IAF, USDA EQIP). Ranges only, sent for local review |
| Compare at least three strategies, including the existing one | ✅ | Baseline + 3 |
| For each: why, evidence, benefits, information gaps, risks needing local review | ✅ | Rotation brief card |
| A supportive tool that doesn't replace farmer judgment | ✅ | Printed on every brief; agrologist built in |

## Considerations: understanding conditions and data

| Brief statement | Status | What we do / what to add |
|---|---|---|
| How temperature, soil moisture, rainfall, evaporation and vegetation stress relate to crop vulnerability and soil health | 🟡 | Add the stress model, and explain the link in one sentence on each risk tick |
| Explain ET, soil-moisture anomalies, NDVI, frost risk and water balance | 🔴 | Add a "What this means" glossary with a plain-language card per term, linked from every chart label |
| How satellite observations differ from ground measurements, and how combining them improves accuracy | ✅ | Satellite vs. ground page, station vs. IMERG, pixel-size badges |

## Considerations: SI, modeling and data fusion

| Brief statement | Status | What we do / what to add |
|---|---|---|
| Compare different SI or statistical approaches for patterns in historical climate and soil | 🔴 | AI section, items 1 and 2: rule vs. ML, z-score vs. isolation forest, accuracy reported |
| SI that highlights seasonal transitions, bare periods and crop stress | 🔴 | Same; show the seasonal transitions (green-up and senescence dates) the model detects on the calendar |
| How the model interprets uncertainty, and where local expertise is needed | ✅ | Three-way uncertainty, ties, local-review checklist |
| Harmonize resolutions to a common analysis grid | 🟡 | Make it explicit: (a) a **field grid**, where fine data (S2, Landsat, ECOSTRESS, SRTM) is aggregated to field and in-field zone statistics; (b) a **regional grid**, the 9 km SMAP EASE grid, with IMERG, POWER and GRACE resampled to it. Show both on one page |
| Fuse SMAP, ECOSTRESS LST, GPM, Landsat/MODIS VI, GEDI biomass and soil into explainable features | 🟡 | Build a feature table per field-week from these sources. GEDI biomass is optional, only where footprints exist. Feature importance from the ML model becomes evidence on the brief |

## Considerations: rotation strategy exploration

| Brief statement | Status | What we do / what to add |
|---|---|---|
| Nutrient cycling | 🟡 | Nitrogen fixing is scored. Add nitrogen scavenging (catch crops), rated from factsheets |
| Erosion risk, organic matter, water use, forage, market | ✅ | Scored |
| Pest-cycle disruption | 🔴 | Pest-break score (see Objectives) |
| Map rotation ideas to priorities: conserving water, supplemental income, soil structure | 🟡 | Sliders cover it. Add income and soil structure (infiltration) to the scoring |
| Explain how nitrogen-fixing, cover, deep-rooting and drought-tolerant crops help soil health | 🔴 | Add four "crop role" explainer cards, linked from each crop in a rotation |

## Considerations: geospatial mapping and visualization

| Brief statement | Status | What we do / what to add |
|---|---|---|
| Interactive maps of long-term trends: soil moisture, heat waves, water-storage declines | 🔴 | Add a **Trends** map with a year slider: SMAP anomaly, heatwave days per year (POWER and ECOSTRESS), GRACE storage |
| Field-level vulnerability zones: erosion zones, water-stress hotspots, frost-prone areas | 🔴 | Add an **in-field zones** layer: slope classes from SRTM (erosion), low spots from SRTM (cold-air pooling, frost-prone), ECOSTRESS/NDVI stress hotspots |
| Timelines | ✅ | Calendar, replay years, news timeline |
| Overlays comparing datasets | ✅ | Satellite vs. ground page |
| **Scenario sliders that adjust rainfall or temperature** | 🔴 | Add "+°C" and "± % rain" sliders that recompute reference ET, crop water need, frost/heat days and exposure live. Cheap to build from formulas we already have |

## Considerations: farmer-centred design

| Brief statement | Status | What we do / what to add |
|---|---|---|
| Interpretable for farmers with little technical experience | ✅ | Plain language, tooltips, glossary (new) |
| Farmers enter their own priorities and constraints: water availability, equipment, market preferences | ✅ | Sliders plus constraints (licence volume, drill, livestock). Add a market-preference input (sell hay / feed own herd / no preference) |
| Reminders that it supports, not replaces, local expertise | ✅ | On every brief and the Limits page |

## Story angle from the brief
- The brief is "inspired in part by **multigenerational farming experience**." Open the pitch with a farm family that has been on the land for generations: "Three generations on this field, and the last five summers broke the pattern."
- The hero photo is a **Nevada alfalfa field**. That supports the alfalfa-heavy drought preset, and a western US preset alongside BC.

## Updated feature list (additions in bold)
1. Field picker with pixel-size overlay, plus an **in-field zone map** (erosion, frost-prone, stress hotspots).
2. Bare-field calendar, plus a **current-crop vulnerability strip** and **seasonal transition dates from the AI model**.
3. **Trends map:** long-term soil moisture, heatwaves, GRACE water storage.
4. Priorities and constraints, plus a **market preference** input.
5. Compare baseline + 3 with ranges, plus **pest-break, infiltration and income** lines, plus **climate scenario sliders**.
6. Rotation brief, plus **LLM-written explanations tied to sources** and **crop-role explainers**.
7. Satellite vs. ground page, plus a **model comparison panel**: rule vs. ML accuracy and feature importance.
8. **Glossary:** ET, soil-moisture anomaly, NDVI, frost risk, water balance.

## Workstream changes
- **Field data:** add MODIS NDVI and ECOSTRESS. Own the in-field zone map.
- **New AI owner,** or merge into Rotation engine if the team is capped at 6: the bare-field/transition model comparison, the stress anomaly model, and the LLM explanation layer with source checking.
- **Frontend:** add the Trends map, scenario sliders and glossary.
- **Story:** the multigenerational farm opener.
