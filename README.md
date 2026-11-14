# Field Shift

NASA Space Apps Challenge 2026, Vancouver: **Field Shift: Adapting Farms with NASA Data**. A crop-rotation planner for two California example farms (Colusa rice, Kings County forage), built on NASA Earth data. Start with [docs/field-shift-plan.md](docs/field-shift-plan.md); build rules are in [CONTRACT.md](CONTRACT.md).

## Try it after pulling

You need **Node 20+** and **[uv](https://docs.astral.sh/uv/)** (it installs Python 3.12 for you). No API keys are needed for anything below.

### The three design options (frontend)

Each runs on its own port; open the URL after `npm run dev`. They all use mock data and say so on screen.

```sh
cd frontend/variants/a-maps   && npm install && npm run dev   # A, Maps classic    → http://127.0.0.1:5171
cd frontend/variants/b-earth  && npm install && npm run dev   # B, Earth explorer  → http://localhost:5172
cd frontend/variants/c-split  && npm install && npm run dev   # C, Split workspace → http://localhost:5173
```

Things to try: pick a field, then **scroll into it on the map** to get the 3D view; open "Your field's year" and "Compare". Screenshots of all six screens per option are in `design/screenshots/`.

### The backend (each chunk runs and checks on its own)

All cached data is committed, so the checks run offline.

```sh
cd backend/api      && uv run uvicorn app.main:app --port 8000   # API → http://localhost:8000/api/locations
cd backend/api      && uv run python checks/check_api.py
cd backend/regional && uv run python checks/run_checks.py        # NASA POWER, reservoirs, drought, soils
cd backend/field    && uv run python checks/run_checks.py        # field outlines, crop history, satellite calendar
cd backend/engine   && uv run python checks/run_checks.py        # rotation scoring
cd backend/news     && uv run python checks/run_checks.py        # news timeline
```

Each check prints PASS/FAIL lines. A few FAILs are expected and are real findings, not bugs; each chunk's `README.md` explains them:
- regional: Colusa's Jan–Mar 2023 rain is not top-3 in the record.
- field: winter flooding at Colusa is visible in only 3 of 6 winters.
- engine: the spec's "baseline erosion = 0" check conflicts with its own formula.
- news: two publisher sites block scripted link checks (403/429).

Re-fetching data (rather than using the cache) is described in each chunk's README. Several sources need accounts; see [SIGNUPS.md](SIGNUPS.md). Keys go in a local `.env`, which is git-ignored. Never commit it.

## Layout

| Path | What |
|---|---|
| `docs/` | Plan, build spec, brief coverage, research, judges |
| `frontend/variants/` | Design options A, B, C |
| `design/` | Screenshots and the capture scripts |
| `backend/api/` | FastAPI server for the spec's routes (real data where available, fixtures otherwise) |
| `backend/regional/` | NASA POWER, reference ET, risk days, CDEC, Drought Monitor, SSURGO, NOAA stations |
| `backend/field/` | Field outlines, Cropland Data Layer history, Sentinel-2/Landsat calendar, 30 m grid |
| `backend/engine/` | Crops, the 8 rotations, scoring with ranges and ties |
| `backend/news/` | Cached headlines for the timeline |
| `schemas/`, `fixtures/` | JSON Schemas and example payloads shared by the API and frontends |
| `data/cache/` | Cached source data per example farm |
