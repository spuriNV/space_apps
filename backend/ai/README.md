# backend/ai: bare / covered / water detector (rule vs ML) and crop-stress weeks

Owner chunk for spec B6.1 (bare-cover and transition detection, rule vs ML), B6.2 (crop-stress anomaly) and B10.1 checks 8 and 9
(the `ds` branch numbers them 7 and 8). No accounts or keys are used. Nothing trains live: models are trained offline and their
results are cached as ModelReports and JSON files the API serves.

**Credit.** The models are the merge of two pieces of work:
- **spuriNV (`ds` branch, `field_shift_ai/`)**: the B6.1 feature set, Sentinel-2 scene-classification labels at 80% pixel agreement,
  the rule / random forest / gradient boosting majority vote, 3-date smoothing and green-up / harvest logic, the "below target" badge,
  and the whole B6.2 stress model (six weekly z-scores, z-score composite vs isolation forest, both / one / none strip, plain-word
  reasons, "fallow is not stress", the evidence sentence) and the ModelReport builder. Module headers say which parts are theirs.
- **backend/ai on main**: the 10 km multi-field training sample, spatial hold-out by block, CDL crop windows and the water class, the
  ML calendar for the field, scripted and cached NASA inputs, and the API-shaped outputs.

The `ds` branch is kept unchanged as the teammate's reference. Its own run (one 200 m box at Colusa) is saved, outputs only, in
`reference/ds_colusa_box/`. The merge plan is `docs/ai-integration.md`.

## Run

```bash
cd backend/ai
uv sync
uv run python -m fieldshift_ai.sample          # 1. 150 m clusters + S2 medians -> data/cache/<id>/ai/ (network; templates only, done)
uv run python -m fieldshift_ai.modis_pc --product mod13q1 --workers 48   # 2. MODIS NDVI per cluster + field (Planetary Computer)
uv run python -m fieldshift_ai.modis_pc --product mod11a2 --workers 48   #    MODIS LST at each field
uv run python -m fieldshift_ai.inputs          # 3. both input tables per field from the caches (offline)
uv run python -m fieldshift_ai.bare_cover      # 4. B6.1: train, 3 tests, calendar_ml + transitions (~4 min per template)
uv run python -m fieldshift_ai.stress          # 5. B6.2 per field (~10 s per field)
uv run python checks/run_checks.py             # PASS/FAIL lines, local files only
```
Steps 1-2 use the network; 3-5 read only cached files and never modify them. All steps take field ids; with none they run every field in
`backend/fields/registry.json` (`FIELDSHIFT_FIELDS` limits the list). `bare_cover --calendar-only` refits the deployment models (same data,
seed 0) and rewrites only `calendar_ml.json` and `transitions.json`.

**Fields.** The two presets (`car_colusa_rice`, `caf_tulare_forage`) have their own 10 km training sample and are trained and tested.
The other registry fields reuse their family's models (`template`: rice -> Colusa, forage -> Tulare/Kings) without retraining; their
`models.json` copies the template's reports with a note and the field's distance from the training box. Each field gets its own stress
run on its own inputs.

## Inputs (`fieldshift_ai/inputs.py`, all cached and scripted on main)

`data/cache/<id>/ai/inputs.meta.json` lists the source and date coverage of every column.

| Column | Source |
|---|---|
| Reflectance, NDVI/NDWI/BSI, SCL fractions per date (clusters) | Sentinel-2 L2A via Planetary Computer (`sample.py`), SCL 4/5/6 over clear pixels |
| NDVI/NDWI/BSI, SCL fractions per date (field) | backend/field `s2.parquet` (SCL fractions per polygon); HLS L30/S30 from backend/nasa (LP DAAC) and backend/nasa_open |
| `modis_ndvi_clim` (B6.1 feature `ndvi_anom_modis`) | MOD13Q1.061 at every cluster and the field (`modis_pc.py`), 2001-2015 same-DOY mean: before every label and test year |
| `ndvi_modis` (B6.2, 2000-) | MOD13Q1 at the field: backend/nasa's AppEEARS file when cached, else `modis_pc.py` |
| `lst_k`, `lst_minus_tmax_c` | ECOSTRESS LST (backend/nasa) when cached, else MODIS MOD11A2 LST (`modis_pc.py`); minus station Tmax |
| `esi` | ECOSTRESS ESI when cached, else ECOSTRESS JET ETdaily / Penman-Monteith ETo (the same ratio; AppEEARS bundle), else OpenET monthly ET / ETo |
| `smap_pct` | SMAP L4 root-zone percentile (backend/nasa); GRACE-DA root-zone percentile where SMAP is missing |
| `imerg_7d_mm`, `imerg_30d_mm` | GPM IMERG V07 (backend/nasa) |
| `t2m_max_c`, `tmax_7d_c` | NOAA NCEI stations (mean of the field's stations), NASA POWER where none reports |
| `eto_mm` | FAO-56 Penman-Monteith, backend/engine `weather.pm_eto` (station T, POWER radiation, humidity, wind) |
| `cdl_class`, `crop`, `in_season` | backend/field `crop_history.json` / cluster CDL; season ISO weeks rice 23-39, forage 14-39 |
| `opera_water_frac` | NASA OPERA DSWx-HLS (backend/nasa), independent water check |
| `usdm_d3plus_pct` | US Drought Monitor county statistics, % of the county in D3-D4 (cached) |
| Field geometry | backend/field/polygons (real DWR outlines) |

## B6.1: bare / covered / water

### Labels (merged)
Per Sentinel-2 date, in priority order (spuriNV's scheme, with a water class added):
1. **Sentinel-2 scene classification (SCL)**: at least 80% of the clear pixels are water (SCL 6), vegetation (4) or not vegetated (5) -> water / covered / bare. Weight 1.
2. **CDL fallow year** (class 61) -> bare all year. Weight 1.
3. **CDL season windows** (`common.CROP_WINDOWS`, all U) -> bare / covered. Weight 0.5 (weak).

At Colusa 95% and at Kings 99% of the training labels come from SCL. So accuracy against the training labels mostly measures
**agreement with ESA's classifier**, which reads the same reflectance the models read. That is why the headline metric is scored
against the **crop-map labels only** (CDL fallow years and season windows; covered vs not covered), which do not come from the imagery.

### Features and models
- **Features:** NDVI, NDWI, BSI; trailing 30/60-day NDVI mean/min/max; 30-day NDVI slope; NDVI minus the MODIS 2001-2015 same-DOY
  normal; DOY sin/cos; 7-day station Tmax; 7-day IMERG rain; soil-moisture percentile. No SCL column is a feature (they define the labels).
- **Ablations:** `full` adds EVI, NBR2 and red/NIR/SWIR reflectance (clusters only; the field series stores no bands); `noseason`
  drops DOY, Tmax, rain and soil moisture.
- **Models:** `RandomForestClassifier(300, class_weight="balanced")` and `HistGradientBoostingClassifier(class_weight="balanced")`,
  random_state 0, label weights as sample weights. Fixed before any test was seen; nothing tuned.
- **Rule:** backend/field B5.1 (NDVI < 0.20 bare, > 0.35 covered, else "thin cover"; NDWI > 0.3 or SCL water > 50% water). Its thin
  cover is scored as covered and shown only on the rule strip.
- **Vote:** majority of rule / RF / HGB (rule thin cover abstains); no majority -> highest mean RF+HGB probability.
- **Smoothing and dates:** 3-date mode; green-up = first of 3 covered dates after bare or water; senescence/harvest = first of 2
  non-covered dates after cover; **cutting** = on alfalfa or hay years, a drop with cover back within 45 days (not a harvest; the
  regrowth is not a green-up).

### Tests
- **Unseen fields (headline):** GroupKFold(4) over the 16 blocks of 2.5 km, all years; a cluster is only ever in one test fold.
- **Unseen years:** train 2016-2022, test 2023-2025 (the `ds` design, on the multi-field sample).
- **2022:** train every other year, test 2022. At Colusa 92% of the 2022 crop-map labels are bare (drought fallow): an easy test, never quoted as the headline.
- **Agreement with Sentinel-2 classification:** on the unseen-field predictions; "agreement", not accuracy.
- **Transition error:** vs the midpoint of the crop-map window gap (crude but independent), and vs the label sequence's own transitions (the `ds` design; circular, since the labels are mostly SCL).
- **The field itself:** it is never training data (nearest cluster 241 m / 150 m away). Its calendar is checked against its own
  Sentinel-2 classes and, for water, against NASA OPERA DSWx, which no model ever sees.

### Results (14 Nov 2026)

| Field | Test | Metric | Rule | RF | HGB | Vote |
|---|---|---|---|---|---|---|
| Colusa rice | **Unseen fields** (headline) | accuracy vs crop map | 0.804 | 0.980 | 0.981 | 0.980 |
| Colusa rice | **Unseen fields** (headline) | F1(bare) vs crop map | 0.834 | 0.985 | 0.986 | 0.985 |
| Colusa rice | **Unseen fields** (headline) | agreement with Sentinel-2 classes | 0.833 | 0.994 | 0.994 | 0.996 |
| Colusa rice | **Unseen fields** (headline) | accuracy vs merged labels | 0.805 | 0.980 | 0.981 | 0.982 |
| Colusa rice | **Unseen fields** (headline) | transition error vs crop-map midpoints (days) | 29.6 | 25.1 | 25.0 | 25.0 |
| Colusa rice | **Unseen fields** (headline) | transition error vs label sequence (days) | 6.9 | 1.2 | 1.3 | 1.3 |
| Colusa rice | Unseen years 2023-25 | accuracy vs crop map | 0.795 | 0.983 | 0.984 | 0.983 |
| Colusa rice | Unseen years 2023-25 | F1(bare) vs crop map | 0.797 | 0.986 | 0.987 | 0.986 |
| Colusa rice | 2022 (easy, mostly bare) | accuracy vs crop map | 0.703 | 0.942 | 0.943 | 0.941 |
| Colusa rice | 2022 (easy, mostly bare) | F1(bare) vs crop map | 0.822 | 0.970 | 0.970 | 0.969 |
| Colusa rice | 2022 (easy, mostly bare) | share of bare labels | 0.920 | 0.920 | 0.920 | 0.920 |
| Colusa rice | The field itself (never trained on) | agreement with its S2 classes | 0.868 | 0.983 | 0.985 | 0.985 |
| Colusa rice | The field itself | transition error vs its S2 classes (days) | 9.2 | 6.6 | 6.9 | 6.6 |
| Colusa rice | The field itself | OPERA water scenes found | 6/20 | 5/20 | 7/20 | 7/20 |
| Colusa rice | Unseen fields, RF ablation `full` | accuracy vs crop map / S2 agreement | | 0.980 / 0.998 | | |
| Colusa rice | Unseen fields, RF ablation `noseason` | accuracy vs crop map / S2 agreement | | 0.980 / 0.992 | | |
| Kings forage | **Unseen fields** (headline) | accuracy vs crop map | 0.854 | 0.848 | 0.853 | 0.853 |
| Kings forage | **Unseen fields** (headline) | F1(bare) vs crop map | 0.714 | 0.761 | 0.766 | 0.767 |
| Kings forage | **Unseen fields** (headline) | agreement with Sentinel-2 classes | 0.854 | 0.997 | 0.996 | 0.996 |
| Kings forage | **Unseen fields** (headline) | accuracy vs merged labels | 0.854 | 0.993 | 0.994 | 0.993 |
| Kings forage | **Unseen fields** (headline) | transition error vs crop-map midpoints (days) | 20.6 | 24.7 | 24.7 | 24.6 |
| Kings forage | **Unseen fields** (headline) | transition error vs label sequence (days) | 6.2 | 1.8 | 1.7 | 1.7 |
| Kings forage | Unseen years 2023-25 | accuracy vs crop map | 0.860 | 0.856 | 0.858 | 0.859 |
| Kings forage | Unseen years 2023-25 | F1(bare) vs crop map | 0.715 | 0.772 | 0.775 | 0.776 |
| Kings forage | 2022 (easy, mostly bare) | accuracy vs crop map | 0.776 | 0.755 | 0.755 | 0.756 |
| Kings forage | 2022 (easy, mostly bare) | F1(bare) vs crop map | 0.665 | 0.688 | 0.688 | 0.689 |
| Kings forage | 2022 (easy, mostly bare) | share of bare labels | 0.424 | 0.424 | 0.424 | 0.424 |
| Kings forage | The field itself (never trained on) | agreement with its S2 classes | 0.831 | 0.956 | 0.952 | 0.954 |
| Kings forage | The field itself | transition error vs its S2 classes (days) | 2.8 | 3.3 | 2.8 | 3.2 |
| Kings forage | The field itself | OPERA water scenes found | 0/0 | 0/0 | 0/0 | 0/0 |
| Kings forage | Unseen fields, RF ablation `full` | accuracy vs crop map / S2 agreement | | 0.847 / 0.997 | | |
| Kings forage | Unseen fields, RF ablation `noseason` | accuracy vs crop map / S2 agreement | | 0.844 / 0.996 | | |

### What the numbers mean
- **Colusa:** on fields it never saw, the ML agrees with the crop map 98% of the time against 80% for the rule. The rule's gap is
  weedy fallow, stubble and volunteer winter growth, which it calls thin cover where the crop map says the field is out of crop.
- **Kings (forage):** on the crop map the ML is **no better than the rule** (85% vs 85%), better only on bare-ground F1 (0.76 vs 0.71),
  and **below target** (0.85 / 0.80), so it ships with the badge. Against Sentinel-2's own classes it agrees 99.7%. The gap is the
  crop-map windows themselves: forage fields are cut and replanted at dates the fixed windows do not know.
- **Dates:** against the crop-map window midpoints the error is about 25 days for every method (the reference is crude). The 1-2 days
  against the label sequence (close to the `ds` branch's 5 days) are circular and should not be quoted as accuracy.
- **Water:** on the Colusa field the models found 5-7 of the 20 OPERA water scenes. Flooded rice with stubble or vegetation reads as bare
  or covered in Sentinel-2's classes, so the water class is under-called. This is the first independent water test; it is weak.
- **Seasonal priors:** dropping DOY, Tmax, rain and soil moisture changes the unseen-field crop-map accuracy by under 0.01 at both
  fields, so the models are not just learning the calendar.
- **Rule vs ML disagreement:** 20% at Colusa and 15% at Kings on test dates (target < 15%): the rule's thin cover vs ML bare on low-green
  fallow and stubble.


## B6.2: crop-stress weeks

### Method
- **Unit:** ISO week x field, in-season weeks (rice ISO weeks 23-39, forage 14-39), 2015-2026. Years with no crop (CDL fallow) are scored
  but shown as "fallow", never as stress, and are left out of the evidence sentence. Weeks with water seen (S2/Landsat or OPERA) are
  "water". 2026 assumes the 2025 crop (the crop map ends in 2025), marked `crop_assumed`.
- **z-scores (leave-one-year-out):** z_NDVI = mean of MODIS (2000-) and the field's S2/HLS/Landsat NDVI, each vs the same ISO week ±1
  in other years **with the same crop** (>= 5 years, else all crop years); z_LST = LST minus station Tmax (ECOSTRESS vs its in-season
  record when cached, else MODIS vs same week); z_ESI per source vs its in-season record; z_SM = probit of the SMAP / GRACE-DA
  percentile; z_ETo and z_IMERG30 vs the same week in all other years.
- **Method A (z-score, ds):** mean(-z_NDVI, z_LST, -z_ESI, -z_SM) > 1, or two of z_NDVI < -1, z_LST > +1, z_SM < -1.
- **Method B (isolation forest, ds):** 200 trees, 10% contamination, on all six z-scores (missing = 0), fitted on crop-year weeks.
- **Events:** US Drought Monitor weeks with >= 50% of the county in D3-D4 (cached county statistics), not assumed dates. Recall is
  compared with the flag rate in weeks with no D3 (a lift above 1 means the flags line up with drought).
- **Field-only diagnostic:** method A with only NDVI, LST and ESI. The Drought Monitor itself uses modelled and GRACE-based soil
  moisture, so part of the full method's recall is a shared input.

### Results (14 Nov 2026; recall of D3+ crop weeks / flag rate in weeks with no D3)

| Field | Weeks scored | D3+ weeks | z-score recall / no-drought rate | z-score field-only recall / rate | IF recall / rate | IF leave-one-year-out recall | wet-cool flagged z / IF | agreement | evidence |
|---|---|---|---|---|---|---|---|---|---|
| caf_corcoran_forage | 260 | 100 | 0.49 / 0.43 | 0.37 / 0.20 | 0.14 / 0.06 | 0.27 | 0.31 / 0.28 | 0.56 | The crop looked stressed in 13 weeks over 2015-2026 (both checks agree), mostly late September; most often dry soil (NASA GRACE-DA) and crop using less water than the weather allows (OpenET). |
| caf_elnido_forage | 312 | 100 | 0.36 / 0.34 | 0.13 / 0.19 | 0.05 / 0.12 | 0.05 | 0.31 / 0.24 | 0.66 | The crop looked stressed in 18 weeks over 2015-2026 (both checks agree), mostly early August; most often dry soil (NASA GRACE-DA) and crop using less water than the weather allows (OpenET). |
| caf_goshen_forage | 312 | 104 | 0.42 / 0.35 | 0.16 / 0.31 | 0.05 / 0.12 | 0.07 | 0.34 / 0.26 | 0.62 | The crop looked stressed in 14 weeks over 2015-2026 (both checks agree), mostly early August; most often dry soil (NASA GRACE-DA) and crop using less water than the weather allows (OpenET). |
| caf_newman_forage | 312 | 99 | 0.60 / 0.19 | 0.35 / 0.22 | 0.12 / 0.08 | 0.15 | 0.24 / 0.16 | 0.66 | The crop looked stressed in 10 weeks over 2015-2026 (both checks agree), mostly late May; most often crop using less water than the weather allows (OpenET) and dry soil (NASA GRACE-DA). |
| caf_riverdale_forage | 312 | 100 | 0.48 / 0.34 | 0.20 / 0.24 | 0.09 / 0.12 | 0.09 | 0.36 / 0.32 | 0.61 | The crop looked stressed in 16 weeks over 2015-2026 (both checks agree), mostly early August; most often dry soil (NASA GRACE-DA) and weaker growth than in its other alfalfa years (NASA MODIS). |
| caf_tipton_forage | 312 | 104 | 0.45 / 0.25 | 0.15 / 0.15 | 0.11 / 0.11 | 0.12 | 0.40 / 0.25 | 0.67 | The crop looked stressed in 14 weeks over 2015-2026 (both checks agree), mostly early May; most often dry soil (NASA GRACE-DA) and crop using less water than the weather allows (OpenET). |
| caf_tulare_forage | 312 | 104 | 0.55 / 0.13 | 0.42 / 0.06 | 0.17 / 0.07 | 0.27 | 0.18 / 0.24 | 0.74 | The crop looked stressed in 18 weeks over 2015-2026 (both checks agree), mostly early August; most often dry soil (NASA GRACE-DA) and crop using less water than the weather allows (OpenET). |
| car_biggs_rice | 153 | 51 | 0.63 / 0.00 | 0.16 / 0.01 | 0.10 / 0.05 | 0.20 | 0.20 / 0.17 | 0.75 | The crop looked stressed in 11 weeks over 2015-2026 (both checks agree), mostly early August; most often very thirsty air (high reference evapotranspiration) (NOAA stations and NASA POWER) and weaker growth than in its other rice years (NASA MODIS). |
| car_colusa_rice | 146 | 34 | 0.71 / 0.12 | 0.38 / 0.12 | 0.06 / 0.12 | 0.38 | 0.19 / 0.12 | 0.70 | The crop looked stressed in 4 weeks over 2015-2026 (both checks agree), mostly early September; most often dry soil (NASA GRACE-DA) and hot leaves for the air temperature (NASA MODIS). |
| car_glenn_rice | 187 | 34 | 0.53 / 0.04 | 0.29 / 0.07 | 0.26 / 0.07 | 0.38 | 0.07 / 0.17 | 0.89 | The crop looked stressed in 11 weeks over 2015-2026 (both checks agree), mostly early September; most often weaker growth than in its other rice years (NASA MODIS and Sentinel-2) and dry soil (NASA GRACE-DA). |
| car_grimes_rice | 118 | 0 | n/a / 0.08 | n/a / 0.11 | n/a / 0.11 | n/a | 0.00 / 0.11 | 0.86 | The crop looked stressed in 2 weeks over 2016-2026 (both checks agree), mostly late August; most often hot leaves for the air temperature (NASA MODIS) and dry soil (NASA GRACE-DA). |
| car_richvale_rice | 204 | 51 | 0.31 / 0.07 | 0.16 / 0.11 | 0.18 / 0.08 | 0.27 | 0.11 / 0.20 | 0.85 | The crop looked stressed in 8 weeks over 2015-2026 (both checks agree), mostly early September; most often dry soil (NASA GRACE-DA) and weaker growth than in its other rice years (NASA MODIS). |
| car_robbins_rice | 204 | 51 | 0.67 / 0.07 | 0.43 / 0.09 | 0.31 / 0.03 | 0.35 | 0.16 / 0.09 | 0.84 | The crop looked stressed in 16 weeks over 2015-2026 (both checks agree), mostly early August; most often crop using less water than the weather allows (OpenET) and hot leaves for the air temperature (NASA MODIS). |
| car_zamora_rice | 162 | 34 | 0.18 / 0.04 | 0.03 / 0.05 | 0.09 / 0.06 | 0.12 | 0.03 / 0.08 | 0.88 | The crop looked stressed in 10 weeks over 2015-2026 (both checks agree), mostly early September; most often weaker growth than in its other rice years (NASA MODIS and Sentinel-2) and hot leaves for the air temperature (NASA MODIS). |

### What the numbers mean
- **z-score method:** at the two presets it flags D3+ drought weeks 4-5x as often as other weeks (Colusa 0.71 vs 0.12, Kings 0.55 vs
  0.13). Much of that comes from regional soil moisture (GRACE-DA), which the Drought Monitor also uses. With field signals only (NDVI,
  LST, ESI) recall is 0.38 / 0.42 against 0.12 / 0.06: weaker, still above the base rate at both presets.
- **Isolation forest:** it finds unusual weeks in any direction, so it hardly follows drought (Colusa 0.06 vs 0.12; Kings 0.17 vs
  0.07). Spec check 9 (both methods >= 2 flags in Jul-Aug 2021/2022) fails at most fields because of it. Fitting it leave-one-year-out
  (`recall_usdm_d3_loyo`) helps at Colusa (0.38) and Kings (0.27).
- **Irrigated crops are buffered.** The fields are irrigated; in 2021 regional drought signals were strong while NDVI and leaf
  temperature on the field mostly stayed normal, as spuriNV found on the `ds` run.
- **Inputs used (14 Nov):** soil moisture came from GRACE-DA, because `smap_l4.parquet` was being re-fetched (4 rows) when this ran;
  LST from MODIS (ECOSTRESS LST/ESI still queued in AppEEARS); ESI from ECOSTRESS JET ET / ETo where it exists, else OpenET / ETo.
  Rerun `inputs` and `stress` when those land; the code already prefers them.


## Outputs (`out/<id>/`)

| File | What | Served by |
|---|---|---|
| `models.json` | All ModelReports: rule / RF / HGB for each test, two ablations, z-score and isolation forest. Schema: `schemas/model_report.schema.json` (adds `test`, `headline`, `badge`, `checks`, `class_order`) | `/models` |
| `calendar_ml.json` | Same shape as backend/field `calendar.json`; per observation also `hgb_class`, `consensus_class`, `all_agree`, `s2_scl_class`, `opera_water_frac`; `field_evaluation` | `/calendar_ml` |
| `transitions.json` | Green-up / senescence_harvest / cutting dates per method (rule, RF, HGB, vote) and from the field's own S2 classes, with date errors | none yet (needs a route) |
| `stress_weekly.json` | Per in-season week: `status` (none / one / both / water / fallow), both flags, six z-scores, `drivers` (z keys) and `reasons` (plain words with the NASA source), inputs and their sources | `/stress` |
| `stress_summary.json` | Evidence sentence, latest-season sentence, Drought Monitor evaluation, check-9 results | attached to `/stress` |
| `bare_cover_eval.json` | Everything `checks/run_checks.py` reads (per-test metrics, merged-label confusion matrices, leakage) | none |

## Checks (`uv run python checks/run_checks.py`)

Presets only (all 14 fields: 138 PASS, 27 FAIL, 81 INFO). The FAILs are targets the models miss, reported as they are.

```
nd = 366 if pd.Timestamp(f"{y['year']}-12-31").dayofyear == 366 else 365
  nd = 366 if pd.Timestamp(f"{y['year']}-12-31").dayofyear == 366 else 365
INFO | coverage car_colusa_rice weekly inputs | ndvi_modis 1326 (2000-08-07..2026-09-14), ndvi_hls 487 (2016-01-25..2026-11-02), lst_k 1331 (2000-02-28..2026-10-12), lst_minus_tmax_c 1331 (2000-02-28..2026-10-12), esi 543 (2016-01
PASS | ModelReport schema car_colusa_rice | 13 items valid
PASS | models.json car_colusa_rice has the headline (unseen fields) RF report | bare_rf_car_colusa_rice_unseen_fields_v2
INFO | training data car_colusa_rice | 41235 labelled S2 dates of 250 clusters in 16 blocks; labels {'bare': 24887, 'covered': 13750, 'water': 2598}; label sources {'s2_scl_pseudo': 39020, 'cdl_window': 1634, 'cdl_fallow': 581}
PASS | leakage car_colusa_rice features exclude the label sources | features ['ndvi', 'ndwi', 'bsi', 'ndvi_30d_mean', 'ndvi_30d_min', 'ndvi_30d_max', 'ndvi_60d_mean', 'ndvi_60d_min', 'ndvi_60d_max', 'ndvi_30d_slope', 'ndvi_anom_mo
PASS | leakage car_colusa_rice unseen_fields: no block or cluster in both train and test | 4 folds, test blocks [[3, 13, 15], [1, 2, 8, 11, 12], [5, 6, 7, 14], [0, 4, 9, 10]]
PASS | leakage car_colusa_rice unseen_years: no year in both train and test | train [2016, 2017, 2018, 2019, 2020, 2021, 2022] test [2023, 2024, 2025]
PASS | leakage car_colusa_rice fallow_2022: no year in both train and test | train [2016, 2017, 2018, 2019, 2020, 2021, 2023, 2024, 2025] test [2022]
PASS | leakage car_colusa_rice the field itself is never training data | nearest training-cluster centre 241 m from the field outline (cluster radius 75 m)
PASS | check 8 car_colusa_rice random_forest HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80 | vs crop-map labels: acc 0.980, F1(bare) 0.985, n 32299; vs merged labels (mostly S2 classes): acc 0.980, F1(bare) 0.984
PASS | check 8 car_colusa_rice hist_gbt HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80 | vs crop-map labels: acc 0.981, F1(bare) 0.986, n 32299; vs merged labels (mostly S2 classes): acc 0.981, F1(bare) 0.984
INFO | check 8 car_colusa_rice consensus HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80 | vs crop-map labels: acc 0.980, F1(bare) 0.985, n 32299; vs merged labels (mostly S2 classes): acc 0.982, F1(bare) 0.985
INFO | check 8 car_colusa_rice rule_ndvi HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80 | vs crop-map labels: acc 0.804, F1(bare) 0.834, n 32299; vs merged labels (mostly S2 classes): acc 0.805, F1(bare) 0.808
PASS | check 8 car_colusa_rice random_forest 2022 hold-out (spec wording; EASY test, 92% bare labels) | acc 0.942, F1(bare) 0.970, n 5408
PASS | check 8 car_colusa_rice hist_gbt 2022 hold-out (spec wording; EASY test, 92% bare labels) | acc 0.943, F1(bare) 0.970, n 5408
INFO | check 8 car_colusa_rice rule_ndvi 2022 hold-out (spec wording; EASY test, 92% bare labels) | acc 0.703, F1(bare) 0.822, n 5408
INFO | check 8 car_colusa_rice unseen years 2023-2025 (rule / RF / HGB / vote) | 0.795 / 0.983 / 0.984 / 0.983 accuracy; per year RF 2023 0.964, 2024 0.994, 2025 0.987
INFO | check 8 car_colusa_rice agreement with Sentinel-2 classification (unseen fields; agreement, not accuracy) | rule_ndvi 0.833 / random_forest 0.994 / hist_gbt 0.994 / consensus 0.996
PASS | check 8 car_colusa_rice transition MAE reported (days) | vs crop-map window midpoints: rule_ndvi 29.6, random_forest 25.1, hist_gbt 25.0, consensus 25.0; vs the label sequence (mostly S2 classes, ds design): rule_ndvi 6.9, 
FAIL | check 8 car_colusa_rice rule-vs-ML disagreement < 15% (or explained) | RF vs rule on unseen-field test dates 20.3%; on the field's own S2 dates 17.8% (explained in README: rule 'thin cover' vs ML bare on weedy fallow and st
INFO | check 8 car_colusa_rice ablation full (RF, unseen fields) | acc 0.980, F1(bare) 0.985, agreement with S2 classes 0.998
INFO | check 8 car_colusa_rice ablation noseason (RF, unseen fields) | acc 0.980, F1(bare) 0.985, agreement with S2 classes 0.992
PASS | calendar_ml shape car_colusa_rice | 11 years 2016-2026, segments tile Jan 1-Dec 31: True; data through 2026-11-11
INFO | field car_colusa_rice (never in training): agreement with its own Sentinel-2 classes | rule_ndvi 0.868 / random_forest 0.983 / hist_gbt 0.985 / consensus 0.985 (n 409); transition MAE vs those classes: rule_ndvi 9.2 d, rand
INFO | field car_colusa_rice water vs NASA OPERA DSWx (independent; the model never sees OPERA) | rule_ndvi 6/20 water scenes found, 0 dry called water / random_forest 5/20 water scenes found, 0 dry called water / consensus 7/20 w
PASS | transitions.json car_colusa_rice | methods ['consensus', 'hist_gbt', 'random_forest', 'rule_ndvi', 's2_scl_reference']; types ['green_up', 'senescence_harvest']; RF cuttings 0
PASS | stress_weekly shape car_colusa_rice | 204 weeks; statuses {'none': 98, 'fallow': 50, 'one': 44, 'water': 8, 'both': 4}
PASS | coverage car_colusa_rice stress inputs on scored weeks | 146 weeks; non-missing z: {'z_ndvi': 146, 'z_lst': 134, 'z_esi': 123, 'z_sm': 143, 'z_eto': 146, 'z_imerg30': 146}; sources {'lst_source': {'modis_mod11a2': 191}, 'es
FAIL | check 9 car_colusa_rice julaug 2021 >= 2 flagged weeks (both methods) | zscore 3, iforest 0 of 9 weeks
INFO | check 9 car_colusa_rice julaug 2022 >= 2 flagged weeks (both methods) | not applicable: 2022: Fallow/Idle Cropland on this field (no crop to stress)
PASS | check 9 car_colusa_rice 2023 water weeks are water, not stress | 1 in-season water weeks in 2023, 0 shown as stress
PASS | check 9 car_colusa_rice zscore flags D3+ drought weeks more often than no-drought weeks | recall 0.71 of 34 D3+ crop weeks vs 0.12 of 112 weeks with no D3; wet-cool weeks flagged 0.1875
FAIL | check 9 car_colusa_rice iforest flags D3+ drought weeks more often than no-drought weeks | recall 0.06 of 34 D3+ crop weeks vs 0.12 of 112 weeks with no D3; wet-cool weeks flagged 0.125
INFO | check 9 car_colusa_rice fallow is not stress | fallow years [2016, 2020, 2022] (50 weeks) scored (flag rates z 1.0, IF 0.98) but shown as fallow, out of the evidence
INFO | check 9 car_colusa_rice evidence | The crop looked stressed in 4 weeks over 2015-2026 (both checks agree), mostly early September; most often dry soil (NASA GRACE-DA) and hot leaves for the air temperature (NASA MODIS). | a
INFO | coverage caf_tulare_forage weekly inputs | ndvi_modis 1310 (2000-08-07..2026-09-14), ndvi_hls 477 (2015-10-05..2026-11-02), lst_k 1318 (2000-02-21..2026-10-12), lst_minus_tmax_c 1318 (2000-02-21..2026-10-12), esi 546 (2016-
PASS | ModelReport schema caf_tulare_forage | 13 items valid
PASS | models.json caf_tulare_forage has the headline (unseen fields) RF report | bare_rf_caf_tulare_forage_unseen_fields_v2
INFO | training data caf_tulare_forage | 31318 labelled S2 dates of 166 clusters in 12 blocks; labels {'covered': 16924, 'bare': 14394}; label sources {'s2_scl_pseudo': 30989, 'cdl_window': 327, 'cdl_fallow': 2}
PASS | leakage caf_tulare_forage features exclude the label sources | features ['ndvi', 'ndwi', 'bsi', 'ndvi_30d_mean', 'ndvi_30d_min', 'ndvi_30d_max', 'ndvi_60d_mean', 'ndvi_60d_min', 'ndvi_60d_max', 'ndvi_30d_slope', 'ndvi_anom_
PASS | leakage caf_tulare_forage unseen_fields: no block or cluster in both train and test | 4 folds, test blocks [[2, 3, 11], [7, 9, 10], [4, 5, 6], [8, 14, 15]]
PASS | leakage caf_tulare_forage unseen_years: no year in both train and test | train [2016, 2017, 2018, 2019, 2020, 2021, 2022] test [2023, 2024, 2025]
PASS | leakage caf_tulare_forage fallow_2022: no year in both train and test | train [2016, 2017, 2018, 2019, 2020, 2021, 2023, 2024, 2025] test [2022]
PASS | leakage caf_tulare_forage the field itself is never training data | nearest training-cluster centre 150 m from the field outline (cluster radius 75 m)
FAIL | check 8 caf_tulare_forage random_forest HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80 | vs crop-map labels: acc 0.848, F1(bare) 0.761, n 12175; vs merged labels (mostly S2 classes): acc 0.993, F1(bare) 0.993 -> 'below t
FAIL | check 8 caf_tulare_forage hist_gbt HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80 | vs crop-map labels: acc 0.853, F1(bare) 0.766, n 12175; vs merged labels (mostly S2 classes): acc 0.994, F1(bare) 0.993 -> 'below target
INFO | check 8 caf_tulare_forage consensus HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80 | vs crop-map labels: acc 0.853, F1(bare) 0.767, n 12175; vs merged labels (mostly S2 classes): acc 0.993, F1(bare) 0.993
INFO | check 8 caf_tulare_forage rule_ndvi HEADLINE unseen fields acc>=0.85 & F1(bare)>=0.80 | vs crop-map labels: acc 0.854, F1(bare) 0.714, n 12175; vs merged labels (mostly S2 classes): acc 0.854, F1(bare) 0.811
FAIL | check 8 caf_tulare_forage random_forest 2022 hold-out (spec wording; EASY test, 42% bare labels) | acc 0.755, F1(bare) 0.688, n 1663
FAIL | check 8 caf_tulare_forage hist_gbt 2022 hold-out (spec wording; EASY test, 42% bare labels) | acc 0.755, F1(bare) 0.688, n 1663
INFO | check 8 caf_tulare_forage rule_ndvi 2022 hold-out (spec wording; EASY test, 42% bare labels) | acc 0.776, F1(bare) 0.665, n 1663
INFO | check 8 caf_tulare_forage unseen years 2023-2025 (rule / RF / HGB / vote) | 0.860 / 0.856 / 0.858 / 0.859 accuracy; per year RF 2023 0.835, 2024 0.852, 2025 0.888
INFO | check 8 caf_tulare_forage agreement with Sentinel-2 classification (unseen fields; agreement, not accuracy) | rule_ndvi 0.854 / random_forest 0.997 / hist_gbt 0.996 / consensus 0.996
PASS | check 8 caf_tulare_forage transition MAE reported (days) | vs crop-map window midpoints: rule_ndvi 20.6, random_forest 24.7, hist_gbt 24.7, consensus 24.6; vs the label sequence (mostly S2 classes, ds design): rule_ndvi 6.2
FAIL | check 8 caf_tulare_forage rule-vs-ML disagreement < 15% (or explained) | RF vs rule on unseen-field test dates 15.2%; on the field's own S2 dates 13.6% (explained in README: rule 'thin cover' vs ML bare on weedy fallow and 
INFO | check 8 caf_tulare_forage ablation full (RF, unseen fields) | acc 0.847, F1(bare) 0.759, agreement with S2 classes 0.997
INFO | check 8 caf_tulare_forage ablation noseason (RF, unseen fields) | acc 0.844, F1(bare) 0.756, agreement with S2 classes 0.996
PASS | calendar_ml shape caf_tulare_forage | 11 years 2016-2026, segments tile Jan 1-Dec 31: True; data through 2026-11-11
INFO | field caf_tulare_forage (never in training): agreement with its own Sentinel-2 classes | rule_ndvi 0.831 / random_forest 0.956 / hist_gbt 0.952 / consensus 0.954 (n 455); transition MAE vs those classes: rule_ndvi 2.8 d, ra
INFO | field caf_tulare_forage water vs NASA OPERA DSWx (independent; the model never sees OPERA) | rule_ndvi 0/0 water scenes found, 0 dry called water / random_forest 0/0 water scenes found, 0 dry called water / consensus 0/0 wa
PASS | transitions.json caf_tulare_forage | methods ['consensus', 'hist_gbt', 'random_forest', 'rule_ndvi', 's2_scl_reference']; types ['cutting', 'green_up', 'senescence_harvest']; RF cuttings 12
PASS | stress_weekly shape caf_tulare_forage | 312 weeks; statuses {'none': 214, 'one': 80, 'both': 18}
PASS | coverage caf_tulare_forage stress inputs on scored weeks | 312 weeks; non-missing z: {'z_ndvi': 312, 'z_lst': 299, 'z_esi': 277, 'z_sm': 309, 'z_eto': 312, 'z_imerg30': 312}; sources {'lst_source': {'modis_mod11a2': 299}, '
FAIL | check 9 caf_tulare_forage julaug 2021 >= 2 flagged weeks (both methods) | zscore 6, iforest 0 of 9 weeks
PASS | check 9 caf_tulare_forage julaug 2022 >= 2 flagged weeks (both methods) | zscore 6, iforest 4 of 9 weeks
PASS | check 9 caf_tulare_forage 2023 water weeks are water, not stress | 0 in-season water weeks in 2023, 0 shown as stress
PASS | check 9 caf_tulare_forage zscore flags D3+ drought weeks more often than no-drought weeks | recall 0.55 of 104 D3+ crop weeks vs 0.13 of 208 weeks with no D3; wet-cool weeks flagged 0.18181818181818182
PASS | check 9 caf_tulare_forage iforest flags D3+ drought weeks more often than no-drought weeks | recall 0.17 of 104 D3+ crop weeks vs 0.07 of 208 weeks with no D3; wet-cool weeks flagged 0.23636363636363636
INFO | check 9 caf_tulare_forage fallow is not stress | fallow years [] (0 weeks) scored (flag rates z None, IF None) but shown as fallow, out of the evidence
INFO | check 9 caf_tulare_forage evidence | The crop looked stressed in 18 weeks over 2015-2026 (both checks agree), mostly early August; most often dry soil (NASA GRACE-DA) and crop using less water than the weather allows (OpenE
---- 34 PASS, 9 FAIL, 27 INFO
```

## Honest limits (for the Limits page, spec B11)

- **Labels are products, not field visits.** Training labels are mostly Sentinel-2 scene classification; the headline uses the USDA crop
  map with fixed season windows (U). Neither is ground truth.
- **Kings is below target** on the crop-map test and the ML does not beat the rule there.
- **Water** is under-called on flooded rice (5-7 of 20 OPERA water scenes found on the Colusa field).
- **Transition dates** are only checked against window midpoints (about 25 days off for every method) or against circular labels.
- **Stress has no labelled events.** Drought Monitor weeks are county-wide and share soil-moisture inputs with the z-score method.
- **Coarse inputs:** SMAP 9 km, GRACE-DA 0.25 deg, MODIS LST 1 km and NDVI 250 m describe the area around the field.
- **Registry fields** use the Colusa or Kings model without retraining; several of them lie outside those training boxes.
- **MODIS gaps:** about 5% of composites failed to read after retries (43 of 1,212 LST, some NDVI); the weekly series interpolates across them.


## Blocked or not done
| Item | Why | What it would add |
|---|---|---|
| OPERA water labels on the training clusters | DSWx is cached for the two field outlines only; the cluster boxes would need 1-2 GB of WTR tiles | An independent water label in training (now only an independent check on the field) |
| HLS in training | The cluster sample is Sentinel-2 only | Denser 2016-2017 dates; NASA-native training data |
| Cross-valley test (train Colusa, test Kings) | Not done for time | A harder transfer test than the registry fields' |
| B6.3 LLM layer | Not in this chunk | |
