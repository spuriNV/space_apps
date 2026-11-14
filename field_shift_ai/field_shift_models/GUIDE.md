# Field Shift models: code guide and how to use it

This guide covers the two AI models from `planner-spec.md` §B6 and the pipeline that runs them on real
California data:

- **B6.1, bare-field / season detector:** for every satellite date, says whether the field is
  **bare, partial or covered**, and finds green-up and harvest dates. It compares a simple NDVI rule with
  two machine-learning models.
- **B6.2, crop-stress detector:** for every growing-season week, says whether the crop looks
  **stressed**. It compares a z-score method with an isolation forest.

Both write their results as `ModelReport` JSON (the schema in `planner-spec.md` §B3), plus CSVs the frontend
can draw.

---

## 1. What's in the folders

There are two zips.

### `field_shift_models/`: the reusable model library (works for any preset)
```
field_shift_models/
├── run_models.py            command-line entry point (bare | stress | demo)
├── README.md                input column lists and assumptions
└── fieldshift_models/
    ├── bare_cover.py        B6.1: features, labels, NDVI rule, RF + HGB, transitions, metrics, reports
    ├── stress.py            B6.2: weekly z-scores, z-score method, isolation forest, evaluation, reports
    ├── common.py            ModelReport builder + JSON writer
    └── synthetic.py         FAKE data generator for smoke tests only
```

### `fs_real/`: the California preset run on real data
```
fs_real/
├── run_all.sh               one command: rebuild inputs, train/test/validate, draw charts
├── merge_s2.py              merges the two Sentinel-2 extracts (fixes the 2022 gap)
├── build_ca_obs.py          builds the B6.1 input table  -> data/obs_ca.csv
├── build_ca_weekly.py       builds the B6.2 input table  -> data/weekly_ca.csv
├── run_b61.py               trains/tests/validates B6.1, prints the results
├── run_b62.py               runs/validates B6.2, prints the results
├── plot_b61.py, plot_b62.py charts -> out/*.png
├── fieldshift_models/       copy of the library above
├── data/                    downloaded raw data (see §5) + the two built input tables
└── out/                     model reports, predictions, charts
```

---

## 2. Setup

Python ≥ 3.10 and:
```
pip install pandas numpy scikit-learn scipy matplotlib
```
scikit-learn must be **1.4 or newer**: the random forest relies on its built-in handling of missing values.

---

## 3. How to run it

### Re-run everything on the California data
```
cd fs_real
./run_all.sh
```
This takes about a minute. It:
1. merges the Sentinel-2 files
2. builds both input tables
3. trains, tests and validates both models
4. prints the scores and draws `out/b61_ca_calendar.png` and `out/b62_ca_stress.png`

You can also run the steps one at a time: `python3 build_ca_obs.py`, then `python3 run_b61.py`, and so on.

### Run on your own data (any preset)
```
cd field_shift_models
python3 run_models.py bare   --obs my_obs.csv     --out cache/models --split year
python3 run_models.py stress --weekly my_weekly.csv --out cache/models [--loyo]
```
- The inputs can be CSV or Parquet files.
- `--split` sets how the data is divided into training and test sets:
  - `year`: train 2019–22, test 2023–25. This is the default.
  - `ca_fallow`: test on California's 2022 fallow year.
  - `cross_site`: train on the Fraser Valley and California fields, test on Salmon River. This is a stretch goal.
- `--loyo` (stretch) scores each year with an isolation forest fitted on the other years.

### Check that the code works (no real data needed)
```
python3 run_models.py demo --out /tmp/fs_demo
```
This uses **fake** data. It only proves the pipeline runs; the numbers mean nothing.

### Use it from Python
```python
import pandas as pd
from fieldshift_models.bare_cover import run_bare_cover
from fieldshift_models.stress import run_stress

b61 = run_bare_cover(pd.read_csv("data/obs_ca.csv"), split="year", out_dir="out")
b62 = run_stress(pd.read_csv("data/weekly_ca.csv"), out_dir="out")
b61.reports, b61.predictions, b61.transitions     # ModelReports, per-date classes, green-up/harvest dates
b62.reports, b62.weekly, b62.summaries            # ModelReports, per-week flags, evidence + checks
```

---

## 4. How the code works

### B6.1: bare / partial / covered (`bare_cover.py`)

**Input:** one row per field per satellite date, using field-median reflectance (`data/obs_ca.csv`). The full
column list is in `field_shift_models/README.md`.

| Step | Function | What it does |
|---|---|---|
| Clean | `_prepare` | drops dates where less than half the field is clearly visible (`valid_fraction < 0.5`) and non-farm rows |
| Spectral features | `add_indices` | NDVI, EVI, NDWI, BSI (bare soil index), NBR2 |
| Time features | `add_temporal` | NDVI 30- and 60-day mean/min/max, 30-day slope, days since last image, NDVI minus the MODIS normal for that day of year, season (sin/cos of day of year) |
| Labels | `make_labels` | **Sentinel-2 SCL:** at least 80% of field pixels "vegetation" → covered, "not vegetated" → bare. **USDA crop map:** class 61 fallow year → bare. **Crop-map season windows:** weak labels at half weight. Sentinel-2 overrides the crop map |
| Rule | `rule_classify` | NDVI below 0.20 is bare, above 0.35 is covered, otherwise partial |
| Machine learning | `run_bare_cover` | random forest (300 trees, balanced classes) and gradient boosting (HGB). Features with no data are dropped and reported |
| Consensus | inside `run_bare_cover` | majority vote of rule, RF and HGB; if all three differ, the rule's class is used |
| Smoothing + dates | `smooth_classes`, `rule_transitions`, `class_transitions` | 3-date median smoothing, then **green-up** (first of 3 covered dates after bare) and **senescence/harvest** |
| Scoring | `_metrics`, `transition_mae` | accuracy, F1 on the bare class, confusion matrix, green-up/harvest date error in days, rule-vs-ML disagreement, which features mattered most (permutation importance) |

**Validation check #7** (`planner-spec.md` §B10.1) is built in. A model with accuracy below 0.80 or bare-class
F1 below 0.75 gets `"badge": "below target"`, and rule-vs-ML disagreement above 20% is flagged.

**Outputs (`out/`):**
- `bare_cover_predictions_<split>.csv`: the class for every date from each method, raw and smoothed. This drives the calendar.
- `bare_cover_transitions_<split>.csv`: green-up and harvest dates from each method, and from the labels themselves.
- `bare_cover_model_reports_<split>.json`: one ModelReport per method. Includes train and test scores, the confusion matrix (rows = true class, order bare/partial/covered), feature importance and the check results.

### B6.2: crop-stress weeks (`stress.py`)

**Input:** one row per field per week (`data/weekly_ca.csv`).

| Step | Function | What it does |
|---|---|---|
| Weekly z-scores | `build_weekly_features` | how unusual each week is: **z_ndvi** and **z_eto** against the same week in other years (NDVI back to 2000); **z_lst** (surface minus air temperature) and **z_esi** against the field's own record; **z_sm** from the soil-moisture percentile; **z_imerg30** from 30-day rain |
| Season | `run_stress` | scores May–Sep weeks of 2015–2025 only |
| Method A | `method_a_zscore` | composite = mean(−z_ndvi, +z_lst, −z_esi, −z_sm). Flags a week if the composite is above 1.0, **or** if 2 of these hold: z_ndvi < −1, z_lst > +1, z_sm < −1 |
| Method B | `method_b_isolation_forest` | isolation forest (200 trees, 10% of weeks flagged) on all six z-scores, fitted per field. Missing values count as normal (0) |
| Strip + reasons | `run_stress`, `_driving_features` | for each week: flagged by "both", "one" or "none", plus which features drove the flag (e.g. "dry soil (SMAP) (+1.8)") |
| Evaluation | `evaluate_location` | B6.2 has **no labelled stress events, so no accuracy**. It reports instead: **event recall** (share of known drought weeks flagged), a **false-positive proxy** (share of wet, cool weeks flagged) and **agreement** between the methods |
| Check #8 | `validation_check_8` | BC: heat dome (late June 2021) and 2023 drought weeks flagged. California: the 2022 fallow year shows as anomalous, labelled "fallow is not stress" |
| Evidence sentence | `evidence_line` | "Current crop showed stress in N weeks…". Fallow years (crop map class 61) are left out |

**Outputs (`out/`):**
- `stress_weekly_flags.csv`: z-scores, both flags, the strip value and the reasons for every week. This drives the vulnerability strip.
- `stress_model_reports.json`: one ModelReport per method.
- `stress_summary.json`: the evidence sentence, evaluation numbers and checks.

To change the known event dates, edit `DEFAULT_EVENTS` in `stress.py`. The current dates are assumptions; the docs name the events but not the exact dates.

### Settings you might want to change
| Setting | File | Default |
|---|---|---|
| `RULE_BARE_NDVI`, `RULE_COVERED_NDVI` | bare_cover.py | 0.20, 0.35 |
| `SCL_AGREEMENT` (label purity) | bare_cover.py | 0.80 |
| `WEAK_LABEL_WEIGHT` (crop-map window labels) | bare_cover.py | 0.5 |
| `TARGET_ACCURACY`, `TARGET_F1_BARE` | bare_cover.py | 0.80, 0.75 |
| `SPLITS` (train/test years) | bare_cover.py | see §3 |
| `COMPOSITE_THR`, `Z_THR` | stress.py | 1.0, 1.0 |
| `IF_CONTAMINATION` (share of weeks flagged) | stress.py | 0.10 |
| `ANALYSIS_YEARS` | stress.py | 2015–2025 |

---

## 5. The California data

The field is the spec's California preset: Colusa County rice, a 200 m box centred on 39.15 N, 122.10 W.
The USDA crop map shows it as rice every year from 2015 to 2025 except 2022, when it was fallow.

| File in `data/` | What it is | Where it came from |
|---|---|---|
| `fs_s2_ca_colusa_rice.csv` | field-median reflectance + SCL class fractions, 2019–2025 | ESA Sentinel-2 Collection-1 L2A, via Earth Search (AWS), tile 10SEJ |
| `fs_s2_ca_colusa_rice_2022_l2a.csv` | the same for 2022 | Sentinel-2 standard L2A. Collection-1 has only 6 scenes for 2022 here |
| `fs_power_ca_colusa_rice.csv` | daily weather 2000–2025 (max/min temperature, rain, humidity, wind, sunlight) | NASA POWER daily point API |
| `fs_power_soilwet_ca_colusa_rice.csv` | surface and root-zone soil wetness 2000–2025 | NASA POWER (GEOS/MERRA-2 model) |
| `fs_modis_ca_colusa_rice.csv` | 16-day NDVI 2000–2025 | NASA MOD13Q1.061, via Microsoft Planetary Computer |
| `fs_modis_lst_ca_colusa_rice.csv` | 8-day daytime land-surface temperature 2015–2025 | NASA MOD11A2.061, via Planetary Computer |
| `fs_climateserv_ca_colusa_rice.csv` | ESI 4-week (2015 to Jul 2025), SMAP surface soil moisture (2015 to Aug 2022), IMERG daily rain (2015 to Jun 2024) | NASA SERVIR ClimateSERV API |
| `fs_cdl_ca_colusa_rice.csv` | crop class per year, 2015–2025 | USDA Cropland Data Layer, via the CropScape API |

**How the files were downloaded:** I pulled them through a web browser using each service's public API. The
download step **is not a script in this repo yet**. To refresh or extend the data, use the same services: Earth
Search STAC (`sentinel-2-c1-l2a`), the NASA POWER `/api/temporal/daily/point` endpoint, the Planetary Computer
STAC plus its point API (`modis-13Q1-061`, `modis-11A2-061`), ClimateSERV `submitDataRequest` (datasets 29, 38
and 26) and the CropScape `GetCDLValue` endpoint. None of them needs a login.

### Stand-ins, and which source fed each week

The spec asks for SMAP, ECOSTRESS and IMERG from NASA Earthdata. Until the AppEEARS request delivers them,
`build_ca_weekly.py` fills each week from the best source it has. The source used is written into
`weekly_ca.csv`, in the `sm_source`, `esi_source`, `rain_source` and `lst_source` columns:

| Input | Used first | Then | Last resort |
|---|---|---|---|
| Soil moisture | AppEEARS SMAP (pending) | NASA-USDA SMAP (to Aug 2022) | NASA POWER soil wetness (a model, not a satellite) |
| ESI | AppEEARS ECOSTRESS ESI (pending) | SERVIR ESI 4-week, about 5 km | (none) |
| Surface temperature | AppEEARS ECOSTRESS LST (pending) | MODIS 1 km 8-day LST | (none) |
| Rain | GPM IMERG (to Jun 2024) | NASA POWER rain | (none) |

**When the AppEEARS files arrive:** download the `*results.csv` files from appeears.earthdatacloud.nasa.gov
(the tasks are named `fieldshift_ca_modis_smap` and `fieldshift_ca_ecostress`) into `fs_real/data/appeears/`,
then run `./run_all.sh`. The builders look for files whose names contain `MOD13Q1`, `SPL3SMP-E`, `ECO-L2T-LSTE`
and `ECO-L4T-ESI`. This step hasn't been tested with real AppEEARS files yet, so check the printed column
counts the first time.

---

## 6. Current results (California, real data)

**B6.1, tested on 2023–25:**
| Method | Accuracy | Bare-class F1 | Green-up/harvest date error |
|---|---|---|---|
| NDVI rule | 91.8% | 0.91 | 11.7 days |
| Random forest | 97.8% | 0.98 | 5.0 days |
| Gradient boosting | 96.3% | 0.96 | 5.0 days |

On the 2022 fallow year the ML models score 100% and the rule 92%. That test only contains bare labels, so
it's an easy one.

**B6.2, 2015–2025, all six inputs:** the two methods agree on 90.5% of weeks.

| | Z-score | Isolation forest |
|---|---|---|
| Drought-week recall, 2021–22 | 43% | 27% (45% with `--loyo`) |
| Wet, cool weeks flagged (lower is better) | 9% | 15% |
| 2022 fallow weeks flagged (check #8) | 82% | 50% |

Evidence sentence: *"Current crop showed stress in 4 weeks over 2015–2025, mostly early May."*

**How to read B6.2:** in 2021 the regional drought signals were strong, with ESI around −1.6 and dry soil. But
the irrigated rice looked normal in NDVI and surface temperature, so few weeks were flagged. The models only
flag a week when several signals agree.

---

## 7. Limits (put these on the app's Limits page)

- **Labels aren't ground truth.** B6.1's labels come from Sentinel-2's own scene classification and the crop
  map, so "accuracy" means agreement with those products. The ML models score 100% on their training data, so
  the test numbers are optimistic.
- **No "partial" labels.** None of the label sources produces "partial", so the ML models never predict it;
  only the rule does. The team needs to decide whether to add a label source or make the ML two-class.
- **B6.2 has no accuracy.** It's unsupervised and checked only against a few known events.
- **One field.** The California preset is a 200 m box at the spec's centre point, not a surveyed field
  boundary. The BC presets haven't been run on real data.
- **Coarse inputs.** Soil moisture (9 km to about 50 km) and ESI (about 5 km) describe the area around the
  field, not the field itself.
- **Assumed event dates.** The event windows in `DEFAULT_EVENTS` are assumptions; the docs name the events
  but not the dates.

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `ValueError: no labelled training rows for this split` | the chosen train years have no Sentinel-2 or crop-map labels; check `scl_*_frac`, `cdl_class` and `in_season` in the input |
| `training labels contain a single class` | the training rows are all bare or all covered; add more years or another field |
| A feature you expected is missing from a ModelReport | it had no data in the training years; it's listed under `features_dropped_no_data` |
| Random forest error about NaN | upgrade scikit-learn to 1.4 or newer |
| B6.2 returns almost no weeks | check that `in_season` is 1 for May–Sep and that the data covers 2015–2025 |
