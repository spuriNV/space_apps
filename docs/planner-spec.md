# Field Shift planner: idea and build spec (v3, single current spec)

**Decision recorded in v3:** California is the product; BC is the motivation. The pitch opens with BC's 2023 Salmon River irrigation order and 2021 Sumas flood and the point that BC lacks the ground data to validate a tool (no OpenET, no field-level soil API, sparse stations, short crop labels), then shifts: "so we built and validated it where the data is rich", and the whole demo runs on two California presets. BC survives as a cached news timeline for the opener [M], one optional NASA-only chart [S], and a "next step: bring it to BC" slide and Limits line. BC presets are in Appendix A (not on the build path).

Written to be handed to coding agents. Every number carries a source or is marked **U**. `field-shift-plan.md` is the team plan; `brief-coverage.md` is the gap check; `research-findings.md` holds endpoint tests.

Marker key: **V** = read from the cited source during research. **U** = unverified / assumed; confirm or label "assumed" in the UI. **[M]** = must-have for the demo. **[S]** = stretch, after all [M] caches exist and the demo runs offline end to end.

---

## Part A: The idea

### A1. The problem and who has it

**Motivation (BC, two water extremes, thin ground data).**
- 16 Aug 2023: fish population protection orders required "approximately 398 surface and groundwater licence holders in the lower Salmon River and Bessette Creek area" to "stop using water for forage crops, which include grass for hay, alfalfa and forage corn"; mid-June mailouts had asked for up to 50% reductions (V): https://news.gov.bc.ca/releases/2023FOR0052-001305 (orders M0238_2023, M0239_2023; expired 30 Sept 2023, V news: https://www.castanetkamloops.net/news/Salmon-Arm/571142/ ). Note: release 2023FOR0059-001512 is the 27 Sept 2023 Koksilah/Tsolum rescind bulletin (V), not this order.
- 14–15 Nov 2021 atmospheric river: Sumas dike breach, ~1,100 farms under order/alert, ~150 km² flooded (V news: https://www.countrylifeinbc.com/catastrophic-flooding-hits-fraser-valley/ ); topsoil loss (V: https://www.cbc.ca/lite/story/1.6261829 ).
- BC gaps (V from the challenge Resources tab and research-findings): OpenET covers western US states only; BC soil comes from survey polygons or SoilGrids (250 m global model), no field-scale API; ECCC stations are sparse in Interior valleys (Salmon Arm CS is the only active daily station in the valley, V Station Inventory); AAFC crop labels start 2011 with incomplete BC ground sampling in 2021 (V dataset notes).

**The product (California, two valleys, rich ground data).**
- **Sacramento Valley rice (Colusa County).** 2022 drought: rice acreage roughly halved; Colusa −84%, Glenn −75% vs 2021 (V, NASA Earth Observatory quoting UC Davis: https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/ ); Glenn-Colusa ID "typically ~100,000 acres … this year 1,000" (V news); ~267,000 acres fallowed in Sutter/Colusa/Glenn (V news). Then 2023: wet winter, late planting, harvest pushed into the rainy season; average planting-to-harvest 145–150 days, 152 in 2023 (V: https://www.agalert.com/california-ag-news/archives/january-3-2024/later-rice-harvest-deals-minor-yield-quality-impacts/ ).
- **San Joaquin Valley forage/dairy (Tulare and Kings Counties).** Tulare County grew 117,066 acres of corn for silage/greenchop in 2022 (V, USDA 2022 Census county profile: https://data.nass.usda.gov/Publications/AgCensus/2022/Online_Resources/County_Profiles/California/cp06107.pdf ) and is the top US agricultural county by value, driven by dairy (V news). Spring 2023: Tulare Lake re-emerged after atmospheric rivers, peaking near 114,000 acres by DWR satellite measurement (V news: https://www.nbcnews.com/science/science-news/dormant-california-lake-reappeared-isnt-going-anywhere-fast-rcna92452 ; county ag losses projected > $300M, V news). 16 Apr 2024: State Water Board placed the Tulare Lake Subbasin on SGMA probation for subsidence from over-pumping (V: https://water.waterboards.ca.gov/press_room/press_releases/2024/pr20240415-tulare-lake-probationary-hearing.html ); litigation since (appeal reversed the 2024 injunction Oct 2025; split ruling Aug 2026) (V news: https://sjvwater.org/kings-county-judge-rules-against-state-water-board-in-high-stakes-groundwater-case ). The brief's hero image is a Nevada alfalfa field; alfalfa under groundwater limits is the same story.

**Who has the problem.** (1) The grower: a Colusa rice grower deciding what to do with a check in a low-allocation year and over winter; a Tulare dairy forage manager deciding how much alfalfa and silage corn to keep under a pumping cap. (2) The adviser: UCCE farm advisor, NRCS planner, irrigation district or GSA staff, crop consultant. The adviser opens the tool; the brief says the tool "does not replace farmer judgment or local agricultural expertise".

### A2. User story

Rosa's family has grown rice west of Williams since her grandfather levelled the first checks. In February 2026 she meets Sam, the UCCE advisor. The planner's Colusa preset shows CDL history 2008–2024 for her block (rice every year, fallow in 2022), the bare-field calendar from HLS (bare mid-Oct to late Apr, except winter-flood years), and the detector agreement (rule vs ML 93%). The news timeline marks 2022 ("Glenn-Colusa plants 1,000 acres") and Jan–Mar 2023 storms next to the SMAP and IMERG signals, and the Trends chart shows GRACE groundwater percentile for her cell since 2003. OpenET's measured ET for her rice in 2021 sits beside the modelled ETc (within the range). Rosa sets priorities (water use high, income high, organic matter medium) and market preference "sell"; the compare screen shows continuous rice against rice + winter cover (no winter flood), a dry-year plan (fallow or safflower when allocation < 50%), and rice–winter wheat. The scenario slider at +2 °C / −15% rain raises irrigation need and the exposure of the bare winter to extreme rain. Sam prints the rice + winter cover brief: LLM-written sentences each with a source chip, the RMA cause-of-loss profile for Colusa rice (drought vs excess moisture share), EQIP 340 cover-crop funding as a range, and local-review items (straw decomposition, waterfowl habitat obligations, herbicide carryover).

Miguel manages forage for a Tulare dairy under a GSA allocation. The Kings/Tulare preset shows his alfalfa and silage-corn fields, SSURGO drainage and AWC, CIMIS ETo vs POWER ETo, OpenET vs modelled ETc by month, and the 2023 flood extent weeks on the calendar. He compares continuous alfalfa against sorghum-sudan summer forage (less water than corn), winter small-grain silage + summer fallow, and alfalfa with a shorter stand life and a winter-cereal break. Irrigation need per rotation is shown against his allocation; income lines use USDA AMS hay prices.

### A3. The decision it changes and why NASA data is uniquely useful

The decision is **what goes into the open window and when, and how much irrigation-dependent acreage to keep**: cover or no cover over winter (rice), fallow or a low-water crop in a short-allocation year, how much alfalfa/corn to carry under a pumping cap, seeded in which week, against which weeks of risk.

NASA data makes observed what is otherwise assumed: when the field is bare, green or stressed (HLS 30 m 2015–, Sentinel-2 10 m 2019–, MODIS 250 m 2000–, ECOSTRESS 70 m LST/ET 2018–) and when and how hard the water signals move, over decades (POWER 1981–, IMERG 2000–, SMAP 2015–, GRACE 2003–). California's ground data (OpenET, CIMIS, SSURGO, CDL, CDEC, RMA) are used to **validate** the NASA-derived measures and to feed crop/soil rules, which is exactly what BC cannot do yet. NASA data never "picks a crop"; it measures exposure, stress, water demand and trends.

### A4. What exists and how this differs

| Existing tool | Does | Does not |
|---|---|---|
| OpenET (https://openetdata.org/) (V) | Field-scale monthly ET, western US | Rotation comparison, bare-period exposure, uncertainty, briefs |
| CIMIS (https://cimis.water.ca.gov/) (V) | Station ETo and irrigation scheduling | Field observation; rotations |
| US Drought Monitor, NOAA outlooks (V exist) | Regional drought and seasonal odds | Field, crops, rotations |
| USDA Cover Crop / Western cover-crop selector (https://covercrop-selector.org) (V) | Goal-based species choice | Field calendar, weather exposure, water |
| CropPlan+, Cropwise-type apps (V exist) | Field records, commercial planning | Open data, exposure, NASA, uncertainty |
| UC ANR / UC Rice / UC Alfalfa guidance (V) | Agronomy | Static documents |
| BC Agriculture Water Calculator, BC Drought Portal (V exist) | Licensing demand; regional drought levels | Field, rotations; and no field-level ground data to validate against |

Gap: nothing combines *when my field is bare or stressed* + *when the weather and water hit* + *which rotation covers it* + *how sure are we* + *what it might pay*, in language a grower and adviser read together, and nothing shows the method's accuracy against measured ground data on the same screen.

### A5. Creative twists (on-brief)

1. **Exposure calendar** [M]: 12-month ring per rotation, bare days × risk ticks → "exposed risk-days".
2. **Replay a real year** [M]: 2022 (drought/fallow) and 2023 (floods, late planting) run against observed daily data.
3. **Satellite saw vs news reported** [M]: timeline markers pairing the NASA signal with 1–3 cached headlines (CA and BC windows) and a *computed* lead-time line; never asserted.
4. **Two detectors, one calendar** [M]: rule vs ML bare/transition detection on the same strip with accuracy and disagreement printed; CDL gives real labels here.
5. **Measured vs modelled** [M]: OpenET vs ETc and CIMIS vs POWER ETo on the Satellite vs ground page: the headline validation.
6. **Adviser hand-off** [M]: printable brief with every number footnoted, gaps, review checklist.
7. **Rich vs sparse** [S]: a "Why not BC yet" card and one NASA-only BC chart showing what the tool can and cannot say without ground data.

### A6. Weakest point and defense

Weakest: rotation scores are rule-of-thumb composites of factsheet ratings and FAO-56 coefficients, not a crop model; ML detectors are trained on CDL year-labels, which are coarse in time; coarse NASA products cannot resolve a field; transferability to BC is a claim.

Defense: comparisons with ranges and declared ties, never a single recommendation; every number linked; NASA data used only for what satellites measure (exposure, stress, water demand, trends); scale drawn on screen; ML evaluated on held-out years including 2022 and compared with the rule; OpenET and CIMIS as independent checks; dollars as ranges; BC explicitly listed as untested and as the next step.

---

## Part B: Build spec

### B1. Presets (California) [M]

Representative fields ("Example field; drag to your own"); final polygons chosen Saturday morning against CDL so pixels are the crop we claim.

#### Preset CAR: Colusa County rice (Sacramento Valley)

| Item | Value | Status / source |
|---|---|---|
| Centre | 39.15 N, −122.10 W (west of Williams) | U: choose a CDL rice (2021) → fallow (2022) → rice (2023) block |
| Field | 60 ha rice check, laser-levelled | U |
| Soil | SSURGO map unit via Soil Data Access: drainage class, hydrologic group, AWC, texture, SAR/salinity if present | V endpoint; values computed |
| Stations | CIMIS 250 Williams (formerly Colusa) (V: https://cimis.water.ca.gov/Stations.aspx ); NOAA NCEI daily Colusa/Williams (U station id) | |
| Water | CDEC Shasta (SHA) and Oroville (ORO) storage, Sacramento River; CVP/Sacramento River Settlement allocation history (U source); DWR groundwater; SGMA Colusa Subbasin (medium priority, U) | V endpoints exist |
| Crop history | CDL 2008–2024 (rice 3, fallow 61, winter wheat 24, safflower 33, sunflower 6; U codes: read legend) | V product |
| Insurance | RMA cause-of-loss, Colusa County, rice, 2010–2024 | V source |
| Events | 2021–22 drought and 2022 fallowing; Jan–Mar 2023 atmospheric rivers and late 2023 planting/harvest | V news |

Calendars (timing V unless marked: average planting-to-harvest 145–150 days; 50% of fields planted by 12 May on average; 1 June considered too late; Colusa trial planted 18 May, harvested 12 Oct; V via UC Rice Blog / Ag Alert: https://www.ucanr.edu/blog/uc-rice-blog ).

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CAR0 Continuous rice, winter flood (baseline) | winter flood | drain | field prep | flood, water-seed late Apr–May | rice | rice | rice | rice | drain, harvest late Sept–Oct | straw mgmt, re-flood | winter flood | winter flood |
| CAR1 Rice + winter cover (cereal/vetch) instead of winter flood | cover | cover | terminate, prep | flood, seed | rice | rice | rice | rice | harvest | drill cover after straw chop (U) | cover | cover |
| CAR2 Dry-year plan: fallow with cover or safflower when allocation < 50% (dry year shown) | cover/bare | cover/bare | safflower plant (Table 11: April, V) | safflower | safflower | safflower | harvest (U) | bare | bare | bare | bare | bare |
| CAR3 Rice–winter wheat (wheat year) | wheat | wheat | wheat | wheat | heading | harvest June (U) | bare | bare | bare | bare | drill wheat (Nov–Dec, FAO-56 Table 11 Calif. December, V) | wheat |

CAR1 cover-crop species and seeding after rice are U (UC is evaluating winter cover crops after rice under the CDFA Healthy Soils Program; results not located, V that trials exist). CAR2 safflower stage lengths 20/35/45/25 days from April planting, California (V, FAO-56 Table 11). Winter flooding for straw decomposition and waterfowl habitat is a known practice; its water and habitat trade-offs go to local_review (U details).

#### Preset CAF: Tulare/Kings forage for dairy (San Joaquin Valley)

| Item | Value | Status / source |
|---|---|---|
| Centre | 36.20 N, −119.60 W (between Corcoran and Hanford, Tulare Lake Subbasin, dairy forage country) | U: choose CDL alfalfa (36) / corn (1) history; confirm inside Tulare Lake Subbasin boundary (DWR Bulletin 118, U) and whether the pixel was in the 2023 flood extent (OPERA DSWx) |
| Field | 32 ha (quarter-section pivot/furrow) | U |
| Soil | SSURGO via SDA | computed |
| Stations | CIMIS Stratford (station 15, U) or Parlier (39, U); confirm on https://cimis.water.ca.gov/Stations.aspx ; NOAA NCEI Hanford (U id) | |
| Water | Groundwater-dependent; GSA allocation user input (acre-ft/acre); DWR well levels; SGMA Tulare Lake Subbasin probation 16 Apr 2024 (V); CDEC Kings River / Pine Flat (PNF) storage (U sensor) | |
| Crop history | CDL 2008–2024 (alfalfa 36, corn 1, winter wheat 24, sorghum 4, cotton 2, fallow 61; U codes) | V product |
| Insurance | RMA cause-of-loss, Tulare and Kings, alfalfa/forage and corn, 2010–2024 | V source |
| Events | 2021–22 drought and pumping; spring 2023 Tulare Lake re-flooding (~114,000 acres peak, V news); 2024 probation (V) | |

Calendars (alfalfa: planting mid-Sept–Oct in the central San Joaquin Valley; 28-day cutting schedules common after first cut; V via UC Alfalfa: https://alfalfa.ucdavis.edu/IrrigatedAlfalfa and UC Ag Briefs 2026: https://ucanr.edu/sites/default/files/2026-07/Ag%20Briefs%20%20-%20July-August%202026%20ADA.pdf ; silage corn and small-grain timing U, typical SJV double-crop).

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CAF0 Alfalfa, 7–8 cuts, 4–5 yr stand (baseline) | dormant/slow | growth | cut 1 | cut 2 | cut 3 | cut 4 | cut 5 | cut 6 | cut 7 | cut 8 (U count) | slow | dormant |
| CAF1 Winter small-grain silage + silage corn double crop | wheat/triticale | growth | growth | harvest silage (Apr–May, U) | plant corn | corn | corn | corn harvest (Aug–Sept, U) | bare | drill small grain (Oct–Nov, U) | grain | grain |
| CAF2 Winter small-grain silage + sorghum-sudan summer forage (lower water than corn) | grain | growth | growth | harvest | plant sorghum-sudan | cut 1 | cut 2 | cut 3 (U) | terminate | drill grain | grain | grain |
| CAF3 Alfalfa 3-yr stand → winter cereal break → re-seed (break year) | cereal | cereal | cereal | harvest silage | fallow (summer, no pumping) | fallow | fallow | prep | re-seed alfalfa mid-Sept–Oct (V window) | establishing | establishing | dormant |

Sorghum-sudan as a lower-water summer forage than corn is a widely stated extension position (U: cite a UC ANR or NRCS source before shipping). CAF3's point: a summer with no irrigated crop under a pumping cap; the tool quantifies ETc by month.

### B2. Data pipeline

General rules:
- One field = one polygon (GeoJSON EPSG:4326; working CRS EPSG:32610 for both CA presets, UTM 10N; V).
- Two analysis grids (B2.14): field grid (30 m HLS-aligned cells in the polygon) and regional grid (9 km EASE-Grid 2.0 SMAP cell + 11 × 11 neighbourhood).
- Daily master table 2015-01-01 to 2025-12-31; longer per-source tables for climatology (POWER 1981–, MODIS 2000–, IMERG 2000–, GRACE 2003–, CDL 2008–).
- Cache everything Saturday: `data/cache/<preset_id>/<dataset>.parquet` + `<dataset>.meta.json` {url, params, fetched_at, footprint_geojson, native_res_m, timestep, units, fill_value, auth}; rasters as COG in `rasters/`. The demo never calls a remote server.
- Time zones: POWER, IMERG daily are UTC; CIMIS/NOAA daily are local (PST). Compare monthly or ±1 day.

#### B2.1 NASA POWER [M] — no auth
`https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR&community=AG&longitude=-122.10&latitude=39.15&start=19810101&end=20251231&format=JSON` (V structure; ≤ 20 params; 0.5° grid; cache). Regional endpoint one parameter per request for the Trends map [S]. Derived: Hargreaves ETo (FAO-56 eq. 52), PM ETo [S], frost/heat/heatwave days.

#### B2.2 GPM IMERG daily [M] — Earthdata login
GPM_3IMERGDF V07, 0.1°, ~2000–present (V). Access: GES DISC Data Rods/Giovanni time series (pattern `https://hydro1.gesdisc.eosdis.nasa.gov/daac-bin/access/timeseries.cgi?variable=GPM:GPM_3IMERGDF_07:precipitation&startDate=2015-01-01T00&endDate=2025-12-31T23&location=GEOM:POINT(-122.10,%2039.15)&type=asc2`, U exact variable string; how-to: https://disc.gsfc.nasa.gov/information/howto?title=How%20to%20Access%20the%20Hydrology%20Data%20Rods%20Time%20Series%20API%20Using%20Python ); AWS mirror https://registry.opendata.aws/nasa-gpm3imergdf/ (V listed; U anonymous); OPeNDAP subset. Footprint ≈ 11 × 9.6 km at 39°N.

#### B2.3 SMAP [M] — Earthdata login
SPL3SMP_E.006 (9 km daily) and SPL4SMGP.008 (L4 surface/root-zone, 9 km, 3-hourly) via AppEEARS point/area (V listed at https://appeears.earthdatacloud.nasa.gov/api/product ). Layers `Soil_Moisture_Retrieval_Data_AM/soil_moisture`, `retrieval_qual_flag`; L4 `sm_rootzone`, `sm_surface`. Note: flooded rice checks and the 2023 Tulare Lake water surface corrupt L3 retrievals; keep the quality flag and show gaps. Area request 11 × 11 cells for Trends [S].

#### B2.4 HLS 30 m [M] — Earthdata login
HLSL30.020, HLSS30.020 (and `_VI` products) via AppEEARS (V listed). Bands B02–B07, Fmask. Primary record for bare/transition detection and the ML features.

#### B2.5 Sentinel-2 L2A 10 m [M] — no account
MPC STAC `https://planetarycomputer.microsoft.com/api/stac/v1` collection `sentinel-2-l2a` (V) or Earth Search `https://earth-search.aws.element84.com/v1` `sentinel-2-c1-l2a` (V). B04, B08, SCL. Visual layer and cross-check of the detectors (SCL 5 "not vegetated").

#### B2.6 Landsat C2 L2 [S] — MPC `landsat-c2-l2` (V), 1984–; long bare-field climatology.

#### B2.7 MODIS MOD13Q1.061 [M] — Earthdata login
250 m, 16-day, 2000-02-18–present via AppEEARS (V). NDVI/EVI/pixel reliability. 25-year baseline for the stress z-score; regional NDVI on the Trends map.

#### B2.8 ECOSTRESS [M point series; S rasters] — Earthdata login
AppEEARS (V listed): `ECO_L2T_LSTE.002` (LST), `ECO_L3T_JET.002` (ET), `ECO_L4T_ESI.002` (ESI), `ECO_L3T_ET_ALEXI.002`. Stress features and in-field hotspots; ET as a third ET opinion next to OpenET and ETc on clear dates. Irregular overpass times: anomalies only.

#### B2.9 GRACE / GRACE-FO DA drought indicators [M series; S map] — Earthdata login
GRACEDADM_CLSM025GL_7D V3.0: 0.25°, weekly, Feb 2003–present, 3–6 month latency; groundwater / root-zone / surface soil-moisture percentiles (V: https://www.earthdata.nasa.gov/data/catalog/ges-disc-gracedadm-clsm025gl-7d-3.0 ; AWS mirror V listed). Central Valley groundwater decline is a textbook GRACE signal; pair with DWR well levels.

#### B2.10 Elevation [M] — NASADEM via MPC `nasadem` / `cop-dem-glo-30` (V) or SRTMGL1_NC.003 via AppEEARS (V). Slope, low spots (rice checks and much of the SJV are flat; see B7.3).

#### B2.11 OPERA DSWx surface water [S] — via CMR (research-findings ✓). 2023 Tulare Lake extent weeks and winter-flooded rice detection; label as water, not "bare".

#### B2.12 CA ground data adapter [M]
- **CDL** 30 m 2008–2024: GeoTIFF download https://www.nass.usda.gov/Research_and_Science/Cropland/Release/ or CroplandCROS (V); clip to bbox; class legend from the release (U codes). Labels for the AI (B6.1) and the crop-history row.
- **SSURGO via Soil Data Access** `POST https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest` `{"format":"JSON","query":"…"}` (V ✓). SQL pattern: mapunit/component by `SDA_Get_Mukey_from_intersection_with_WktWgs84('POLYGON(…)')`, fields `muname, compname, comppct_r, drainagecl, hydgrp, taxorder`, horizons `awc_r, om_r, sandtotal_r, claytotal_r, ec_r` for 0–100 cm (U exact names). Store drainage class, hydrologic group, AWC (mm/m), OM %, texture.
- **OpenET** `POST https://openet-api.org/raster/timeseries/point` (key) body `{date_range:["2016-01-01","2025-12-31"], interval:"monthly", geometry:[lon,lat], model:"Ensemble", variable:"ET", reference_et:"gridMET", units:"mm", file_format:"JSON"}` (V endpoint ✓; U fields); also the polygon endpoint for field means (U). Validation only, never a score input.
- **CIMIS** `https://et.water.ca.gov/api/data?appKey=KEY&targets=250&startDate=2015-01-01&endDate=2025-12-31&dataItems=day-eto,day-precip,day-air-tmp-min,day-air-tmp-max` (V ✓; U item names). Station ETo vs POWER Hargreaves/PM.
- **CDEC** `https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet?Stations=SHA,ORO,PNF&SensorNums=15&dur_code=D&Start=2015-01-01&End=2025-12-31` (V ✓; U sensor 15 = storage). Allocation context strip.
- **DWR groundwater levels** via `https://data.cnra.ca.gov/api/3/action/package_search?q=periodic+groundwater+level` (V ✓) → nearest wells' depth-to-water series; **SGMA basin priority / probation status** as a static JSON with source URLs (V for Tulare Lake probation).
- **USDA RMA cause of loss** yearly files https://www.rma.usda.gov/tools-reports/summary-business/cause-loss (V): filter state 06, county (Colusa 011, Tulare 107, Kings 031; U FIPS), commodity (rice, alfalfa/forage, corn); compute indemnity share by cause 2010–2024.
- **USDA NASS Quick Stats** (key) county acres/yields (V exists); **USDA AMS My Market News** (key) `https://marsapi.ams.usda.gov/services/v1.2/reports` California hay reports (V exists; U slug); **US Drought Monitor** county time series `https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=06011&startdate=1/1/2015&enddate=12/31/2025&statisticsType=1` (V service exists; U params); **NOAA CPC seasonal outlooks** ArcGIS REST (V exists; U layer) as a context strip only.
- **NOAA NCEI** daily `https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=…&startDate=…&endDate=…&dataTypes=PRCP,TMAX,TMIN&format=json` (V ✓; U station ids).
- **EQIP practice 340 (cover crop)** payment rate from the California payment schedule PDF (U rate; source https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives-program ).

#### B2.13 BC minimal set
- **[M] BC news cache** for two windows (B9): Salmon River Jun–Oct 2023; Sumas Nov–Dec 2021; sources BC Gov News RSS (V ✓), Google News CA, GDELT archive.
- **[S] One NASA-only chart**: SMAP L3/L4 percentile and GRACE groundwater percentile for the EASE cell at 50.62 N, −119.33 W (lower Salmon River; U representative point) for Mar–Oct 2023, with the mid-June request and 16 Aug order marked and `lead_days` computed per B9; POWER from the same point. No crop, soil or scoring for BC.

#### B2.14 Common analysis grids [M]
- **Field grid:** 30 m HLS-aligned cells clipped to the polygon; HLS, S2 (10→30 m mean), ECOSTRESS (70→30 m nearest), NASADEM, CDL, OpenET (30 m) expressed per cell; field and zone statistics from it.
- **Regional grid:** EASE-Grid 2.0 9 km cells; IMERG 0.1° (area-weighted), POWER 0.5° (nearest), GRACE 0.25° (area-weighted), MODIS 250 m (mean), USDM county % (attached, not resampled) on it; the field's cell is the regional signal; 11 × 11 neighbourhood is the Trends map.
- Never resample coarse data down to the field grid. The UI draws both grids and footprints.
- Weekly **feature table** per field (`features_weekly.parquet`): field-grid stats (NDVI median/p10/p90, BSI, NBR2, LST anomaly, ESI, OpenET monthly carried to weeks) + regional values (SMAP sm/percentile, IMERG 7-day, POWER Tmax/Tmin/ETo, GRACE percentiles, MODIS NDVI anomaly, USDM category).

### B3. Shared JSON schemas

Every numeric leaf is a `SourcedNumber`.

```json
// SourcedNumber
{ "value": 1.20, "unit": "Kc", "low": 1.10, "high": 1.25, "method": "lookup | computed | assumed | model",
  "source": { "id": "fao56_table12", "title": "FAO-56 Table 12, Rice, Kc mid", "url": "https://www.fao.org/4/x0490e/x0490e0b.htm", "accessed": "2026-11-14", "verified": true }, "note": "" }
```

```json
// Location
{ "id": "car_colusa_rice", "name": "Colusa County rice check (example)", "region_adapter": "ca", "regime": "drought_then_flood", "state_fips": "06", "county_fips": "011",
  "geometry": {…}, "centroid": {"lon": -122.10, "lat": 39.15}, "area_ha": {…}, "crs_working": "EPSG:32610",
  "soil": { "mukey": "…", "muname": "…", "drainage_class": "…", "hydrologic_group": "D", "awc_mm_per_m": {…}, "om_pct": {…}, "texture_class": "…", "source": {"id":"ssurgo_sda","url":"https://sdmdataaccess.sc.egov.usda.gov/","verified":true} },
  "terrain": { "slope_mean_pct": {…}, "slope_p90_pct": {…}, "elev_m": {…}, "low_spot_fraction": {…} },
  "water": { "source": "surface | groundwater | mixed", "allocation_input": {"unit":"acre-ft/acre","value":null}, "district": "Glenn-Colusa ID (U)", "sgma_subbasin": "Colusa", "sgma_status": {"text":"…","url":"…","verified":true}, "cdec_stations": ["SHA","ORO"] },
  "market_preference": "sell | feed_own_herd | no_preference",
  "stations": [ {"network":"CIMIS","id":250,"name":"Williams","distance_km":8,"years":[2016,2026]}, {"network":"NOAA","id":"…"} ],
  "regional_cell": { "grid":"EASE2_G9km","row":0,"col":0,"footprint":{…} },
  "datasets": { "power":{…}, "imerg":{…}, "smap_l3":{…}, "smap_l4":{…}, "hls":{…}, "s2":{…}, "modis":{…}, "ecostress":{…}, "grace":{…}, "dem":{…}, "cdl":{…}, "openet":{…}, "cimis":{…}, "cdec":{…}, "dwr_wells":{…}, "rma":{…}, "usdm":{…}, "news":{…} },
  "crop_history": { "2019":"Rice","2020":"Rice","2021":"Rice","2022":"Fallow/Idle","2023":"Rice","2024":"Rice" },
  "observed_cover": { "typically_bare_doy_ranges": [[290,110]], "bare_doy_file":"…", "years_used":[2016,…,2025], "detector":"consensus" },
  "events": [ {"date":"2022-05-01","type":"drought_fallow","title":"Sacramento Valley rice acreage roughly halved","url":"https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/","verified":true},
              {"date":"2023-01-09","type":"atmospheric_river","title":"…","url":"…","verified":false} ] }
```

```json
// Crop
{ "id": "rice_medium_grain", "name": "Rice (medium grain, water-seeded)", "family": "Poaceae", "role": ["cash"], "legume": false, "root": "shallow fibrous",
  "kc": { "ini": {"value":1.05,…fao56 V}, "mid": {"value":1.20,…V}, "end": {"value":0.75,"low":0.60,"high":0.90,…V} },
  "stage_lengths_days": {"ini":30,"dev":30,"mid":60,"late":30,"source":"fao56_table11 Rice May Mediterranean (V)"},
  "cover_by_stage": {"ini":0.3,"dev":0.7,"mid":1.0,"late":0.8},
  "ratings_0_4": { "erosion_reduction":{…}, "soil_builder":{…}, "lasting_residue":{…}, "nitrogen_fixation":{"value":0}, "nitrogen_scavenging":{…}, "compaction_reduction":{…}, "forage_harvest_value":{"value":0}, "weed_suppression":{…}, "tolerance_flood":{"value":4}, "tolerance_drought":{"value":0} },
  "yield_range": {"value":9500,"low":8000,"high":11000,"unit":"kg/ha","method":"assumed"},
  "drainage_classes_ok": ["poorly","very poorly","somewhat poor"], "seeding_window": {"start":"04-20","end":"06-01","best":"by mid-May","verified":true},
  "pest_notes": ["weedy rice", "rice water weevil (U)"], "cautions": ["herbicide carryover to rotation crops (U)"],
  "seed_cost_per_ha": {…"USD/ha","method":"assumed"}, "explainer_card": null,
  "sources": [ {"id":"fao56_table12","url":"https://www.fao.org/4/x0490e/x0490e0b.htm"}, {"id":"uc_rice","url":"https://rice.ucanr.edu/"} ] }
```
Cover/forage crop ratings (0–4) come from the Western cover-crop selector goal table transcribed by hand (V tool exists; U values) and USDA PLANTS traits (U); BC factsheet bars may be used for species that overlap (fall rye, triticale, vetch, clovers; V bars) with the note "rated for BC conditions".

```json
// RotationStrategy
{ "id": "car1_rice_wintercover", "location_id": "car_colusa_rice", "name": "Rice + winter cover (no winter flood)", "is_baseline": false, "cycle_years": 1,
  "calendar": [ {"year":1,"crop_id":"rice_medium_grain","plant":"05-10","harvest":"10-05","role":"cash","timing_source":"uc_rice_blog (V avg)"}, {"year":1,"crop_id":"cereal_vetch_cover","plant":"10-25","terminate":"03-20","role":"cover","timing_source":"assumed (U)"} ],
  "allocation_rule": null,
  "exposure": { "bare_days_per_year":{…}, "exposed_rain_days":{…}, "exposed_frost_days":{…}, "exposed_heat_days":{…}, "exposed_dry_days":{…}, "replay": {"2022":{…},"2023":{…}}, "scenario": {"dT_c":0,"dP_pct":0} },
  "water": { "etc_mm_season":{…}, "irrigation_need_mm":{…}, "etc_by_month_mm":[…], "openet_et_mm_season": {…"method":"measured"}, "etc_vs_openet_pct": {…} },
  "scores": { "water_use":{…}, "forage_value":{…}, "n_fixation":{…}, "erosion":{…}, "organic_matter":{…}, "market":{…}, "pest_break":{…}, "infiltration":{…}, "n_scavenging":{…}, "income":{…} },
  "composite": {"value":58,"low":47,"high":66,"weights_used":{…}},
  "risk_profile": { "rma_share_drought": {…}, "rma_share_excess_moisture": {…}, "rma_years": [2010,2024] },
  "funding": [ {"program":"USDA EQIP practice 340 Cover Crop","rate_per_acre_usd":{"value":null,"method":"assumed"},"url":"https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives-program","verified":false} ],
  "brief": { "why":[{"text":"…","source_ids":[…],"numbers_used":[…],"author":"llm|template","checked":true}], "evidence":[…], "benefits":[…], "gaps":[…], "local_review":[{"item":"…","severity":"high"}], "explainer_cards":["cover_crop"], "llm_report":{"sentences":9,"numbers_checked":23,"rejected":1,"model":"…","cached_at":"…"} },
  "uncertainty": { "dataset_disagreement":{…}, "scale":{…}, "agronomic_gap_count":3, "detector_disagreement_pct":7 } }
```

```json
// ModelReport
{ "id":"bare_rf_car_v1", "task":"bare_cover | transition | stress_anomaly", "method":"rule_ndvi | random_forest | hist_gbt | zscore | isolation_forest",
  "features":[…], "labels":"cdl_year_class + season_rules | s2_scl_pseudo", "split":{"train_years":[2016,2017,2018,2019,2020,2021,2023],"test_years":[2022,2024,2025]},
  "metrics":{"accuracy":0.92,"f1_bare":0.89,"transition_mae_days":8}, "confusion":[[…]], "feature_importance":[…], "disagreement_with":{"rule_ndvi":0.07}, "notes":"…" }
```

```json
// NewsItem
{ "date":"2022-05-20","title":"Calif. rice acreage to drop to 39-year low","source":"Farm Progress","url":"https://www.farmprogress.com/rice/calif-rice-acreage-to-drop-to-39-year-low","rank":2,"place_match":["Sacramento Valley"],"query_id":"car_2022_drought","signal":{"dataset":"smap_l3","value_pct":9,"lead_days":null} }
```

API (lock in hour 1): `GET /api/locations`; `GET /api/locations/{id}`; `GET /api/locations/{id}/daily?from&to`; `GET /api/locations/{id}/features/weekly`; `GET /api/locations/{id}/strategies`; `POST /api/locations/{id}/score` `{weights, constraints, market_preference, allocation, replay_year?, scenario:{dT_c,dP_pct}}`; `GET /api/locations/{id}/models`; `GET /api/locations/{id}/zones`; `GET /api/locations/{id}/trends?layer=smap_anomaly|heatwave_days|grace_gw_pct|precip_anomaly|modis_ndvi_anomaly&year=`; `GET /api/locations/{id}/news?from&to`; `GET /api/locations/{id}/validation` (OpenET vs ETc, CIMIS vs POWER, station vs IMERG); `GET /api/bc/news` and `GET /api/bc/signal` (opener data); `GET /api/glossary`; `GET /api/crops/{id}`. Frontend builds against `fixtures/*.json` from hour 2.

### B4. Scoring model

Every score 0–100 with low/high; baseline is the reference; "rule of thumb, not a model" under every score.

#### B4.1 Water use [M]
- ETo: Hargreaves from POWER (FAO-56 eq. 52); PM [S]; CIMIS station ETo as the ground reference; report POWER-vs-CIMIS bias and use it to widen ranges.
- ETc = Σ Kc(d) × ETo(d) (FAO-56 single-coefficient curve; stage lengths Table 11; plant/harvest from calendar). Bare Kc 0.15 (U).
- **FAO-56 Table 12 values (V):** Rice 1.05 / 1.20 / 0.90–0.60; Alfalfa hay averaged cutting effects 0.40 / 0.95 / 0.90, individual cutting periods 0.40 / 1.20 / 1.15; Maize field (grain) mid 1.20, end 0.60–0.35 (ini U; silage harvested before end stage → Kc ≈ 1.0 at harvest, U); Winter wheat non-frozen soils 0.7 / 1.15 / 0.25–0.4; Barley/oats mid 1.15, end 0.25; Safflower mid 1.0–1.15, end 0.25 (ini U); Sunflower mid 1.0–1.15, end 0.35; Cotton mid 1.15–1.20, end 0.70–0.50; Sudan grass hay averaged 0.50 / 0.90 / 0.85; Bermuda hay 0.55 / 1.00 / 0.85; Grazing pasture rotated 0.40 / 0.85–1.05 / 0.85; Clover hay 0.40 / 0.90 / 0.85; Rye grass hay 0.95 / 1.05 / 1.00. Winter triticale/rye → winter wheat values (assumed ±0.1); vetch cover → clover values (assumed). Table 11 stage lengths for California entries (V): rice 30/30/60/30 (May, Mediterranean), safflower 20/35/45/25 (April, California), winter wheat 20/60/70/30 (December, California), sudan first cycle 25/25/15/10, cotton 30/50/60/55 (Mar–May, Calif.).
- Irrigation need `I = Σ_season max(0, ETc − 0.8 P)` (0.8 U) with P from IMERG, CIMIS/NOAA, POWER → range; rice adds a flood-establishment and percolation term `F` (U: 300–600 mm; cite UC rice water-use before shipping) so that rice I is not understated.
- Validation line: `etc_vs_openet_pct = (ETc_season − OpenET_season)/OpenET_season` for the baseline crop in 2019–2024; shown on the brief and the validation page; if |bias| > 25% the water score carries a "model/measured mismatch" badge.
- Score `water_use = 100 × clamp(1 − I/I_max)`; `allocation_check`: I vs user allocation (acre-ft/acre → mm) → local_review item "exceeds allocation" if I > allocation.

#### B4.2 Forage value [M] — `100 × Σ(rating_forage/4 × harvestable_months_share × min(yield/10,000,1)) / cycle_years`; alfalfa and silage corn rating 4; yields U ranges (alfalfa 15–20 t DM/ha SJV, silage corn 20–30 t DM/ha, U: cite UC/NASS county yields). Rice forage 0.

#### B4.3 Nitrogen fixation [M] — legumes only (alfalfa, vetch, clovers): `100 × Σ(rating_nfix/4 × months_growing/12)/cycle_years`.

#### B4.4 Erosion reduction [M] — exposure-based `E = Σ_d (1 − cover(d)) × rain_risk(d) × slope_factor`, `slope_factor = 1 + slope_mean_pct/5` (U); `erosion = 100 × (1 − E/E_baseline)` blended 70/30 with crop residue rating. Laser-levelled rice: slope ≈ 0, so erosion is about exposed bare days to extreme rain (runoff/sediment to drains), and the UI says so.

#### B4.5 Organic matter [M] — `100 × [0.5 × mean(soil_builder, lasting_residue)/4 + 0.3 × perennial_years/cycle_years + 0.2 × (1 − bare_days/365)]`.

#### B4.6 Market suitability [M] — table + inputs: `market_preference` (sell → cash crops with local market: rice, hay, wheat; feed_own_herd → silage, sorghum-sudan, small-grain silage), equipment, district/GSA rules; ±25; always a local-review item.

#### B4.7 Pest-cycle break [M] — `100 × min(1, distinct_families/3) × (1 − max_consecutive_same_family_years/cycle_years)`; families: Poaceae (rice, corn, wheat, sorghum), Fabaceae (alfalfa, vetch, clover), Asteraceae (safflower, sunflower), Malvaceae (cotton), Brassicaceae; pest notes to local_review (weedy rice, rice water weevil, alfalfa weevil; U text). No pest dataset exists.

#### B4.8 Infiltration [M] — `100 × [0.5 × compaction_reduction/4 + 0.3 × root_depth_class/2 + 0.2 × cover_months/12]`; plus SSURGO hydrologic group as context (D soils: say "low intrinsic infiltration; rotation effect limited").

#### B4.9 Nitrogen scavenging [M] — `100 × nitrogen_scavenging_rating/4 × fall_winter_cover_months/6`.

#### B4.10 Supplemental income [M in CA] — `$/ha range = sold_product × price_range − seed_cost + EQIP_340_rate × area_share` with hay prices from AMS (U slug), rice/wheat prices from NASS (V exists), EQIP 340 rate U; always "range, confirm locally".

#### B4.11 Historical loss risk [M in CA] — RMA cause-of-loss 2010–2024, county × commodity: `share_drought`, `share_excess_moisture`, `share_heat`, `share_other` of indemnity; shown as a profile bar per crop; not in the composite; "insurance history, not a forecast".

#### B4.12 Weighting, ranges, scenarios [M] — sliders w_i ∈ [0,4] for the six brief priorities + pest_break, infiltration, income (default 0); `composite = Σ W_i s_i` with low/high; tie rule (interval overlap > 50% → "tie within uncertainty"); scenario ΔT ∈ [−1,+4] °C and ΔP ∈ [−30,+30]% recompute ETo, ETc, I, frost/heat/extreme-rain days, exposure live; "2050s" preset values from Cal-Adapt (https://cal-adapt.org , U values). Ranges: deterministic min/max over Kc low/high, ETo ±15% (or POWER–CIMIS bias if larger), three precipitation sources, bare threshold 0.15–0.30, rain threshold 25–50 mm; Monte Carlo N=200 [S].

### B5. Bare-field detection, transitions and risk windows

#### B5.1 Rule-based detector [M] — HLS Fmask / S2 SCL masking; NDVI, BSI; bare < 0.20, partial 0.20–0.35, covered > 0.35 (U rule of thumb; https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology ); water class from NDWI > 0.3 or SCL 6 / DSWx (winter-flooded rice and 2023 lake are "water", not "bare"); green-up = 3 consecutive NDVI > 0.35; senescence/harvest = 2 consecutive drops > 0.2 from 30-day max; ≤ 30-day interpolation, else unknown.

#### B5.2 ML detector [M] — B6.1.

#### B5.3 Risk days (regional grid) [M]

| Risk | Rule | Status | Data |
|---|---|---|---|
| Extreme rain | P ≥ 25 mm/day (Central Valley), 3-day ≥ 75 mm; data-driven 95th percentile of wet days | U (NWS flood-watch thresholds vary; state as our definition) | IMERG; CIMIS/NOAA; POWER |
| Frost | T2M_MIN ≤ 0 °C; ≤ −2 °C hard (U) | FAO-56 −4 °C alfalfa season rule V where used | POWER; stations |
| Heat | T2M_MAX ≥ 35 °C; ≥ 40 °C severe; heatwave ≥ 3 days ≥ 35 °C (Central Valley summer baseline is hot, hence higher thresholds, U) | FAO-56 > 35 °C text V | POWER; ECOSTRESS LST anomaly |
| Dry spell | SMAP AM < 20th percentile of same month ≥ 14 valid days; or IMERG 30-day < 50% of climatology; USDM category ≥ D2 for the county as a check | U convention; USDM V exists | SMAP; IMERG; USDM |
| Water-storage low | GRACE groundwater percentile < 20 for ≥ 8 weeks; CDEC reservoir storage < 50% of historical average for the date (U) | U | GRACE-DA; CDEC |

#### B5.4 Exposure overlay [M] — `exposed_<risk>_days = Σ_d [cover(d) < 0.5 and not water(d)] × risk(d)`; baseline uses observed consensus cover; alternatives use modelled cover (said on screen). Replay years 2022, 2023.

#### B5.5 Current-crop vulnerability strip [M] — growing-season weeks flagged by B6.2 for the existing crop: "both / one / none".

### B6. AI ("SI") section

Small models trained offline Saturday, cached as ModelReports and per-date predictions; nothing trains live. Answers the brief's "compare different SI or statistical approaches … seasonal transitions, bare-field periods … times when current crops show increased stress … how the model interprets uncertainty".

#### B6.1 Bare-cover and transition detection: rule vs ML [M]
- **Unit:** HLS observation date × field (field-median features) for the calendar; × 30 m cell for the zone map [S].
- **Features:** NDVI, EVI, NDWI, BSI, NBR2, red/NIR/SWIR1/SWIR2 reflectance; 30/60-day rolling NDVI mean/min/max, 30-day slope, days since last valid obs, NDVI minus MODIS same-DOY climatology; sin/cos DOY; SMAP percentile, IMERG 7-day, POWER Tmax 7-day mean; water flag.
- **Labels (CDL-based, real year labels):** for each field-year, CDL class gives the crop; class 61 Fallow/Idle → bare all year (except where DSWx/NDWI shows water); crop classes + the preset calendar windows (plant/harvest ± 15 days, U) → bare before planting and after harvest, covered in mid-season, "uncertain" in the ± windows (excluded from training). Secondary pseudo-labels from Sentinel-2 SCL 5/4 on clear days for 2019+. Training uses all CDL-labelled 30 m cells in a 10 km box around each preset (thousands of fields), not just the preset field.
- **Models:** `RandomForestClassifier(n_estimators=300, class_weight="balanced")` and `HistGradientBoostingClassifier`; classes bare/partial/covered/water. Rule = B5.1.
- **Splits:** (a) year split: train 2016–2021 + 2023, test 2022 (fallow year), 2024, 2025; (b) train 2016–2021, test 2022–2025; (c) cross-valley: train Colusa box, test Tulare/Kings box [S]; (d) spatial block hold-out within a box (fields, not pixels) to avoid leakage [M].
- **Metrics:** accuracy, F1(bare), confusion; transition-date MAE (days) vs CDL-window labels and vs SCL pseudo-labels; rule-vs-ML per-date disagreement %; permutation feature importance.
- **Transitions:** smoothed class sequence (3-observation median or HMM); green-up/senescence dates for both methods drawn on the calendar.
- **UI:** Model comparison panel (metrics, confusion, importance bars, disagreement strip per year), calendar toggle rule / ML / consensus; importance line becomes brief evidence.
- **Honesty line:** labels are CDL year classes plus calendar windows; in-season bare periods (e.g. a failed stand) are not labelled; 2022 fallow is the only true held-out bare year.

#### B6.2 Crop-stress anomaly: z-score vs isolation forest [M]
- **Unit:** ISO week × field in the existing crop's growing season, 2015–2025; MODIS 2000–2025 for the NDVI climatology.
- **Features:** z_NDVI (MODIS cell and HLS field), z_LST (ECOSTRESS LST − POWER T2M_MAX, standardised on the field's own record), ESI weekly mean, z_SM (SMAP percentile → z), z_ETo, IMERG 30-day anomaly, OpenET monthly anomaly vs the field's 2016–2024 same-month mean (CA only; measured), USDM category.
- **Method A:** composite z = mean(−z_NDVI, +z_LST, −ESI_z, −z_SM, −z_OpenET); flag if > 1.0 or any two component thresholds hold.
- **Method B:** `IsolationForest(n_estimators=200, contamination=0.10)` per field; leave-one-year-out variant [S].
- **Evaluation:** event recall on known episodes: Jun–Sept 2021 and 2022 drought (both presets), Sept 2022 heat wave (California, U dates), 2023 flood weeks (CAF; label as "water", not stress); agreement %; false-positive proxy = flags in cool wet weeks.
- **UI:** vulnerability strip; tooltips list driving features; brief evidence line.

#### B6.3 LLM explanation layer with source checking [M]
- Input: RotationStrategy JSON (SourcedNumbers), Crop records, Location soil/water, ModelReports, templates. Prompt rules: plain language; each sentence cites `source_ids` and lists `numbers_used`; no new crops/places/dates/numbers; ≤ 25 words.
- Validator: every numeral in a sentence must equal a `value`/`low`/`high` of a referenced SourcedNumber within display rounding; all `source_ids` exist; names in an allow-list; failing sentences replaced by templates; counts logged.
- Output cached at build time; footer "AI-written, checked against N sourced numbers; M sentences rejected and replaced". Temperature 0; prompts in `prompts/brief_v1.md`; template-only path if no key.

### B7. Maps and visual layers

#### B7.1 Field picker [M] — two CA preset cards; "Why not BC yet" info card (B8 screen 1); footprints toggle; zones toggle.

#### B7.2 Trends map [M field-cell charts; S map with year slider] — 11 × 11 EASE cells; layers: SMAP growing-season anomaly (2015+), heatwave days/yr (POWER 1981+), GRACE groundwater percentile (2003+), precipitation anomaly (IMERG 2000+), MODIS May–Sept NDVI anomaly (2000+), USDM weeks ≥ D2 per year (county); event markers (2022 fallow, 2023 floods, 2024 probation); DWR well depth-to-water as the ground line next to GRACE.

#### B7.3 In-field zones [M where meaningful] — NASADEM slope classes (erosion), low spots (≥ 1 m below 300 m focal mean; frost/ponding candidate, U), stress hotspots (Jul–Aug NDVI anomaly < −0.5 σ and/or ECOSTRESS LST > field median + 2 K on ≥ 2 scenes, U), **OpenET 30 m within-field ET variation** (measured; CA only) as a water-stress zone layer. Rice checks: slope zones off, hotspots + OpenET on; say "levelled field, slope zones not meaningful".

#### B7.4 Scenario panel [M] — B4.12.

#### B7.5 Glossary and explainer cards [M] — glossary cards: ET / ETo / ETc / Kc; soil-moisture anomaly and percentile; NDVI and bare/partial/covered; frost risk; water balance and irrigation need; heat stress / LST; groundwater storage (GRACE) and SGMA; allocation (acre-ft/acre ↔ mm); pixel/footprint and scale badge; label vs pseudo-label; isolation forest. Crop-role cards: nitrogen-fixing, cover, deep-rooting, drought-tolerant crops (~80 words, one citation each: UC ANR / NRCS / covercrop-selector).

### B8. UI flow and the rotation brief

Users: grower and adviser side by side; plain language; dual units (mm and inches; ha and acres; acre-ft/acre and mm); acronyms and dataset names in tooltips.

1. **Pick a field** [M]: cards "Colusa rice (Sacramento Valley)" and "Tulare/Kings forage (San Joaquin Valley)" with "ground data: rich" badge; map; draw-your-own (CA only; POWER + HLS + S2 + CDL + SSURGO live, with a note); **"Why not BC yet" card**: three lines (no OpenET, no field-soil API, one station per valley, labels since 2011) + "next step" link to the BC appendix; footprints and zones toggles.
2. **Your field's year** [M]: calendar rows 2016–2025 (hatched unknown, brown bare, light green partial, green covered, blue water), detector toggle and disagreement hatching, risk ticks, green-up/senescence markers, vulnerability strip, CDL history row, **news timeline** row, right rail with scale badges and model agreement.
3. **Trends** [M charts / S map].
4. **Priorities and constraints** [M]: six brief sliders + three collapsed; constraints (water source, allocation acre-ft/acre, livestock type dairy/beef/none, equipment, "no new perennials"); **market preference**; scenario panel.
5. **Compare** [M]: four columns; exposure rings; headline metrics: irrigation need (mm and acre-ft/acre) vs allocation, exposed heavy-rain days, OpenET-vs-ETc badge; nine score bars with whiskers and tie badges; RMA profile chips; Replay 2022 / 2023; "Open brief".
6. **Rotation brief** [M] (A4 print): header; cycle calendar; Why (LLM/template, chips); Evidence (3–6 bullets incl. feature-importance and stress lines and the OpenET check); Benefits by priority (nine rows); Funding and income box (EQIP 340 range; NASS/AMS prices); Insurance history (RMA profile); Crop-role chips; Gaps; Needs local review (severity, tick boxes; includes "allocation exceeded", "SGMA status", "waterfowl habitat / straw management", "herbicide carryover"); footer sources + AI check line.
7. **Satellite vs ground** [M]: OpenET vs ETc monthly (headline chart); CIMIS vs POWER ETo and Tmin/Tmax; IMERG vs CIMIS/NOAA vs POWER rain; SMAP vs L4 vs bucket model; GRACE vs DWR wells; Model comparison panel; grids page with footprints.
8. **Limits** [M]: B11.

### B9. News timeline [M]

- **Sources (cached Saturday):** Google News RSS `https://news.google.com/rss/search?q=<q>&hl=en-US&gl=US&ceid=US:en` (CA) and `hl=en-CA&gl=CA&ceid=CA:en` (BC) (V ✓, unofficial, server-side cache); GDELT DOC 2.0 `https://api.gdeltproject.org/api/v2/doc/doc?query=<q>&mode=artlist&format=json&startdatetime=…&enddatetime=…` (V; ~1 req / 5 s; pre-fetch); ca.gov feeds: DWR news https://water.ca.gov/News , State Water Board press releases https://www.waterboards.ca.gov/press_room/ , CDFA (U RSS availability; scrape and cache if no RSS); farm press agalert.com (RSS U); BC Gov News RSS Agriculture & Food and Water, Land & Resource Stewardship (V ✓).
- **Queries:** CAR 2022: `(Colusa OR Glenn OR "Sacramento Valley" OR "Glenn-Colusa") AND rice AND (drought OR fallow* OR allocation OR "Central Valley Project")` after:2022-02-01 before:2022-11-30; CAR 2023: `("Sacramento Valley" OR Colusa OR Glenn) AND (rice OR farm*) AND ("atmospheric river" OR flood* OR "late planting")` after:2022-12-20 before:2023-11-15; CAF 2023: `("Tulare Lake" OR Kings County OR Corcoran OR Tulare) AND (flood* OR "atmospheric river") AND (dairy OR farm* OR alfalfa OR crop*)` after:2023-03-01 before:2023-08-31; CAF 2024: `("Tulare Lake" subbasin OR "Kings County") AND (probation OR SGMA OR groundwater)` after:2024-03-01 before:2024-06-30; BC opener: Salmon River `("Salmon River" OR Shuswap OR "Salmon Arm" OR Westwold OR "Bessette Creek") AND (drought OR "fish protection order" OR curtail* OR "fish population protection") AND (farm* OR forage OR hay OR irrigation OR rancher*)` after:2023-06-01 before:2023-10-15; Sumas `("Sumas Prairie" OR Abbotsford OR "Fraser Valley") AND ("atmospheric river" OR flood*) AND (farm* OR dairy OR blueberr* OR livestock)` after:2021-11-10 before:2021-12-31.
- **Ranking:** government (ca.gov, usda.gov, news.gov.bc.ca) > farm press (agalert.com, farmprogress.com, countrylifeinbc.com, sjvwater.org) > other; drop items without a place match; dedupe; 1–3 per marker.
- **Marker:** date, NASA signal (SMAP percentile / IMERG 3-day / GRACE percentile), headlines, and `lead_days = event_date − first date of a ≥ 7-day run with SMAP percentile < 10 (or IMERG 3-day > 95th percentile for wet events) in the preceding 120 days`, shown **only when computed**; otherwise "lead time: computing".

### B10. Validation, demo, workstreams

#### B10.1 Validation checks (`checks/`, run before anyone pitches)
1. Coordinates and polygons: lon/lat order logged; CAR polygon on CDL rice 2021 and fallow 2022; CAF polygon on alfalfa/corn history and flagged if inside the 2023 DSWx water extent.
2. Units/ranges asserted on load (POWER mm/day, °C; IMERG mm/day; SMAP 0.02–0.6; NDVI −1..1; LST 250–340 K; GRACE 0–100; OpenET 0–400 mm/month; CIMIS ETo 0–15 mm/day).
3. **Headline validation:** modelled rice ETc (2019, 2021, 2023) vs OpenET Ensemble for the CAR field; alfalfa and corn ETc vs OpenET for CAF; target |bias| ≤ 25% (U expectation; record whatever it is and print it).
4. ETo: POWER Hargreaves vs CIMIS 250 and the CAF station, monthly bias and RMSE (expect Hargreaves high bias in windy/dry months; record).
5. Rain: monthly IMERG vs CIMIS/NOAA; Jan–Mar 2023 is a top-3 multi-month total in all sources; 2022 winter below climatology.
6. Drought: SMAP and GRACE percentiles for 2021–22 below 30 at both presets; USDM county ≥ D3 weeks in 2021–22 (V expectation).
7. Cover: observed consensus cover vs modelled baseline ≥ 60% agreement; CDL shows fallow 2022 at CAR; alfalfa/corn history at CAF.
8. ML: test-year accuracy ≥ 0.85 and F1(bare) ≥ 0.80 on the 2022 hold-out, or ML ships with a "below target" badge; transition MAE reported; rule-vs-ML disagreement < 15% or explained.
9. Stress: both methods flag ≥ 2 weeks in Jul–Aug 2021 and 2022; 2023 flood weeks appear as water, not stress.
10. Lead time: `lead_days` computed for CAR 2022 (allocation announcement date, U) and for the BC opener chart (16 Aug 2023) if built; UI shows "computing" otherwise; pitch states no number not produced by the pipeline.
11. LLM: rejection rate logged; zero unchecked sentences; 10 sentences spot-read.
12. Scores: baseline erosion 0; full-year cover → exposed rain days ≈ 0; alfalfa summer ETc > small-grain ETc; rice I > wheat I; +2 °C increases ETo; allocation check triggers when I > allocation.
13. Sources: every SourcedNumber has a URL; `verified:false` count printed per brief; References field lists every dataset, library, image.

#### B10.2 Demo script (3 min local pitch) and 7-slide outline
- 0:00 (30 s) **BC opener (multigenerational):** "Three generations on the lower Salmon River. On 16 Aug 2023 about 398 licence holders were told to stop irrigating forage. Two years earlier, Sumas Prairie went under." Show the cached BC news timeline (and the one NASA-only chart if built, with lead time only if computed). "BC has the problem and NASA's data, but not the ground data to prove a tool works: no field-level water use, no soil API, one station per valley. So we built and validated it where the data is rich."
- 0:30 (2:00) **California demo:** Colusa calendar (2022 fallow, 2023 storms; rule vs ML toggle; vulnerability strip; news markers) → OpenET vs ETc chart ("measured vs modelled") → priorities incl. allocation and market preference → compare (tie badge, nine lines, RMA chips, scenario slider) → one brief (checked-AI footer, EQIP range, local review) → 15 s on the Tulare/Kings preset (alfalfa under a pumping cap, 2023 flood weeks as water).
- 2:30 (30 s) **Close:** "Supports the grower and adviser; never replaces them. Every number has a source; every model shows its accuracy and where it disagrees; the water numbers are checked against measured ET. Next step: bring it home to BC, where the same satellites already see the problem."
- Slides (V: 7 max or 30-s video with English subtitles): 1 title; 2 BC motivation (two events, news, the data gap); 3 "built where data is rich": CA presets and data stack; 4 calendar + detectors + validation chart; 5 compare + scenario; 6 brief + AI check + uncertainty; 7 limits and next step (BC). References field complete.

#### B10.3 Six-person workstreams

| # | Owner | Saturday | Sunday |
|---|---|---|---|
| 1 Regional data + news | POWER, IMERG, SMAP L3/L4, GRACE, USDM cached for both CA presets (point + 11×11); ETo; risk days; CA + BC news windows cached and ranked; BC opener chart data [S] | disagreement metrics; lead-time computation; Trends layers |
| 2 Field data + zones | HLS, S2, MODIS, ECOSTRESS, NASADEM, CDL, OpenET (30 m + point) cached; weekly feature table; rule detector; zone rasters; DSWx [S] | observed-vs-modelled agreement; hotspots + OpenET zones; calendar exports |
| 3 AI | CDL-based labels for both boxes; RF/HGB detectors with ModelReports (year and spatial splits); z-score + isolation forest; LLM prompt + validator with cached briefs | cross-valley test; model comparison panel data; rejection report |
| 4 Rotation engine + CA adapter | crops.json (FAO-56, UC ANR, covercrop-selector, PLANTS), 8 strategies, scoring v1 with ranges and scenario recompute; adapter: SSURGO SDA, OpenET, CIMIS, CDEC, DWR, RMA, NASS/AMS, EQIP; API | income/funding, pest/infiltration/N-scavenging, allocation check, local_review rules |
| 5 Frontend | screens 1, 2, 4, 5 against fixtures; glossary and role cards; "Why not BC yet" card | screens 3, 6, 7, 8; print CSS; phone width; polish |
| 6 Integration, validation, story | repo, schemas, fixtures, pre-commit source check, `checks/`; BC opener story and news selection; slide skeleton | runs all checks incl. OpenET headline; owns demo laptop and offline cache; 30-s video; 3× rehearsal; submit before 11:59 pm |

**First-hour contracts:**
1. `schemas/`: SourcedNumber, Location, Crop, RotationStrategy, ModelReport, NewsItem, FeatureRow; API routes (B3); CA adapter interface `get_soil(polygon)`, `get_crop_history(polygon)`, `get_station_daily(id)`, `get_field_et(polygon)`, `get_loss_profile(county, commodity)`, `get_prices(commodity)`, `get_water_context(location)`.
2. Preset IDs `car_colusa_rice`, `caf_tulare_forage`; polygons committed; CRS EPSG:32610; 10 km training boxes committed.
3. Cache paths and `meta.json`; fixtures for both presets so the frontend starts at hour 2.
4. Keys on the data laptop: **Earthdata** login (GES DISC, NSIDC, LP DAAC/AppEEARS authorised, `.netrc`), **OpenET**, **CIMIS**, **USDA NASS** Quick Stats, **USDA AMS** My Market News, **LLM** API; MPC/Earth Search reachable; GDELT pre-fetch started; RMA yearly files downloaded.
5. Definitions of done: number = value, unit, low, high, method, source URL (pre-commit); model = ModelReport with split, metrics, disagreement; LLM sentence = `checked: true`; validation = check 3 (OpenET vs ETc) produces a number before anyone writes a slide about water.
6. Must-have list frozen to [M]; [S] starts only after both CA presets run offline end to end; merge every 3 hours; feature freeze Saturday 22:00.

### B11. What the data cannot support (the app's Limits page)

- **BC is out of scope for the demo.** The BC news timeline and the optional NASA-only chart show the problem; no BC field was modelled, scored or validated. **Transferability to BC is a claim to test**, not a result: without OpenET, field-scale soil data and dense stations, the ETc and bare-period estimates there are unvalidated.
- SMAP, IMERG, POWER, GRACE and USDM cannot distinguish one field from its neighbour; they describe weeks and years across the valley or basin. GRACE's underlying signal is ~300 km.
- HLS/Sentinel-2 see cover, greenness and water, not soil loss, infiltration, nitrate or yield; winter cloud leaves gaps; flooded rice and the 2023 lake read as water, and SMAP retrievals there are unreliable.
- ECOSTRESS overpasses are irregular; LST/ET are used as anomalies. OpenET is a model ensemble calibrated to flux towers, not a direct measurement; it is the best available field-scale reference, not truth.
- ML detectors are trained on CDL year classes plus calendar windows; in-season failures are unlabelled; 2022 fallow is the single true bare hold-out year. Stress models have no labelled stress events and are checked against a handful of episodes.
- The LLM rephrases sourced numbers; rejected sentences are replaced by templates; emphasis is still a choice the adviser should read critically.
- Scores are rule-of-thumb composites of ratings and FAO-56 coefficients; silage-corn end-stage Kc, rice flood/percolation water, cover-crop species after rice, sorghum-sudan water savings and all yields are U until cited; prices and EQIP rates are ranges from public series and schedules.
- Scenario sliders scale temperature and rain uniformly; they are not climate projections. Lead time between a satellite signal and an event is an observation on one or two events, not a forecast.
- SGMA status is in litigation and changes; the tool shows a dated status line with a source, not legal advice. Allocation checks use the user's number.
- Pest-cycle break is a family-rotation rule of thumb; no pest or disease dataset exists behind it.
- Preset calendars, field sizes and allocations are typical examples, not measured farms. Every alternative rotation needs review by the grower and an adviser before anything is seeded; that sentence is on every brief.

---

## Appendix A: BC context (not on the build path)

Kept for the opener, the "next step" slide and a future BC version. All [S].

- **FV (Fraser Valley wet, Sumas Prairie dairy):** 49.06 N, −122.17 W (U); Sumas Soil Management Group 2,650 ha, very poorly drained lacustrine deposits (V: https://www.env.gov.bc.ca/esd/distdata/ecosystems/Soils_Reports/Docs/soil_mgmt_hbk_fraservalley.pdf ); ECCC Abbotsford A 50308/54238, Agassiz RCS 706 (V). Baseline continuous silage corn with bare Oct–Apr; alternatives: corn + fall rye cover (late-Sept seeding improves survivability; terminate at stem elongation; DM 3,360–10,800 kg/ha; V BC factsheet https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/agriculture-and-seafood/agricultural-land-and-environment/soil-nutrients/cover-crops/fall_rye_final.pdf ), corn + Italian ryegrass relay at 6-leaf (relay cut runoff 53% and sediment 74% in a Lower Fraser Valley study, V via https://bcfoodweb.ca/node/479 ), 3-yr grass-legume hay then corn.
- **SR (Salmon River / Shuswap drought):** 50.62 N, −119.33 W (U; inside order M0238_2023 area); Salmon Arm CS 6843 (1991–2026), Vernon Auto 46987, Kamloops A 51423 (V). Baseline alfalfa 2 cuts, 5-yr stand (V Kamloops Forage Manual 2002); alternatives: barley break year, 1/5 of stand in fall-seeded cereal silage harvested before an August order (cereals "the most commonly grown alternatives" under limited irrigation, V BC 2005 factsheet https://www.irrigationtoolbox.com/ReferenceDocuments/Extension/BCExtension/665000-6.pdf ), sainfoin-grass on the bench (V https://www.bcclimatechangeadaptation.ca/app/uploads/BF04-FactSheet-Non-bloat-Legumes-2023.pdf ).
- **BC data stack for a future version:** SoilGrids v2 REST (V ✓), AAFC Annual Crop Inventory and Crop Rotations GeoTIFFs (V ✓), ECCC bulk CSV / api.weather.gc.ca (V), BC cover-crop factsheets (23 species, V), BC Drought Portal (V), BC Gov News RSS (V ✓). Missing: field-scale ET, field-scale soil API, dense agro-met network.
- **BC facts for the opener (V):** 16 Aug 2023 order, ~398 licence holders, mid-June −50% mailouts (https://news.gov.bc.ca/releases/2023FOR0052-001305 ); Sumas Nov 2021 figures (Country Life in BC; CBC). Hay $75→$190/bale is U until verified in Country Life in BC.
