"""GET /api/locations/{id}/this_week and GET /api/reach."""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import json
import os
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from . import plan, reach as reach_mod, weather as W
from .resolve import ROOT, resolve_location
from .sources import sn, src

router = APIRouter()
TTL_S = 10800
LABEL = "Forecast, not a guarantee"
CACHE_DIR = Path(os.environ.get("WEEK_CACHE_DIR", ROOT / "data" / "cache" / "_points" / "week"))   # git-ignored
_MEM: dict[str, tuple[float, dict]] = {}
_LOCK = threading.Lock()


def _ck(pid: str) -> str:
    return f"{pid}_{dt.date.today().isoformat()}"


def cache_get(pid: str):
    k = _ck(pid)
    with _LOCK:
        hit = _MEM.get(k)
    if hit and time.time() - hit[0] < TTL_S:
        return hit[1]
    f = CACHE_DIR / f"{k}.json"
    try:
        if f.is_file() and time.time() - f.stat().st_mtime < TTL_S:
            data = json.loads(f.read_text())
            with _LOCK:
                _MEM[k] = (f.stat().st_mtime, data)
            return data
    except Exception:  # noqa: BLE001
        pass
    return None


def cache_put(pid: str, data: dict):
    k = _ck(pid)
    with _LOCK:
        _MEM[k] = (time.time(), data)
        for old in [x for x in _MEM if not x.endswith(dt.date.today().isoformat())]:
            _MEM.pop(old, None)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{k}.json").write_text(json.dumps(data))
    except OSError:
        pass


def _sec(status, reason=None, **kw):
    return {"status": status, **({"reason": reason} if reason else {}), **kw}


def build(loc: dict) -> dict:
    lat, lon, pid = loc["lat"], loc["lon"], loc["id"]
    cache = ROOT / "data" / "cache" / pid
    is_us = loc["region"] == "ca" or (loc["region"] != "bc" and W.in_us(lat, lon))
    sections: dict[str, dict] = {}
    with cf.ThreadPoolExecutor(3) as ex:
        f_fc = ex.submit(W.open_meteo, lat, lon)
        f_al = ex.submit(W.nws_alerts, lat, lon) if is_us else None
        f_wet = ex.submit(W.wetness, cache if cache.is_dir() else None, lat, lon, dt.date.today())
        fc, fallback_reason = None, None
        try:
            fc = f_fc.result()
        except Exception as e:  # noqa: BLE001
            fallback_reason = f"Open-Meteo failed ({type(e).__name__})"
            if is_us:
                try:
                    fc = W.nws_forecast(lat, lon)
                except Exception as e2:  # noqa: BLE001
                    fallback_reason += f"; NWS fallback failed ({type(e2).__name__})"
            else:
                fallback_reason += "; no fallback outside the US"
        alerts, a_sec = [], _sec("not_applicable", "NWS alerts cover US locations only")
        if f_al is not None:
            try:
                alerts, a_sec = f_al.result(), _sec("ready")
            except Exception as e:  # noqa: BLE001
                a_sec = _sec("unavailable", f"NWS alerts did not answer ({type(e).__name__})")
        try:
            wet = f_wet.result()
        except Exception as e:  # noqa: BLE001
            wet = {"skipped": [f"error {type(e).__name__}"]}
    today = dt.date.fromisoformat(fc["today"]) if fc else dt.date.today()
    out = {"location_id": pid, "name": loc.get("name"), "point": {"lat": round(lat, 4), "lon": round(lon, 4)}, "family": loc.get("family"),
           "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ttl_s": TTL_S, "label": LABEL}
    if fc is None:
        sections["forecast"] = _sec("unavailable", fallback_reason)
        out.update(forecast=[], alerts=alerts, irrigation={"verdict": "Forecast unavailable right now — try again later", "kind": "unavailable"},
                   field_access={"line": "Field access unknown without a forecast", "rule": plan.RULE, "days": [
                       {"date": (today + dt.timedelta(days=i)).isoformat(), "status": "unknown"} for i in range(7)]})
        sections.update(alerts=a_sec, irrigation=_sec("unavailable", "no forecast"), field_access=_sec("unavailable", "no forecast"))
        out["sections"] = sections
        return out
    fsrc_key = "open_meteo" if fc["source"] == "open_meteo" else "nws"
    fsrc = src(fsrc_key)
    et_src = fsrc if fc["source"] == "open_meteo" else src("hargreaves")
    out["forecast"] = [{"date": r["date"], "weekday": dt.date.fromisoformat(r["date"]).strftime("%a"),
                        "rain_mm": sn(r["rain_mm"], "mm", fsrc, "model"), "tmax_c": sn(r["tmax_c"], "degC", fsrc, "model"),
                        "tmin_c": sn(r["tmin_c"], "degC", fsrc, "model"),
                        "et0_mm": sn(r["et0_mm"], "mm", et_src, "model" if fc["source"] == "open_meteo" else "computed", fc["et0_method"])} for r in fc["days"]]
    out["forecast_source"] = {"provider": fc["source"], "et0_method": fc["et0_method"], "fallback": fc["source"] != "open_meteo", "timezone": fc["tz"]}
    sections["forecast"] = _sec("ready" if fc["source"] == "open_meteo" else "fallback", fallback_reason)
    out["alerts"], sections["alerts"] = alerts, a_sec
    try:
        from rotation_engine.model import EFFECTIVE_RAIN  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        EFFECTIVE_RAIN = 0.8
    try:
        irr = plan.irrigation(ROOT, loc, fc["days"], today, fsrc, EFFECTIVE_RAIN)
        if not loc.get("crop_known", True):
            irr["note_crop"] = "The crop at this spot is not known yet, so the forage rotation is used as the baseline. Tap the spot on the map to analyse it first."
        sections["irrigation"] = _sec("ready")
    except Exception as e:  # noqa: BLE001
        irr = {"verdict": "Irrigation estimate unavailable", "kind": "unavailable"}
        sections["irrigation"] = _sec("unavailable", f"rotation engine: {type(e).__name__}: {e}")
    out["irrigation"] = irr
    wsrc_note = None
    pct = wet.get("pct")
    if pct is not None:
        wsrc = src({"smap_l4": "smap_l4", "grace": "grace", "power": "power"}[wet["kind"]])
        wetness = {"percentile": sn(pct, "percentile", wsrc, "computed",
                                    f"{wet['what']} on {wet['obs_date']} compared with this place's own history for the same time of year"),
                   "kind": wet["kind"], "obs_date": wet["obs_date"], "age_days": wet["age_days"], "skipped": wet["skipped"]}
        sections["field_access"] = _sec("ready")
    else:
        wetness = {"percentile": None, "kind": "unknown", "skipped": wet.get("skipped", [])}
        sections["field_access"] = _sec("partial", "no soil-wetness reading available; the call uses forecast rain only")
    fa = plan.field_access(fc["days"], fc["past"], wet if pct is not None else None, fsrc)
    out["field_access"] = {"line": plan.access_line(fa["days"]), "rule": plan.RULE, "wetness": wetness, "days": fa["days"]}
    out["sections"] = sections
    return out


@router.get("/api/locations/{pid}/this_week")
def this_week(pid: str, resp: Response, refresh: bool = False):
    loc = resolve_location(pid)
    if loc is None:
        raise HTTPException(404, f"unknown location {pid}")
    data = None if refresh else cache_get(pid)
    state = "hit"
    if data is None:
        data, state = build(loc), "miss"
        if data["sections"]["forecast"]["status"] != "unavailable":
            cache_put(pid, data)
    resp.headers["X-Data-Source"] = "live"
    resp.headers["X-Cache"] = state
    return {**data, "_source": "live"}


@router.get("/api/reach")
def reach(resp: Response):
    resp.headers["X-Data-Source"] = "real"
    return {**reach_mod.build(), "_source": "real"}
