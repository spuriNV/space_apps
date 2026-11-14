"""Pick the two example field polygons against CDL (spec B1).

Field boundaries: DWR / Land IQ Statewide Crop Mapping 2023 (final) field
polygons, queried from DWR's public ArcGIS MapServer (no account). Each
candidate field near the preset centre is scored against the CDL rasters
cached by `cdl.py` (majority class + purity per year). The best candidate is
written to polygons/<preset>.geojson in EPSG:4326 (lon, lat), together with a
10 km training box centred on the field.

Usage: uv run python -m fieldshift_field.select_fields [preset ...]
"""
from __future__ import annotations

import json
import sys
import urllib.parse

import numpy as np
from shapely.geometry import box, mapping, shape
from shapely import transform as _tf
transform = lambda f, g: _tf(g, lambda xy: np.column_stack(f(xy[:, 0], xy[:, 1])))

from .cdl import _get
from .common import CDL_CRS, POLY_DIR, PRESETS, WORK_CRS, cache, now, read_json, to_crs, write_json
from .zonal import cdl_year_stats

DWR_2023 = ("https://utility.arcgis.com/usrsvcs/servers/d94e891e00364e49a2ed9e9e2e27837d/rest/services/"
            "Planning/i15_Crop_Mapping_2023/MapServer/0")
SEARCH_HALF_DEG = 0.035  # ~3-4 km search window around the preset centre

RICE, FALLOW, ALFALFA, CORN = 3, 61, 36, 1  # codes confirmed from cdl_legend.json at run time


def dwr_fields(lon, lat, half=SEARCH_HALF_DEG):
    feats, offset = [], 0
    while True:
        d = json.loads(_get(DWR_2023 + "/query", {
            "geometry": f"{lon-half},{lat-half},{lon+half},{lat+half}", "geometryType": "esriGeometryEnvelope",
            "inSR": 4326, "outSR": 4326, "spatialRel": "esriSpatialRelIntersects",
            "outFields": "UniqueID,ACRES,COUNTY,CLASS1,SUBCLASS1,CROPTYP1,CROPTYP2,MAIN_CROP,MAIN_CROP_DATE",
            "returnGeometry": "true", "f": "geojson", "resultOffset": offset, "resultRecordCount": 1000}))
        fs = d.get("features", [])
        feats += fs
        if len(fs) < 1000:
            return feats
        offset += 1000


def _check_legend(preset):
    leg = read_json(cache(preset) / "cdl_legend.json")["classes"]
    for code, want in [(RICE, "Rice"), (FALLOW, "Fallow/Idle Cropland"), (ALFALFA, "Alfalfa"), (CORN, "Corn")]:
        assert leg[str(code)]["name"] == want, (code, leg[str(code)])


def score_car(st):
    p = lambda y, c: st[y]["fractions"].get(c, 0.0)
    ok = st[2021]["majority"] == RICE and st[2022]["majority"] == FALLOW and st[2023]["majority"] == RICE
    return ok, min(p(2021, RICE), p(2022, FALLOW), p(2023, RICE))


def score_caf(st):
    yrs = [y for y in st if st[y]["majority"] in (ALFALFA, CORN)]
    alf = sum(st[y]["majority"] == ALFALFA for y in st)
    corn = sum(st[y]["majority"] == CORN for y in st)
    ok = alf >= 3 and len(yrs) >= 8
    # prefer fields with both alfalfa and corn in history, then by forage-years and mean purity
    purity = np.mean([max(st[y]["fractions"].values()) for y in yrs]) if yrs else 0
    return ok, (min(alf, 1) + min(corn, 1)) + len(yrs) / 18 + 0.5 * purity


def select(preset: str):
    _check_legend(preset)
    cfg = PRESETS[preset]
    lon0, lat0 = cfg["centre"]
    target = cfg["target_ha"]
    to_utm = to_crs("EPSG:4326", WORK_CRS)
    to_alb = to_crs("EPSG:4326", CDL_CRS)
    feats = dwr_fields(lon0, lat0)
    years = list(range(2008, 2026))
    cands = []
    for f in feats:
        g = shape(f["geometry"])
        if g.is_empty:
            continue
        gu = transform(to_utm.transform, g)
        area_ha = gu.area / 1e4
        if not (0.5 * target <= area_ha <= 1.6 * target):
            continue
        ga = transform(to_alb.transform, g)
        st = {y: cdl_year_stats(preset, ga, y) for y in years}
        if any(s is None for s in st.values()):
            continue
        ok, sc = (score_car if preset.startswith("car") else score_caf)(st)
        if not ok:
            continue
        c = gu.centroid
        cx, cy = to_utm.transform(lon0, lat0)
        dist_km = ((c.x - cx) ** 2 + (c.y - cy) ** 2) ** 0.5 / 1000
        size_pen = abs(area_ha - target) / target
        cands.append({"f": f, "g": g, "gu": gu, "area_ha": area_ha, "score": sc, "dist_km": dist_km,
                      "rank": sc - 1.0 * size_pen - 0.05 * dist_km, "stats": st})
    print(f"{preset}: {len(feats)} DWR fields in window, {len(cands)} pass the CDL rule")
    if not cands:
        raise SystemExit(f"{preset}: no candidate field passes the CDL rule")
    cands.sort(key=lambda c: -c["rank"])
    for c in cands[:5]:
        print(" ".join(str(c["stats"][y]["majority"]) for y in sorted(c["stats"])))
        print(f"  {c['f']['properties']['UniqueID']}: {c['area_ha']:.1f} ha, score {c['score']:.3f}, "
              f"{c['dist_km']:.2f} km from centre, rank {c['rank']:.3f}")
    best = cands[0]
    g = best["g"]
    if g.geom_type == "MultiPolygon":  # keep the largest part
        g = max(g.geoms, key=lambda p: p.area)
    g = g.simplify(0)  # no-op, keeps geometry exact
    leg = read_json(cache(preset) / "cdl_legend.json")["classes"]
    hist = {str(y): leg.get(str(s["majority"]), {}).get("name", str(s["majority"])) for y, s in best["stats"].items()}
    cen = g.centroid
    props = {
        "preset_id": preset, "name": cfg["name"], "area_ha": round(best["area_ha"], 2),
        "centroid": {"lon": round(cen.x, 6), "lat": round(cen.y, 6)},
        "crs": "EPSG:4326 (lon, lat)", "crs_working": WORK_CRS,
        "boundary_source": {"id": "dwr_landiq_crop_mapping_2023", "title": "DWR Statewide Crop Mapping 2023 (Land IQ), final",
                            "url": DWR_2023, "verified": True, "dwr_unique_id": best["f"]["properties"]["UniqueID"],
                            "dwr_attributes": best["f"]["properties"]},
        "selection_rule": ("CDL majority Rice 2021, Fallow/Idle 2022, Rice 2023; ranked by min purity, size vs 60 ha, distance"
                           if preset.startswith("car") else
                           "CDL majority Alfalfa or Corn in >= 8 of 2008-2025 with >= 3 alfalfa years; ranked by both-crops, forage years, purity, size vs 32 ha, distance"),
        "cdl_majority_by_year": hist, "selected_at": now(),
        "candidates_considered": len(cands),
    }
    POLY_DIR.mkdir(exist_ok=True)
    write_json(POLY_DIR / f"{preset}.geojson", {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": props, "geometry": mapping(g)}]})
    # 10 km training box centred on the field centroid, square in UTM 10N
    cu = best["gu"].centroid
    bx = box(cu.x - 5000, cu.y - 5000, cu.x + 5000, cu.y + 5000)
    b4326 = transform(to_crs(WORK_CRS, "EPSG:4326").transform, bx)
    write_json(POLY_DIR / f"{preset}_training_box.json", {
        "preset_id": preset, "size_km": 10, "centre": props["centroid"],
        "bbox_epsg32610": [round(v, 1) for v in bx.bounds],
        "bbox_epsg4326": [round(v, 6) for v in b4326.bounds],
        "geometry_epsg4326": mapping(b4326),
        "note": "Square in EPSG:32610 centred on the field centroid; bbox_epsg4326 is its lon/lat envelope (minx, miny, maxx, maxy)."})
    print(f"  -> chose {props['boundary_source']['dwr_unique_id']} {props['area_ha']} ha at {props['centroid']}")
    return props


if __name__ == "__main__":
    for p in (sys.argv[1:] or list(PRESETS)):
        select(p)
