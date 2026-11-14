# backend/regional: regional ground + weather data (no-auth sources)

Own `uv` project (Python 3.12). Run from this directory:

```
uv sync
uv run python src/fetch_power.py   # NASA POWER 1981 -> today (latest published day) -> data/cache/<id>/power.{parquet,meta.json}
uv run python src/derive.py        # Hargreaves ETo + risk days -> out/<id>/{daily_derived.parquet,risk_days_by_year.json,eto_monthly.json}
uv run python src/fetch_cdec.py    # CDEC SHA/ORO/PNF storage 2015-2025 -> cdec.*
uv run python src/fetch_usdm.py    # US Drought Monitor county weekly 2015-2025 -> usdm.*
uv run python src/fetch_ssurgo.py  # SSURGO soil (reads backend/field/polygons/<id>.geojson if present) -> soil.json
uv run python src/fetch_ncei.py    # GHCN-Daily nearest long-record stations, 1981 -> today -> ncei.*
uv run python checks/run_checks.py # PASS/FAIL (last output saved in out/checks_output.txt)
```
Each script is independent. Caches: `data/cache/<preset_id>/`. Every `*.meta.json` records url, params, fetched_at, units, native resolution, fill value, auth.

## Verified facts that differ from / refine the spec
- CDEC sensor 15 = STORAGE (AF) confirmed live for SHA, ORO, PNF (sensor 6 = RES ELE, ft). Dates are non-zero-padded (`2023-1-1 00:00`); for some records `obsDate` is a day after `date`. We key on `date`. 4018 daily rows per station, 2015-01-01..2025-12-31; 8 missing values (ORO 1, PNF 7).
- USDM service works with no key. `statisticsType=1` is cumulative (d2 = % area in D2 or worse), `2` is categorical. Both are cached (column `stat`). First map date is 2014-12-30 (valid into 2015). 575 weeks per county.
- CAF centre (36.20 N, -119.60 W) lies in **Kings County (06031)** per the Census geocoder, not Tulare; Tulare (06107) is cached as adjacent context.
- POWER header fill value is -999; ALLSKY_SFC_SW_DWN is -999 for 1981-01-01..1983-12-31 (kept as NaN). `time_standard` is LST. Point request returns the 0.5 deg cell; elevation 57.4 m (CAR) / 106.1 m (CAF).
- SSURGO: map units/components/horizons via SDA SQL work as in spec. Per-map-unit area share uses `mupolygon.mupolygongeo.STIntersection(...).STArea()` (degrees^2, relative only). Texture column is `chtexturegrp.texture` (not `texcl`). AWC is cm/cm; stored as mm/m (x1000). Footprint currently the 400 m placeholder square (no field polygon existed at run time); re-run `fetch_ssurgo.py` after `backend/field/polygons/<id>.geojson` lands.
- NCEI stations: the search service `https://www.ncei.noaa.gov/access/services/search/v1/data` finds candidates by bbox. The nearest CAR station, Williams (USC00049677, 4 km), has data only to 1988-10, so it is not used. Selected (nearest with >=70% 1981-2025 coverage of PRCP/TMAX/TMIN):
  - CAR: USC00041948 Colusa 2 SSW (7.6 km), USC00049699 Willows 6 W (45 km), USC00049781 Woodland 1 WNW (58 km)
  - CAF: USC00042012 Corcoran Irrigation Dist. (11.5 km), USC00043747 Hanford 1 S (13.3 km), USC00049367 Visalia (30.5 km)

## Derived products
- Hargreaves ETo = FAO-56 eq. 52 with Tmean=(Tmax+Tmin)/2, Ra from eq. 21 (latitude, day of year). Annual mean 1981-2025: CAR 1458 mm, CAF 1582 mm. Uncorrected for local bias (no CIMIS yet); spec range +/-15%.
- Risk days (spec B5.3): frost Tmin<=0; hard frost <=-2; heat Tmax>=35; severe >=40; heatwave day = in a >=3-day run of heat days; extreme rain P>=25 mm, 3-day>=75 mm, and 95th percentile of wet days (CAR 32.4 mm, CAF 22.6 mm). POWER rain is a ~50 km reanalysis and smooths extremes, so rain counts are likely low-biased; POWER 2 m Tmax may also be biased vs stations (51 "severe heat" days at CAR in 2022 should be checked against NCEI/CIMIS before display).

### Cross-check: POWER >= 40 C days vs NCEI stations (done 2026-11-14, `backend/api/build_real.py` -> `validation.json`)
**POWER is badly high for heat extremes.** CAR 2022: POWER 51 days with Tmax >= 40 C; NCEI Colusa 2 SSW (USC00041948, 7.6 km) 12 days (359 days observed), Woodland 1 WNW (USC00049781, 58 km) 14 (355 observed), Willows 6 W (USC00049699, 45 km) 30 (364 observed). So POWER is about 1.7-4x the stations (2021: 51 vs 7/15/34; 2023: 22 vs 9/0/8). The station annual maxima in 2022 were 43.9-46.7 C vs POWER 48.3 C. Over 1981-2025, monthly Tmax bias (POWER minus the 3-station mean) is +0.4 C at CAR but **+3.4 C in Jul-Aug**; at CAF it is +2.1 C overall and +3.8 C in summer (CAF 2022: POWER 60 days vs 25/9/9). Tmin is +0.9 C (CAR) and +2.0 C (CAF). Monthly rain: POWER total is +54% (CAR) and +68% (CAF) vs the station mean (R2 0.92 / 0.89). The thresholds (35 C heat, 40 C severe heat) were not changed; counts of heat days, heatwave days, and the engine's exposed-heat days are therefore high-biased and should be shown with this caveat (MERRA-2 0.5 x 0.625 deg cell smooths the valley floor and reads warm in dry summers; CIMIS would settle it).

## What is verified
`checks/run_checks.py` (see `out/checks_output.txt`). Known real-data contradiction: Jan-Mar 2023 is **not** top-3 at CAR in POWER (rank 8/45) or NCEI (rank 5-7); it is rank 1 at CAF in POWER and all three NCEI stations.

## Blocked (needs keys / login; not attempted)
| Source | Why blocked | What unblocks it |
|---|---|---|
| CIMIS station ETo (stn 250 etc.) | needs appKey; not attempted | free CIMIS API key from https://et.water.ca.gov (register account) |
| OpenET point/polygon ET | needs API key; not attempted | OpenET API key (https://etdata.org / openet-api.org account) |
| GPM IMERG daily | Earthdata login required | NASA Earthdata account (+ `~/.netrc`) |
| SMAP L3/L4 | Earthdata login required | same Earthdata account |
| GRACE/GRACE-FO DA | Earthdata login required | same Earthdata account |
| HLS / MODIS / ECOSTRESS | Earthdata login (owned by field chunk) | same Earthdata account |
| NASS Quick Stats, AMS My Market News | API keys | NASS Quick Stats key; AMS MARS API key |
No endpoint in the no-auth set failed.

## 2026 update (run 2026-11-14)
- POWER now runs 1981-01-01..2026-11-11 (16751 days, the latest day POWER had; values for 2026 are identical to `backend/nasa` `power_nrt.parquet`, which is the same near-real-time service, so treat 2026 as provisional). `derive.py` recomputed ETo and risk days; the 95th-percentile rain threshold (CAR 32.4 mm, CAF 22.6 mm) and the monthly ETo climatology stay on 1981-2025. 2026 rows in `risk_days_by_year.json` carry `partial_year_through` and `days_with_data`; `eto_monthly.json` has `null` for months with no data.
- NCEI GHCN-Daily is fetched through today; station selection still uses 1981-2025 coverage, so the same stations are kept. Latest observed day: CAR Colusa 2 SSW 2026-09-30, Willows 6 W 2026-06-14 (precipitation and temperatures), Woodland 1 WNW 2024-10-22 (no 2026 data); CAF Corcoran 2026-10-28, Hanford 2026-11-09, Visalia 2026-11-10 (precip and Tmax/Tmin; row dated 11-11). CAR station data therefore ends in autumn; POWER fills the gap.
