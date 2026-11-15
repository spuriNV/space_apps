# Farm catalog (`backend/catalog`)

About 445 real fields across California, British Columbia, ten US farm regions (215 fields, USDA Crop Sequence Boundaries outlines via `select_us.py`), the Canadian Prairies and Ontario / Quebec (42 fields, AAFC ACI patches via `select_can.py`; SLC soil for AB/SK/MB/ON/QC in `slc_can.json.gz`, built by `slc_bc.py --rest`), pre-built with the any-location tier-1 pipeline (`backend/api/app/anyloc`) so the map can open them instantly. Served by `GET /api/catalog` and `GET /api/locations/<pt_id>` (`_source: "catalog"`); see `backend/api/README.md`.

| Script | Writes | Notes |
|---|---|---|
| `slc_bc.py` | `backend/api/app/anyloc/slc_bc.json.gz` | The 463 BC polygons of AAFC Soil Landscapes of Canada v3.2 that have soil tables, simplified to ~100 m, with `backend/bc/fetch_slc.py`'s 0-100 cm summary. Read by BC taps at run time. The 36 MB national zip is cached once under `data/cache/_slc/` (git-ignored) or passed with `--zip`. |
| `select.py` | `out/selection.json` | California: DWR / Land IQ 2023 polygons, 20-300 acres, by area (Sacramento Valley, Delta, San Joaquin Valley, Imperial / Coachella, Central Coast, North Coast) and crop group, kept when the 2023 CDL at the interior point agrees. BC: AAFC ACI 2025 + 2024 patches (ImageServer `exportImage`) in the Okanagan, Shuswap / Salmon Valley, Thompson / Kamloops, Fraser Valley, Peace River and Creston; the ParcelMap BC parcel clipped to the ALR must contain the point, be 20-300 acres and be at least half that crop group. Farthest-point spread per cell, every pair at least 2 km apart. Names from TIGERweb places or the Canadian Geographical Names Database. |
| `build.py` | `backend/api/out/catalog/<pt_id>/location.json`, `strategies.json.gz`, `index.json` | Runs `anyloc.build.analyse` three points at a time (retries errored tier-1 sections), validates against `schemas/location.schema.json`. Daily rows are not stored. |

Run:

```
cd backend/catalog && uv run python slc_bc.py --zip /path/to/ca_all_slc_v3r2.zip   # once
cd backend/catalog && uv run python select.py                                       # --only ca|bc keeps the other region
cd backend/api && uv run python ../catalog/build.py                                 # --missing, --only id,id, --index-only
```

Reserve and tribal land are not excluded (no special handling was asked for); a catalog field on such land carries `land_status` and `nation_tools` like any tapped point.
