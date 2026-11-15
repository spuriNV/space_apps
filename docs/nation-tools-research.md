# CropLytics with Indigenous Nations and farmers: research findings for NASA Space Apps 2026

Accessed date for every URL: **2026-11-15**. I didn't edit any repo files. Scratch extracts are in /tmp/claude-1000/-home-caiden-nasa/9d7178d5-c90a-42d5-9484-69406bb4e69e/scratchpad/.

**How claims are marked:**
- **[V]**: I opened the primary page or PDF and read the text.
- **[S]**: seen only in search results or snippets, or a secondary source. Check before you quote it.
- **[NV]**: could not verify.

**Bottom line:** The two strongest wins are:
1. **Salmon River (BC):** a dry-year forage rotation and "water left in the river" planner for Splatsin and the Secwépemc/Syilx Nations.
2. **Tulare Lake Subbasin (CA):** a groundwater and drought-rotation view for the Santa Rosa Rancheria Tachi Yokut Tribe. It sits right next to our Kings, Corcoran and Tipton fields.

Both rest on the Nation's own words, which I found in primary documents. Both use data we already pull. A grant-ready one-page report is the cross-cutting feature that makes either one useful to a small lands office.

---

## PART A: THE WIN, ranked

### Ground rules for every feature
**Respect rules (apply to every feature):**
- **Tap-anywhere on reserve or trust land:** compute the analysis live and don't store it. Put "Your analysis, not saved" on the result. Don't cache it in `data/cache`, and don't log the coordinates.
- **Named Nation views:** published only with the Nation's written permission. Until then, demos use our existing non-reserve fields, and we say "being co-developed with" only if that becomes true.
- **Outputs the Nation owns:** the PDF and CSV export go to the user. We keep no copy. OCAP® and CARE apply ([docs/bc-first-nations.md](/home/caiden/nasa/space_apps/docs/bc-first-nations.md) §5).
- **No cultural layers:**
  - We never map cultural sites, gathering sites or harvest locations.
  - Tachi Yokut told the State Water Board that recharge projects "disturbed or inundated Tachi Yokut Tribal burial grounds" [V]. A tool that recommends where to recharge or flood ground must never do so on its own.
  - Harvest and hunting views stay on the user's own tapped polygon. They're opt-in.

### Win #1: The Salmon River dry-year rotation and river-water planner (Splatsin; also Neskonlith, Adams Lake, Skwlax, OKIB/Syilx)

**Why it's credible.** These are the Nations' and partners' own words.

- **Splatsin's IR1:** IR1 Salmon River is about 1,600 ha, and "the land is mostly used for agriculture, grazing and forestry". Splatsin runs a community Land Use Plan process: "Get involved in Splatsin's LUP by contacting the Lands Use Officer". https://splatsin.ca/your-government/land [V]
- **The water budget:**
  - The Shuswap Watershed Council (SWC) partnered "with the Province of BC, Splatsin te Secwepemc, and… Associated Environmental, to complete a detailed water budget" for the Salmon River between Falkland and Salmon Arm.
  - Its findings: "During dry periods, the Salmon River runs a deficit". "There is limited long-term monitoring of groundwater". The budget "can help inform decisions about water licensing… protecting salmon habitat and planning for dry years".
  - Source: SWC Annual Report 2024–25, https://www.fraserbasin.bc.ca/_Library/TR_SWC/SWC_Annual_Report_2024-25_WEB.pdf [V]
- **Splatsin's own trail-camera monitoring:** The Splatsin Territorial Water Manager, quoted by PSF (4 Dec 2025), said: "Trail cameras on the Swawll Setatkwa (Salmon River) enabled us to watch the changing habitat conditions", and that the program "created affordable access for our community to witness and further understand". https://psf.ca/blog/smarter-drought-monitoring-for-salmon/ [V]
- **The Syilx watershed emergency:**
  - The Syilx Okanagan Nation declared a watershed emergency in May 2026 covering the Okanagan, Similkameen, Nicola, Kettle, **Salmon and Bessette** watersheds.
  - It asked for "a temporary pause on new surface and groundwater licences", "mandatory reductions in water use" and a co-governance forum.
  - Chief Robert Louie: "the health of our watersheds can no longer be treated as secondary to development". https://indiginews.com/?p=38618 (26 May 2026) [V, secondary]
  - The ONA's own resolution PDF returned 404 to me [NV].
- **The 2026 rescinded order:** The Okanagan Nation Chiefs Executive Council objected that the 2026 Salmon River order was rescinded "without consultation or a meeting with the Syilx Okanagan Nation". https://syilx.org/?p=5013 [V]
- **The 2026 order:** "458 surface water and groundwater licences… ordered to stop using water for irrigation of forage crops" (19 Aug 2026). https://news.gov.bc.ca/releases/2026WLRS0042-000965 [V, from the repo doc]
- **Ranchers want the same thing.** Speaking for BC ranchers, the BC Cattlemen's Association GM said: "What we have to do is make it so that there's no need to shut it down". He wants better monitoring. The Tyee, 8 Sep 2026: https://thetyee.ca/News/2026/09/08/Fish-Go-Blind-BC-Droughts/ [V]
- **BC First Nations Climate Strategy:**
  - Theme 4.6.2: "Recognize First Nations authority to conduct climate-related assessments and monitoring work in their own self-determined ways to generate their own data".
  - The strategy says Nations "require support in developing and strengthening community-based flood, drought, and food security strategies, including an in-depth assessment of… water balance".
  - Source: BCAFN BCFNCSAP Final Draft (22 Apr 2022), https://bcafn.ca/sites/default/files/2022-04/BCFNCSAP%20Final%20Draft%20(22April2022).pdf [V]

**What we build.** It runs on data we already have: the BC field, WSC 08LE021 "SALMON RIVER NEAR SALMON ARM" (already in `backend/bc/fetch_wsc.py`), SMAP, GRACE-DA, POWER, IMERG, ECOSTRESS ET and HLS NDVI.
- The "Salmon and the field" panel works on any tapped polygon in the Salmon watershed, including IR1 if a Splatsin user taps it (live, not saved). Its inputs and outputs:
  - flow now against the order trigger history (2023, Jul 2026, Aug 2026);
  - water temperature where available;
  - each rotation's irrigation demand from mid-August;
  - "water left in river" per rotation: river flow minus summed ET-based demand, as an indicator, not a licence calculation;
  - a "dry-year rotation" recommendation, for example cut timing and a winter cereal before forage that can tolerate a mid-August shut-off.
- Groundwater card: GRACE-DA shallow groundwater and root-zone percentile at 0.25°, labelled "regional context; the SWC water budget notes limited groundwater monitoring".

**Fit to judging:**
- **Local Impact:** a real watershed, with orders in 2023 and 2026.
- **Most Inspirational:** the farmer–salmon–Nation reconciliation story. Ranchers and the Nation both want "no need to shut it down".
- **Global Connection:** snowmelt rivers shared by irrigators and salmon exist from the Fraser to the Klamath to Chile.
- **Impact:** 458 licences.

**Feasibility this week:** high. It's mostly wiring existing data into the panel. The Nation-facing claims stay modest.

### Win #2: Tulare Lake groundwater and drought-rotation view (Santa Rosa Rancheria Tachi Yokut Tribe; Kings County)

**Why it's credible:**
- **The consultation record.** The tribe consulted the State Water Board and DWR on 12 Mar 2024. The record says:
  - "The Tachi Yokut Tribe shared concerns regarding groundwater quantity, groundwater quality, and subsidence issues affecting their beneficial uses and tribal reserved water rights, including drinking water and agricultural activities."
  - "it only has limited access to surface water, with seasonality, high variability, and bureaucratic obstacles contributing to inconsistent deliveries."
  - "The Tachi Yokut Tribe has also developed a farming operation… impacts to groundwater pose risks to this enterprise."
  - "The Tachi Yokut Tribe's tribal reserved water rights have not been quantified."
  - The tribe also wanted "coordinating groundwater management among neighboring basins".
  - Source: Tulare Lake probationary hearing, Final Staff Report Appendix C, https://www.waterboards.ca.gov/sgma/docs/tulare-lake/202403-tulare-lake-pbh-final-staff-report-appendix-c.pdf [V]
- **Tachi Farms and water.** DWR set up temporary and permanent water transfers for Tachi Farms, LLC, which the tribe owns. The amount was "over 600 acre-feet", and the tribal chairman called it "a historic moment". https://www.western-water.com/2024/06/13/california-aids-tachi-yokut-tribe-with-water-transfer-deal/ [V, secondary]
  - The DWR release returned 403 to me: https://water.ca.gov/News/News-Releases/2024/Jun-24/California-and-Tribal-Partners-Secure-Critical-Water-Supply-to-Support-Native-American-Farmers [S]
- **Seats.** The tribe is not one of the five Tulare Lake GSAs [S, State Water Board draft resolution]. One report says the tribe owns about 3,600 acres in the basin and has no seat on the five water district boards [S].
- **What SGMA says about tribes:**
  - Water Code §10723.2(h) lists "California Native American Tribes" among the interests a GSA "shall consider".
  - §10720.3(d): "federally reserved water rights to groundwater shall be respected in full".
  - I read both as quoted in DWR's tribal guidance (June 2017 **draft** text): https://cawaterlibrary.net/wp-content/uploads/2018/03/GD_Tribal_Final_2017-06-28.pdf [V]. leginfo returned 403, so check the current statute text there.

**What we build:**
- Tap the tribe's farm parcel (live, not stored) and show:
  - GRACE-DA groundwater percentile, weekly, with the 2012–16 and 2020–22 droughts marked;
  - SMAP root-zone moisture;
  - OpenET or ECOSTRESS crop water use per rotation. We already have Kings, Corcoran and Tipton fields in this subbasin to calibrate against.
- A "surface-water-short year" rotation that compares pumping demand by rotation.
- SGMA context card:
  - subbasin name and probation status (designated probationary 16 Apr 2024; enforcement suspended by injunction from 13 Sep 2024 [S]);
  - the GSA list;
  - links to the State Water Board Tulare Lake page and the SGMA portal (https://sgma.water.ca.gov/portal/ [V live]).
- An optional subsidence line from OPERA DISP-S1 InSAR. It's **not in our stack yet**, so it's out of scope this week.

**Respect rule specific to this tribe:** don't suggest recharge or flooding sites (see the burial-ground statement above).

**Fit to judging:** groundwater is California's defining farm-water problem (Impact). This Kings County tribe farms beside our own fields (Local). It also fits Global Connection: aquifer depletion and GRACE are a global story.

**Feasibility this week:** high for the data. Name the tribe on screen only with permission. Otherwise say "built for tribal farms in the Tulare Lake Subbasin, e.g. after tribal consultation concerns documented by the State Water Board."

### Win #3 (cross-cutting): a grant-ready one-page field report (PDF or CSV) a lands or water office can attach

The best near-term hooks:
- **CDFA Tribal Food Sovereignty Grant Program:**
  - $15M, funded by the 2024 climate bond, for California Native American Tribes.
  - It covers food systems "encompassing stewardship, cultivation, harvesting, production, and distribution", plus land return and acquisition.
  - Public comment Nov–Dec 2026, RFP January 2027, applications due March 2027 (tentative).
  - https://www.cdfa.ca.gov/tribal_food_sovereignty/ [V]
- **First Nation Adapt (Canada):** open all year, $8.42M for FY2026–27, for First Nations south of 60°. It funds risk assessments and "integrating adaptation into land-use… planning". https://www.rcaanc-cirnac.gc.ca/eng/1481305681144/1594738066665 [V]
- **BIA Water Management, Planning & Pre-Development:** funds "water surveys including quantification studies" [S]. That matches Tachi's unquantified rights.

**Report contents:**
- field outline, area and land cover;
- a 10–20-year drought history: IMERG precipitation anomaly, SMAP, and GRACE-DA percentiles;
- water-use baseline from ECOSTRESS or OpenET per crop;
- rotation comparison: water, erosion, soil cover, nitrogen;
- river or groundwater context;
- the data sources and their caveats;
- "Prepared by [Nation]; data © Nation, generated [date]; not stored by CropLytics."

**Fit to judging:** it turns NASA data into a dollars-and-capacity outcome. That answers the "small staff" need: the Navajo DSET lesson is that tools must save managers' time, and the user-community shouldn't carry the upkeep burden.

**Ranking:** #1 (BC) is first because the need is publicly documented by several Nations, the data path is already built, and it ties to the 2026 orders. #2 (Tachi) has the strongest written statement of need, but it should be framed carefully. #3 makes both useful.

### "Nation tools" feature set, with proposed API fields
New routes follow the existing `/api/locations/{pid}/…` pattern. Tap-anywhere `pid`s on reserve or trust land should carry `ephemeral: true`, which means no disk cache.

**1. Farming tools**

`GET /api/locations/{pid}/nation/drought_rotation`. This is drought-year rotation planning for Nation-run farms.

| Field | What it holds |
|---|---|
| `land_status` | `reserve` / `trust` / `fee` / `private` / `unknown`, from CLSS or BIA LAR boundaries |
| `ephemeral` | bool |
| `rotations[]` | each with `id`, `name`, `water_mm_season`, `water_mm_after_cutoff`, `erosion_t_ha`, `soil_cover_pct`, `n_balance_kg_ha`, `dry_year_rank` |
| `cutoff_scenarios[]` | `cutoff_date`, `yield_loss_pct` per rotation |
| `drought_history[]` | `year`, `imerg_precip_anom_pct`, `smap_rootzone_pctl`, `gracedadm_gw_pctl`, `power_et0_mm` |
| `sources[]` | data sources |

`GET /api/locations/{pid}/nation/groundwater` (California)

| Field | What it holds |
|---|---|
| `b118_subbasin_id`, `b118_subbasin_name` | Bulletin 118 subbasin |
| `gsa_names[]` | GSAs covering the parcel |
| `sgma_status` | e.g. "probationary – enforcement enjoined" |
| `gw_pctl_weekly[]` | GRACEDADM_CLSM025GL_7D (already used in the backend) |
| `smap_rootzone_weekly[]` | SMAP root-zone moisture |
| `et_mm_by_crop` | crop water use |
| `pumping_need_af_by_rotation` | pumping need per rotation |
| `tribal_links[]` | DWR tribal guidance, State Water Board tribal affairs |
| `caveat` | "GRACE-DA is ~25 km regional context, not a well" |

**2. Salmon flow vs irrigation**

`GET /api/locations/{pid}/nation/salmon`

| Field | What it holds |
|---|---|
| `station_id` | "08LE021" |
| `flow_m3s_daily[]` | daily flow |
| `flow_pctile_today` | today's flow percentile |
| `water_temp_c[]` | if available |
| `orders[]` | each with `date`, `type`, `licences`, `url` |
| `run_timing[]` | chinook entry window, cited |
| `rotations[]` | each with `irrigation_m3_after_aug15`, `share_of_low_flow_pct` |
| `dswx_wet_area_km2` | OPERA DSWx river wetted extent, if usable |

**3. Harvest, hunting and plant tools** (opt-in, on the user's own polygon only)

`GET /api/locations/{pid}/nation/land_season`

| Field | What it holds |
|---|---|
| `ndvi_weekly[]` | HLS or MODIS MOD13Q1 |
| `greenup_doy`, `peak_doy`, `senescence_doy` | phenology, usable as a proxy for forage, berry and plant timing |
| `ndvi_vs_normal_pct` | greenness against normal |
| `snow_cover_pct_weekly[]`, `snow_off_doy` | MODIS MOD10A1 (https://nsidc.org/data/mod10a1 [V live]) |
| `fire_detections_365d[]` | NASA FIRMS (https://firms.modaps.eosdis.nasa.gov/ [V live]) |
| `burn_scars[]` | each with `year`, `source` (MTBS https://www.mtbs.gov/ [V live] for the US; BC historical fire perimeters https://catalogue.data.gov.bc.ca/dataset/bc-wildfire-fire-perimeters-historical [V live]) |
| `regs_links[]` | links only: BC 2026–2028 Hunting & Trapping Regulations Synopsis https://www2.gov.bc.ca/gov/content/sports-culture/recreation/fishing-hunting/hunting/regulations-synopsis [V live]; CDFW deer zones https://wildlife.ca.gov/Hunting/Deer/Zones and elk https://wildlife.ca.gov/Hunting/Elk [V live] |
| `harvest_rights_note` | "Aboriginal/treaty and tribal harvesting rights are set by the Nation and by law, not by this tool; provincial/state seasons shown for context only" (my wording, not a legal source) |

Don't overstate this layer. NDVI phenology is a proxy for forage and plant timing, not a measure of game or berries. **We store no harvest locations.**

**4. Funding tools**

`GET /api/locations/{pid}/nation/funding?jurisdiction=CA|BC|US`

| Field | What it holds |
|---|---|
| `programs[]` | each with `name`, `agency`, `eligible`, `funds`, `typical_amount`, `status`, `deadline`, `url`, `url_checked`, `how_croplytics_helps`, `report_sections[]` |

`GET /api/locations/{pid}/nation/report.pdf?program=cdfa_tfs|fn_adapt|bia_wmppd|eqip` builds the one-page report with the sections that program asks for. The PDF goes to the user and nothing is kept.

**5. Traditional and cultural plants in rotations** (only as an option the Nation turns on)
- **Secwépemc:** *Secwepemc People and Plants* (Ignace, Turner and Peacock eds.) records more than 135 plant species used, at least 48 as food. That includes:
  - spring beauty, called "mountain potato";
  - balsamroot;
  - saskatoon, "the most important" berry.
  - Sources: https://ethnobiology.org/publications/contributions/secwepemc-people-and-plants-research-papers-shuswap-ethnobotany [V live; contents S] and https://shuswappassion.ca/history/the-secwepemc-use-of-wild-plants/ [S]
- **California:** NRCS's *Native Uses of Native Plants (Sierra Nevada and foothills)* lists deergrass ("a very significant basketry plant") and California black oak (acorn food). https://www.nrcs.usda.gov/sites/default/files/2023-01/Native_Uses_of_Native_Plants-revised_2018-web.pdf [S; the fetch timed out]
- **Product idea:** a field-border or hedgerow "set-aside" option in the rotation, for example native perennial grass or deergrass strips. Score it on soil cover, erosion and water.
  - Don't present cultural plants as crops we recommend.
  - Plant knowledge belongs to the Nations (OCAP®/CARE). Add species only from a Nation's list.

**6. Language and naming**
- Show the Nation's own place names next to English, with the source:
  - "Swawll Setatkwa (Salmon River)", per Splatsin via PSF [V];
  - the Okanagan Nation Alliance's spelling, "akscʷin" [from the repo doc];
  - "Yocha Dehe = 'home by the spring water'" (https://yochadehe.gov/heritage/our-story/ [S]). The Nation's language page says "Revitalizing and reclaiming Patwin is not only an act of cultural preservation" (https://yochadehe.gov/culture/language/ [V]).
- Fields: `place_names[]` with `{name, language, source_url, approved_by_nation:bool}`. Show a name only when `approved_by_nation` is true, or cite the Nation's own public page.

---

## PART B: FINDINGS BY SECTION

### 1. Who is near our fields: farming, land base, harvest

**BC (Secwépemc and Syilx).** The SWC says the Shuswap watershed is "within Secwepemc'ulecw, the traditional unceded territory of the Secwepemc Peoples and the homeland of the Neskonlith, Skw'lax, Adams Lake, and Splatsin te Secwepemc First Nations", and that its waters are "culturally significant to the Secwepemc and Syilx First Nations" [V, SWC report].

**Splatsin**
- Farming and land base:
  - IR1 is about 1,600 ha, "mostly used for agriculture, grazing and forestry", with a Land Use Plan process underway [V].
  - Reserve access is by BCR; use permits "for a defined period of time" [V].
  - The Splatsin Tsm7aksaltn Society runs a food sovereignty program: "Hunting and fishing trips guided by knowledge keepers", "Gardening and seed-saving", funded by NRT's Indigenous Food Security and Sovereignty Fund. https://newrelationshiptrust.ca/splatsins-path-to-food-sovereignty/ [V]
  - I found no farm enterprise acreage or crop list [NV].
- Harvest, water and salmon:
  - Splatsin has a Territorial Water Manager and took part in the 2025 low-flow pilot (PSF) [V].
  - It was a partner in the SWC Salmon River water budget [V].
  - The lands page doesn't name the water manager role. That differs from the repo doc, which says the lands page lists it.

**Neskonlith**
- Farming and land base: the nearest reserve to our field (Switsemalph IR 3). Its Comprehensive Community Plan PDF returned 404 to me [NV]. A snippet from the plan says ranches filled grazing lands by 1940 and that the Veterans Lands Act (1942) removed Secwépemc people from most arable valley land [S]. Its Lands Department uses GIS for referrals [S].
- Harvest, water and salmon: no public detail found [NV].

**Adams Lake**
- Farming and land base: its Land Use Plan Phase II (2013) has an "'A' Agricultural" zone "intended for uses which have 'agriculture' as the primary activity", allows "Intensive Agriculture (with a permit from Lands Department)", and refers to an "ALIB 'Farm Development Agreement' Policy". https://adamslakeband.org/wp-content/uploads/2016/09/LUP-Phase-II-final-final-report.pdf [V]. A greenhouse project appears in its 2019–20 annual report [S].
- Harvest: it contributed 574 chinook to a Secwépemc Fisheries Commission (SFC) communal fishery in 2019. https://adamslakeband.org/home/sfc-communal-fishing-report-for-2019 [S]

**Skwlax te Secwépemc**
- Farming and land base: no public agriculture information found [NV].
- Harvest: no public detail found [NV].

**Okanagan Indian Band (Syilx)**
- Farming and land base:
  - The Sun Valley Ranch project near Vernon (2023 Young Agrarians tour) [S].
  - IAF-delivered food-security funding [S].
  - The band's Chief chairs the BC Indigenous Advisory Council on Agriculture and Food [S; news.gov.bc.ca/releases/2021AFF0044-001364 not opened].
- Harvest, water and salmon:
  - The ONA calls sockeye a "primary food mainstay of the syilx Okanagan peoples" [S].
  - In 2025 a thermal barrier meant no coordinated food fishery. https://syilx.org/wp-content/uploads/2025/07/Declining-Salmon-Returns-2025-Community-Notice_July-21-25.pdf [S]
  - The 2026 watershed emergency [V, secondary].

**Secwépemc Fisheries Commission (SNTC):** established in 1988. It manages Food, Social and Ceremonial fisheries [S]. https://shuswapnation.org/fisheries/ [V live]. DFO says 2026 is a dominant Adams River sockeye year [S].

**California**

**Cachil Dehe Band of Wintun Indians (Colusa)**
- Farming:
  - "We now farm over 4,000 acres of diversified tree, grain and field crops".
  - "in excess of 2,800 acres, is currently planted with rice".
  - "220,000 to 245,000 cwt. sacks per year".
  - It runs a rice dryer (built 2001).
  - Source: https://www.colusa-nsn.gov/farming/ [V]
- Land base: a BIA FONSI covers a 519-acre fee-to-trust application (2026) [S].
- **Groundwater:** I found no tribal role in the Colusa Subbasin GSAs [S].
- **This is the closest match to our Colusa rice fields.**

**Yocha Dehe Wintun Nation (Capay Valley, Yolo)**
- Farming:
  - "3,000 acres currently being farmed", 250 of them certified organic.
  - "800 head of cattle on 20,000 acres of rangeland".
  - "more than 1,200 acres… protected through permanent conservation easements".
  - Practices include crop rotation, cover crops and drip irrigation.
  - Séka Hills olive oil, wine and honey.
  - Source: https://yochadehe.gov/farm-ranch/ [V]. Other sources give 17,000–25,000 acres; those likely count range and conservation land [S].
- Water:
  - The Yocha Dehe Environmental Department monitors 35 wells, has a well ordinance and declared a tribal drought emergency (Yolo County water forum, May 2023) [S].
  - **The Nation has a seat on the Yolo Subbasin Groundwater Agency board.** https://yologroundwater.specialdistrict.org/board-members [S]

**Paskenta Band of Nomlaki (Tehama, near Glenn)**
- Land base: about 1,898 acres taken into trust in 2000, with later trust bids [S].
- Farming: none found [NV].

**Mechoopda (Chico, Butte)**
- Land base:
  - The 93-acre Butte Creek Ecological Preserve was transferred from Chico State in 2022 [S].
  - A 450-acre "Ótakim Séwi" parcel on Big Chico Creek was bought through CNRA's Tribal Nature-Based Solutions program. Holdings are about 3,000 acres [S]. The CNRA page returned 403, so the date is [NV].
- Harvest, water and salmon: EPA GAP/CWA 106/319 and BIA Water Management grants; salmon framing [S].

**Santa Rosa Rancheria Tachi Yokut (Kings)**
- Farming:
  - Tachi Farms, LLC, a "farming operation to provide economic development and employment" [V, SWRCB].
  - 600+ AF water transfers [V, secondary].
  - A proposed RV park, orchard and Mussel Slough restoration on about 437 acres [S].
  - Rancheria: 1,806 acres (2008) [S].
- Harvest and water: groundwater, subsidence, drinking water and reserved rights (above) [V]. Tulare Lake reconnection (2023 coverage) [S].

**Tule River Tribe (Tulare)**
- Land base and harvest:
  - 17,030 acres (Hershey and Carothers ranches, "Yowlumne Hills") returned, and **tule elk reintroduced** with CDFW, announced 29 Oct 2025. https://www.gov.ca.gov/2025/10/29/tule-river-indian-tribe-of-california-reclaims-over-17000-acres-and-reintroduces-tule-elk-on-ancestral-land/ [V live; details S]
  - The Natural Resources Department mission is to manage "agricultural and natural resources" [S].
- Water:
  - The South Fork supplies about 80% of its water.
  - In drought the tribe has relied on trucked water.
  - The Tule River Tribe Reserved Water Rights Settlement Act of 2025 (S.689) was reported by the Senate Committee on Indian Affairs. Enactment is [NV]. https://www.congress.gov/119/bills/s689/BILLS-119s689rs.htm [S]

**Picayune Rancheria of Chukchansi**
- Groundwater: the State Water Board lists it among tribes with ties to the **Chowchilla Subbasin** (agriculture is over 97% of groundwater use there) [S].
- Farming: none found [NV].

### 2. Documented needs our data addresses

| Need | Evidence |
|---|---|
| Drought and groundwater | Tachi (SWRCB Appendix C) [V]; SWC "limited long-term monitoring of groundwater" [V]; Yocha Dehe well monitoring and drought declaration [S]; SGMA §10723.2(h) [V via DWR draft] |
| Water rights and allocations | Tachi rights "have not been quantified" [V]; Tule River settlement bill [S]; BC licences under orders [V] |
| Salmon and instream flow | Salmon River orders 2023 and 2026 [V]; Syilx emergency [V]; PSF and Splatsin pilot [V]; Klamath tribal monitoring: Karuk real-time stations at waterquality.karuk.us (EPA R9 2025 workshop) [S] |
| Food sovereignty | Splatsin Society [V]; CDFA program [V]; BCFNCSAP Theme 4.4 [V] |
| Climate adaptation | BCFNCSAP Themes 2.4, 4.4 and 4.6 [V]; First Nation Adapt [V] |
| Land back and new farmland | Tule River 17,030 acres [V/S]; Mechoopda 450 acres [S]; Cachil Dehe 519 acres [S]; Yocha Dehe purchases [S] |
| Capacity | DSET lesson: maintenance should "not fall on the user communities" [V]; the SGC Tribal Capacity Building Program funds staff [V] |

### 3. Programs and funding

Here "eligible" means who can apply. "How CropLytics helps" is our proposal.

**United States: federal**

**NASA Indigenous Peoples Initiative (IPI), Earth Action / Capacity Building**
- Eligible: tribes and Indigenous communities.
- Funds: training and co-developed workshops (for example, Karuk DNR on wildfire and watersheds), not grants.
- Amount: n/a.
- Status: ongoing. The appliedsciences IPI page now redirects to science.nasa.gov/earth-science/earth-action, which lists "Federally-recognized Tribes" as partners [V].
- URL: https://science.nasa.gov/earth-science/earth-action [V]
- How CropLytics helps: a NASA-data tool that IPI could use in trainings. Cite IPI's principle of "listening" and "co-develop" (2024 presentation [S]).

**NASA DEVELOP**
- Eligible: partner organizations, tribes included (e.g. Rosebud Sioux 2021, Navajo 2016).
- Funds: 10-week feasibility projects at no cost to the partner.
- Amount: n/a.
- Status: term-based. develop.larc.nasa.gov timed out [NV].
- How CropLytics helps: our tool could be the starting point for a DEVELOP–Nation project.

**NASA ARSET**
- Eligible: open to anyone.
- Funds: online training. A past course was "Earth Observations for Indigenous-Led Land Management" (2019).
- Amount: free.
- Status: catalogue live.
- URL: https://www.earthdata.nasa.gov/data/projects/arset [V]
- How CropLytics helps: point staff to it for capacity building.

**NASA WWAO**
- Eligible: western water managers.
- Funds: co-developed tools (e.g. Navajo DSET).
- Amount: n/a.
- Status: ongoing.
- URL: https://wwao.jpl.nasa.gov/water-portfolio/water-projects/nasa-navajo-drought-severity-tool-user-guide [V]
- How CropLytics helps: precedent for a Nation water tool.

**USDA NRCS EQIP**
- Eligible: producers, including tribes. "Indian tribes… are eligible for an increased payment rate and may receive advance payment of up to 50 percent" (NRCS Idaho [S]).
- Funds: conservation practices such as irrigation efficiency and cover crops.
- Amount: practice payment schedules; the historically-underserved rate is at least 25% above the base rate [S].
- Status: continuous sign-up with state ranking dates.
- URL: https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives (timed out for me [NV])
- How CropLytics helps: the report gives the baseline water use per crop, erosion and soil-cover figures, and the rotation change that maps to cover crop (340) and irrigation water management (449).

**USDA Indigenous Animals Harvesting & Meat Processing Grant**
- Eligible: tribes.
- Funds: meat processing.
- Amount: up to $50M total (ARPA); FY23 awards of about $42M to 8 Nations [S].
- Status: no 2026 round found. The FY23 round closed 19 Jul 2023 [S].
- URL: https://www.usda.gov/iag (403 to curl [NV])
- How CropLytics helps: only weakly, through forage and range greenness for herd planning (Yocha Dehe's 800 head).

**USDA NIFA FRTEP**
- Eligible: land-grant universities (1862, 1890, 1994), with extension on reservations.
- Funds: farm and ranch productivity, natural resources.
- Amount: not listed; past funding over $3.8M.
- Status: see the NOFO.
- URL: https://www.nifa.usda.gov/grants/programs/federally-recognized-tribes-extension-program [V]
- How CropLytics helps: a tool extension agents can use with tribal farms.

**USDA Office of Tribal Relations**
- Eligible: tribes.
- Funds: coordination and referral, not grants.
- URL: https://www.usda.gov/tribalrelations (403 [NV])
- How CropLytics helps: a referral path.

**BIA Tribal Community Resilience Annual Awards**
- Eligible: federally recognized tribes and tribal organizations.
- Funds: competitive resilience funding.
- Amount: not listed.
- Status: "Updates are pending on future funding cycles"; contact resilience.funding@bia.gov.
- URL: https://www.bia.gov/service/tcr-annual-awards-program [V]
- How CropLytics helps: drought and climate history plus rotation scenarios for an adaptation-planning narrative.

**BIA Water Management, Planning & Pre-Development**
- Eligible: tribes, through the BIA Regional Office.
- Funds: technical assistance and "water surveys including quantification studies" [S].
- Amount: not listed. The House FY27 mark adds $3.307M [S].
- Status: the FY27 call went out in March 2026 [S].
- URL: https://www.bia.gov/service/water-management-planning-and-pre-development-program [V live]
- How CropLytics helps: ET-based crop water demand and GRACE-DA trends as preliminary characterization of "water concerns". This is the best fit for Tachi.

**EPA Indian Environmental General Assistance Program (GAP)**
- Eligible: federally recognized tribes and consortia.
- Funds: building environmental program capacity, including monitoring.
- Amount: Region 10's ceiling is up to $138k/yr [S]; Region 9's amount is not listed.
- Status: FY26 NOFA for workplans starting on or after 1 Oct 2026. The Region 9 deadline (6 Feb 2026) has passed [S].
- URL: https://www.epa.gov/tribal-pacific-sw/r9-gap-funding [S]
- How CropLytics helps: water and land monitoring baselines for the workplan.

**US Bureau of Reclamation Native American Affairs**
- Eligible: tribes.
- Funds: technical assistance on water.
- Amount: varies.
- URL: https://www.usbr.gov/native/ [V live]
- How CropLytics helps: water-use estimates.

**California**

**CDFA Tribal Food Sovereignty Grant Program**
- Eligible: California Native American Tribes.
- Funds: food systems (stewardship, cultivation, harvesting, production, distribution) and land return.
- Amount: $15M total.
- Status: RFP January 2027; due March 2027; comment period Nov–Dec 2026.
- URL: https://www.cdfa.ca.gov/tribal_food_sovereignty/ [V]
- How CropLytics helps: the field report gives the drought history, water baseline and rotation plan for a food-production proposal. **Best CA timing.**

**SGC Tribal Capacity Building Program, Round 2**
- Eligible: CA tribes on the NAHC list.
- Funds: staff salaries, planning and pursuing climate funding.
- Amount: $350k–$420k over 3 years.
- Status: closed 11 Aug 2026; awards were scheduled for 28 Oct 2026.
- URL: https://sgc.ca.gov/grant-programs/tribal [V]
- How CropLytics helps: a no-cost tool that adds to a funded staff member's capacity.

**CNRA Tribal Nature-Based Solutions**
- Eligible: CA tribes.
- Funds: land acquisition and return, and stewardship (the 2026 round is about $9.2M [S]).
- Status: [NV]
- URL: https://resources.ca.gov/ (pages 403)
- How CropLytics helps: a baseline land-cover, water and NDVI profile for a parcel being acquired.

**DWR SGMA tribal engagement**
- Eligible: tribes.
- Funds: guidance and consultation, not money. It includes "Engagement with Tribal Governments" guidance and a SGMA Tribal Advisory Group (Tachi consultation was offered through the TAG on 1 Nov 2023 [V]).
- URL: https://water.ca.gov/About/Tribal-Policy (403 [NV])
- How CropLytics helps: groundwater context for a GSA consultation.

**First Nations Development Institute, California Tribal Fund** (non-government)
- Eligible: CA Native-led nonprofits and tribal programs.
- Funds: ancestral lands and waters stewardship.
- Status: 2026 deadline 27 Apr 2026 (closed).
- URL: https://www.firstnations.org/programs/california-tribal-fund/ [V live]

**Canada (federal)**

**AAFC Indigenous Pathfinder Service**
- Eligible: "First Nations, Métis, and Inuit individuals and organizations".
- Funds: advice and referral to AAFC programs.
- Amount: n/a.
- Status: open. Contact aafc.indigenouspathfinder-explorateurautochtone.aac@agr.gc.ca.
- URL: https://agriculture.canada.ca/en/programs/indigenous-pathfinder-service [V]
- How CropLytics helps: the report as a project summary for the advisor.

**CIRNAC First Nation Adapt**
- Eligible: First Nations south of 60°.
- Funds: risk assessments, hazard mapping, adaptation in land-use planning.
- Amount: $8.42M available for FY26–27.
- Status: **open year-round**.
- URL: https://www.rcaanc-cirnac.gc.ca/eng/1481305681144/1594738066665 [V]
- How CropLytics helps: drought, flow-order and fire history for IR1 to feed Splatsin's Land Use Plan. **Best BC fit.**

**CIRNAC Indigenous Community-Based Climate Monitoring**
- Eligible: Indigenous communities and Nations.
- Funds: monitoring plans, staff and equipment.
- Amount: not listed.
- Status: no deadline, but south-of-60 funding for 2026–28 is prioritized for previous recipients and referrals.
- URL: https://www.rcaanc-cirnac.gc.ca/eng/1509728370447 [V]
- How CropLytics helps: satellite baselines that sit beside Nation-run cameras and gauges.

**BC Salmon Restoration and Innovation Fund**
- Eligible: Indigenous groups and others.
- Funds: salmon habitat.
- Status: **closed**; it supports projects to 31 Mar 2026.
- URL: https://www.dfo-mpo.gc.ca/fisheries-peches/initiatives/fish-fund-bc-fonds-peche-cb/index-eng.html [V]
- How CropLytics helps: n/a now.

**FCC Indigenous financing**
- Eligible: Indigenous producers.
- Funds: loans.
- URL: https://www.fcc-fac.ca/en/financing/indigenous-financing [V live]
- How CropLytics helps: rotation economics context.

**British Columbia**

**IAF / AAFC–BC Indigenous Food Systems & Agriculture Partnership Program (IFSAP)**
- Eligible: BC Indigenous Nations and organizations.
- Funds: agriculture, food processing, planning.
- Amount: up to $80k [S].
- Status: appears closed [S]. https://iafbc.ca/ifsap returned 404. Program guide: https://iafbc.ca/wp-content/uploads/2022/09/IFSAP-Program-Guide_Web_Sept_FINAL.pdf [S]
- How CropLytics helps: n/a now.

**BC Indigenous Food Pathways Program**
- Eligible: BC Indigenous groups.
- Funds: food projects.
- Amount: up to 75% of costs, max $200k [S].
- Status: closed. Intake deadline was 10 Jan 2025 [S]; the program page returned 404.
- How CropLytics helps: n/a now.

**NRT Indigenous Food Security & Sovereignty Grant**
- Eligible: BC First Nations, departments and Indigenous farms.
- Funds: planning (Stream 1) and capital (Stream 2).
- Amount: up to $150k (S1) and $250k (S2).
- Status: **closed, funds exhausted**.
- URL: https://newrelationshiptrust.ca/indigenous-food-security-and-sovereignty/ [V]
- How CropLytics helps: for a future intake.

**IAF ISAT (skills and training)**
- Status: "Not Accepting Applications" (repo doc).
- URL: https://iafbc.ca/indigenous-food-systems-and-agriculture-skills-and-training-program/ [V live]

**BC First Nations Climate Strategy & Action Plan**
- Funds: none; it's a policy framework. Cite Themes 2.4, 4.4 and 4.6.
- URL: BCAFN PDF above [V]
- How CropLytics helps: lets us align the pitch with Nation-led data priorities.

### 4. Precedents, and what made them respectful

- **Navajo Nation DSET (NASA DEVELOP 2015/16, then WWAO and DRI; finished 2020).** USDA Climate Hubs case study (Aug 2022) [V]: https://www.climatehubs.usda.gov/sites/default/files/Co-Developing_the_Drought_Severity_Evaluation_Tool_for_Use_on_the_Navajo_Nation.pdf
  - The team "strive[d] for restorative and reciprocal collaboration and authentic co-development".
  - It added Navajo Chapter boundaries so the analysis matched local decisions, and it pulled in Navajo Nation Department of Water Resources data from 85 rain gauges.
  - Training videos were made "in the Navajo language".
  - Lesson: "the financial and operational responsibility to maintain tools should not fall on the user communities".
  - Lesson: the DEVELOP R Shiny version "required extensive programming experience", which is why it was rebuilt.
  - **This is the closest NASA precedent to ours; cite it.**
- **NASA IPI and the Karuk Tribe.** About a year of dialogue led to a co-developed workshop on remote sensing of wildfire and watersheds. In-person training took place at Karuk DNR in Orleans, CA [S; the IPI 2023 report URL now redirects].
- **Karuk and Yurok Klamath monitoring.** Real-time tribal water-quality stations after dam removal; a 2025 coalition report counted over 10,000 large fish passing Iron Gate [S]. The data is owned and published by the tribes.
- **SEI "Remote data, Indigenous California" (2022–23).** It looked at how satellite imagery could support tribal land and water decisions, and the barriers to it [S; the page returned 403].
- **Indigenous Mapping Workshop (Firelight; partners include Google, Esri Canada, CSA and NASA).** The 2026 edition in Vancouver, 21–23 Sep, centred on "Indigenous Data Sovereignty… in the era of AI". Maps made there stay private unless the Nation publishes them [S]. https://firelight.ca/news/2026-indigenous-mapping-workshop [S]
- **Space Apps 2021 Most Inspirational: Bioshi/SIMACT.** Landsat plus sensors against illegal logging, for the Guna, Emberá and Wounaan peoples. The page says the team was motivated by "their own Indigenous communities" but shows **no direct co-design** [V]. https://2021.spaceappschallenge.org/challenges/statements/space-for-change/teams/bioshi/project/
- **Common thread:** co-development over months, Nation boundaries and Nation data, training and handover, the Nation's language, and data that stays private by default. NASA has no formal Indigenous data sovereignty policy that I could find [NV]. Cite CARE (GIDA), OCAP® and BCFNCSAP Theme 2.4 instead.

### 5. Judging-criteria mapping (summary)
- **Impact:** 458 BC licences, and the Tulare Lake groundwater crisis.
- **Local Impact:** the Salmon River, and Kings County beside our fields.
- **Most Inspirational:** farmers and the Nation both say they want "no need to shut it down"; data that stays with the Nation; following DSET's example. Use Bioshi-style framing, but stay honest: it's "built to be co-developed".
- **Global Connection:** snowmelt rivers, salmon and aquifers, using GRACE, SMAP and ECOSTRESS, which are global datasets.

### 6. Draft outreach email (not sent)
**To:** Splatsin Lands Department, through the Lands contact form at https://splatsin.ca/your-government/land, or the administration office at (250) 838-6496 [V]

**Subject:** A free farm-water and salmon planning tool – would it be useful to Splatsin?

> Weytk,
>
> We are a small student team building CropLytics, a free crop-rotation planner for the 2026 NASA Space Apps Challenge. It uses NASA satellite data (rainfall, soil moisture, crop water use, groundwater) together with the Water Survey of Canada gauge on the Swawll Setatkwa (Salmon River) to show how much irrigation different forage rotations need, especially after a mid-August water order.
>
> We have not analysed any Splatsin reserve land, and we will not publish anything about Splatsin or IR1 without the Nation's written permission. If a member of your staff ever uses the tool on Splatsin land, the analysis is computed on the spot and not stored by us; any report it produces belongs to the Nation.
>
> We would be grateful to know:
> 1. Would a tool like this be useful to your lands, water or farm staff at all? "No" is a perfectly good answer.
> 2. If so, what would help most: dry-year rotation planning, river flow vs. irrigation, a one-page report for funding applications (e.g. First Nation Adapt), or something else?
> 3. Is there a research or data protocol we should follow, and who should we speak with about it?
>
> We are happy to show a short demo at a time that suits you, and to credit or compensate anyone who gives us their time. Thank you for considering this.
>
> Kukwstsétsemc,
> The CropLytics team

Check the Secwepemctsín greeting and thanks with the Nation, or drop them. For the CA version, write to the Tachi Yokut Tribal EPA through https://www.tachi-yokut-nsn.gov/epa-center [S live], swapping in the Tulare Lake groundwater framing.

---

## PART C: UNVERIFIED AND CONFLICTS
- The DWR, CNRA, PPIC, SEI, leginfo, USDA (iag, tribalrelations) and resources.ca.gov pages returned 403 to me. The statute text came from DWR's June 2017 **draft** tribal guidance, so check it against leginfo.
- The ONA watershed emergency resolution and media release PDFs returned 404. The event is confirmed through IndigiNews.
- The repo doc says Splatsin's lands page lists the Territorial Water Manager role. My fetch found no mention; the role is confirmed by PSF.
- Not found: Mechoopda 450-acre date, Skwlax and Paskenta and Picayune agriculture, Tachi Farms crops and acreage, the Neskonlith CCP (404), and a 2026 USDA IAG round.
- CNRA dates the Tule River return to 2023 in one place; the Governor's release says 29 Oct 2025.
- Acreage for Yocha Dehe differs by source (3,000 farmed acres on its own page; 17k–25k elsewhere).
- Secwépemc and NRCS plant facts are [S]. Don't quote them on screen without reading the books.

## SOURCES (all accessed 2026-11-15)
- https://splatsin.ca/your-government/land
- https://psf.ca/blog/smarter-drought-monitoring-for-salmon/
- https://www.fraserbasin.bc.ca/_Library/TR_SWC/SWC_Annual_Report_2024-25_WEB.pdf
- https://syilx.org/?p=5013
- https://indiginews.com/?p=38618
- https://thetyee.ca/News/2026/09/08/Fish-Go-Blind-BC-Droughts/
- https://news.gov.bc.ca/releases/2026WLRS0042-000965
- https://news.gov.bc.ca/releases/2023FOR0052-001305
- https://bcafn.ca/sites/default/files/2022-04/BCFNCSAP%20Final%20Draft%20(22April2022).pdf
- https://newrelationshiptrust.ca/splatsins-path-to-food-sovereignty/
- https://adamslakeband.org/wp-content/uploads/2016/09/LUP-Phase-II-final-final-report.pdf
- https://adamslakeband.org/home/sfc-communal-fishing-report-for-2019
- https://shuswapnation.org/fisheries/
- https://syilx.org/wp-content/uploads/2025/07/Declining-Salmon-Returns-2025-Community-Notice_July-21-25.pdf
- https://youngagrarians.org/event-recap-farm-tour-at-sun-valley-ranch-with-okanagan-indian-band/
- https://www.colusa-nsn.gov/farming/
- https://www.colusa-nsn.gov/wp-content/uploads/2026/05/NT55685-FONSI-FTT-Wortham-519-Initial.Finalized-5.19.26.pdf
- https://yochadehe.gov/farm-ranch/
- https://yochadehe.gov/culture/language/
- https://yochadehe.gov/heritage/our-story/
- https://yologroundwater.specialdistrict.org/board-members
- https://yolocounty.gov/home/showpublisheddocument/77166/638222718870300000
- https://www.waterboards.ca.gov/sgma/docs/tulare-lake/202403-tulare-lake-pbh-final-staff-report-appendix-c.pdf
- https://www.western-water.com/2024/06/13/california-aids-tachi-yokut-tribe-with-water-transfer-deal/
- https://water.ca.gov/News/News-Releases/2024/Jun-24/California-and-Tribal-Partners-Secure-Critical-Water-Supply-to-Support-Native-American-Farmers
- https://www.tachi-yokut-nsn.gov/epa-center
- https://www.gov.ca.gov/2025/10/29/tule-river-indian-tribe-of-california-reclaims-over-17000-acres-and-reintroduces-tule-elk-on-ancestral-land/
- https://www.congress.gov/119/bills/s689/BILLS-119s689rs.htm
- https://resources.ca.gov/Newsroom/Page-Content/News-List/Mechoopda-Indian-Tribe-Reclaims-450-Acres
- https://capitalrivers.com/mechoopda-tribe-land-return/
- https://waterboards.ca.gov/sgma/docs/chowchilla/202504-chowchilla-staff-assessment.pdf
- https://cawaterlibrary.net/wp-content/uploads/2018/03/GD_Tribal_Final_2017-06-28.pdf
- https://sgma.water.ca.gov/portal/
- https://www.cdfa.ca.gov/tribal_food_sovereignty/
- https://sgc.ca.gov/grant-programs/tribal
- https://www.bia.gov/service/tcr-annual-awards-program
- https://www.bia.gov/service/water-management-planning-and-pre-development-program
- https://www.epa.gov/tribal-pacific-sw/r9-gap-funding
- https://www.nifa.usda.gov/grants/programs/federally-recognized-tribes-extension-program
- https://www.usda.gov/iag
- https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives/idaho/environmental-quality-incentives
- https://www.usbr.gov/native/
- https://www.firstnations.org/programs/california-tribal-fund/
- https://agriculture.canada.ca/en/programs/indigenous-pathfinder-service
- https://www.rcaanc-cirnac.gc.ca/eng/1481305681144/1594738066665
- https://www.rcaanc-cirnac.gc.ca/eng/1509728370447
- https://www.dfo-mpo.gc.ca/fisheries-peches/initiatives/fish-fund-bc-fonds-peche-cb/index-eng.html
- https://newrelationshiptrust.ca/indigenous-food-security-and-sovereignty/
- https://iafbc.ca/wp-content/uploads/2022/09/IFSAP-Program-Guide_Web_Sept_FINAL.pdf
- https://iafbc.ca/indigenous-food-systems-and-agriculture-skills-and-training-program/
- https://www.fcc-fac.ca/en/financing/indigenous-financing
- https://science.nasa.gov/earth-science/earth-action
- https://www.earthdata.nasa.gov/data/projects/arset
- https://wwao.jpl.nasa.gov/water-portfolio/water-projects/nasa-navajo-drought-severity-tool-user-guide
- https://www.climatehubs.usda.gov/sites/default/files/Co-Developing_the_Drought_Severity_Evaluation_Tool_for_Use_on_the_Navajo_Nation.pdf
- https://www.nasa.gov/nasa-engages-with-tribes-through-scientific-collaboration/
- https://wwao.jpl.nasa.gov/documents/115/WWAO-Annual-Meeting-Presentation-2024-mccullum-nasa-ea-05-01-24.pdf
- https://www.epa.gov/system/files/documents/2025-05/2025-r9-tribal-cwa-workshop-presentation-5-supporting-klamath-river-restoration.pdf
- https://firelight.ca/news/2026-indigenous-mapping-workshop
- https://2021.spaceappschallenge.org/challenges/statements/space-for-change/teams/bioshi/project/
- https://www.gida-global.org/careprinciples
- https://ethnobiology.org/publications/contributions/secwepemc-people-and-plants-research-papers-shuswap-ethnobotany
- https://shuswappassion.ca/history/the-secwepemc-use-of-wild-plants/
- https://www.nrcs.usda.gov/sites/default/files/2023-01/Native_Uses_of_Native_Plants-revised_2018-web.pdf
- https://firms.modaps.eosdis.nasa.gov/
- https://www.mtbs.gov/
- https://nsidc.org/data/mod10a1
- https://catalogue.data.gov.bc.ca/dataset/bc-wildfire-fire-perimeters-historical
- https://www2.gov.bc.ca/gov/content/sports-culture/recreation/fishing-hunting/hunting/regulations-synopsis
- https://wildlife.ca.gov/Hunting/Deer/Zones
- https://wildlife.ca.gov/Hunting/Elk
- https://wateroffice.ec.gc.ca/report/real_time_e.html?stn=08LE021
- https://appeears.earthdatacloud.nasa.gov/
