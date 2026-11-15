"""AAFC Soil Landscapes of Canada (SLC) v3.2 soil for the BC field: the SLC polygon under the field, its soil components and
their layer data (no key; one 36 MB zip, nothing else to install).

Source: https://sis.agr.gc.ca/cansis/nsdb/slc/v3.2/index.html (Agriculture and Agri-Food Canada, Canadian Soil Information
Service). The zip holds the polygons (shapefile, NAD83 lon/lat), the component table (cmp: soil and % of polygon per
component), the component rating table (crt: AWHC class, rooting depth) and the national Soil Name and Soil Layer tables v2
(drainage class, water table; per-layer sand/silt/clay, organic carbon, pH, Ksat, water retention at 33 and 1500 kPa).

Scale: SLC is a 1:1,000,000 map. A polygon is a soil landscape of several km2 with up to ~10 soils in stated proportions;
which soil is in this 21 ha field is not mapped. Values below are proportion-weighted over the polygon's soils, the way
SSURGO's map-unit values are component-weighted, and drainage / hydrologic group are "dominant condition" (the class with the
largest share of the polygon), as in SSURGO's muaggatt. BC's 1:20,000-1:50,000 soil survey maps exist but have no query API.

Per soil (component), over 0-100 cm mineral layers (LFH litter layers above 0 cm are skipped):
  sand/silt/clay, organic carbon (% by weight) depth-weighted; organic matter = OC x 1.724 (van Bemmelen, assumed);
  available water = (KP33 - KP1500) x thickness: both are % of total soil volume, so 1 %vol over 1 m = 10 mm/m;
  hydrologic soil group from USDA NRCS NEH 630 ch. 7 (2009) Table 7-1 on the least-transmissive Ksat (cm/h x 2.778 = um/s),
  with the water-table depth taken from the drainage class (assumed): poorly / very poorly drained -> water table < 60 cm
  (dual group A/D, B/D, C/D or D, Ksat in 0-50 cm); imperfectly drained -> 60-100 cm (Ksat in 0-50 cm: >40 A, >10 B, >1 C,
  else D); better drained -> deeper than 100 cm (Ksat in 0-100 cm: >10 A, >4 B, >0.4 C, else D). Root-restricting layers
  < 50 cm -> D.

Writes data/cache/bc_salmon_river_forage/slc.json.
Run: cd backend/bc && uv run python fetch_slc.py
"""
from __future__ import annotations

import io
import struct
import zipfile

from pyproj import Geod
from shapely.geometry import Point, Polygon

from common import CACHE, get, now, polygon, write_json
from fetch_soilgrids import usda_texture

PAGE = "https://sis.agr.gc.ca/cansis/nsdb/slc/v3.2/index.html"
ZIP = "https://sis.agr.gc.ca/nsdb/ca/cac003/cac003.20110308.v3.2/ca_all_slc_v3r2.zip"
DRAIN = {"VR": "Very rapidly drained", "R": "Rapidly drained", "W": "Well drained", "MW": "Moderately well drained",
         "I": "Imperfectly drained", "P": "Poorly drained", "VP": "Very poorly drained", "-": "not applicable"}
AWHC = {"1": [0, 50], "2": [50, 99], "3": [100, 149], "4": [150, 199], "5": [200, 250]}
AWHC_NA = {"6": "solonetzic or saline soils", "7": "high water table", "8": "perennially frozen subsoils", "-": "water, ice or rock"}
ROOT_DEPTH = {"1": "< 25 cm", "2": "25-49 cm", "3": "50-74 cm", "4": "75-99 cm", "5": ">= 100 cm", "-": "not applicable"}
CMH_TO_UMS = 1e4 / 3600   # 1 cm/h = 2.778 um/s


def dbf(raw: bytes):
    """Rows of a dBase III table as dicts of stripped strings."""
    n = struct.unpack("<I", raw[4:8])[0]
    hl, rl = struct.unpack("<HH", raw[8:12])
    fields, o = [], 32
    while raw[o] != 0x0D:
        d = raw[o:o + 32]
        fields.append((d[:11].split(b"\0")[0].decode(), d[16]))
        o += 32
    for i in range(n):
        r = raw[hl + i * rl: hl + (i + 1) * rl]
        if r[:1] == b"*":
            continue
        rec, p = {}, 1
        for name, ln in fields:
            rec[name] = r[p:p + ln].decode("latin1").strip()
            p += ln
        yield rec


def shp_polygons(shp: bytes, shx: bytes, bbox):
    """(record index, shapely polygon) for every polygon record whose bounding box meets bbox (minx, miny, maxx, maxy)."""
    for i in range((len(shx) - 100) // 8):
        c = struct.unpack(">i", shx[100 + 8 * i:104 + 8 * i])[0] * 2 + 8
        if struct.unpack("<i", shp[c:c + 4])[0] != 5:
            continue
        x0, y0, x1, y1 = struct.unpack("<4d", shp[c + 4:c + 36])
        if x1 < bbox[0] or x0 > bbox[2] or y1 < bbox[1] or y0 > bbox[3]:
            continue
        nparts, npts = struct.unpack("<2i", shp[c + 36:c + 44])
        parts = list(struct.unpack(f"<{nparts}i", shp[c + 44:c + 44 + 4 * nparts])) + [npts]
        p0 = c + 44 + 4 * nparts
        xy = struct.unpack(f"<{2 * npts}d", shp[p0:p0 + 16 * npts])
        rings = [[(xy[2 * k], xy[2 * k + 1]) for k in range(parts[j], parts[j + 1])] for j in range(nparts)]
        # rings: clockwise = outer, counter-clockwise = hole (shapefile spec); even-odd union is enough here
        geom = None
        for r in rings:
            pr = Polygon(r).buffer(0)
            geom = pr if geom is None else geom.symmetric_difference(pr)
        yield i, geom


def num(v):
    try:
        f = float(v)
    except ValueError:
        return None
    return None if f == -9 else f


def hsg(drain: str, layers: list[dict], root_depth_code: str) -> tuple[str, str]:
    if root_depth_code in ("1", "2"):
        return "D", "root-restricting layer < 50 cm"

    def kmin(depth):
        ks = [l["ksat_cm_h"] for l in layers if l["top"] < depth and l["ksat_cm_h"] is not None]
        return None if not ks else min(ks) * CMH_TO_UMS
    if drain in ("P", "VP"):
        k = kmin(50)
        g = None if k is None else "A/D" if k > 40 else "B/D" if k > 10 else "C/D" if k > 1 else "D"
        return g, f"water table assumed < 60 cm ({DRAIN[drain].lower()}); least Ksat 0-50 cm {k and round(k, 2)} um/s"
    if drain == "I":
        k = kmin(50)
        g = None if k is None else "A" if k > 40 else "B" if k > 10 else "C" if k > 1 else "D"
        return g, f"water table assumed 60-100 cm (imperfectly drained); least Ksat 0-50 cm {k and round(k, 2)} um/s"
    k = kmin(100)
    g = None if k is None else "A" if k > 10 else "B" if k > 4 else "C" if k > 0.4 else "D"
    return g, f"water table assumed > 100 cm ({DRAIN.get(drain, drain).lower()}); least Ksat 0-100 cm {k and round(k, 2)} um/s"


def profile(rows: list[dict], top=0, bottom=100) -> tuple[dict, list[dict]]:
    """Depth-weighted 0-100 cm values of one soil's mineral layers."""
    layers = []
    for r in sorted(rows, key=lambda r: int(r["LAYER_NO"])):
        u, l = num(r["UDEPTH"]), num(r["LDEPTH"])
        if u is None or l is None or l <= 0:
            continue
        layers.append({"top": max(u, 0), "bottom": l, "horizon": (r["HZN_LIT"] + r["HZN_MAS"] + r["HZN_SUF"]).strip(),
                       "sand_pct": num(r["TSAND"]), "silt_pct": num(r["TSILT"]), "clay_pct": num(r["TCLAY"]),
                       "coarse_frag_pct": num(r["COFRAG"]), "org_carbon_pct": num(r["ORGCARB"]), "ph": num(r["PH2"]),
                       "ksat_cm_h": num(r["KSAT"]), "kp33_vol_pct": num(r["KP33"]), "kp1500_vol_pct": num(r["KP1500"]),
                       "bulk_density_g_cm3": num(r["BD"])})
    out = {}

    def wavg(key, lo=top, hi=bottom):
        s = w = 0.0
        for L in layers:
            t = min(L["bottom"], hi) - max(L["top"], lo)
            if t > 0 and L[key] is not None:
                s, w = s + L[key] * t, w + t
        return (None, 0) if not w else (s / w, w)
    for k in ("sand_pct", "silt_pct", "clay_pct", "org_carbon_pct", "coarse_frag_pct"):
        out[k] = wavg(k)[0]
    out["ph_0_30cm"] = wavg("ph", 0, 30)[0]
    out["org_carbon_pct_0_30cm"] = wavg("org_carbon_pct", 0, 30)[0]
    aw = 0.0
    covered = 0.0
    for L in layers:
        t = min(L["bottom"], bottom) - max(L["top"], top)
        if t > 0 and L["kp33_vol_pct"] is not None and L["kp1500_vol_pct"] is not None:
            aw += (L["kp33_vol_pct"] - L["kp1500_vol_pct"]) / 100 * t * 10   # mm over t cm
            covered += t
    out["awc_mm_per_m"] = None if not covered else aw * 100 / covered      # per metre of the covered depth
    out["profile_depth_cm"] = max((L["bottom"] for L in layers), default=None)
    return out, layers


def r(v, n=1):
    return None if v is None else round(v, n)


def main():
    g, _ = polygon()
    c = g.centroid
    raw = get(ZIP, timeout=600).content
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = {n.lower(): n for n in z.namelist()}
    rd = lambda suffix: z.read(next(v for k, v in names.items() if k.endswith(suffix)))  # noqa: E731
    shp, shx = rd("ca_all_slc_v3r2.shp"), rd("ca_all_slc_v3r2.shx")
    attrs = list(dbf(rd("ca_all_slc_v3r2.dbf")))
    geod = Geod(ellps="GRS80")
    field_m2 = abs(geod.geometry_area_perimeter(g)[0])
    hits = []
    for i, pg in shp_polygons(shp, shx, g.bounds):
        inter = pg.intersection(g)
        if inter.is_empty:
            continue
        hits.append({"poly_id": attrs[i]["POLY_ID"], "eco_id": attrs[i]["ECO_ID"], "contains_centroid": pg.contains(Point(c.x, c.y)),
                     "share_of_field": round(abs(geod.geometry_area_perimeter(inter)[0]) / field_m2, 3),
                     "polygon_area_km2": round(abs(geod.geometry_area_perimeter(pg)[0]) / 1e6, 1)})
    if not hits:
        raise SystemExit("no SLC polygon under the field")
    hits.sort(key=lambda h: (-h["contains_centroid"], -h["share_of_field"]))
    pid = hits[0]["poly_id"]
    cmp = sorted((x for x in dbf(rd("ca_all_slc_v3r2_cmp.dbf")) if x["POLY_ID"] == pid), key=lambda x: int(x["CMP"]))
    ids, cids = {x["SOIL_ID"] for x in cmp}, {x["CMP_ID"] for x in cmp}
    crt = {x["CMP_ID"]: x for x in dbf(rd("ca_all_slc_v3r2_crt.dbf")) if x["CMP_ID"] in cids}
    snt = {x["SOIL_ID"]: x for x in dbf(rd("soil_name_canada_v2r20231107.dbf")) if x["SOIL_ID"] in ids}
    slt: dict[str, list] = {}
    for x in dbf(rd("soil_layer_canada_v2r20231108.dbf")):
        if x["SOIL_ID"] in ids:
            slt.setdefault(x["SOIL_ID"], []).append(x)
    lat = next((x for x in dbf(rd("ca_all_slc_v3r2_lat.dbf")) if x["POLY_ID"] == pid), {})

    comps = []
    for x in cmp:
        sn, cr = snt.get(x["SOIL_ID"], {}), crt.get(x["CMP_ID"], {})
        summ, layers = profile(slt.get(x["SOIL_ID"], []))
        grp, why = hsg(sn.get("DRAINAGE", ""), layers, cr.get("DEPTH", ""))
        tex = None if None in (summ["sand_pct"], summ["silt_pct"], summ["clay_pct"]) else usda_texture(summ["sand_pct"], summ["silt_pct"], summ["clay_pct"])
        comps.append({
            "cmp": int(x["CMP"]), "percent": int(x["PERCENT"]), "soil_id": x["SOIL_ID"], "soil_name": sn.get("SOILNAME", "").title(),
            "drainage_code": sn.get("DRAINAGE"), "drainage_class": DRAIN.get(sn.get("DRAINAGE", ""), sn.get("DRAINAGE")),
            "water_table": sn.get("WATERTBL"), "parent_material": sn.get("MDEP1"), "soil_order_cssc3": sn.get("ORDER3"),
            "great_group_cssc3": sn.get("G_GROUP3"), "slope_class": x["SLOPE"], "stoniness": x["STONE"],
            "awhc_class": cr.get("AWHC"), "awhc_class_mm": AWHC.get(cr.get("AWHC", "")), "awhc_na_reason": AWHC_NA.get(cr.get("AWHC", "")),
            "root_depth_class": ROOT_DEPTH.get(cr.get("DEPTH", ""), cr.get("DEPTH")),
            "hydrologic_group": grp, "hydrologic_group_basis": why,
            "texture_class_0_100cm": tex, **{k: r(v, 2) for k, v in summ.items()},
            "om_pct_0_100cm": r(None if summ["org_carbon_pct"] is None else summ["org_carbon_pct"] * 1.724, 2),
            "layers": layers})

    def weighted(key):
        vs = [(cp[key], cp["percent"]) for cp in comps if cp.get(key) is not None]
        w = sum(p for _, p in vs)
        return None if not w else sum(v * p for v, p in vs) / w

    def dominant(key):
        share: dict[str, int] = {}
        for cp in comps:
            if cp.get(key):
                share[cp[key]] = share.get(cp[key], 0) + cp["percent"]
        best = max(share.items(), key=lambda kv: kv[1]) if share else (None, 0)
        return best[0], best[1], dict(sorted(share.items(), key=lambda kv: -kv[1]))

    sand, silt, clay = weighted("sand_pct"), weighted("silt_pct"), weighted("clay_pct")
    tot = (sand or 0) + (silt or 0) + (clay or 0)
    if tot:
        sand, silt, clay = sand * 100 / tot, silt * 100 / tot, clay * 100 / tot
    dr, dr_pct, dr_share = dominant("drainage_class")
    hg, hg_pct, hg_share = dominant("hydrologic_group")
    awcs = [cp["awc_mm_per_m"] for cp in comps if cp["awc_mm_per_m"] is not None]
    oms = [cp["om_pct_0_100cm"] for cp in comps if cp["om_pct_0_100cm"] is not None]
    top = comps[0]
    write_json(CACHE / "slc.json", {
        "source": {"id": "aafc_slc_v3_2", "title": "AAFC Soil Landscapes of Canada v3.2 (1:1,000,000) with the Soil Name and Soil Layer tables v2",
                   "url": PAGE, "download": ZIP, "accessed": now()[:10], "verified": True,
                   "citation": "Soil Landscapes of Canada Working Group, 2011. Soil Landscapes of Canada version 3.2. Agriculture and Agri-Food Canada.",
                   "licence": "Free use with acknowledgement of Agriculture and Agri-Food Canada's authorship (readme.txt)"},
        "fetched_at": now(), "scale": "1:1,000,000",
        "field_centroid_lonlat": [round(c.x, 5), round(c.y, 5)],
        "polygons_under_field": hits, "poly_id": pid, "land_area_ha": num(lat.get("LAND_AREA", "")) if lat else None,
        "components": comps,
        "summary": {
            "sand_pct": r(sand), "silt_pct": r(silt), "clay_pct": r(clay),
            "texture_class": None if not tot else usda_texture(sand, silt, clay),
            "awc_mm_per_m": r(weighted("awc_mm_per_m")), "awc_low": r(min(awcs, default=None)), "awc_high": r(max(awcs, default=None)),
            "om_pct": r(weighted("om_pct_0_100cm"), 2), "om_low": r(min(oms, default=None), 2), "om_high": r(max(oms, default=None), 2),
            "ph_0_30cm": r(weighted("ph_0_30cm")),
            "drainage_class": dr, "drainage_share_pct": dr_pct, "drainage_by_share": dr_share,
            "hydrologic_group": hg, "hydrologic_group_share_pct": hg_pct, "hydrologic_group_by_share": hg_share,
            "first_component": {"soil_name": top["soil_name"], "percent": top["percent"], "drainage_class": top["drainage_class"],
                                "hydrologic_group": top["hydrologic_group"], "texture_class_0_100cm": top["texture_class_0_100cm"]},
            "method": "proportion-weighted over the polygon's soils, 0-100 cm mineral layers; drainage and hydrologic group = dominant "
                      "condition (largest share of the polygon)",
        },
        "notes": ["SLC is a 1:1,000,000 map: the polygon is a soil landscape of several km2 and which of its soils is in this field is not "
                  "mapped. A soil test or the BC 1:20,000 soil survey map is the field-scale answer.",
                  "Available water = (water at 33 kPa - water at 1500 kPa), both % of total soil volume, over 0-100 cm. The SLC "
                  "component AWHC class (awhc_class_mm) is AAFC's own rating and is kept per soil for comparison.",
                  "Organic matter = organic carbon x 1.724 (van Bemmelen factor, a convention, assumed).",
                  "Hydrologic group is derived here (NRCS NEH 630 ch. 7 Table 7-1 on SLC Ksat, water-table depth assumed from the "
                  "drainage class); SLC does not publish one."]})
    print("SLC polygon", pid, hits)
    for cp in comps:
        print(f"  {cp['percent']:3d}% {cp['soil_name']:<12} {cp['drainage_class']:<22} HSG {cp['hydrologic_group']:<4} "
              f"{cp['texture_class_0_100cm']:<16} AWC {cp['awc_mm_per_m']} mm/m (AWHC class {cp['awhc_class_mm']}) OM {cp['om_pct_0_100cm']}%")


if __name__ == "__main__":
    main()
