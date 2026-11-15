"""Run the rotation engine (backend/engine, `rotation_engine.score`) for a point that is not in the registry.

The engine is keyed by registry id and reads its inputs from data/cache/<id>/. For a point we register a virtual
entry for the duration of one call, under a lock:
- fieldreg.get / fieldreg.has see a virtual entry {family, template, region "ca", slope_pct} (the engine reuses the
  family's rotation set: rice -> CAR0-CAR3 of car_colusa_rice, forage/other -> CAF0-CAF3 of caf_tulare_forage);
- rotation_engine.weather._CACHE[pid] holds the POWER series we fetched (no station cache: POWER precipitation and
  temperatures only, which the engine already supports);
- rotation_engine.engine.load_soil returns the point's SSURGO summary (drainage check).
Everything else the engine looks for (observed cover, OpenET, NOAA stations) does not exist for a point, and the engine
falls back as it does for a registry field without those outputs. The entries are removed after the call.
"""
from __future__ import annotations

import threading

_LOCK = threading.Lock()
_POINTS: dict[str, dict] = {}
_patched = False


def _patch():
    global _patched
    if _patched:
        return
    import fieldreg  # noqa: PLC0415  (same module object the engine imported)
    from rotation_engine import engine as E  # noqa: PLC0415
    get0, has0, soil0 = fieldreg.get, fieldreg.has, E.load_soil

    def get(fid):
        if fid in _POINTS:
            return _POINTS[fid]["entry"]
        return get0(fid)

    def has(fid):
        return fid in _POINTS or has0(fid)

    def load_soil(pid):
        if pid in _POINTS:
            return _POINTS[pid].get("soil")
        return soil0(pid)

    fieldreg.get, fieldreg.has, E.load_soil = get, has, load_soil
    _patched = True


def run(pid: str, entry: dict, df, lat: float, elev_m: float, url: str, soil: dict | None, **kw) -> list[dict]:
    """score(pid, **kw) with the point registered. df: POWER daily (index date; T2M, T2M_MAX, T2M_MIN, RH2M, WS2M,
    ALLSKY_SFC_SW_DWN, PRECTOTCORR)."""
    from rotation_engine import engine as E  # noqa: PLC0415
    from rotation_engine import weather as W  # noqa: PLC0415
    with _LOCK:
        _patch()
        _POINTS[pid] = {"entry": entry, "soil": soil}
        W.PRESETS[pid] = {"lat": lat, "lon": entry["centroid"]["lon"], "name": entry["name"]}
        W._CACHE[pid] = W.Weather(pid, lat, df.astype("float64"), "live NASA POWER fetch (not stored in the repo)", url,
                                  "live fetch for this point", elev_m=float(elev_m or 0.0))
        try:
            return E.score(pid, **kw)
        finally:
            _POINTS.pop(pid, None)
            W.PRESETS.pop(pid, None)
            for d in (W._CACHE, W._CLIM, W._ST, W._STT):
                d.pop(pid, None)
            # per-id lru caches: weather_years (64 entries), _imax and _openet_years (8) are bounded; clear the
            # weather-years cache so point arrays do not linger in memory
            E.weather_years.cache_clear()
            E._imax.cache_clear()
            E._openet_years.cache_clear()
