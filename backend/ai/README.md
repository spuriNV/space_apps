# backend/ai: the brief's "SI" (bare/cover detector rule vs ML, crop-stress anomaly)

Owner chunk for spec B6.1 (bare-cover and transition detection, rule vs ML), B6.2 (crop-stress anomaly, reduced) and B10.1 checks 8 and 9.
No accounts or keys are used. Nothing trains live. Models are trained offline, and their results are cached as ModelReports.

## Run

```bash
cd backend/ai
uv sync
uv run python -m fieldshift_ai.sample        # 1. clusters + S2 medians -> data/cache/<id>/ai/  (network, ~2.5 min per preset)
uv run python -m fieldshift_ai.bare_cover    # 2. rule vs RF vs HGB -> out/<id>/{models.json, calendar_ml.json, bare_cover_eval.json} (~4 min CAR)
uv run python -m fieldshift_ai.bare_cover --calendar-only  # only rewrite calendar_ml.json (new S2 obs, e.g. 2026); no metrics rewritten
uv run python -m fieldshift_ai.stress        # 3. z-score vs isolation forest -> out/<id>/stress_weekly.json (+ items in models.json)
uv run python checks/run_checks.py           # PASS/FAIL for B10.1 checks 8-9 (local files only)
```
Only step 1 uses the network. Steps 2 and 3 read the cached files listed below. They do not modify those files.

## Inputs

| Input | Where it comes from |
|---|---|
| CDL 2016-2025 class rasters (labels) | `data/cache/<id>/rasters/cdl_<yr>.tif` (backend/field, USDA CroplandCROS) |
| 10 km training box, preset polygon | `backend/field/polygons/<id>_training_box.json`, `<id>.geojson` |
| Sentinel-2 L2A for the training sample | Planetary Computer `sentinel-2-l2a`, anonymous (this chunk, `sample.py`) |
| Preset field S2 / Landsat series (calendar, stress) | `data/cache/<id>/{s2,landsat}.parquet` (backend/field) |
| Crop history (stress season years) | `backend/field/out/<id>/crop_history.json` |
| Rule calendar (for comparison) | `backend/field/out/<id>/calendar.json`. The rule thresholds and the `segments` / `transitions` functions are imported from `fieldshift_field.detector`. |
| Weather | `data/cache/<id>/power.parquet` (T2M_MAX, PRECTOTCORR); Hargreaves ETo from `backend/regional/out/<id>/daily_derived.parquet` |
| USDM (stress context only) | `data/cache/<id>/usdm.parquet` |

### Data volume
- **Clusters:** 250 at CAR and 166 at CAF. CAF has fewer cells that keep a labelled annual crop class for 8 of 10 years, because orchards and perennials are excluded. Each cluster is a CDL 30 m cell whose 5 x 5 neighbourhood (150 m) is a single class in that year. Clusters are at least 250 m apart. None is within 150 m of the preset field, so the preset field is never training data.
- **Scenes:** one S2 tile per box (CAR 10SEJ, CAF 10SGF), scene cloud < 50 %, keeping the clearest scene per half-month. That gives 206 scenes for CAR and 220 for CAF, from 2015-07 to 2025-12, with 0 read errors.
- **What is read per scene:** only the box window. SCL is read at its native 20 m. B02, B03, B04, B08, B11 and B12 are read at 40 m from the COG overviews, which is 1-2 internal blocks per band. No full scenes are downloaded. The bytes downloaded were not metered.
- **Cached output:** `s2_clusters.parquet` with 51,500 rows for CAR and 36,520 for CAF, about 3.6 MB in total, plus `clusters.parquet` and `s2_clusters.meta.json`.
- **Training table:** an observation is used when every SCL pixel around the cluster is clear, and when it falls in a labelled window. That leaves 32,299 labelled observations at CAR and 12,175 at CAF.

## B6.1: bare / covered / water, rule vs ML

### Labels
Each label comes from the CDL class for the cluster in that year plus calendar windows (`common.CROP_WINDOWS`, all U):
- Fallow (61) is bare all year.
- Rice: bare from DOY 1 to 114 and from 290 to 366; covered from 171 to 258.
- Other crops have windows for corn, winter wheat, alfalfa (covered only), cotton, sunflower, safflower and double-crop wheat/corn.
- A bare-window observation is labelled water when its water flag is set (NDWI > 0.3 or SCL water > 50 %).
- Observations between windows (planting/harvest ± ~15 days) are not used.

There is no `partial` label, so the models predict 3 classes. The rule's `partial` is scored as covered: it is neither bare nor water.

### Features and models
- **Features (`CORE`):** NDVI, NDWI, BSI, SCL water fraction, 30/60-day trailing NDVI mean/min/max, 30-day NDVI slope, DOY sin/cos, POWER 7-day Tmax mean and 7-day precipitation.
- **Feature restriction:** `CORE` contains only what backend/field stores for the preset field, so the same model can produce `calendar_ml.json`.
- **Spectral ablation (`bare_rf_full_*`):** an extra RF adds EVI, NBR2, red/NIR/SWIR1/SWIR2 reflectance and days since the last observation.
- **Seasonal ablation (`bare_rf_noseason_*`):** an extra RF drops DOY and Tmax.
- **Models:** `RandomForestClassifier(n_estimators=300, class_weight="balanced")` and `HistGradientBoostingClassifier(class_weight="balanced")`, both with random_state=0. They were fixed before the test results were seen, and nothing was tuned on the test years.

### Splits
- **year** (spec a): train on 2016-2021 and 2023; test on 2022, 2024 and 2025.
- **spatial** (spec d): GroupKFold(4) over the 16 blocks of 2.5 km in the box, all years. A cluster is only ever in one fold.
- **year_spatial:** both at once. The test is the test years in held-out blocks, so the test fields were never seen in any year.

### Results (test sets; acc / F1(bare))

| Preset | Split | Rule (B5.1) | RF | HGB |
|---|---|---|---|---|
| CAR | year, 2022 only | 0.703 / 0.818 | **0.993 / 0.997** | **0.997 / 0.999** |
| CAR | year, all test yrs | 0.763 / 0.805 | 0.994 / 0.996 | 0.996 / 0.997 |
| CAR | year+block, 2022 | 0.703 / 0.818 | 0.992 / 0.996 | 0.995 / 0.997 |
| CAR | spatial block, all yrs | 0.804 / 0.809 | 0.998 / 0.999 | 0.998 / 0.999 |
| CAF | year, 2022 only | 0.776 / 0.666 | **0.830 / 0.738** | **0.811 / 0.695** |
| CAF | year, all test yrs | 0.813 / 0.686 | 0.908 / 0.850 | 0.897 / 0.826 |
| CAF | year+block, 2022 | 0.776 / 0.666 | 0.833 / 0.744 | 0.824 / 0.723 |
| CAF | spatial block, all yrs | 0.854 / 0.714 | 0.958 / 0.926 | 0.958 / 0.926 |

| Metric | CAR | CAF |
|---|---|---|
| Transition-date MAE, test years: rule / RF / HGB (days) | 32.8 / 29.3 / 29.2 | 38.4 / 40.0 / 40.1 |
| RF agreement with SCL pseudo-labels, 2019+: rule / RF | 0.80 / 0.97 | 0.88 / 0.88 |
| RF vs rule disagreement on test observations | 23.6 % | 11.3 % |
| RF vs rule disagreement on the preset field's S2 observations | 15.9 % | 24.5 % |

Transition-date MAE is measured against the midpoint of the CDL-window gap, which is a crude reference (U).

Ablations (year split, RF):

| Ablation | CAR acc / F1(bare), 2022 | CAF acc / F1(bare), 2022 |
|---|---|---|
| Full spectral features | 0.993 | 0.865 (F1(bare) on all test years 0.878) |
| No DOY / Tmax | 0.958 / 0.978 | 0.809 / 0.704 |

### Top permutation importances
Measured on the year-split test set as the drop in f1_macro.
- **CAR:** water_frac 0.30 and doy_cos 0.14 dominate. tmax7, ndvi_max60 and ndvi_max30 each add less than 0.015.
- **CAF:** doy_cos 0.12 (RF) or 0.22 (HGB), then ndvi_mean60 and ndvi_max30/60 at about 0.01-0.03.

### What the numbers mean
- **CAR's ~0.99 is mostly the label rules being learned.** At CAR, 234 of 250 clusters are CDL fallow in 2022, and 97 % of the 2022 labels are bare, so most of the test set has a single class. Water labels are defined by the water flag, which is also a feature. Bare labels cover the whole rice off-season whatever the NDVI is. The model learns "winter or fallow-like → bare" and agrees with CDL. Without DOY and Tmax it still scores 0.96 / 0.98, because a fallow year's 60-day NDVI max stays low.
- **Why the rule scores lower at CAR.** 2,750 bare-labelled observations have NDVI ≥ 0.20: weedy fallow, rice stubble, volunteer winter growth. The rule calls them partial or covered. Either the labels or the rule could be "right" here. The CDL year class cannot say whether a fallow field had weeds.
- **CAF is the harder and more honest test.** Its bare windows are short gaps between forage crops. RF and HGB beat the rule in every split, but miss the 2022 target (acc ≥ 0.85, F1(bare) ≥ 0.80). The ML therefore ships with a **"below target"** badge for CAF.
- **Rule vs ML.** The disagreement target is < 15 %, and CAR exceeds it on test observations (23.6 %). The disagreement is almost entirely rule `partial`/`covered` versus ML `bare` on low-green fallow and rice off-season observations. That is the label definition above.
- **Rule vs ML on the preset field calendar.** At CAF, the ML calendar calls 50-130 winter days per alfalfa year "bare" where the rule sees covered or partial. The model learned the winter-bare prior from corn, wheat and cotton windows, and dormant alfalfa has no bare label to correct it. The rule is likely closer to reality for dormant alfalfa. Use the ML calendar there as a comparison layer, not truth.

### `calendar_ml.json`
Same shape as `backend/field/out/<id>/calendar.json`, so the frontend can swap them. It is produced by the year-split RF, so 2022, 2024 and 2025 are out-of-sample years.
- **Observations:** Sentinel-2 only (field clear ≥ 0.5, ≥ 20 clear pixels). The model was trained on S2, so the Landsat dates in the rule calendar are not used. This is why 2016-2017 have more `unknown` days.
- **Smoothing and fill:** class probabilities are smoothed with a 3-observation centred mean. Days are filled by linearly interpolating the probabilities within gaps of up to 30 days, then taking the argmax.
- **Markers:** green_up is when the smoothed class becomes covered. senescence_harvest is covered → bare.
- **Extra fields:**
  - each observation: `p_bare`, `p_covered`, `p_water`, `class_unsmoothed`, `rule_class`
  - per year: `summary.disagreement_with_rule_obs_pct`, `summary.rule_days_by_class`, `summary.in_training_years`
- **`partial`** stays in `classes` with 0 days, because there is no partial label.

## B6.2: crop-stress anomaly (reduced)

### Method
- **Unit:** ISO week × preset field, in the crop season: CAR rice weeks 23-39, CAF forage weeks 14-39. Only years in which CDL shows the crop are used: CAR 2016, 2020 and 2022 are fallow and skipped.
- **z_ndvi:** weekly field NDVI (S2, with Landsat filling weeks that have no S2) compared with the same ISO week ± 1 in the field's other years with the same crop, leave-one-year-out. If there are fewer than 3 same-crop years, all of the preset's crop years are used.
- **z_tmax, z_eto:** POWER weekly mean Tmax and Hargreaves ETo compared with the same ISO week in 1991-2020.
- **Method A (z-score):** composite = mean(−z_ndvi, z_tmax, z_eto). A week is flagged if the composite > 1 or if 2 or more components are > 1.
- **Method B:** `IsolationForest(n_estimators=200, contamination=0.10)`.
- **Water weeks** are labelled water and never flagged.

### Results

| Preset | Weeks | Flags z / IF | Jul-Aug 2021 z / IF | Jul-Aug 2022 z / IF | Agreement | Cool-week flags z / IF | Sept 2022 heat wave z / IF |
|---|---|---|---|---|---|---|---|
| CAR | 115 | 28 / 12 | 3 / 2 | n/a (fallow) | 77.4 % | 0/12 / 5/12 | n/a |
| CAF | 237 | 46 / 24 | 3 / 1 | 3 / 0 | 78.1 % | 0/18 / 11/18 | 2/2 / 1/2 |

### What the results mean
- **Why the isolation forest misses drought.** It flags unusual weeks in either direction: 11 of its 24 CAF flags are cool weeks. As a result it misses the Jul-Aug drought weeks at CAF, and check 9 fails there.
- **Why the z-score is mostly a heat detector.** Tmax and Hargreaves ETo are almost collinear, so "two components > 1" is in practice a heat rule. Neither method has labelled stress events.
- **2023 flood weeks.** Neither field showed water in the 2023 season, so check 9's "flood weeks appear as water" holds only trivially: there were 0 water weeks and 0 flags.

## Checks (`uv run python checks/run_checks.py`, 2026-11-14)

```
PASS | ModelReport schema car_colusa_rice | 13 items valid
PASS | check 8 car_colusa_rice random_forest 2022 hold-out acc>=0.85 & F1(bare)>=0.80 | acc 0.9933, F1(bare) 0.9965, n 5408
PASS | check 8 car_colusa_rice hist_gbt 2022 hold-out ... | acc 0.9972, F1(bare) 0.9986, n 5408
INFO | check 8 car_colusa_rice rule_ndvi 2022 hold-out ... | acc 0.7028, F1(bare) 0.8182
PASS | check 8 car_colusa_rice transition MAE reported | rule 32.8, RF 29.3, HGB 29.2 days
FAIL | check 8 car_colusa_rice rule-vs-ML disagreement < 15% (or explained) | RF vs rule on test obs 23.6%; preset field 15.9% (explained above)
PASS | check 8 car_colusa_rice no year leakage / no field leakage (spatial, year_spatial) / preset field not in training (241 m)
PASS | calendar_ml shape car_colusa_rice
PASS | check 9 car_colusa_rice Jul-Aug 2021 >= 2 flagged weeks (both methods) | zscore 3, iforest 2
INFO | check 9 car_colusa_rice Jul-Aug 2022 | not applicable: CDL 2022 Fallow/Idle Cropland
PASS | check 9 car_colusa_rice 2023 flood weeks are water, not stress | 0 water weeks, 0 flagged
PASS | ModelReport schema caf_tulare_forage | 13 items valid
FAIL | check 8 caf_tulare_forage random_forest 2022 hold-out | acc 0.8298, F1(bare) 0.7382 -> 'below target' badge
FAIL | check 8 caf_tulare_forage hist_gbt 2022 hold-out | acc 0.8112, F1(bare) 0.6951 -> 'below target' badge
INFO | check 8 caf_tulare_forage rule_ndvi 2022 hold-out | acc 0.7763, F1(bare) 0.6655
PASS | check 8 caf_tulare_forage transition MAE reported | rule 38.4, RF 40.0, HGB 40.1 days
PASS | check 8 caf_tulare_forage rule-vs-ML disagreement < 15% | test obs 11.3%; preset field 24.5%
PASS | check 8 caf_tulare_forage no year / field leakage; preset field not in training (150 m)
PASS | calendar_ml shape caf_tulare_forage
FAIL | check 9 caf_tulare_forage Jul-Aug 2021 >= 2 flagged weeks (both methods) | zscore 3, iforest 1
FAIL | check 9 caf_tulare_forage Jul-Aug 2022 >= 2 flagged weeks (both methods) | zscore 3, iforest 0
PASS | check 9 caf_tulare_forage 2023 flood weeks are water, not stress | 0 water weeks, 0 flagged
---- 20 PASS, 5 FAIL, 15 INFO   (abridged; the script prints the full lines)
```

## Honest limits (feed the Limits page, spec B11)
- **Labels.** Labels are CDL year classes plus calendar windows (U), not field observations. In-season bare periods (a failed stand, a cut alfalfa field) are not labelled. A weedy fallow field is labelled bare.
- **Hold-out years.** 2022 is the only true held-out bare year, and at CAR it is almost all fallow. CAR's ~0.99 mainly shows that the model reproduces the label rules. The CAF numbers are the more informative test.
- **Seasonal priors.** DOY and Tmax are strong features because the labels are seasonal. The no-season ablation in `models.json` shows how much the score depends on them.
- **Water labels.** Water labels use the same NDWI/SCL threshold as the rule, so "water" accuracy is not independent evidence.
- **Training unit.** The unit is a 150 m CDL-homogeneous cluster sampled at 40 m reflectance, not every 30 m cell in the box. Spec B6.1 asks for all cells. This is a sample, chosen to keep downloads small.
- **Sensors.** Sentinel-2 only for the ML, with no HLS harmonisation and no Landsat in training.
- **Transition MAE.** It is measured against window midpoints, not observed planting or harvest dates.
- **Stress models.** They have no labelled stress events. They are checked against two drought summers and one heat wave (U dates), and use only NDVI and temperature-driven anomalies.

## Blocked
| Item | Needs | What it unblocks |
|---|---|---|
| HLS 30 m (spec unit for B6.1) | Earthdata login | Harmonised S2+Landsat training/calendar, more clear dates in 2016-2017 |
| MODIS MOD13Q1 NDVI climatology (feature "NDVI minus MODIS same-DOY", B6.2 z_NDVI 2000+) | Earthdata login | Longer NDVI baseline than the field's 6-7 crop years |
| SMAP L3/L4 soil moisture (B6.1 feature, B6.2 z_SM) | Earthdata login | Soil-moisture stress component |
| ECOSTRESS LST / ESI (B6.2 z_LST, ESI) | Earthdata login | Thermal stress component (the most direct stress signal) |
| GPM IMERG (B6.1 7-day rain, B6.2 30-day anomaly) | Earthdata login | Replaces POWER precipitation |
| OPERA DSWx (water labels) | Earthdata login | Independent water labels instead of the NDWI/SCL rule; 2023 flood check |
| OpenET monthly ET anomaly (B6.2) | OpenET API key | Measured field-scale ET deficit component |
| Cross-valley test, split (c) [S] and split (b) | none (not done for time) | Train CAR, test CAF |
| B6.3 LLM layer | LLM API key | Not in this chunk's scope here |

## 2026 update (run 2026-11-14)
`calendar_ml.json` now covers 2016-2026 (`method.forward_years` = [2026], `data_through` 2026-11-11). Models are not saved, so `--calendar-only` refits the same year-split random forest on the unchanged 2016-2021 + 2023 table (seed 0, so earlier years reproduce exactly) and classifies the new S2 scenes. Nothing is trained on 2026 (CDL labels end in 2025), and `models.json`, `bare_cover_eval.json` and the stress outputs are untouched. Years 2016-2024 are identical to the previous file; only the last 2025 observation's probability moves, because the 3-observation smoothing now sees a 2026 neighbour. Rule-vs-ML disagreement on the field's S2 observations over 2016-2026 is 15.8 % (CAR) and 22.3 % (CAF); 2026 alone is 15.1 % and 2.0 %. 2026 is out of sample for the model.
