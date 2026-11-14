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
Segments tile every day of the year (Jan 1 → Dec 31) with no overlaps, so a strip can draw `start_doy..end_doy` rectangles directly in `classes[class].color`; `unknown` is hatched. Markers and transitions are point events on the same axis. Years 2016-2026. 2026 is a partial year: top-level `data_through` (2026-11-11) is the last observation, and days after it are `unknown` (not yet observed). Earlier years are unchanged by the 2026 extension.

Rules (spec B5.1, thresholds U, not tuned): observation used if field clear fraction ≥ 0.5 and ≥ 20 clear pixels; same date S2 over Landsat. water if NDWI median > 0.3 or > 50 % of clear pixels flagged water (SCL 6 / QA bit 7); else NDVI median < 0.20 bare, ≤ 0.35 partial, > 0.35 covered. Days between two observations ≤ 30 days apart take the class of linearly interpolated NDVI (nearest observation if either is water); longer gaps are unknown. green_up = first of 3 consecutive obs > 0.35 after one ≤ 0.35; senescence_harvest = first of 2 consecutive obs each > 0.2 below the 30-day running max (alfalfa cuttings show up as this marker too).

### `out/<preset_id>/grid.geojson` (3D drill-down)
30 m cells in EPSG:32610 (edges on multiples of 30 m) clipped to the polygon, written in EPSG:4326. Feature properties: `cell_id, row, col, area_m2, frac_in_field`, then per layer `ndvi_<key>` (null if no clear pixel) and `n_ndvi_<key>`. Layers (listed in the top-level `layers` array): `ndvi_<year>_q<1-4>` = median over S2 scenes (field clear ≥ 0.5) of the cell mean, 2016-2026 (Q4 2026 runs to 11 Nov), with `n_` = scenes; `ndvi_d_<YYYYMMDD>` = single clear (≥ 0.95) scene nearest 15 Jan/Apr/Jul/Oct of 2021-2023 and 2026, with `n_` = 10 m pixels. Cell value = mean of the 10 m S2 pixels whose centre is in the cell (10 → 30 m mean, B2.14). For CAF the S2/HLS tiles are in UTM 11, so CAF cells are not HLS-aligned (S2 pixels are reprojected point-wise into the 32610 cells).

## Verified / results
Run on 2026-11-14 under Python 3.12.13 with rasterio 1.5.2 (GDAL 3.12) wheels. uv installed them without problems.

**Polygons** (chosen from DWR 2023 field outlines, scored against CDL):
- `car_colusa_rice`: DWR field 0605542, Colusa County, **60.25 ha**, centroid 39.14139 N, -122.08334 W (1.7 km from the spec centre). Of the 189 DWR fields in a ~4 km window, 22 have CDL majority Rice 2021, Fallow 2022 and Rice 2023. This one has the best purity at about 60 ha (min purity 98.8%). DWR 2023 main crop is R1 (rice).
- `caf_tulare_forage`: DWR field 1603054, **Kings County**, **29.47 ha**, centroid 36.23675 N, -119.63470 W (5.1 km from the spec centre). 11 of 209 fields pass the rule (>= 8 Alfalfa/Corn years and >= 3 Alfalfa years). This one has the most alfalfa and corn years. DWR 2023 main crop is F16 (corn/sorghum/sudan group), which matches CDL 2023 Corn. It is not in the Tulare Lake bed. CDL 2023 is corn, and no water was seen in spring 2023.

**Crop history (CDL majority, purity)**
- CAR: 2008 Fallow 96, 2009 Rice 98, 2010 Fallow 97, 2011-2015 Rice 97-99, 2016 Fallow 98, 2017-2019 Rice 98-99, 2020 Fallow 96, 2021 Rice 99, 2022 Fallow 99, 2023 Rice 99, 2024 Rice 99.8, 2025 Rice 99.5. The field has 5 fallow years, all in drought or rotation years.
- CAF: Alfalfa 2008-2010 (99/99/92), 2011 Dbl Crop WinWht/Corn 97, Alfalfa 2012-2015 (98-99), 2016 Corn 88, Alfalfa 2017-2020 (88-96), 2021 Corn 95, 2022 Alfalfa 74, 2023 Corn 95, Alfalfa 2024-2025 (94/96).

**Scenes** (rows in cache; usable = field clear >= 0.5): CAR S2 710 (461 usable, 2015-11..2026-11), Landsat 868 (619); CAF S2 724 (496), Landsat 489 (362). There were 4 Landsat window reads that failed after retries (listed in `landsat.meta.json` `errors`). Those scenes were skipped.

**Checks output** (`uv run python checks/run_checks.py`):
```
PASS | lon/lat order car_colusa_rice | first vertex (x=-122.08658, y=39.13788) -> x is lon in CA range: True, y is lat in CA range: True
PASS | polygon area car_colusa_rice | 60.25 ha in EPSG:32610 (target ~60 ha, accepted 50-150%); centroid 39.14139 N, -122.08334 E
PASS | training box car_colusa_rice | 10.0 x 10.0 km in EPSG:32610
PASS | lon/lat order caf_tulare_forage | first vertex (x=-119.63508, y=36.23316) -> x is lon in CA range: True, y is lat in CA range: True
PASS | polygon area caf_tulare_forage | 29.47 ha in EPSG:32610 (target ~32 ha, accepted 50-150%); centroid 36.23675 N, -119.63470 E
PASS | training box caf_tulare_forage | 10.0 x 10.0 km in EPSG:32610
PASS | CAR CDL 2021 is Rice | majority Rice (98.8% of 670 px)
PASS | CAR CDL 2022 is Fallow/Idle Cropland | majority Fallow/Idle Cropland (99.0% of 670 px)
PASS | CAR CDL 2023 is Rice | majority Rice (99.1% of 670 px)
PASS | CAF CDL alfalfa/corn history | 17/18 years Alfalfa or Corn; Alfalfa [2008, 2009, 2010, 2012, 2013, 2014, 2015, 2017, 2018, 2019, 2020, 2022, 2024, 2025]; Corn [2016, 2021, 2023]
INFO | CAF CDL 2023 | Corn (95.1%)
PASS | NDVI in [-1,1] s2 car_colusa_rice | 1596 values, min -0.336, max 0.994; 710 scenes 2015-11-17..2026-11-11
PASS | clear_frac in [0,1] s2 car_colusa_rice | median 1.00; scenes with clear_frac>=0.5: 461
PASS | NDVI in [-1,1] landsat car_colusa_rice | 2070 values, min -0.433, max 0.963; 868 scenes 2016-01-03..2026-10-29
PASS | clear_frac in [0,1] landsat car_colusa_rice | median 0.97; scenes with clear_frac>=0.5: 619
PASS | NDVI in [-1,1] s2 caf_tulare_forage | 1605 values, min -0.003, max 0.987; 724 scenes 2015-10-05..2026-11-11
PASS | clear_frac in [0,1] s2 caf_tulare_forage | median 1.00; scenes with clear_frac>=0.5: 496
PASS | NDVI in [-1,1] landsat caf_tulare_forage | 1119 values, min -0.009, max 0.938; 489 scenes 2016-01-13..2026-11-08
PASS | clear_frac in [0,1] landsat caf_tulare_forage | median 0.98; scenes with clear_frac>=0.5: 362
PASS | usable obs per year car_colusa_rice (total(S2/Landsat), need >=12) | 2016:66(10/56) 2017:67(16/51) 2018:90(47/43) 2019:81(40/41) 2020:98(51/47) 2021:89(45/44) 2022:96(51/45) 2023:104(48/56) 2024:103(49/54) 2025:94(51/43) 2026:90(53/37)
PASS | usable obs per year caf_tulare_forage (total(S2/Landsat), need >=12) | 2016:46(13/33) 2017:50(19/31) 2018:81(52/29) 2019:77(52/25) 2020:77(49/28) 2021:82(54/28) 2022:70(51/19) 2023:91(51/40) 2024:74(47/27) 2025:80(57/23) 2026:73(49/24)
PASS | CAR 2022 calendar mostly bare | bare 297 of 365 known days (81%); all: {'unknown': 0, 'bare': 297, 'partial': 34, 'covered': 0, 'water': 34}
FAIL | CAR winter (Nov-Feb after a CDL rice year) reads water rather than bare | 3/6 winters with water days > bare days | 2017/18: water 19 bare 54 partial 5 covered 0 unknown 42; 2018/19: water 0 bare 74 partial 46 covered 0 unknown 0; 2019/20: water 48 bare 37 partial 35 covered 0 unknown 0; 2021/22: water 37 bare 58 partial 25 covered 0 unknown 0; 2023/24: water 38 bare 36 partial 46 covered 0 unknown 0; 2024/25: water 31 bare 25 partial 64 covered 0 unknown 0
INFO | CAF spring 2023 (Mar-Jun) water on the field | no water seen: days {'unknown': 0, 'bare': 34, 'partial': 42, 'covered': 46, 'water': 0}; 36 obs, max field-median NDWI -0.241
PASS | grid car_colusa_rice | 724 cells, clipped area 60.25 ha, 60 NDVI layers, values in [-1,1]: True
PASS | grid caf_tulare_forage | 365 cells, clipped area 29.47 ha, 60 NDVI layers, values in [-1,1]: True
---- 23 PASS, 1 FAIL, 2 INFO
```

What the data says:
- CAR 2022 is 81% bare. The 34 water days are in Jan 2022, when S2 SCL marked 61-78% of the field as water and the field-median NDWI was only about 0.0-0.13. So the water class comes from the mask, not from the NDWI > 0.3 rule.
- Winter flooding is only partly seen: water beat bare in 3 of 6 post-rice winters (the check needs more than half, so it FAILs). Some winters show near-zero NDVI with NDWI around 0 and no SCL water (e.g. 2024-01-29: NDVI 0.01, NDWI -0.02). These may be shallow flood over stubble that the NDWI > 0.3 threshold misses, or the field may not have been flooded. DSWx would settle this, but it needs Earthdata (see Blocked). Thresholds were not changed.
- CAF spring 2023: no water. Max field-median NDWI was -0.24 from March to June.
- Markers: CAF alfalfa years show 9-14 senescence_harvest markers per year, which are cuttings. Corn years show 3-6.
- B10.1 check 7's "consensus vs modelled baseline >= 60%" needs the engine's modelled cover. It is not part of this chunk and is not run here.
- Cross-sensor note: over bare soil in 2022, Landsat field NDVI is about 0.04 higher than S2 (0.19 vs 0.15). No harmonisation is applied, and S2 wins when both sensors observe the same day.


## 2026 update (run 2026-11-14)
`s2.parquet` / `landsat.parquet` already held 2026 (STAC search on 14 Nov found no scene that is not cached; the other items are same-day duplicates of another tile). Latest scenes: CAR S2 2026-11-11 (75 scenes in 2026, 53 usable), Landsat 2026-10-29 (70, 37 usable on days without S2); CAF S2 2026-11-11 (72, 49 usable), Landsat 2026-11-08 (38, 24 usable). `detector.py` now covers 2016-2026 and `grid.py` adds 2026 quarter medians and 2026 key-date scenes. Re-running `timeseries` re-reads the whole archive, so only do it when new scenes exist.

## Blocked
- **HLS (B2.4), MODIS (B2.7), ECOSTRESS (B2.8), OPERA DSWx (B2.11)**: these need a NASA Earthdata login, which we do not have, so nothing was attempted. With a login, DSWx would give an independent water check for the CAR winter floods and the CAF 2023 flood extent. HLS would be the spec's primary 30 m record.
- **OpenET 30 m (B2.12, B7.3)**: needs an OpenET API key. Not attempted.
- **CropScape CDL API** `https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLFile?year=2022&bbox=...`: `curl: Operation timed out after 60006 milliseconds with 0 bytes received`, and again at 240 s. Not needed, because the CroplandCROS image service works.
- **Earth Search S2** (`sentinel-2-c1-l2a`): not blocked, but incomplete for these fields (0 items in 2016, 6 in 2022 at CAR). Planetary Computer is used instead.
- **4 Landsat scenes** failed to read after 4 retries with GDAL `/vsicurl/` errors on MPC blobs: LC08 044033 2022-11-03, LC08 045033 2022-07-21, LC09 044033 2022-05-19 (CAR), and LC09 042035 2022-04-03 (CAF). Re-running `timeseries landsat` may recover them.
- **Check FAIL (data, not a bug)**: "CAR winter reads water rather than bare", 3/6 winters. See above.

