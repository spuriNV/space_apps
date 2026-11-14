"""Field Shift API. Serves spec B3 routes: real output file if present, else fixture. No database."""
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(os.environ.get("FIELDSHIFT_ROOT", Path(__file__).resolve().parents[3]))
FIX = ROOT / "fixtures"
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]
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
    "news": ["backend/news/out/{p}.json", "data/cache/{p}/news.json"],
    "validation": ["backend/api/out/{p}/validation.json", "backend/regional/out/{p}/validation.json", "backend/field/out/{p}/validation.json", "data/cache/{p}/validation.json"],
    "bc_news": ["backend/news/out/bc_opener.json", "backend/news/out/bc_news.json", "data/cache/bc/news.json"],
    "bc_signal": ["backend/regional/out/bc_signal.json", "data/cache/bc/signal.json"],
    "glossary": ["backend/engine/out/glossary.json", "data/cache/glossary.json"],
    "crop": ["backend/engine/out/crops/{c}.json"],
    "calendar": ["backend/field/out/{p}/calendar.json"],
    "crop_history": ["backend/field/out/{p}/crop_history.json"],
    "grid": ["backend/field/out/{p}/grid.geojson"],
    "calendar_ml": ["backend/ai/out/{p}/calendar_ml.json"],
    "outlook": ["backend/outlook/out/{p}/outlook.json"],
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


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def resolve(kind: str, p: str | None = None, l: str | None = None, c: str | None = None, key: str | None = None):
    """Return (payload_dict, 'real'|'fixture'). Bare lists in real files are wrapped as {"items": [...]}.
    If a real file is a dict keyed by crop id (crops.json), `key` selects the entry."""
    fmt = dict(p=p, l=l, c=c)
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
    if not f.is_file():
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
    resp.headers["X-Data-Source"] = src
    data = dict(data)
    data["_source"] = src
    if src == "real":
        data.pop("_fixture", None)
    return data


def check_preset(pid: str):
    if pid not in PRESETS:
        raise HTTPException(404, f"unknown location {pid}; known: {PRESETS}")


def filter_dates(data: dict, key: str, frm: str | None, to: str | None, field: str = "date"):
    if (frm or to) and isinstance(data.get(key), list):
        data[key] = [r for r in data[key] if (not frm or r[field] >= frm) and (not to or r[field] <= to)]
    return data


@app.get("/api/health")
def health():
    return {"ok": True, "root": str(ROOT), "presets": PRESETS}


@app.get("/api/locations")
def locations(resp: Response):
    items, srcs = [], []
    for p in PRESETS:
        d, s = resolve("location", p)
        items.append({k: v for k, v in d.items() if k not in ("_fixture", "_source")}); srcs.append(s)
    src = "real" if all(s == "real" for s in srcs) else "fixture"
    out = {"items": items, "_fixture": True} if src == "fixture" else {"items": items}
    return send(resp, out, src)


@app.get("/api/locations/{pid}")
def location(pid: str, resp: Response):
    check_preset(pid); d, s = resolve("location", pid); return send(resp, d, s)


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
        items = [normalize_strategy(st) for st in items]
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
    check_preset(pid); d, s = resolve("models", pid); return send(resp, d, s)


@app.get("/api/locations/{pid}/zones")
def zones(pid: str, resp: Response):
    check_preset(pid); d, s = resolve("zones", pid); return send(resp, d, s)


@app.get("/api/locations/{pid}/trends")
def trends(pid: str, resp: Response, layer: str = "smap_anomaly", year: int | None = None):
    check_preset(pid)
    if layer not in LAYERS:
        raise HTTPException(422, f"layer must be one of {LAYERS}")
    d, s = resolve("trends", pid, l=layer)
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
    for rel in LOOKUP[kind]:
        f = ROOT / rel.format(p=pid)
        if f.is_file():
            return _read(f)
    raise HTTPException(404, f"no {kind} output for {pid} (run backend/field to build it)")


@app.get("/api/locations/{pid}/calendar")
def calendar(pid: str, resp: Response, year: int | None = None):
    """Observed field calendar (backend/field rule detector) + CDL crop history. Real only; 404 if backend/field has not run."""
    check_preset(pid)
    d = _real_only("calendar", pid)
    if year is not None:
        d = {**d, "years": [y for y in d["years"] if y["year"] == year]}
    try:
        h = _real_only("crop_history", pid)
        d = {**d, "crop_history": {k: h[k] for k in ("by_year", "source", "years", "caveats") if k in h}}
    except HTTPException:
        pass
    d["location_id"] = pid
    return send(resp, d, "real")


@app.get("/api/locations/{pid}/calendar_ml")
def calendar_ml(pid: str, resp: Response):
    """ML detector calendar (backend/ai), same shape as /calendar. Real only."""
    check_preset(pid)
    d = _real_only("calendar_ml", pid)
    d["location_id"] = pid
    return send(resp, d, "real")


@app.get("/api/locations/{pid}/outlook")
def outlook(pid: str, resp: Response):
    """Coming-season outlooks (backend/outlook). Outlooks, not forecasts. Real only."""
    check_preset(pid)
    d = _real_only("outlook", pid)
    d["location_id"] = pid
    return send(resp, d, "real")


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
