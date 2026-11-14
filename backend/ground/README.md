# backend/ground: California ground data

Run from `backend/ground/` (uv, Python 3.12). `uv sync` first.

## Run order
1. `uv run python src/rma.py`    RMA cause of loss -> `out/<preset>/rma_profile.json` (no key)
2. `uv run python src/eqip.py`   EQIP 340 -> `out/eqip_340_ca.json` (no key)
3. Keyed (need repo-root `.env`; each prints `BLOCKED: no <NAME> in .env` and exits 0 if missing):
   `src/openet.py` (add `--models` for per-model, uses ~8 of the 100 free monthly queries), `src/cimis.py`, `src/nass.py`, `src/ams.py`
   -> `data/cache/<preset>/{openet,cimis,nass,ams}.parquet` + `.meta.json` (no secrets stored)
4. `uv run python checks/run_checks.py`  PASS/FAIL (keyed checks SKIP until data exists)

## Status
| Source | Status |
|---|---|
| RMA cause of loss 2010-2024 | DONE. Files: https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/cause_of_loss/colsom_YYYY.zip (page moved to https://www.rma.usda.gov/tools-reports/summary-of-business/cause-loss). Grouping: drought = Drought + Failure of Irrigation Supply; excess_moisture = Excess Moisture + Flood + Cold Wet Weather; heat = Heat + Hot Wind; other = rest. Raw CA rows cached in `out/_rma_raw/`. |
| EQIP 340 CA | DONE. No static PDF exists any more; the NRCS Payment Schedules tool (list "California EQIP-1") is replayed by `eqip.py`. Fiscal year is not labelled by the tool. |
| OpenET | DONE (2 fields x Ensemble, 120 monthly rows each, 2016-01..2025-12 -> `data/cache/<preset>/openet.parquet`). Real API quirks: polygon needs the flat `geometry` [lon,lat,...] array (outer ring, no closing point); `geojson` returns 404 "Invalid geoJSON format". Response is `[{"time","et"}]`. 5 queries used (3 failed attempts may count). |
| CIMIS | BLOCKED: key rejected. The 32-char key in `.env` is sent dashed (8-4-4-4-12) because the WAF rejects the undashed form, and the API then answers `ERR1006 INVALID APP KEY`. Re-copy the AppKey from the CIMIS account page. Stations unchanged: 250 Williams (CAR), 15 Stratford (CAF); activity not yet confirmed live. |
| NASS | DONE: CAR 345 rows, CAF 1113 rows (`nass.parquet`, 2010-2025). Rice and corn silage have annual SURVEY county rows; county alfalfa hay exists only as CENSUS (2012, 2017, 2022). The `short_desc__LIKE` filter is broad (returns related series); filter by `short_desc` downstream. |
| AMS hay | DONE: slug 2904 "California Direct Hay Report" confirmed in the report list (`out/ams_reports.json`); 6041 rows 2020-02-28..2025-12-15 (no 2015-2019 reports under this slug), `ams.parquet` in both presets. Region 4 (Madera, Fresno, Kings, Tulare, Inyo) and Region 2 (includes Colusa) are defined in each header's special_notes. |

## Caveats
- RMA alfalfa/forage: CA alfalfa is insured as "Forage Production"/"Pasture,Rangeland,Forage" (index plans); ~100% of Kings/Tulare forage indemnity has no peril attribution (`share_peril_unattributed`), so the cause split is not meaningful there. Corn (Kings) and rice (Colusa) are informative.
- Validation (checks): OpenET vs the engine's monthly ETc climatology, using only CDL-matched years (CDL majority crop in `backend/field/out/<id>/crop_history.json` equals the baseline crop, 2016-2025; same rule as `backend/engine/checks/validate_et.py`). The engine stores one 2015-2025 mean per month, so this is an approximation of that script's matched-year engine run; CIMIS ETo vs POWER Hargreaves from `backend/regional/out/<id>/daily_derived.parquet`. Numbers are reported, never tuned.
