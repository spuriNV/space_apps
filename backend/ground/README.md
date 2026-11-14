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
| OpenET | BLOCKED: OPENET_API_KEY (fetcher written from docs; response body shape undocumented, parser is defensive and raw JSON saved to `out/<preset>/openet_raw_*.json`) |
| CIMIS | BLOCKED: CIMIS_APP_KEY. Stations: 250 Williams (CAR); 15 Stratford (CAF, ~22 km from field) |
| NASS | BLOCKED: NASS_API_KEY. `short_desc` strings are discovered with `short_desc__LIKE` and printed, not assumed. County alfalfa survey data may not exist (Census years only). |
| AMS hay | BLOCKED: AMS_API_KEY. Slug 2904 (California Direct Hay Report) unverified; the script saves the report list to `out/ams_reports.json`. |

## Caveats
- RMA alfalfa/forage: CA alfalfa is insured as "Forage Production"/"Pasture,Rangeland,Forage" (index plans); ~100% of Kings/Tulare forage indemnity has no peril attribution (`share_peril_unattributed`), so the cause split is not meaningful there. Corn (Kings) and rice (Colusa) are informative.
- Validation (checks): OpenET vs the engine's monthly ETc climatology (engine only stores a 2015-2025 mean per month, so OpenET is averaged 2019-2024 per month); CIMIS ETo vs POWER Hargreaves from `backend/regional/out/<id>/daily_derived.parquet`. Numbers are reported, never tuned.
