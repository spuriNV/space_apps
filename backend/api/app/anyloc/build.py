"""Assemble a location-shaped payload (schemas/location.schema.json) for any tapped point, tier 1 only.

Tier 1 (synchronous, a few seconds cold): POWER daily, SSURGO, CDL history, DWR/Land IQ field outline (else a 200 m
square), county, DWR water layers (California), family from CDL, engine strategies with the family's rotation set.
Tier 2 (IMERG, SMAP, GRACE, S2/Landsat/HLS series, NASADEM, OpenET, ...) is not computed for points: those sections carry
status "not_computed" with the reason. OpenET is never called (100 queries a month).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import time

import numpy as np

from . import bc as BC
from . import fetch as F

STATUSES = ("ready", "not_computed", "unavailable", "error")
CA_BOX = (-124.6, 32.4, -114.0, 42.1)   # lon/lat box around California: DWR layers are only queried inside it
RICE = "3"
FORAGE = {"36", "37", "1", "225", "205", "28", "4", "21", "24", "226", "27", "58", "59", "60", "236"}
# Alfalfa, Other Hay, Corn, Dbl WinWht/Corn, Triticale, Oats, Sorghum, Barley, Winter Wheat, Dbl Oats/Corn, Rye,
# Clover/Wildflowers, Sod/Grass Seed, Switchgrass, Dbl WinWht/Sorghum: the registry's forage rule classes (pick_fields.py)
FALLOW = "61"
NON_CROP = {"111", "112", "121", "122", "123", "124", "131", "141", "142", "143", "152", "176", "190", "195", "63", "64", "65", "83", "87", "88", "92"}
TEMPLATES = {"rice": "car_colusa_rice", "forage": "caf_tulare_forage", "other": "caf_tulare_forage"}
BC_TEMPLATE = "bc_salmon_river_forage"   # BC rotation set BC0-BC3 (backend/engine strategies.json), for every BC point
MAX_OUTLINE_HA = 400                      # a BC parcel / ALR piece bigger than this is not used as the field outline
DAILY_FROM = "2015-01-01"
CONUS = {"AL", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI",
         "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
         "UT", "VT", "VA", "WA", "WV", "WI", "WY"}   # the Cropland Data Layer covers the lower 48 states only


def point_id(lat: float, lon: float) -> str:
    """pt_<n|s><|lat| x 1e4>_<e|w><|lon| x 1e4>: stable at 4 decimals (~11 m)."""
    la, lo = round(lat * 1e4), round(lon * 1e4)
    return f"pt_{'n' if la >= 0 else 's'}{abs(la)}_{'e' if lo >= 0 else 'w'}{abs(lo)}"


def parse_id(pid: str) -> tuple[float, float] | None:
    try:
        _, a, b = pid.split("_")
        lat = int(a[1:]) / 1e4 * (1 if a[0] == "n" else -1 if a[0] == "s" else None)
        lon = int(b[1:]) / 1e4 * (1 if b[0] == "e" else -1 if b[0] == "w" else None)
    except (ValueError, TypeError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or point_id(lat, lon) != pid:
        return None
    return lat, lon


def sec(status, reason=None, **kw):
    assert status in STATUSES
    return {"status": status, **({"reason": reason} if reason else {}), **kw}


def blocked_sn(unit, why):
    return {"value": None, "unit": unit, "low": None, "high": None, "method": "assumed", "note": why}


def sn(v, unit, source, note, method="computed", low=None, high=None):
    return {"value": v, "unit": unit, "low": low, "high": high, "method": method, "source": source, "note": note}


def src(sid, title, url, today, verified=True):
    return {"id": sid, "title": title, "url": url, "accessed": today, "verified": verified}


def engine_entry(pid: str, name: str, family: str, region: str, centroid: dict) -> dict:
    """Virtual registry entry for engine_bridge: rice -> CAR0-3, forage/other -> CAF0-3 in California; BC points reuse the BC
    field's rotation set (BC0-BC3) and its region post-pass (rotation_engine/bc.py)."""
    if region == "bc":
        na = {}
        try:
            import fieldreg  # noqa: PLC0415
            na = dict(fieldreg.get(BC_TEMPLATE).get("not_available") or {})
        except Exception:  # noqa: BLE001
            pass
        na["cimis"] = "CIMIS is California's station network; in BC the nearest ECCC climate stations are listed instead."
        return {"id": pid, "name": name, "family": "forage", "template": BC_TEMPLATE, "region": "bc", "centroid": centroid,
                "slope_pct": 1.0, "not_available": na}
    return {"id": pid, "name": name, "family": "rice" if family == "rice" else "forage", "template": TEMPLATES[family],
            "region": "ca", "centroid": centroid, "slope_pct": 0.0 if family == "rice" else 0.5}


async def bc_stage1(c, lon, lat, today):
    """Regional district (also the 'is it BC' test), reserve, parcel, ECCC stations and the Salmon watershed test, in parallel."""
    names = ("rd", "reserve", "parcel", "eccc", "salmon", "place")
    res = await asyncio.gather(BC.regional_district(c, lon, lat), BC.reserve_at(c, lon, lat), BC.parcel_at(c, lon, lat),
                               BC.eccc(c, lon, lat, dt.date.fromisoformat(today)), BC.salmon_watershed(c, lon, lat),
                               asyncio.wait_for(BC.canada_place(c, lon, lat), 6), return_exceptions=True)  # place is optional in BC: never let it eat the stage deadline
    return dict(zip(names, res))


async def can_stage1(c, lon, lat, today):
    """Canada outside BC: ECCC stations and the nearest named place / province (no BC WFS layers)."""
    res = await asyncio.gather(BC.eccc(c, lon, lat, dt.date.fromisoformat(today)), asyncio.wait_for(BC.canada_place(c, lon, lat), 15), return_exceptions=True)
    return {"rd": None, "eccc": res[0], "place": res[1]}


async def bc_boundary(c, parcel, lon, lat):
    """(geometry, info) from the ParcelMap BC parcel clipped to the ALR; (None, why) when there is no usable outline."""
    if not isinstance(parcel, dict):
        return None, {"why": "no ParcelMap BC parcel at this spot" if parcel is None else f"ParcelMap BC did not answer ({type(parcel).__name__})"}
    geom, share = await BC.alr_clip(c, parcel["geometry"], lon, lat)
    info = {"parcel_class": parcel["parcel_class"], "owner_type": parcel["owner_type"], "parcel_area_ha": parcel["area_ha"],
            "alr_share_of_parcel": round(share, 3), "municipality": parcel["municipality"]}
    if geom is not None:
        ring = geom["coordinates"][0]
        if F.ring_area_m2(ring) / 1e4 <= MAX_OUTLINE_HA:
            return {"type": "Polygon", "coordinates": [ring]}, {**info, "clip": "parcel inside the Agricultural Land Reserve"}
    g = parcel["geometry"]
    ring = next((r for r in F.rings_of(g) if F.in_ring(lon, lat, r)), F.rings_of(g)[0])
    if F.ring_area_m2(ring) / 1e4 <= MAX_OUTLINE_HA:
        return {"type": "Polygon", "coordinates": [ring]}, {**info, "clip": "whole parcel (not in the ALR)" if share == 0 else
                                                           "whole parcel (its ALR part did not contain the spot)"}
    return None, {**info, "why": f"the parcel here is {parcel['area_ha']:.0f} ha (not a single field)"}


# ------------------------------------------------------------------ family from CDL
def crop_history(cdl: dict, legend: dict) -> tuple[dict, dict]:
    """({year: majority class name}, {year: purity}) over the sampled points."""
    hist, purity = {}, {}
    for y in sorted(cdl):
        cnt = cdl[y]["counts"]
        code = max(cnt, key=cnt.get)
        hist[str(y)] = legend.get(code, f"CDL class {code}")
        purity[str(y)] = round(cnt[code] / cdl[y]["n"], 2)
    return hist, purity


def family_of(cdl: dict) -> tuple[str, str, bool]:
    """('rice'|'forage'|'other', plain-language why, is_cropland) from the last 10 CDL years at the field."""
    years = sorted(cdl)[-10:]
    if not years:
        return "other", "no Cropland Data Layer here (outside the lower 48 states): the forage rotation set is used as a stand-in", False
    maj = {y: max(cdl[y]["counts"], key=cdl[y]["counts"].get) for y in years}
    n_rice = sum(c == RICE for c in maj.values())
    n_alf = sum(c == "36" for c in maj.values())
    n_for = sum(c in FORAGE for c in maj.values())
    n_crop = sum(c not in NON_CROP for c in maj.values())
    span = f"{years[0]}-{years[-1]}"
    if n_rice >= 3:
        return "rice", f"CDL shows rice in {n_rice} of the {len(years)} years {span}", True
    if n_alf >= 2 or n_for >= 5:
        return "forage", f"CDL shows alfalfa in {n_alf} and forage crops in {n_for} of the {len(years)} years {span}", True
    if n_crop < len(years) / 2:
        return "other", (f"CDL shows cropland in only {n_crop} of the {len(years)} years {span} (not a farm field?): the forage "
                         "rotation set is shown as a stand-in"), False
    return "other", (f"CDL shows neither rice nor mostly forage {span}: the forage rotation set (CAF0-CAF3) is shown as the "
                     "closest stand-in, not a plan for this crop"), True


# ------------------------------------------------------------------ daily (POWER) rows, same keys as the preset /daily
def hargreaves(tmax, tmin, lat, doy):
    from rotation_engine.weather import hargreaves_eto  # noqa: PLC0415
    return hargreaves_eto(tmax, tmin, lat, doy)


def daily_rows(df, lat: float) -> list[dict]:
    d = df.loc[DAILY_FROM:]
    tx, tn, p = (d[c].to_numpy(dtype="float64") for c in ("T2M_MAX", "T2M_MIN", "PRECTOTCORR"))
    doy = d.index.dayofyear.to_numpy()
    eto = hargreaves(tx, tn, lat, doy)
    heat = tx >= 35
    run = np.zeros(len(heat), dtype=bool)
    i = 0
    while i < len(heat):      # heatwave_day: inside a run of >= 3 consecutive days with Tmax >= 35 C (backend/regional derive.py)
        if heat[i]:
            j = i
            while j + 1 < len(heat) and heat[j + 1]:
                j += 1
            if j - i + 1 >= 3:
                run[i:j + 1] = True
            i = j + 1
        else:
            i += 1
    r = lambda v, n=2: None if v != v else round(float(v), n)  # noqa: E731
    return [{"date": ix.strftime("%Y-%m-%d"), "tmax_c": r(tx[k]), "tmin_c": r(tn[k]), "precip_mm": r(p[k]), "eto_mm": r(eto[k]),
             "ndvi": None, "cover_class": "unknown", "cover_source": None, "power_run": None, "imerg_precip_mm": None, "imerg_run": None,
             "smap_sm_pct": None, "smap_rootzone_m3m3": None, "smap_l3_sm_m3m3": None, "grace_gw_pct": None,
             "ncei_tmax_c": None, "ncei_tmin_c": None, "ncei_precip_mm": None,
             "heatwave_day": bool(run[k]), "severe_heat_40c": bool(tx[k] >= 40)} for k, ix in enumerate(d.index)]


def daily_payload(pid, df, lat, pmeta, today):
    rows = daily_rows(df, lat)
    return {"location_id": pid, "from": rows[0]["date"] if rows else None, "to": rows[-1]["date"] if rows else None,
            "sources": {"power": src("nasa_power", "NASA POWER daily point (MERRA-2 cell), AG community", pmeta["url"], today),
                        "eto": src("hargreaves_fao56_eq52", "Hargreaves ETo (FAO-56 eq. 52) on POWER Tmax/Tmin", "https://www.fao.org/3/x0490e/x0490e07.htm", today)},
            "notes": ["Analysed point: only NASA POWER columns are filled (tmax/tmin/precip, Hargreaves ETo, heat flags). "
                      "IMERG, SMAP, GRACE, satellite cover and NOAA station columns are not computed for tapped points (null).",
                      "POWER Tmax runs warm vs stations in summer in the Central Valley; heat flags inherit that bias."],
            "rows": rows}


# ------------------------------------------------------------------ the location payload
NASA_STATIC = [
    ("imerg", "GPM IMERG rainfall", "How much rain fell on your field each day, from NASA's satellite rain estimate.", "about 10 km (0.1 deg), daily", "https://doi.org/10.5067/GPM/IMERGDF/DAY/07"),
    ("smap_l4", "SMAP soil moisture (L4, root zone)", "How wet the soil is down to about 1 m compared with normal for this time of year.", "9 km, daily", "https://nsidc.org/data/spl4smgp/versions/8"),
    ("grace", "GRACE-FO groundwater", "Whether groundwater under your area is higher or lower than usual (percentile).", "about 25 km (0.25 deg), weekly", "https://doi.org/10.5067/8DNK2ZU3U1RO"),
    ("hls", "HLS (Harmonized Landsat Sentinel-2)", "What is growing on the field and when it is bare, green or flooded, every 2-3 days.", "30 m, every 2-3 days", "https://doi.org/10.5067/HLS/HLSS30.002"),
    ("nasadem", "NASADEM elevation", "Slope and low spots on and around the field.", "30 m, one-time (2000 radar)", "https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001"),
]
TIER2_WHY = "not computed for tapped points yet (needs a per-field satellite or Earthdata download that takes minutes); open a preset field to see it"


def tier2_sections():
    s = {k: sec("not_computed", TIER2_WHY) for k in ("imerg", "smap", "grace", "satellite_cover", "terrain")}
    s["openet"] = sec("unavailable", "OpenET is not queried for tapped points (100 queries a month account limit)")
    for k in ("calendar", "zones", "grid", "insurance", "outlook", "stress", "news", "models", "transitions", "water_seen", "nasa_series"):
        s[k] = sec("not_computed", "built per preset field by the offline pipeline; not available for tapped points")
    return s


async def analyse(lat: float, lon: float, power_cache, outline: dict | None = None) -> tuple[dict, dict, list | None, dict]:
    """Returns (location payload, daily payload or {}, strategies items or None, timings ms)."""
    pid = point_id(lat, lon)
    lat, lon = parse_id(pid)
    today = dt.date.today().isoformat()
    t0 = time.perf_counter()
    ms = {}
    sections: dict[str, dict] = {}
    in_ca_box = CA_BOX[0] <= lon <= CA_BOX[2] and CA_BOX[1] <= lat <= CA_BOX[3]
    bc_box = BC.in_bc_box(lon, lat) and not in_ca_box
    can_box = BC.in_canada_box(lon, lat) and not in_ca_box
    from water_sources import AG_WORDS, SWRCB, L as LAYERS  # noqa: PLC0415  (backend/fields/water_sources.py)

    async def timed(name, coro, deadline):
        t = time.perf_counter()
        try:
            return await asyncio.wait_for(coro, deadline)
        finally:
            ms[name] = round((time.perf_counter() - t) * 1000)

    async with F.client() as c:
        # stage 1: independent lookups at the tapped point
        st1 = await asyncio.gather(
            timed("county", F.county(c, lon, lat), 8),
            timed("boundary", F.dwr_field(c, lon, lat) if in_ca_box else _none(), 10),
            timed("power", power_cache.get(c, lon, lat), 30),
            timed("cdl_catalog", power_cache.cdl_meta(c), 10),
            timed("swrcb", power_cache.swrcb(c, SWRCB) if in_ca_box else _none(), 8),
            timed("bc", bc_stage1(c, lon, lat, today) if bc_box else can_stage1(c, lon, lat, today) if can_box else _none(), 20),
            timed("tribal", BC.tribal_at(c, lon, lat) if in_ca_box else _none(), 8),
            return_exceptions=True)
        cty, dwr, pw, cdlmeta, board, bcd, tribal = st1
        ca_now = isinstance(cty, dict) and cty["state_fips"] == "06"
        bcd = bcd if isinstance(bcd, dict) else {}
        in_bc = cty is None and isinstance(bcd.get("rd"), str)
        in_can = cty is None and (in_bc or (can_box and isinstance(bcd.get("place"), dict)))
        cplace = bcd.get("place") if isinstance(bcd.get("place"), dict) else {}
        bc_info = {}
        if in_bc:
            try:
                bgeom, bc_info = await timed("bc_boundary", bc_boundary(c, bcd.get("parcel"), lon, lat), 15)
            except Exception as e:  # noqa: BLE001
                bgeom, bc_info = None, {"why": f"ParcelMap BC / ALR lookup failed ({type(e).__name__})", "error": True}
        # boundary
        if in_bc and bgeom is not None:
            geom = bgeom
            ring, props = geom["coordinates"][0], {}
            sections["boundary"] = sec("ready", source="parcelmap_bc_x_alr", **{k: v for k, v in bc_info.items() if k != "why"})
        elif in_bc:
            geom = F.square(lon, lat, 100)
            ring, props = geom["coordinates"][0], {}
            sections["boundary"] = sec("error" if bc_info.get("error") else "unavailable",
                                       bc_info.get("why", "no parcel outline") + ": a 200 m square around the tap is used", fallback="square_200m")
        elif outline is not None and not isinstance(dwr, dict):
            geom = outline
            ring, props = geom["coordinates"][0], {}
            sections["boundary"] = sec("ready", source="catalog_outline", note="field polygon from the catalog selection source "
                                       "(USDA Crop Sequence Boundaries / AAFC Annual Crop Inventory patch)")
        elif isinstance(dwr, dict):
            ring = next((r for r in F.rings_of(dwr["geometry"]) if F.in_ring(lon, lat, r)), F.rings_of(dwr["geometry"])[0])
            geom = {"type": "Polygon", "coordinates": [ring]}
            props = dwr.get("properties") or {}
            sections["boundary"] = sec("ready", source="dwr_landiq_crop_mapping_2023", dwr_unique_id=props.get("UniqueID"))
        else:
            geom = F.square(lon, lat, 100)
            ring, props = geom["coordinates"][0], {}
            why = ("no DWR/Land IQ 2023 crop-mapped field at this spot (not farmland in 2023, or a road/yard): a 200 m square "
                   "around the tap is used" if dwr is None and in_ca_box else
                   f"DWR field lookup failed ({type(dwr).__name__}): a 200 m square around the tap is used" if isinstance(dwr, Exception) else
                   "outside California (the DWR/Land IQ field map covers California only): a 200 m square around the tap is used")
            sections["boundary"] = sec("unavailable" if not isinstance(dwr, Exception) else "error", why, fallback="square_200m")
        cen = F.ring_centroid(ring)
        area_ha = F.ring_area_m2(ring) / 1e4
        # stage 2: soil + CDL inside the footprint
        outside_us = cty is None                         # FCC answered: no US census block here
        no_cdl = outside_us or (isinstance(cty, dict) and cty["state_code"] not in CONUS)
        st2 = await asyncio.gather(
            timed("soil", F.ssurgo(c, ring) if not outside_us else _none(), 15),
            timed("cdl", _none() if no_cdl else F.cdl_history(c, F.sample_points(ring, lon, lat), cdlmeta[0]) if not isinstance(cdlmeta, Exception) else _raise(cdlmeta), 15),
            timed("water", F.water(c, lon, lat, LAYERS, AG_WORDS, today) if ca_now else _none(), 10),
            timed("aci", BC.aci_history(c, F.sample_points(ring, lon, lat)) if in_can else _none(), 15),
            return_exceptions=True)
        soil_raw, cdl, wat, aci = st2

    # county / region
    if isinstance(cty, dict):
        sections["county"] = sec("ready", source="fcc_census_area_2020")
    elif in_bc:
        sections["county"] = sec("ready", source="bc_regional_districts_wfs", regional_district=bcd["rd"])
        cty = None
    elif in_can:
        sections["county"] = sec("ready", source="cgndb_geonames", place=cplace.get("name"), province=cplace.get("province"))
        cty = None
    else:
        sections["county"] = sec("error" if isinstance(cty, Exception) else "unavailable",
                                 f"county lookup failed ({type(cty).__name__})" if isinstance(cty, Exception) else "outside the United States (no county)")
        cty = None
    in_ca = bool(cty and cty["state_fips"] == "06")
    region = "ca" if in_ca else "bc" if in_bc else "other"

    # weather
    df = pmeta = None
    if isinstance(pw, Exception):
        sections["weather"] = sec("error", f"NASA POWER did not answer ({type(pw).__name__}: {str(pw)[:120]})")
    else:
        df, pmeta = pw
        sections["weather"] = sec("ready", source="nasa_power_daily", range=[pmeta["date_min"], pmeta["date_max"]])
    sections["daily"] = dict(sections["weather"])
    stations, eccc_clim = [], None
    if in_can:
        ec = bcd.get("eccc")
        if isinstance(ec, dict) and ec["stations"]:
            stations = [{"network": "ECCC", "id": s["id"], "name": s["name"].title().replace(" Cs", " CS"), "distance_km": s["distance_km"],
                         "years": [int(s["daily"][0][:4]), int(s["daily"][1][:4])]} for s in ec["stations"]]
            eccc_clim = {"stations": ec["stations"], "monthly": ec["monthly"],
                         "source": src("eccc_climate", "ECCC daily/monthly climate (MSC GeoMet OGC API)", BC.ECCC + "/climate-monthly", today)}
            sections["stations"] = sec("ready", source="eccc_geomet", stations=[s["id"] for s in ec["stations"]],
                                       climate_summary=bool(ec["monthly"]))
        else:
            sections["stations"] = sec("error" if isinstance(ec, Exception) else "unavailable",
                                       f"ECCC station lookup failed ({type(ec).__name__})" if isinstance(ec, Exception) else
                                       "no ECCC daily climate station within 80 km")
    else:
        sections["stations"] = sec("not_computed", "station series (NOAA, CIMIS) are built per preset field; tapped California points use NASA POWER")

    # crop history + family
    if in_can:
        if isinstance(aci, Exception) or not aci:
            sections["crop_history"] = sec("error" if isinstance(aci, Exception) else "unavailable",
                                           f"AAFC crop inventory did not answer ({type(aci).__name__})" if isinstance(aci, Exception) else
                                           "the AAFC crop inventory does not map this spot")
            hist, purity, aci = {}, {}, {}
        else:
            hist, purity = crop_history(aci, BC.aci_legend())
            sections["crop_history"] = sec("ready", source="aafc_aci", years=[min(aci), max(aci)], points_sampled=max(v["n"] for v in aci.values()))
        family, fam_why, cropland = BC.family_bc(aci)
        cdl = aci
    elif isinstance(cdl, Exception) or isinstance(cdlmeta, Exception):
        e = cdl if isinstance(cdl, Exception) else cdlmeta
        sections["crop_history"] = sec("error", f"Cropland Data Layer did not answer ({type(e).__name__})")
        hist, purity, cdl = {}, {}, {}
    else:
        cdl = cdl or {}
        hist, purity = crop_history(cdl, cdlmeta[1])
        sections["crop_history"] = (sec("ready", source="usda_nass_cdl", years=[min(cdl), max(cdl)], points_sampled=max(v["n"] for v in cdl.values()) if cdl else 0)
                                    if cdl else sec("unavailable", "no Cropland Data Layer here (it covers the lower 48 US states only)"))
    if not in_can:
        family, fam_why, cropland = family_of(cdl)
    if sections["crop_history"]["status"] == "error" and not in_can:
        fam_why = "crop history unavailable: the forage rotation set (CAF0-CAF3) is shown as a stand-in"
    tpl = BC_TEMPLATE if in_can else TEMPLATES[family]
    sections["family"] = sec("ready" if cdl else "unavailable", fam_why, family=family, template=tpl, cropland=cropland)

    # soil
    slc = BC.slc_at(lon, lat) if in_can else None
    s_src = {"id": "ssurgo_sda", "title": "USDA NRCS SSURGO via Soil Data Access", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "accessed": today, "verified": True}
    if slc:
        soil, engine_soil = slc_soil(slc, today)
        sections["soil"] = sec("ready", source="aafc_slc_v3_2", poly_id=slc["poly_id"])
    elif isinstance(soil_raw, dict):
        a, o = soil_raw["awc"], soil_raw["om"]
        soil = {"mukey": soil_raw["mukey"], "muname": soil_raw["muname"] or "", "drainage_class": soil_raw["drainage_class"] or "unknown",
                "hydrologic_group": soil_raw["hydrologic_group"] or "unknown",
                "awc_mm_per_m": (sn(a[0], "mm/m", s_src, "0-100 cm depth-weighted awc_r (cm/cm x 1000), comppct- and area-weighted; low/high = awc_l/awc_h", "lookup", a[1], a[2])
                                 if a[0] is not None else blocked_sn("mm/m", "SSURGO has no AWC for these map units")),
                "om_pct": (sn(o[0], "%", s_src, "0-100 cm depth-weighted om_r", "lookup", o[1], o[2]) if o[0] is not None else blocked_sn("%", "SSURGO has no organic matter for these map units")),
                "texture_class": soil_raw["texture_class"] or "unknown",
                "source": {"id": "ssurgo_sda", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": True},
                "ec_ds_per_m": soil_raw["ec_ds_per_m"], "dominant_component": soil_raw["dominant_component"],
                "texture_detail": soil_raw["texture_detail"], "map_units": soil_raw["map_units"]}
        sections["soil"] = sec("ready", source="ssurgo_sda")
        engine_soil = {"drainage_class": soil["drainage_class"], "hydrologic_group": soil["hydrologic_group"], "mukey": soil["mukey"], "muname": soil["muname"]}
    else:
        why = (f"Soil Data Access did not answer ({type(soil_raw).__name__})" if isinstance(soil_raw, Exception)
               else "no Soil Landscapes of Canada soil data for this spot (SLC v3.2 has soil tables for farmed landscapes only)" if in_can
               else "no SSURGO soil survey here (SSURGO covers the United States)")
        soil = {"mukey": "unavailable", "muname": why, "drainage_class": "unknown", "hydrologic_group": "unknown",
                "awc_mm_per_m": blocked_sn("mm/m", why), "om_pct": blocked_sn("%", why), "texture_class": "unknown",
                "source": {"id": "ssurgo_sda", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": False}}
        sections["soil"] = sec("error" if isinstance(soil_raw, Exception) else "unavailable", why)
        engine_soil = None

    # water (California only)
    if in_can:
        w = None
        sections["water"] = sec("unavailable", "Canadian water licences and groundwater aquifers are not looked up for tapped points "
                                               "(the California SGMA / district layers do not apply)")
    elif not in_ca:
        w = None
        sections["water"] = (sec("unavailable", "water district, SGMA subbasin and GSA layers are California (DWR) only") if sections["county"]["status"] != "error"
                             else sec("error", "not looked up: the county/state lookup failed, so it is not known whether the spot is in California"))
    elif isinstance(wat, Exception):
        w = None
        sections["water"] = sec("error", f"DWR water layers did not answer ({type(wat).__name__})")
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
        sections["water"] = sec("error" if w.get("errors") and len(w["errors"]) >= 4 else "ready",
                                ("some DWR layers did not answer: " + ", ".join(w["errors"])) if w.get("errors") else None)
    water = water_block(w, family)

    # strategies (engine)
    items, eng_ms = None, None
    if df is not None:
        from . import engine_bridge  # noqa: PLC0415
        entry = engine_entry(pid, f"Point {lat:.4f}, {lon:.4f}", family, "bc" if in_can else region, {"lon": cen[0], "lat": cen[1]})
        t = time.perf_counter()
        try:
            items = await asyncio.to_thread(engine_bridge.run, pid, entry, df, lat, pmeta.get("elevation_m"), pmeta["url"], engine_soil)
            items = _plain(items)
            for st in items:   # schema wants brief.gaps as {text, source_ids} (main.py normalize_strategy)
                gaps = (st.get("brief") or {}).get("gaps")
                if isinstance(gaps, list):
                    st["brief"]["gaps"] = [{"text": g, "source_ids": []} if isinstance(g, str) else g for g in gaps]
            sections["strategies"] = sec("ready", (f"BC rotation set (BC0-BC3, {BC_TEMPLATE}; the only Canadian set, a stand-in outside BC)" if in_can else
                                                   f"{TEMPLATES[family][:3].upper()} rotation set ({'rice' if family == 'rice' else 'forage'} family)")
                                         + " scored with this spot's NASA POWER weather" + ("" if engine_soil else "; no soil drainage check"),
                                         template=tpl)
        except Exception as e:  # noqa: BLE001
            sections["strategies"] = sec("error", f"rotation engine failed for this point ({type(e).__name__}: {str(e)[:160]})")
        eng_ms = round((time.perf_counter() - t) * 1000)
    else:
        sections["strategies"] = sec("error", "needs NASA POWER weather, which did not answer")
    ms["engine"] = eng_ms
    sections.update(tier2_sections())

    # payload
    row, col, _, _, foot = F.power_cell(lon, lat)
    elev = (pmeta or {}).get("elevation_m")
    p_src = src("nasa_power_daily", "NASA POWER daily point", (pmeta or {}).get("url", F.POWER_URL), today)
    has_outline = bool(props) or sections["boundary"]["status"] == "ready"
    area_src = (src("dwr_landiq_crop_mapping_2023", "DWR Statewide Crop Mapping 2023 (Land IQ), final", F.DWR_2023, today)
                if props else src("fieldshift_square", "200 m square around the tapped point (no field outline)", "urn:fieldshift:assumed", today, False))
    crop_now = props.get("MAIN_CROP") or props.get("CROPTYP2")
    county_name = cty["county_name"] if cty else bcd.get("rd") if in_bc else cplace.get("province_name") if in_can else None
    prov_code = "BC" if in_bc else cplace.get("province") if in_can else None
    place = (f"{county_name} County, {cty['state_code']}" if cty else f"{county_name}, BC" if in_bc else
             f"{cplace['name']}, {prov_code}" if in_can and cplace.get("name") and prov_code else f"{lat:.3f}, {lon:.3f}")
    fam_word = {"rice": "Rice", "forage": "Forage"}.get(family, "Field")
    if in_bc:
        area_src = (src("parcelmap_bc_x_alr", "ParcelMap BC parcel (open parcel fabric) clipped to the Agricultural Land Reserve; "
                        "parcel id and owner not stored", BC.WFS, today) if sections["boundary"]["status"] == "ready" else area_src)
    # land status + Nation tools
    land = None
    if in_bc and isinstance(bcd.get("reserve"), dict):
        land = BC.land_status_bc(bcd["reserve"])
    elif isinstance(tribal, dict):
        land = BC.land_status_us(tribal)
    sections["land_status"] = (sec("ready", source="bc_reserves_wfs" if in_bc else "census_aiannh", kind=land["kind"]) if land else
                               sec("error", "reserve / tribal land lookup failed") if (in_bc and isinstance(bcd.get("reserve"), Exception)) or isinstance(tribal, Exception)
                               else sec("ready", source="bc_reserves_wfs" if in_bc else "census_aiannh", kind=None) if (in_bc or in_ca_box)
                               else sec("not_computed", "reserve / tribal land is looked up in BC and California only"))
    ds_stat = lambda k: {"status": sections[k]["status"] if sections[k]["status"] != "ready" else "real", **({"reason": sections[k]["reason"]} if sections[k].get("reason") else {})}  # noqa: E731
    loc = {
        "id": pid, "name": f"Tapped spot {lat:.4f}, {lon:.4f}", "dwr_unique_id": props.get("UniqueID"),
        "region_adapter": "ca" if in_ca else "bc" if in_bc else "other", "region": region, "regime": "not assessed (tapped point)",
        "state_fips": cty["state_fips"] if cty else "", "county_fips": cty["county_fips"] if cty else "",
        "geometry": geom, "centroid": {"lon": round(cen[0], 6), "lat": round(cen[1], 6)},
        "area_ha": sn(round(area_ha, 2), "ha", area_src, "polygon area (local equirectangular projection)" + ("" if has_outline else "; placeholder square, not a field"), "computed" if has_outline else "assumed"),
        "crs_working": "EPSG:32610",
        "family": family, "farmer_name": f"{fam_word} spot in {place}" if (cty or in_can) else f"Spot at {place}",
        "acres": round(area_ha * 2.47105, 1), "county_name": county_name, "state_code": cty["state_code"] if cty else prov_code if in_can else None,
        "regional_district": bcd.get("rd") if in_bc else None,
        "template": tpl, "why_chosen": "You tapped this spot on the map. " + fam_why[:1].upper() + fam_why[1:] + ".",
        "soil": soil,
        "terrain": {"slope_mean_pct": blocked_sn("%", "NASADEM not computed for tapped points"),
                    "slope_p90_pct": blocked_sn("%", "NASADEM not computed for tapped points"),
                    "elev_m": (sn(elev, "m", p_src, "elevation of the POWER (MERRA-2) grid cell, NOT a field DEM value", "lookup") if elev is not None
                               else blocked_sn("m", "POWER did not answer")),
                    "low_spot_fraction": blocked_sn("fraction", "NASADEM not computed for tapped points")},
        "water": water, "market_preference": "no_preference", "stations": stations,
        "land_status": land,
        "nation_tools": BC.nation_tools(land, salmon=bcd.get("salmon") is True, water=water),
        "climate_eccc": eccc_clim,
        "parcel": ({k: bc_info.get(k) for k in ("parcel_class", "owner_type", "parcel_area_ha", "alr_share_of_parcel", "clip")}
                   if in_bc and sections["boundary"]["status"] == "ready" else None),
        "regional_cell": {"grid": "POWER_MERRA2_0.5x0.625", "row": row, "col": col, "footprint": foot},
        "datasets": {"power": {**ds_stat("weather"), **({"range": [pmeta["date_min"], pmeta["date_max"]]} if pmeta else {})},
                     "cdl": ds_stat("crop_history") if not in_can else {"status": "unavailable", "reason": "the Cropland Data Layer is US-only; Canada uses the AAFC Annual Crop Inventory (sections.crop_history)"}, "imerg": {"status": "not_computed"}, "smap_l3": {"status": "not_computed"},
                     "smap_l4": {"status": "not_computed"}, "grace": {"status": "not_computed"}, "hls": {"status": "not_computed"},
                     "s2": {"status": "not_computed"}, "modis": {"status": "not_computed"}, "ecostress": {"status": "not_computed"},
                     "dem": {"status": "not_computed"}, "openet": {"status": "unavailable", "reason": "not queried for tapped points (monthly quota)"},
                     "cimis": {"status": "blocked", "reason": "needs CIMIS appKey"}, "cdec": {"status": "not_computed"},
                     "usdm": {"status": "not_computed"}, "rma": {"status": "not_computed"}, "news": {"status": "not_computed"}},
        "nasa_datasets": ([{"id": "power", "name": "NASA POWER daily weather", "tells_you": "Daily heat, cold, rain and the reference crop water demand (ETo) for your area.",
                            "resolution": "about 50 km (0.5 x 0.625 deg)", "date_range": [pmeta["date_min"], pmeta["date_max"]] if pmeta else None,
                            "rows": pmeta["rows"] if pmeta else 0, "status": "live" if pmeta else "blocked",
                            "used_in": ["daily", "strategies water use", "heat and frost days"], "source_url": "https://power.larc.nasa.gov/"}]
                          + [{"id": i, "name": n, "tells_you": t, "resolution": r, "date_range": None, "rows": 0, "status": "pending",
                              "used_in": [], "source_url": u, "note": TIER2_WHY} for i, n, t, r, u in NASA_STATIC]),
        "crop_history": hist,
        "crop_history_purity": purity,
        "dwr_2023": ({"main_crop": crop_now, "class": props.get("CLASS1"), "croptyp2": props.get("CROPTYP2"), "acres": props.get("ACRES"),
                      "county": props.get("COUNTY")} if props else None),
        "observed_cover": {"typically_bare_doy_ranges": [], "bare_doy_file": None, "years_used": [],
                           "detector": "not computed for tapped points (needs the Sentinel-2/Landsat series)"},
        "events": [],
        "_notes": {"analysis": ("Built live for a tapped Canadian point: NASA POWER, ECCC stations, AAFC Soil Landscapes of Canada, AAFC Annual "
                                "Crop Inventory, ParcelMap BC parcel in the ALR, regional district (parcel, ALR and district for BC only). " if in_can else
                                "Built live for a tapped point: NASA POWER, SSURGO, CDL, DWR/Land IQ outline, county and DWR water layers. ")
                               + "Satellite series, IMERG, SMAP, GRACE, NASADEM and OpenET are not computed for points (sections.*).",
                   "boundary": ("DWR Statewide Crop Mapping 2023 (Land IQ), final" if props else
                                "field polygon from the catalog selection source" if sections["boundary"].get("source") == "catalog_outline" else
                                "ParcelMap BC parcel clipped to the Agricultural Land Reserve (follows legal lines, not the crop edge)" if has_outline and in_bc
                                else "200 m square around the tap (no field outline)"),
                   "engine": f"rotation set reused from {tpl} (no new agronomy); market preference no_preference (not asked)"},
    }
    ms["total"] = round((time.perf_counter() - t0) * 1000)
    daily = daily_payload(pid, df, lat, pmeta, today) if df is not None else {}
    return loc, daily, items, {"timings_ms": ms, "sections": sections, "in_ca": in_ca}


def slc_soil(p: dict, today: str) -> tuple[dict, dict]:
    """Location.soil from an SLC v3.2 polygon (slc_bc.json.gz) + the engine's drainage-check soil."""
    s = p["summary"]
    srcd = {"id": "aafc_slc_v3_2", "title": p["source"]["title"], "url": p["source"]["url"], "accessed": today, "verified": True}
    comps = ", ".join(f"{cp['soil_name']} {cp['percent']}%" for cp in p["components"][:4])
    note = ("proportion-weighted over the SLC polygon's soils, 0-100 cm (1:1,000,000 map: which soil is in this field is not mapped)")
    soil = {"mukey": f"SLC {p['poly_id']}", "muname": f"Soil Landscapes of Canada polygon {p['poly_id']}: {comps}",
            "drainage_class": s["drainage_class"] or "unknown", "hydrologic_group": s["hydrologic_group"] or "unknown",
            "awc_mm_per_m": (sn(s["awc_mm_per_m"], "mm/m", srcd, "available water (33-1500 kPa) " + note, "lookup", s["awc_low"], s["awc_high"])
                             if s["awc_mm_per_m"] is not None else blocked_sn("mm/m", "SLC has no water retention data for these soils")),
            "om_pct": (sn(s["om_pct"], "%", srcd, "organic carbon x 1.724 (assumed factor), " + note, "lookup", s["om_low"], s["om_high"])
                       if s["om_pct"] is not None else blocked_sn("%", "SLC has no organic carbon for these soils")),
            "texture_class": s["texture_class"] or "unknown",
            "source": {"id": "aafc_slc_v3_2", "url": p["source"]["url"], "verified": True},
            "ph_0_30cm": s.get("ph_0_30cm"),
            "texture_detail": {"sand_pct": s["sand_pct"], "silt_pct": s["silt_pct"], "clay_pct": s["clay_pct"],
                               "method": "USDA triangle on SLC 0-100 cm proportion-weighted sand/silt/clay"},
            "drainage_basis": f"dominant condition ({s['drainage_share_pct']}% of the polygon)",
            "hydrologic_group_basis": ("derived from SLC Ksat and drainage (NRCS NEH 630 ch. 7 Table 7-1; SLC publishes none), dominant "
                                       f"condition ({s['hydrologic_group_share_pct']}% of the polygon)"),
            "components": p["components"]}
    return soil, {"drainage_class": soil["drainage_class"], "hydrologic_group": soil["hydrologic_group"], "mukey": soil["mukey"], "muname": soil["muname"]}


def water_block(w: dict | None, family: str) -> dict:
    """Location.water from a point lookup (same keys as backend/api/build_real.py water_block)."""
    if not w:
        return {"source": None, "source_note": "not looked up (outside California or lookup failed)",
                "allocation_input": {"unit": "acre-ft/acre", "value": None}, "district": None, "other_agencies": [],
                "sgma_subbasin": None, "sgma_subbasin_number": None, "sgma_priority": None, "critically_overdrafted": None,
                "gsa": [], "sgma_status": {"text": None, "url": None, "verified": False}, "cdec_stations": [], "lookup": None}
    sb = w.get("subbasin") or {}
    board = w.get("state_board") or {}
    gsp = [g.get("dwr_status") for g in (w.get("gsp") or []) if g.get("dwr_status")]
    bits = [f"{sb.get('name', '').split(' - ')[-1].title()} Subbasin ({sb.get('number')})" if sb else None,
            f"{w.get('sgma_priority')} priority" if w.get("sgma_priority") else None,
            "critically overdrafted" if w.get("critically_overdrafted") else None,
            f"State Water Board: {board.get('status')}" if board else None,
            f"DWR GSP assessment: {sorted(set(gsp))[0]}" if len(set(gsp)) == 1 else (f"DWR GSP assessments: {', '.join(sorted(set(gsp)))}" if gsp else None)]
    return {"source": None, "source_note": "surface vs groundwater use not looked up for a tapped point",
            "allocation_input": {"unit": "acre-ft/acre", "value": None},
            "example_limit_af_ac": {"value": 5.0 if family == "rice" else 3.0, "unit": "acre-ft/acre", "low": None, "high": None, "method": "assumed",
                                    "source": {"id": "fieldshift_example_limit", "title": "CropLytics example value (assumed)", "url": "urn:fieldshift:assumed", "verified": False},
                                    "note": "Example limit for trying the water-allocation control (U). Not this field's allocation."},
            "district": w.get("district"), "other_agencies": w.get("other_agencies", []),
            "sgma_subbasin": sb.get("name"), "sgma_subbasin_number": sb.get("number"), "sgma_priority": w.get("sgma_priority"),
            "critically_overdrafted": w.get("critically_overdrafted"), "gsa": [g["name"] for g in (w.get("gsa") or [])],
            "sgma_status": {"text": "; ".join(b for b in bits if b) or None, "url": board.get("url") or (w.get("gsp_source") or {}).get("url"), "verified": True},
            "cdec_stations": [], "lookup": w}


async def _none():
    return None


async def _raise(e):
    raise e


def _plain(x):
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if hasattr(x, "tolist"):
        return _plain(x.tolist())
    if hasattr(x, "item"):
        return x.item()
    if isinstance(x, float) and x != x:
        return None
    return x
