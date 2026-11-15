"""Field Shift API. Serves spec B3 routes: real output file if present, else fixture. No database."""
import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .myfields import router as myfields_router  # user-drawn fields (app/myfields); my_* ids only
from .nation import router as nation_router  # Nation tools (app/nation): /api/locations/{pid}/nation/*
from .week import router as week_router  # this week + reach (app/week)
from .anyloc import router as anyloc_router  # analyse any tapped point (app/anyloc); pt_* ids only

ROOT = Path(os.environ.get("FIELDSHIFT_ROOT", Path(__file__).resolve().parents[3]))
FIX = ROOT / "fixtures"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/api, for nasa_build
sys.path.insert(0, str(ROOT / "backend" / "fields"))
import fieldreg  # noqa: E402  field registry (backend/fields/registry.json)
from .sanitize import sanitize  # noqa: E402  internal markers out of user-facing text, repo-path links -> public pages

PRESETS = fieldreg.ids(region=None)   # every registry field of every region; the original two first
LAYERS = ["smap_anomaly", "heatwave_days", "grace_gw_pct", "precip_anomaly", "modis_ndvi_anomaly", "usdm_d2_weeks", "reservoir_storage"]
DEFAULT_W = {"water_use": 1, "forage_value": 1, "n_fixation": 1, "erosion": 1, "organic_matter": 1, "market": 1,
             "pest_break": 0, "infiltration": 0, "n_scavenging": 0, "income": 0}

# Real-output lookup paths, relative to ROOT, first existing wins. {p}=preset id, {l}=trend layer, {c}=crop id.
LOOKUP = {
    "location": ["backend/api/out/{p}/location.json", "data/cache/{p}/location.json", "backend/field/out/{p}/location.json", "backend/engine/out/{p}/location.json"],
    "daily": ["backend/api/out/{p}/daily.json", "data/cache/{p}/daily.json", "backend/regional/out/{p}/daily.json"],
    "features_weekly": ["backend/api/out/{p}/features_weekly.json", "data/cache/{p}/features_weekly.json", "backend/field/out/{p}/features_weekly.json"],
    "strategies": ["backend/engine/out/{p}/strategies.json", "data/cache/{p}/strategies.json"],
    "models": ["data/cache/{p}/models.json", "backend/ai/out/{p}/models.json", "backend/field/out/{p}/models.json"],
    "zones": ["backend/api/out/{p}/zones.json", "data/cache/{p}/zones.json", "backend/field/out/{p}/zones.json"],
    "trends": ["backend/api/out/{p}/trends_{l}.json", "backend/regional/out/{p}/trends_{l}.json", "data/cache/{p}/trends_{l}.json"],
    "news": ["backend/news/out/{p}.json", "data/cache/{p}/news.json", "backend/news/out/{t}.json"],  # {t}: family template
    "validation": ["backend/api/out/{p}/validation.json", "backend/regional/out/{p}/validation.json", "backend/field/out/{p}/validation.json", "data/cache/{p}/validation.json"],
    "bc_news": ["backend/news/out/bc_opener.json", "backend/news/out/bc_news.json", "data/cache/bc/news.json"],
    "bc_signal": ["backend/api/out/bc_signal.json", "backend/regional/out/bc_signal.json", "data/cache/bc/signal.json"],
    "glossary": ["backend/api/glossary.json", "backend/engine/out/glossary.json", "data/cache/glossary.json"],
    "insurance": ["backend/ground/out/{p}/rma_profile.json"],
    "stress": ["backend/ai/out/{p}/stress_weekly.json"],
    "water_seen": ["backend/api/out/{p}/water_seen.json"],
    "crop": ["backend/engine/out/crops/{c}.json"],
    "calendar": ["backend/field/out/{p}/calendar.json"],
    "calendar_hls": ["backend/nasa/out/{p}/calendar_hls.json"],
    "nasa_series": ["backend/api/out/{p}/nasa_series.json"],
    "crop_history": ["backend/field/out/{p}/crop_history.json"],
    "grid": ["backend/field/out/{p}/grid.geojson"],
    "calendar_ml": ["backend/ai/out/{p}/calendar_ml.json"],
    "transitions": ["backend/ai/out/{p}/transitions.json"],
    "outlook": ["backend/outlook/out/{p}/outlook.json"],
    "first_nations": ["backend/api/out/{p}/first_nations.json"],
}
FIXTURE = {
    "location": "{p}/location.json", "daily": "{p}/daily.json", "features_weekly": "{p}/features_weekly.json",
    "strategies": "{p}/strategies.json", "models": "{p}/models.json", "zones": "{p}/zones.json",
    "trends": "{p}/trends_{l}.json", "news": "{p}/news.json", "validation": "{p}/validation.json",
    "bc_news": "bc_news.json", "bc_signal": "bc_signal.json", "glossary": "glossary.json", "crop": "crops/{c}.json",
}

try:  # engine is a path dependency (see pyproject); fixture/stored-score fallback if it can't be imported
    from rotation_engine import score as _engine_score_fn
except Exception:  # noqa: BLE001
    _engine_score_fn = None

app = FastAPI(title="Field Shift API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Data-Source"])
app.include_router(nation_router)  # before anyloc: its pt_* catch-all would 404 the /nation routes
app.include_router(week_router)  # before anyloc: its pt_* catch-all would swallow /this_week
app.include_router(anyloc_router)  # before the preset routes: /api/analyze and /api/locations/pt_* (other ids fall through)
app.include_router(myfields_router)  # my_* ids and /api/my-fields


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def resolve(kind: str, p: str | None = None, l: str | None = None, c: str | None = None, key: str | None = None):
    """Return (payload_dict, 'real'|'fixture'). Bare lists in real files are wrapped as {"items": [...]}.
    If a real file is a dict keyed by crop id (crops.json), `key` selects the entry."""
    fmt = dict(p=p, l=l, c=c, t=fieldreg.template(p) if p and fieldreg.has(p) else p)
    for rel in LOOKUP[kind]:
        f = ROOT / rel.format(**fmt)
        if f.is_file():
            data = _read(f)
            if isinstance(data, list):
                data = {"items": data}
            return data, "real"
    if kind == "crop":  # engine writes backend/engine/crops.json = {"crops": [...]}; also accept list/dict forms
        for rel in ("backend/engine/crops.json", "backend/engine/out/crops.json"):
            f = ROOT / rel
            if not f.is_file():
                continue
            data = _read(f)
            items = data if isinstance(data, list) else data.get("crops", data.get("items", list(data.values())))
            for it in items:
                if isinstance(it, dict) and it.get("id") == c:
                    return it, "real"
    f = FIX / FIXTURE[kind].format(**fmt)
    if not f.is_file() or (p and fieldreg.has(p) and not fieldreg.is_original(p) and "{p}" in FIXTURE[kind]):
        raise HTTPException(404, f"no data for {kind} {fmt}")
    return _read(f), "fixture"


def normalize_strategy(st: dict) -> dict:
    """Engine emits brief.gaps as plain strings; schema wants {text, source_ids}. Wrap strings, leave objects."""
    gaps = (st.get("brief") or {}).get("gaps")
    if isinstance(gaps, list):
        st["brief"]["gaps"] = [{"text": g, "source_ids": []} if isinstance(g, str) else g for g in gaps]
    return st


def normalize_strategies(d: dict) -> dict:
    for st in d.get("items", []):
        normalize_strategy(st)
    return d


def send(resp: Response, data: dict, src: str):
    """Every route returns through here. Real and estimate payloads are sanitized (app/sanitize.py): internal markers such as
    "(U)", "(V)" and "spec B11" are stripped from user-facing text, and repo-path source links become the dataset's public page
    or carry `internal: true`. `method` / `verified` are untouched, so the data status still comes from them. Fixtures are
    served as written (dev placeholders whose "(U)" marks them as such)."""
    resp.headers["X-Data-Source"] = src
    data = dict(data)
    data["_source"] = src
    if src == "real":
        data.pop("_fixture", None)
    if src != "fixture":
        data = sanitize(data)
    return data


def check_preset(pid: str):
    if pid not in PRESETS:
        raise HTTPException(404, f"unknown location {pid}; known: {PRESETS}")


# California-only outputs -> the registry's not_available key that explains the gap for a field outside California
REGION_GAPS = {"openet": "openet", "insurance": "insurance", "outlook": "outlook", "usdm_d2_weeks": "outlook", "reservoir_storage": "sgma",
               "calendar_ml": "ml_calendar", "stress": "ml_calendar", "transitions": "ml_calendar", "models": "ml_calendar", "water_seen": None}
# Outside California these outputs are estimates in the California shape (backend/bc/estimates.py, via backend/bc/build_api.py),
# served from backend/api/out/<id>/<file> with `_source: "estimate"` and X-Data-Source: estimate.
ESTIMATE_FILE = {"openet": "openet.json", "insurance": "insurance.json", "outlook": "outlook.json", "calendar_ml": "calendar_ml.json",
                 "stress": "stress.json", "transitions": "transitions.json", "models": "models.json", "water_seen": "water_seen.json",
                 "usdm_d2_weeks": "trends_usdm_d2_weeks.json", "reservoir_storage": "trends_reservoir_storage.json"}


def is_estimate(kind: str, pid: str) -> bool:
    """True when `kind` is a California-only output and `pid` is a field outside California (its payload is an estimate)."""
    return kind in REGION_GAPS and fieldreg.region(pid) != "ca"


def _estimate(kind: str, pid: str) -> dict | None:
    f = ROOT / "backend" / "api" / "out" / pid / ESTIMATE_FILE[kind]
    return _read(f) if is_estimate(kind, pid) and f.is_file() else None


def region_gap(kind: str, pid: str):
    """For a California-only output asked of a field outside California: fine when its estimate is built, else
    404 "not available in BC: <registry reason>"."""
    if is_estimate(kind, pid) and _estimate(kind, pid) is None:
        reg = fieldreg.region(pid)
        why = (fieldreg.get(pid).get("not_available") or {}).get(REGION_GAPS[kind] or "")
        raise HTTPException(404, f"{kind} not available in {reg.upper()}" + (f": {why}" if why else ""))


def src_of(kind: str, pid: str) -> str:
    return "estimate" if is_estimate(kind, pid) else "real"


def filter_dates(data: dict, key: str, frm: str | None, to: str | None, field: str = "date"):
    if (frm or to) and isinstance(data.get(key), list):
        data[key] = [r for r in data[key] if (not frm or r[field] >= frm) and (not to or r[field] <= to)]
    return data


@app.get("/api/health")
def health():
    return {"ok": True, "root": str(ROOT), "presets": PRESETS}


@app.get("/api/locations")
def locations(resp: Response, family: str | None = Query(None, pattern="^(rice|forage)$"), county: str | None = None,
              region: str | None = Query(None, pattern="^(ca|bc)$")):
    """Every registry field (backend/fields/registry.json). ?family=rice|forage and ?county=<name or FIPS> filter the list;
    `facets` counts all fields by family and county so a picker can build its filters."""
    items, srcs = [], []
    for f in fieldreg.fields(family, county, region=region):
        try:
            d, s = resolve("location", f["id"])
        except HTTPException:   # registry field whose payload is not built yet: skip it rather than fail the list
            continue
        items.append({"region": f.get("region", "ca"), **{k: v for k, v in d.items() if k not in ("_fixture", "_source")}}); srcs.append(s)
    src = "real" if srcs and all(s == "real" for s in srcs) else "fixture"
    fam, cty, rgn = {}, {}, {}
    for f in fieldreg.fields(region=None):
        rgn[f.get("region", "ca")] = rgn.get(f.get("region", "ca"), 0) + 1
        fam[f["family"]] = fam.get(f["family"], 0) + 1
        cty[f["county"]["name"]] = cty.get(f["county"]["name"], 0) + 1
    out = {"items": items, "count": len(items), "filters": {"family": family, "county": county, "region": region},
           "facets": {"family": fam, "county": dict(sorted(cty.items())), "region": rgn}}
    if src == "fixture":
        out["_fixture"] = True
    return send(resp, out, src)


@app.get("/api/locations/{pid}")
def location(pid: str, resp: Response):
    check_preset(pid); d, s = resolve("location", pid); d.setdefault("region", fieldreg.region(pid)); return send(resp, d, s)


@app.get("/api/locations/{pid}/daily")
def daily(pid: str, resp: Response, from_: str | None = Query(None, alias="from"), to: str | None = None):
    check_preset(pid); d, s = resolve("daily", pid); return send(resp, filter_dates(d, "rows", from_, to), s)


@app.get("/api/locations/{pid}/features/weekly")
def features_weekly(pid: str, resp: Response):
    check_preset(pid); d, s = resolve("features_weekly", pid); return send(resp, d, s)


@app.get("/api/locations/{pid}/strategies")
def strategies(pid: str, resp: Response):
    check_preset(pid); d, s = resolve("strategies", pid); d.setdefault("location_id", pid)
    return send(resp, normalize_strategies(d), s)


class Scenario(BaseModel):
    dT_c: float = Field(0, ge=-1, le=4)
    dP_pct: float = Field(0, ge=-30, le=30)


class ScoreRequest(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    market_preference: str | None = None
    allocation: float | None = None
    replay_year: int | None = None
    scenario: Scenario = Scenario()


def _rank(strats):
    out = []; ordered = sorted(strats, key=lambda s: -s["composite"]["value"])
    for i, s in enumerate(ordered):
        c = s["composite"]; tie = False
        if i:
            p = ordered[i - 1]["composite"]
            ov = min(c["high"], p["high"]) - max(c["low"], p["low"])
            tie = ov > 0.5 * min(c["high"] - c["low"], p["high"] - p["low"])
        out.append({"id": s["id"], "composite": c["value"], "low": c["low"], "high": c["high"], "tie_with_previous": tie})
    return out


def _plain(x):
    """Engine output may hold numpy scalars/arrays; convert to plain JSON types."""
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if hasattr(x, "tolist"):
        return _plain(x.tolist())
    if hasattr(x, "item"):
        return x.item()
    return x


def _engine_score(pid: str, req: ScoreRequest, w: dict):
    """Run the real rotation engine. Returns strategies list, or None if the engine is unavailable."""
    if _engine_score_fn is None:
        return None
    try:
        return _plain(_engine_score_fn(pid, weights=w, constraints=req.constraints,
                                market_preference=req.market_preference or "no_preference",
                                allocation=req.allocation, replay_year=req.replay_year,
                                scenario=req.scenario.model_dump()))
    except ValueError as e:  # engine input validation (bounds, unknown keys)
        raise HTTPException(422, str(e))
    except Exception:  # noqa: BLE001  engine data missing/broken: fall back to placeholder
        return None


OPENET_KEYS = ("etc_vs_openet_pct", "openet_et_mm_season")


def _with_openet(pid: str, items: list) -> list:
    """The engine's score() does not recompute the OpenET check; copy water.etc_vs_openet_pct / openet_et_mm_season from the
    stored strategies (same id) so POST /score carries them like GET /strategies. The check compares the default-weather
    model with OpenET, so it does not change with weights/scenario; the note says so."""
    try:
        stored, _ = resolve("strategies", pid)
    except HTTPException:
        return items
    by_id = {s["id"]: s for s in stored.get("items", []) if isinstance(s, dict)}
    for st in items:
        src = (by_id.get(st.get("id")) or {}).get("water", {})
        wat = st.setdefault("water", {})
        for k in OPENET_KEYS:
            if k in src and k not in wat:
                wat[k] = {**src[k], "note": (src[k].get("note", "") + " Copied from GET /strategies (default weather); "
                                             "not recomputed for this request's scenario.").strip()}
    return items


@app.post("/api/locations/{pid}/score")
def score(pid: str, req: ScoreRequest, resp: Response):
    """Scores via the rotation engine (weights, constraints, market_preference, allocation, replay_year, scenario all applied).
    Falls back to a placeholder re-weighting of stored scores if the engine can't be imported or run."""
    check_preset(pid)
    for k, v in req.weights.items():
        if k not in DEFAULT_W:
            raise HTTPException(422, f"unknown weight '{k}'; valid: {list(DEFAULT_W)}")
        if not 0 <= v <= 4:
            raise HTTPException(422, f"weight {k} must be in [0, 4]")
    w = {**DEFAULT_W, **req.weights}
    if sum(w.values()) <= 0:
        raise HTTPException(422, "at least one weight must be > 0")
    items = _engine_score(pid, req, w)
    if items is not None:
        items = [normalize_strategy(st) for st in _with_openet(pid, items)]
        out = {"location_id": pid, "request": req.model_dump(), "items": items, "ranking": _rank(items),
               "note": "scored by backend/engine (rule of thumb, not a model)"}
        return send(resp, out, "real")
    d, s = resolve("strategies", pid)
    tot = sum(w.values()); items = []
    for st in d["items"]:
        st = json.loads(json.dumps(st)); sc = st["scores"]
        def f(k):
            return round(sum(w[x] * (sc[x][k] if sc[x].get(k) is not None else sc[x]["value"])
                             for x in w if x in sc and sc[x].get("value") is not None) / tot, 1)
        st["composite"] = {"value": f("value"), "low": f("low"), "high": f("high"), "weights_used": w}
        st["exposure"]["scenario"] = req.scenario.model_dump()
        items.append(normalize_strategy(st))
    out = {"location_id": pid, "request": req.model_dump(), "items": items, "ranking": _rank(items),
           "note": "api placeholder (engine unavailable): composite re-weighted from stored scores; scenario/constraints/allocation/replay not applied"}
    if s == "fixture":
        out["_fixture"] = True
    return send(resp, out, s)


@app.get("/api/locations/{pid}/models")
def models(pid: str, resp: Response):
    check_preset(pid); region_gap("models", pid)
    if is_estimate("models", pid):
        return send(resp, _estimate("models", pid), "estimate")
    d, s = resolve("models", pid); return send(resp, d, s)


@app.get("/api/locations/{pid}/zones")
def zones(pid: str, resp: Response):
    check_preset(pid); d, s = resolve("zones", pid); return send(resp, d, s)


@app.get("/api/locations/{pid}/trends")
def trends(pid: str, resp: Response, layer: str = "smap_anomaly", year: int | None = None):
    check_preset(pid)
    if layer not in LAYERS:
        raise HTTPException(422, f"layer must be one of {LAYERS}")
    region_gap(layer, pid)
    d, s = resolve("trends", pid, l=layer)
    if is_estimate(layer, pid):
        s = "estimate"
    if "by_year" in d:  # real files hold every year: pick one, default_year when `year` is omitted
        y = year if year is not None else d.get("default_year")
        if str(y) not in d["by_year"]:
            raise HTTPException(404, f"no {layer} data for year {y}; available: {d.get('years')}")
        d = {k: v for k, v in d.items() if k != "by_year"}
        d["year"] = int(y)
        d["cells"] = _read_by_year(pid, layer)[str(y)]
    elif year is not None:
        d["year"] = year  # fixtures hold one year; echo requested year
    return send(resp, d, s)


def _read_by_year(pid: str, layer: str) -> dict:
    for rel in LOOKUP["trends"]:
        f = ROOT / rel.format(p=pid, l=layer)
        if f.is_file():
            return _read(f)["by_year"]
    return {}


@app.get("/api/locations/{pid}/news")
def news(pid: str, resp: Response, from_: str | None = Query(None, alias="from"), to: str | None = None):
    check_preset(pid); d, s = resolve("news", pid); d.setdefault("location_id", pid)
    return send(resp, filter_dates(d, "items", from_, to), s)


@app.get("/api/locations/{pid}/validation")
def validation(pid: str, resp: Response):
    check_preset(pid); d, s = resolve("validation", pid); return send(resp, d, s)


@app.get("/api/bc/news")
def bc_news(resp: Response):
    d, s = resolve("bc_news"); return send(resp, d, s)


@app.get("/api/bc/signal")
def bc_signal(resp: Response):
    d, s = resolve("bc_signal"); return send(resp, d, s)


@app.get("/api/glossary")
def glossary(resp: Response):
    d, s = resolve("glossary"); return send(resp, d, s)


@app.get("/api/crops/{cid}")
def crop(cid: str, resp: Response):
    if not cid.replace("_", "").isalnum():
        raise HTTPException(404, "bad crop id")
    d, s = resolve("crop", c=cid); return send(resp, d, s)


def _real_only(kind: str, pid: str) -> dict:
    """The built output for `kind` (real only, no fixture); for a California-only kind outside California, its estimate."""
    region_gap(kind, pid)
    if is_estimate(kind, pid):
        return _estimate(kind, pid)
    for rel in LOOKUP[kind]:
        f = ROOT / rel.format(p=pid)
        if f.is_file():
            return _read(f)
    raise HTTPException(404, f"no {kind} output for {pid} (run backend/field to build it)")


@app.get("/api/locations/{pid}/calendar")
def calendar(pid: str, resp: Response, year: int | None = None, source: str = Query("s2_landsat", pattern="^(s2_landsat|hls)$")):
    """Observed field calendar + CDL crop history. Real only. source=s2_landsat (default, backend/field: Sentinel-2 + Landsat)
    or source=hls (same rule detector on NASA HLS v2.0 only, backend/nasa/out/<id>/calendar_hls.json)."""
    check_preset(pid)
    d = _real_only("calendar_hls" if source == "hls" else "calendar", pid)
    if year is not None:
        d = {**d, "years": [y for y in d["years"] if y["year"] == year]}
    try:
        h = _real_only("crop_history", pid)
        d = {**d, "crop_history": {k: h[k] for k in ("by_year", "source", "years", "caveats") if k in h}}
    except HTTPException:
        pass
    d["location_id"] = pid
    return send(resp, d, "real")


@app.get("/api/locations/{pid}/openet")
def openet(pid: str, resp: Response, from_: str | None = Query(None, alias="from"), to: str | None = None):
    """Monthly measured actual ET (OpenET Ensemble, field polygon) from data/cache/<id>/openet.parquet. Real only.
    Outside California (no OpenET): the engine's modelled ETc in the same shape, `_source: "estimate"`."""
    check_preset(pid); region_gap("openet", pid)
    if is_estimate("openet", pid):
        d = {**_estimate("openet", pid), "location_id": pid}
        return send(resp, filter_dates(d, "rows", from_, to), "estimate")
    f = ROOT / "data" / "cache" / pid / "openet.parquet"
    if not f.is_file():
        raise HTTPException(404, f"no OpenET cache for {pid}")
    import pandas as pd
    df = pd.read_parquet(f)
    meta_f = f.with_suffix(".meta.json")
    meta = _read(meta_f) if meta_f.is_file() else {}
    rows = [{"date": pd.Timestamp(r.date).strftime("%Y-%m-%d"), "month": pd.Timestamp(r.date).strftime("%Y-%m"),
             "et_mm": round(float(r.et_mm), 1), "et_in": round(float(r.et_mm) / 25.4, 2), "model": r.model}
            for r in df.sort_values("date").itertuples() if r.et_mm == r.et_mm]
    years = {}
    for r_ in rows:
        years.setdefault(r_["date"][:4], []).append(r_["et_mm"])
    d = {"location_id": pid, "unit": "mm/month", "rows": rows,
         "annual": [{"year": int(y), "et_mm": round(sum(v), 0), "months": len(v)} for y, v in sorted(years.items())],
         "source": {"id": "openet", "title": "OpenET Ensemble monthly actual ET over the field polygon", "url": meta.get("url", "https://openet-api.org"),
                    "accessed": (meta.get("fetched_at") or "")[:10], "verified": True},
         "note": "Measured (satellite ensemble) actual crop water use, not a model of this app. Used to check the engine, never as a score input."}
    return send(resp, filter_dates(d, "rows", from_, to), "real")


@app.get("/api/locations/{pid}/nasa_now")
def nasa_now(pid: str, resp: Response, date: str | None = None):
    """NASA readings for the field at a date (default today): SMAP root-zone percentile, GRACE groundwater percentile,
    IMERG rain season to date vs normal, MODIS/HLS greenness, ECOSTRESS stress, DSWx water, each with its observation date.
    Values come from the 10-day series; a field with no value in that step falls back to its latest earlier step (stale_steps)."""
    check_preset(pid)
    s = _real_only("nasa_series", pid)
    from nasa_build import now_reading  # noqa: PLC0415  (backend/api/nasa_build.py, pandas only)
    d = now_reading(s, date)
    d["location_id"] = pid
    return send(resp, d, "real")


@app.get("/api/locations/{pid}/nasa_series")
def nasa_series(pid: str, resp: Response, from_: str | None = Query(None, alias="from"), to: str | None = None):
    """10-day NASA series (1st/11th/21st) for the 3D slabs and timeline: same fields as /nasa_now, one row per step."""
    check_preset(pid)
    d = _real_only("nasa_series", pid)
    d["location_id"] = pid
    return send(resp, filter_dates(d, "rows", from_, to), "real")


@app.get("/api/locations/{pid}/insurance")
def insurance(pid: str, resp: Response):
    """USDA RMA crop-insurance cause-of-loss profile for the county and crop (backend/ground). Real only.
    Kept as published, including `share_peril_unattributed` (forage/alfalfa indemnity that RMA does not tie to a peril)."""
    check_preset(pid)
    d = _real_only("insurance", pid)
    d["location_id"] = pid
    return send(resp, d, src_of("insurance", pid))


@app.get("/api/locations/{pid}/stress")
def stress(pid: str, resp: Response):
    """Weekly in-season crop-stress flags (backend/ai: z-score and isolation forest). Real only. Adds `summary` per crop year
    (weeks evaluated / flagged) and any backend/ai stress summary or evaluation file that exists."""
    check_preset(pid)
    d = _real_only("stress", pid)
    by = {}
    for w in d.get("weeks", []):
        y = by.setdefault(str(w.get("iso_year")), {"crop": w.get("crop"), "weeks": 0, "evaluated": 0, "flag_zscore": 0, "flag_iforest": 0, "water": 0})
        y["weeks"] += 1
        y["evaluated"] += bool(w.get("evaluated"))
        y["flag_zscore"] += bool(w.get("flag_zscore"))
        y["flag_iforest"] += bool(w.get("flag_iforest"))
        y["water"] += bool(w.get("water"))
    d["summary"] = {"by_year": by, "note": "counts of season weeks; computed by the API from `weeks`"}
    for name in ("stress_summary", "stress_eval", "stress_evaluation"):
        f = ROOT / "backend" / "ai" / "out" / pid / f"{name}.json"
        if f.is_file():
            d[name] = _read(f)
    d["location_id"] = pid
    return send(resp, d, src_of("stress", pid))


@app.get("/api/locations/{pid}/water_seen")
def water_seen(pid: str, resp: Response, from_: str | None = Query(None, alias="from"), to: str | None = None):
    """NASA OPERA DSWx: share of the field under water per satellite scene, per-season summary and a plain-language line."""
    check_preset(pid)
    d = _real_only("water_seen", pid)
    d["location_id"] = pid
    return send(resp, filter_dates(d, "scenes", from_, to), src_of("water_seen", pid))


@app.get("/api/locations/{pid}/calendar_ml")
def calendar_ml(pid: str, resp: Response):
    """ML detector calendar (backend/ai), same shape as /calendar. Real only."""
    check_preset(pid)
    d = _real_only("calendar_ml", pid)
    d["location_id"] = pid
    return send(resp, d, src_of("calendar_ml", pid))


@app.get("/api/locations/{pid}/transitions")
def transitions(pid: str, resp: Response):
    """Green-up, harvest and cutting dates per detector method (backend/ai transitions.json). Real only, 404 if not built."""
    check_preset(pid)
    d = _real_only("transitions", pid)
    if isinstance(d, dict):
        d["location_id"] = pid
    return send(resp, d, src_of("transitions", pid))


@app.get("/api/locations/{pid}/outlook")
def outlook(pid: str, resp: Response):
    """Coming-season outlooks (backend/outlook). Outlooks, not forecasts. Real only."""
    check_preset(pid)
    d = _real_only("outlook", pid)
    d["location_id"] = pid
    return send(resp, d, src_of("outlook", pid))


@app.get("/api/locations/{pid}/grid")
def grid(pid: str, resp: Response, layer: list[str] | None = Query(None)):
    """30 m field grid (GeoJSON, EPSG:4326) with NDVI layers. `layer` (repeatable) keeps only those ndvi_* keys. Real only."""
    check_preset(pid)
    d = _real_only("grid", pid)
    if layer:
        keep = set(layer) | {"cell_id", "row", "col", "area_m2", "frac_in_field"}
        unknown = set(layer) - {l["key"] for l in d.get("layers", [])}
        if unknown:
            raise HTTPException(422, f"unknown layer(s) {sorted(unknown)}")
        d = {**d, "layers": [l for l in d["layers"] if l["key"] in keep],
             "features": [{**f, "properties": {k: v for k, v in f["properties"].items() if k in keep or (k.startswith("n_") and k[2:] in keep)}} for f in d["features"]]}
    d["location_id"] = pid
    return send(resp, d, "real")


@app.get("/api/locations/{pid}/first_nations")
def first_nations(pid: str, resp: Response):
    """First Nations context for a BC field (backend/bc/build_api.py, facts from docs/bc-first-nations.md). 404 for California."""
    check_preset(pid)
    if fieldreg.region(pid) != "bc":
        raise HTTPException(404, "First Nations context is built for the BC example field only")
    d = _real_only("first_nations", pid)
    return send(resp, d, "real")


@app.get("/api/locations/{pid}/salmon")
def salmon(pid: str, resp: Response):
    """Salmon and the field (backend/bc/salmon.py; schema schemas/salmon.schema.json): Salmon River flow and temperature,
    run timing, a spring early-warning table and each rotation's Aug-Sep irrigation draw. BC example field only."""
    check_preset(pid)
    f = ROOT / "backend" / "api" / "out" / pid / "salmon.json"
    if fieldreg.region(pid) != "bc" or not f.is_file():
        raise HTTPException(404, "Salmon context is built for the BC example field only (bc_salmon_river_forage)")
    return send(resp, _read(f), "real")


@app.get("/api/locations/{pid}/first_nations/reserves.geojson")
def first_nations_reserves(pid: str, resp: Response):
    """Nearby reserve outlines (BC CLSS layer, ~20 km), for the map as context only. BC fields only."""
    check_preset(pid)
    f = ROOT / "data" / "cache" / pid / "reserves_nearby.geojson"
    if fieldreg.region(pid) != "bc":
        raise HTTPException(404, "First Nations context is built for the BC example field only")
    if not f.is_file():
        raise HTTPException(404, f"no reserves_nearby.geojson for {pid} (run backend/bc/fetch_reserves.py)")
    d = _read(f)
    d["location_id"] = pid
    return send(resp, d, "real")


# Optional: serve the built frontend from the same origin (set FRONTEND_DIST to frontend/app/dist). /api routes win.
_dist = os.environ.get("FRONTEND_DIST")
if _dist and (Path(_dist) / "index.html").is_file():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _dist_p = Path(_dist).resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "not found")
        f = (_dist_p / path).resolve()
        if path and f.is_file() and _dist_p in f.parents:
            return FileResponse(f)
        return FileResponse(_dist_p / "index.html")
