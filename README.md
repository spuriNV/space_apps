# CropLytics

NASA Space Apps Challenge 2026, Vancouver: **Field Shift: Adapting Farms with NASA Data**.

A crop-rotation planner for a grower and their farm adviser, built on NASA Earth data. It works on two real California fields: a rice field west of Williams (Colusa County) and an alfalfa field south of Hanford (Kings County). For each field it shows:
- what's happening on the field now;
- what's likely in the coming season;
- what each rotation would gain or give up in water, soil cover and risk.

It ends with a one-page brief for the adviser.

**Start here:**
- [PLAN.md](PLAN.md): the working plan and the decisions made so far.
- [docs/judging-rubric.md](docs/judging-rubric.md): where the project stands on each judging criterion.
- [CONTRACT.md](CONTRACT.md): build rules for anyone adding code.

## Live site

**https://croplytics.xyz**: the full app and API, self-hosted and redeployed automatically within about 2 minutes of every push to `main`.

Backup: **https://croplytics-app.onrender.com** (Render, free plan; the first visit after it has been idle takes a moment to wake up).

**Reach:** California planted about 524,000 acres of rice in 2025; CropLytics covers every one of those fields with the same NASA data (USDA NASS, served at `/api/reach`).

## Run it locally

You need **Node 20+** and **[uv](https://docs.astral.sh/uv/)** (it installs Python 3.12 for you). Cached data is committed, so the app runs without any API keys.

```sh
# 1. API (real data from the cache)
cd backend/api && uv run uvicorn app.main:app --port 8000

# 2. App, in a second terminal
cd frontend/app && npm install && npm run dev      # open http://localhost:5170
```

Pick a field, then try:
- "Your field now";
- "Coming season";
- "Your field's year";
- "Compare";
- "Print a summary for your adviser".

Scroll into the field on the map for the 3D view (crop, then soil moisture, then groundwater), or use **Look under the field in 3D** / **See this field’s year (3D)** on the field panel. Without the API running, the app falls back to example data and says so.

**Nation tools example:** on Pick your field, open **Nation tools example** (Torres-Martinez Reservation farm field), or go to `#spot=pt_n335100_w1161200`. Land status is tribal land; open the tools for drought rotation, groundwater, land and season, and funding.

Current screenshots are in `design/screenshots/app/`.

## Check the data

Each backend chunk runs and checks on its own and prints PASS/FAIL lines:

```sh
cd backend/api      && uv run python checks/check_api.py     # every route, validated against schemas/
cd backend/regional && uv run python checks/run_checks.py    # NASA POWER, reservoirs, drought, soils, NOAA stations
cd backend/field    && uv run python checks/run_checks.py    # field outlines, crop history, satellite calendar, 30 m grid
cd backend/engine   && uv run python checks/run_checks.py    # rotation scoring, incl. the OpenET water check
cd backend/ground   && uv run python checks/run_checks.py    # OpenET, NASS, AMS, crop insurance, EQIP
cd backend/ai       && uv run python checks/run_checks.py    # bare-field detectors (rule vs machine learning), stress
cd backend/outlook  && uv run python checks/run_checks.py    # coming-season outlooks
cd backend/nasa     && uv run python checks/run_checks.py    # SMAP, IMERG, GRACE, MODIS, ECOSTRESS, OPERA
cd backend/nasa_open && uv run python checks/run_checks.py   # NASADEM, HLS, ISS photos
cd backend/news     && uv run python checks/run_checks.py    # news timeline
```

Some FAIL lines are real findings rather than bugs, for example Colusa's winter flooding showing in only some winters. Each chunk's `README.md` explains its results.

**Headline validation:** our modelled crop water use is within +16% (rice) and +21% (alfalfa) of OpenET's satellite-based measurements for the same fields and years. See `backend/engine/README.md`.

## Re-fetching data (needs keys)

Some sources need free accounts; see [SIGNUPS.md](SIGNUPS.md).
- Copy `.env.example` to `.env` and fill it in. `.env` is git-ignored; never commit it.
- Check the NASA login with `cd backend/nasa && uv run python check_auth.py`.

## Layout

| Path | What |
|---|---|
| `frontend/app/` | The app (Vite, React, TypeScript, MapLibre) |
| `backend/api/` | FastAPI server; serves real data where it exists, fixtures otherwise |
| `backend/nasa/` | NASA data behind the Earthdata login: SMAP, GPM IMERG, GRACE, MODIS, ECOSTRESS, OPERA |
| `backend/nasa_open/` | NASA data without a login: NASADEM elevation, HLS imagery, ISS astronaut photos |
| `backend/regional/` | NASA POWER weather, reference ET, risk days, reservoirs, Drought Monitor, SSURGO soils, NOAA stations |
| `backend/field/` | Field outlines, Cropland Data Layer history, satellite cover calendar, 30 m grid |
| `backend/ai/` | Bare-field detection (rule vs random forest / gradient boosting) and crop-stress anomalies |
| `backend/engine/` | Crops, the 8 rotations, scoring with ranges and ties, water check against OpenET |
| `backend/ground/` | California ground data: OpenET, CIMIS, NASS, AMS hay prices, crop-insurance losses, EQIP |
| `backend/outlook/` | Coming-season outlooks: NOAA seasonal and drought outlooks, reservoirs, allocations |
| `backend/news/` | Cached headlines for the timeline |
| `schemas/`, `fixtures/` | JSON Schemas and example payloads |
| `data/cache/` | Cached source data per field |
| `design/` | Screenshots, capture scripts, and earlier design explorations |
| `frontend/variants/`, `design/explorations/` | Earlier design rounds, kept for reference only |
| `docs/` | Team plan, build spec, brief coverage, research, judging rubric |
| `.claude/skills/fieldshift-visual-design/` | Design rules for the app, charts, brief and slides |
