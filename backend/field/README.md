# backend/field — field polygons, CDL history, Sentinel-2/Landsat series, rule detector, 30 m grid

Owner chunk for spec B1 (polygons), B2.5 / B2.6 (S2, Landsat), B2.12 (CDL), B2.14 (field grid), B5.1 (rule detector).
No accounts or keys are used anywhere in this chunk.

## Run

```bash
cd backend/field
uv sync
uv run python -m fieldshift_field.cdl              # 1a. CDL 2008-2025, 16 km box per preset -> data/cache/<id>/rasters/cdl_<yr>.tif
uv run python -m fieldshift_field.select_fields    # 1b. pick polygons -> polygons/<id>.geojson + <id>_training_box.json
uv run python -m fieldshift_field.crop_history     # 2.  -> out/<id>/crop_history.json, data/cache/<id>/cdl.parquet
uv run python -m fieldshift_field.timeseries all   # 3.  -> data/cache/<id>/{s2,landsat}.parquet + .meta.json (~10-25 min)
uv run python -m fieldshift_field.detector         # 4.  -> out/<id>/calendar.json
uv run python -m fieldshift_field.grid             # 5.  -> out/<id>/grid.geojson
uv run python checks/run_checks.py                 # PASS/FAIL lines (local files only)
```

Every step reads only what the previous steps cached; steps 4, 5 and the checks need no network.

## Sources actually used (and why)

| Data | Endpoint (no account) | Notes |
|---|---|---|
| CDL 2008-2025 | USDA CroplandCROS ImageServer `https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer` (`exportImage`, mosaic locked to one year's raster, `imageSR=5070`, nearest neighbour, CDL pixel grid) | 30 m to 2023, **10 m in 2024 and 2025**. Class names read from the service's `rasterAttributeTable` (saved in `data/cache/<id>/cdl_legend.json`): 1 Corn, 3 Rice, 36 Alfalfa, 61 Fallow/Idle Cropland, 24 Winter Wheat, 225 Dbl Crop WinWht/Corn ... — the spec's codes are confirmed. |
| — not used | Planetary Computer `usda-cdl` | Only 2008-2021, misses 2022 fallow year. |
| — not used | CropScape `nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLFile` | Timed out (no bytes after 60 s and 240 s) on 2026-11-14. |
| Field boundaries | DWR / Land IQ Statewide Crop Mapping 2023 (final), ArcGIS MapServer `https://utility.arcgis.com/usrsvcs/servers/d94e891e00364e49a2ed9e9e2e27837d/rest/services/Planning/i15_Crop_Mapping_2023/MapServer/0` | Real field outlines instead of drawn rectangles; DWR's own 2023 crop code is kept in the polygon properties as a cross-check. |
| Sentinel-2 L2A | Planetary Computer STAC `sentinel-2-l2a` (anonymous SAS via `planetary-computer`) | Full archive 2015-06 → today. B02 B03 B04 B08 B11 + SCL. |
| — not used | Earth Search `sentinel-2-c1-l2a` / `sentinel-2-l2a` | Incomplete over these fields: c1 had 0 items in 2016 and 6 in 2022 at the Colusa field; old l2a had 0 in 2016. |
| Landsat C2 L2 | Planetary Computer STAC `landsat-c2-l2`, Landsat 7/8/9, Tier 1 only, 2016 → today | blue green red nir08 swir16 + qa_pixel. |

Only the polygon window is read from each COG (GDAL range requests); no whole scenes are downloaded.

## Outputs

### `polygons/<preset_id>.geojson`
FeatureCollection with one Polygon, EPSG:4326, **[lon, lat]**. `properties`: `preset_id, name, area_ha, centroid{lon,lat}, crs, crs_working, boundary_source{..., dwr_unique_id, dwr_attributes}, selection_rule, cdl_majority_by_year, candidates_considered`.
`polygons/<preset_id>_training_box.json`: 10 km square in EPSG:32610 centred on the field (`bbox_epsg32610`, `bbox_epsg4326` = minx,miny,maxx,maxy, `geometry_epsg4326`). The CDL rasters cached for the preset (16 km box) cover it.

### `out/<preset_id>/crop_history.json`
`{preset_id, source{...}, method, by_year{"2008":"Rice",...}, years:[{year, majority_code, majority_name, purity_pct, n_pixels, pixel_res_m, top_classes:[{code,name,pct}]}], caveats}`. `by_year` has the shape of `Location.crop_history` in spec B3.

### `data/cache/<preset_id>/`
`cdl.parquet` (year, code, name, fraction, n_pixels inside polygon) + `cdl.meta.json` + `cdl_legend.json` + `rasters/cdl_<year>.tif` (COG, EPSG:5070).
`s2.parquet`, `landsat.parquet` one row per scene date: `scene_id, datetime, date, platform, tile|path_row, epsg, n_pixels_poly, n_valid, clear_frac, water_frac, {ndvi,ndwi,bsi}_{med,p10,p90}`, S2 also `scl_0..scl_11` (share of polygon pixels per SCL class) and `processing_baseline`; Landsat also `fill_frac, cloud_frac, shadow_frac`. Rows with `clear_frac = 0` are kept (NaN indices) so observation gaps are visible. `*.meta.json` follows spec B2 general rules (`url, params, fetched_at, footprint_geojson, native_res_m, timestep, units, fill_value, auth`) plus item/row/error counts.
`rasters/s2_ndvi_stack.npz` + `.json`: per-scene 10 m clear-pixel NDVI windows (float16) used by the grid.

Index definitions: NDVI = (NIR−Red)/(NIR+Red); NDWI = (Green−NIR)/(Green+NIR) (McFeeters); BSI = ((SWIR1+Red)−(NIR+Blue))/((SWIR1+Red)+(NIR+Blue)).
Masks: S2 clear = SCL ∈ {2 dark area, 4 vegetation, 5 not vegetated, 6 water} (2 kept because flooded checks can read as dark area); S2 processing baseline ≥ 04.00 has the −1000 DN offset removed. Landsat clear = QA_PIXEL bit 6 (clear) or bit 7 (water) and none of bits 0,1,3,4,5; reflectance = 2.75e-5·DN − 0.2.

### `out/<preset_id>/calendar.json` (frontend calendar strip)

```jsonc
{
  "preset_id": "car_colusa_rice", "generated_at": "...", "detector": "rule_ndvi",
  "classes": { "unknown": {"label": "...", "color": "#bdbdbd", "pattern": "hatched"},
               "bare": {...,"color":"#8c6d46"}, "partial": {...}, "covered": {...}, "water": {...,"color":"#2b7bba"} },
  "method": { "bare_lt": 0.2, "covered_gt": 0.35, "water": "...", "max_interp_gap_days": 30, ... },
  "sources": [ {"id","title","url","accessed","verified"} ],
  "years": [
    { "year": 2022,
      "segments":   [ {"start":"2022-01-01","end":"2022-01-08","start_doy":1,"end_doy":8,"days":8,"class":"bare","n_obs":1}, ... ],
      "transitions":[ {"date":"2022-01-09","from":"bare","to":"water","after_unknown_gap":false}, ... ],
      "markers":    [ {"date":"2021-06-20","type":"green_up","ndvi":0.41},
                      {"date":"2021-09-30","type":"senescence_harvest","ndvi":0.4,"from_30d_max":0.9} ],
      "summary":    { "days_by_class": {"unknown":0,"bare":317,...}, "n_obs":56, "n_obs_s2":51, "n_obs_landsat":5 },
      "observations":[ {"date","sensor":"s2|landsat","ndvi","ndwi","bsi","clear_frac","class"} ] } ] }
```
Segments tile every day of the year (Jan 1 → Dec 31) with no overlaps, so a strip can draw `start_doy..end_doy` rectangles directly in `classes[class].color`; `unknown` is hatched. Markers and transitions are point events on the same axis. Years 2016-2025.

Rules (spec B5.1, thresholds U, not tuned): observation used if field clear fraction ≥ 0.5 and ≥ 20 clear pixels; same date S2 over Landsat. water if NDWI median > 0.3 or > 50 % of clear pixels flagged water (SCL 6 / QA bit 7); else NDVI median < 0.20 bare, ≤ 0.35 partial, > 0.35 covered. Days between two observations ≤ 30 days apart take the class of linearly interpolated NDVI (nearest observation if either is water); longer gaps are unknown. green_up = first of 3 consecutive obs > 0.35 after one ≤ 0.35; senescence_harvest = first of 2 consecutive obs each > 0.2 below the 30-day running max (alfalfa cuttings show up as this marker too).

### `out/<preset_id>/grid.geojson` (3D drill-down)
30 m cells in EPSG:32610 (edges on multiples of 30 m) clipped to the polygon, written in EPSG:4326. Feature properties: `cell_id, row, col, area_m2, frac_in_field`, then per layer `ndvi_<key>` (null if no clear pixel) and `n_ndvi_<key>`. Layers (listed in the top-level `layers` array): `ndvi_<year>_q<1-4>` = median over S2 scenes (field clear ≥ 0.5) of the cell mean, 2016-2025, with `n_` = scenes; `ndvi_d_<YYYYMMDD>` = single clear (≥ 0.95) scene nearest 15 Jan/Apr/Jul/Oct of 2021-2023, with `n_` = 10 m pixels. Cell value = mean of the 10 m S2 pixels whose centre is in the cell (10 → 30 m mean, B2.14). For CAF the S2/HLS tiles are in UTM 11, so CAF cells are not HLS-aligned (S2 pixels are reprojected point-wise into the 32610 cells).

## Verified / results
RESULTS_PLACEHOLDER

## Blocked
BLOCKED_PLACEHOLDER
