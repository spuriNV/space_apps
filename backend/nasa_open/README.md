# backend/nasa_open: NASA data that needs no Earthdata login

Three outputs that raise the "Relevance" score (rubric section 4) without accounts or keys. Python 3.12, `uv`.

```bash
cd backend/nasa_open && uv sync
uv run python -m nasa_open.terrain      # NASADEM  -> out/<id>/terrain.json
uv run python -m nasa_open.hls          # HLS      -> data/cache/<id>/hls.parquet + hls.meta.json (~12 min through today)
uv run python -m nasa_open.iss          # ISS      -> data/cache/<id>/iss/{iss.json,*.jpg}
uv run python checks/run_checks.py      # PASS/FAIL (ISS URL check needs the network)
```
Needs `backend/field/polygons/<id>.geojson`, `backend/field/out/<id>/grid.geojson` and `data/cache/<id>/{s2,landsat}.parquet` from backend/field.

## 1. NASADEM terrain (`out/<id>/terrain.json`)
- Source: NASADEM HGT v001 (NASA JPL, reprocessed SRTM, 1 arc-second, ~30 m) via Microsoft Planetary Computer `nasadem`, anonymous SAS token from the `planetary-computer` package. https://planetarycomputer.microsoft.com/dataset/nasadem
- Credit: "NASADEM, NASA JPL / LP DAAC (doi:10.5067/MEASURES/NASADEM/NASADEM_HGT.001), via Microsoft Planetary Computer". Licence: public domain (NASA).
- Method: bilinear resample onto the same 30 m EPSG:32610 lattice as `backend/field/out/<id>/grid.geojson`; slope = Horn 3x3, in percent; low spot = cell at least 1 m below the mean of cells within 150 m (a 300 m window, spec B7.3, U).
- Contents: `field_summary` (SourcedNumbers: `slope_mean_pct`, `slope_p90_pct`, `elev_m`, `low_spot_fraction`, plus `*_raw`), `field_stats`, `box_stats` (~2 km box, 68 x 68 cells), `cells[]` (one per grid `cell_id`: `elevation_m`, `slope_pct`, `slope_pct_smoothed`, `rel_elev_m_smoothed`, `low_spot_smoothed`, `low_spot` raw), `box_2km` (rasters as nested lists with origin/shape for the 3D view).
- **Noise caveat (important):** NASADEM is a radar surface model stored in whole metres. Over flat farmland single 30 m pixels carry +-2-4 m noise, so raw slope reads 2-4 % even on a levelled rice field. The headline `slope_*` and `low_spot_fraction` use a 5x5 (150 m) mean DEM; the raw values are kept as `*_raw`. Low spots are candidates (frost or ponding), not surveyed depressions; `low_spot_fraction` stays `verified: false`.
- Use: slope input for the engine's erosion score (use the smoothed value), in-field low-spot/erosion zones in the 3D drill-down, "levelled field, slope zones not meaningful" text for rice (spec B7.3).

## 2. HLS (`data/cache/<id>/hls.parquet`, `hls.meta.json`)
- Source: HLS v2.0 (NASA/USGS Harmonized Landsat Sentinel-2, HLSL30 + HLSS30, 30 m) via Planetary Computer `hls2-l30` and `hls2-s30`. Anonymous. (NASA's own copy at LP DAAC needs Earthdata login.)
- Credit: "HLS v2.0, NASA/USGS (Masek et al. 2021), doi:10.5067/HLS/HLSL30.002 and HLSS30.002; hosted by Microsoft Planetary Computer". Licence: public domain (NASA/USGS).
- Method: same as `backend/field/timeseries.py`: only the polygon window of each scene is read; NDVI = (NIR-Red)/(NIR+Red) with the narrow NIR band (B05 on HLSL30, B8A on HLSS30), NDWI = (Green-NIR)/(Green+NIR); clear pixels = Fmask without cloud, adjacent cloud/shadow, shadow, snow/ice (water kept). One row per scene: field median and p10/p90, `clear_frac`, `water_frac`.
- **Coverage limit:** Planetary Computer's copy only holds HLSL30 from 2017-08 (2017: ~13 and 2018: 1-4 usable scenes, none in 2016 or 2019) and HLSS30 from 2020-01. So 2016 and most of 2017-2019 cannot be filled from HLS; use backend/field's Sentinel-2/Landsat series for those years. Item metadata of some 2017-2021 scenes names a southern-hemisphere CRS (EPSG:327xx) although the files are 326xx; the reader uses the file's own CRS.
- Use: a NASA-native NDVI/NDWI calendar (HLS rows can feed the same detector in backend/field), and a cross-check of the ESA Sentinel-2 series.

## 3. ISS astronaut photography (`data/cache/<id>/iss/`)
- Source: NASA JSC Gateway to Astronaut Photography of Earth, https://eol.jsc.nasa.gov (public search pages and TSV export; the JSON Photos Database API needs a free key by email, not used).
- Credit line (confirmed on https://eol.jsc.nasa.gov/FAQ/, "Conditions of use"): **"Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center"**; also print the photo ID (mission-roll-frame) and eol.jsc.nasa.gov. NASA keeps no copyright on these photos.
- `iss.json` holds, per photo: `photo_id, date, time_gmt, center_lat, center_lon` (stored to 0.1 degree), `lens_mm, camera, tilt_deg, cloud_pct_class, features, altitude_km, page_url, image_url` (full size, about 2 MB), `thumb_url, credit, local_file`. 3 photos per area (6 total) are downloaded.
- How found: coordinate-range search (`CoordinateRangeSearch.pl`, cataloged photos with a centre point) and a "sacramento valley" feature search. Raw results are saved in `out/iss_search/*.tsv`.
- **What exists:** no cataloged photo with a centre point over either area in 2021-2023 (including the 2023 Tulare Lake re-flooding). Uncataloged 2021-2023 frames have only a spacecraft nadir point; those spot-checked as thumbnails (e.g. ISS068-E-30327, ISS065-E-471067, ISS070-E-129298) show mountains or other regions, so none were used. The photos taken are 3-4 March 2020 (ISS062, 400 mm, a wet late winter) over Sutter Buttes / Sacramento Valley and over the Kings River / Lemoore area. Earlier Tulare-area frames from 29 Oct 2014 (ISS041-E-1039xx, drought) are listed in the search TSV but not downloaded.
- Use: "seen from the ISS" panel in the pitch and the 3D view. Centre points are approximate: say "near", not "of this field".

## Blocked / limits
- HLS before mid-2017 (before 2020 for HLSS30) on Planetary Computer; NASA's full 2013+ archive requires Earthdata login.
- ISS photos of 2021-2023 events over these two areas: none cataloged with a centre point. The Gateway's JSON API needs a key; the website's own search endpoints were slow and sometimes returned 502 (feature searches for "tulare lake" returned nothing).
- NASADEM vertical noise limits slope and low spots on flat fields (see above).

## 2026 update (run 2026-11-14)
`nasa_open.hls` now defaults to `--end` today. Planetary Computer HLS reaches 2026-11-04 at CAR (968 scenes, 111 in 2026, 82 usable) and 2026-11-01 at CAF (1477 scenes, 180 in 2026, 128 usable; last usable 2026-10-27). Rows through 2025 are unchanged (no scene dropped).
