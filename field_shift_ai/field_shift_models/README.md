# Field Shift models: B6.1 + B6.2

Implements `planner-spec.md` §B6.1 (bare-cover / transition detection, rule vs ML) and §B6.2
(crop-stress anomaly, z-score vs isolation forest), with outputs in the B3 `ModelReport` shape and
the B10.1 checks #7 and #8 built in. Models train offline; the demo reads the cached outputs.

Requires Python ≥ 3.10, pandas, scikit-learn ≥ 1.4 (random forest handles NaN natively), scipy.

```
python run_models.py bare   --obs hls_obs.csv     --out cache/models --split year        # train 2019-22, test 2023-25
python run_models.py bare   --obs hls_obs.csv     --out cache/models --split ca_fallow   # CA: test on 2022
python run_models.py bare   --obs hls_obs.csv     --out cache/models --split cross_site  # [S] train FV+CA, test SR
python run_models.py stress --weekly weekly.csv   --out cache/models [--loyo]
python run_models.py demo   --out /tmp/fs_demo    # FAKE synthetic data: smoke test only
```
Inputs can be `.csv` or `.parquet`. Preset IDs must match `fv_sumas_dairy`, `sr_salmon_river_hay`, `ca_colusa_rice`.

## Input 1: per-observation table (B6.1), from workstream 2

One row per field × HLS observation date, field-median values, cloud/shadow already masked.

| column | required | notes |
|---|---|---|
| `location_id`, `date` | yes | |
| `blue, green, red, nir, swir1, swir2` | yes | surface reflectance 0–1 |
| `valid_fraction` | | rows < 0.5 are dropped (B5.1) |
| `snow_flag` | | 0/1 from Fmask/SCL |
| `modis_ndvi_clim` | | MODIS 250 m same-DOY NDVI climatology for the field's cell |
| `smap_pct`, `imerg_7d_mm`, `power_tmax_7d_c` | | context features |
| `scl_bare_frac`, `scl_veg_frac` | | fraction of field pixels with S2 SCL 5 / SCL 4 on a clear same-day scene; NaN if none |
| `cdl_class` | CA | 61 = Fallow/Idle → bare all year |
| `in_season` | CA | 1 inside / 0 outside the CDL crop's regional planting–harvest window, NaN at the edges |
| `is_agricultural` | BC | from AAFC ACI; False rows dropped |
| `crop_type` | | passed through to outputs (ACI/CDL crop type for transition labelling) |

Features computed: NDVI, EVI, NDWI, BSI, NBR2, red/NIR/SWIR1; trailing 30/60-day NDVI mean/min/max,
30-day NDVI slope, days since last valid obs, NDVI − MODIS climatology; sin/cos DOY; context columns.

## Input 2: weekly table (B6.2), from workstreams 1 + 2

One row per field × week (`week_start` = Monday). NDVI should go back to 2000 for the climatology;
scoring uses in-season weeks of 2015–2025.

`location_id, week_start` (required); `in_season`, `ndvi_modis`, `ndvi_hls`, `lst_k` (ECOSTRESS),
`t2m_max_c` (POWER, same day as the overpass) or a precomputed `lst_minus_tmax_c`, `esi`,
`smap_pct`, `eto_mm`, `imerg_30d_mm`.

## Outputs (in `--out`)

- `bare_cover_predictions_<split>.csv`: per date: rule / random_forest / hist_gbt / consensus, raw and 3-obs-median smoothed, plus a rule-vs-ML disagreement flag
- `bare_cover_transitions_<split>.csv`: green-up / senescence dates per method, and the pseudo-label reference
- `bare_cover_model_reports_<split>.json`: ModelReports per method per location: accuracy, F1(bare), confusion (order bare/partial/covered), transition MAE, disagreement, permutation importance, `badge: "below target"` and check #7 results
- `stress_weekly_flags.csv`: z features, composite z, both flags, `strip` = both/one/none, driving features
- `stress_model_reports.json`: ModelReports: flag rate, event recall, false-positive proxy, agreement, check #8
- `stress_summary.json`: evidence line ("Current crop showed stress in N weeks over 2015–2025, mostly late July") + evaluation

## Where the docs were silent, and what this code assumes

1. **No label source for "partial".** The labels in the docs (SCL 5/4, CDL fallow, CDL windows) only give bare or covered, so the ML models never learn "partial", while the rule can output it. Decide whether to (a) add a partial label (e.g. mixed-SCL scenes) or (b) make it a 2-class model.
2. **CDL window labels.** The docs say "weak bare/covered labels outside the season". The code reads this as outside the window → bare and inside → covered, with weight 0.5. The edges are left unlabelled.
3. **Label priority:** S2 SCL > CDL fallow > CDL window.
4. **ML transitions.** The docs say they are extracted "the same way as the rule". The code uses green-up = 3 consecutive *covered* after a *bare*, and senescence = 2 consecutive non-covered after cover.
5. **Transition MAE:** each pseudo-label transition is matched to the nearest predicted one of the same type within 60 days.
6. **Consensus** = majority of rule/RF/HGB; when all three differ, the rule's class is used.
7. **z_NDVI:** the MODIS z and the HLS z (each against its own same-week climatology) are averaged where HLS exists.
8. **Isolation forest:** missing z values are filled with 0, meaning "normal". It flags anomalies in any direction, including wet and cold weeks.
9. **Event windows** (in `stress.DEFAULT_EVENTS`): heat dome 21 Jun–4 Jul 2021, BC drought 1 Jul–31 Aug 2023, CA drought 2021–22. The docs name these events but not exact dates.
10. **False-positive proxy:** "wet, cool week" = (SMAP z > 0 or 30-day rain z > 0) and ETo z < 0.

The synthetic data in `synthetic.py` is fake and too easy: its labels come straight from NDVI, so
accuracy is 1.0 and permutation importance is ~0. Only use it to check the pipeline runs.
