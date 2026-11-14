# Integrating the `ds` branch models into Field Shift

**Date:** 14 Nov 2026.
**Subject:** the `ds` branch (commit `80ace9f`, "model data", by spuriNV), folder `field_shift_ai/`.
**Compared against:** `backend/ai/` on `main`.

**Recommendation in one line:** merge the two into one `backend/ai`.
- **Bare-field detector:** our multi-field Cropland Data Layer training plus the teammate's per-date Sentinel-2 labels, voting and transition logic.
- **Stress model:** the teammate's stress model (the core of `ds`), fed by our real NASA downloads.
- **Fields:** run everything on both real field outlines.
- **Outputs:** in the shapes the API and app already use.

Credit the teammate in the README and the slides.

---

## 1. What the `ds` branch contains

| Path | What it is |
|---|---|
| `field_shift_ai/field_shift_models/` | Reusable library and command-line runner (`run_models.py bare / stress / demo`) |
| `field_shift_ai/fs_real/` | The library run on real data for one Colusa location: input CSVs in `data/`, results in `out/`, charts, `run_all.sh` |
| `fieldshift_models/bare_cover.py` | B6.1 bare / partial / covered detector |
| `fieldshift_models/stress.py` | B6.2 crop-stress detector |
| `fieldshift_models/common.py` | ModelReport builder |
| `fieldshift_models/synthetic.py` | Fake data for smoke tests only |
| `GUIDE.md`, `README.md` | Documentation |

The library is copied twice (`field_shift_models/fieldshift_models/` and `fs_real/fieldshift_models/`) and `GUIDE.md` three times.

**B6.1 bare-field detector.**
- **Features:** NDVI, EVI, NDWI, BSI and NBR2, rolling NDVI statistics, NDVI minus MODIS climatology, and day of year.
- **Labels:** from Sentinel-2's scene classification (SCL), at 80% pixel agreement per date, plus Cropland Data Layer fallow years and half-weight crop-season windows.
- **Models:** NDVI rule vs random forest vs gradient boosting, combined by a majority vote, then 3-date smoothing to get green-up and harvest dates.
- **Checks:** spec check #7 built in.

**B6.2 crop-stress detector.**
- **Inputs:** weekly z-scores of NDVI (MODIS back to 2000), land-surface temperature minus air temperature, evaporative stress index, soil moisture, reference ET and 30-day rain.
- **Methods:** a z-score composite against an isolation forest.
- **Output:** a "both / one / none" strip, the driving features per week in plain words, and an evidence sentence.
- **Fallow years:** excluded ("fallow is not stress").
- **Checks:** spec check #8 built in.

### Reported results (Colusa, their 200 m box)

| B6.1, test years 2023–25 | Accuracy | Bare F1 | Green-up/harvest error |
|---|---|---|---|
| NDVI rule | 91.8% | 0.91 | 11.7 days |
| Random forest | 97.8% | 0.98 | 5.0 days |
| Gradient boosting | 96.3% | 0.96 | 5.0 days |

B6.1 on the 2022 fallow year: the models score 100%, the rule 92%. That test set contains only bare labels.

B6.2 over 2015–2025, 241 in-season weeks:

| | z-score method | Isolation forest |
|---|---|---|
| Recall on 2021–22 drought weeks | 43% | 27% |
| Wet, cool weeks flagged | 9% | 15% |

The two methods agree on 90% of weeks. Evidence sentence: "stress in 4 weeks, mostly early May".

---

## 2. Side by side with `backend/ai`

| | `ds` (`field_shift_ai`) | `main` (`backend/ai`) |
|---|---|---|
| Fields | One 200 m box at the spec centre point (39.15 N, −122.10 W), Colusa only | Real DWR field outlines for both presets (Colusa and Kings) |
| Preset IDs | `ca_colusa_rice` | `car_colusa_rice`, `caf_tulare_forage` |
| Training data | 1 location; 164 train and 134 test labels | 250 (Colusa) and 166 (Kings) 150 m clusters across a 10 km box; about 32,000 and 12,000 labelled observations |
| Labels | Sentinel-2 SCL per date (strong), CDL fallow, CDL season windows (weak) | CDL year class plus season windows; water from the SCL and NDWI flag |
| Classes | bare / partial / covered (ML never learns "partial") | bare / covered / water |
| Test design | Held-out years (2023–25), plus 2022 | 2022 held out; year split; spatial block hold-out by field; preset field never in training |
| Bare-field result | 92% rule / 98% RF / 96% HGB on 2023–25 | Colusa about 99% (inflated by label construction); Kings 83% ("below target") |
| Transition date error | **5 days** | about 29–40 days |
| Stress inputs | MODIS NDVI 2000–, MODIS LST, SERVIR ESI, NASA-USDA SMAP (to Aug 2022), IMERG (to Jun 2024), POWER | Sentinel-2/Landsat NDVI and POWER Tmax/ETo only |
| Stress output | Per-week reasons in plain words, an evidence sentence, fallow excluded | Flags and agreement only; mostly a heat detector |
| Data access | Downloaded by hand in a browser; no fetch script | Scripted fetch (Planetary Computer, CroplandCROS), cached with metadata |
| Packaging | `pip` instructions, no lockfile | uv project, checks script, metadata files, as required by `CONTRACT.md` |
| API outputs | CSVs and ModelReport JSON in its own folder | `models.json`, `calendar_ml.json` and `stress_weekly.json`, already served by `/models` and `/calendar_ml` |

**Net:**
- **The teammate's** stress model, labels and transition logic are clearly better.
- **Ours** wins on coverage (both fields, real outlines), on a larger and more honest training and test design, on reproducibility, and on wiring into the app.

---

## 3. Problems to solve in the merge

### Scientific

1. **Sentinel-2 labels are partly circular.** The model learns from the same Sentinel-2 reflectance that produced the labels, so "98% accuracy" partly measures agreement with ESA's own classifier. Report it as "agreement with Sentinel-2 scene classification", not ground truth.
   - **Fix:** combine label sources, and keep the Cropland Data Layer and unseen-field tests as the headline validation.
2. **One field, 164 training labels, 100% training accuracy.** The `ds` test numbers come from the same 200 m box in other years, so they say nothing about other fields.
   - **Fix:** train across the 10 km sample of fields (ours) and report a spatial hold-out by field.
3. **The 2022 fallow test is trivial.** It contains only bare labels, so 100% says little. Both branches share this. Don't quote it.
4. **"Partial" has no labels.** The `ds` machine-learning models never predict it; ours uses bare / covered / water instead.
   - **Fix (decided below):** three output classes, bare / covered / water. The rule's "partial" is shown as "thin cover" only on the rule strip, and isn't scored.
5. **Water vs bare at Colusa.** Winter-flooded rice reads as water in our data in only 3 of 6 winters. `ds` has no water class.
   - **Fix:** use the OPERA surface-water data now in `backend/nasa` as an independent water label, which also breaks the water circularity.
6. **Stress inputs are stand-ins.** `ds` has SMAP to Aug 2022 and IMERG to Jun 2024, and falls back to POWER's modelled soil wetness. We now have real SMAP L3/L4, IMERG, GRACE, MODIS and ECOSTRESS from Earthdata in `backend/nasa`.
   - **Fix:** point the weekly builder at those.
7. **Assumed event dates.** `DEFAULT_EVENTS` in `stress.py` are guesses. Use dated, sourced events instead: Drought Monitor D3+ weeks (cached) for drought, and Kings spring 2023 for the flood.
8. **Kings has never been run** through the `ds` models. Alfalfa's many cuttings will look like repeated "harvests", so the transition logic needs a minimum gap or a "cutting" type for perennial forage.

### Engineering

9. **Preset IDs differ:** map `ca_colusa_rice` to `car_colusa_rice`.
10. **No fetch script:** the `ds` inputs can't be reproduced. Rebuild the input tables from our cached, scripted data instead of committing hand-downloaded CSVs.
11. **Duplicate copies** of the library and guide. Keep one library inside `backend/ai`.
12. **Doesn't follow `CONTRACT.md`:** no uv project, no SourcedNumber wrapping or metadata, and outputs not in API shape.
13. **Schema fit:** `ds` ModelReports are close to `schemas/model_report.schema.json`, but fields such as `badge`, `checks` and `features_dropped_no_data` need adding to the schema or nesting under `notes`.
14. **scikit-learn ≥ 1.4** is needed for NaN handling in the random forest. Pin it in `backend/ai/pyproject.toml`.
15. **Merge mechanics:** don't merge `ds` into `main` as-is. It adds about 32,000 lines, mostly CSVs, and parallel code. Bring the code across in a new commit, and keep `ds` untouched as the teammate's reference.

---

## 4. Target design

```
backend/ai/
  pyproject.toml                  uv project; scikit-learn>=1.4 pinned
  fieldshift_ai/
    inputs.py                     NEW: builds both input tables per preset from our caches
    bare_cover.py                 MERGED: ds features + labels + vote + smoothing/transitions,
                                  trained on our multi-field sample; classes bare/covered/water
    stress.py                     FROM ds: weekly z-scores, z-score vs isolation forest, reasons,
                                  evidence sentence; event windows from Drought Monitor
    common.py                     MERGED ModelReport builder (schema-valid)
    sample.py                     OURS: 10 km multi-field sampling
  reference/ds_colusa_box/        the ds run's outputs, unchanged, credited (no copied code)
  checks/run_checks.py            checks 7 and 8 plus the leakage and coverage checks
  out/<preset>/
    models.json                   all ModelReports (rule, RF, HGB, z-score, isolation forest)
    calendar_ml.json              same shape as backend/field calendar.json
    transitions.json              green-up / harvest / cutting dates per method
    stress_weekly.json            per week: strip, both flags, z-scores, reasons in plain words
    stress_summary.json           evidence sentence + evaluation
```

### Inputs, all from data already cached and scripted on `main`

| Input column | Source |
|---|---|
| Reflectance, `valid_fraction`, `scl_bare_frac`, `scl_veg_frac` | Sentinel-2 L2A field windows (backend/field), extended to use the SCL fractions per date |
| Same, NASA-native | HLS L30/S30 (backend/nasa_open, plus LP DAAC with the login) |
| `modis_ndvi_clim`, `ndvi_modis` | MODIS MOD13Q1 2000– (backend/nasa) |
| `lst_k`, `esi` | ECOSTRESS LST and ESI (backend/nasa); MODIS LST as fallback |
| `smap_pct` | SMAP L4 root-zone percentile (backend/nasa) |
| `imerg_30d_mm`, `imerg_7d_mm` | GPM IMERG (backend/nasa) |
| `t2m_max_c`, `eto_mm` | NOAA stations with POWER fallback; Penman–Monteith ETo as in the engine |
| `cdl_class`, `in_season` | backend/field crop_history.json plus preset calendars |
| Water label (new) | OPERA DSWx water fraction (backend/nasa) |
| Field geometry | backend/field/polygons (real DWR outlines) |

### Validation, reported in `models.json` and on the app's "How we know" panel

1. **Unseen fields** (spatial hold-out across the 10 km sample): the headline number.
2. **Unseen years** (2023–25 held out, the `ds` design), on the multi-field sample.
3. **2022 fallow:** reported, but labelled "easy test, bare only".
4. **Agreement with Sentinel-2 classification:** labelled as agreement, not accuracy.
5. **Green-up and harvest date error,** in days.
6. **Rule vs machine-learning disagreement,** in %.
7. **Stress:** recall of Drought Monitor D3+ weeks, false positives in cool wet weeks, agreement between the two methods, and fallow years excluded.

"Below target" badges are shown in plain words wherever a threshold is missed.

---

## 5. What it looks like in the app

- **Your field's year:**
  - a "How the field's cover was read" toggle: **Simple rule / Machine learning / Both agree**;
  - shading where they disagree;
  - harvest and green-up ticks from the consensus.
- **Your field now:** one stress line in plain words from the evidence sentence and the latest week's reasons, for example "Crop looked stressed 2 weeks this summer, mostly dry soil (NASA SMAP) and hot leaves (ECOSTRESS)."
- **Crop-stress strip** under the year strips: "both methods / one method / none", each flagged week with its reasons on hover.
- **How we know (new small panel, also a slide):**
  - unseen-field accuracy per field, with the Kings "below target" note;
  - harvest-date error in days;
  - one line: "Labels come from the USDA crop map and Sentinel-2 classification, not field visits."
- **Brief:** one evidence sentence and one validation sentence, both from the files above.

The pitch line this supports (only once the numbers exist): "Two detectors, a simple rule and a machine-learning model, read the field's cover from NASA and ESA imagery. We test them on fields and years they never saw, and show where they disagree."

---

## 6. Work plan

| Step | Effort |
|---|---|
| 1. Copy the `ds` library into `backend/ai/fieldshift_ai/` (merge `bare_cover.py`; take `stress.py`); pin scikit-learn; delete duplicates | small |
| 2. `inputs.py`: build the observation and weekly tables for both presets from cached data; add SCL fractions and OPERA water labels | medium |
| 3. Train B6.1 on the multi-field sample with the merged labels; run all five tests; write the outputs | medium |
| 4. Run B6.2 with real NASA inputs and Drought Monitor events; add "cutting" handling for alfalfa | medium |
| 5. Schema update, `check_api.py`, API routes for `transitions` and `stress_summary` if needed | small |
| 6. Frontend: toggle, stress strip, "How we know" panel, brief lines | medium |
| 7. Move the `ds` outputs to `reference/ds_colusa_box/`, credit the teammate, update `docs/judging-rubric.md` | small |

**Ownership:** one agent for steps 1–5 and one for step 6, after 5. The teammate reviews step 3's results.

---

## 7. Decisions taken here (change if the teammate disagrees)

- **One AI chunk:** `backend/ai`. The `ds` branch stays as the teammate's reference and is not merged as-is.
- **Classes:** bare / covered / water; "partial" is shown only as the rule's "thin cover".
- **Headline accuracy:** the unseen-field test, never the 2022 fallow test or the 99% Colusa figure.
- **Stress events:** from Drought Monitor D3+ weeks, not assumed dates.
- **All inputs:** come from scripted, cached sources on `main`.
