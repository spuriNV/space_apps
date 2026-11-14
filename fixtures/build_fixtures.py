"""Generates every fixtures/**/*.json. Run: python3 fixtures/build_fixtures.py
All numbers are PLACEHOLDERS unless a SourcedNumber says verified:true with a URL copied from planner-spec.md."""
import json, math, random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
ACC = "2026-11-14"
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]
PLACE = {"id": "fixture_placeholder", "title": "Fixture placeholder (not a measurement)",
         "url": "urn:fieldshift:fixture-placeholder", "accessed": ACC, "verified": False}
FAO12 = {"id": "fao56_table12", "title": "FAO-56 Table 12, Rice, Kc", "url": "https://www.fao.org/4/x0490e/x0490e0b.htm", "accessed": ACC, "verified": True}
EQIP = "https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives-program"


def sn(v, unit=None, lo=None, hi=None, method="assumed", src=None, note="", rng=True):
    d = {"value": v}
    if unit: d["unit"] = unit
    if v is not None and rng:
        d["low"] = round(lo if lo is not None else v * 0.85, 3)
        d["high"] = round(hi if hi is not None else v * 1.15, 3)
    d["method"] = method
    if v is not None: d["source"] = src or PLACE
    if note: d["note"] = note
    return d


def dump(rel, obj):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, dict): obj = {"_fixture": True, **obj}
    p.write_text(json.dumps(obj, indent=1) + "\n")


# ---------------- crops ----------------
RK = ["erosion_reduction", "soil_builder", "lasting_residue", "nitrogen_fixation", "nitrogen_scavenging",
      "compaction_reduction", "forage_harvest_value", "weed_suppression", "tolerance_flood", "tolerance_drought"]
# id: (name, family, role, legume, root, kc(ini,mid,end), stages(ini,dev,mid,late), cover, ratings, yield, window, pests, seed)
CROPS = {
 "rice_medium_grain": ("Rice (medium grain, water-seeded)", "Poaceae", ["cash"], False, "shallow fibrous", (1.05, 1.20, 0.75), (30, 30, 60, 30), (0.3, 0.7, 1.0, 0.8),
   (1, 2, 3, 0, 1, 0, 0, 1, 4, 0), 9500, ("04-20", "06-01"), ["weedy rice", "rice water weevil (U)"], 180),
 "cereal_vetch_cover": ("Cereal + vetch winter cover", "Poaceae/Fabaceae", ["cover"], True, "fibrous + taproot", (0.40, 0.90, 0.35), (20, 30, 60, 30), (0.4, 0.8, 1.0, 0.6),
   (3, 3, 3, 3, 3, 2, 1, 3, 1, 2), 0, ("10-15", "11-30"), [], 90),
 "safflower": ("Safflower", "Asteraceae", ["cash"], False, "deep taproot", (0.35, 1.15, 0.25), (20, 35, 45, 25), (0.2, 0.6, 0.9, 0.5),
   (1, 1, 2, 0, 2, 3, 0, 1, 0, 3), 2200, ("03-15", "04-30"), [], 60),
 "winter_wheat": ("Winter wheat", "Poaceae", ["cash"], False, "fibrous", (0.40, 1.15, 0.25), (30, 140, 40, 30), (0.3, 0.8, 1.0, 0.7),
   (3, 2, 3, 0, 3, 1, 1, 2, 1, 2), 6500, ("11-01", "12-31"), [], 75),
 "alfalfa": ("Alfalfa (hay/forage)", "Fabaceae", ["forage", "cash"], True, "deep taproot", (0.40, 1.20, 1.15), (10, 30, 25, 10), (0.5, 0.9, 1.0, 1.0),
   (3, 4, 3, 4, 2, 3, 4, 2, 1, 3), 17000, ("09-15", "10-31"), ["alfalfa weevil (U)"], 220),
 "silage_corn": ("Silage corn", "Poaceae", ["forage"], False, "fibrous", (0.30, 1.20, 0.60), (30, 40, 50, 30), (0.2, 0.7, 1.0, 0.8),
   (1, 1, 2, 0, 2, 1, 4, 1, 1, 1), 25000, ("04-15", "05-31"), [], 250),
 "winter_small_grain_silage": ("Winter small-grain silage (wheat/triticale)", "Poaceae", ["forage", "cover"], False, "fibrous", (0.40, 1.15, 0.25), (30, 140, 40, 30), (0.3, 0.8, 1.0, 0.5),
   (3, 2, 3, 0, 3, 1, 3, 2, 1, 2), 14000, ("10-15", "11-30"), [], 75),
 "sorghum_sudan": ("Sorghum-sudan summer forage", "Poaceae", ["forage"], False, "deep fibrous", (0.30, 1.00, 0.55), (20, 35, 40, 30), (0.2, 0.7, 1.0, 0.9),
   (2, 2, 2, 0, 2, 2, 3, 2, 1, 3), 18000, ("04-25", "06-15"), [], 70),
 "fallow": ("Fallow / bare", "none", ["fallow"], False, "none", (0.0, 0.0, 0.0), (0, 0, 0, 0), (0.0, 0.0, 0.0, 0.0),
   (0, 0, 0, 0, 0, 0, 0, 0, 0, 0), 0, ("01-01", "12-31"), [], 0),
}
SPEC_NOTE = "placeholder"


def crop(cid):
    n, fam, role, leg, root, kc, st, cov, rt, y, win, pests, seed = CROPS[cid]
    if cid == "rice_medium_grain":
        kcd = {"ini": sn(1.05, "Kc", method="lookup", src=FAO12, rng=False),
               "mid": sn(1.20, "Kc", method="lookup", src=FAO12, rng=False),
               "end": sn(0.75, "Kc", 0.60, 0.90, method="lookup", src=FAO12)}
        stage_src = "fao56_table11 Rice May Mediterranean (V)"
    else:
        kcd = {k: sn(v, "Kc", v * 0.9, v * 1.1) for k, v in zip(["ini", "mid", "end"], kc)}
        stage_src = "fao56_table11 (V) for safflower California" if cid == "safflower" else "assumed placeholder (U)"
    ratings = {k: sn(v, "0-4 rating", v, v, note="placeholder rating (U)") for k, v in zip(RK, rt)}
    ver = cid == "rice_medium_grain"
    return {
        "id": cid, "name": n, "family": fam, "role": role, "legume": leg, "root": root, "kc": kcd,
        "stage_lengths_days": dict(zip(["ini", "dev", "mid", "late"], st), source=stage_src),
        "cover_by_stage": dict(zip(["ini", "dev", "mid", "late"], cov)),
        "ratings_0_4": ratings,
        "yield_range": sn(y, "kg/ha", y * 0.84 if cid == "rice_medium_grain" else None, y * 1.16 if cid == "rice_medium_grain" else None),
        "drainage_classes_ok": ["poorly", "very poorly", "somewhat poor"] if cid == "rice_medium_grain" else ["well", "moderately well", "somewhat poor"],
        "seeding_window": {"start": win[0], "end": win[1], "best": "by mid-May" if ver else "placeholder", "verified": ver},
        "pest_notes": pests, "cautions": ["herbicide carryover to rotation crops (U)"] if ver else [],
        "seed_cost_per_ha": sn(seed, "USD/ha"), "explainer_card": "cover_crop" if cid == "cereal_vetch_cover" else None,
        "sources": ([{"id": "fao56_table12", "url": "https://www.fao.org/4/x0490e/x0490e0b.htm"}, {"id": "uc_rice", "url": "https://rice.ucanr.edu/"}]
                    if ver else [{"id": "fixture_placeholder", "url": "urn:fieldshift:fixture-placeholder"}]),
    }


# ---------------- strategies ----------------
def cal(year, crop_id, plant, harvest, role, src, **kw):
    d = {"year": year, "crop_id": crop_id, "plant": plant, "role": role, "timing_source": src}
    if role == "cover": d["terminate"] = harvest
    else: d["harvest"] = harvest
    d.update(kw)
    return d

RICE_AVG = "uc_rice_blog Colusa trial planted 18 May, harvested 12 Oct (V)"
STRATS = {
 "car_colusa_rice": [
  ("car0_rice_winterflood", "Continuous rice, winter flood (baseline)", True, 1, None,
   [cal(1, "rice_medium_grain", "05-18", "10-12", "cash", RICE_AVG)]),
  ("car1_rice_wintercover", "Rice + winter cover (no winter flood)", False, 1, None,
   [cal(1, "rice_medium_grain", "05-10", "10-05", "cash", "uc_rice_blog (V avg)"),
    cal(1, "cereal_vetch_cover", "10-25", "03-20", "cover", "assumed (U)", harvest_year_offset=1)]),
  ("car2_dry_year_safflower", "Dry-year plan: safflower / cover fallow (allocation < 50%)", False, 1, "applies when surface-water allocation < 50% (dry year shown)",
   [cal(1, "safflower", "04-05", "07-31", "cash", "plant: fao56_table11 April (V); harvest assumed (U)")]),
  ("car3_rice_winterwheat", "Rice, then winter wheat (wheat year)", False, 2, None,
   [cal(1, "rice_medium_grain", "05-18", "10-12", "cash", RICE_AVG),
    cal(1, "winter_wheat", "12-01", "06-15", "cash", "plant: fao56_table11 Calif. December (V); harvest assumed (U)", harvest_year_offset=1)]),
 ],
 "caf_tulare_forage": [
  ("caf0_alfalfa_baseline", "Alfalfa, 7-8 cuts, 4-5 yr stand (baseline)", True, 4, None,
   [cal(1, "alfalfa", "09-25", "11-15", "forage", "UC Alfalfa: plant mid-Sept-Oct (V); 7-8 cuts (U count)")]),
  ("caf1_silage_corn_double", "Winter small-grain silage + silage corn", False, 1, None,
   [cal(1, "winter_small_grain_silage", "10-25", "04-25", "forage", "assumed (U)", harvest_year_offset=1),
    cal(1, "silage_corn", "05-05", "08-25", "forage", "assumed (U)")]),
  ("caf2_silage_sorghum_sudan", "Winter small-grain silage + sorghum-sudan", False, 1, None,
   [cal(1, "winter_small_grain_silage", "10-25", "04-25", "forage", "assumed (U)", harvest_year_offset=1),
    cal(1, "sorghum_sudan", "05-05", "08-20", "forage", "assumed (U)")]),
  ("caf3_alfalfa_break_year", "Alfalfa 3-yr stand, cereal break year, re-seed", False, 4, "break year leaves a summer with no irrigated crop under a pumping cap",
   [cal(1, "alfalfa", "09-25", "11-15", "forage", "UC Alfalfa window (V)"),
    cal(2, "alfalfa", None, "11-15", "forage", "assumed (U)"), cal(3, "alfalfa", None, "11-15", "forage", "assumed (U)"),
    cal(4, "winter_small_grain_silage", None, "04-25", "forage", "assumed (U); sown previous autumn"),
    cal(4, "fallow", "05-01", "08-31", "fallow", "assumed (U): summer fallow, no pumping")]),
 ],
}
SCORE_KEYS = ["water_use", "forage_value", "n_fixation", "erosion", "organic_matter", "market", "pest_break", "infiltration", "n_scavenging", "income"]
DEFAULT_W = {"water_use": 1, "forage_value": 1, "n_fixation": 1, "erosion": 1, "organic_matter": 1, "market": 1,
             "pest_break": 0, "infiltration": 0, "n_scavenging": 0, "income": 0}
EXP_KEYS = ["bare_days_per_year", "exposed_rain_days", "exposed_frost_days", "exposed_heat_days", "exposed_dry_days"]


def composite(scores, w):
    tot = sum(w.values()) or 1
    f = lambda k: round(sum(w[x] * scores[x][k] for x in w) / tot, 1)
    return {"value": f("value"), "low": f("low"), "high": f("high"), "weights_used": dict(w)}


def strategy(pid, spec, rng):
    sid, name, base, cyc, rule, calendar = spec
    scores = {k: sn(round(rng.uniform(25, 85), 1), "score 0-100", note="placeholder score") for k in SCORE_KEYS}
    for s in scores.values(): s["low"], s["high"] = round(s["value"] - 9, 1), round(s["value"] + 9, 1)
    exp = {k: sn(round(rng.uniform(5, 160)), "days") for k in EXP_KEYS}
    exp["replay"] = {y: {k: sn(round(rng.uniform(5, 160)), "days") for k in EXP_KEYS} for y in ("2022", "2023")}
    exp["scenario"] = {"dT_c": 0, "dP_pct": 0}
    etc = round(rng.uniform(450, 1100))
    months = [sn(round(etc * w / 12 * 12 / 6 if 4 <= i <= 9 else 10), "mm") for i, w in enumerate([1] * 12)]
    ev_cover = any(c["role"] == "cover" for c in calendar)
    return {
        "id": sid, "location_id": pid, "name": name, "is_baseline": base, "cycle_years": cyc, "calendar": calendar,
        "allocation_rule": rule, "exposure": exp,
        "water": {"etc_mm_season": sn(etc, "mm"), "irrigation_need_mm": sn(round(etc * 0.8), "mm"), "etc_by_month_mm": months,
                  "openet_et_mm_season": sn(round(etc * 0.95), "mm", method="measured", note="placeholder, not OpenET"),
                  "etc_vs_openet_pct": sn(5.0, "%")},
        "scores": scores, "composite": composite(scores, DEFAULT_W),
        "risk_profile": {"rma_share_drought": sn(0.4, "share", 0.3, 0.5), "rma_share_excess_moisture": sn(0.2, "share", 0.1, 0.3),
                         "rma_share_heat": sn(0.1, "share"), "rma_share_other": sn(0.3, "share"), "rma_years": [2010, 2024]},
        "funding": ([{"program": "USDA EQIP practice 340 Cover Crop", "rate_per_acre_usd": {"value": None, "method": "assumed"}, "url": EQIP, "verified": False}] if ev_cover else []),
        "brief": {
            "why": [{"text": "[fixture placeholder] Explanation text is written by the LLM layer and checked against the numbers.", "source_ids": ["fixture_placeholder"], "numbers_used": ["composite.value"], "author": "template", "checked": True}],
            "evidence": [{"text": "[fixture placeholder] evidence line", "source_ids": ["fixture_placeholder"]}],
            "benefits": [{"text": "[fixture placeholder] benefit line", "source_ids": ["fixture_placeholder"]}],
            "gaps": [{"text": "[fixture placeholder] gap line", "source_ids": []}],
            "local_review": [{"item": "Confirm district / GSA rules and local seeding dates", "severity": "high"}],
            "explainer_cards": ["cover_crop"] if ev_cover else [],
            "llm_report": {"sentences": 0, "numbers_checked": 0, "rejected": 0, "model": None, "cached_at": None}},
        "uncertainty": {"dataset_disagreement": sn(12, "%"), "scale": sn(30, "m", method="lookup", note="field grid vs 9 km regional"),
                        "agronomic_gap_count": 3, "detector_disagreement_pct": 7},
    }


# ---------------- locations ----------------
def square(lon, lat, hw_m, hh_m):
    dlat = hh_m / 111320.0
    dlon = hw_m / (111320.0 * math.cos(math.radians(lat)))
    return {"type": "Polygon", "coordinates": [[[round(lon - dlon, 6), round(lat - dlat, 6)], [round(lon + dlon, 6), round(lat - dlat, 6)],
             [round(lon + dlon, 6), round(lat + dlat, 6)], [round(lon - dlon, 6), round(lat + dlat, 6)], [round(lon - dlon, 6), round(lat - dlat, 6)]]]}

CDEC = "https://cdec.water.ca.gov/"
LOCS = {
 "car_colusa_rice": dict(
   name="Colusa County rice check (example)", regime="drought_then_flood", county="011", lon=-122.10, lat=39.15, ha=60, hw=387, hh=387,
   soil=dict(muname="[fixture] placeholder map unit", drain="somewhat poorly drained", hsg="D", awc=140, om=1.8, tex="clay loam"),
   water=dict(source="surface", district="Glenn-Colusa ID (U)", sgma="Colusa", sgma_text="SGMA Colusa Subbasin, medium priority (U)", sgma_url=None, sgma_ver=False, cdec=["SHA", "ORO"]),
   mp="sell", stations=[{"network": "CIMIS", "id": 250, "name": "Williams", "distance_km": 8, "years": [2016, 2026]}, {"network": "NOAA", "id": "U-station-id-tbd", "name": "Colusa/Williams (U)", "distance_km": None, "years": [2016, 2026]}],
   hist={"2019": "Rice", "2020": "Rice", "2021": "Rice", "2022": "Fallow/Idle", "2023": "Rice", "2024": "Rice"}, bare=[[290, 110]],
   events=[{"date": "2022-05-01", "type": "drought_fallow", "title": "Sacramento Valley rice acreage roughly halved", "url": "https://science.nasa.gov/earth/earth-observatory/a-rough-year-for-rice-in-california-150412/", "verified": True},
           {"date": "2023-01-09", "type": "atmospheric_river", "title": "Jan-Mar 2023 atmospheric rivers (start date placeholder)", "url": None, "verified": False}]),
 "caf_tulare_forage": dict(
   name="Tulare/Kings forage-for-dairy check (example)", regime="drought_then_flood", county="031", lon=-119.60, lat=36.20, ha=32, hw=283, hh=283,
   soil=dict(muname="[fixture] placeholder map unit", drain="well drained", hsg="B", awc=150, om=1.2, tex="loam"),
   water=dict(source="groundwater", district="Tulare Lake Subbasin GSA (U)", sgma="Tulare Lake", sgma_text="SGMA Tulare Lake Subbasin placed on probation 16 Apr 2024 (spec marks V; URL not in spec)", sgma_url=None, sgma_ver=False, cdec=["PNF"]),
   mp="feed_own_herd", stations=[{"network": "CIMIS", "id": 15, "name": "Stratford (U)", "distance_km": None, "years": [2016, 2026]}, {"network": "NOAA", "id": "U-station-id-tbd", "name": "Hanford (U)", "distance_km": None, "years": [2016, 2026]}],
   hist={"2019": "Alfalfa", "2020": "Alfalfa", "2021": "Alfalfa", "2022": "Corn", "2023": "Fallow/Idle", "2024": "Alfalfa"}, bare=[[300, 60]],
   events=[{"date": "2023-03-15", "type": "flood", "title": "Spring 2023 Tulare Lake re-flooding (~114,000 acres peak); date is a placeholder", "url": None, "verified": False, "note": "spec marks the event V (news) but gives no URL"},
           {"date": "2024-04-16", "type": "sgma_probation", "title": "Tulare Lake Subbasin placed on SGMA probation", "url": None, "verified": False, "note": "spec marks V but gives no URL"}]),
}
DATASETS = ["power", "imerg", "smap_l3", "smap_l4", "hls", "s2", "modis", "ecostress", "grace", "dem", "cdl", "openet", "cimis", "cdec", "dwr_wells", "rma", "usdm", "news"]


def location(pid):
    c = LOCS[pid]; s = c["soil"]; w = c["water"]
    return {
     "id": pid, "name": c["name"], "region_adapter": "ca", "regime": c["regime"], "state_fips": "06", "county_fips": c["county"],
     "geometry": square(c["lon"], c["lat"], c["hw"], c["hh"]), "centroid": {"lon": c["lon"], "lat": c["lat"]},
     "area_ha": sn(c["ha"], "ha", method="assumed", note="spec B1 field size (U); polygon here is a placeholder square"),
     "crs_working": "EPSG:32610",
     "soil": {"mukey": "fixture", "muname": s["muname"], "drainage_class": s["drain"], "hydrologic_group": s["hsg"],
              "awc_mm_per_m": sn(s["awc"], "mm/m"), "om_pct": sn(s["om"], "%"), "texture_class": s["tex"],
              "source": {"id": "ssurgo_sda", "url": "https://sdmdataaccess.sc.egov.usda.gov/", "verified": True}},
     "terrain": {"slope_mean_pct": sn(0.1 if pid.startswith("car") else 0.3, "%"), "slope_p90_pct": sn(0.3, "%"),
                 "elev_m": sn(20 if pid.startswith("car") else 62, "m"), "low_spot_fraction": sn(0.04, "fraction")},
     "water": {"source": w["source"], "allocation_input": {"unit": "acre-ft/acre", "value": None}, "district": w["district"],
               "sgma_subbasin": w["sgma"], "sgma_status": {"text": w["sgma_text"], "url": w["sgma_url"], "verified": w["sgma_ver"]}, "cdec_stations": w["cdec"]},
     "market_preference": c["mp"], "stations": c["stations"],
     "regional_cell": {"grid": "EASE2_G9km", "row": 0, "col": 0, "footprint": square(c["lon"], c["lat"], 4500, 4500)},
     "datasets": {k: {"status": "fixture"} for k in DATASETS},
     "crop_history": c["hist"],
     "observed_cover": {"typically_bare_doy_ranges": c["bare"], "bare_doy_file": None, "years_used": list(range(2016, 2026)), "detector": "consensus"},
     "events": c["events"],
    }


# ---------------- other routes ----------------
def daily(pid):
    rows = []; d0 = date(2023, 1, 1)
    for i in range(365):
        d = d0 + timedelta(days=i); s = math.sin((i - 100) / 365 * 2 * math.pi)
        cover = "bare" if (i > 290 or i < 100) and pid.startswith("caf") is False and False else ("covered" if 130 < i < 280 else "bare")
        rows.append({"date": d.isoformat(), "tmax_c": round(22 + 14 * s, 1), "tmin_c": round(8 + 8 * s, 1),
                     "precip_mm": round(max(0, 4 * math.sin(i / 7.0)) if i < 100 or i > 300 else 0, 1),
                     "eto_mm": round(max(0.5, 3.5 + 3 * s), 2), "smap_sm_pct": round(50 + 30 * math.sin(i / 40), 1),
                     "ndvi": round(0.55 + 0.4 * s if cover == "covered" else 0.12, 2), "cover_class": cover})
    return {"location_id": pid, "rows": rows}


def weekly(pid):
    rows = []; d0 = date(2023, 1, 2)
    for i in range(52):
        d = d0 + timedelta(weeks=i); s = math.sin((i - 14) / 52 * 2 * math.pi); iso = d.isocalendar()
        rows.append({"week_start": d.isoformat(), "iso_year": iso[0], "iso_week": iso[1], "ndvi_median": round(0.4 + 0.35 * s, 3),
                     "ndvi_p10": round(0.3 + 0.35 * s, 3), "ndvi_p90": round(0.5 + 0.35 * s, 3), "bsi": round(0.1 - 0.1 * s, 3), "nbr2": round(0.05 + 0.05 * s, 3),
                     "lst_anomaly_k": round(0.8 * s, 2), "esi": round(0.5 * s, 2), "openet_et_mm_month": round(max(10, 80 + 70 * s), 1),
                     "smap_sm": round(0.25 + 0.05 * s, 3), "smap_sm_pct": round(50 + 20 * math.sin(i / 6), 1), "imerg_7d_mm": round(max(0, 15 * math.sin(i / 4)) if i < 15 or i > 40 else 0, 1),
                     "power_tmax_c": round(22 + 14 * s, 1), "power_tmin_c": round(8 + 8 * s, 1), "power_eto_mm": round(max(3, 25 + 20 * s), 1),
                     "grace_sfsm_pct": round(50 + 10 * math.sin(i / 9), 1), "grace_rzsm_pct": round(50 + 8 * math.sin(i / 11), 1), "grace_gws_pct": round(30 + 5 * math.sin(i / 20), 1),
                     "modis_ndvi_anomaly": round(0.3 * math.sin(i / 8), 2), "usdm_category": ["None", "D0", "D1", "D2"][i // 14 % 4]})
    return {"location_id": pid, "rows": rows}


def models(pid):
    tr, te = [2016, 2017, 2018, 2019, 2020, 2021, 2023], [2022, 2024, 2025]
    feats = ["ndvi_median", "bsi", "nbr2", "ndvi_p10"]
    def mr(i, task, method, labels, metrics):
        return {"id": f"{i}_{pid}_v1", "task": task, "method": method, "features": feats if method != "zscore" else ["ndvi_median"], "labels": labels,
                "split": {"train_years": tr, "test_years": te}, "metrics": metrics, "confusion": [[90, 10], [8, 92]] if task == "bare_cover" else [],
                "feature_importance": [{"feature": f, "importance": round(0.4 - 0.1 * k, 2)} for k, f in enumerate(feats)] if method == "random_forest" else [],
                "disagreement_with": {"rule_ndvi": 0.07} if method != "rule_ndvi" else {}, "notes": "[fixture placeholder] numbers are not model output"}
    return {"location_id": pid, "items": [
        mr("bare_rule", "bare_cover", "rule_ndvi", "cdl_year_class + season_rules", {"accuracy": 0.88, "f1_bare": 0.85}),
        mr("bare_rf", "bare_cover", "random_forest", "cdl_year_class + season_rules", {"accuracy": 0.92, "f1_bare": 0.89, "transition_mae_days": 8}),
        mr("stress_if", "stress_anomaly", "isolation_forest", "s2_scl_pseudo", {"precision_at_k": 0.6})]}


def zones(pid):
    c = LOCS[pid]; lon, lat = c["lon"], c["lat"]; car = pid.startswith("car")
    f = lambda layer, dx, dy, meaningful, label, note="": {"type": "Feature", "geometry": square(lon + dx, lat + dy, 60, 60),
        "properties": {"layer": layer, "meaningful": meaningful, "label": label, "value": sn(1.0, "placeholder"), **({"note": note} if note else {})}}
    feats = [f("slope", -0.001, 0.001, not car, "slope class", "levelled field, slope zones not meaningful" if car else ""),
             f("low_spot", 0.001, -0.001, True, "low spot (>= 1 m below 300 m focal mean) (U)"),
             f("stress_hotspot", 0.0015, 0.0015, True, "stress hotspot (U)"), f("openet_zone", -0.0015, -0.0015, True, "OpenET within-field ET zone")]
    return {"location_id": pid, "type": "FeatureCollection", "features": feats}


LAYERS = {"smap_anomaly": "sd", "heatwave_days": "days/yr", "grace_gw_pct": "percentile", "precip_anomaly": "%", "modis_ndvi_anomaly": "sd"}


def trends(pid, layer):
    rng = random.Random(pid + layer)
    return {"location_id": pid, "layer": layer, "year": 2023, "unit": LAYERS[layer], "grid": "EASE2_G9km",
            "source": dict(PLACE), "cells": [{"row": r, "col": c, "value": round(rng.uniform(-1, 1), 2)} for r in range(11) for c in range(11)],
            "field_cell_series": [{"year": y, "value": round(rng.uniform(-1, 1), 2)} for y in range(2015, 2026)],
            "event_markers": [{"date": e["date"], "title": e["title"], "url": e["url"], "verified": e["verified"]} for e in LOCS[pid]["events"]]}


def news(pid):
    if pid.startswith("car"):
        items = [{"date": "2022-05-20", "title": "Calif. rice acreage to drop to 39-year low", "source": "Farm Progress",
                  "url": "https://www.farmprogress.com/rice/calif-rice-acreage-to-drop-to-39-year-low", "rank": 2, "place_match": ["Sacramento Valley"],
                  "query_id": "car_2022_drought", "signal": {"dataset": "smap_l3", "value_pct": None, "lead_days": None}}]
    else:
        items = [{"date": "2023-03-15", "title": "[fixture placeholder] Tulare Lake re-flooding headline", "source": "fixture", "url": None, "rank": 1,
                  "place_match": ["Tulare Lake"], "query_id": "caf_2023_flood", "signal": {"dataset": "imerg", "value_pct": None, "lead_days": None}}]
    return {"location_id": pid, "items": items}


def validation(pid):
    t = [("openet_vs_etc", "OpenET vs modelled ETc"), ("cimis_vs_power", "CIMIS vs NASA POWER ETo"), ("station_vs_imerg", "Station rain vs IMERG")]
    return {"location_id": pid, "checks": [{"id": i, "title": n, "status": "pending", "metrics": {"bias_pct": sn(None, "%"), "r2": sn(None)}, "note": "[fixture] not computed"} for i, n in t]}


def score_fixture(pid, strategies):
    return {"location_id": pid, "request": {"weights": DEFAULT_W, "constraints": {}, "market_preference": LOCS[pid]["mp"], "allocation": None, "replay_year": None, "scenario": {"dT_c": 0, "dP_pct": 0}},
            "items": strategies, "ranking": rank(strategies), "note": "fixture: default weights; scenario not applied"}


def rank(strats):
    out = []; ordered = sorted(strats, key=lambda s: -s["composite"]["value"])
    for i, s in enumerate(ordered):
        c = s["composite"]; tie = False
        if i:
            p = ordered[i - 1]["composite"]; ov = min(c["high"], p["high"]) - max(c["low"], p["low"])
            tie = ov > 0.5 * min(c["high"] - c["low"], p["high"] - p["low"])
        out.append({"id": s["id"], "composite": c["value"], "low": c["low"], "high": c["high"], "tie_with_previous": tie})
    return out


GLOSSARY = [
 ("eto", "ETo (reference evapotranspiration)", "How much water a well-watered grass surface would lose to air and plants in a day, set by weather."),
 ("etc", "ETc (crop evapotranspiration)", "ETo times the crop coefficient Kc: how much water the actual crop uses."),
 ("kc", "Kc (crop coefficient)", "A crop-stage multiplier that turns ETo into ETc."),
 ("soil_moisture_pct", "Soil-moisture percentile", "Where today's soil moisture sits compared with the same time of year in past years."),
 ("ndvi", "NDVI and bare / partial / covered", "A greenness index from satellite images; low values mean bare soil, high values mean plant cover."),
 ("frost_risk", "Frost risk", "Days when minimum temperature is cold enough to damage a crop that is at a tender stage."),
 ("water_balance", "Water balance and irrigation need", "Crop water use minus useful rain and stored soil water; the rest must be irrigated."),
 ("lst", "Heat stress / land-surface temperature", "How hot the ground and canopy are, seen from space, compared with normal."),
 ("grace", "Groundwater storage (GRACE) and SGMA", "Satellite gravity data show regional groundwater change; SGMA is California's groundwater law."),
 ("allocation", "Allocation (acre-ft/acre)", "The water a district or GSA lets you use per acre; 1 acre-ft/acre is about 305 mm."),
 ("pixel", "Pixel / footprint and scale badge", "Each dataset has a cell size; a 9 km cell cannot see inside a 60 ha field."),
 ("pseudo_label", "Label vs pseudo-label", "A label is checked ground truth; a pseudo-label is a rule's guess used to train a model."),
 ("isolation_forest", "Isolation forest", "An unsupervised method that flags weeks that look unusual compared with the rest."),
]


def main():
    for cid in CROPS: dump(f"crops/{cid}.json", crop(cid))
    locs = []
    for pid in PRESETS:
        rng = random.Random(pid)
        loc = location(pid); locs.append(loc)
        strats = [strategy(pid, sp, rng) for sp in STRATS[pid]]
        dump(f"{pid}/location.json", loc); dump(f"{pid}/daily.json", daily(pid)); dump(f"{pid}/features_weekly.json", weekly(pid))
        dump(f"{pid}/strategies.json", {"location_id": pid, "items": strats}); dump(f"{pid}/score.json", score_fixture(pid, strats))
        dump(f"{pid}/models.json", models(pid)); dump(f"{pid}/zones.json", zones(pid))
        for l in LAYERS: dump(f"{pid}/trends_{l}.json", trends(pid, l))
        dump(f"{pid}/news.json", news(pid)); dump(f"{pid}/validation.json", validation(pid))
    dump("locations.json", {"items": locs})
    dump("bc_news.json", {"items": [
        {"date": "2023-08-16", "title": "[fixture placeholder] Salmon River fish protection order headline", "source": "fixture", "url": None, "rank": 1,
         "place_match": ["Salmon River"], "query_id": "bc_salmon_2023", "signal": {"dataset": "smap_l3", "value_pct": None, "lead_days": None}}]})
    dump("bc_signal.json", {"point": {"lon": -119.33, "lat": 50.62}, "markers": [
        {"date": "2023-06-15", "title": "Irrigators' request (mid-June; exact date placeholder)", "approximate": True, "lead_days": None, "url": None},
        {"date": "2023-08-16", "title": "Fish population protection order", "approximate": False, "lead_days": None, "url": None}],
        "series": [{"date": (date(2023, 3, 1) + timedelta(days=7 * i)).isoformat(), "smap_pct": round(60 - i * 1.4, 1), "grace_gw_pct": round(45 - i * 0.4, 1),
                    "power_tmax_c": round(5 + 22 * math.sin(i / 34 * math.pi), 1)} for i in range(34)]})
    dump("glossary.json", {"items": [{"id": i, "term": t, "short": s, "source_url": None} for i, t, s in GLOSSARY]})


if __name__ == "__main__":
    main()
