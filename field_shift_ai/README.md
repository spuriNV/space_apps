# field_shift_ai: AI models (spec B6.1 bare-field detector, B6.2 crop-stress detector)

This folder sits at the root of `space_apps/` and is separate from the team's `backend/ai/` chunk; it does not
read or change anything there.

Start with [GUIDE.md](GUIDE.md): it explains the code, how to run it, the data and the current results.

- `field_shift_models/` is the reusable model library and CLI (`run_models.py bare | stress | demo`).
- `fs_real/` runs both models on real data for the California rice preset (39.15 N, 122.10 W, a 200 m box
  at the spec's preset centre). It includes the downloaded inputs (`data/`) and the model outputs (`out/`).
  `./run_all.sh` rebuilds everything.

The outputs in `fs_real/out/` are the results reported in GUIDE.md §6. They are committed unchanged.

Not yet integrated with the rest of the backend: this uses its own 200 m box rather than the DWR field
polygon in `backend/field/polygons/`, the preset id `ca_colusa_rice` rather than `car_colusa_rice`, and it
does not yet write `out/<preset>/models.json` in the shape `backend/api` serves.
