"""Reserve outlines within ~20 km of the BC field, for the map as context only (no analysis of reserve land).

Source: BC Data Catalogue WFS layer WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP (CLSS legal reserve boundaries with
band names). These are legal survey boundaries, not maps of traditional territory or of where a Nation's rights apply.

Writes data/cache/bc_salmon_river_forage/reserves_nearby.geojson (EPSG:4326, simplified to ~20 m, source in "properties").
Served by GET /api/locations/bc_salmon_river_forage/first_nations/reserves.geojson.

Run: cd backend/bc && uv run python fetch_reserves.py
"""
from __future__ import annotations

import warnings

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

from common import CACHE, FID, get, now, polygon, write_json

WFS = "https://openmaps.gov.bc.ca/geo/pub/wfs"
LAYER = "WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP"
RADIUS_KM = 20
WORK = "EPSG:32611"          # UTM 11N: the field is at -119.4 (distances only)
SIMPLIFY_M = 20
warnings.filterwarnings("ignore", category=DeprecationWarning)


def main():
    g, _ = polygon()
    to_w = Transformer.from_crs("EPSG:4326", WORK, always_xy=True).transform
    to_ll = Transformer.from_crs(WORK, "EPSG:4326", always_xy=True).transform
    gw = transform(to_w, g)
    x0, y0, x1, y1 = transform(to_ll, gw.buffer(RADIUS_KM * 1000 + 2000)).bounds
    p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeName": LAYER, "outputFormat": "json",
         "srsName": "EPSG:4326", "sortBy": "OBJECTID", "count": 2000, "bbox": f"{x0},{y0},{x1},{y1},EPSG:4326"}
    feats = get(WFS, params=p, timeout=180).json()["features"]
    out = []
    for f in feats:
        rw = transform(to_w, shape(f["geometry"]))
        d_km = gw.distance(rw) / 1000
        if d_km > RADIUS_KM:
            continue
        pr = f["properties"]
        out.append({"type": "Feature",
                    "properties": {"name": pr.get("ENGLISH_NAME"), "band": pr.get("BAND_NAME"), "band_number": str(pr.get("BAND_NUMBER")),
                                   "area_ha": round(rw.area / 1e4, 1), "distance_to_field_km": round(d_km, 1), "context_only": True},
                    "geometry": mapping(transform(to_ll, rw.simplify(SIMPLIFY_M, preserve_topology=True)))})
    out.sort(key=lambda f: f["properties"]["distance_to_field_km"])
    write_json(CACHE / "reserves_nearby.geojson", {
        "type": "FeatureCollection",
        "properties": {
            "preset_id": FID, "fetched_at": now(), "radius_km": RADIUS_KM, "simplified_m": SIMPLIFY_M,
            "source": {"title": "Indian reserves with band names (CLSS boundaries), BC Data Catalogue", "layer": LAYER,
                       "url": "https://catalogue.data.gov.bc.ca/dataset/8efe9193-80d2-4fdf-a18c-d531a94196ad", "wfs": WFS,
                       "licence": "Open Government Licence - British Columbia", "verified": True},
            "note": "Context only: legal reserve boundaries, not traditional territories. No reserve land is analysed by this app.",
        },
        "features": out})
    print(f"{len(out)} reserves within {RADIUS_KM} km:", [(f["properties"]["name"], f["properties"]["distance_to_field_km"]) for f in out])


if __name__ == "__main__":
    main()
