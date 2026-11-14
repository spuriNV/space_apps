# Field Shift: Research Findings

Combined results of three research agents, 2026-11-14. Read alongside `field-shift-plan.md` (overall plan) and `planner-spec.md` (detailed build spec).

**Legend:**
- ✓ = endpoint tested and returned a live response.
- (verified) = existence confirmed by web search only.
- (unverified) = not confirmed. Check before relying on it.

---

## 1. Problem to target

### Recommended: BC forage farmers cut off from irrigation mid-summer
- **Who:** a Shuswap (Salmon River) or Cowichan (Koksilah) dairy or cattle operator.
- **Decision:** in March or April, how much land to put into irrigated alfalfa or hay versus a drought-tolerant or early-harvest mix.
- **Information gap:** the order to stop irrigating arrives mid-summer, with no warning at the level of one field.
- **What happened in 2023:**
  - About 398 licence holders on the Salmon River/Bessette Creek and about 108 on the Koksilah were ordered to stop irrigating forage.
  - Vegetables and livestock watering were exempt.
  - Hay went from $75 to $190 a bale, and some ranchers considered selling their herds.
- **What NASA data adds:** SMAP soil moisture, GRACE-FO groundwater and HLS vegetation index in spring, compared with the same signals in past cut-off years.
- **Sources:**
  - https://news.gov.bc.ca/releases/2023FOR0052-001305 (16 Aug 2023 Salmon River/Bessette Creek order). Correction: 2023FOR0059-001512, cited here earlier, is the 27 Sept 2023 bulletin rescinding the Koksilah and Tsolum orders.
  - https://www.countrylifeinbc.com/water-curtailments-squeeze-forage-production/
  - https://globalnews.ca/news/9834742/bc-farmers-drought-impacts-summer-2023
  - https://amp.cbc.ca/lite/story/1.6907515

### Second preset (wet extreme): Fraser Valley and Sumas Prairie atmospheric rivers
- **Decision:** which October cover crop or fall-seeded rotation to plant before atmospheric-river season.
- **What happened in November 2021:** about 628,000 poultry, 420 dairy cattle and about 12,000 hogs were killed. 420 is the official cattle tally; some sources say about 500.
- **What NASA data adds:** IMERG rainfall and SMAP saturation for November 2021, overlaid on the fields.
- **Source:** https://www.canadianpoultrymag.com/catastrophic-floods-hit-b-c/
- Don't pitch this as flood prevention. The 2021 flood came from a dyke failure.

### Backup problem: nitrate leaching into the Abbotsford aquifer
71% of 2,757 well samples exceeded the 10 mg/L nitrate-N guideline. Fall rain timing plus soil saturation shows when leaching risk peaks.

### Why a Google search fails
- Orders, drought levels and prices are spread across dozens of separate releases.
- Coverage is regional, not tied to one field.
- Reports come after the event, never at planting time.
- Nothing weighs trade-offs, such as alfalfa yield against cut-off risk.

### Pitch hook (verify the 398 count against the BC release first)
> "In summer 2023, BC ordered about 398 Shuswap licence holders to stop irrigating forage mid-season, and hay went from $75 to $190 a bale. We show farmers in spring what NASA's satellites showed before those orders, so they can pick a rotation that survives the order."

The satellite lead time ("SMAP dropped below normal X days before the order") is **not computed yet**. Calculate it from real SMAP data before saying it.

---

## 2. Region choice: BC presets plus one California data showcase

**Recommendation:**
- Lead the demo with BC; that's the local hook.
- Add one data-rich California preset (Sacramento Valley or San Joaquin) as "the ceiling with rich ground truth".
- Present BC as "how it works where ground data is sparse, as in most of the world, on NASA data alone."
- Build one pipeline: NASA global layers everywhere, plus a regional adapter for each area's ground data.

**What the California preset adds that BC can't:**
1. Checking the model against measured field-level water use (OpenET), not just modelled values.
2. Rotation rules driven by field-scale soil water capacity and drainage class.
3. More than 15 years of field-level crop history (CDL) showing which rotations happened in drought versus wet years.
4. Groundwater limits from GRACE plus state well data.
5. Showing the tool still works, with less detail, where data is thinner. That makes it believable worldwide, which global judges value.

**Which California valley:**
- **Sacramento Valley (rice):** clearest back-to-back extremes. The 2021–22 drought fallowed about half the rice, visible in CDL, then the 2023 floods hit, visible in OPERA DSWx and river gauges.
- **San Joaquin:** more crop variety, plus the 2023 refilling of Tulare Lake.

---

## 3. Data sources

### NASA (global, same everywhere)
| Dataset | Access | Notes |
|---|---|---|
| POWER daily ag weather (0.5°) | `https://power.larc.nasa.gov/api/temporal/daily/point?...&community=AG` ✓ | No auth |
| SMAP L3 9 km / L4 root zone | SPL3SMP_E, SPL4SMGP via CMR ✓ | Earthdata login |
| IMERG daily rain (0.1°) | GPM_3IMERGDF ✓ | Earthdata login |
| HLS Landsat/Sentinel (30 m) | HLSL30 ✓ | Bare-field detection |
| ECOSTRESS evapotranspiration (70 m) | ECO_L3T_JET ✓ | Earthdata login |
| GRACE-DA groundwater (0.25°, weekly) | GRACEDADM_CLSM025GL_7D ✓ | Earthdata login |
| SRTM elevation (30 m) | SRTMGL1 ✓ | Slope, erosion risk |
| OPERA DSWx surface water (30 m) | via CMR ✓ | Flood mapping |
| AppEEARS point and area subsetting | `https://appeears.earthdatacloud.nasa.gov/api/` ✓ | **Easiest route for a hackathon** |
| CMR search | `https://cmr.earthdata.nasa.gov/search/collections.json?short_name=...` ✓ | |

Downloads need a free NASA Earthdata Login. Create accounts in the first hour.

### California ground data
| Source | Access | Auth |
|---|---|---|
| OpenET field water use (30 m, monthly) | `https://openet-api.org/raster/timeseries/point` ✓ | Free key |
| USDA Soil Data Access (SSURGO, SQL) | `https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest` ✓ | None |
| Cropland Data Layer | CroplandCROS ✓ or GeoTIFF download; CropScape API (unverified, unreliable) | None |
| CIMIS weather stations and reference ET | `https://et.water.ca.gov/api/data?appKey=` ✓ | Free key |
| CDEC reservoirs and rivers | `https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet` ✓ | None |
| DWR groundwater levels | `https://data.cnra.ca.gov/api/3/action/package_search` ✓ | None |
| USGS water data | `https://api.waterdata.usgs.gov/ogcapi/v0/collections/field-measurements` ✓ | None |
| NOAA station data | `https://www.ncei.noaa.gov/access/services/data/v1` ✓ | None |
| PRISM climate (800 m–4 km) | `prism.oregonstate.edu/fetchData.php` ✓ (file downloads) | None |

### BC ground data
| Source | Access | Notes |
|---|---|---|
| AAFC Annual Crop Inventory (30 m) | `https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/data_donnees/tif/` ✓ | GeoTIFF |
| AAFC Crop Rotations product | `.../cropRotation/data_donnees/tif/` ✓ | Fits the planner directly |
| Environment Canada climate and river data | `https://api.weather.gc.ca/collections/...` ✓ | Fraser station 08MH024 worked |
| BC Data Catalogue (groundwater wells, soil survey) | `https://catalogue.data.gov.bc.ca/api/3/` ✓ | |
| BC map services | `openmaps.gov.bc.ca/geo/pub/wfs` ✓ | |
| SoilGrids (250 m, global) | `https://rest.isric.org/soilgrids/v2.0/properties/query` ✓ | **Practical BC soil source** |
| CanSIS soil landscapes | `https://sis.agr.gc.ca/cansis/` ✓ | Coarse; no query API |
| BC drought levels | `https://droughtportal.gov.bc.ca` (verified) | Website only, no API |

**BC gaps:**
- No OpenET, so no field-level water use.
- No field-scale soil API.
- No dense agricultural weather network like California's CIMIS.

### Planting decision data (non-NASA), top 8 by value for effort
1. **Open-Meteo:** forecast, historical and seasonal outlook; no key (verified). Used for growing degree days, frost dates, evapotranspiration and seasonal risk.
2. **FAO-56 crop coefficients:** static tables entered by hand into a CSV of about 30 crops. Water need = coefficient × reference evapotranspiration.
   - https://www.fao.org/3/x0490e/x0490e0b.htm (unverified)
3. **USDA NASS Quick Stats:** free key (verified). Yields, prices and acreage for market suitability.
4. **US Drought Monitor:** no key (verified). Current and historical drought by county.
5. **Statistics Canada table 32-10-0359-01:** BC crop area, yield and price. The table is verified; the endpoint pattern is unverified.
6. **NOAA seasonal outlooks:** ArcGIS REST, no key (verified). Odds of above- or below-normal rain, e.g. "wet winter likely, pick a cover crop."
7. **CIMIS:** California reference ET (see above).
8. **USDA PLANTS traits:** drought tolerance, waterlogging tolerance, nitrogen fixing and root depth (unverified).

**Also useful:**
- **USDA crop-insurance loss records (RMA):** county history of losses by crop from drought or excess moisture. A strong, real-history risk score (verified).
  - https://www.rma.usda.gov/tools-reports/summary-business/cause-loss
- **Cover-crop funding:**
  - USDA EQIP practice 340 pays per acre (state PDFs).
  - BC's IAF Climate Agri-Solutions Fund covers 85% of cover-crop costs (cap given as $100k in one place and $30k in another; confirm).
  - The tool can say "this rotation may be partly paid for."
- **USDA AMS market news:** weekly hay and forage prices, free key (verified).
- **California SGMA groundwater basin priorities:** overdrafted basins penalize thirsty rotations (verified).
- **Western cover-crop selector:** https://covercrop-selector.org (no API; use it to build a goal table by hand).
- **Environment Canada CanSIPS:** 12-month seasonal forecast (exact collection IDs unconfirmed).

**Not found:** a pest or disease API, or any cover-crop selector API.

---

## 4. News feed

| Source | Status | Use |
|---|---|---|
| BC Gov News: Agriculture & Food | `https://news.gov.bc.ca/ministries/agriculture-and-food/feed` ✓ | **Use.** Drought levels, irrigation orders, flood releases |
| BC Gov News: Water, Land & Resource Stewardship | `https://news.gov.bc.ca/ministries/water-land-and-resource-stewardship/feed` ✓ | **Use** |
| Google News search feed | `https://news.google.com/rss/search?q=<q>&hl=en-CA&gl=CA&ceid=CA:en` ✓ | **Use.** No key; supports date operators. Unofficial, so fetch on the backend and cache |
| GDELT DOC 2.0 | `https://api.gdeltproject.org/api/v2/doc/doc?query=...&mode=artlist&format=json` | **Archive only.** Rate-limited to about 1 request per 5 s; save results before the demo |
| NewsAPI.org | Free plan is development only, 1 month of history | **Skip** |
| The Guardian | Needs a key; little BC coverage | **Skip** |

### How to make it targeted
Each event on the farm's timeline generates its own search query:
```
("Salmon River" OR Shuswap OR "Salmon Arm")
AND (drought OR "water shortage" OR "fish protection order" OR curtail* OR "atmospheric river" OR flood*)
AND (farm* OR forage OR hay OR irrigation OR livestock)
after:2023-07-25 before:2023-09-15
```
- **Ranking:** BC government releases first, then farm press (countrylifeinbc.com), then everything else.
- **Filtering:** drop any article with no place match.

### "What the satellite saw vs. what the news reported"
Each timeline marker shows:
- the NASA signal for that date (e.g. SMAP soil-moisture anomaly, or IMERG multi-day rainfall);
- 1–3 dated headlines;
- a lead-time line, e.g. "SMAP dropped below the 10th percentile X days before the order."

The news confirms what happened; the satellite shows it coming.

---

## 5. Changes to make in `planner-spec.md`
- Move the drought example farm from Kamloops/Thompson to the **Salmon River (Shuswap)**, which gives real 2023 order dates to line up against satellite data.
- Add the **California preset** with a regional adapter for SSURGO, CDL, OpenET and CIMIS.
- Use **SoilGrids** for BC soil, and the **AAFC Crop Rotations** product for current rotations.
- Add the **news timeline** and the **crop-insurance loss risk score**.
- Add **cover-crop funding** to each rotation summary.

## 6. Verify before pitching
- The 398 and 108 licence counts, against the primary BC release.
- The SMAP lead time before the 2023 orders, computed from real data.
- The IAF fund cap ($100k vs $30k).
- Everything marked "U" in `planner-spec.md`.
- That the Vancity prize exists, and the 6-person team limit.
