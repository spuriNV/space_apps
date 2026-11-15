"""Compact AAFC Soil Landscapes of Canada v3.2 table for British Columbia, read by the any-location pipeline at run time.

backend/bc/fetch_slc.py summarises the SLC polygon under the one BC registry field from the national 36 MB zip. A tapped
BC point needs the same summary without a 36 MB download per request, so this script reads the zip once and writes, for
every SLC polygon with a BC soil component: a simplified outline (about 100 m; SLC is a 1:1,000,000 map) and the same
proportion-weighted 0-100 cm summary fetch_slc.py computes (texture, available water, organic matter, dominant drainage
and derived hydrologic group, the soils and their shares).

Writes backend/api/app/anyloc/slc_bc.json.gz (committed; the API needs no shapely or zip to use it).
Run: cd backend/catalog && uv run python slc_bc.py [--zip /path/to/ca_all_slc_v3r2.zip]
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import zipfile
from pathlib import Path

import requests
from shapely.geometry import mapping

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "backend" / "bc"))
from fetch_slc import AWHC, DRAIN, PAGE, ROOT_DEPTH, ZIP, dbf, hsg, profile, r, shp_polygons  # noqa: E402
from fetch_soilgrids import usda_texture  # noqa: E402

OUT = REPO / "backend" / "api" / "app" / "anyloc" / "slc_bc.json.gz"
OUT_REST = REPO / "backend" / "api" / "app" / "anyloc" / "slc_can.json.gz"   # AB SK MB ON QC (read after slc_bc by bc.slc_at)
REST_PROVINCES = {"AB", "SK", "MB", "ON", "QC"}
REST_BOX = (-120.1, 41.6, -57.0, 62.0)
CACHE_ZIP = REPO / "data" / "cache" / "_slc" / "ca_all_slc_v3r2.zip"
BC_BOX = (-139.1, 48.2, -114.0, 60.1)
SIMPLIFY_DEG = 0.001


def load_zip(path: str | None) -> zipfile.ZipFile:
    p = Path(path) if path else CACHE_ZIP
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        print("downloading", ZIP)
        p.write_bytes(requests.get(ZIP, timeout=600).content)
    return zipfile.ZipFile(io.BytesIO(p.read_bytes()))


def summarise(comps: list[dict]) -> dict:
    def weighted(key):
        vs = [(cp[key], cp["percent"]) for cp in comps if cp.get(key) is not None]
        w = sum(p for _, p in vs)
        return None if not w else sum(v * p for v, p in vs) / w

    def dominant(key):
        share: dict[str, int] = {}
        for cp in comps:
            if cp.get(key):
                share[cp[key]] = share.get(cp[key], 0) + cp["percent"]
        return max(share.items(), key=lambda kv: kv[1]) if share else (None, 0)

    sand, silt, clay = weighted("sand_pct"), weighted("silt_pct"), weighted("clay_pct")
    tot = (sand or 0) + (silt or 0) + (clay or 0)
    if tot:
        sand, silt, clay = sand * 100 / tot, silt * 100 / tot, clay * 100 / tot
    awcs = [cp["awc_mm_per_m"] for cp in comps if cp.get("awc_mm_per_m") is not None]
    oms = [cp["om_pct"] for cp in comps if cp.get("om_pct") is not None]
    dr, drp = dominant("drainage_class")
    hg, hgp = dominant("hydrologic_group")
    return {"sand_pct": r(sand), "silt_pct": r(silt), "clay_pct": r(clay),
            "texture_class": usda_texture(sand, silt, clay) if tot else None,
            "awc_mm_per_m": r(weighted("awc_mm_per_m")), "awc_low": r(min(awcs, default=None)), "awc_high": r(max(awcs, default=None)),
            "om_pct": r(weighted("om_pct"), 2), "om_low": r(min(oms, default=None), 2), "om_high": r(max(oms, default=None), 2),
            "ph_0_30cm": r(weighted("ph_0_30cm")),
            "drainage_class": dr, "drainage_share_pct": drp, "hydrologic_group": hg, "hydrologic_group_share_pct": hgp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", help="local copy of ca_all_slc_v3r2.zip (else data/cache/_slc/, downloaded once)")
    ap.add_argument("--rest", action="store_true", help="write the AB/SK/MB/ON/QC table (slc_can.json.gz, coarser outlines) instead of BC")
    a = ap.parse_args()
    z = load_zip(a.zip)
    provs, box, out_path, simp = (REST_PROVINCES, REST_BOX, OUT_REST, 0.004) if a.rest else ({"BC"}, BC_BOX, OUT, SIMPLIFY_DEG)
    names = {n.lower(): n for n in z.namelist()}
    rd = lambda suffix: z.read(next(v for k, v in names.items() if k.endswith(suffix)))  # noqa: E731
    cmp_all = [x for x in dbf(rd("ca_all_slc_v3r2_cmp.dbf")) if x["PROVINCE"] in provs]
    bc_polys = {x["POLY_ID"] for x in cmp_all}
    soil_ids = {x["SOIL_ID"] for x in cmp_all}
    snt = {x["SOIL_ID"]: x for x in dbf(rd("soil_name_canada_v2r20231107.dbf")) if x["SOIL_ID"] in soil_ids}
    crt = {x["CMP_ID"]: x for x in dbf(rd("ca_all_slc_v3r2_crt.dbf"))}
    slt: dict[str, list] = {}
    for x in dbf(rd("soil_layer_canada_v2r20231108.dbf")):
        if x["SOIL_ID"] in soil_ids:
            slt.setdefault(x["SOIL_ID"], []).append(x)
    by_poly: dict[str, list] = {}
    for x in cmp_all:
        by_poly.setdefault(x["POLY_ID"], []).append(x)
    attrs = list(dbf(rd("ca_all_slc_v3r2.dbf")))
    out = []
    for i, pg in shp_polygons(rd("ca_all_slc_v3r2.shp"), rd("ca_all_slc_v3r2.shx"), box):
        pid = attrs[i]["POLY_ID"]
        if pid not in bc_polys or pg is None or pg.is_empty:
            continue
        comps = []
        for x in sorted(by_poly[pid], key=lambda x: int(x["CMP"])):
            sn, cr = snt.get(x["SOIL_ID"], {}), crt.get(x["CMP_ID"], {})
            summ, layers = profile(slt.get(x["SOIL_ID"], []))
            grp, _why = hsg(sn.get("DRAINAGE", ""), layers, cr.get("DEPTH", ""))
            tex = None if None in (summ["sand_pct"], summ["silt_pct"], summ["clay_pct"]) else usda_texture(summ["sand_pct"], summ["silt_pct"], summ["clay_pct"])
            comps.append({"percent": int(x["PERCENT"]), "soil_name": sn.get("SOILNAME", "").title() or x["SOIL_CODE"],
                          "drainage_class": DRAIN.get(sn.get("DRAINAGE", ""), sn.get("DRAINAGE")), "hydrologic_group": grp,
                          "texture_class": tex, "awhc_class_mm": AWHC.get(cr.get("AWHC", "")),
                          "root_depth_class": ROOT_DEPTH.get(cr.get("DEPTH", ""), cr.get("DEPTH")),
                          "sand_pct": summ["sand_pct"], "silt_pct": summ["silt_pct"], "clay_pct": summ["clay_pct"],
                          "awc_mm_per_m": summ["awc_mm_per_m"], "ph_0_30cm": summ["ph_0_30cm"],
                          "om_pct": None if summ["org_carbon_pct"] is None else summ["org_carbon_pct"] * 1.724})
        g = pg.simplify(simp, preserve_topology=True)
        geo = mapping(g)
        polys = [geo["coordinates"]] if geo["type"] == "Polygon" else list(geo["coordinates"]) if geo["type"] == "MultiPolygon" else []
        rings = [[[round(x, 4), round(y, 4)] for x, y in ring] for poly in polys for ring in poly]
        rings = [rg for rg in rings if len(rg) >= 4]
        if not rings:
            continue
        out.append({"poly_id": pid, "bbox": [round(v, 4) for v in pg.bounds], "rings": rings, "summary": summarise(comps),
                    "components": [{k: (r(v, 1) if isinstance(v, float) else v) for k, v in cp.items()} for cp in comps]})
    doc = {"source": {"id": "aafc_slc_v3_2", "title": "AAFC Soil Landscapes of Canada v3.2 (1:1,000,000) with the Soil Name and Soil Layer tables v2",
                      "url": PAGE, "download": ZIP, "verified": True,
                      "citation": "Soil Landscapes of Canada Working Group, 2011. Soil Landscapes of Canada version 3.2. Agriculture and Agri-Food Canada.",
                      "licence": "Free use with acknowledgement of Agriculture and Agri-Food Canada's authorship"},
           "method": "backend/bc/fetch_slc.py per-soil 0-100 cm profile and NEH 630 hydrologic group, proportion-weighted per polygon; "
                     f"drainage and hydrologic group = dominant condition; outlines simplified {simp} deg (even-odd rings)",
           "polygons": out}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wt", compresslevel=9) as f:
        json.dump(doc, f, separators=(",", ":"))
    print(f"{len(out)} SLC polygons -> {out_path} ({out_path.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
