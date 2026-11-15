"""Pick a real forage field in the lower Salmon River valley, off reserve land, and write its outline.

Steps (no keys; every layer is public):
1. AAFC ACI 2014-2020 and 2022-2025 (aci.py clips): pixels classed 122 Pasture / Forages in at least MIN_YEARS of
   those 11 years ("stable forage"). 2011-2013 and 2021 are skipped: AAFC mapped this area only as 120 Agriculture
   (undifferentiated) in those years.
2. Indian reserves from BC's WFS layer WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP (CLSS boundaries with band
   names). Any candidate within RESERVE_BUFFER_M of a reserve is dropped: this example is built on non-reserve
   farmland (see docs/bc-first-nations.md).
3. Legal parcels from ParcelMap BC (WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW, open WFS) and the Agricultural Land
   Reserve (WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS). Field outline = one parcel inside the ALR, clipped to its stable-
   forage pixels (largest connected part, 30 m pixel edges smoothed by a +/-15 m buffer). BC publishes no field
   boundary layer like California's DWR / Land IQ crop map, so this is a parcel-and-pixel outline, labelled as such.
   Parcel identifiers (PID) and owner details are not stored.
4. Candidates 15-80 ha are ranked by forage purity over the years; the best one becomes
   backend/field/polygons/bc_salmon_river_forage.geojson (+ _training_box.json, a 10 km box like the CA fields).

Run: uv run python select_field.py
"""
from __future__ import annotations

import json

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import shapes
from scipy import ndimage
from shapely.geometry import box, mapping, shape
from shapely.ops import transform, unary_union  # noqa: F401
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

from common import CACHE, FID, POLY, get, now, write_json

WFS = "https://openmaps.gov.bc.ca/geo/pub/wfs"
YEARS = [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2022, 2023, 2024, 2025]
MIN_YEARS = 9
RESERVE_BUFFER_M = 1000
SEARCH = (-119.45, 50.53, -119.22, 50.68)   # lower Salmon River valley, Silver Creek - Salmon Valley (lon/lat)
HA_MIN, HA_MAX = 15, 80
WORK = "EPSG:32610"


def wfs(layer: str, bbox, extra: dict | None = None) -> list:
    feats, start = [], 0
    while True:
        p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeName": layer,
             "outputFormat": "application/json", "srsName": "EPSG:4326", "count": 2000, "startIndex": start, "sortBy": "OBJECTID",
             "bbox": ",".join(map(str, bbox)) + ",EPSG:4326", **(extra or {})}
        d = get(WFS, params=p, timeout=180).json()
        feats += d["features"]
        if len(d["features"]) < 2000:
            return feats
        start += 2000


def main():
    to_w = Transformer.from_crs("EPSG:4326", WORK, always_xy=True).transform
    # 1. stable forage
    stack = []
    for y in YEARS:
        with rasterio.open(CACHE / "rasters" / f"aci_{y}.tif") as r:
            stack.append(r.read(1))
            tr, crs = r.transform, r.crs
    stack = np.stack(stack)
    nfor = (stack == 122).sum(0)
    stable = nfor >= MIN_YEARS
    to_aci = Transformer.from_crs(crs, WORK, always_xy=True).transform

    # 2. reserves
    res = wfs("WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP", (-119.9, 50.3, -118.8, 50.95))
    reserves = [{"name": f["properties"]["ENGLISH_NAME"], "band": f["properties"]["BAND_NAME"],
                 "band_number": f["properties"]["BAND_NUMBER"], "geom_w": transform(to_w, shape(f["geometry"]))}
                for f in res]
    res_buf = unary_union([r["geom_w"] for r in reserves]).buffer(RESERVE_BUFFER_M)
    print(f"{len(reserves)} reserves in the wider box")

    # 3. ALR and parcels in the search box
    alr = unary_union([transform(to_w, shape(f["geometry"])) for f in wfs("WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS", SEARCH)])
    parcels = wfs("WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW", SEARCH)
    print(f"{len(parcels)} parcels in the search box")
    search_w = transform(to_w, box(*SEARCH))

    # stable-forage pixels as polygons in the working CRS
    lab, n = ndimage.label(stable)
    forage_polys = [transform(to_aci, shape(g)) for g, v in shapes(lab.astype("int32"), mask=stable, transform=tr) if v > 0]
    forage = unary_union(forage_polys)

    cands = []
    for f in parcels:
        p = f["properties"]
        g = transform(to_w, shape(f["geometry"]))
        if not g.is_valid:
            g = g.buffer(0)
        if not g.within(search_w.buffer(-200)) or g.intersects(res_buf) or g.area < HA_MIN * 1e4:
            continue
        if alr.intersection(g).area < 0.9 * g.area:
            continue
        fg = g.intersection(forage)
        if fg.is_empty:
            continue
        parts = list(getattr(fg, "geoms", [fg]))
        part = max(parts, key=lambda x: x.area).buffer(15, join_style=2).buffer(-15, join_style=2)
        if part.geom_type == "MultiPolygon":
            part = max(part.geoms, key=lambda x: x.area)
        ha = part.area / 1e4
        if not HA_MIN <= ha <= HA_MAX:
            continue
        # purity per year inside the outline
        back = Transformer.from_crs(WORK, crs, always_xy=True).transform
        from rasterio.features import geometry_mask
        m = ~geometry_mask([mapping(transform(back, part))], out_shape=stable.shape, transform=tr)
        pur = {y: float((stack[i][m] == 122).mean()) for i, y in enumerate(YEARS)}
        cands.append({"part": part, "ha": ha, "purity_mean": float(np.mean(list(pur.values()))),
                      "purity_min": min(pur.values()), "purity": pur, "parcel_ha": g.area / 1e4,
                      "share_of_parcel": part.area / g.area, "owner_type": p.get("OWNER_TYPE"),
                      "parcel_class": p.get("PARCEL_CLASS"),
                      "regional_district": p.get("REGIONAL_DISTRICT"), "municipality": p.get("MUNICIPALITY"),
                      "dist_reserve_km": part.distance(unary_union([r["geom_w"] for r in reserves])) / 1000})
    cands.sort(key=lambda c: (-round(c["purity_min"], 2), -c["purity_mean"]))
    print(f"{len(cands)} candidates")
    for c in cands[:12]:
        cen = transform(Transformer.from_crs(WORK, "EPSG:4326", always_xy=True).transform, c["part"].centroid)
        print(f"  {c['ha']:5.1f} ha purity mean {c['purity_mean']:.2f} min {c['purity_min']:.2f} "
              f"parcel {c['parcel_ha']:.0f} ha ({c['owner_type']}) reserve {c['dist_reserve_km']:.1f} km "
              f"at {cen.y:.4f} N {cen.x:.4f}")
    best = cands[0]
    to_ll = Transformer.from_crs(WORK, "EPSG:4326", always_xy=True).transform
    g_ll = transform(to_ll, best["part"].simplify(5))
    cen = g_ll.centroid
    near = sorted(({"name": r["name"], "band": r["band"], "band_number": r["band_number"],
                    "distance_km": round(best["part"].distance(r["geom_w"]) / 1000, 1)} for r in reserves),
                  key=lambda r: r["distance_km"])[:5]
    props = {
        "preset_id": FID, "name": "Forage field in the lower Salmon River valley (Shuswap, BC)",
        "region": "bc", "area_ha": round(best["part"].area / 1e4, 2),
        "centroid": {"lon": round(cen.x, 6), "lat": round(cen.y, 6)}, "crs": "EPSG:4326", "crs_working": WORK,
        "boundary_source": {
            "id": "parcelmap_bc_x_aafc_aci",
            "title": "ParcelMap BC legal parcel (open parcel fabric) inside the Agricultural Land Reserve, clipped to "
                     "AAFC Annual Crop Inventory Pasture / Forages pixels (class 122 in >= 9 of 11 mapped years)",
            "url": WFS + "?service=WFS&request=GetCapabilities (WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW, "
                         "WHSE_LEGAL_ADMIN_BOUNDARIES.OATS_ALR_POLYS)",
            "aci_url": "https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/data_donnees/tif/",
            "parcel_area_ha": round(best["parcel_ha"], 1), "share_of_parcel": round(best["share_of_parcel"], 2),
            "owner_type": best["owner_type"], "regional_district": best["regional_district"],
            "municipality": best["municipality"],
            "note": "No field-boundary product exists for BC (California uses DWR / Land IQ field outlines). The outline "
                    "follows 30 m pixel edges; parcel id and owner are deliberately not stored."},
        "selection_rule": (f"ACI Pasture / Forages in >= {MIN_YEARS} of {len(YEARS)} years {YEARS}; parcel fully in the "
                           f"search box {SEARCH}, >= 90% in the ALR, > {RESERVE_BUFFER_M} m from any Indian reserve; "
                           f"{HA_MIN}-{HA_MAX} ha; ranked by the lowest yearly forage purity, then the mean"),
        "aci_forage_purity_by_year": {str(k): round(v, 3) for k, v in best["purity"].items()},
        "nearest_reserves": near,
        "reserve_source": {"title": "Indian reserves with band names (CLSS boundaries), BC Data Catalogue",
                           "url": "https://catalogue.data.gov.bc.ca/dataset/8efe9193-80d2-4fdf-a18c-d531a94196ad",
                           "layer": "WHSE_ADMIN_BOUNDARIES.ADM_INDIAN_RESERVES_BANDS_SP"},
        "candidates_considered": len(cands), "selected_at": now(),
    }
    write_json(POLY, {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": props,
                                                                  "geometry": mapping(g_ll)}]})
    c_w = best["part"].centroid
    tb = box(c_w.x - 5000, c_w.y - 5000, c_w.x + 5000, c_w.y + 5000)
    tb_ll = transform(to_ll, tb)
    write_json(POLY.with_name(f"{FID}_training_box.json"), {
        "preset_id": FID, "bbox_epsg32610": list(tb.bounds), "bbox_epsg4326": list(tb_ll.bounds),
        "geometry_epsg4326": mapping(tb_ll), "note": "10 km square centred on the field (same convention as CA)"})
    # reserves near the valley for the First Nations doc (names, bands, sizes; no analysis of reserve land)
    write_json(CACHE / "reserves_nearby.json", {
        "source": props["reserve_source"], "fetched_at": now(),
        "reserves": sorted(({"name": r["name"], "band": r["band"], "band_number": r["band_number"],
                             "area_ha": round(r["geom_w"].area / 1e4, 1),
                             "distance_to_field_km": round(best["part"].distance(r["geom_w"]) / 1000, 1)}
                            for r in reserves), key=lambda r: r["distance_to_field_km"])})
    print("wrote", POLY, json.dumps({k: props[k] for k in ("area_ha", "centroid", "nearest_reserves")}, indent=1))


if __name__ == "__main__":
    main()
