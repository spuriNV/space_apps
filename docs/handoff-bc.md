# Handoff: the BC example field (`bc_salmon_river_forage`)

Branch `wip/bc-field`, paused 15 Nov 2026 so the work can move to another computer. Nothing here is on `main` yet and the live site is unchanged.

## The task

Add a real British Columbia forage field in the Salmon River / Shuswap area, the 2023 irrigation-order story. It should be served by the API like the California fields, with `region: "bc"`, and every California-only piece should be labelled "not available in BC". The task also covers:
- BC rotations from planner-spec Appendix A;
- `docs/bc-first-nations.md`, on reserve land and data sovereignty. The example is built on non-reserve farmland.

## Done (committed on this branch)

| What | Where |
|---|---|
| Registry is region-aware. `fields()`/`ids()` default to `region="ca"`, so no California pipeline sees the BC field. `region=None` gives every field. `FIELDSHIFT_FIELDS` can name a BC field. Adds `region(fid)`; `template()` reads the registry `template` key. | `backend/fields/fieldreg.py` |
| BC entry under a new top-level `fields_other_regions` array, so the CA scripts that read `doc["fields"]` directly are untouched. The entry has `region: "bc"`, `county` (Columbia-Shuswap, StatCan census division 5939), `eccc_stations`, `water_context` (the 2023 order), and `not_available` (a reason each for OpenET, CIMIS, insurance/RMA, SGMA, CDL, soil survey, outlook, ML calendar). | `backend/fields/registry.json` |
| `backend/field` can see a BC field when `FIELDSHIFT_FIELDS` names it (one line). | `backend/field/fieldshift_field/common.py` |
| POWER range check widened for BC cold (T2M down to -50 C). Shuswap winters failed the CA-tuned -30 C limit. | `backend/regional/src/fetch_power.py` |
| New chunk `backend/bc/` (uv project) with `common.py`, `fetch_eccc.py`, `aci.py`, `select_field.py`, `crop_history.py`, `fetch_soilgrids.py` (written, not yet run to completion) | `backend/bc/` |
| Field outline and 10 km training box | `backend/field/polygons/bc_salmon_river_forage{.geojson,_training_box.json}` |
| AAFC crop history in the CDL `crop_history.json` shape | `backend/field/out/bc_salmon_river_forage/crop_history.json` |
| Caches: `eccc`, `aci` (+ legend and meta), `power`, `grace`, `reserves_nearby.json`. `rasters/` is git-ignored. | `data/cache/bc_salmon_river_forage/` |

## The field

**Location**
- Centroid 50.6434 N, -119.3826 W.
- In the Salmon Valley, inside City of Salmon Arm limits (Columbia Shuswap Regional District), about 10 km southwest of downtown Salmon Arm.
- In the lower Salmon River area covered by the 16 Aug 2023 fish population protection order M0238_2023.

**Size:** 21.5 ha (53.1 acres). That is 66% of a 33 ha private parcel.

**Outline**
- A ParcelMap BC legal parcel at least 90% inside the ALR, clipped to its stable AAFC "Pasture / Forages" pixels.
- BC has no field-boundary product like DWR / Land IQ, so this is labelled as a parcel-and-pixel outline.
- The parcel ID and owner are deliberately not stored.

**Crop history (AAFC ACI majority, purity)**

| Years | Class | Purity |
|---|---|---|
| 2009–2010 | Not mapped | – |
| 2011–2013 | Agriculture (undifferentiated) | – |
| 2014 | Pasture / Forages | 77% (21% corn) |
| 2015 | Pasture / Forages | 85% |
| 2016 | Pasture / Forages | 99% |
| 2017 | Pasture / Forages | 92% |
| 2018 | Pasture / Forages | 76% |
| 2019 | Pasture / Forages | 100% |
| 2020 | Pasture / Forages | 80% |
| 2021 | Agriculture (undifferentiated) | – |
| 2022 | Pasture / Forages | 80% |
| 2023 | Pasture / Forages | 100% |
| 2024 | Pasture / Forages | 85% (12% rye) |
| 2025 | Pasture / Forages | 99.6% |

ACI class 122 lumps alfalfa, clover, grass hay and pasture; there is no alfalfa class. ACI's BC crop-class accuracy is 88.34% for 2024 and 89.02% for 2025 (province-wide, from the ACI specification).

**Distance from reserves:** 6.5 km from the nearest reserve (Switsemalph IR No. 3, Neskonlith). The selection rule excludes anything within 1 km of a reserve.

**Other candidates:** six passed the rules; the next two are adjacent parcels of 22.0 and 15.4 ha. The scoring is in `select_field.py`.

## BC data sources: what works and what is a gap

| Source | Status |
|---|---|
| AAFC Annual Crop Inventory (crop history) | **Works.** Per-year BC zips, ~1.6 GB for 2009–2025, from `agriculture.canada.ca/atlas/data_donnees/annualCropInventory/data_donnees/tif/<year>/`. CRS EPSG:10820. Class legend is from the ISO 19131 spec PDF (transcribed in `aci.py`). Gaps: 2009–2010 do not cover this area; 2011–2013 and 2021 are "Agriculture (undifferentiated)" only. |
| ParcelMap BC parcels, ALR, Indian reserves (BC WFS `openmaps.gov.bc.ca/geo/pub/wfs`) | **Works.** Paging needs `sortBy=OBJECTID`. Layers: `WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW`, `WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS`, `WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP` (has band names). |
| ECCC daily climate (`api.weather.gc.ca/collections/climate-daily`) | **Works.** Salmon Arm CS `116FRMN`: 1991 to 13 Nov 2026, the only active station near the valley. Silver Creek `1167337`: 1991 to Oct 2021, then closed. This is the "sparse stations" gap. The API pads closed stations with empty days; `fetch_eccc.py` drops them. |
| NASA POWER | **Works.** 1981 to 12 Nov 2026. Note: the POWER cell elevation is 1025 m while the field is about 450 m, so POWER temperatures run cold; the engine should use ECCC Tmax/Tmin for ETo (see below). |
| GRACE-DA (OPeNDAP) | **Works.** 1231 weekly rows. |
| SMAP L4, IMERG, POWER NRT (`backend/nasa`) | Started, then stopped for the move. Not cached yet. |
| Sentinel-2 / Landsat field series (`backend/field timeseries`) | Started (1590 S2 items found), then stopped at 600/1590. Not cached yet. |
| SoilGrids v2 (`fetch_soilgrids.py`) | Written. The run was slow (ISRIC asks for at most 5 requests per minute; 5 points) and was stopped. Not cached yet. |
| HLS (`nasa_open`), MODIS (Planetary Computer, `backend/ai/fieldshift_ai/modis_pc.py`) | Not started. They need the field's S2 cache and grid first. |
| **Gaps, by design (in `registry.json` `not_available`)** | No OpenET. No field-scale soil API (SoilGrids is a 250 m model; drainage class, hydrologic group and AWC stay unknown). Sparse stations. No CDL (AAFC instead). No RMA insurance. No CA water district / SGMA / CDEC. No NOAA outlook / USDM. CA-trained ML calendar not run. |

## Left to do

1. **Fetch the remaining data** (commands below): the S2/Landsat series, then detector and grid; SMAP L4, IMERG and POWER NRT; SoilGrids; then HLS / NASADEM (`nasa_open`) and optionally `build_calendar_hls.py`.
2. **Engine BC rotations.** Add these to `backend/engine/src/rotation_engine/build_data.py`, then regenerate `crops.json`/`strategies.json` and check the CA entries are byte-identical. The designs are below.
3. **Engine BC adaptations** (keep them small):
   - `weather.py`: `load_station_precip` / `station_temps` should fall back to `data/cache/<id>/eccc.parquet`, which has the same columns as `ncei.parquet`: `date`, `prcp_mm`, `tmax_c`, `tmin_c`, `station`.
   - Add a BC post-pass in `score()` for region `bc` that rewrites the US-only text:
     - `risk_profile` RMA → "not available in BC";
     - `funding` EQIP → BC programs, unverified;
     - `income` NASS/AMS → not available;
     - OpenET blocked → "OpenET not available in BC";
     - `_psources` labels → ECCC.
   - Add `"alfalfa_hay_bc": {"Pasture / Forages"}` to `observed.BASELINE_CDL` (flagged: the ACI class is not alfalfa-specific).
   - Run with `FIELDSHIFT_FIELDS=bc_salmon_river_forage uv run rotation-engine bc_salmon_river_forage`.
4. **API payloads.** Write a `backend/bc/build_api.py` to produce `backend/api/out/bc_salmon_river_forage/{location,daily,features_weekly,nasa_series}.json`, reusing `backend/api/nasa_build.py` (`load`, `nasa_series`, `nasa_datasets`).
   - `location.json` follows `schemas/location.schema.json`: `region_adapter: "bc"` is already in the enum.
   - The soil block comes from SoilGrids: `mukey`/`muname` give the source; drainage and hydrologic group are "unknown".
   - Add `data_gaps` from the registry's `not_available`.
   - The schema needs small additions: `id` enum, and `ECCC` in `stations.network`.
   - Field news: derive it from `backend/news/out/bc_opener.json` into `backend/news/out/bc_salmon_river_forage.json`, so the `{t}` template fallback never serves California news.
5. **`backend/api/app/main.py`.** Keep it small and pull first; other agents edit this file.
   - `PRESETS = fieldreg.ids(region=None)`.
   - `/api/locations` uses `fieldreg.fields(family, county, region=None)` and adds a `region` facet.
   - `_real_only` returns 404 with the registry's `not_available[kind]` text for BC (openet, insurance, outlook, calendar_ml, stress, water_seen).
6. **`backend/api/checks/check_api.py`.**
   - The registry block currently asserts 14 fields, and its core-route loop expects 200 on `/openet`, `/insurance` and similar for every field.
   - Add a BC section: core routes 200 + schema; CA-only routes 404 with "not available in BC".
   - Keep the CA count checks on `region="ca"`.
   - Then run `cd backend/api && uv run python checks/check_api.py` and `cd frontend/app && VITE_API_BASE=/api npm run build`.
7. **`backend/bc/checks/run_checks.py`** (PASS/FAIL), `backend/bc/README.md`, and `docs/bc-first-nations.md` (findings below).
8. **Merge to `main`.** Use explicit paths, check `git diff --cached --name-only`, `git pull --rebase origin main`, plain messages, and never force-push.

### BC rotations to add (Appendix A, sources read)

**Sources**
- Kamloops District Forage Manual (BC Ministry of Agriculture, 2002), archived at https://bac-lac.wayback.archive-it.org/web/20080212123631/http://www.al.gov.bc.ca/forage/publications/documents/kamloops_forage_manual.pdf
  - Zone 2: "Although 3 cuts of alfalfa are possible in this area, 2 cuts are more typical with the aftermath being grazed in late fall".
  - A 5-year stand is "the typical length of a stand of irrigated alfalfa".
  - Systems: "Continuous alfalfa, five year cycle, with 20 per cent reseeded each year", and "A five year cycle, with one-half of new seeding area in annual crops (e.g. barley/annual ryegrass)".
  - The 2-cut budget gives 2.0 + 1.5 = 3.5 ton/acre of hay.
  - It is the Kamloops district, the neighbour of the Shuswap, so applying it here is **assumed**.
- BC Drought Management Factsheet No. 6, "Alternate forage crops when irrigation water is limited" (Order No. 665.000-6, Oct 2005), https://www.irrigationtoolbox.com/ReferenceDocuments/Extension/BCExtension/665000-6.pdf
  - Cereals are "the most commonly grown alternative forage crops".
  - Fall rye and fall triticale: high drought tolerance, low water use; they need fall moisture to establish and must be harvested before heading.
  - Barley is "most commonly grown for cereal silage", "about 100 days"; "one crop of barley silage may only require about 15 inches of water for a 3 to 4 ton/acre yield", against about 36 inches for full-season alfalfa.
- BF04 fact sheet "Non-bloat legumes" (BC Climate Change Adaptation, 2023), https://www.bcclimatechangeadaptation.ca/app/uploads/BF04-FactSheet-Non-bloat-Legumes-2023.pdf
  - Sainfoin is drought tolerant and suits 300–600 mm precipitation and lighter, well-drained soils, with no wet feet.
  - "Under dryland production, sainfoin generally provides 1 cut per season but it can provide 2 cuts under irrigation."
  - Pair it with bunchgrasses (meadow brome, hybrid brome, Russian wildrye, timothy).
  - It was written for the Bulkley-Nechako and Fraser-Fort George regions (northern BC), so applying it to the Shuswap is **assumed**.
- FAO-56 (checked on the FAO page). Table 12: alfalfa averaged 0.40/0.95/0.90; barley 0.3/1.15/0.25; winter wheat with frozen soils 0.4/1.15/0.25–0.4; clover hay averaged 0.40/0.90/0.85. Table 11: alfalfa total season runs "last -4 C in spring until first -4 C in fall" (init 10, dev 30); barley at 35–45° latitude, Mar/Apr planting 20/25/60/30; winter wheat Idaho Oct 160/75/75/25.
- -4 °C dates computed from ECCC Silver Creek 1991–2021: median last spring -4 °C is day 100 (10 Apr), median first fall -4 °C is day 299 (26 Oct). Salmon Arm CS gives days 84 and 307.

**Planned calendars.** New crops: `alfalfa_hay_bc`, `barley_silage_bc`, `fall_cereal_silage_bc`, `sainfoin_grass_bc`. Every stage split and yield not quoted above is **U**.

- **`bc0_alfalfa` (baseline):** irrigated alfalfa-grass, 2 cuts (Jun, Aug), steady-state 1-year cycle.
  - Entry `10-26`→`10-26` with `stage_override` ini 176 (dormant plus FAO init 10), dev 30, mid 129, late 30.
  - Yield about 6,900 kg DM/ha (5,000–8,500), from the Kamloops 3.5 ton/acre at an assumed 88% DM.
- **`bc1_barley_break`:** 5-year cycle (Kamloops system 2).
  - Year 1: barley silage `05-01`→`08-05` (scaled FAO 20/25/60/30, harvested before a mid-August order).
  - Alfalfa reseeded `08-15`, establishing to `10-26` with `cover_override`.
  - Established `10-26`→`10-26` in years 1–4.
  - Old stand dormant `10-26`→`04-20` in year 5 (wraps), terminated in spring.
  - Calendar note: the late-summer seeding needs August water, which an order year would not allow.
- **`bc2_fall_cereal_silage`:** 5-year cycle, one year in five in fall cereal (the "1/5 of stand" idea on one field).
  - Last alfalfa year cut twice, terminated `08-20`.
  - Fall rye or triticale `08-25`→`06-05` (wraps), adapted from FAO winter wheat Idaho: ini 205, dev 55, mid 24.
  - Alfalfa reseeded `06-15`; established `10-26` years 1–3; then `10-26`→`08-20` in year 4.
- **`bc3_sainfoin_grass`:** dryland sainfoin-meadow brome (`irrigated: false`), 1 cut in July.
  - Kc proxy: FAO clover hay averaged (assumed).
  - Yield about 2,500 kg DM/ha (1,500–4,000, U).
  - Constraint: needs lighter, well-drained soil (check the SoilGrids texture).

## First Nations findings (for `docs/bc-first-nations.md`)

**Reserves near the valley** (BC WFS `ADM_INDIAN_RESERVES_BANDS_SP`, queried 15 Nov 2026; list in `data/cache/bc_salmon_river_forage/reserves_nearby.json`)
- **SALMON RIVER 1 (SPLATSIN):** Splatsin, band 600, 1,583 ha, at about 50.47–50.52 N on the lower Salmon River, 14.2 km from the field. Splatsin's land page says IR1 is "mostly used for agriculture, grazing and forestry" (https://splatsin.ca/your-government/land).
- **Neskonlith (band 690):** Neskonlith 1, Neskonlith IR No. 2, Switsemalph IR No. 3 (6.5 km from the field).
- **Adams Lake (band 684):** Switsemalph 6 and 7, Sahhaltkum 4 and others.
- **Skwlax te Secwépemc (band 689):** Quaaout 1, North Bay 5 and others.
- **Okanagan Indian Band (Syilx, band 616):** Okanagan 1, which reaches the Salmon River side; Otter Lake 2, Harris 3, Swan Lake 4.
- **Splatsin is the Nation whose reserve sits on the lower Salmon River, not Neskonlith.**

**Farmland visible in AAFC data:** not computed. Whether reserve land shows ACI forage was deliberately left un-analysed. Only a yes/no count, done with care, would belong in the doc; the plan is to not analyse reserve land at all and to say so.

**Water and salmon interest**
- Splatsin has a Territorial Water Manager. Its Yucwmenlúcwu staff and the Secwépemc Fisheries Commission monitored low-flow fish passage on the lower Salmon River in 2025 (https://psf.ca/blog/smarter-drought-monitoring-for-salmon/).
- The Syilx Okanagan Nation objected in 2026 that a Salmon River ("akscʷin") order was rescinded "without consultation" (https://syilx.org/?p=5013).
- New Salmon River orders were issued in July–Aug 2026, with 456 licence holders told to stop irrigating (https://news.gov.bc.ca/releases/2026WLRS0042-000965).

**Boundary data**
- NRCan "Aboriginal Lands of Canada Legislative Boundaries" (CLSS), https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067
- CLSS map browser, https://clss.nrcan-rncan.gc.ca/mb-nc/en
- BC catalogue entry, https://catalogue.data.gov.bc.ca/dataset/8efe9193-80d2-4fdf-a18c-d531a94196ad

**Principles and guidance**
- OCAP® (FNIGC): https://fnigc.ca/wp-content/uploads/2022/10/OCAP_Brochure_20220927_web.pdf. Cite it as "OCAP® is a registered trademark of the First Nations Information Governance Centre (FNIGC)".
- CARE (GIDA).
- TCPS 2 Chapter 9 (https://ethics.gc.ca/eng/tcps2-eptc2_2022_chapter9-chapitre9.html):
  - Art. 9.1 requires engagement for research on reserve lands.
  - Art. 9.21 exempts publicly available data, but OCAP and CARE go further.
- No FNIGC guidance specific to satellite imagery was found.

**Contacts to suggest** (public pages only; no names)
- Splatsin Lands Department / Territorial Water Manager: https://splatsin.ca/your-government/land
- Neskonlith: https://neskonlith.net/contact-us/
- Adams Lake (Lands, Natural Resources): https://adamslakeband.org/contact-us/
- Okanagan Indian Band: https://okib.ca/services/administration
- Shuswap Nation Tribal Council and Secwépemc Fisheries Commission: https://shuswapnation.org/fisheries/

**Agriculture programs**
- BC Indigenous Food Systems and Agriculture hub (with the BC Indigenous Pathfinder Service): https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood/indigenous-food-systems-and-agriculture
- IFSAP via IAF: https://iafbc.ca/ifsap
- AAFC Indigenous Pathfinder Service: https://agriculture.canada.ca/en/programs/indigenous-pathfinder-service
- AAFC Indigenous Agriculture and Food Systems Initiative: intake suspended.
- FCC Indigenous lending.
- **The "First Nations Agricultural Association (BC)" could not be confirmed as a current organisation.** Do not cite it as current. The First Nations Agricultural Lending Association has only 2003–2006 references.

**Approach (co-developed version)**
1. Start with Splatsin.
2. Send a plain-language note saying no reserve data has been analysed.
3. Ask for the Nation's research protocol and who decides; a Band Council Resolution or a data agreement may be needed.
4. Offer: Nation ownership of outputs, co-design, no publication without written consent, data returned or deleted on request, credit and paid time, and a community-controlled version.
5. Expect a timeline of months.

Guides:
- Kitasoo/Xai'xais "Informing Stewardship with Applied Research", https://klemtu.com/wp-content/uploads/2023/05/Informing-Stewardship-with-Applied-Research.pdf
- Secwépemc research protocol template, https://secwepemcmuseum.ca/wp-content/uploads/2024/05/Research_Protocol_September_2018.pdf

**Line for the app and the doc:** "Built to be co-developed with First Nations farmers; we'd only add a reserve field with the Nation's permission."

## Commands to resume

```sh
git fetch origin && git switch wip/bc-field && git rebase origin/main   # resolve if main moved
cd backend/bc && uv sync

# ACI zips (~1.6 GB) are not in the repo: download them, then re-clip (needed only to rebuild the outline or history)
mkdir -p /tmp/aci && cd /tmp/aci && B=https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/data_donnees/tif
for y in $(seq 2009 2025); do f=$(curl -sL "$B/$y/" | grep -o 'aci_[0-9]*_bc_v[0-9]*\.zip' | head -1); echo "$B/$y/$f"; done | xargs -P 5 -n 1 curl -sSLO
cd -  && uv run python aci.py --zips /tmp/aci && uv run python select_field.py && uv run python crop_history.py

uv run python fetch_eccc.py            # done; rerun to refresh
uv run python fetch_soilgrids.py       # ~1-2 min (5 points, rate-limited)

export FIELDSHIFT_FIELDS=bc_salmon_river_forage
(cd ../field && uv run python -m fieldshift_field.timeseries all bc_salmon_river_forage \
   && uv run python -m fieldshift_field.detector && uv run python -m fieldshift_field.grid)   # ~15-25 min
(cd ../nasa && uv run python fetch_smap_l4_opendap.py && uv run python fetch_imerg.py && uv run python fetch_power_nrt.py)  # ~30 min, needs .env
(cd ../regional/src && uv run python fetch_power.py)   # done
(cd ../nasa_open && uv run python -m nasa_open.terrain && uv run python -m nasa_open.hls)
```

A detector caveat to check: winter snow cover is masked (S2 SCL 11, Landsat bit 5), so Dec–Feb will mostly be `unknown`. That is honest, but say so in the calendar notes.
