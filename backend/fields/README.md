# backend/fields: the field registry

CropLytics now works on a list of real fields instead of two hard-wired presets. `registry.json` is that list; every chunk reads it through `fieldreg.py` (stdlib only), and `run_all.py` runs each chunk's existing per-field steps for every field that still needs them.

| File | What |
|---|---|
| `registry.json` | One entry per field: `id`, `name` / `farmer_name`, `family` (`rice` or `forage`), `county` (`fips`, `name`), `usdm_counties`, `dwr_unique_id`, `centroid`, `area_ha`, `acres`, `polygon` (path), `weather_point` (null = centroid), `ncei_stations`, `reservoirs` (CDEC), `slope_pct`, `template`, `why`, and `water` (district, SGMA subbasin, GSA, priority, probation; see below) |
| `fieldreg.py` | `ids()`, `fields(family, county)`, `get(id)`, `template(id)`, `selected()` (honours `FIELDSHIFT_FIELDS`) |
| `run_all.py` | Batch runner over every chunk's per-field steps; skips steps whose outputs exist (`--list` shows status) |
| `pick_fields.py` | One-off candidate search: DWR 2023 outlines near seed points, ranked against CDL 2008-2025 (run from `backend/field`) |
| `water_sources.py` | Looks up each field's water district, SGMA subbasin, GSA, basin priority and State Water Board status from public layers |
| `checks/run_checks.py` | PASS/FAIL per field: registry vs polygon, crop history fits the family, water lookup, every step's output |

Ids keep the original prefixes: `car_*` fields are rice and reuse the CAR0-CAR3 rotation set and the rice ML model of `car_colusa_rice`; `caf_*` fields are forage and reuse CAF0-CAF3 and the forage model of `caf_tulare_forage`. No new agronomy and no retraining.

## The 14 fields

| id | Name | County | Acres | CDL 2016-2025 | Why |
|---|---|---|---|---|---|
| `car_colusa_rice` | Rice field 4 miles east of Williams | Colusa | 148.9 | Rice, fallow 2016, 2020, 2022 | Original rice example |
| `caf_tulare_forage` | Alfalfa field 6 miles south of Hanford | Kings | 72.8 | Alfalfa with corn 2016, 2021, 2023 | Original forage example |
| `car_glenn_rice` | Rice field 3 miles southwest of Glenn | Glenn | 200.7 | Rice every year except fallow 2022 | Large Glenn check, fallowed only in the 2022 drought |
| `car_richvale_rice` | Rice field 3 miles northwest of Richvale | Butte | 66.9 | Rice all 18 CDL years | Never fallowed, even in 2022 (Feather River water) |
| `car_biggs_rice` | Rice field 2 miles northwest of Biggs | Butte | 152.7 | Rice, rotation fallow 2017, 2019, 2024 | A recent (2024) bare year, not tied to drought |
| `car_robbins_rice` | Rice field 1 mile northeast of Robbins | Sutter | 143.8 | Rice, sunflower in 2022 (and 2014) | A dry-year rotation crop instead of bare fallow |
| `car_zamora_rice` | Rice field 6 miles north of Zamora | Yolo | 145.7 | Rice, fallow 2022 and 2024 | West-side Yolo rice |
| `car_grimes_rice` | Rice field 4 miles west of Grimes | Colusa | 150.8 | Rice, fallow 2017, 2020, 2021, 2022 | Sits out dry years most often |
| `caf_corcoran_forage` | Forage field 4 miles south of Corcoran (Tulare Lake bed) | Kings | 140.1 | Alfalfa, wheat/corn, idle 2023-2024, alfalfa 2025 | In the 2023 Tulare Lake re-flooding area |
| `caf_goshen_forage` | Alfalfa field 2 miles southwest of Goshen | Tulare | 74.1 | Alfalfa with single corn years | Classic dairy rotation |
| `caf_tipton_forage` | Forage field 2 miles southeast of Tipton | Tulare | 37.7 | Alfalfa 2019-2023, then wheat/corn double crop | Switches between alfalfa and double-cropped forage |
| `caf_riverdale_forage` | Alfalfa field 2 miles northwest of Riverdale | Fresno | 97.0 | Alfalfa, wheat 2020, triticale 2025 | Fallowed in the 2013-14 drought |
| `caf_elnido_forage` | Alfalfa field 2 miles northeast of El Nido | Merced | 67.3 | Alfalfa, wheat 2017, cotton 2018 | Highest purity of the Merced candidates |
| `caf_newman_forage` | Alfalfa field 3 miles north of Newman | Stanislaus | 100.2 | Alfalfa with corn and oats breaks | West-side Stanislaus |

How the twelve were picked (`pick_fields.py`, same method as `backend/field/select_fields.py`): DWR / Land IQ Statewide Crop Mapping 2023 field outlines within about 3.5 km of 23 seed points, 15-120 ha, single part; CDL 2008-2025 majority class and purity inside each outline. Rice rule: CDL Rice in at least 6 of 2016-2025, every other year fallow except at most one, Rice in 2025. Forage rule: Alfalfa in at least 3 and forage (alfalfa, corn, winter-grain/corn double crop, hay, small-grain forage) in at least 7 of 2016-2025, forage in 2024 or 2025. Ranked by mean purity; then one per seed was chosen by hand for variety (fallow patterns, soils, districts). The Tulare Lake bed had no field that passes the forage rule in 2023 (the flooded fields were idle), so `caf_corcoran_forage` was chosen from a relaxed list: forage before and after, CDL idle in 2023-2024, DWR left it unclassified in 2023. OPERA DSWx confirms the flood: water on more than half the field in 31 of 32 clear scenes from 13 Mar to 30 Jun 2023.

Soils differ (SSURGO dominant map unit): Willows clay (Glenn), Esquon-Neerdobe clay (Richvale, Biggs), Clear Lake clay (Robbins), Sacramento clay (Zamora), Willows silty clay (Grimes), Gepford clay, lake-bed (Corcoran), Tagus loam (Goshen), Akers saline-sodic sandy loam (Tipton), Chino loam (Riverdale), Fresno saline-sodic loam (El Nido), Vernalis clay loam (Newman).

## Water source (`water` in each entry)

`water_sources.py` queries DWR's public ArcGIS layers at the polygon centroid (no key): water district (`i03_WaterDistricts`), Bulletin 118 subbasin, SGMA 2019 basin priority, critically overdrafted basins, GSA (`i03_Groundwater_Sustainability_Agencies`), GSP status from DWR's assessment (`i03_Groundwater_Sustainability_Plan_Areas`) and adjudicated areas. The State Water Board status (probationary / under evaluation / returned to DWR) is read from the basin list at https://www.waterboards.ca.gov/water_issues/programs/sgma/groundwater_basins/. Each item stores its source URL and lookup date. All layers answered on 14 Nov 2026. `caf_elnido_forage` has no water-district polygon at its centroid in the DWR layer, so `district` is null; nothing is filled in.

## Coarse cells are fetched once

POWER (0.5 x 0.625 deg): `fetch_power.py` copies the series to fields in the same cell (Glenn, Richvale, Biggs, Grimes; Robbins, Zamora; Corcoran, Goshen, Riverdale). IMERG (0.1 deg), GRACE-DA (0.25 deg) and SMAP L4 (9 km, OPeNDAP): one hyperslab per granule for all fields. SMAP L3, MODIS, ECOSTRESS: one AppEEARS point task for all fields. DSWx: each WTR tile is downloaded once and masked for every field it covers.

## Adding a field

1. Find a candidate: add a seed `(id, family, county, lon, lat)` to `SEEDS` in `pick_fields.py` and run it from `backend/field`:
   `uv run python ../fields/pick_fields.py --out /tmp/cand.json --cdl-dir /tmp/cdl <seed>`. Pick a DWR `UniqueID` whose CDL history fits the family.
2. Add an entry to `registry.json` (copy a new-field entry): id `car_<place>_rice` or `caf_<place>_forage`, `family`, `county`, `usdm_counties`, `dwr_unique_id`, `centroid`, `area_ha`, `acres`, `polygon`, `reservoirs`, `cdl_half_box_m: 2000`, `weather_point`/`ncei_stations: null`, `template`, `why`.
3. `python3 backend/fields/run_all.py --fields <id>` (needs the repo-root `.env` for the NASA and OpenET steps). It checks the OpenET quota first (one query per field). The NOAA stations it picks are written back into the registry.
4. `python3 backend/fields/checks/run_checks.py` and `cd backend/api && uv run python checks/check_api.py`.
5. Commit the registry, `backend/field/polygons/<id>*`, the chunk `out/<id>/` folders and `data/cache/<id>/` (not `data/cache/<id>/rasters/`, which is git-ignored).

## Status (15 Nov 2026, paused)

Done for all 12 new fields: registry entry, DWR polygon, CDL crop history, POWER, NOAA stations, SSURGO, USDM, CDEC, water source, OpenET (12 queries, 17 of 100 used this month), RMA, IMERG, GRACE, DSWx, outlook CPC and water-now.
Done for 8 (`car_glenn_rice`, `car_biggs_rice`, `car_robbins_rice`, `car_zamora_rice`, `car_grimes_rice`, `caf_goshen_forage`, `caf_tipton_forage`, `caf_elnido_forage`): S2/Landsat series, calendar, grid, NASADEM terrain, strategies, API payloads (served by `/api/locations`).
Remaining: S2/Landsat series for `caf_corcoran_forage` (none), `caf_newman_forage` (none), `caf_riverdale_forage` (Landsat), then calendar/grid/terrain/strategies/API for those three and `car_richvale_rice`; SMAP L4 (OPeNDAP + HTTPS streaming of ~1,200 recent granules) for all 12; `ai.*` with complete series; `outlook.history/irrigation/build`. SMAP L3, MODIS and ECOSTRESS: AppEEARS tasks (submitted 14 Nov) were still pending after 8 hours, as were the originals' tasks; rerunning the fetchers resumes the same tasks.

Resume: `python3 backend/fields/run_all.py` (skips what is done), then `python3 backend/fields/checks/run_checks.py` and `cd backend/api && uv run python checks/check_api.py`.

Data findings: one or two scenes per field give NDVI p10/p90 outside [-1, 1] at Glenn, Richvale, Robbins and El Nido (and one El Nido Landsat median of 1.81), so the backend/field check "NDVI in [-1,1]" fails there; these scenes were not filtered and should be dropped (reflectance artefacts) before the calendars are trusted for those dates.

## Limits

- The rule thresholds, rotation calendars and ML model were set on the two original fields and are reused unchanged. Every new field is outside the 10 km training box of its family's model, so its ML calendar is a transfer test (`calendar_ml.json` `method.field_in_training_box: false`).
- Engine slope stays a family placeholder (0 % rice, 0.5 % forage); NASADEM, HLS and ISS photos (`backend/nasa_open`) were not run for the new fields.
- NASS, AMS and CIMIS (county prices, hay reports, station ETo) were not fetched for the new fields.
