# Field Shift planner: idea and build spec (v2, single current spec)

One rotation planner, two BC water regimes plus one data-rich California preset, built around a bare-field calendar, an AI layer that the brief calls "SI", and a per-strategy rotation brief. Written to be handed to coding agents; every number carries a source or is marked **U**. Supersedes v1; `field-shift-plan.md` is the team plan, `brief-coverage.md` is the gap check this version closes, `research-findings.md` holds endpoint test results.

Marker key: **V** = read from the cited source during research. **U** = unverified / assumed / inferred; confirm or label "assumed" in the UI. **[M]** = must-have for the demo. **[S]** = stretch; build only after all [M] items are cached and demoable.

---

## Part A: The idea

### A1. The real problem and who has it

BC farms sit on two water extremes, and both punish an uncovered or water-hungry field. California's Sacramento Valley lived both extremes back to back (2021–22 drought, 2023 floods) with far richer ground data, which lets us show the ceiling of the method and test it.

**Drought regime (Shuswap / Salmon River, Thompson-Okanagan).**
- 16 Aug 2023: fish population protection orders under the Water Sustainability Act required "approximately 398 surface and groundwater licence holders in the lower Salmon River and Bessette Creek area" to "stop using water for forage crops, which include grass for hay, alfalfa and forage corn"; vegetables, livestock watering and domestic use exempt; "starting in mid-June, multiple mailouts were sent to all licensed water users requesting reductions of up to 50%" (V): https://news.gov.bc.ca/releases/2023FOR0052-001305 . Ministerial orders M0238_2023 (lower Salmon River) and M0239_2023 (Bessette Creek) (V, linked from the release). Orders expired 30 Sept 2023 (V, news: https://www.castanetkamloops.net/news/Salmon-Arm/571142/ ). **Correction to research-findings.md:** release 2023FOR0059-001512 is the 27 Sept 2023 bulletin rescinding the *Koksilah and Tsolum* (Vancouver Island) orders (V), not the Salmon River order.
- Hay prices reported rising from ~$75 to ~$190 a bale in 2023 (U: from research-findings; verify in https://www.countrylifeinbc.com/water-curtailments-squeeze-forage-production/ before putting on a slide).
- Aug 2023: North and South Thompson basins at drought Level 5 (V, news): https://amp.cbc.ca/lite/story/1.6936387
- Okanagan crop water demand projected +37% (745 to 1021 mm/yr) by 2070–2099 (V): https://www.frontiersin.org/articles/10.3389/fenvs.2018.00074/full
- Forage in the Interior is mainly winter feed for beef; two alfalfa cuts, 5-year stands (V, 2002 Kamloops Forage Manual, archived): https://bac-lac.wayback.archive-it.org/web/20080212123631/http://www.al.gov.bc.ca/forage/publications/documents/kamloops_forage_manual.pdf

**Wet regime (Fraser Valley / Sumas Prairie).**
- 14–15 Nov 2021 atmospheric river: Sumas dike breach, ~1,100 farms under order/alert, ~150 km² of farmland flooded (V, news; figures vary by outlet): https://www.countrylifeinbc.com/catastrophic-flooding-hits-fraser-valley/ ; livestock deaths ~628,000 poultry, 420 dairy cattle, ~12,000 hogs (V via https://www.canadianpoultrymag.com/catastrophic-floods-hit-b-c/ ).
- Topsoil stripped into the Fraser (V): https://www.cbc.ca/lite/story/1.6261829
- The everyday problem: bare silage-corn ground Oct–Apr. Italian ryegrass relay under silage corn cut mean annual runoff 53% and suspended solids 74% in a Lower Fraser Valley study (V via https://bcfoodweb.ca/node/479 ; locate primary paper before quoting).
- N left after mid-August is lost over winter without a cover crop (V, BC Ministry): https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/agricultural-land-and-environment/soil-nutrients/management/cover-crops
- Backup angle: 71% of 2,757 Abbotsford-aquifer well samples exceeded 10 mg/L nitrate-N (U: from research-findings; source needed).

**Data-rich ceiling (Sacramento Valley rice, Colusa/Glenn).**
- 2022 drought: Sacramento Valley rice acreage roughly halved; Colusa and Glenn down 84% and 75% vs 2021 (V, NASA Earth Observatory quoting UC Davis): https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/ ; Glenn-Colusa Irrigation District "typically ~100,000 acres of rice … this year 1,000" (V, news); ~267,000 acres fallowed in Sutter/Colusa/Glenn (V, news).
- Jan–Mar 2023 atmospheric rivers and Sacramento Valley flooding (U: cite a DWR/NOAA summary before pitching).

**Who has the problem.** Two personas, served together:
1. The farmer: Fraser Valley dairy producer (silage corn + grass); Salmon River valley cattle/dairy operator with irrigated alfalfa/grass hay; Colusa County rice grower (California).
2. The agrologist / adviser: BC Ministry regional agrologist, AgriServiceBC staff or a private P.Ag.; in California a UCCE farm advisor or NRCS planner. This person opens the tool. The brief: "does not replace farmer judgment or local agricultural expertise".

### A2. User story (concrete)

Maria's family has milked cows on Sumas Prairie for three generations; her 12 ha back field has been continuous silage corn for nine years. In March she meets Dev, the regional agrologist. Dev opens the planner, picks the Fraser Valley preset, drags the boundary over the back field. The bare-field calendar shows the field read as bare from mid-October to late April in six of seven years; the rule-based and ML detectors agree on 91% of days (the disagreement is hatched). Heavy-rain ticks from IMERG and the Abbotsford station land inside the bare window, including 14–15 Nov 2021; the news timeline under the calendar shows the BC Gov release and two headlines for that week. The current-crop vulnerability strip shows two late-June weeks in 2021 flagged by both the z-score and isolation-forest models (heat dome). Maria sets priorities (erosion and organic matter high, forage medium, water low) and market preference "feed own herd". Compare shows baseline vs (1) corn + fall rye, (2) corn + Italian ryegrass relay, (3) three years of grass-legume hay then corn. Exposed heavy-rain days drop from ~45 to ~8–15 for the cover options; the ryegrass relay leads on her weights but overlaps fall rye, so the tool says "tie within uncertainty". The +2 °C / −15% summer rain scenario slider widens the gap slightly (more ETo in spring favours the relay's earlier feed). Dev prints both briefs; the LLM-written "why" and "evidence" sentences each carry a source chip and the footer says "9 sentences checked against 23 sourced numbers; 1 rejected". The "needs local review" list includes seeding window vs harvest date, herbicide compatibility, waterfowl pressure, and the IAF cover-crop funding cap to confirm.

Shuswap mirror: Len's family has ranched on the lower Salmon River since the 1950s. On 16 Aug 2023 he was one of ~398 licence holders ordered to stop irrigating forage. In March 2026 the planner shows him what the satellites showed in spring and early summer 2023: SMAP soil-moisture percentile for his 9 km cell, GRACE groundwater percentile for the region, the HLS green-up date, each against the 2015–2025 record, and the computed lead time between the first sustained SMAP low and the order (the number is computed by the pipeline, not asserted). He compares continuous alfalfa against fall-seeded cereal silage harvested in June (before any August order), a sainfoin-grass mix on the bench, and a barley break year; irrigation need per rotation is shown in mm against his licence volume.

California: the same screens with SSURGO drainage and AWC, CDL 2008–2024 crop history (rice → fallow in 2022 → rice in 2023), OpenET measured ET next to our modelled ETc, CIMIS station ETo next to POWER, and the RMA cause-of-loss profile for Colusa rice (drought vs excess moisture share of indemnities).

### A3. The decision it changes, and why NASA data is uniquely useful

The decision is **what goes into the open window, and when**: which cover/relay/forage crop, seeded which week, on which part of the field, against which weeks of risk, and (Interior) how much of the stand to keep in irrigation-dependent alfalfa before an August order can arrive.

NASA data makes two inputs observed instead of assumed: *when the field is bare and when the crop is stressed* (HLS/Sentinel-2 30/10 m since 2015/2019, MODIS 250 m since 2000, ECOSTRESS 70 m LST/ET since 2018) and *when and how hard the weather hits, over decades* (POWER 1981–, IMERG 2000–, SMAP 2015–, GRACE 2003–). In the Interior the nearest ECCC station is often in another valley; the satellite record is continuous and everywhere. NASA data is never used to "pick a crop"; it measures exposure, stress and water demand; crop properties come from BC/USDA factsheets.

### A4. What exists, and how this differs

| Existing tool | What it does | What it does not do |
|---|---|---|
| BC Agriculture Water Calculator (https://bcwatercalculator.ca/) (V exists) | Annual irrigation / livestock demand for licensing | No rotation comparison, no satellite observation, no uncertainty |
| BC Agriculture Water Demand Model (V) | Basin planning, ETo × Kc per polygon | Planner-facing; no field observation; no alternatives |
| BC AgriWeather / Farmwest ET (V exist) | Station ET and irrigation scheduling | Within-season scheduling, not rotation choice |
| BC Drought Portal (https://droughtportal.gov.bc.ca) (V exists) | Drought levels by basin | Regional, after the fact, no field, no crops |
| OpenET (https://openetdata.org/) | Field-scale ET, western US | Not available in BC (V, challenge Resources tab) |
| CropPlan+ (FCC), Cropwise-type apps (V exist) | Field records, commercial crop planning | Closed; no exposure window; no NASA data; no uncertainty |
| Western cover-crop selector (https://covercrop-selector.org) (V exists) | Goal-based species selection | No field observation, no weather exposure |
| BC cover-crop factsheets, 23 species (V) | Ratings for goals/tolerances/drainage | Static PDFs |

The gap: nothing combines *when my field is bare or stressed* + *when the weather hits* + *which rotation covers it* + *how sure are we* + *what it might pay*, in language a farmer and adviser can read together.

### A5. Creative twists (on-brief)

1. **Exposure calendar** [M]. A 12-month ring per rotation: bare days shaded, risk ticks (extreme rain / frost / heat / dry spell); the intersection is "exposed risk-days".
2. **Replay a real year** [M]. "Replay 2021 / 2023" runs the proposed calendar against observed daily data.
3. **Satellite saw vs news reported** [M]. Timeline markers pair the NASA signal on a date with 1–3 dated headlines and a *computed* lead-time line ("SMAP cell fell below the 10th percentile N days before the 16 Aug 2023 order").
4. **Agrologist hand-off** [M]. Printable brief with every number footnoted, gaps listed, review checklist.
5. **Two detectors, one calendar** [M]. Rule-based and ML bare/transition detection drawn on the same strip; disagreement is hatched, accuracy is printed. The brief's "compare different SI or statistical approaches" becomes a visible feature.
6. **Rich vs sparse** [S]. Same screens for Colusa (SSURGO, CDL, OpenET, CIMIS) and Shuswap (SoilGrids, ACI, no OpenET, one station); a "ground data: rich / sparse" badge shows how the tool degrades gracefully, which is the global-relevance argument.

### A6. The weakest point, and the defense

**Weakest point:** rotation scores are rule-of-thumb composites of factsheet ratings and FAO-56 coefficients, not a calibrated crop model; the ML detectors are trained on pseudo-labels; satellites cannot resolve a field in SMAP/IMERG/POWER.

**Defense (say it first):** we output comparisons with ranges and declare ties; every number links to its source; the only things computed from NASA data are exposure, stress, water demand and trends, which satellites measure well; scale is on screen (footprints drawn, badges on every score); ML is evaluated on held-out years and compared with the rule, with accuracy and disagreement shown; OpenET and CIMIS in California are an independent check of our ETc and ETo; yield and dollars are listed as gaps and ranges, never a single number. Second weakness, "why not a station?": stations are points and sparse in BC valleys; we use them to validate and show the difference.

---

## Part B: Build spec

### B1. Presets

All presets are *representative* fields ("Example field; drag to your own"). Final polygons chosen Saturday morning against AAFC ACI / CDL so the pixels are the crop we claim.

#### Preset FV (Fraser Valley, wet): Sumas Prairie dairy field [M]

| Item | Value | Status / source |
|---|---|---|
| Centre | 49.06 N, −122.17 W | U: representative; confirm corn/forage in ACI 2023/2024 |
| Field | 12 ha (~350 × 350 m) | U: typical dairy field; Census gives totals only: https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/agriculture-and-seafood/statistics/census/ag-in-brief/ag_in_brief_2021_-_cd_fraser_valley.pdf |
| Soil | Sumas Soil Management Group: 2,650 ha, level lacustrine deposits exposed when Sumas Lake was drained; "very poorly drained". Fairfield group around it: 11,000 ha, imperfectly drained | V: https://www.env.gov.bc.ca/esd/distdata/ecosystems/Soils_Reports/Docs/soil_mgmt_hbk_fraservalley.pdf ; SoilGrids point query for texture/SOC (B2.12) |
| Slope / elevation | ~0–1% / ~5–10 m; compute from NASADEM | U until computed |
| ECCC stations | Abbotsford A 50308 (2011–2026), 54238 (2016–2026); Agassiz RCS 706 (1988–2026); Chilliwack South 51978 (2018–2026) | V: ECCC Station Inventory |
| Irrigation | none | U |
| Current rotation evidence | AAFC ACI 2011–2024 class history; AAFC Crop Rotations 2017–2020 | V products exist (B2.11) |

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FV0 Corn only (baseline) | bare | bare | bare | bare/tillage | plant | corn | corn | corn | harvest late Sept (U) | bare | bare | bare |
| FV1 Corn + fall rye cover | rye | rye | rye | terminate at stem elongation | plant corn | corn | corn | corn | harvest; drill rye late Sept | rye | rye | rye |
| FV2 Corn + Italian ryegrass relay | IRG | IRG | IRG cut/graze | terminate | plant corn | broadcast IRG at 6-leaf | corn + IRG | corn + IRG | harvest; IRG released | IRG | IRG | IRG |
| FV3 3-yr grass-legume hay then corn (hay year) | sod | sod | sod | growth | cut 1 | growth | cut 2 | growth | cut 3 | sod | sod | sod |

Notes (V unless marked): fall rye late-Sept planting improves survivability; terminate at stem elongation; uses significant spring moisture; allelopathic to following alfalfa; ergot risk; DM 3,360–10,800 kg/ha (BC fall rye factsheet: https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/agriculture-and-seafood/agricultural-land-and-environment/soil-nutrients/cover-crops/fall_rye_final.pdf ). IRG relay: seed between rows at corn 6-leaf; earlier-harvested shorter-season corn increases relay growth; relay biomass 0.3–1.2 t DM/ha at corn harvest; tetraploid biennials best (V via https://bcfoodweb.ca/node/479 and https://www.bcclimatechangeadaptation.ca/app/uploads/FI17-Final-Report-Innovative-Corn-Practices-2023.pdf ); IRG winterkills in many regions but overwinters in mild zones (V, BC annual ryegrass factsheet). FV3 species mix U ("example mix").

#### Preset SR (Salmon River / Shuswap, drought): irrigated hay in the lower Salmon River valley [M]

| Item | Value | Status / source |
|---|---|---|
| Centre | 50.62 N, −119.33 W (lower Salmon River valley near Silver Creek, upstream of Salmon Arm) | U: representative; move onto a pixel classed Pasture/Forages in ACI; must lie inside the area of order M0238_2023 (check the order's map: https://www.bclaws.gov.bc.ca/civix/document/id/mo/mo/m0238_2023 ) |
| Field | 20 ha (wheel-line / pivot hay field) | U |
| Soil | Valley-bottom alluvium / fluvial terraces; Interior Chernozemic or Brunisolic | U: confirm with BC Soil Information Finder https://www2.gov.bc.ca/gov/content/environment/air-land-water/land/soil/soil-information-finder and SoilGrids (B2.12) |
| Slope / elevation | 0–3% / ~380–420 m | U until computed |
| ECCC stations | Salmon Arm CS 6843 (1991–2026); Vernon Auto 46987 (2005–2026); Kamloops A 51423 (2013–2026) and legacy 1275 (1951–2013) for the Thompson climatology; Falkland Salmon Valley 1262 (1959–1986, historical only) | V: ECCC Station Inventory |
| River gauge | Salmon River near Salmon Arm (WSC 08LE021) for low-flow context | U: confirm station ID at https://wateroffice.ec.gc.ca or api.weather.gc.ca hydrometric collections |
| Irrigation | surface/groundwater licence, 1 Apr–30 Sept term; licence volume user input (m³) | V term dates (news); default volume U |
| Event anchors | mid-June 2023 mailouts (−50% requested); 16 Aug 2023 order; 30 Sept 2023 expiry | V (release and news) |

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SR0 Alfalfa / alfalfa-grass, 2 cuts (baseline) | dormant | dormant | dormant | green-up | growth, irrigate | cut 1 | regrowth, irrigate | cut 2 (irrigation at risk of order) | aftermath graze | dormant | dormant | dormant |
| SR1 Alfalfa with barley break year (year 6) | stubble | bare | bare | seed barley | barley | barley | greenfeed/silage harvest | re-seed alfalfa late Aug | establishing | establishing | dormant | dormant |
| SR2 1/5 of stand in fall-seeded winter cereal silage (cereal year) | rye/triticale | dormant | green-up | rapid growth on spring moisture | light irrigation | silage harvest early–mid June | bare or short annual | fall-seed next | establishing | establishing | dormant | dormant |
| SR3 Sainfoin-grass hay on the well-drained bench | dormant | dormant | dormant | green-up | growth, irrigate | cut 1 | regrowth | cut 2 / graze | aftermath | dormant | dormant | dormant |

Notes (V unless marked): cereals are "the most commonly grown alternatives" when irrigation is limited; fall rye suitable if fall moisture; spring rye more drought tolerant than barley; oats less than barley (V, BC 2005 factsheet: https://www.irrigationtoolbox.com/ReferenceDocuments/Extension/BCExtension/665000-6.pdf ). Alfalfa goes dormant rather than dying under drought (V, BC drought guide: https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/agriculture-and-seafood/agricultural-land-and-environment/biodiversity/grazing-management-guide/15_-_managing_grazing_lands_during_drought.pdf ). Sainfoin: drought tolerant, non-bloat, no "wet feet", no acidity/salinity (V: https://www.bcclimatechangeadaptation.ca/app/uploads/BF04-FactSheet-Non-bloat-Legumes-2023.pdf ). SR2's point is that the water-intensive growth happens before an August order; the tool quantifies ETc by month so this is visible.

#### Preset CA (Sacramento Valley, data-rich ceiling): Colusa County rice [S, but data pulls are [M] so the adapter is proven]

| Item | Value | Status / source |
|---|---|---|
| Centre | 39.15 N, −122.10 W (west of Williams, Colusa County) | U: pick a CDL rice (2021) → fallow (2022) → rice (2023) pixel block |
| Field | 60 ha rice check (laser-levelled) | U |
| Soil | SSURGO map unit via Soil Data Access: drainage class, hydrologic group, AWC, texture | V endpoint (research-findings ✓); values computed |
| Stations | CIMIS 250 Williams (formerly Colusa) (V: https://cimis.water.ca.gov/Stations.aspx ); NOAA NCEI daily for Colusa/Williams (U station id) | |
| Water | CDEC reservoir storage (Shasta SHA, Oroville ORO) and Sacramento River; DWR groundwater; SGMA basin status (Colusa Subbasin) | V endpoints exist (research-findings); U details |
| Insurance | USDA RMA cause-of-loss, Colusa County, rice, 2010–2024 | V source: https://www.rma.usda.gov/tools-reports/summary-business/cause-loss |

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CA0 Continuous rice (baseline) | flooded/bare | drain | prep | flood, seed late Apr–May | rice | rice | rice | rice | drain, harvest Sept–Oct | straw/decomp flood | winter flood (habitat) | winter flood |
| CA1 Rice with winter cover (vetch/cereal) instead of winter flood | cover | cover | terminate | flood, seed | rice | rice | rice | rice | harvest | drill cover | cover | cover |
| CA2 Rice–fallow/safflower in low-allocation years (dry-year plan) | bare | bare | safflower plant | safflower | safflower | safflower | harvest | bare | bare | bare | bare | bare |
| CA3 Rice–dry-land small grain (wheat) rotation (grain year) | wheat | wheat | wheat | wheat | heading | harvest June | bare | bare | bare | bare | drill wheat | wheat |

All CA calendars U (typical Sacramento Valley timing; confirm with UC Rice Production manual https://rice.ucanr.edu/ before shipping). Rice Kc not verified in this research; FAO-56 Table 12 lists rice (U: read values). The CA preset is where OpenET measured ET is compared against modelled ETc.

### B2. Data pipeline

General rules:
- One field = one polygon (GeoJSON, EPSG:4326 stored; EPSG:32610 for BC and EPSG:32610 for CA working CRS: both are UTM zone 10N (V)).
- Two analysis grids (B2.14): **field grid** (30 m HLS-aligned cells inside the polygon → zones and field statistics) and **regional grid** (the 9 km EASE-Grid 2.0 SMAP cell containing the centroid, plus its 11 × 11 neighbourhood for the Trends map).
- Common time step: daily master table 2015-01-01 to 2025-12-31; longer tables per source for climatology (POWER 1981–, MODIS 2000–, IMERG 2000–, GRACE 2003–).
- Cache everything Saturday; the demo never calls a remote server. Layout `data/cache/<preset_id>/<dataset>.parquet` + `<dataset>.meta.json` {url, params, fetched_at, footprint_geojson, native_res_m, timestep, units, fill_value, auth}. Rasters as COG in `rasters/`.
- Time zones: POWER and IMERG daily are UTC; ECCC/CIMIS/NOAA daily are local. Compare at monthly totals or allow ±1 day for events.
- Fill values: POWER −999; SMAP quality flag; HLS Fmask; MODIS pixel reliability.

#### B2.1 NASA POWER [M] — no auth
- `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR&community=AG&longitude=-119.33&latitude=50.62&start=19810101&end=20251231&format=JSON` (V structure: https://power.larc.nasa.gov/docs/services/api/temporal/daily/ ; max 20 params; 0.5° grid; cache to avoid blocking).
- Regional (Trends map) [S]: `/api/temporal/daily/regional?parameters=T2M_MAX&community=AG&longitude-min=…&latitude-min=…&…` one parameter per request (V limit), or use the monthly/climatology endpoints.
- Derived: Hargreaves ETo (FAO-56 eq. 52), frost/heat days, heatwave days (≥ 3 consecutive days T2M_MAX ≥ 30 °C, U definition).

#### B2.2 GPM IMERG daily [M] — Earthdata login
- GPM_3IMERGDF V07, 0.1°, ~June 2000–present (V): https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergdf-07
- Access, in order: (1) GES DISC Hydrology Data Rods / Giovanni time series (inputs variable, location, startDate, endDate, type; V) pattern `https://hydro1.gesdisc.eosdis.nasa.gov/daac-bin/access/timeseries.cgi?variable=GPM:GPM_3IMERGDF_07:precipitation&startDate=2015-01-01T00&endDate=2025-12-31T23&location=GEOM:POINT(-119.33,%2050.62)&type=asc2` (U exact variable string; how-to: https://disc.gsfc.nasa.gov/information/howto?title=How%20to%20Access%20the%20Hydrology%20Data%20Rods%20Time%20Series%20API%20Using%20Python ); (2) AWS Open Data mirror https://registry.opendata.aws/nasa-gpm3imergdf/ (V listed; U anonymous access); (3) OPeNDAP subset with .netrc.
- Footprint ≈ 11 × 7 km ≈ 80 km² at 49–51°N; 11 × 9.6 km at 39°N.

#### B2.3 SMAP [M] — Earthdata login
- SPL3SMP_E.006 (9 km, daily, 31 Mar 2015–present) and SPL4SMGP.008 (L4 surface + root-zone, 9 km, 3-hourly, model-assimilated) via AppEEARS point/area requests (V: both listed at https://appeears.earthdatacloud.nasa.gov/api/product ). Layers: `Soil_Moisture_Retrieval_Data_AM/soil_moisture`, `retrieval_qual_flag`; L4 `sm_rootzone`, `sm_surface`.
- Area request for the 11 × 11 cell neighbourhood (~100 × 100 km) for the Trends map [S].
- Winter frozen-ground gaps: show as "no data", never interpolate across them in the Interior.
- Derived: daily percentile vs same-calendar-month 2015–2025 distribution; dry-spell flag (B5.3); **lead time** before 2023-08-16 (B8.1 check 9).

#### B2.4 HLS (Harmonized Landsat Sentinel-2, 30 m) [M] — Earthdata login
- HLSL30.020 and HLSS30.020 via AppEEARS (V listed), 2015–present (L30), 2017–present (S30) (U exact start). Layers: B02 blue, B03 green, B04 red, B05 NIR (L30) / B8A (S30), B06 SWIR1, B07 SWIR2, Fmask. Also HLSL30_VI / HLSS30_VI (pre-computed indices, V listed) as a shortcut.
- Primary source for bare-field, transitions and the ML classifier (one harmonised 30 m record). Sentinel-2 L2A at 10 m (B2.5) is the visual layer and the pseudo-label source.

#### B2.5 Sentinel-2 L2A (10 m) [M] — no account
- STAC: Microsoft Planetary Computer `https://planetarycomputer.microsoft.com/api/stac/v1` collection `sentinel-2-l2a` (V), sign with `planetary-computer`; or Earth Search `https://earth-search.aws.element84.com/v1` collections `sentinel-2-c1-l2a`, `sentinel-2-l2a` (V), anonymous. Assets B04, B08, SCL. Reliable from ~2019 (U).

#### B2.6 Landsat C2 L2 (30 m, 1984–) [S] — MPC `landsat-c2-l2` (V). Extends the bare-field climatology; QA_PIXEL bits U (check `classification:bitfields`). Skip if HLS suffices.

#### B2.7 MODIS MOD13Q1.061 NDVI/EVI (250 m, 16-day, 2000-02-18–present) [M] — Earthdata login
- Via AppEEARS (V listed). Layers `_250m_16_days_NDVI`, `_250m_16_days_EVI`, `_250m_16_days_pixel_reliability` (keep 0–1). Scale factor 0.0001.
- Use: 25-year vegetation baseline for the stress z-score (the HLS record is too short for a robust climatology); regional NDVI on the Trends map (aggregate 250 m → 9 km cell).

#### B2.8 ECOSTRESS (70 m, ISS-dependent revisit, 2018–) [M for point series; S for rasters] — Earthdata login
- AppEEARS products (V listed): `ECO_L2T_LSTE.002` (LST, K), `ECO_L3T_JET.002` (ET instantaneous and daily, mm/day), `ECO_L4T_ESI.002` (evaporative stress index), `ECO_L3T_ET_ALEXI.002`.
- Use: LST anomaly and ESI as stress features (B6); in-field hotspots (B7.3); ET as a check on modelled ETc on clear summer dates. Caveat: irregular overpass times; compare LST with POWER T2M_MAX only as a relative anomaly, not absolute.

#### B2.9 GRACE / GRACE-FO data assimilation drought indicators [M for time series; S for map] — Earthdata login
- GRACEDADM_CLSM025GL_7D V3.0: 0.25°, weekly, Feb 2003–present with 3–6 month latency; layers groundwater percentile, root-zone soil-moisture percentile, surface soil-moisture percentile (V: https://www.earthdata.nasa.gov/data/catalog/ges-disc-gracedadm-clsm025gl-7d-3.0 ; AWS mirror https://registry.opendata.aws/nasa-grace-da-dm/ V listed). Access via GES DISC OPeNDAP/HTTPS subset or the AWS bucket (U anonymous).
- Use: long-term water-storage trend chart; Trends map layer; groundwater context for SR (groundwater licences were included in the 2023 order) and CA (SGMA).

#### B2.10 Elevation [M] — NASADEM via MPC `nasadem` or `cop-dem-glo-30` (V); SRTMGL1_NC.003 via AppEEARS (V). 30 m. Slope %, local depressions (B7.3).

#### B2.11 Crop history
- **BC [M]:** AAFC Annual Crop Inventory 30 m GeoTIFF per year `https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/data_donnees/tif/` (V ✓) and dataset page https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9 ; AAFC Crop Rotations product `https://agriculture.canada.ca/atlas/data_donnees/cropRotation/data_donnees/tif/crop_rotation_2017_2020.zip` (V listed). Class codes from the legend file (U: do not hard-code).
- **CA [M]:** USDA Cropland Data Layer 30 m, 2008–2024, via CroplandCROS or GeoTIFF download https://www.nass.usda.gov/Research_and_Science/Cropland/Release/ (V exists); CropScape API unreliable (research-findings). Rice class code 3, Fallow/Idle 61 (U: check legend).

#### B2.12 Soils
- **BC [M]:** SoilGrids v2 point query `https://rest.isric.org/soilgrids/v2.0/properties/query?lon=-119.33&lat=50.62&property=clay&property=sand&property=silt&property=soc&property=bdod&depth=0-5cm&depth=5-15cm&depth=15-30cm&value=mean` (V endpoint ✓; U parameter spelling) → texture class, SOC; 250 m, label "global model estimate". Drainage class by hand from the BC handbook / Soil Information Finder for the presets.
- **CA [M]:** Soil Data Access `POST https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest` with `{"format":"JSON","query":"<SQL>"}`; SQL pattern: `SELECT mu.mukey, mu.muname, c.compname, c.drainagecl, c.hydgrp, c.comppct_r FROM mapunit mu JOIN component c ON c.mukey=mu.mukey WHERE mu.mukey IN (SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT(-122.10 39.15)')) ORDER BY c.comppct_r DESC` and AWC from `chorizon.awc_r` (U exact function/column names; endpoint V ✓).

#### B2.13 Ground stations and water
- **BC [M]:** ECCC bulk CSV `https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=6843&Year=2023&Month=1&Day=1&timeframe=2&submit=Download+Data` (V pattern; one call per year); alternative `https://api.weather.gc.ca/collections/climate-daily/items?...` (V ✓ per research-findings). Hydrometric: `api.weather.gc.ca/collections/hydrometric-daily-mean/items?STATION_NUMBER=08LE021` (U station). 
- **CA [M]:** CIMIS `https://et.water.ca.gov/api/data?appKey=KEY&targets=250&startDate=2015-01-01&endDate=2025-12-31&dataItems=day-eto,day-precip,day-air-tmp-min,day-air-tmp-max` (V endpoint ✓; U item names); CDEC `https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet?Stations=SHA,ORO&SensorNums=15&dur_code=D&Start=2015-01-01&End=2025-12-31` (V endpoint ✓; U sensor codes); DWR groundwater via `https://data.cnra.ca.gov/api/3/action/package_search?q=groundwater+levels` (V ✓); OpenET `POST https://openet-api.org/raster/timeseries/point` with key, body `{date_range:[…], interval:"monthly", geometry:[lon,lat], model:"Ensemble", variable:"ET", reference_et:"gridMET", units:"mm", file_format:"JSON"}` (V endpoint ✓; U body fields); NOAA NCEI `https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=…` (V ✓; U station).

#### B2.14 Common analysis grids [M] (the brief's "harmonize … to a common analysis grid")
- **Field grid:** 30 m cells aligned to the HLS tile grid, clipped to the polygon. Fine data (HLS, S2 resampled 10→30 m by mean, ECOSTRESS 70→30 m nearest, NASADEM, CDL/ACI) are expressed per cell; field statistics (median, p10, p90) and zone statistics (B7.3) derive from it.
- **Regional grid:** EASE-Grid 2.0 9 km cells (SMAP native). IMERG 0.1° (area-weighted mean), POWER 0.5° (nearest), GRACE 0.25° (area-weighted), MODIS 250 m (mean) are resampled onto it. The field's cell is the "regional signal"; the 11 × 11 neighbourhood is the Trends map.
- Never resample coarse data down to the field grid (it invents information); the UI shows both grids on one page with the footprints drawn.
- Weekly **feature table** per field (`features_weekly.parquet`): one row per ISO week with field-grid stats (NDVI median/p10/p90, BSI, LST anomaly, ESI, slope-weighted bare fraction) and regional-grid values (SMAP sm and percentile, IMERG 7-day total, POWER Tmax/Tmin/ETo, GRACE percentiles, MODIS NDVI anomaly). GEDI biomass [S] only where footprints fall in the field (unlikely for the presets).

#### B2.15 News sources [M] (cached) — see B9.

#### B2.16 Prices and funding [S]
- Hay prices: USDA AMS My Market News API (key) `https://marsapi.ams.usda.gov/services/v1.2/reports` (V exists; U report slugs for California hay); Statistics Canada farm product prices table 32-10-0077-01 and crop area/yield 32-10-0359-01 (V tables exist; U endpoint pattern for CSV download via `https://www150.statcan.gc.ca/t1/tbl1/en/dtl!downloadDbLoadingData-nonTraduit.action?pid=3210007701&latestN=…`).
- Funding: BC IAF Climate Agri-Solutions Fund covers 85% of cover-crop costs (cap $100k vs $30k conflicting, U; confirm at https://iafbc.ca ); USDA EQIP practice 340 cover crop per-acre rates from state payment schedules (U).
- USDA NASS Quick Stats (key) for county yields/acres (V exists).

#### B2.17 Non-NASA weather [S]
- Open-Meteo forecast / seasonal (no key, V exists) for a "next 6 months" strip; NOAA CPC seasonal outlook (ArcGIS REST, V exists); ECCC CanSIPS (U collection IDs). Only as context; never in scores.

### B3. Shared JSON schemas

Every numeric leaf is a `SourcedNumber`; agents must not emit bare numbers.

```json
// SourcedNumber
{ "value": 0.95, "unit": "Kc", "low": 0.90, "high": 1.05,
  "method": "lookup | computed | assumed | model",
  "source": { "id": "fao56_table12", "title": "FAO-56 Table 12, Alfalfa hay, Kc mid", "url": "https://www.fao.org/4/x0490e/x0490e0b.htm", "accessed": "2026-11-14", "verified": true },
  "note": "subhumid-climate value" }
```

```json
// Location
{ "id": "sr_salmon_river_hay", "name": "Lower Salmon River hay field (example)", "region_adapter": "bc", "regime": "drought",
  "geometry": {"type":"Polygon","coordinates":[[…]]}, "centroid": {"lon": -119.33, "lat": 50.62}, "area_ha": {…SourcedNumber},
  "crs_working": "EPSG:32610",
  "soil": { "drainage_class": "well (U)", "texture_class": "from SoilGrids", "soc_g_kg": {…}, "awc_mm": {…}, "hydrologic_group": null, "sources": [ {"id":"soilgrids_v2","url":"https://rest.isric.org/soilgrids/v2.0/properties/query?…"} ] },
  "terrain": { "slope_mean_pct": {…}, "slope_p90_pct": {…}, "elev_m": {…}, "low_spot_fraction": {…} },
  "irrigation": { "available": true, "licence_m3_per_yr": null, "term": ["04-01","09-30"], "system": "wheel line (U)" },
  "market_preference": "feed_own_herd | sell_hay | no_preference",
  "stations": [ {"name":"Salmon Arm CS","station_id":6843,"distance_km":9.0,"years":[1991,2026]} ],
  "regional_cell": { "grid": "EASE2_G9km", "row": 0, "col": 0, "footprint": {…geojson} },
  "datasets": { "power": {"cache":"…","footprint_area_m2":2.0e9,"native_res_m":55000,"timestep":"daily","period":["1981-01-01","2025-12-31"]},
                "imerg": {…}, "smap_l3": {…}, "smap_l4": {…}, "hls": {…}, "s2": {…}, "modis": {…}, "ecostress": {…}, "grace": {…}, "dem": {…}, "crop_history": {…}, "stations": {…}, "news": {…} },
  "observed_cover": { "typically_bare_doy_ranges": [[290,110]], "bare_doy_file": "…/bare_doy.json", "years_used": [2019,…,2025], "detector": "rule | ml | consensus" },
  "events": [ {"date":"2023-08-16","type":"irrigation_order","title":"Fish population protection order, lower Salmon River","url":"https://news.gov.bc.ca/releases/2023FOR0052-001305","verified":true},
              {"date":"2023-06-15","type":"request","title":"Mailouts requesting up to 50% reduction (mid-June)","url":"…","verified":true} ] }
```

```json
// Crop (BC factsheets + FAO-56 + USDA PLANTS)
{ "id": "fall_rye", "name": "Fall rye", "family": "Poaceae", "role": ["cover","forage"], "legume": false, "root": "fibrous, medium depth",
  "kc": {"ini":{…0.40 assumed=winter wheat},"mid":{…1.15},"end":{…0.25-0.4}}, "stage_lengths_days": {"ini":30,"dev":60,"mid":60,"late":30,"source":"fao56_table11 winter wheat proxy (U)"},
  "cover_by_stage": {"ini":0.2,"dev":0.6,"mid":1.0,"late":0.8},
  "ratings_0_4": { "erosion_reduction":{…}, "soil_builder":{…}, "lasting_residue":{…}, "nitrogen_fixation":{"value":0}, "nitrogen_scavenging":{…}, "compaction_reduction":{…}, "forage_harvest_value":{…}, "weed_suppression":{…}, "biofumigation":{…}, "tolerance_flood":{…}, "tolerance_drought":{…} },
  "dry_matter_yield_kg_ha": {"value":7000,"low":3360,"high":10800,"source":{"id":"bc_factsheet_fall_rye","verified":true}},
  "drainage_classes_ok": ["very well","well","moderately well","somewhat poor","poorly"],
  "seeding_window": {"start":"09-01","end":"10-15","best":"late September","verified":true}, "termination": "stem elongation",
  "pest_notes": ["ergot risk"], "cautions": ["allelopathy to following alfalfa","N immobilisation if large biomass incorporated","uses significant spring moisture"],
  "seed_cost_per_ha": {"value":60,"low":40,"high":90,"unit":"CAD/ha","method":"assumed"},
  "explainer_card": "cover_crop",
  "sources": [ {"id":"bc_factsheet_fall_rye","url":"https://www2.gov.bc.ca/assets/gov/…/fall_rye_final.pdf"} ] }
```

```json
// RotationStrategy
{ "id": "sr2_cereal_silage", "location_id": "sr_salmon_river_hay", "name": "1/5 of stand in fall-seeded cereal silage", "is_baseline": false, "cycle_years": 5,
  "calendar": [ {"year":1,"crop_id":"winter_triticale","plant":"09-10","harvest":"06-10","role":"forage","timing_source":"assumed (U)"}, … ],
  "exposure": { "bare_days_per_year":{…}, "exposed_rain_days":{…}, "exposed_frost_days":{…}, "exposed_heat_days":{…}, "exposed_dry_days":{…},
                "replay": {"2021":{…},"2023":{…}}, "scenario": {"dT_c":0,"dP_pct":0} },
  "water": { "etc_mm_season":{…}, "irrigation_need_mm":{…}, "etc_by_month_mm":[…12 SourcedNumbers], "share_of_etc_before_aug16":{…} },
  "scores": { "water_use":{…}, "forage_value":{…}, "n_fixation":{…}, "erosion":{…}, "organic_matter":{…}, "market":{…},
              "pest_break":{…}, "infiltration":{…}, "n_scavenging":{…}, "income":{…} },
  "composite": {"value":58,"low":47,"high":66,"weights_used":{…}},
  "risk_profile": { "rma_cause_of_loss": null },
  "funding": [ {"program":"BC IAF Climate Agri-Solutions Fund","share":0.85,"cap_cad":{"value":30000,"low":30000,"high":100000,"method":"assumed"},"url":"https://iafbc.ca","verified":false} ],
  "brief": { "why":[{"text":"…","source_ids":["smap_l3","fao56_table12"],"numbers_used":[…],"author":"llm|template","checked":true}],
             "evidence":[…], "benefits":[…], "gaps":[…], "local_review":[{"item":"…","severity":"high"}], "explainer_cards":["drought_tolerant","cover_crop"],
             "llm_report": {"sentences":9,"numbers_checked":23,"rejected":1,"model":"…","cached_at":"…"} },
  "uncertainty": { "dataset_disagreement":{…}, "scale":{…}, "agronomic_gap_count":3, "detector_disagreement_pct": 9 } }
```

```json
// ModelReport (one per detector/anomaly model per location)
{ "id": "bare_rf_v1", "task": "bare_cover | transition | stress_anomaly", "method": "rule_ndvi | random_forest | hist_gbt | zscore | isolation_forest",
  "features": ["ndvi","bsi","ndvi_30d_slope",…], "labels": "s2_scl_pseudo | cdl_fallow | aci_class", "split": {"train_years":[2019,2020,2021,2022],"test_years":[2023,2024,2025]},
  "metrics": {"accuracy":0.91,"f1_bare":0.88,"transition_mae_days":9}, "confusion": [[…]], "feature_importance": [{"feature":"ndvi","importance":0.41},…],
  "disagreement_with": {"rule_ndvi": 0.09}, "notes": "pseudo-labels from Sentinel-2 SCL; not ground truth" }
```

```json
// NewsItem
{ "date":"2023-08-16","title":"Targeted actions protect chinook runs in Thompson Okanagan","source":"BC Gov News","url":"https://news.gov.bc.ca/releases/2023FOR0052-001305","rank":1,"place_match":["Salmon River"],"query_id":"sr_2023_drought","signal":{"dataset":"smap_l3","value_pct":6,"lead_days":null} }
```

API contract (lock in hour 1): `GET /api/locations`; `GET /api/locations/{id}`; `GET /api/locations/{id}/daily?from&to`; `GET /api/locations/{id}/features/weekly`; `GET /api/locations/{id}/strategies`; `POST /api/locations/{id}/score` body `{weights, constraints, market_preference, replay_year?, scenario:{dT_c,dP_pct}}`; `GET /api/locations/{id}/models` (ModelReports); `GET /api/locations/{id}/zones` (GeoJSON cells with zone classes); `GET /api/locations/{id}/trends?layer=smap_anomaly|heatwave_days|grace_gw_pct|precip_anomaly&year=` (regional grid cells); `GET /api/locations/{id}/news?from&to`; `GET /api/glossary`; `GET /api/crops/{id}`. Frontend builds against `fixtures/*.json` from hour 2.

### B4. Scoring model

Every score 0–100 with low/high; baseline is the reference; "rule of thumb, not a model" printed under every score. Factsheet 5-step bars coded 0–4.

#### B4.1 Water use [M]
- ETo daily: Hargreaves from POWER (FAO-56 eq. 52); Penman-Monteith with RH2M/WS2M/radiation as upgrade [S]. In CA compare with CIMIS ETo (station) and OpenET ET (field).
- ETc = Σ Kc(d) × ETo(d) from the FAO-56 single-coefficient curve (stage lengths + plant/harvest). Bare Kc 0.15 (U).
- Verified FAO-56 Table 12 values (V): alfalfa hay 0.40/0.95/0.90; grazing pasture 0.40/0.85–1.05/0.85; rye grass hay 0.95/1.05/1.00; clover hay 0.40/0.90/0.85; winter wheat (frozen soils) 0.40/1.15/0.25–0.4; barley/oats/spring wheat mid 1.15, end 0.25 (ini 0.3 U); maize mid 1.20, end 0.60–0.35 (ini 0.3 U; silage harvested before end stage → Kc≈1.0 at harvest, U). Fall rye/triticale → winter wheat values (assumed, ±0.1); sainfoin → alfalfa values (assumed, ±0.1); rice, safflower U (read Table 12). Alfalfa season: last −4 °C to first −4 °C (V, Table 11 footnote).
- Irrigation need `I = Σ max(0, ETc − 0.8 P)` over the licence term (0.8 U), with P from IMERG, station and POWER → range. Also `share_of_etc_before_aug16` for SR (how much of the water demand falls before a possible order).
- Score `water_use = 100 × clamp(1 − I / I_max)`; wet preset scores on ETc and is labelled "water demand (rain-fed)".

#### B4.2 Forage value [M] — `100 × Σ(rating_forage/4 × harvestable_months_share × min(DM/10,000,1)) / cycle_years`; DM ranges from factsheets (fall rye V); alfalfa 8,000–14,000 and silage corn 15,000–20,000 kg DM/ha U.

#### B4.3 Nitrogen fixation [M] — `100 × Σ(legume ? rating_nfix/4 × months_growing/12 : 0) / cycle_years`. Hairy vetch highest N fixer among listed legumes; red clover "ample" (V factsheets). Alfalfa 4 (U).

#### B4.4 Erosion reduction [M] — exposure-based: `E = Σ_d (1 − cover(d)) × rain_risk(d) × slope_factor`, `slope_factor = 1 + slope_mean_pct/5` (U proxy, not RUSLE); `erosion = 100 × (1 − E/E_baseline)` blended 70/30 with the factsheet "Erosion Reduction" rating. In-field version uses zone slope (B7.3).

#### B4.5 Organic matter [M] — `100 × [0.5 × mean(soil_builder, lasting_residue)/4 + 0.3 × perennial_years/cycle_years + 0.2 × (1 − bare_days/365)]`.

#### B4.6 Market suitability [M] — table + inputs: on-farm use (dairy → silage/relay feed high; beef → hay/greenfeed), `market_preference` (sell_hay boosts cash-hay crops; feed_own_herd boosts relay/silage), equipment, seed cost class. Range ±25; always emits a local-review item.

#### B4.7 Pest-cycle break [M] — `pest_break = 100 × min(1, distinct_families/3) × (1 − max_consecutive_same_family_years/cycle_years)`; families from Crop.family (corn/cereals/rice/grasses = Poaceae; legumes = Fabaceae; mustard/radish = Brassicaceae; safflower = Asteraceae). Add factsheet pest notes (ergot on rye; corn rootworm/wireworm text U) to local_review. Rule of thumb; no pest model exists (research-findings).

#### B4.8 Infiltration (soil structure) [M] — `100 × [0.5 × compaction_reduction_rating/4 + 0.3 × root_depth_class/2 + 0.2 × cover_months/12]`, root class deep taproot = 2, medium = 1, shallow = 0 (from factsheet text; U mapping).

#### B4.9 Nitrogen scavenging [M] — `100 × nitrogen_scavenging_rating/4 × fall_winter_cover_months/6` (BC factsheets rate "Nitrogen Scavenging"; V bars exist). Shown as a nutrient-cycling line next to N fixation.

#### B4.10 Supplemental income [S] — `income_per_ha = forage_sold_DM × price_range − seed_cost + funding_share × establishment_cost` as a $/ha range; prices from AMS/StatCan (U), funding from IAF/EQIP (U). Always "range, confirm locally". Score `income = 100 × clamp(income/income_max)`.

#### B4.11 Historical loss risk (CA only) [S] — RMA cause-of-loss 2010–2024 for county × commodity: `share_drought = indemnity_drought / indemnity_total`, `share_excess_moisture`, shown as a profile bar on each CA strategy's crops; not in the composite.

#### B4.12 Weighting, ranges, scenarios [M]
- Sliders w_i ∈ [0,4] for the six brief priorities plus pest_break, infiltration, income (default 0 for the extra three so the brief's six dominate); `composite = Σ W_i s_i`, low/high likewise.
- Tie rule: intervals overlapping > 50% of the smaller interval → "tie within uncertainty".
- Scenario sliders: ΔT ∈ [−1, +4] °C added to Tmin/Tmax (changes Hargreaves ETo, frost/heat days, alfalfa season dates), ΔP ∈ [−30, +30]% scaling daily P (changes irrigation need and extreme-rain-day counts; note "simple scaling, not a climate model"). Recompute ETc, I, exposure, scores live client-side from the cached daily table. Preset buttons "2050s typical" from ClimateData.ca for the region (U values; link https://climatedata.ca ).
- Ranges: deterministic min/max over Kc low/high, ETo ±15%, three precipitation sources, bare-NDVI threshold 0.15–0.30, rain threshold 25–50 mm; Monte Carlo N=200 [S].

### B5. Bare-field detection, transitions and risk windows

#### B5.1 Rule-based detector [M]
- Per HLS observation (and S2 scene): mask Fmask cloud/shadow/snow (HLS Fmask bits 1 cloud, 2 adjacent, 3 shadow, 4 snow; U bit order, check product guide) / SCL ∉ {3,8,9,10,11}; drop if valid fraction < 0.5.
- NDVI = (NIR − Red)/(NIR + Red); BSI = ((SWIR1 + Red) − (NIR + Blue))/((SWIR1 + Red) + (NIR + Blue)).
- Cover class: bare if NDVI < 0.20; partial 0.20–0.35; covered > 0.35 (U rule of thumb; cite https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology ; threshold tunable 0.15–0.30 for the range).
- Transitions: green-up = first of 3 consecutive observations with NDVI > 0.35 after a bare period; senescence/harvest = first of 2 consecutive observations with NDVI drop > 0.2 from the 30-day max.
- Interpolate ≤ 30-day gaps; otherwise `unknown` (hatched "no clear view").

#### B5.2 ML detector [M] — see B6.1.

#### B5.3 Risk days (regional grid) [M]

| Risk | Rule | Status | Data |
|---|---|---|---|
| Extreme rain | P ≥ 50 mm/day coast, ≥ 25 mm/day interior; 3-day ≥ 75 mm; plus data-driven 95th percentile of wet days | U (ECCC warning criteria are of this order: https://www.canada.ca/en/environment-climate-change/services/types-weather-forecasts-use/public/criteria-alerts.html ) | IMERG; station; POWER |
| Frost | T2M_MIN ≤ 0 °C light; ≤ −4 °C killing | V for −4 °C (FAO-56) | POWER; station |
| Heat | T2M_MAX ≥ 30 °C; ≥ 35 °C severe; heatwave = ≥ 3 consecutive days ≥ 30 °C | V 35 °C text (FAO-56); 30 °C U | POWER; ECOSTRESS LST anomaly as field-scale confirmation |
| Dry spell | SMAP AM sm < 20th percentile of same month for ≥ 14 valid days; or IMERG 30-day < 50% of climatology | U convention | SMAP; IMERG |
| Water-storage low [S] | GRACE groundwater percentile < 20 for ≥ 8 weeks | U | GRACE-DA |

#### B5.4 Exposure overlay [M] — `exposed_<risk>_days(strategy, year) = Σ_d [cover(d) < 0.5] × risk(d)`; baseline uses observed cover (consensus of detectors) where known; alternatives use modelled cover; say so on screen. Replay years: 2021, 2023 (BC); 2022, 2023 (CA).

#### B5.5 Current-crop vulnerability strip [M] — weeks of the growing season flagged by the stress models (B6.2) for the existing crop, drawn under the calendar as "both models", "one model", "none".

### B6. AI ("SI") section

All models are small, trained offline on Saturday, cached as ModelReports and per-date predictions; the demo never trains live. Everything here answers the brief's "compare different SI or statistical approaches … highlight seasonal transitions, bare-field periods, or times when current crops show increased stress … explain how the model interprets uncertainty".

#### B6.1 Bare-cover and transition detection: rule vs ML [M]

- **Unit of prediction:** one HLS observation date × field (field-median features) for the field-level calendar; one HLS observation × 30 m cell for the zone map [S].
- **Features (per observation):** NDVI, EVI, NDWI (Green−NIR), BSI, NBR2 (SWIR1−SWIR2)/(SWIR1+SWIR2), red/NIR/SWIR1 reflectances; temporal: NDVI 30- and 60-day rolling mean/min/max, 30-day NDVI slope, days since last valid observation, NDVI minus MODIS 250 m same-DOY climatology (anomaly); calendar: sin/cos day-of-year; context: SMAP percentile that week, IMERG 7-day total, POWER Tmax 7-day mean, snow flag from Fmask/SCL.
- **Labels:** (i) pseudo-labels from Sentinel-2 SCL on clear days: field majority SCL 5 "not vegetated" → bare, SCL 4 "vegetation" → covered (training only on scenes with ≥ 80% agreement across pixels); (ii) CA: CDL class 61 Fallow/Idle years → bare all year; CDL crop class + regional planting/harvest windows → weak bare/covered labels outside the season; (iii) BC: AAFC ACI class to define crop type (for transition labelling) and to exclude non-agricultural pixels. State on screen: "labels are satellite pseudo-labels and crop-inventory rules, not ground observations".
- **Models:** scikit-learn `RandomForestClassifier(n_estimators=300, class_weight="balanced")` and `HistGradientBoostingClassifier`; 3 classes bare/partial/covered. Rule-based = B5.1 with threshold 0.20.
- **Split:** by year: train 2019–2022, test 2023–2025 (and for CA also test on the 2022 fallow year with train 2019–2021, 2023–2024); additionally hold out one preset entirely for a cross-site test (train FV+CA, test SR) [S].
- **Metrics:** accuracy, F1 (bare), confusion matrix; transition-date MAE in days vs pseudo-label transitions; rule-vs-ML per-date disagreement %; feature importance (permutation).
- **Transitions:** the ML class sequence is smoothed (HMM or 3-observation median) and green-up/senescence dates extracted the same way as the rule; both sets of dates drawn on the calendar.
- **UI:** "Model comparison" panel on the Satellite vs ground page: metrics table, confusion matrix, feature-importance bars, and a per-year strip with disagreement hatched; the calendar has a toggle rule / ML / consensus. Feature importance becomes a brief evidence line ("Bare periods were identified mainly from NDVI and SWIR brightness, with soil-moisture context contributing 8%").
- **Honesty line:** pseudo-labels inherit SCL errors; accuracy is agreement with another satellite product, not with the ground. Printed under the table.

#### B6.2 Crop-stress anomaly: z-score vs isolation forest [M]

- **Unit:** ISO week × field during the growing season of the existing crop (from the baseline calendar), 2015–2025 (MODIS back to 2000 for the NDVI climatology).
- **Features (weekly):** z_NDVI = (NDVI − μ_DOY)/σ_DOY using MODIS 2000–2025 same-week climatology (field's 250 m cell) and HLS where available; z_LST = ECOSTRESS LST minus POWER T2M_MAX same day, standardised against the field's own ECOSTRESS record; ESI (ECO_L4T_ESI) weekly mean; z_SM = SMAP percentile transformed to z; z_ETo (POWER) ; IMERG 30-day anomaly.
- **Method A (statistical):** composite stress z = mean(−z_NDVI, +z_LST, −ESI_z, −z_SM); flag week if composite > 1.0 or if any two of (z_NDVI < −1, z_LST > +1, z_SM < −1) hold.
- **Method B (ML):** `IsolationForest(n_estimators=200, contamination=0.10)` on the weekly feature vector (fit per field on all years; also fit on all years except the test year for a leave-one-year-out variant [S]).
- **Evaluation (no ground truth):** event recall on known stress episodes: BC late-June 2021 heat dome, July–Aug 2023 drought (SR, FV), CA 2021–22 drought; show how many of those weeks each method flags; agreement % between methods; false-positive proxy = flags in wet, cool weeks.
- **UI:** vulnerability strip (B5.5) with legend "both / one / none"; per-week tooltip lists the driving features; brief "evidence" line "Current crop showed stress in N weeks over 2015–2025, mostly late July".

#### B6.3 LLM explanation layer with source checking [M]

- **Input:** the RotationStrategy JSON (SourcedNumbers only, plus the Crop records and the Location soil/terrain), the ModelReports, and sentence templates for why / evidence / benefits.
- **Prompt rules:** write in plain language for a farmer; each sentence must cite `source_ids` from the input and list `numbers_used` (value strings exactly as they appear, with units); do not introduce crops, places, dates or numbers not in the input; one sentence per fact; ≤ 25 words per sentence.
- **Validator (deterministic, runs on every sentence):** extract all numerals (incl. ranges and percentages); each must match a `value`, `low` or `high` of a SourcedNumber referenced in `source_ids` within rounding (±1 unit of the displayed precision); every `source_id` must exist; crop/place names must be in an allow-list built from the input; sentences failing any check are rejected and replaced by the template sentence for that fact. Log counts.
- **Output stored:** `brief.why/evidence/benefits` arrays with `author: "llm"|"template"`, `checked: true`, plus `llm_report` {sentences, numbers_checked, rejected, model, cached_at}. Generation runs offline at build time and is cached; the demo shows cached text and the report footer "AI-written, checked against N sourced numbers; M sentences rejected and replaced".
- **Model:** any hosted LLM API available to the team; keep temperature 0; store prompts in `prompts/brief_v1.md`. If no key is available, the template path alone ships; the footer then reads "template-written".

### B7. Maps and visual layers

#### B7.1 Field picker with footprints [M] — polygon, SMAP/IMERG/POWER/GRACE footprints toggle, scale badges.

#### B7.2 Trends map [M for the field's cell time series; S for the map with slider]
- Regional grid (11 × 11 EASE cells around the field) with a year slider 2003–2025 and layers: SMAP growing-season (May–Sept) soil-moisture anomaly vs 2015–2025 mean (2015+); heatwave days per year (POWER regional; 1981+); GRACE groundwater percentile annual mean (2003+); precipitation anomaly (IMERG 2000+ / POWER 1981+); MODIS May–Sept NDVI anomaly (2000+).
- Side chart: the field's cell as time series for each layer, with the event markers (2021 flood, 2023 order, CA 2022 fallow) and the 2023 lead-time annotation once computed.
- Data: POWER regional endpoint one parameter at a time (V limit) or monthly endpoint; SMAP/MODIS area requests via AppEEARS; IMERG and GRACE bbox subsets from files. Pre-compute annual rasters per layer to small GeoJSON grids.

#### B7.3 In-field zones [M for BC presets; S for CA where fields are laser-levelled]
- From NASADEM 30 m on the field grid: erosion zones by slope class (< 2%, 2–5%, > 5%; U classes) weighted into B4.4; **frost-prone low spots** = cells whose elevation is ≥ 1 m below the focal mean of a 300 m window (U rule of thumb for cold-air pooling; label "candidate"); **stress hotspots** = cells whose mean NDVI anomaly in Jul–Aug of flagged stress years is < −0.5 σ and/or ECOSTRESS LST exceeds the field median by > 2 K on ≥ 2 scenes (U thresholds).
- Honesty: a 12 ha, 0–1% prairie field will show weak zones; show "zones not distinct on this field" rather than inventing them. Rice checks: zones off, hotspots only.

#### B7.4 Scenario panel [M] — ΔT and ΔP sliders (B4.12) with live recompute; shows ETo, ETc, irrigation need, frost/heat/extreme-rain days, exposure before/after.

#### B7.5 Glossary and explainer cards [M]
- Glossary drawer, one card each, linked from every chart label and tooltip: evapotranspiration (ET, ETo, ETc, Kc), soil-moisture anomaly and percentile, NDVI (and what bare/partial/covered mean), frost risk (0 °C vs −4 °C, cold-air pooling), water balance (P − ETc, effective rain, irrigation need), heat stress / LST, groundwater storage (GRACE), pixel/footprint and scale badge, pseudo-label, isolation forest (one sentence). Plain language, one example number from the current field each.
- Crop-role explainer cards (the brief's four): nitrogen-fixing crops, cover crops, deep-rooting crops, drought-tolerant crops; each ~80 words with one factsheet citation; linked from each crop chip in a rotation.

### B8. UI flow and the rotation brief

Users: farmer and adviser side by side; plain language, dual units, acronyms only in tooltips, dataset names in tooltips ("satellite rainfall" → "GPM IMERG").

1. **Pick a field** [M]: three preset cards (Sumas Prairie dairy / Lower Salmon River hay / Colusa rice), "ground data: sparse / rich" badge, map, draw-your-own (POWER + S2 + HLS only, with a note), footprints toggle, in-field zones toggle.
2. **Your field's year** [M]: bare-field calendar rows 2019–2025 (hatched unknown, brown bare, light green partial, green covered) with detector toggle rule / ML / consensus and disagreement hatching; risk ticks above; green-up/senescence markers; current-crop vulnerability strip below; AAFC/CDL crop history row; **news timeline** row with markers (B9); right rail "what this is built from" with scale badges and the model-agreement %.
3. **Trends** [M cell chart / S map]: B7.2.
4. **Priorities and constraints** [M]: six brief sliders (+ three extra collapsed), constraints (irrigation available, licence m³, livestock type, drill, "no new perennials"), **market preference** (sell hay / feed own herd / no preference), scenario panel.
5. **Compare** [M]: four columns; exposure rings; headline metric by regime (exposed heavy-rain days / irrigation need mm and share before 16 Aug / for CA both plus RMA profile); score bars with whiskers and tie badges; new lines pest break, infiltration, N scavenging, income (range); Replay and Scenario toggles; "Open brief".
6. **Rotation brief** [M] (printable A4): header with name, field, regime, date, "Example data / rule of thumb, not a model"; cycle calendar strip; **Why suggested** (LLM or template sentences, each with source chip); **Evidence** 3–6 bullets with chips and scale badges (incl. one line from feature importance and one from the stress model); **Benefits by priority** (nine rows incl. pest break, infiltration, income with range); **Funding and income** box ("may be partly paid for: IAF 85% of cost, cap to confirm" / "EQIP 340") ; **Crop role cards** chips; **Gaps**; **Needs local review** checklist with severity; footer sources + "AI-written, checked against N sourced numbers; M rejected".
7. **Satellite vs ground** [M]: monthly rain IMERG / station / POWER; T2M_MIN vs station; SMAP vs L4 vs bucket model; CA: OpenET vs ETc, CIMIS vs POWER ETo; **Model comparison** panel (B6.1, B6.2); grid page showing field grid and regional grid with footprints (B2.14).
8. **Limits** [M]: B11.

### B9. News timeline [M]

- **Sources (cached Saturday):** BC Gov News Agriculture & Food RSS `https://news.gov.bc.ca/ministries/agriculture-and-food/feed` and Water, Land & Resource Stewardship RSS `https://news.gov.bc.ca/ministries/water-land-and-resource-stewardship/feed` (V ✓); Google News RSS `https://news.google.com/rss/search?q=<q>&hl=en-CA&gl=CA&ceid=CA:en` (V ✓; unofficial; fetch server-side, cache) and `hl=en-US&gl=US&ceid=US:en` for CA; GDELT DOC 2.0 `https://api.gdeltproject.org/api/v2/doc/doc?query=<q>&mode=artlist&format=json&startdatetime=…&enddatetime=…` (V; ~1 request / 5 s; archive only, pre-fetched).
- **Query design:** one query per event window per preset. SR 2023: `("Salmon River" OR Shuswap OR "Salmon Arm" OR Westwold OR "Bessette Creek") AND (drought OR "water shortage" OR "fish protection order" OR curtail* OR "fish population protection") AND (farm* OR forage OR hay OR irrigation OR livestock OR rancher*)` with `after:2023-06-01 before:2023-10-15`. FV 2021: `("Sumas Prairie" OR Abbotsford OR "Fraser Valley") AND ("atmospheric river" OR flood*) AND (farm* OR dairy OR blueberr* OR livestock)` with `after:2021-11-10 before:2021-12-31`. CA: `(Colusa OR Glenn OR "Sacramento Valley") AND (rice) AND (drought OR fallow* OR flood* OR "atmospheric river")` for 2022 and 2023 windows.
- **Ranking:** government releases (news.gov.bc.ca, ca.gov) first, farm press (countrylifeinbc.com, agalert.com) second, everything else third; drop items without a place match in title or description; dedupe by canonical URL; keep 1–3 per marker.
- **Marker:** date, NASA signal that day (SMAP percentile or IMERG 3-day total or GRACE percentile), headlines, and a lead-time line **only when computed**: `lead_days = event_date − first date of a ≥ 7-day run with SMAP percentile < 10 in the preceding 120 days` (and the analogous IMERG run for wet events). Until computed the UI shows "lead time: computing" and the pitch does not state a number.

### B10. Validation, demo, workstreams

#### B10.1 Validation checks (scripts in `checks/`, run before anyone pitches)
1. Coordinates: lon/lat order logged for every call; field plotted on basemap; SR polygon inside the M0238_2023 area; CA polygon on CDL rice (2021) and fallow (2022).
2. Units and ranges asserted on load (POWER mm/day and °C; IMERG mm/day; SMAP 0.02–0.6 m³/m³; NDVI −1..1; LST 250–340 K; GRACE percentiles 0–100; OpenET mm/month 0–400).
3. Rain: monthly IMERG vs Abbotsford A 50308, Salmon Arm CS 6843, CIMIS 250; expect most months within ~25%; record bias per preset.
4. Events: 13–15 Nov 2021 is a top-3 multi-day total in all precipitation sources for FV; Jan–Mar 2023 for CA (U); 2023 Jun–Aug IMERG below climatology for SR.
5. Drought: SMAP Jul–Aug 2023 at SR below the 2015–2025 same-month median; GRACE groundwater percentile 2023 (SR) and 2021–22 (CA) below 30 (U expectation).
6. Cover: observed consensus cover vs modelled baseline calendar ≥ 60% agreement; crop-history class consistent with the preset crop in ≥ 4 of the last 6 years; CA shows fallow in 2022.
7. ML: test-year accuracy ≥ 0.80 and F1(bare) ≥ 0.75 or the ML toggle ships with a "below target" badge; transition MAE reported; rule-vs-ML disagreement < 20% or explained.
8. Stress: both stress methods flag ≥ 1 week in late June 2021 (BC) and ≥ 2 weeks in Jul–Aug 2023 (SR); CA flags 2022 as anomalous (fallow) — note that fallow is not "stress", and label it.
9. **Lead time:** compute `lead_days` for 2023-08-16 at SR from SMAP L3 and L4; print it with the run length; if no sustained run exists, the UI says so and the pitch drops the claim.
10. LLM: validator rejection rate logged; zero unchecked sentences in any brief; spot-read 10 sentences against sources.
11. Scores: baseline erosion 0; full-year cover → exposed rain days ≈ 0; alfalfa Jun–Aug ETc > winter-cereal Jun–Aug ETc at SR; CA modelled rice ETc within ±25% of OpenET for 2021 (U expectation); scenario +2 °C increases ETo.
12. Sources: every SourcedNumber has a URL; count of `verified:false` printed on each brief; the References field of the submission lists every dataset, library and image.

#### B10.2 Demo script (3 min local pitch) and submission
- 0:00 (25 s) **Multigenerational opener:** "Three generations have farmed this field. The last five summers broke the pattern." Len's family on the lower Salmon River; 16 Aug 2023, ~398 licence holders told to stop irrigating forage (V); hay price line only if verified.
- 0:25 (20 s) **Shuswap hook:** "In spring the satellites already showed it coming" → Trends chart with the 2023 SMAP/GRACE lines and the news marker; state the lead time only if computed (B10.1 #9).
- 0:45 (1:45) **Live demo:** FV calendar (2021 ticks on bare; rule vs ML toggle), vulnerability strip, priorities incl. market preference, compare (tie badge, pest/infiltration/income lines), scenario slider, one brief with the checked-AI footer, ten seconds on Satellite vs ground / model comparison, switch to SR irrigation-need bars with "share before 16 Aug", one glance at CA ("same tool, richer ground data").
- 2:30 (30 s) **Close:** "Supports the farmer and the agrologist; never replaces them. Every number has a source; every model shows its accuracy and where it disagrees. NASA POWER, IMERG, SMAP, HLS, MODIS, ECOSTRESS, GRACE and SRTM, with ESA Sentinel-2 and BC's and USDA's own ground data."
- Submission (V, judging guide): 7 slides **or** 30-s video with English subtitles; slides: 1 title; 2 problem (two BC events + CA); 3 calendar + detectors; 4 compare + scenario; 5 brief; 6 data, grids, validation, model comparison; 7 limits and next steps. References field complete.

#### B10.3 Six-person workstreams

| # | Owner | Saturday | Sunday |
|---|---|---|---|
| 1 Regional data + news | POWER, IMERG, SMAP L3/L4, GRACE cached for 3 presets (point + 11×11 cells); ETo; risk days; RSS/Google News/GDELT cached and ranked | disagreement metrics; lead-time computation; Trends layers |
| 2 Field data + zones | HLS, S2, MODIS, ECOSTRESS, NASADEM, ACI/CDL cached; weekly feature table; rule detector; zone rasters | observed-vs-modelled agreement; hotspot layer; calendar exports |
| 3 AI | pseudo-labels; RF/HGB detectors with ModelReports; z-score + isolation forest; LLM prompt + validator with cached briefs | cross-site test; model comparison panel data; rejection-rate report |
| 4 Rotation engine + adapters | crops.json (BC factsheets, FAO-56, USDA PLANTS), 12 strategies, scoring v1 with ranges and scenario recompute, BC/CA adapters (SoilGrids, SDA, OpenET, CIMIS, CDEC, RMA), API | income/funding lines, pest/infiltration/N-scavenging, local_review rules |
| 5 Frontend | screens 1, 2, 4, 5 against fixtures; glossary and explainer cards | screens 3, 6, 7, 8; print CSS; phone width; polish |
| 6 Integration, validation, story | repo, schemas, fixtures, pre-commit source check, `checks/` scripts; farmer story draft; slide skeleton | runs all checks; owns demo laptop and offline cache; records 30-s video; rehearses pitch 3×; submits before 11:59 pm |

If a seventh off-roster helper exists, give them story + video.

**First-hour contracts** (nothing else starts until committed):
1. `schemas/`: SourcedNumber, Location, Crop, RotationStrategy, ModelReport, NewsItem, FeatureRow; API routes in B3; region adapter interface `get_soil(centroid)`, `get_crop_history(polygon)`, `get_station_daily()`, `get_field_et()` (returns null in BC), `get_loss_profile()` (null in BC).
2. Preset IDs `fv_sumas_dairy`, `sr_salmon_river_hay`, `ca_colusa_rice`; polygons committed; working CRS EPSG:32610.
3. Cache paths and `meta.json`; fixtures for all three presets so the frontend starts at hour 2.
4. Accounts and keys on the data laptop: Earthdata login with GES DISC, NSIDC, LP DAAC/AppEEARS authorised; OpenET key; CIMIS key; USDA NASS/AMS keys; LLM API key; `.netrc`; MPC/Earth Search reachable from venue Wi-Fi; GDELT pre-fetch started.
5. Definition of done for a number: value, unit, low, high, method, source URL; pre-commit fails otherwise. Definition of done for a model: ModelReport with split, metrics, disagreement. Definition of done for an LLM sentence: `checked: true`.
6. Must-have list frozen: everything tagged [M] above. [S] items start only after all [M] caches exist and the FV demo runs offline end to end. Merge every 3 hours; feature freeze Saturday 22:00.

### B11. What the data cannot support (the app's Limits page; extend as items change)

- SMAP, IMERG, POWER and GRACE cannot distinguish one field from its neighbour; they say which weeks and years were wet, dry, cold or hot across the valley or basin. GRACE is coarser still (~0.25° assimilation product; underlying signal ~300 km).
- HLS/Sentinel-2 see cover and greenness, not soil loss, infiltration, nitrate, tile drains or yield; winter cloud leaves gaps of weeks; snow hides everything.
- ECOSTRESS overpasses are irregular; LST/ET anomalies are relative, not absolute water-use measurements. OpenET exists only in the western US.
- The bare/transition ML models are trained on satellite pseudo-labels and crop-inventory rules, not ground truth; their accuracy is agreement with another product. The stress models have no labelled stress events; they are checked against a handful of known episodes.
- The LLM only rephrases sourced numbers; it adds no knowledge, and rejected sentences are replaced by templates. It can still choose an awkward emphasis; the adviser reads it.
- Scores are rule-of-thumb composites of factsheet ratings and FAO-56 coefficients; Kc for fall rye, triticale, sainfoin (and rice/safflower until read) are borrowed or unverified; income and funding are ranges from public price series and program pages, not quotes.
- Scenario sliders scale temperature and rain uniformly; they are not climate projections.
- Lead time between a satellite signal and a government order is a statistical observation on one or two events, not a forecast.
- The 2021 flood was a dike failure; no rotation prevents that. The tool addresses bare-ground exposure, not flood protection.
- Pest-cycle break is a family-rotation rule of thumb; there is no pest or disease dataset behind it.
- Preset calendars, field sizes and soils are typical examples, not measured farms. Every alternative rotation needs review by the farmer and an agrologist before anything is seeded; that sentence is on every brief.
