# Field Shift B6.1 + B6.2 on real California data (ca_colusa_rice, 39.15 N 122.10 W)

Run order: `python3 build_ca_obs.py && python3 build_ca_weekly.py && python3 run_b61.py && python3 run_b62.py`
then `python3 plot_b61.py` / `python3 plot_b62.py "<feature list>"`.

## Data actually used (all real, pulled 2026-11-14)
| file | source | notes |
|---|---|---|
| data/fs_s2_ca_colusa_rice.csv | ESA Copernicus Sentinel-2 C1 L2A, Earth Search (AWS), tile 10SEJ | 200 m box at the preset centre; field-median reflectance on SCL-valid pixels + SCL class fractions; 2019-2025, scenes with cloud <= 90% |
| data/fs_s2_ca_colusa_rice_2022_l2a.csv | Sentinel-2 standard L2A (C1 has only 6 scenes in 2022 here) | baseline >= 04.00 COGs already harmonised: +0.1 added back in the merge (checked against C1 on shared dates, diff ~0.003) |
| data/fs_power_ca_colusa_rice.csv | NASA POWER daily point API (AG community), 2000-2025 | T2M_MAX/MIN, PRECTOTCORR, etc.; Hargreaves ETo computed |
| data/fs_modis_ca_colusa_rice.csv | NASA MOD13Q1.061 NDVI via Microsoft Planetary Computer point API | 2000-2025, QA pixel_reliability 0/1 kept |
| data/fs_cdl_ca_colusa_rice.csv | USDA NASS CDL via CropScape API | 2018-2025: 3x3 points, all Rice except 2022 = 61 Fallow/Idle; 2015-2017: 3 diagonal points, all Rice (replicated to 9 columns) |

| data/fs_power_soilwet_ca_colusa_rice.csv | NASA POWER GWETTOP/GWETROOT (GEOS/MERRA-2), 2000-2025 | SMAP stand-in: same-week percentile of surface soil wetness |
| data/fs_modis_lst_ca_colusa_rice.csv | NASA MOD11A2.061 day LST 1 km via Planetary Computer, 2015-2025 | ECOSTRESS stand-in: LST minus POWER Tmax, QC bits 0-1 <= 01 |

| data/fs_climateserv_ca_colusa_rice.csv | NASA SERVIR ClimateSERV API (no login), 0.06 deg box | ESI 4-week (2015-2025-07), NASA-USDA enhanced SMAP surface SM (2015-04..2022-08), GPM IMERG late daily (2015..2024-06) |

Which source fed each week is recorded in weekly_ca.csv (sm_source, esi_source, rain_source, lst_source).
Stand-ins: IMERG 7/30-day rain -> POWER PRECTOTCORR (IMERG needs GES DISC). HLS -> Sentinel-2 L2A directly.
SMAP -> POWER GWETTOP (model, ~50 km, no irrigation). ECOSTRESS LST -> MODIS LST (1 km, 8-day). ESI: none yet.
The builders prefer the real AppEEARS files automatically when they are present in data/appeears/.
Pending: SMAP SPL3SMP_E.006, ECOSTRESS ECO_L2T_LSTE.002 + ECO_L4T_ESI.002 (AppEEARS tasks submitted; drop the
`*results.csv` files into data/appeears/ and rerun build_ca_weekly.py / build_ca_obs.py / run_b62.py).

## Outputs (out/)
bare_cover_model_reports_{year,ca_fallow}.json, bare_cover_predictions_*.csv, bare_cover_transitions_*.csv,
stress_model_reports.json, stress_summary.json, stress_weekly_flags.csv, b61_ca_calendar.png, b62_ca_stress.png
