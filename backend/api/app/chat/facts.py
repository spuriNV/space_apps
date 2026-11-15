"""The fact sheet the chat model sees: a small summary of one field in grower units, built from this app's own routes.

Calls go in-process through httpx's ASGI transport, so presets, drawn `my_` fields and tapped `pt_` spots resolve the
same way the frontend sees them. Any part that fails or is missing is left out; the model is told missing = not available.
Cached per field for 10 minutes."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

MM_PER_IN = 25.4
_cache: dict[str, tuple[float, dict]] = {}
TTL = 600


def _v(x: Any) -> Any:
    """SourcedNumber -> its value; plain values pass through."""
    return x.get("value") if isinstance(x, dict) else x


def _r(x: Any, n: int = 1):
    x = _v(x)
    return round(x, n) if isinstance(x, (int, float)) else None


def _in(mm: Any, n: int = 1):
    mm = _v(mm)
    return round(mm / MM_PER_IN, n) if isinstance(mm, (int, float)) else None


def _rng(x: Any, n: int = 1):
    if not isinstance(x, dict) or x.get("value") is None:
        return None
    out = {"about": round(x["value"], n)}
    if x.get("low") is not None and x.get("high") is not None:
        out["range"] = [round(x["low"], n), round(x["high"], n)]
    return out


async def _get(c: httpx.AsyncClient, path: str) -> dict | None:
    try:
        r = await c.get(path, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:  # noqa: BLE001  a missing part is left out, never fails the chat
        return None


def _location(L: dict) -> dict:
    soil = L.get("soil") or {}
    water = L.get("water") or {}
    hist = L.get("crop_history") or {}
    years = sorted(hist)[-6:]
    awc = _v(soil.get("awc_mm_per_m"))
    out = {
        "name": L.get("farmer_name") or L.get("name"),
        "acres": _r(L.get("acres"), 0),
        "county": L.get("county_name") or ((L.get("county") or {}).get("name") if isinstance(L.get("county"), dict) else L.get("county")),
        "region": L.get("region"),
        "kind": {"rice": "rice field", "forage": "forage or alfalfa field"}.get(L.get("family"), L.get("family")),
        "crops_by_year_from_satellite_crop_maps": {y: hist[y] for y in years},
        "soil": {
            "name": soil.get("muname"),
            "texture": soil.get("texture_class"),
            "drainage": soil.get("drainage_class"),
            "hydrologic_group": soil.get("hydrologic_group"),
            "water_held_inches_per_foot": round(awc * 12 / 1000, 1) if isinstance(awc, (int, float)) else None,
            "organic_matter_percent": _r(soil.get("om_pct")),
            "salt_ds_per_m": _r(soil.get("ec_ds_m") or soil.get("ec")),
            "sand_silt_clay_percent": [_r(soil.get(k), 0) for k in ("sand_pct", "silt_pct", "clay_pct")] if soil.get("clay_pct") is not None else None,
        } if soil else None,
        "water": {
            "source": water.get("source"),
            "irrigation_district": water.get("district") or water.get("nearest_district"),
            "groundwater_basin": water.get("sgma_subbasin"),
            "groundwater_basin_priority": water.get("sgma_priority"),
            "critically_overdrafted": water.get("critically_overdrafted"),
            "example_water_limit_acre_feet_per_acre": _r(water.get("example_limit_af_ac")),
            "water_limit_entered_acre_feet_per_acre": _r((water.get("allocation_input") or {}).get("value")),
        } if water else None,
        "events": [f"{e.get('date', '')[:7]}: {e.get('title')}" for e in (L.get("events") or [])[:4] if isinstance(e, dict)],
        "is_tapped_spot_or_drawn_field": bool(L.get("spot") or L.get("mine")),
    }
    return out


def _nasa(N: dict) -> dict:
    rd = N.get("readings") or {}

    def g(k):
        return (rd.get(k) or {}).get("value")

    def when(k):
        return (rd.get(k) or {}).get("obs_date")
    return {
        "reading_date": N.get("step"),
        "rain_since_1_oct_inches": _in(g("imerg_wy_to_date_mm")),
        "normal_rain_since_1_oct_inches": _in(g("imerg_wy_to_date_normal_mm")),
        "rain_source": "NASA GPM IMERG satellite rain",
        "soil_moisture_root_zone_percentile": _r(g("smap_rootzone_pct"), 0),
        "soil_moisture_date": when("smap_rootzone_pct"),
        "soil_moisture_source": "NASA SMAP, one reading for a square about 6 miles across",
        "groundwater_percentile": _r(g("grace_gw_pct"), 0),
        "groundwater_date": when("grace_gw_pct"),
        "groundwater_source": "NASA GRACE-FO, whole basin, not the grower's own well",
        "greenness_ndvi_0_to_1": _r(g("hls_ndvi"), 2),
        "greenness_date": when("hls_ndvi"),
        "greenness_source": "NASA HLS (Landsat and Sentinel-2)",
        "share_of_field_under_water_percent": _r((g("dswx_water_frac") or 0) * 100, 0) if g("dswx_water_frac") is not None else None,
        "plain_language": N.get("plain_language"),
        "note": "Percentile compares with the same time of year in past years: 50 typical, 0 driest, 100 wettest.",
    }


def _strategies(S: dict) -> list[dict]:
    items = [s for s in (S.get("items") or []) if isinstance(s, dict) and not s.get("filtered_out")]
    items.sort(key=lambda s: (not s.get("is_baseline"), -((s.get("composite") or {}).get("value") or 0)))
    out = []
    for s in items[:4]:
        w = s.get("water") or {}
        ex = s.get("exposure") or {}
        out.append({
            "name": s.get("short_name") or s.get("name"),
            "is_current_rotation": bool(s.get("is_baseline")),
            "water_need_acre_feet_per_acre_per_year": _rng(w.get("irrigation_need_af_ac")),
            "bare_soil_days_per_year": _rng(ex.get("bare_days_per_year"), 0),
            "overall_score_0_to_100_rule_of_thumb": _rng(s.get("composite"), 0),
            "fits_water_limit": (w.get("allocation_check") or {}).get("status"),
        })
    return out


def _outlook(O: dict) -> dict:
    cpc = (O.get("cpc_seasonal_outlook") or {}).get("seasons") or []
    dm = (O.get("drought") or {}).get("us_drought_monitor") or {}
    res = O.get("reservoirs_now") or {}
    snow = (O.get("snowpack_runoff") or {}).get("snow_now_statewide") or {}
    return {
        "label": "NOAA outlook, not a forecast",
        "next_seasons": [{"season": (x.get("temperature") or {}).get("valid_season") or x.get("season"),
                          "temperature": (x.get("temperature") or {}).get("category"),
                          "rain": (x.get("precipitation") or {}).get("category")} for x in cpc[:3]],
        "drought_monitor": {"county": dm.get("county"), "worst": dm.get("worst_category"), "map_date": dm.get("map_date")} if dm else None,
        "reservoirs": [{"name": (v.get("name") or k).title(), "percent_full": _r(v.get("pct_of_capacity"), 0),
                        "percent_of_average_for_date": _r(v.get("pct_of_cdec_average"), 0)} for k, v in res.items() if isinstance(v, dict)],
        "statewide_snow_percent_of_normal": _r(snow.get("pct_of_normal_for_date"), 0),
        "snow_note": _v((snow.get("pct_of_normal_for_date") or {}).get("note")) if isinstance(snow.get("pct_of_normal_for_date"), dict) else None,
    }


def _prune(x: Any) -> Any:
    """Drop None, empty lists and empty dicts so the sheet stays short."""
    if isinstance(x, dict):
        d = {k: _prune(v) for k, v in x.items()}
        return {k: v for k, v in d.items() if v not in (None, [], {}, "")}
    if isinstance(x, list):
        return [v for v in (_prune(i) for i in x) if v not in (None, [], {}, "")]
    return x


async def build_facts(fid: str, water_limit: float | None = None) -> dict:
    hit = _cache.get(fid)
    if hit and time.time() - hit[0] < TTL:
        return _with_limit(hit[1], water_limit)
    from ..main import app  # noqa: PLC0415  (import here: main imports this package)
    base = f"/api/locations/{fid}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://app") as c:
        L, N, S, O = await asyncio.gather(_get(c, base), _get(c, base + "/nasa_now"), _get(c, base + "/strategies"), _get(c, base + "/outlook"))
    facts = {
        "field": _location(L) if L else None,
        "satellite_readings_today": _nasa(N) if N else None,
        "rotations": _strategies(S) if S else None,
        "coming_season": _outlook(O) if O else None,
    }
    if not L:
        facts["note"] = "This field's details could not be loaded."
    facts = _prune(facts)
    if L:
        _cache[fid] = (time.time(), facts)
    return _with_limit(facts, water_limit)


def _with_limit(facts: dict, limit: float | None) -> dict:
    """The water limit set on screen (client state, example unless the grower changed it), and each rotation against it."""
    if limit is None:
        return facts
    f = {**facts, "water_limit_on_screen_acre_feet_per_acre": round(limit, 1)}
    rot = []
    for r in facts.get("rotations") or []:
        need = (r.get("water_need_acre_feet_per_acre_per_year") or {}).get("about")
        r = {k: v for k, v in r.items() if k != "fits_water_limit"}
        if need is not None:
            r["over_limit_by_acre_feet_per_acre"] = round(max(0.0, need - limit), 1)
        rot.append(r)
    if rot:
        f["rotations"] = rot
    return f
