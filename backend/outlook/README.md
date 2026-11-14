# backend/outlook: coming-season outlook data (winter 2026-27 and the 2027 season)

Own `uv` project. Everything is labelled **outlook, not a forecast**. Output: `out/<preset_id>/outlook.json` (SourcedNumbers with value, low/high, unit, source URL, `fetched_at`, `verified`) plus a `plain_language_summary`. Built 14 Nov 2026.

```
uv sync
uv run python src/fetch_cpc.py        # CPC 90-day temp/precip + drought outlooks at each field -> out/cpc.json
uv run python src/fetch_water.py      # USDM to latest week, CDEC storage + CDEC average -> out/water_now.json, data/cache/<id>/{usdm_2026,cdec_2026}.*
uv run python src/fetch_context.py    # snow, Bulletin 120 status, CVP/SWP allocations, storage-vs-allocation -> out/context.json
uv run python src/history.py          # bare window, heavy-rain chance, scenario shifts -> out/history.json
(cd ../engine && uv run python ../outlook/src/irrigation.py)   # engine score() runs -> out/irrigation.json
uv run python src/build_outlook.py    # -> out/<id>/outlook.json
uv run python checks/run_checks.py    # PASS/FAIL (saved in out/checks_output.txt)
```

## Sources
| Item | Source (no key) |
|---|---|
| CPC 90-day temp/precip | GIS shapefiles `https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/seastemp_202610.zip`, `seasprcp_202610.zip` (Oct 2026 issue, 15 Oct; leads NDJ 2026-27 to ASO 2027). Point-in-polygon at the field polygon centroid. Page: https://www.cpc.ncep.noaa.gov/products/predictions/90day/ |
| CPC drought outlook | `https://ftp.cpc.ncep.noaa.gov/GIS/droughtlook/sdo_update_polygons_20261031.zip` (seasonal, to 31 Jan 2027) and `mdo_polygons_20261031.zip` (Nov 2026) |
| Drought now | US Drought Monitor county API (`usdmdataservices.unl.edu`), map 10 Nov 2026; cached 2026 weeks in `data/cache/<id>/usdm_2026.parquet` |
| Reservoirs | CDEC Daily Reservoir Storage Summary `https://cdec.water.ca.gov/reportapp/javareports?name=RES` (storage, capacity, CDEC average for the date, % of average, year-ago), plus daily JSON sensor 15 (`cdec_2026.parquet`). Our own 2015-2025 same-day mean is also given and labelled; it reads lower/higher than CDEC's long-term average |
| Snow / runoff | CDEC statewide SWE `...name=DLYSWEQ`; Bulletin 120 `...name=B120UP` |
| CVP allocations | Reclamation `https://www.usbr.gov/mp/cvo/vungvari/water_allocations_historical.pdf` (updated 27 Oct 2026) and news releases 5289, 5305, 5338, 5386 |
| SWP allocations | DWR release URLs below; values read from ACWA's copy (`verified: false`) |
| History | `backend/field/out/<id>/calendar.json`, `crop_history.json`; NOAA GHCN-Daily stations in `data/cache/<id>/ncei.parquet` (not POWER) |

## Methods (all conditional climatology or engine runs, not forecasts)
- **CPC probability** is the favoured category's contour (33 means the 33-40% band). Equal chances stored as `null`, never a number.
- **Bare window**: longest run of `bare` satellite class (1 Oct-30 Apr, >= 14 days) in each winter after a year whose CDL crop is the current crop (rice at CAR, alfalfa at CAF; 2025 crop assumed again in 2026). Median start/end by offset from 1 Oct.
- **Heavy-rain chance**: share of 1981-2024 winters with a >= 25 mm (1 inch) day at the 3 NOAA stations inside the median window dates. Conditional version: winters split into terciles of the CPC season's station rain (1991-2020 base); chance = sum of CPC probability x event rate in that tercile. Near-normal held at 33.3% and the opposite category takes the remainder (our assumption). About 11-15 winters per tercile, so noisy; low/high span climatology, blended and favoured-only.
- **Irrigation 2027**: `score(preset, scenario={dT_c, dP_pct})` for three scenarios: climatology (0, 0), CPC-weighted shift, and the favoured category fully realised. Shifts from the same tercile method (temperature: NDJ, FMA, MJJ, ASO; rain: NDJ and FMA as % of mean water-year rain, capped at +/-30% by the engine). value = CPC-weighted run; low/high = min/max of the three. The engine's own parameter range is kept as `engine_param_range`. There is **no default allocation in the repo** (spec: user input), so none is assumed; comparison is against the engine's default-weather run.
- Storage vs final allocation: Shasta storage on 13 Nov vs Reclamation's last CVP allocation for the next year, 2016-2026 (2026 not final). Descriptive: low early storage preceded both 0% and 100% south-of-Delta allocations (2023: 31% full, then 100% after a wet winter), so early-winter storage alone is a weak guide; Settlement Contractors were cut only in 2015, 2021, 2022.

## Results in one line each
- CAR: precip above normal tilt (Dec-Feb 40%, Jan-Mar 50%, Feb-Apr 40%), temp above normal; Shasta 92% / Oroville 80% of CDEC average; Colusa D0 100%; CPC drought outlook no drought; bare window ~13 Feb-1 Apr, 1-inch rain day 54% of winters (61% weighted, range 54-88%); rice irrigation need 5.2 af/ac, barely moved by the outlook.
- CAF: Dec-Mar precip above normal 50%, temp equal chances; Pine Flat 66% of average and 19% full; Kings County no drought; no typical bare window (alfalfa stays covered; 2 of 6 winters bare); alfalfa need 3.8 af/ac.

## Blocked / Not yet published
| Item | Status | URL tried |
|---|---|---|
| Bulletin 120 WY2027 forecast | not yet published; CDEC page still shows May 2026 | https://cdec.water.ca.gov/reportapp/javareports?name=B120UP ; https://cdec.water.ca.gov/snow/bulletin120/ |
| SWP initial 2027 allocation | not yet announced (due by 1 Dec) | https://water.ca.gov/News/News-Releases/2025/Dec-25/SWP-Allocation |
| CVP initial 2027 allocation | not yet announced (late Feb in 2025-26) | https://www.usbr.gov/mp/cvo/vungvari/water_allocations_historical.pdf |
| DWR pages and SWP historical Table A allocations | HTTP 403 to automated fetches; SWP past allocations therefore unsourced and not used | https://water.ca.gov/-/media/DWR-Website/Web-Pages/Programs/State-Water-Project/Management/SWP-Water-Contractors/Files/Historical-SWP-allocations-1996-2024-112923.pdf ; https://water.ca.gov/News/News-Releases/2026/May-2026/State-Water-Project-Allocation-Increases-Heading-into-Summer-Months |
| CPC November 2026 outlook | issued 19 Nov; Oct issue is latest | https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/ |
| Snow percent of normal | reported 0% (normal for mid-Nov is near zero); not informative yet | https://cdec.water.ca.gov/reportapp/javareports?name=DLYSWEQ |
| Allocation entered by grower | none; engine allocation check left `no_allocation_entered` | n/a |

## Caveats
- NOAA station rain ends Dec 2025 (Woodland Oct 2024); POWER rain is 50-70% wet vs stations, so POWER is not used for rain chances. The engine, however, still uses POWER/NOAA as documented in its README; its default `out/<id>/strategies.json` baseline (5.47 af/ac at CAR) differs from a fresh `score()` default run (5.19), so the engine output file looks stale; we used fresh runs.
- `raw/` (downloads) is gitignored and recreated by the scripts.
