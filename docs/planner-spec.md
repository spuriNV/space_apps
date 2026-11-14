# Field Shift planner: idea and build spec

One rotation planner, two BC water regimes, built around a bare-field calendar and a per-strategy rotation brief. Written to be handed to coding agents; every number carries a source or is marked **UNVERIFIED**. Where this doc says "verify", a human opens the link before the number ships.

Marker key: **V** = read from the cited source during research for this spec. **U** = unverified / assumed / inferred; must be confirmed or labelled "assumed" in the UI.

---

## Part A: The idea

### A1. The real problem and who has it

BC farms sit on two water extremes, and both of them punish an uncovered or water-hungry field.

**Drought regime (Thompson / Nicola / Okanagan).**
- August 2023: the province put the North and South Thompson basins at drought Level 5 (the top level); Kamloops banned lawn sprinklers while field irrigation continued. Source (V, news): https://amp.cbc.ca/lite/story/1.6936387 and https://www.castanetkamloops.net/news/Kelowna/442219/Much-of-BCs-Interior-now-at-a-Level-5-drought
- Ranchers hauled water for livestock; the BC Cattlemen's Association was still pressing the province on lingering drought and costs in May 2026 (V, news): https://cfjctoday.com/?p=1092333
- Okanagan crop water demand is projected to rise ~37% (745 to 1021 mm/yr) between present day and 2070–2099 (V): Neilsen et al., Frontiers in Environmental Science 2018, https://www.frontiersin.org/articles/10.3389/fenvs.2018.00074/full
- Forage in the Kamloops area is grown mainly as winter feed for beef cattle; two alfalfa cuts a year with aftermath grazing, continuous alfalfa on a ~5-year cycle is a common system (V, 2002 Kamloops Forage Manual, archived): https://bac-lac.wayback.archive-it.org/web/20080212123631/http://www.al.gov.bc.ca/forage/publications/documents/kamloops_forage_manual.pdf
- Regional scale: alfalfa 42,418 ha and other hay 61,162 ha in the Thompson-Okanagan (V, GrowBC 2016 profile): https://www.bcaitc.ca/sites/default/files/resources/ThompsonOkanagan.pdf
- The province's own drought-in-agriculture page: https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/agricultural-land-and-environment/water/drought-in-agriculture

**Wet regime (Fraser Valley / Sumas Prairie).**
- 14–15 Nov 2021 atmospheric river: Sumas dike breach, ~1,100 farms under evacuation order or alert, ~150 km² of farmland flooded; ~2,500 acres of blueberries affected (V, news/Wikipedia; figures from different outlets do not reconcile exactly): https://en.wikipedia.org/wiki/2021_British_Columbia_floods , https://www.countrylifeinbc.com/catastrophic-flooding-hits-fraser-valley/
- Soil scientist quoted that floodwater strips topsoil, "the most organic and important layer", into the Fraser (V): https://www.cbc.ca/lite/story/1.6261829
- The everyday version of the same problem is not the dike; it is bare silage-corn ground from October to April under 150+ mm months. A Lower Fraser Valley study found an Italian ryegrass relay crop under silage corn cut mean annual runoff 53% and suspended-solids load 74% (V, via bcfoodweb/ASA abstract; locate the primary paper before quoting on a slide): https://bcfoodweb.ca/node/479
- Nitrogen left in the soil or mineralised after mid-August is lost over winter unless a winter cover crop is grown (V, BC Ministry cover-crop material): https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/agricultural-land-and-environment/soil-nutrients/management/cover-crops
- BC Ministry fall rye factsheet: planting in late September increases winter survivability versus late August; terminate at stem elongation (V): https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/agriculture-and-seafood/agricultural-land-and-environment/soil-nutrients/cover-crops/fall_rye_final.pdf

**Who has the problem.** Two personas, and the tool must serve them together:
1. The farmer: a Fraser Valley dairy producer growing silage corn and grass; an Interior rancher growing irrigated alfalfa/grass hay for winter feed.
2. The agrologist: a BC Ministry regional agrologist / AgriServiceBC staff or a private P.Ag. who already sits with farmers to talk rotations, Environmental Farm Plans and water licences. This is the person who will actually open the tool. The brief's own line is "does not replace farmer judgment or local agricultural expertise", so design the agrologist in, not out.

### A2. User story (concrete)

Maria runs 120 dairy cows on Sumas Prairie; her 12 ha "back field" has been continuous silage corn for nine years. In March she meets Dev, the regional agrologist, about her Environmental Farm Plan. Dev opens the planner on a laptop, picks the Fraser Valley preset, drags the field boundary over her back field. The bare-field calendar shows the field has read as bare on Sentinel-2 from roughly mid-October to late April in six of the last seven years, and overlays the heaviest-rain days from IMERG and the Abbotsford station on top: nearly all of them fall inside the bare window, including 14–15 Nov 2021. Maria sets priorities: erosion and organic matter high, forage value medium, water use low (she is not short of water). The compare screen shows her baseline against (1) corn + fall rye cover seeded late September, (2) corn + Italian ryegrass relay seeded at 6-leaf corn, (3) three years of grass-legume hay then corn. Exposed risk-days drop from ~45 to ~8–15 for the cover-crop options. The ryegrass relay scores highest on her weights but its range overlaps fall rye, so the tool says "tie within uncertainty" and lists the reasons: establishment under a tall corn canopy is site-specific; the data cannot see her tile drains. Dev prints the two rotation briefs; each ends with "needs local review" items (seeding window vs. her harvest date, herbicide program compatibility, waterfowl grazing pressure in Delta-type sites). They decide to trial the relay on half the field this year. Replay mode shows what the Nov 2021 and Jan 2024 storms would have landed on under each option.

Interior mirror: Jake has 40 ha of pivot-irrigated alfalfa east of Kamloops; in 2023 his licence volume was short. The planner shows seasonal crop-water demand per rotation from POWER-derived ETo × FAO-56 Kc, the 2023 SMAP dryness anomaly, and three options that put part of the stand into fall-seeded cereal silage, a sainfoin-grass mix on the well-drained bench, or a barley break year before re-seeding.

### A3. The decision it changes, and why NASA data is uniquely useful

The decision is **what goes into the open window, and when**: which cover/relay/forage crop, seeded in which week, on which field, against which weeks of risk. Today that decision is made from memory and a factsheet. The tool changes two inputs:
1. "When is this field actually bare?" becomes observed (Sentinel-2/Landsat, 10–30 m, 7+ years) instead of assumed.
2. "When does the weather hit?" becomes a multi-decade daily record at the farm (POWER 1981–present, IMERG 2000–present, SMAP 2015–present), not a single station that may be 30 km away in another valley. In the Interior the nearest ECCC station is often not in the same microclimate; the satellite record is continuous and everywhere.

NASA data is not used to "recommend a crop". It is used to measure exposure (bare × risk) and water demand (ETo). Crop properties come from BC factsheets. That split is the honest one and it maps onto the brief's "what evidence supports it".

### A4. What exists, and how this differs

| Existing tool | What it does | What it does not do |
|---|---|---|
| BC Agriculture Water Calculator (https://bcwatercalculator.ca/) (V exists) | Annual irrigation / livestock water demand for licensing, crop × soil × climate | No rotation comparison, no satellite observation, no bare-period, no uncertainty |
| BC Agriculture Water Demand Model (https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/agricultural-land-and-environment/water/water-management/agriculture-water-demand-model) (V) | Basin planning: ETo × Kc per polygon, daily, station-driven | Planner-facing, not farmer-facing; no field observation; no alternatives |
| BC AgriWeather / ET calculator, Farmwest (https://farmwest.com/) (V exists) | Station-based ET and irrigation scheduling | Scheduling within a season, not rotation choice; no satellite |
| Canadian Drought Monitor / Drought Watch (AAFC) (U: check current URL) | Monthly regional drought map | Regional; no field, no crops |
| OpenET | Field-scale ET | Western US states only (V, challenge Resources tab wording) |
| CropPlan+ (FCC/AgExpert), Cropwise-type apps (V exist) | Field records, crop planning, commercial | Closed, no exposure window, no uncertainty, no NASA data |
| BC cover crop factsheets (23 species) (V) | Ratings for goals/tolerances/drainage | Static PDFs; not combined with a field's observed calendar or weather |

The gap: nothing combines *when my field is bare* + *when the weather hits* + *which rotation covers it* + *how sure are we*, in language a farmer and agrologist can read together. We make the factsheets computable and put them against the field's own satellite record.

### A5. Creative twists (on-brief)

1. **Exposure calendar.** A 12-month ring (or heat strip) per rotation: bare days shaded, risk days (extreme rain / frost / heat / dry spell) drawn as ticks; the intersection is the single headline number "exposed risk-days". Four rings side by side make the trade-off visible in two seconds and directly answer "highlight times when fields are typically bare".
2. **Replay a real year.** Toggle "Replay Nov 2021" or "Replay summer 2023": the proposed rotation calendar is run against the observed daily data of that year, so the farmer sees what the storm or drought would have landed on. Cheap to build (same data), high Presentation value.
3. **Agrologist hand-off.** The rotation brief is a print/PDF page with every number footnoted, gaps listed, and a "review before acting" checklist with tick boxes. The product of the session is a document two people can sign off on, which is exactly the brief's "risks that would need local review by farmers or agricultural experts".
4. (Baseline, not a twist) **"What the satellite can't see" panel**: draw the actual SMAP 9 km, IMERG 0.1°, and POWER 0.5° pixel footprints over the field polygon. Turning the weakness into an explicit screen earns the "clarify how satellite observations differ from ground-based measurements" consideration.

### A6. The weakest point, and the defense

**Weakest point:** the rotation scores are rule-of-thumb from factsheet ratings and FAO-56 coefficients, not a calibrated crop model, and there is no yield or dollar output. A sceptical judge (physics / data) will ask "how do you know fall rye reduces erosion here?" and "isn't the SMAP pixel bigger than the whole farm?"

**Defense (say it before they ask):**
- We never output a recommendation; we output a comparison with ranges, and we show a tie when ranges overlap. The brief asks for "a supportive tool … not replace farmer judgment".
- Every number has a source link in the UI. Crop ratings are the BC Ministry's own factsheets; coefficients are FAO-56 Table 12; the only things we compute from NASA data are exposure and water demand, which is what satellites are actually good at.
- Scale is on screen, not hidden: field-scale data (10–30 m) does field-scale jobs (bare period, slope); regional data (SMAP, IMERG, POWER) does regional jobs (which years and weeks were dry, wet, cold, hot). The scale badge says which is which.
- We validate against the ground: IMERG and POWER are compared with the Abbotsford A and Kamloops A stations on the validation panel, and the disagreement widens our ranges.
- Dollar/yield is listed under "gaps" and "market suitability" is explicitly a local-review item. Judges reward honesty about gaps more than a fake yield number.

Second weakness: "why not just a station?" Answer: the station is 1 point; the field calendar needs the field, and the Interior's valleys are under-sampled. We use both and show the difference.

---

## Part B: Build spec

### B1. Preset farms

Both presets are *representative* fields, not real farms. Say so in the UI ("Example field; drag to your own"). Pick the final polygon on Saturday morning against the AAFC Annual Crop Inventory so that the pixel is actually the crop we claim (see B2.8).

#### Preset FV (Fraser Valley, wet regime): Sumas Prairie dairy field

| Item | Value | Status / source |
|---|---|---|
| Centre | 49.06 N, −122.17 W (Sumas Prairie, between Abbotsford and Chilliwack) | U: representative; confirm field is corn/forage in ACI 2023/2024 |
| Field size | 12 ha rectangle (~350 × 350 m) | U: typical dairy field assumed; 2021 Census Ag-in-Brief for Fraser Valley CD gives area totals, not field sizes: https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/agriculture-and-seafood/statistics/census/ag-in-brief/ag_in_brief_2021_-_cd_fraser_valley.pdf |
| Soil | Sumas Soil Management Group: 2,650 ha, level lacustrine deposits exposed when Sumas Lake was drained; "soils are very poorly drained". Surrounding Fairfield group: 11,000 ha, imperfectly drained (Matsqui, Sumas, Chilliwack, Pitt Meadows) | V: Soil Management Handbook for the Lower Fraser Valley, https://www.env.gov.bc.ca/esd/distdata/ecosystems/Soils_Reports/Docs/soil_mgmt_hbk_fraservalley.pdf ; BC Soil Information Finder: https://www2.gov.bc.ca/gov/content/environment/air-land-water/land/soil/soil-information-finder |
| Slope | ~0–1% (prairie); compute from NASADEM | V method; value U until computed |
| Elevation | ~5–10 m | U |
| Nearest ECCC stations | Abbotsford A: stationID 50308 (2011–2026), 54238 (2016–2026), legacy 702 (1944–2012); Agassiz RCS 706 (1988–2026); Chilliwack South 51978 (2018–2026) | V: ECCC Station Inventory EN.csv |
| Irrigation | None assumed (rain-fed) | U |

Baseline FV0: continuous silage corn, bare winter.

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FV0 Corn only | bare | bare | bare | bare/tillage | corn plant | corn | corn | corn | corn harvest (late) | bare | bare | bare |

Alternatives (crop properties from the BC factsheets linked in B4.2):

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FV1 Corn + fall rye cover | rye (dormant cover) | rye | rye | rye, terminate at stem elongation | corn plant | corn | corn | corn | corn harvest; drill fall rye late Sept | rye establishing | rye | rye |
| FV2 Corn + Italian ryegrass relay | ryegrass | ryegrass | ryegrass (graze/cut) | terminate | corn plant | corn; broadcast IRG at 6-leaf | corn + IRG understory | corn + IRG | corn harvest; IRG released | IRG | IRG | IRG |
| FV3 3-yr grass-legume hay then corn (year shown = hay year) | sod | sod | sod | 1st growth | cut 1 | growth | cut 2 | growth | cut 3 | sod | sod | sod |

Notes (V unless marked): fall rye late-Sept planting improves survivability; terminate at stem elongation to limit N immobilisation; can use "significant amounts of moisture in the spring", allelopathic to following alfalfa, ergot risk (fall rye factsheet). Italian ryegrass relay: seed between rows at corn 6-leaf; shorter-season corn harvested ~2 weeks earlier increases relay growth; relay biomass at corn harvest 0.3–1.2 t DM/ha in trials; tetraploid biennial types performed best (V via https://bcfoodweb.ca/node/479 and https://www.bcclimatechangeadaptation.ca/app/uploads/FI17-Final-Report-Innovative-Corn-Practices-2023.pdf). Italian ryegrass is winterkilled in many regions of Canada but can overwinter in milder zones (V, BC annual ryegrass factsheet). Silage corn harvest date in the Fraser Valley: late Sept–mid Oct (U: assumed; confirm with an agrologist or the FI17 report). FV3 species (orchardgrass/tall fescue + red or white clover) U: pick from BC factsheets; mark "example mix".

#### Preset KT (Kamloops / Thompson, drought regime): irrigated hay field

| Item | Value | Status / source |
|---|---|---|
| Centre | 50.68 N, −120.10 W (South Thompson valley bottom, east of Kamloops) | U: representative; shift to a pixel classed as forage in ACI |
| Field size | 32 ha circle (centre pivot, ~640 m diameter) | U: example listing near Walhachin shows 70 acres (~28 ha) under pivot: https://www.landquest.com/listings/high-quality-agricultural-land-under-pivot-irrigation-walhachin-bc |
| Soil | Valley-bottom alluvial / terrace soils, Brown to Dark Brown Chernozemic order typical of the dry Interior | U: confirm with BC Soil Information Finder and the BC Detailed Soil Survey (https://open.canada.ca/data/en/dataset/adf4d26a-9fc0-44c9-ba38-620531ca0dbe) |
| Slope | 0–3% on the flat; compute | U until computed |
| Elevation | ~350 m | U |
| Nearest ECCC stations | Kamloops A 51423 (2013–2026), Kamloops AUT 42203 (2006–2026), legacy Kamloops A 1275 (1951–2013); Kelowna UBCO 51117; Merritt 49408 | V: Station Inventory |
| Irrigation | Sprinkler/pivot; licence volume as a user input (m³/yr) | U default |

Baseline KT0: continuous alfalfa (or alfalfa-grass), ~5-year stand, 2 cuts, aftermath grazed in fall (V, Kamloops Forage Manual 2002).

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KT0 Alfalfa, 2 cuts | dormant | dormant | dormant | green-up | growth, irrigate | cut 1 | regrowth, irrigate | cut 2 | aftermath graze | dormant | dormant | dormant |
| KT1 Alfalfa with barley break year (year 6 of cycle shown) | bare/stubble | bare | bare | seed barley | barley | barley | barley greenfeed/silage harvest | bare → re-seed alfalfa late Aug | alfalfa establishing | establishing | dormant | dormant |
| KT2 1/5 of stand each year in fall-seeded winter cereal silage (cereal year shown) | winter rye/triticale | dormant | green-up | rapid growth (spring moisture) | growth, light irrigation | silage harvest early–mid June | bare or short-season annual | fall-seed next cereal or alfalfa | establishing | establishing | dormant | dormant |
| KT3 Sainfoin-grass hay on the well-drained bench | dormant | dormant | dormant | green-up | growth, irrigate | cut 1 | regrowth | cut 2 (or graze) | aftermath | dormant | dormant | dormant |

Notes (V unless marked): "cereals are the most commonly grown alternatives" when irrigation water is limited; fall rye "suitable if fall moisture available"; spring rye more drought tolerant than barley; oats less drought tolerant than barley (V, BC Ministry 2005 factsheet on alternate forages under limited irrigation: https://www.irrigationtoolbox.com/ReferenceDocuments/Extension/BCExtension/665000-6.pdf). Alfalfa is among the most drought-resistant tame forages because of its deep roots and goes dormant when water is short (V, BC grazing-lands drought guide: https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/agriculture-and-seafood/agricultural-land-and-environment/biodiversity/grazing-management-guide/15_-_managing_grazing_lands_during_drought.pdf). Sainfoin: drought tolerant, non-bloat, low tolerance of "wet feet", intolerant of acidity/salinity; not a substitute where alfalfa fails from high water table (V, https://www.bcclimatechangeadaptation.ca/app/uploads/BF04-FactSheet-Non-bloat-Legumes-2023.pdf). Birdsfoot trefoil, sainfoin, cicer milkvetch have moderate-high drought tolerance (V, https://www.bcclimatechangeadaptation.ca/library/legumes-for-resiliency-fact-sheet/). Winter triticale similar biomass to fall rye, less weed suppression (V, BC winter triticale factsheet). Harvest and seeding weeks for KT1–KT3 are U (typical, not sourced); label "typical timing, adjust locally".

Honest limit: KT alternatives mostly trade *summer irrigation demand* for *spring moisture use* and stand life; the tool can quantify the ETc side but cannot quantify yield or feed quality. Say so in the brief's gaps.

### B2. Data pipeline

General rules:
- One field = one polygon (GeoJSON). All coarse data are sampled at the centroid and the sampled pixel footprint polygon is stored. All fine rasters are clipped to the field bbox + 500 m and reduced to field statistics.
- Common time step: **daily table, 2015-01-01 to 2025-12-31** (SMAP start bounds the common period); POWER and Landsat extend back further and are kept in their own longer tables for climatology.
- Cache everything on Saturday; the demo never calls a NASA server. Layout: `data/cache/<preset_id>/<dataset>.parquet` plus `<dataset>.meta.json` {url, params, fetched_at, pixel_footprint_geojson, native_resolution_m, native_timestep, units, fill_value}. Rasters: `data/cache/<preset_id>/rasters/<dataset>_<date>.tif` (COG, EPSG:32610 for both presets).
- Time zone: POWER daily is UTC by default (LST option exists); IMERG daily is 00–24 UTC; ECCC daily is local. Compare at monthly totals, or allow ±1 day when matching event days.
- Fill values: POWER uses −999; drop them. SMAP: use `retrieval_qual_flag` (keep recommended-quality only) and drop frozen-ground days.

#### B2.1 NASA POWER (meteorology, ETo inputs) — no auth

- Endpoint (V, structure from https://power.larc.nasa.gov/docs/services/api/temporal/daily/):
  `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR&community=AG&longitude=-122.17&latitude=49.06&start=19810101&end=20251231&format=JSON`
- Limits (V): max 20 parameters per point request; 0.5° × 0.5° grid (met is MERRA-2 at ~0.5° × 0.625°); repeated identical requests may be blocked, so cache.
- Use: T2M_MIN for frost days; T2M_MAX for heat days; Hargreaves ETo (FAO-56 eq. 52: `ETo = 0.0023 × (Tmean + 17.8) × (Tmax − Tmin)^0.5 × Ra`, Ra from latitude and day of year, FAO-56 ch. 3) as primary; FAO Penman-Monteith with RH2M, WS2M, ALLSKY_SFC_SW_DWN as the upgrade if time allows. FAO-56: https://www.fao.org/4/x0490e/x0490e00.htm
- PRECTOTCORR is a reanalysis/merged precipitation, not a gauge; use it as the third opinion in the disagreement panel, not as truth.
- Cache: `power_daily.parquet` columns date, t2m, t2m_max, t2m_min, rh2m, ws2m, sw_down, prectotcorr, eto_hargreaves.

#### B2.2 GPM IMERG daily (extreme rain) — Earthdata login likely

- Product: GPM_3IMERGDF V07 (Final, daily, 0.1°, ~June 2000–present) (V, GES DISC catalog: https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergdf-07). Use variable `precipitation` (mm/day).
- Access options, in order of preference:
  1. GES DISC Hydrology Data Rods / Giovanni time-series service, point query, ASCII back. Documented inputs are variable, location, startDate, endDate, type (V, https://www.earthdata.nasa.gov/learn/articles/data-rods-for-hydrology ). Known URL pattern (U: confirm the exact variable string on the how-to page https://disc.gsfc.nasa.gov/information/howto?title=How%20to%20Access%20the%20Hydrology%20Data%20Rods%20Time%20Series%20API%20Using%20Python ):
     `https://hydro1.gesdisc.eosdis.nasa.gov/daac-bin/access/timeseries.cgi?variable=GPM:GPM_3IMERGDF_07:precipitation&startDate=2015-01-01T00&endDate=2025-12-31T23&location=GEOM:POINT(-122.17,%2049.06)&type=asc2`
     Needs Earthdata login (cookie/.netrc) and GES DISC app authorisation on the account.
  2. AWS Open Data mirror of GPM_3IMERGDF (V listed: https://registry.opendata.aws/nasa-gpm3imergdf/ ; U whether anonymous access works). Read the 0.1° cell for the centroid with xarray/h5py.
  3. GES DISC OPeNDAP subset of the daily files with .netrc.
- Pixel footprint: 0.1° ≈ 11 km N–S × 7 km E–W at 49–51°N ≈ 80 km². Store it.
- Cache: `imerg_daily.parquet` date, precip_mm, source_option.
- Fallback if auth fails on the day: use ECCC station precipitation for the event calendar and PRECTOTCORR for the satellite side; label clearly. Do not fake IMERG.

#### B2.3 SMAP soil moisture (dry spells) — Earthdata login

- Product: SPL3SMP_E.006, 9 km EASE-Grid, daily, 31 Mar 2015–present (V, NSIDC and AppEEARS product list). Layers: `Soil_Moisture_Retrieval_Data_AM/soil_moisture` (m³/m³), `.../retrieval_qual_flag`. Also available: SPL4SMGP.008 (L4 surface/root-zone, 9 km, 3-hourly, model-assimilated, gap-free) — if used, label "model-assimilated".
- Access: AppEEARS point sample (V: AppEEARS lists SPL3SMP_E.006 at 9000 m daily; API at https://appeears.earthdatacloud.nasa.gov/api/ ; login then POST /task with type "point", coordinates, dates, layers; poll; download CSV). Tutorial via NSIDC: https://nsidc.org/data/spl3smp_e
- Winter: retrievals are flagged/missing over frozen ground; treat Nov–Mar as "no satellite soil-moisture data" in the Interior rather than interpolating.
- Pixel footprint: 9 km × 9 km = 81 km². Store it.
- Cache: `smap_daily.parquet` date, sm_am, qual_flag, sm_am_valid.

#### B2.4 Sentinel-2 L2A (bare-field detection, 10 m) — no account

- STAC: Microsoft Planetary Computer `https://planetarycomputer.microsoft.com/api/stac/v1`, collection `sentinel-2-l2a` (V listed); sign asset hrefs with the `planetary-computer` Python package (free, no account). Alternative: Element84 Earth Search `https://earth-search.aws.element84.com/v1`, collections `sentinel-2-c1-l2a` (Collection-1 reprocessed) and `sentinel-2-l2a` (V listed), anonymous.
- Query: intersects = field polygon; datetime = 2017-01-01/2025-12-31 (U: expect reliable L2A from ~2019; earlier scenes may be missing); `eo:cloud_cover < 80` as a coarse filter, then per-field SCL masking (B5).
- Assets: `B04` (red, 10 m), `B08` (NIR, 10 m), `SCL` (20 m; resample nearest to 10 m). Read windowed with rasterio/stackstac/odc-stac; never download whole tiles.
- Cache: `s2_scenes.parquet` scene_id, date, cloud_cover_scene, valid_pixel_fraction_field, ndvi_median, ndvi_p10, ndvi_p90, bare_fraction; plus small clipped NDVI COGs for the UI (optional).

#### B2.5 Landsat Collection 2 Level 2 (long record, 30 m) — no account on MPC

- STAC: MPC collection `landsat-c2-l2` (V listed; 1982/84–present). Earth Search also lists `landsat-c2-l2` but the USGS bucket is requester-pays (U: avoid).
- Bands: `red`, `nir08`, `qa_pixel`. QA_PIXEL bits: 1 dilated cloud, 3 cloud, 4 cloud shadow, 5 snow (U: standard C2 bit layout; check the asset's `classification:bitfields`).
- Use: extend the bare-field climatology back to 2013 (L8) or earlier for "how long has this field been winter-bare"; Sentinel-2 remains primary for 2019+.
- Alternative all-in-one: HLS (HLSS30.020 / HLSL30.020, 30 m, harmonised, via AppEEARS, Earthdata login) (V listed in AppEEARS).

#### B2.6 Elevation / slope — no account

- NASADEM via MPC collection `nasadem` (V listed), or `cop-dem-glo-30` (V listed on both STACs); SRTMGL1_NC.003 via AppEEARS (V listed). 30 m.
- Compute slope (%) per pixel, then field mean and p90; also the flow-accumulation direction is unnecessary for the demo.
- Cache: `dem_field.tif`, `terrain.json` {slope_mean_pct, slope_p90_pct, elev_m}.

#### B2.7 ECCC station data (ground truth) — no auth

- Bulk CSV (V pattern): `https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=50308&Year=2021&Month=1&Day=1&timeframe=2&submit=Download+Data` (timeframe=2 = daily; one call per year).
- Stations (V, ECCC Station Inventory): FV: Abbotsford A 50308 (2011–2026) and 54238 (2016–2026); Agassiz RCS 706. KT: Kamloops A 51423 (2013–), Kamloops AUT 42203 (2006–); legacy Kamloops A 1275 for 1951–2013 climatology.
- Columns used: Total Precip (mm), Min Temp (°C), Max Temp (°C). Cache `eccc_daily.parquet`.

#### B2.8 AAFC Annual Crop Inventory (what is the current rotation) — no auth

- 30 m national GeoTIFF per year, optical + radar decision tree (V): https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9 ; ArcGIS ImageServer per year, e.g. `https://www.agr.gc.ca/imagery-images/rest/services/annual_crop_inventory/2019/ImageServer` (V exists for several years; use `/identify` for a point or export a small clip).
- Use: (a) confirm preset polygons are corn/forage; (b) show "observed crop history 2011–2024" under the baseline calendar as independent evidence of the current rotation. Class codes: read from the dataset legend (U: do not hard-code from memory). BC coverage caveat: 2021 had incomplete BC ground sampling (V, dataset notes).

#### B2.9 BC soils — manual

- BC Soil Information Finder Tool (interactive): https://www2.gov.bc.ca/gov/content/environment/air-land-water/land/soil/soil-information-finder
- BC Detailed Soil Survey (open data): https://open.canada.ca/data/en/dataset/adf4d26a-9fc0-44c9-ba38-620531ca0dbe
- Store drainage class, texture, organic matter class in `location.soil` with source URL. For the hackathon, the two presets are filled by hand from the handbook/finder; user-drawn fields show "soil: enter from Soil Information Finder".

#### B2.10 Optional (only if B2.1–B2.9 are cached by Saturday noon)

- GLDAS_NOAH025_3H soil moisture (Data Rods) as a second soil-moisture opinion.
- ECOSTRESS ET (ECO_L3T_ET_ALEXI.002, 70 m, via AppEEARS, V listed) for one or two summer dates as an illustration of field-scale ET; not for scoring.
- GRACE/GRACE-FO groundwater anomaly for the Interior as a long-term water trend sparkline (coarse, ~300 km; label accordingly).

#### B2.11 Common grid / time step

- Daily master table per preset: `daily.parquet` with columns from B2.1, B2.2, B2.3, B2.7 joined on date, plus `ndvi_interp`, `cover_class` from B5, plus `risk_rain`, `risk_frost`, `risk_heat`, `risk_dry` booleans.
- Spatial: do **not** resample coarse grids down to 10 m (it invents information). Instead, per dataset store `footprint_area_m2` and compute `scale_ratio = footprint_area / field_area` (B6.2). Fine rasters are reduced to field statistics. This satisfies "harmonise to a common analysis grid" with the field as the grid cell, and the UI says so.

### B3. Shared JSON schemas

Every numeric leaf is a `SourcedNumber`. Agents must not emit bare numbers.

```json
// SourcedNumber
{
  "value": 0.95,
  "unit": "Kc",
  "low": 0.90,
  "high": 1.05,
  "method": "lookup | computed | assumed",
  "source": {
    "id": "fao56_table12",
    "title": "FAO-56 Table 12, Alfalfa hay, averaged cutting effects, Kc mid",
    "url": "https://www.fao.org/4/x0490e/x0490e0b.htm",
    "accessed": "2026-11-14",
    "verified": true
  },
  "note": "Subhumid-climate value; adjust for RHmin/wind per FAO-56 eq. 62 if time allows"
}
```

```json
// Location (one per preset or user field)
{
  "id": "fv_sumas_dairy",
  "name": "Sumas Prairie dairy field (example)",
  "regime": "wet | drought",
  "geometry": { "type": "Polygon", "coordinates": [[[-122.1725, 49.0585], ...]] },
  "centroid": { "lon": -122.17, "lat": 49.06 },
  "area_ha": { "value": 12.0, "unit": "ha", "method": "computed", "source": {"id": "geometry"} },
  "crs_working": "EPSG:32610",
  "soil": {
    "management_group": "Sumas",
    "drainage_class": "very poorly drained",
    "texture": "lacustrine silty clay (U)",
    "organic_matter_class": null,
    "source": { "id": "bc_fv_soil_handbook", "url": "https://www.env.gov.bc.ca/esd/distdata/ecosystems/Soils_Reports/Docs/soil_mgmt_hbk_fraservalley.pdf", "verified": true }
  },
  "terrain": { "slope_mean_pct": {...SourcedNumber}, "slope_p90_pct": {...}, "elev_m": {...} },
  "irrigation": { "available": false, "licence_m3_per_yr": null, "system": null },
  "stations": [ { "name": "Abbotsford A", "station_id": 50308, "distance_km": 14.2, "years": [2011, 2026] } ],
  "datasets": {
    "power":  { "cache": "data/cache/fv_sumas_dairy/power_daily.parquet",  "footprint_area_m2": 2.0e9, "native_res_m": 55000, "timestep": "daily", "period": ["1981-01-01","2025-12-31"] },
    "imerg":  { "cache": "...imerg_daily.parquet",  "footprint_area_m2": 8.0e7, "native_res_m": 10000, "timestep": "daily", "period": ["2015-01-01","2025-12-31"] },
    "smap":   { "cache": "...smap_daily.parquet",   "footprint_area_m2": 8.1e7, "native_res_m": 9000,  "timestep": "daily", "period": ["2015-03-31","2025-12-31"] },
    "s2":     { "cache": "...s2_scenes.parquet",    "footprint_area_m2": 100,   "native_res_m": 10,    "timestep": "~5 day", "period": ["2017-01-01","2025-12-31"] },
    "landsat":{ "cache": "...landsat_scenes.parquet","footprint_area_m2": 900,  "native_res_m": 30,    "timestep": "~8-16 day", "period": ["2013-04-01","2025-12-31"] },
    "dem":    { "cache": "...dem_field.tif", "native_res_m": 30 },
    "eccc":   { "cache": "...eccc_daily.parquet", "station_id": 50308 },
    "aci":    { "cache": "...aci_history.json", "classes_by_year": { "2019": "Corn", "2020": "Corn" } }
  },
  "observed_cover": {
    "typically_bare_doy_ranges": [[290, 110]],
    "bare_fraction_by_doy": "data/cache/fv_sumas_dairy/bare_doy.json",
    "years_used": [2019, 2020, 2021, 2022, 2023, 2024, 2025]
  }
}
```

```json
// Crop (one per species; data from BC factsheets + FAO-56)
{
  "id": "fall_rye",
  "name": "Fall rye",
  "type": "winter cereal cover/forage",
  "legume": false,
  "kc": { "ini": {...SourcedNumber 0.4 fao56 winter wheat proxy, method assumed}, "mid": {...1.15}, "end": {...0.25-0.4} },
  "stage_lengths_days": { "ini": 30, "dev": 60, "mid": 60, "late": 30, "source": "fao56_table11 winter wheat proxy (U)" },
  "cover_by_stage": { "ini": 0.2, "dev": 0.6, "mid": 1.0, "late": 0.8 },
  "ratings_0_4": {
    "erosion_reduction": {...SourcedNumber from factsheet bar},
    "soil_builder": {...}, "lasting_residue": {...}, "nitrogen_fixation": {"value": 0, ...},
    "nitrogen_scavenging": {...}, "forage_harvest_value": {...}, "weed_suppression": {...},
    "tolerance_flood": {...}, "tolerance_drought": {...}
  },
  "dry_matter_yield_kg_ha": { "value": 7000, "low": 3360, "high": 10800, "source": {"id": "bc_factsheet_fall_rye", "verified": true} },
  "drainage_classes_ok": ["very well", "well", "moderately well", "somewhat poor", "poorly"],
  "seeding_window": { "start": "09-01", "end": "10-15", "best": "late September", "source": "bc_factsheet_fall_rye (text)", "verified": true },
  "termination": "stem elongation (spring)",
  "cautions": ["ergot risk", "allelopathy to following alfalfa", "N immobilisation if large biomass incorporated", "uses significant spring moisture"],
  "sources": [ { "id": "bc_factsheet_fall_rye", "url": "https://www2.gov.bc.ca/assets/gov/.../fall_rye_final.pdf" } ]
}
```

```json
// RotationStrategy
{
  "id": "fv1_corn_fallrye",
  "location_id": "fv_sumas_dairy",
  "name": "Silage corn + fall rye winter cover",
  "is_baseline": false,
  "cycle_years": 1,
  "calendar": [
    { "year": 1, "crop_id": "silage_corn", "plant": "05-05", "harvest": "09-28", "role": "cash", "timing_source": "assumed (U)" },
    { "year": 1, "crop_id": "fall_rye", "plant": "09-30", "terminate": "04-15", "role": "cover", "timing_source": "bc_factsheet_fall_rye late-Sept (V)" }
  ],
  "modelled_cover_by_doy": "computed from calendar + cover_by_stage",
  "exposure": {
    "bare_days_per_year": {...SourcedNumber},
    "exposed_rain_days": {...}, "exposed_frost_days": {...}, "exposed_heat_days": {...}, "exposed_dry_days": {...},
    "replay": { "2021": { "exposed_rain_days": {...} }, "2023": { "exposed_dry_days": {...} } }
  },
  "water": { "etc_mm_season": {...}, "irrigation_need_mm": {...} },
  "scores": {
    "water_use": { "value": 62, "low": 51, "high": 70, "method": "computed", "source": {"id": "scoring_v1"} },
    "forage_value": {...}, "n_fixation": {...}, "erosion": {...}, "organic_matter": {...}, "market": {...}
  },
  "composite": { "value": 58, "low": 47, "high": 66, "weights_used": {"water_use": 0.1, "erosion": 0.3, ...} },
  "brief": {
    "why": "…",
    "evidence": [ { "text": "Field read as bare 15 Oct–25 Apr in 6 of 7 years (Sentinel-2)", "source_ids": ["s2"] }, ... ],
    "benefits": [ { "priority": "erosion", "text": "...", "source_ids": [...] } ],
    "gaps": [ "No tile-drainage data", "Yield and cost not modelled", "SMAP pixel is 81 km²; field is 0.12 km²" ],
    "local_review": [ { "item": "Confirm corn harvest date allows late-Sept rye seeding", "severity": "high" }, ... ]
  },
  "uncertainty": { "dataset_disagreement": {...}, "scale": {...}, "agronomic_gap_count": 3 }
}
```

API contract (lock in hour 1): `GET /api/locations`, `GET /api/locations/{id}` (Location), `GET /api/locations/{id}/daily?from&to` (daily table), `GET /api/locations/{id}/strategies` (array of RotationStrategy with scores at default weights), `POST /api/locations/{id}/score` body `{weights, constraints, replay_year?}` returns the strategies re-scored. The frontend can be built against `fixtures/*.json` that match these schemas from hour 2.

### B4. Scoring model

Principle: every score is 0–100 with low/high; the baseline is the reference; "rule of thumb, not a model" is printed under every score. Ratings from BC factsheets use the factsheets' own 5-step bars (Not effective → Very effective) coded 0–4.

#### B4.1 Water use

- Reference ET: `ETo_d` daily (Hargreaves from POWER; B2.1). Climatology mean per day-of-year over 1991–2020 plus the replay year's actual.
- Crop ET per strategy: `ETc = Σ_d Kc(d) × ETo_d` where Kc(d) is the FAO-56 single-coefficient curve built from `kc.ini/mid/end` and `stage_lengths_days`, anchored on the calendar's plant/harvest dates (FAO-56 ch. 6: https://www.fao.org/4/x0490e/x0490e0b.htm ). Bare periods: Kc = 0.15 (U: FAO-56 bare-soil Kc ini order of magnitude; mark assumed) so that bare winter still evaporates a little.
- Verified FAO-56 Table 12 values (subhumid climate, RHmin≈45%, u2≈2 m/s) (V):
  - Alfalfa hay, averaged cutting effects: Kc ini 0.40, mid 0.95, end 0.90
  - Grazing pasture, rotated grazing: 0.40 / 0.85–1.05 / 0.85
  - Rye grass hay, averaged cutting effects: 0.95 / 1.05 / 1.00
  - Clover hay (berseem), averaged cutting effects: 0.40 / 0.90 / 0.85
  - Winter wheat with frozen soils: 0.40 / 1.15 / 0.25–0.4
  - Barley, oats, spring wheat: mid 1.15, end 0.25 (Kc ini 0.3, U: column not captured in research; read Table 12)
  - Maize, field (grain): mid 1.20, end 0.60–0.35 (Kc ini 0.3, U; silage corn is harvested before the end stage, so use Kc end ≈ 1.0 at silage harvest, U, and say so)
  - Fall rye and winter triticale: not in Table 12 → use winter-wheat values, `method: assumed`, widen range ±0.1.
  - Sainfoin: not in Table 12 → use alfalfa values, `method: assumed`, widen ±0.1.
  - FAO-56 growing-season rule for alfalfa in frost climates: last −4 °C in spring to first −4 °C in fall (V, Table 11 footnote). Use POWER T2M_MIN to set these dates per year.
- Irrigation need (drought preset): `I = Σ_season max(0, ETc_d − 0.8 × P_d)` with P from IMERG (and recomputed with ECCC and POWER for the range). Effective-rain factor 0.8 is U/assumed.
- Score: `water_use = 100 × clamp(1 − I_strategy / I_max, 0, 1)` where `I_max` is the largest I among the four strategies (so the thirstiest scores 0, and a rain-fed field that needs nothing scores 100). For the wet preset where no irrigation is used, score on ETc instead and label "water demand (not irrigated)".
- Range: recompute with Kc low/high, ETo ±15% (Hargreaves vs PM typical spread, U), and each of the three precipitation sources → take min/max.

#### B4.2 Forage value

- `forage_value = 100 × Σ_crops (rating_forage_0_4 / 4 × harvestable_months_share × DM_yield_norm)` summed over the cycle, divided by cycle years. `DM_yield_norm = DM / 10,000 kg/ha` capped at 1.
- Ratings and DM from BC factsheets (V, all at https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/agricultural-land-and-environment/soil-nutrients/management/cover-crops ): fall rye DM 3,360–10,800 kg/ha, "Forage Harvest Value" bar; annual ryegrass "commonly grown as a forage crop"; winter wheat "excellent quality forage"; winter triticale; spring barley; winter barley; field peas; hairy vetch; red clover; sainfoin from the BF04 non-bloat legume factsheet. Alfalfa and silage corn: cash forage, rating 4 by definition (U: not a cover-crop factsheet), DM U → use range 8,000–14,000 kg/ha alfalfa hay and silage corn 15,000–20,000 kg DM/ha (U, mark "regional typical, unverified").
- Range: ±1 rating step and DM low/high.

#### B4.3 Nitrogen fixation

- `n_fixation = 100 × Σ_crops (legume ? rating_nfix_0_4 / 4 × months_growing / 12 : 0) / cycle_years`.
- Hairy vetch "can fix the highest quantity of nitrogen" among the listed legumes; red clover "capable of fixing ample nitrogen"; alsike, crimson, white, sweet clover, field peas, common vetch, sainfoin are legumes (V, BC factsheets). Cereals 0. Penalty note (not a score change): fall rye immobilises N if a large biomass is incorporated; terminate at stem elongation (V).
- Alfalfa: rating 4 (U: perennial legume, not a factsheet). Range ±1 step.

#### B4.4 Erosion reduction

- Exposure-based, from NASA data: `E = Σ_d cover_deficit(d) × rain_risk(d) × slope_factor` where `cover_deficit = 1 − modelled_cover(d)`, `rain_risk(d) = 1` if IMERG ≥ threshold (B5.3) else 0, `slope_factor = 1 + slope_mean_pct/5` (U: simple monotone proxy, not RUSLE; say so).
- `erosion = 100 × (1 − E_strategy / E_baseline)` clamped 0–100 (baseline scores 0; a strategy that removes all exposed rain-days scores 100). Blend 70% exposure + 30% factsheet "Erosion Reduction" rating of the cover crop (V ratings) so that a crop's known residue quality counts.
- Range: thresholds 25–50 mm; three precipitation sources; cover curve ±20%.

#### B4.5 Organic matter improvement

- `organic_matter = 100 × [0.5 × mean(rating_soil_builder, rating_lasting_residue)/4 + 0.3 × perennial_years/cycle_years + 0.2 × (1 − bare_days/365)]`.
- Ratings from factsheets (V). Range ±1 rating step.

#### B4.6 Market suitability

- Not computable from satellites. Score from a small table + user inputs: on-farm use (dairy herd → silage/relay feed scores high; beef → hay/greenfeed), local hay market present (Interior yes, U), equipment available (drill, pivot), seed cost class (U). `market = 100 × mean(flags)`, range ±25 fixed, and **always** emits a local_review item "Market/feed fit: confirm with buyer or nutritionist".

#### B4.7 Weighting and ranges

- Sliders w_i ∈ [0, 4]; normalise `W_i = w_i / Σ w`. If all zero, equal weights.
- `composite = Σ W_i × score_i`; `composite_low = Σ W_i × low_i`; `composite_high = Σ W_i × high_i`.
- Ranking rule: sort by composite, but if two strategies' [low, high] intervals overlap by more than 50% of the smaller interval, display them as "tie within uncertainty" and do not show a numeric rank between them.
- Monte Carlo alternative (if time): N = 200 draws of Kc, thresholds, ETo factor, rating ±1 → report p10/p90 as low/high. Deterministic min/max is acceptable for the demo.

### B5. Bare-field detection and risk windows

#### B5.1 Per-scene field cover (Sentinel-2)

1. For each scene intersecting the field: read B04, B08, SCL windowed to the polygon.
2. Valid pixel mask: SCL ∈ {4 vegetation, 5 not-vegetated, 6 water (keep but flag), 7 unclassified} and not in {3 cloud shadow, 8 cloud medium, 9 cloud high, 10 thin cirrus, 11 snow/ice} (U: standard SCL legend; confirm in the collection metadata). Drop the scene if valid fraction < 0.5.
3. NDVI = (B08 − B04) / (B08 + B04) per valid pixel; store field median, p10, p90.
4. Cover class per scene: `bare` if median NDVI < 0.20; `partial` if 0.20–0.35; `covered` if > 0.35. Thresholds: bare soil/rock typically ≤ 0.1–0.2, sparse vegetation 0.2–0.5 (U: common remote-sensing rule of thumb; cite USGS NDVI explainer https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology and treat the 0.20 threshold as a tunable parameter 0.15–0.30 for the range).
5. Snow: SCL 11 scenes are "unknown, snow" and are excluded from bare statistics but drawn as a snow tick on the calendar.

#### B5.2 Time series → calendar

- Interpolate median NDVI linearly between valid scenes if the gap ≤ 30 days; otherwise mark `unknown`. Fraser Valley winters will have long cloudy gaps: show them as hatched "no clear view" rather than guessing.
- For each day-of-year, `bare_fraction(doy) = bare_years / known_years` over 2019–2025. "Typically bare" = bare_fraction ≥ 0.5 with known_years ≥ 3.
- Observed baseline calendar vs the modelled baseline (from the calendar in B1): print the agreement (% of days where modelled cover class equals observed) on the validation panel. If it is below 60%, the preset calendar dates are wrong; fix the preset, not the satellite.
- Landsat: same logic with QA_PIXEL and 30 m, used to extend to 2013+ and shown as a thinner strip.

#### B5.3 Risk days (regional data)

| Risk | Rule | Source for rule | Data |
|---|---|---|---|
| Extreme rain | daily P ≥ 50 mm (coast) / ≥ 25 mm (interior); also 3-day ≥ 75 mm | U: ECCC rainfall-warning thresholds for BC are of this order; verify at https://www.canada.ca/en/environment-climate-change/services/types-weather-forecasts-use/public/criteria-alerts.html . Also compute a data-driven threshold: 95th percentile of wet days at the field | IMERG; ECCC; POWER PRECTOTCORR |
| Frost | T2M_MIN ≤ 0 °C (light), ≤ −4 °C (killing; FAO-56 alfalfa season bounds) | V for −4 °C (FAO-56 Table 11 footnote) | POWER; ECCC |
| Heat | T2M_MAX ≥ 30 °C (stress), ≥ 35 °C (severe; FAO-56 notes long periods > 35 °C can send grass dormant) | V for 35 °C text; 30 °C U | POWER; ECCC |
| Dry spell | SMAP AM soil moisture below the 20th percentile of the same calendar month over 2015–2025 for ≥ 14 consecutive valid days; or IMERG 30-day total < 50% of climatology | U: SPI/percentile-style convention; label as our definition | SMAP; IMERG |

#### B5.4 Exposure overlay

- `exposed_<risk>_days(strategy, year) = Σ_d [modelled_cover(d) < 0.5] × risk_<risk>(d)`.
- Baseline uses the *observed* cover where known and the modelled where unknown; alternatives use modelled cover (they do not exist yet). Say this on screen: "baseline: observed; alternatives: modelled from calendar".
- Replay years: 2021 (Nov atmospheric river), 2023 (Level 5 drought), 2024 (Jan cold snap / Feb) (U: choose after looking at the data).

### B6. Uncertainty: concrete computations

#### B6.1 Dataset disagreement

- Precipitation: monthly totals from IMERG, POWER PRECTOTCORR, ECCC station. `rel_diff = |A − B| / mean(A, B)`. Badge "sources disagree" on any month where max pairwise rel_diff > 0.25. Event-level: count extreme-rain days per source; show the min–max as the range on the calendar ("8–13 heavy-rain days in the bare window").
- Temperature: POWER T2M_MIN vs station Tmin daily: report bias and RMSE; frost-day counts per source → range.
- Soil moisture: SMAP L3 vs (optional) SPL4/GLDAS vs a simple POWER bucket model (`S_{d+1} = S_d + P − ETc`, capacity from soil texture, U). Report the fraction of days where anomaly signs agree; badge if < 0.7.
- Everything above goes into `uncertainty.dataset_disagreement` with the numbers, and the widened ranges feed B4.

#### B6.2 Scale mismatch

- `scale_ratio = footprint_area_m2 / field_area_m2`. For a 12 ha field: Sentinel-2 10 m → 0.0008 ("field-scale: 1,200 pixels in the field"); Landsat 30 m → 0.0075; IMERG ~80 km² → ~670 ("the rain pixel is 670 fields"); SMAP 81 km² → 675; POWER ~2,000 km² at 49°N (0.5° × 0.625° ≈ 55 × 45 km) → ~17,000.
- Badge classes: ratio ≤ 1 "field-scale"; 1–100 "neighbourhood"; 100–1,000 "sub-regional"; > 1,000 "regional". Draw the footprint polygons over the field on the map (twist 4). Any score that depends only on regional data carries the badge of its coarsest input.

#### B6.3 Agronomic gaps

- Every Crop attribute has `method ∈ {lookup, computed, assumed}` and `source.verified`. For each strategy count `n_assumed` and `n_unverified`; list them verbatim in `brief.gaps` ("Kc for fall rye assumed = winter wheat (FAO-56)").
- Standing gaps that are always printed: no yield model; no price/cost; no tile drainage or water-table data; no pest/disease model; soil properties from survey polygons, not a soil test; satellite cannot see under snow or cloud; SMAP sees the top ~5 cm.
- Severity for `local_review`: high = timing conflicts (seeding window vs harvest date), drainage-class mismatch (crop `drainage_classes_ok` vs location drainage), irrigation licence exceeded; medium = winterkill risk for species noted as marginal (Italian ryegrass), allelopathy/ergot cautions; low = market/equipment.

### B7. UI flow and the rotation brief

Users: farmer and agrologist side by side on a laptop; occasionally a phone. Plain language, units with conversions (mm and inches; ha and acres), every acronym has a tooltip, no dataset names in headlines (say "satellite rainfall" with "GPM IMERG" in the tooltip).

Screens:
1. **Pick a field.** Two preset cards (photo-free, one line each: "Sumas Prairie dairy, wet winters" / "Kamloops hay under pivot, dry summers"), map with the polygon; "draw your own" (works with POWER + Sentinel-2 only, with a note that IMERG/SMAP need the cache). Footprint toggle shows the SMAP/IMERG/POWER pixels over the field.
2. **Your field's year.** Bare-field calendar: one row per year 2019–2025 (hatched = no clear view, brown = bare, light green = partial, green = covered) with the risk ticks above (blue drops = heavy rain, snowflake = frost, sun = heat, cracked = dry). Below: "typically bare" band and the observed crop history from AAFC. Right rail: "what this is built from" with the scale badges.
3. **Priorities.** Six sliders (water use, forage value, nitrogen fixation, erosion, organic matter, market) 0–4 with plain labels; constraints: irrigation available (y/n, licence m³), livestock on farm (dairy/beef/none), drill available, "no new perennials". Live preview of composite ranking.
4. **Compare.** Four columns: baseline + 3. Top: exposure rings (twist 1) with the headline "exposed heavy-rain days" / "irrigation need (mm)" depending on regime. Middle: six score bars with range whiskers and the tie badge. Bottom: Replay toggle (2021 / 2023). Button "Open brief" per column.
5. **Rotation brief** (card, printable A4):
   - Header: strategy name, field, regime, date, "Example data / rule of thumb, not a model".
   - Calendar strip for the cycle (crop-by-month).
   - **Why suggested** (2–3 sentences, templated from priorities and exposure).
   - **Evidence**: 3–6 bullet facts, each with a source chip (satellite / station / factsheet / FAO-56) and a scale badge; e.g. "Bare 15 Oct–25 Apr in 6 of 7 years (Sentinel-2, field-scale)".
   - **Benefits by priority**: six rows, score with range, one-line reason.
   - **Gaps**: the generated list from B6.3.
   - **Needs local review**: checklist with severity and tick boxes.
   - Footer: sources list with URLs; "Satellite data: NASA POWER, GPM IMERG, SMAP, Landsat; ESA Sentinel-2".
6. **Satellite vs ground.** Validation panel (B8.1) as a user-visible page, not hidden: monthly rain bars for IMERG / station / POWER, the Nov 2021 event, the 2023 soil-moisture anomaly, and the observed-vs-modelled baseline cover agreement.

### B8. Validation, demo, workstreams

#### B8.1 Validation checks (run before anyone pitches)

1. Coordinates: every API call logs lon,lat order; POWER wants longitude then latitude params by name; STAC/GeoJSON are [lon, lat]. Plot the field on a basemap and confirm it is on farmland.
2. Units: POWER precipitation mm/day, temperatures °C; IMERG mm/day; SMAP m³/m³ (0.05–0.5 plausible); ECCC mm and °C; NDVI −1..1. Assert plausible ranges on load.
3. Rain: monthly IMERG vs Abbotsford A 50308 and Kamloops A 51423 totals for 2015–2025; expect agreement within ~25% in most months; Interior convective months may be worse. Record bias.
4. Event: 13–15 Nov 2021 must appear as a top-3 multi-day total in all three precipitation sources for the FV preset (station totals of order 100–200 mm over two days reported; U: verify from ECCC).
5. Drought: SMAP AM soil moisture July–Aug 2023 at KT below the 2015–2025 same-month median; POWER PRECTOTCORR May–Aug 2023 below climatology.
6. Cover: observed baseline cover class vs modelled calendar agreement ≥ 60%; AAFC class history consistent with the preset crop in ≥ 4 of the last 6 years.
7. Scores: baseline erosion score is 0 by construction; a strategy with full-year cover must have exposed_rain_days ≈ 0; alfalfa ETc must exceed winter-cereal ETc in June–August at KT.
8. Sources: every SourcedNumber in the fixtures has a URL; count of `verified: false` is printed on the brief.

#### B8.2 Demo script (3 min local pitch) and submission deliverables

- 0:00 Farmer story (20 s): "In November 2021 Maria's back field was bare. So was almost every corn field on Sumas Prairie." One sentence on Jake and summer 2023.
- 0:20 Problem (20 s): bare field + water extreme = lost soil, lost nitrogen, lost water. Show the calendar screen for FV with the 2021 ticks landing on brown.
- 0:40 Live demo (1:50): set priorities, compare, show the tie badge and ranges, open one brief, flip to the Satellite vs ground page for ten seconds ("here is what the satellite can't see"), switch to KT and show irrigation-need bars and the 2023 replay.
- 2:30 Close (30 s): "Supports the farmer and agrologist, doesn't replace them. Every number has a source. Built on NASA POWER, IMERG, SMAP and Landsat, with Sentinel-2 and BC's own factsheets."
- Submission (V, judging guide): 7 slides max **or** a 30-second video with English subtitles; both are allowed to exist but one is the official demo. Slides: 1 title; 2 problem with the two BC events; 3 what the tool does (calendar screenshot); 4 compare screen with ranges; 5 brief card; 6 data and scale badges + validation chart; 7 limits and next steps. All external code, data and images go in the References field.

#### B8.3 Six-person workstream split and first-hour contracts

| # | Owner | Saturday deliverable | Sunday deliverable |
|---|---|---|---|
| 1 Regional data | POWER + IMERG + SMAP + ECCC cached for both presets as parquet with meta.json; ETo computed | disagreement metrics (B6.1), replay-year extracts |
| 2 Field data | Sentinel-2 + Landsat scene table, NDVI, cover classes, bare_doy.json; NASADEM slope; AAFC history | observed-vs-modelled agreement; calendar PNG export |
| 3 Rotation engine | crops.json from factsheets (ratings, Kc, windows, cautions, URLs), 8 strategies, scoring v1 with ranges, brief text generator | Monte Carlo ranges, local_review rules, API |
| 4 Frontend | screens 1–4 against fixtures | screens 5–6, print CSS, polish, phone width |
| 5 Validation + integration | repo, schemas, fixtures, CI check that every number has a source; runs B8.1 as scripts | fixes units/dates; owns the demo laptop and the offline cache |
| 6 Story + submission | farmer story, 7 slides, 30-s video storyboard, project page text | records video, rehearses pitch 3×, submits before 11:59 pm |

First-hour contracts (nothing else starts until these are committed):
1. `schemas/*.json` for SourcedNumber, Location, Crop, RotationStrategy (B3) and the API routes.
2. Preset IDs `fv_sumas_dairy`, `kt_thompson_hay`; polygons committed as GeoJSON; working CRS EPSG:32610.
3. Cache paths (B2) and `meta.json` fields; fixture files `fixtures/fv_sumas_dairy.location.json`, `fixtures/*.strategies.json` with fake-but-schema-valid data so #4 can start immediately.
4. Earthdata login created, GES DISC and AppEEARS authorised, `.netrc` on the data laptop; MPC/Earth Search confirmed reachable from the venue Wi-Fi.
5. Definition of done for a number: value, unit, low, high, method, source URL. A pre-commit script fails if any numeric leaf under `scores`, `kc`, `ratings_0_4` lacks `source.url`.
6. Merge cadence: every 3 hours into `main`; feature freeze Saturday 22:00; Sunday is validation, polish, video, pitch.

### B9. What the data cannot support (print this in the app's "Limits" page)

- SMAP, IMERG and POWER cannot say anything about one field versus its neighbour; they say which weeks and years were wet, dry, cold or hot across the valley.
- Sentinel-2 sees cover, not soil loss, infiltration, nitrate or tile drains; winter cloud leaves gaps of weeks.
- Scores are rule-of-thumb composites of factsheet ratings and FAO-56 coefficients; they are not yield, profit or a validated agronomic model, and Kc for fall rye, triticale and sainfoin are borrowed from related crops.
- The flood of 2021 was a dike failure; no rotation prevents that. The tool addresses bare-ground exposure to heavy rain, not flood protection.
- Calendars for the presets are typical, not measured on a real farm; the two presets are examples.
- Every alternative rotation needs review by the farmer and an agrologist before anything is seeded. That sentence is on every brief.
