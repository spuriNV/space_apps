"""SSURGO via USDA Soil Data Access for each preset -> data/cache/<id>/soil.json (+ soil.meta.json).
Footprint: backend/field/polygons/<id>.geojson if it exists, else a ~400 m square around the preset centre."""
import math, json, requests
import numpy as np
from shapely.geometry import shape, box, mapping
from common import *

SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"

def sda(sql):
    r = requests.post(SDA, json={"format": "JSON+COLUMNNAME", "query": sql}, timeout=180, headers=UA)
    r.raise_for_status()
    t = r.json().get("Table", [])
    if not t: return []
    cols = t[0]
    return [dict(zip(cols, row)) for row in t[1:]]

def fnum(x):
    return None if x in (None, "") else float(x)

def texture_class(sand, silt, clay):
    """USDA texture triangle (percent)."""
    if clay >= 40 and sand <= 45 and silt < 40: return "clay"
    if clay >= 40 and silt >= 40: return "silty clay"
    if clay >= 35 and sand > 45: return "sandy clay"
    if clay >= 27 and clay < 40 and sand <= 20: return "silty clay loam"
    if clay >= 27 and clay < 40 and sand <= 45: return "clay loam"
    if clay >= 20 and clay < 35 and silt < 28 and sand > 45: return "sandy clay loam"
    if silt >= 80 and clay < 12: return "silt"
    if (silt >= 50 and clay >= 12 and clay < 27) or (silt >= 50 and silt < 80 and clay < 12): return "silt loam"
    if clay >= 7 and clay < 27 and silt >= 28 and silt < 50 and sand <= 52: return "loam"
    if (silt + 1.5 * clay < 15): return "sand"
    if (silt + 1.5 * clay >= 15 and silt + 2 * clay < 30): return "loamy sand"
    return "sandy loam"

def footprint(pid, p):
    f = ROOT / "backend" / "field" / "polygons" / f"{pid}.geojson"
    if f.exists():
        gj = json.loads(f.read_text())
        geoms = [shape(ft["geometry"]) for ft in gj["features"]] if gj.get("type") == "FeatureCollection" else [shape(gj.get("geometry", gj))]
        g = geoms[0]
        for x in geoms[1:]: g = g.union(x)
        return g, f"field polygon {f.relative_to(ROOT)}"
    dlat = 200 / 111320; dlon = 200 / (111320 * math.cos(math.radians(p["lat"])))
    return box(p["lon"] - dlon, p["lat"] - dlat, p["lon"] + dlon, p["lat"] + dlat), "400 m square around preset centre (placeholder until field polygon exists)"

def wavg(h, key, top=0, bot=100):
    num = den = 0.0
    for r in h:
        v = fnum(r[key]); a, b = fnum(r["hzdept_r"]), fnum(r["hzdepb_r"])
        if v is None or a is None or b is None: continue
        t = max(0.0, min(b, bot) - max(a, top))
        num += v * t; den += t
    return (num / den if den else None), den

def main():
    for pid, p in PRESETS.items():
        g, fp_note = footprint(pid, p)
        wkt = g.wkt
        areas = sda(f"SELECT mukey, mupolygongeo.STIntersection(geometry::STGeomFromText('{wkt}',4326)).STArea() AS a FROM mupolygon WHERE mukey IN (SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{wkt}'))")
        share = {}
        for r in areas: share[r["mukey"]] = share.get(r["mukey"], 0) + float(r["a"])
        tot = sum(share.values()); assert tot > 0, "no intersection area"
        share = {k: v / tot for k, v in share.items()}
        mukeys = sorted(share, key=lambda k: -share[k])
        mk = ",".join(mukeys)
        comps = sda(f"SELECT mu.mukey, mu.muname, c.cokey, c.compname, c.comppct_r, c.drainagecl, c.hydgrp, c.taxorder, c.majcompflag FROM mapunit mu JOIN component c ON c.mukey=mu.mukey WHERE mu.mukey IN ({mk}) ORDER BY mu.mukey, c.comppct_r DESC")
        hz = sda(f"SELECT c.cokey, h.chkey, h.hzname, h.hzdept_r, h.hzdepb_r, h.awc_l, h.awc_r, h.awc_h, h.om_l, h.om_r, h.om_h, h.sandtotal_r, h.silttotal_r, h.claytotal_r, h.ec_r, (SELECT TOP 1 g.texture FROM chtexturegrp g WHERE g.chkey=h.chkey AND g.rvindicator='Yes') AS texture FROM chorizon h JOIN component c ON c.cokey=h.cokey WHERE c.mukey IN ({mk}) ORDER BY c.cokey, h.hzdept_r")
        by_co = {}
        for r in hz: by_co.setdefault(r["cokey"], []).append(r)
        # per-component 0-100 cm profile
        comp_prof = {}
        for c in comps:
            h = by_co.get(c["cokey"], [])
            if not h: continue
            prof = {}
            for k, out in [("awc_r", "awc"), ("awc_l", "awc_l"), ("awc_h", "awc_h"), ("om_r", "om"), ("om_l", "om_l"), ("om_h", "om_h"), ("sandtotal_r", "sand"), ("silttotal_r", "silt"), ("claytotal_r", "clay"), ("ec_r", "ec")]:
                prof[out], cov = wavg(h, k)
            # AWC in SDA is cm/cm (fraction); sum over depth -> mm in top 100 cm = awc*1000 mm/m * 1 m
            prof["depth_covered_cm"] = wavg(h, "awc_r")[1]
            top = [r for r in h if fnum(r["hzdept_r"]) is not None and fnum(r["hzdept_r"]) < 30]
            prof["surface_texture"] = top[0]["texture"] if top else None
            comp_prof[c["cokey"]] = prof
        def comp_mean(mukey, key):
            num = den = 0.0
            for c in comps:
                if c["mukey"] != mukey or c["cokey"] not in comp_prof: continue
                v = comp_prof[c["cokey"]].get(key)
                if v is None: continue
                w = float(c["comppct_r"] or 0); num += v * w; den += w
            return num / den if den else None
        def area_mean(key):
            num = den = 0.0
            for m in mukeys:
                v = comp_mean(m, key)
                if v is None: continue
                num += v * share[m]; den += share[m]
            return num / den if den else None
        dom = mukeys[0]
        dcomp = [c for c in comps if c["mukey"] == dom]
        dc = max(dcomp, key=lambda c: float(c["comppct_r"] or 0))
        awc_mm = {k: (None if area_mean(k) is None else round(area_mean(k) * 1000, 1)) for k in ("awc", "awc_l", "awc_h")}
        om = {k: (None if area_mean(k) is None else round(area_mean(k), 2)) for k in ("om", "om_l", "om_h")}
        sand, silt, clay = area_mean("sand"), area_mean("silt"), area_mean("clay")
        for nm, v in [("awc", awc_mm["awc"]), ("om", om["om"])]:
            assert v is not None, f"{pid}: no {nm} in SDA for footprint"
        assert 20 <= awc_mm["awc"] <= 250, f"AWC out of range {awc_mm}"
        assert 0 <= om["om"] <= 30
        src = {"id": "ssurgo_sda", "title": "USDA NRCS SSURGO via Soil Data Access", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "accessed": now()[:10], "verified": True}
        soil = {
            "mukey": dom, "muname": dc["muname"], "drainage_class": dc["drainagecl"], "hydrologic_group": dc["hydgrp"],
            "dominant_component": {"compname": dc["compname"], "comppct_r": dc["comppct_r"], "taxorder": dc["taxorder"]},
            "awc_mm_per_m": {"value": awc_mm["awc"], "unit": "mm/m", "low": awc_mm["awc_l"], "high": awc_mm["awc_h"], "method": "lookup",
                             "source": src, "note": "0-100 cm depth-weighted awc_r (cm/cm x 1000), comppct-weighted, area-weighted over map units; low/high = awc_l/awc_h"},
            "om_pct": {"value": om["om"], "unit": "%", "low": om["om_l"], "high": om["om_h"], "method": "lookup", "source": src, "note": "0-100 cm depth-weighted om_r"},
            "texture_class": (texture_class(sand, silt, clay) if None not in (sand, silt, clay) else None),
            "texture_detail": {"sand_pct": None if sand is None else round(sand, 1), "silt_pct": None if silt is None else round(silt, 1), "clay_pct": None if clay is None else round(clay, 1),
                               "surface_horizon_texture_code": comp_prof.get(dc["cokey"], {}).get("surface_texture"), "method": "USDA triangle on 0-100 cm weighted sand/silt/clay"},
            "ec_ds_per_m": None if area_mean("ec") is None else round(area_mean("ec"), 2),
            "map_units": [{"mukey": m, "muname": next(c["muname"] for c in comps if c["mukey"] == m), "area_share": round(share[m], 3),
                           "components": [{"compname": c["compname"], "comppct_r": c["comppct_r"], "drainage_class": c["drainagecl"], "hydrologic_group": c["hydgrp"], "taxorder": c["taxorder"]} for c in comps if c["mukey"] == m]} for m in mukeys],
            "footprint": fp_note, "source": {"id": "ssurgo_sda", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": True}}
        d = cache_dir(pid)
        write_json(d / "soil.json", soil)
        write_json(d / "soil.meta.json", {"url": SDA, "params": {"format": "JSON+COLUMNNAME", "footprint_wkt": wkt, "depth_cm": [0, 100]}, "fetched_at": now(),
                   "footprint_geojson": mapping(g), "footprint_note": fp_note, "native_res_m": None, "native_res": "SSURGO map-unit polygons (order 2 survey, ~1:24k)",
                   "timestep": "static", "units": {"awc": "mm/m", "om": "percent by weight", "texture": "percent sand/silt/clay"}, "fill_value": "null in SDA", "auth": "none"})
        print(pid, dom, dc["muname"], dc["drainagecl"], dc["hydgrp"], awc_mm, om, soil["texture_class"], {m: round(share[m], 2) for m in mukeys})

if __name__ == "__main__":
    main()
