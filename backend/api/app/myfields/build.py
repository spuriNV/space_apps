"""Location-shaped payload for a user-drawn polygon (same fetchers and engine as app/anyloc, aggregated over the polygon)."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import time

from ..anyloc import bc as BC
from ..anyloc import build as B
from ..anyloc import fetch as F
from . import geom as G


async def _post_layer(c, url, rings, fields):
    import httpx  # noqa: PLC0415
    g = json.dumps({"rings": rings, "spatialReference": {"wkid": 4326}})
    r = await c.post(url + "/query", data={"geometry": g, "geometryType": "esriGeometryPolygon", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
                                           "outFields": fields, "returnGeometry": "false", "resultRecordCount": 100, "f": "json"},
                     timeout=httpx.Timeout(10.0, connect=4.0))
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(str(d["error"])[:150])
    return [f["attributes"] for f in d.get("features", [])]


async def analyse(fid: str, name: str, poly: dict, area_ha: float, power_cache, note: dict | None) -> tuple[dict, dict, list | None, dict]:
    """Returns (location payload, daily {} , strategies items or None, {timings_ms, sections})."""
    parts = G.polys(poly)
    nverts = sum(len(r) - 1 for p in parts for r in p)
    pts, (lon, lat) = G.sample_parts(poly, 25)
    today = dt.date.today().isoformat()
    t0 = time.perf_counter()
    ms, sections = {}, {}
    cw = [list(reversed(r)) for p in parts for r in p]   # ArcGIS: outer rings clockwise, holes counter-clockwise (ours are the opposite)
    in_ca_box = B.CA_BOX[0] <= lon <= B.CA_BOX[2] and B.CA_BOX[1] <= lat <= B.CA_BOX[3]
    if BC.in_bc_box(lon, lat) and not in_ca_box:
        try:
            async with F.client() as c0:
                rd0 = await asyncio.wait_for(BC.regional_district(c0, lon, lat), 8)
        except Exception:  # noqa: BLE001
            rd0 = None
        if isinstance(rd0, str):
            return await analyse_bc(fid, name, poly, area_ha, power_cache, note, rd0)
    from water_sources import AG_WORDS, SWRCB, L as LAYERS  # noqa: PLC0415

    async def timed(k, coro, deadline):
        t = time.perf_counter()
        try:
            return await asyncio.wait_for(coro, deadline)
        finally:
            ms[k] = round((time.perf_counter() - t) * 1000)

    xs = sorted(pts, key=lambda p: p[0]); ys = sorted(pts, key=lambda p: p[1])
    probe = {tuple(p) for p in (xs[0], xs[-1], ys[0], ys[-1])}
    if len(parts) > 1:
        probe |= {tuple(G.sample_grid(p, 1)[1]) for p in parts}
    probe = set(sorted(probe - {(lon, lat)})[:8])
    async with F.client() as c:
        cty, dwr, pw, cdlmeta, board, *others = await asyncio.gather(
            timed("county", F.county(c, lon, lat), 8),
            timed("dwr_fields", _post_layer(c, F.DWR_2023, cw, "UniqueID,ACRES,COUNTY,CLASS1,MAIN_CROP,CROPTYP2") if in_ca_box else B._none(), 12),
            timed("power", power_cache.get(c, lon, lat), 30),
            timed("cdl_catalog", power_cache.cdl_meta(c), 10),
            timed("swrcb", power_cache.swrcb(c, SWRCB) if in_ca_box else B._none(), 8),
            *[timed(f"county_probe{i}", F.county(c, p[0], p[1]), 8) for i, p in enumerate(sorted(probe))],
            return_exceptions=True)
        ca_now = isinstance(cty, dict) and cty["state_fips"] == "06"
        outside_us = cty is None
        no_cdl = outside_us or (isinstance(cty, dict) and cty["state_code"] not in B.CONUS)

        async def span_layers():
            names = {"districts": "AGENCYNAME", "gsa": "GSA_ID,GSA_Name", "b118": "Basin_Subbasin_Number,Basin_Subbasin_Name"}
            res = await asyncio.gather(*(_post_layer(c, LAYERS[k], cw, f) for k, f in names.items()), return_exceptions=True)
            return dict(zip(names, res))

        soil_raw, cdl, wat, spans = await asyncio.gather(
            timed("soil", F.ssurgo(c, None, G.wkt_geom(poly)) if not outside_us else B._none(), 20),
            timed("cdl", B._none() if no_cdl else F.cdl_history(c, pts, cdlmeta[0]) if not isinstance(cdlmeta, Exception) else B._raise(cdlmeta), 20),
            timed("water", F.water(c, lon, lat, LAYERS, AG_WORDS, today) if ca_now else B._none(), 10),
            timed("spans", span_layers() if ca_now else B._none(), 12),
            return_exceptions=True)

    sections["boundary"] = B.sec("ready", source="user_drawn", vertices=nverts, parts=len(parts))
    # county
    if isinstance(cty, dict):
        sections["county"] = B.sec("ready", source="fcc_census_area_2020")
        counties = {cty["county_name"]}
        for o in others:
            if isinstance(o, dict):
                counties.add(o["county_name"])
    else:
        sections["county"] = B.sec("error" if isinstance(cty, Exception) else "unavailable",
                                   f"county lookup failed ({type(cty).__name__})" if isinstance(cty, Exception) else "outside the United States (no county)")
        cty, counties = None, set()
    in_ca = bool(cty and cty["state_fips"] == "06")
    # DWR fields overlapping
    if isinstance(dwr, list):
        dwr_fields = sorted(({"id": a.get("UniqueID"), "crop": a.get("MAIN_CROP") or a.get("CROPTYP2"), "class": a.get("CLASS1"), "acres": a.get("ACRES")} for a in dwr),
                            key=lambda r: -(r["acres"] or 0))
        sections["dwr_fields"] = B.sec("ready", source="dwr_landiq_crop_mapping_2023", count=len(dwr_fields))
    else:
        dwr_fields = []
        sections["dwr_fields"] = (B.sec("error", f"DWR field lookup failed ({type(dwr).__name__})") if isinstance(dwr, Exception)
                                  else B.sec("unavailable", "the DWR/Land IQ field map covers California only"))
    # weather
    df = pmeta = None
    if isinstance(pw, Exception):
        sections["weather"] = B.sec("error", f"NASA POWER did not answer ({type(pw).__name__}: {str(pw)[:120]})")
    else:
        df, pmeta = pw
        sections["weather"] = B.sec("ready", source="nasa_power_daily", range=[pmeta["date_min"], pmeta["date_max"]], at="polygon centroid")
    sections["daily"] = dict(sections["weather"])
    # crop history (majority class per year over the sample points)
    if isinstance(cdl, Exception) or isinstance(cdlmeta, Exception):
        e = cdl if isinstance(cdl, Exception) else cdlmeta
        sections["crop_history"] = B.sec("error", f"Cropland Data Layer did not answer ({type(e).__name__})")
        hist, purity, cdl, legend = {}, {}, {}, {}
    else:
        cdl = cdl or {}
        legend = cdlmeta[1]
        hist, purity = B.crop_history(cdl, legend)
        sections["crop_history"] = (B.sec("ready", source="usda_nass_cdl", years=[min(cdl), max(cdl)], points_sampled=max(v["n"] for v in cdl.values()))
                                    if cdl else B.sec("unavailable", "no Cropland Data Layer here (it covers the lower 48 US states only)"))
    mix = {str(y): [{"crop": legend.get(k, f"CDL class {k}"), "share": round(n / v["n"], 2)}
                    for k, n in sorted(v["counts"].items(), key=lambda kv: -kv[1])[:3]] for y, v in sorted(cdl.items())}
    family, fam_why, cropland = B.family_of(cdl)
    if sections["crop_history"]["status"] == "error":
        fam_why = "crop history unavailable: the forage rotation set (CAF0-CAF3) is shown as a stand-in"
    sections["family"] = B.sec("ready" if cdl else "unavailable", fam_why, family=family, template=B.TEMPLATES[family], cropland=cropland)
    # soil (SDA polygon intersection, area-weighted map units)
    s_src = {"id": "ssurgo_sda", "title": "USDA NRCS SSURGO via Soil Data Access", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "accessed": today, "verified": True}
    engine_soil = None
    if isinstance(soil_raw, dict):
        a, o = soil_raw["awc"], soil_raw["om"]
        soil = {"mukey": soil_raw["mukey"], "muname": soil_raw["muname"] or "", "drainage_class": soil_raw["drainage_class"] or "unknown",
                "hydrologic_group": soil_raw["hydrologic_group"] or "unknown",
                "awc_mm_per_m": (B.sn(a[0], "mm/m", s_src, "0-100 cm weighted awc_r over the polygon: map units weighted by their area inside it, components by comppct", "lookup", a[1], a[2])
                                 if a[0] is not None else B.blocked_sn("mm/m", "SSURGO has no AWC for these map units")),
                "om_pct": (B.sn(o[0], "%", s_src, "0-100 cm weighted om_r over the polygon (area-weighted map units)", "lookup", o[1], o[2]) if o[0] is not None
                           else B.blocked_sn("%", "SSURGO has no organic matter for these map units")),
                "texture_class": soil_raw["texture_class"] or "unknown",
                "source": {"id": "ssurgo_sda", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": True},
                "ec_ds_per_m": soil_raw["ec_ds_per_m"], "dominant_component": soil_raw["dominant_component"],
                "texture_detail": soil_raw["texture_detail"], "map_units": soil_raw["map_units"]}
        sections["soil"] = B.sec("ready", source="ssurgo_sda", map_units=len(soil_raw["map_units"]), method="area-weighted over the polygon")
        engine_soil = {"drainage_class": soil["drainage_class"], "hydrologic_group": soil["hydrologic_group"], "mukey": soil["mukey"], "muname": soil["muname"]}
    else:
        why = (f"Soil Data Access did not answer ({type(soil_raw).__name__})" if isinstance(soil_raw, Exception)
               else "no SSURGO soil survey here (SSURGO covers the United States)")
        soil = {"mukey": "unavailable", "muname": why, "drainage_class": "unknown", "hydrologic_group": "unknown",
                "awc_mm_per_m": B.blocked_sn("mm/m", why), "om_pct": B.blocked_sn("%", why), "texture_class": "unknown",
                "source": {"id": "ssurgo_sda", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": False}}
        sections["soil"] = B.sec("error" if isinstance(soil_raw, Exception) else "unavailable", why)
    # water: centroid lookup + every district / GSA / subbasin the polygon touches
    span = {"counties": sorted(counties), "districts": [], "gsas": [], "subbasins": []}
    if not in_ca:
        w = None
        sections["water"] = (B.sec("unavailable", "water district, SGMA subbasin and GSA layers are California (DWR) only") if sections["county"]["status"] != "error"
                             else B.sec("error", "not looked up: the county/state lookup failed, so it is not known whether the field is in California"))
    elif isinstance(wat, Exception):
        w = None
        sections["water"] = B.sec("error", f"DWR water layers did not answer ({type(wat).__name__})")
    else:
        w = wat
        if isinstance(board, dict):
            short = ((w.get("subbasin") or {}).get("name") or "").split(" - ")[-1].strip().lower()
            st = "not listed (DWR jurisdiction)"
            for k, label in (("probationary", "probationary"), ("under_evaluation", "under evaluation for probation"), ("returned_to_dwr", "returned to DWR")):
                if any(n.lower().removesuffix(" subbasin") == short for n in board.get(k) or []):
                    st = label
            w["state_board"] = {"status": st, "url": SWRCB, "accessed": today, "verified": True}
        else:
            w["state_board"] = None
        if isinstance(spans, dict):
            g = spans.get("gsa")
            d = spans.get("districts")
            b = spans.get("b118")
            if isinstance(d, list):
                span["districts"] = sorted({x["AGENCYNAME"].strip() for x in d if x.get("AGENCYNAME")})
            if isinstance(g, list):
                span["gsas"] = sorted({(x.get("GSA_Name") or "").strip() for x in g if x.get("GSA_Name")})
                w["gsa"] = [{"name": n, "id": next((x.get("GSA_ID") for x in g if (x.get("GSA_Name") or "").strip() == n), None), "url": None, "exclusive": None}
                            for n in span["gsas"]] or w.get("gsa")
            if isinstance(b, list):
                span["subbasins"] = sorted({x["Basin_Subbasin_Name"] for x in b if x.get("Basin_Subbasin_Name")})
            if span["districts"]:
                w["other_agencies"] = [n for n in span["districts"] if n != w.get("district")]
        sections["water"] = B.sec("error" if w.get("errors") and len(w["errors"]) >= 4 else "ready",
                                  ("some DWR layers did not answer: " + ", ".join(w["errors"])) if w.get("errors") else None,
                                  at="centroid; districts, GSAs and subbasins listed over the whole polygon")
    water = B.water_block(w, family)
    # strategies
    items = None
    if df is not None:
        from ..anyloc import engine_bridge  # noqa: PLC0415
        entry = {"id": fid, "name": name, "family": "rice" if family == "rice" else "forage", "template": B.TEMPLATES[family], "region": "ca",
                 "centroid": {"lon": lon, "lat": lat}, "slope_pct": 0.0 if family == "rice" else 0.5}
        t = time.perf_counter()
        try:
            items = B._plain(await asyncio.to_thread(engine_bridge.run, fid, entry, df, lat, pmeta.get("elevation_m"), pmeta["url"], engine_soil))
            for st in items:
                gaps = (st.get("brief") or {}).get("gaps")
                if isinstance(gaps, list):
                    st["brief"]["gaps"] = [{"text": g, "source_ids": []} if isinstance(g, str) else g for g in gaps]
            sections["strategies"] = B.sec("ready", f"{B.TEMPLATES[family][:3].upper()} rotation set ({'rice' if family == 'rice' else 'forage'} family) scored with "
                                                    "NASA POWER weather at the polygon centre" + ("" if engine_soil else "; no soil drainage check"), template=B.TEMPLATES[family])
        except Exception as e:  # noqa: BLE001
            sections["strategies"] = B.sec("error", f"rotation engine failed ({type(e).__name__}: {str(e)[:160]})")
        ms["engine"] = round((time.perf_counter() - t) * 1000)
    else:
        sections["strategies"] = B.sec("error", "needs NASA POWER weather, which did not answer")
        ms["engine"] = None
    sections.update(B.tier2_sections())
    # payload
    row, col, _, _, foot = F.power_cell(lon, lat)
    elev = (pmeta or {}).get("elevation_m")
    p_src = B.src("nasa_power_daily", "NASA POWER daily point", (pmeta or {}).get("url", F.POWER_URL), today)
    area_src = B.src("user_drawn_polygon", "Outline drawn by the user; geodesic area", "urn:fieldshift:user", today, True)
    county_name = cty["county_name"] if cty else None
    place = f"{county_name} County, {cty['state_code']}" if cty else f"{lat:.3f}, {lon:.3f}"
    ds_stat = lambda k: {"status": sections[k]["status"] if sections[k]["status"] != "ready" else "real", **({"reason": sections[k]["reason"]} if sections[k].get("reason") else {})}  # noqa: E731
    top = dwr_fields[0] if dwr_fields else None
    loc = {
        "id": fid, "name": name, "dwr_unique_id": top["id"] if top else None,
        "region_adapter": "ca" if in_ca else "other", "region": "ca" if in_ca else "other", "regime": "not assessed (user-drawn field)",
        "state_fips": cty["state_fips"] if cty else "", "county_fips": cty["county_fips"] if cty else "",
        "geometry": poly, "centroid": {"lon": lon, "lat": lat},
        "area_ha": B.sn(round(area_ha, 2), "ha", area_src, "geodesic area of the drawn polygon", "computed"),
        "crs_working": "EPSG:32610",
        "family": family, "farmer_name": name, "acres": round(area_ha * 2.47105, 1), "county_name": county_name,
        "state_code": cty["state_code"] if cty else None, "template": B.TEMPLATES[family],
        "why_chosen": "You drew this field. " + fam_why[:1].upper() + fam_why[1:] + ".",
        "soil": soil,
        "terrain": {"slope_mean_pct": B.blocked_sn("%", "NASADEM not computed for drawn fields"), "slope_p90_pct": B.blocked_sn("%", "NASADEM not computed for drawn fields"),
                    "elev_m": (B.sn(elev, "m", p_src, "elevation of the POWER (MERRA-2) grid cell, NOT a field DEM value", "lookup") if elev is not None
                               else B.blocked_sn("m", "POWER did not answer")),
                    "low_spot_fraction": B.blocked_sn("fraction", "NASADEM not computed for drawn fields")},
        "water": water, "market_preference": "no_preference", "stations": [],
        "regional_cell": {"grid": "POWER_MERRA2_0.5x0.625", "row": row, "col": col, "footprint": foot},
        "datasets": {"power": {**ds_stat("weather"), **({"range": [pmeta["date_min"], pmeta["date_max"]]} if pmeta else {})},
                     "cdl": ds_stat("crop_history"), "imerg": {"status": "not_computed"}, "smap_l3": {"status": "not_computed"},
                     "smap_l4": {"status": "not_computed"}, "grace": {"status": "not_computed"}, "hls": {"status": "not_computed"},
                     "s2": {"status": "not_computed"}, "modis": {"status": "not_computed"}, "ecostress": {"status": "not_computed"},
                     "dem": {"status": "not_computed"}, "openet": {"status": "unavailable", "reason": "not queried for drawn fields (monthly quota)"},
                     "cimis": {"status": "blocked", "reason": "needs CIMIS appKey"}, "cdec": {"status": "not_computed"},
                     "usdm": {"status": "not_computed"}, "rma": {"status": "not_computed"}, "news": {"status": "not_computed"}},
        "nasa_datasets": ([{"id": "power", "name": "NASA POWER daily weather", "tells_you": "Daily heat, cold, rain and the reference crop water demand (ETo) for your area.",
                            "resolution": "about 50 km (0.5 x 0.625 deg)", "date_range": [pmeta["date_min"], pmeta["date_max"]] if pmeta else None,
                            "rows": pmeta["rows"] if pmeta else 0, "status": "live" if pmeta else "blocked",
                            "used_in": ["daily", "strategies water use", "heat and frost days"], "source_url": "https://power.larc.nasa.gov/"}]
                          + [{"id": i, "name": n, "tells_you": t, "resolution": r, "date_range": None, "rows": 0, "status": "pending",
                              "used_in": [], "source_url": u, "note": B.TIER2_WHY} for i, n, t, r, u in B.NASA_STATIC]),
        "crop_history": hist, "crop_history_purity": purity,
        "dwr_2023": ({"main_crop": top["crop"], "class": top["class"], "acres": top["acres"], "county": None, "largest_of": len(dwr_fields)} if top else None),
        "observed_cover": {"typically_bare_doy_ranges": [], "bare_doy_file": None, "years_used": [],
                           "detector": "not computed for drawn fields (needs the Sentinel-2/Landsat series)"},
        "events": [],
        "user_field": {"name": name, "place": place, "vertices": nverts, "parts": {"count": len(parts), "items": [{"part": i + 1, "area_ha": round(G.part_ha(p), 2), "acres": round(G.part_ha(p) * 2.47105, 1), "holes": len(p) - 1} for i, p in enumerate(parts)]}, "sample_points": len(pts), "spans": span, "dwr_fields": dwr_fields,
                       "crop_mix": mix, "simplified": note,
                       "method": "CDL majority class per year over a grid of up to 25 sample points inside the parts and outside holes (purity = share of points in that class); "
                                 "SSURGO map units weighted by area inside the polygon; POWER at the interior point nearest the centroid"},
        "_notes": {"analysis": "Built live for a user-drawn polygon: NASA POWER (centroid), SSURGO (area-weighted), CDL (sampled), DWR/Land IQ fields overlapping, "
                               "county and DWR water layers. Satellite series, IMERG, SMAP, GRACE, NASADEM and OpenET are not computed (sections.*).",
                   "boundary": "outline drawn by the user", "engine": f"rotation set reused from {B.TEMPLATES[family]} (no new agronomy)"},
    }
    ms["total"] = round((time.perf_counter() - t0) * 1000)
    return loc, {}, items, {"timings_ms": ms, "sections": sections}



# ------------------------------------------------------------------ British Columbia (bannered: BC drawn fields)
async def analyse_bc(fid: str, name: str, poly: dict, area_ha: float, power_cache, note: dict | None, rd: str):
    """BC tier 1 for a drawn polygon: ECCC climate, SLC soil, AAFC crop inventory (sampled), regional district, ALR, BC rotation set."""
    parts = G.polys(poly)
    nverts = sum(len(r) - 1 for p in parts for r in p)
    pts, (lon, lat) = G.sample_parts(poly, 25)
    today = dt.date.today().isoformat()
    t0 = time.perf_counter()
    ms, sections = {}, {}

    async def timed(k, coro, deadline):
        t = time.perf_counter()
        try:
            return await asyncio.wait_for(coro, deadline)
        finally:
            ms[k] = round((time.perf_counter() - t) * 1000)

    async with F.client() as c:
        pw, bcd, aci, alr = await asyncio.gather(
            timed("power", power_cache.get(c, lon, lat), 30),
            timed("bc", B.bc_stage1(c, lon, lat, today), 20),
            timed("aci", BC.aci_history(c, pts), 20),
            timed("alr", BC.alr_clip(c, poly, lon, lat), 20),
            return_exceptions=True)
    bcd = bcd if isinstance(bcd, dict) else {}
    sections["boundary"] = B.sec("ready", source="user_drawn", vertices=nverts, parts=len(parts))
    sections["county"] = B.sec("ready", source="bc_regional_districts_wfs", regional_district=rd)
    df = pmeta = None
    if isinstance(pw, Exception):
        sections["weather"] = B.sec("error", f"NASA POWER did not answer ({type(pw).__name__}: {str(pw)[:120]})")
    else:
        df, pmeta = pw
        sections["weather"] = B.sec("ready", source="nasa_power_daily", range=[pmeta["date_min"], pmeta["date_max"]], at="polygon centroid")
    sections["daily"] = dict(sections["weather"])
    # ECCC climate stations
    stations, eccc_clim = [], None
    ec = bcd.get("eccc")
    if isinstance(ec, dict) and ec["stations"]:
        stations = [{"network": "ECCC", "id": s["id"], "name": s["name"].title().replace(" Cs", " CS"), "distance_km": s["distance_km"],
                     "years": [int(s["daily"][0][:4]), int(s["daily"][1][:4])]} for s in ec["stations"]]
        eccc_clim = {"stations": ec["stations"], "monthly": ec["monthly"],
                     "source": B.src("eccc_climate", "ECCC daily/monthly climate (MSC GeoMet OGC API)", BC.ECCC + "/climate-monthly", today)}
        sections["stations"] = B.sec("ready", source="eccc_geomet", stations=[s["id"] for s in ec["stations"]], climate_summary=bool(ec["monthly"]))
    else:
        sections["stations"] = B.sec("error" if isinstance(ec, Exception) else "unavailable",
                                     f"ECCC station lookup failed ({type(ec).__name__})" if isinstance(ec, Exception) else "no ECCC daily climate station within 80 km")
    # crop history (AAFC ACI majority class per year over the sample points)
    if isinstance(aci, Exception) or not aci:
        sections["crop_history"] = B.sec("error" if isinstance(aci, Exception) else "unavailable",
                                         f"AAFC crop inventory did not answer ({type(aci).__name__})" if isinstance(aci, Exception) else "the AAFC crop inventory does not map this field")
        hist, purity, aci = {}, {}, {}
    else:
        hist, purity = B.crop_history(aci, BC.aci_legend())
        sections["crop_history"] = B.sec("ready", source="aafc_aci", years=[min(aci), max(aci)], points_sampled=max(v["n"] for v in aci.values()))
    legend = BC.aci_legend()
    mix = {str(y): [{"crop": legend.get(k, f"ACI class {k}"), "share": round(n / v["n"], 2)}
                    for k, n in sorted(v["counts"].items(), key=lambda kv: -kv[1])[:3]] for y, v in sorted(aci.items())}
    family, fam_why, cropland = BC.family_bc(aci)
    sections["family"] = B.sec("ready" if aci else "unavailable", fam_why, family=family, template=B.BC_TEMPLATE, cropland=cropland)
    # soil (SLC)
    slc = BC.slc_at(lon, lat)
    if slc:
        soil, engine_soil = B.slc_soil(slc, today)
        sections["soil"] = B.sec("ready", source="aafc_slc_v3_2", poly_id=slc["poly_id"])
    else:
        why = "no Soil Landscapes of Canada soil data for this field (SLC v3.2 has soil tables for BC's farmed landscapes only)"
        soil = {"mukey": "unavailable", "muname": why, "drainage_class": "unknown", "hydrologic_group": "unknown",
                "awc_mm_per_m": B.blocked_sn("mm/m", why), "om_pct": B.blocked_sn("%", why), "texture_class": "unknown",
                "source": {"id": "ssurgo_sda", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": False}}
        sections["soil"] = B.sec("unavailable", why)
        engine_soil = None
    sections["water"] = B.sec("unavailable", "BC water licences and groundwater aquifers are not looked up for drawn fields (the California layers do not apply)")
    water = B.water_block(None, family)
    # ALR + parcel context
    parcel = None
    if isinstance(alr, tuple):
        _g, share = alr
        p = bcd.get("parcel") if isinstance(bcd.get("parcel"), dict) else {}
        parcel = {"parcel_class": p.get("parcel_class"), "owner_type": p.get("owner_type"), "parcel_area_ha": p.get("area_ha"),
                  "alr_share_of_parcel": round(share, 3), "clip": "share of the drawn field inside the Agricultural Land Reserve"}
        sections["alr"] = B.sec("ready", source="bc_alr_wfs", alr_share=round(share, 3))
    else:
        sections["alr"] = B.sec("error", f"ALR lookup failed ({type(alr).__name__})")
    # land status + Nation tools (as anyloc)
    land = BC.land_status_bc(bcd["reserve"]) if isinstance(bcd.get("reserve"), dict) else None
    sections["land_status"] = (B.sec("ready", source="bc_reserves_wfs", kind=land["kind"]) if land else
                               B.sec("error", "reserve / tribal land lookup failed") if isinstance(bcd.get("reserve"), Exception)
                               else B.sec("ready", source="bc_reserves_wfs", kind=None))
    # strategies: BC rotation set
    items = None
    if df is not None:
        from ..anyloc import engine_bridge  # noqa: PLC0415
        entry = B.engine_entry(fid, name, family, "bc", {"lon": lon, "lat": lat})
        t = time.perf_counter()
        try:
            items = B._plain(await asyncio.to_thread(engine_bridge.run, fid, entry, df, lat, pmeta.get("elevation_m"), pmeta["url"], engine_soil))
            for st in items:
                gaps = (st.get("brief") or {}).get("gaps")
                if isinstance(gaps, list):
                    st["brief"]["gaps"] = [{"text": g, "source_ids": []} if isinstance(g, str) else g for g in gaps]
            sections["strategies"] = B.sec("ready", f"BC rotation set (BC0-BC3, {B.BC_TEMPLATE}) scored with NASA POWER weather at the polygon centre"
                                           + ("" if engine_soil else "; no soil drainage check"), template=B.BC_TEMPLATE)
        except Exception as e:  # noqa: BLE001
            sections["strategies"] = B.sec("error", f"rotation engine failed ({type(e).__name__}: {str(e)[:160]})")
        ms["engine"] = round((time.perf_counter() - t) * 1000)
    else:
        sections["strategies"] = B.sec("error", "needs NASA POWER weather, which did not answer")
        ms["engine"] = None
    sections.update(B.tier2_sections())
    row, col, _, _, foot = F.power_cell(lon, lat)
    elev = (pmeta or {}).get("elevation_m")
    p_src = B.src("nasa_power_daily", "NASA POWER daily point", (pmeta or {}).get("url", F.POWER_URL), today)
    area_src = B.src("user_drawn_polygon", "Outline drawn by the user; geodesic area", "urn:fieldshift:user", today, True)
    place = f"{rd}, BC"
    ds_stat = lambda k: {"status": sections[k]["status"] if sections[k]["status"] != "ready" else "real", **({"reason": sections[k]["reason"]} if sections[k].get("reason") else {})}  # noqa: E731
    loc = {
        "id": fid, "name": name, "dwr_unique_id": None,
        "region_adapter": "bc", "region": "bc", "regime": "not assessed (user-drawn field)",
        "state_fips": "", "county_fips": "",
        "geometry": poly, "centroid": {"lon": lon, "lat": lat},
        "area_ha": B.sn(round(area_ha, 2), "ha", area_src, "geodesic area of the drawn polygon", "computed"),
        "crs_working": "EPSG:32610",
        "family": family, "farmer_name": name, "acres": round(area_ha * 2.47105, 1), "county_name": rd, "state_code": "BC",
        "regional_district": rd, "template": B.BC_TEMPLATE,
        "why_chosen": "You drew this field. " + fam_why[:1].upper() + fam_why[1:] + ".",
        "soil": soil,
        "terrain": {"slope_mean_pct": B.blocked_sn("%", "NASADEM not computed for drawn fields"), "slope_p90_pct": B.blocked_sn("%", "NASADEM not computed for drawn fields"),
                    "elev_m": (B.sn(elev, "m", p_src, "elevation of the POWER (MERRA-2) grid cell, NOT a field DEM value", "lookup") if elev is not None
                               else B.blocked_sn("m", "POWER did not answer")),
                    "low_spot_fraction": B.blocked_sn("fraction", "NASADEM not computed for drawn fields")},
        "water": water, "market_preference": "no_preference", "stations": stations,
        "land_status": land, "nation_tools": BC.nation_tools(land, salmon=bcd.get("salmon") is True, water=water),
        "climate_eccc": eccc_clim, "parcel": parcel,
        "regional_cell": {"grid": "POWER_MERRA2_0.5x0.625", "row": row, "col": col, "footprint": foot},
        "datasets": {"power": {**ds_stat("weather"), **({"range": [pmeta["date_min"], pmeta["date_max"]]} if pmeta else {})},
                     "cdl": {"status": "unavailable", "reason": "the Cropland Data Layer is US-only; BC uses the AAFC Annual Crop Inventory (sections.crop_history)"},
                     "imerg": {"status": "not_computed"}, "smap_l3": {"status": "not_computed"},
                     "smap_l4": {"status": "not_computed"}, "grace": {"status": "not_computed"}, "hls": {"status": "not_computed"},
                     "s2": {"status": "not_computed"}, "modis": {"status": "not_computed"}, "ecostress": {"status": "not_computed"},
                     "dem": {"status": "not_computed"}, "openet": {"status": "unavailable", "reason": "not queried for drawn fields (monthly quota)"},
                     "cimis": {"status": "blocked", "reason": "needs CIMIS appKey"}, "cdec": {"status": "not_computed"},
                     "usdm": {"status": "not_computed"}, "rma": {"status": "not_computed"}, "news": {"status": "not_computed"}},
        "nasa_datasets": ([{"id": "power", "name": "NASA POWER daily weather", "tells_you": "Daily heat, cold, rain and the reference crop water demand (ETo) for your area.",
                            "resolution": "about 50 km (0.5 x 0.625 deg)", "date_range": [pmeta["date_min"], pmeta["date_max"]] if pmeta else None,
                            "rows": pmeta["rows"] if pmeta else 0, "status": "live" if pmeta else "blocked",
                            "used_in": ["daily", "strategies water use", "heat and frost days"], "source_url": "https://power.larc.nasa.gov/"}]
                          + [{"id": i, "name": n, "tells_you": t, "resolution": r, "date_range": None, "rows": 0, "status": "pending",
                              "used_in": [], "source_url": u, "note": B.TIER2_WHY} for i, n, t, r, u in B.NASA_STATIC]),
        "crop_history": hist, "crop_history_purity": purity, "dwr_2023": None,
        "observed_cover": {"typically_bare_doy_ranges": [], "bare_doy_file": None, "years_used": [],
                           "detector": "not computed for drawn fields (needs the Sentinel-2/Landsat series)"},
        "events": [],
        "user_field": {"name": name, "place": place, "vertices": nverts, "parts": {"count": len(parts), "items": [{"part": i + 1, "area_ha": round(G.part_ha(p), 2), "acres": round(G.part_ha(p) * 2.47105, 1), "holes": len(p) - 1} for i, p in enumerate(parts)]},
                       "sample_points": len(pts), "spans": {"counties": [], "regional_districts": [rd], "districts": [], "gsas": [], "subbasins": []}, "dwr_fields": [],
                       "crop_mix": mix, "simplified": note,
                       "method": "AAFC Annual Crop Inventory majority class per year over a grid of up to 25 sample points inside the parts and outside holes (purity = share of points in that class); "
                                 "Soil Landscapes of Canada polygon at the interior point; ECCC climate stations nearest the centroid; NASA POWER at the interior point nearest the centroid"},
        "_notes": {"analysis": "Built live for a user-drawn BC polygon: NASA POWER (centroid), ECCC climate stations, AAFC Soil Landscapes of Canada, AAFC Annual Crop Inventory (sampled), "
                               "regional district and Agricultural Land Reserve context. Satellite series, IMERG, SMAP, GRACE, NASADEM and OpenET are not computed (sections.*).",
                   "boundary": "outline drawn by the user", "engine": f"rotation set reused from {B.BC_TEMPLATE} (no new agronomy)"},
    }
    ms["total"] = round((time.perf_counter() - t0) * 1000)
    return loc, {}, items, {"timings_ms": ms, "sections": sections}
