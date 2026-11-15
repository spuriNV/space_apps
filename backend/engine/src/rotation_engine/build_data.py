"""Builds crops.json and strategies.json (chunk root) from the spec quotes below.

Run: uv run python -m rotation_engine.build_data

Everything marked lookup()/V is copied from planner-spec B1/B4.1 (which quotes
FAO-56 Tables 11/12 and UC pages). Everything marked assumed()/U is a team
placeholder with a range; it is NOT a fact and must be cited before shipping.
"""
from __future__ import annotations

import json
from pathlib import Path

from .sources import assumed, lookup, src

ROOT = Path(__file__).resolve().parents[2]
U_RATING = "Hand rating 0-4, team placeholder. To cite: Western cover-crop selector goal table / USDA PLANTS (spec B3)."


def r(v, lo=None, hi=None, note=U_RATING):
    lo = max(0, v - 1) if lo is None else lo
    hi = min(4, v + 1) if hi is None else hi
    return assumed(v, "rating_0_4", low=lo, high=hi, note=note, to_cite="https://covercrop-selector.org")


def ratings(ero, soil, resid, nfix, nscav, compact, forage, weed, flood, drought):
    return {"erosion_reduction": r(ero), "soil_builder": r(soil), "lasting_residue": r(resid),
            "nitrogen_fixation": r(nfix), "nitrogen_scavenging": r(nscav), "compaction_reduction": r(compact),
            "forage_harvest_value": r(forage), "weed_suppression": r(weed), "tolerance_flood": r(flood),
            "tolerance_drought": r(drought)}


def seed(v, lo, hi):
    return assumed(v, "USD/ha", low=lo, high=hi,
                   note="Placeholder order of magnitude only; no cited source. Needed for B4.10 income.",
                   to_cite="UC ANR cost-and-return studies (https://coststudies.ucdavis.edu/)")


def root_class(v, note="0 shallow, 1 medium, 2 deep; team placeholder (U)"):
    return assumed(v, "class_0_2", low=max(0, v - 1), high=min(2, v + 1), note=note)


def cover_stage(ini, dev, mid, late, note="Modelled canopy cover fraction by stage; team placeholder (U)."):
    return {"ini": ini, "dev": dev, "mid": mid, "late": late, "method": "assumed", "verified": False, "note": note}


STAGE_U = "assumed (U)"

CROPS = [
    {
        "id": "rice_medium_grain", "name": "Rice (medium grain, water-seeded)", "family": "Poaceae",
        "role": ["cash"], "legume": False, "perennial": False, "root": "shallow fibrous", "market_class": "sell",
        "kc": {"ini": lookup(1.05, "Kc", "fao56_table12", note="Spec B4.1 quote: Rice 1.05 / 1.20 / 0.90-0.60"),
               "mid": lookup(1.20, "Kc", "fao56_table12"),
               "end": lookup(0.75, "Kc", "fao56_table12", low=0.60, high=0.90,
                             note="Spec quotes end 0.90-0.60; value = midpoint")},
        "stage_lengths_days": {"ini": 30, "dev": 30, "mid": 60, "late": 30, "verified": True,
                               "source": "fao56_table11 Rice May Mediterranean (V)", "url": src("fao56_table11")["url"]},
        "cover_by_stage": cover_stage(0.3, 0.7, 1.0, 0.8, note="Values from the spec B3 Crop example; still U."),
        "ratings_0_4": {**ratings(1, 1, 2, 0, 1, 0, 0, 2, 4, 0),
                        "forage_harvest_value": assumed(0, "rating_0_4", low=0, high=0,
                                                        note="Spec B4.2: 'Rice forage 0' (stated by spec; no range)")},
        "root_depth_class": root_class(0),
        "flood_percolation_mm": assumed(450, "mm/season", low=300, high=600,
                                        note="Rice flood-establishment and percolation term F (spec B4.1, U: 300-600 mm)",
                                        to_cite="UC rice water-use publication (spec B4.1: cite before shipping)"),
        "yield_range": assumed(9500, "kg/ha", low=8000, high=11000, note="Grain yield; spec B3 example, U"),
        "drainage_classes_ok": {"value": ["very poorly drained", "poorly drained", "somewhat poorly drained",
                                          "moderately well drained"], "method": "assumed", "verified": False,
                                "note": "U. Spec B3 example lists poorly/very poorly/somewhat poor; we added moderately "
                                        "well drained because Capay clay (the CAR preset's SSURGO unit) is a common "
                                        "rice soil. Needs an agronomist."},
        "seeding_window": {"start": "04-20", "end": "06-01", "best": "by mid-May", "verified": True,
                           "source": "uc_rice_blog", "url": src("uc_rice_blog")["url"],
                           "note": "50% planted by 12 May; 1 June considered too late (spec B1, V)"},
        "pest_notes": ["weedy rice (U)", "rice water weevil (U)"],
        "cautions": ["herbicide carryover to rotation crops (U)"],
        "seed_cost_per_ha": seed(150, 100, 250), "needs_drill": False, "explainer_card": None,
        "sources": [src("fao56_table12"), src("fao56_table11"), src("uc_rice_blog")],
    },
    {
        "id": "alfalfa_hay", "name": "Alfalfa (hay/haylage, multi-cut)", "family": "Fabaceae",
        "role": ["forage"], "legume": True, "perennial": True, "root": "deep taproot", "market_class": "either",
        "kc": {"ini": lookup(0.40, "Kc", "fao56_table12", note="Spec B4.1 quote: Alfalfa hay, averaged cutting effects 0.40 / 0.95 / 0.90"),
               "mid": lookup(0.95, "Kc", "fao56_table12"),
               "end": lookup(0.90, "Kc", "fao56_table12")},
        "kc_individual_cutting_periods": {
            "ini": lookup(0.40, "Kc", "fao56_table12"), "mid": lookup(1.20, "Kc", "fao56_table12"),
            "end": lookup(1.15, "Kc", "fao56_table12"),
            "note": "Reference only; engine uses averaged cutting effects over the season."},
        "stage_lengths_days": {"ini": 62, "dev": 28, "mid": 245, "late": 30, "verified": False,
                               "source": STAGE_U + ": read off the spec B1 CAF0 calendar (dormant Dec-Jan, growth Feb, "
                                         "cuts Mar-Oct, slow Nov), starting 1 Dec; not FAO-56 Table 11",
                               "url": src("assumed")["url"]},
        "cover_by_stage": cover_stage(0.6, 0.8, 0.85, 0.8,
                                      note="U. Established stand; dormant crowns+stubble assumed >= 0.5 cover; mid is a "
                                           "cutting-cycle average."),
        "ratings_0_4": {**ratings(3, 3, 1, 4, 2, 3, 4, 2, 1, 3),
                        "forage_harvest_value": assumed(4, "rating_0_4", low=4, high=4,
                                                        note="Spec B4.2: alfalfa rating 4 (stated by spec; not cited)")},
        "root_depth_class": root_class(2),
        "yield_range": assumed(17500, "kg DM/ha/yr", low=15000, high=20000,
                               note="Spec B4.2: alfalfa 15-20 t DM/ha SJV (U: cite UC/NASS county yields)"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat excessively drained"],
                                "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "09-15", "end": "10-31", "best": "mid-Sept to Oct (central SJV)", "verified": True,
                           "source": "uc_alfalfa", "url": src("uc_alfalfa")["url"]},
        "pest_notes": ["alfalfa weevil (U)"], "cautions": [],
        "seed_cost_per_ha": seed(300, 200, 450), "needs_drill": True, "explainer_card": "nitrogen_fixing",
        "sources": [src("fao56_table12"), src("uc_alfalfa")],
    },
    {
        "id": "silage_corn", "name": "Corn for silage", "family": "Poaceae",
        "role": ["forage"], "legume": False, "perennial": False, "root": "fibrous, medium", "market_class": "feed",
        "kc": {"ini": lookup(0.30, "Kc", "fao56_table12", low=0.20, high=0.40,
                             note="FAO-56 Table 12 leaves the maize Kc ini cell blank; the cereals group row gives "
                                  "Kc ini 0.3 (re-checked 2026-11-14), used here. Range 0.2-0.4 kept (ours)."),
               "mid": lookup(1.20, "Kc", "fao56_table12", note="Spec B4.1 quote: Maize field (grain) mid 1.20"),
               "end": assumed(1.00, "Kc", low=0.85, high=1.05,
                              note="U (spec B4.1): silage harvested before end stage, Kc ~1.0 at harvest. "
                                   "Grain maize end 0.60-0.35 (V) does not apply.")},
        "stage_lengths_days": {"ini": 30, "dev": 40, "mid": 50, "late": 30, "verified": True,
                               "source": "fao56_table11 Maize (grain) April, Spain/Calif. 30/40/50/30 = 150 d (V, "
                                         "re-checked 2026-11-14); scaled to the 110-d silage season in the calendar "
                                         "(scaling U). Replaces the earlier 20/35/40/15 placeholder (U)",
                               "url": src("fao56_table11")["url"]},
        "cover_by_stage": cover_stage(0.1, 0.6, 1.0, 0.9),
        "ratings_0_4": {**ratings(1, 1, 0, 0, 1, 1, 4, 1, 1, 1),
                        "forage_harvest_value": assumed(4, "rating_0_4", low=4, high=4,
                                                        note="Spec B4.2: silage corn rating 4 (stated by spec; not cited)")},
        "root_depth_class": root_class(1),
        "yield_range": assumed(25000, "kg DM/ha", low=20000, high=30000,
                               note="Spec B4.2: silage corn 20-30 t DM/ha (U: cite UC/NASS county yields)"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat poorly drained"],
                                "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "04-15", "end": "06-15", "best": "May (U)", "verified": False,
                           "source": "assumed", "url": src("assumed")["url"]},
        "pest_notes": [], "cautions": [], "seed_cost_per_ha": seed(250, 180, 350), "needs_drill": False,
        "explainer_card": None, "sources": [src("fao56_table12")],
    },
    {
        "id": "winter_wheat", "name": "Winter wheat (grain)", "family": "Poaceae",
        "role": ["cash"], "legume": False, "perennial": False, "root": "fibrous, medium", "market_class": "sell",
        "kc": {"ini": lookup(0.70, "Kc", "fao56_table12", note="Spec B4.1 quote: Winter wheat non-frozen soils 0.7 / 1.15 / 0.25-0.4"),
               "mid": lookup(1.15, "Kc", "fao56_table12"),
               "end": lookup(0.325, "Kc", "fao56_table12", low=0.25, high=0.40, note="Range quoted; value = midpoint")},
        "stage_lengths_days": {"ini": 20, "dev": 60, "mid": 70, "late": 30, "verified": True,
                               "source": "fao56_table11 Winter wheat December California (V)",
                               "url": src("fao56_table11")["url"]},
        "cover_by_stage": cover_stage(0.1, 0.6, 1.0, 0.7),
        "ratings_0_4": ratings(3, 2, 3, 0, 3, 2, 0, 2, 1, 2),
        "root_depth_class": root_class(1),
        "yield_range": assumed(6500, "kg/ha", low=5000, high=8000, note="Grain yield placeholder (U)"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat poorly drained",
                                          "poorly drained"], "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "11-01", "end": "12-31", "best": "December (FAO-56 Table 11 Calif.)",
                           "verified": True, "source": "fao56_table11", "url": src("fao56_table11")["url"]},
        "pest_notes": [], "cautions": [], "seed_cost_per_ha": seed(80, 50, 120), "needs_drill": True,
        "explainer_card": None, "sources": [src("fao56_table12"), src("fao56_table11")],
    },
    {
        "id": "small_grain_silage", "name": "Winter small-grain silage (triticale/wheat)", "family": "Poaceae",
        "role": ["forage"], "legume": False, "perennial": False, "root": "fibrous, medium", "market_class": "feed",
        "kc": {"ini": assumed(0.70, "Kc", low=0.60, high=0.80, note="Spec B4.1: winter triticale -> winter wheat values (assumed +/-0.1)"),
               "mid": assumed(1.15, "Kc", low=1.05, high=1.25, note="Spec B4.1: winter wheat values (assumed +/-0.1)"),
               "end": assumed(0.325, "Kc", low=0.15, high=0.50,
                              note="Wheat end 0.25-0.40 widened +/-0.1 (assumed). Silage is cut before maturity, so the "
                                   "true Kc at harvest is likely higher (doubt).")},
        "stage_lengths_days": {"ini": 20, "dev": 60, "mid": 70, "late": 30, "verified": False,
                               "source": STAGE_U + ": borrowed from FAO-56 winter wheat December California and scaled "
                                                   "to a late-Oct planting / April silage cut",
                               "url": src("assumed")["url"]},
        "cover_by_stage": cover_stage(0.1, 0.6, 1.0, 0.8),
        "ratings_0_4": ratings(3, 2, 1, 0, 3, 2, 3, 2, 1, 2),
        "root_depth_class": root_class(1),
        "yield_range": assumed(11000, "kg DM/ha", low=8000, high=14000, note="Placeholder (U)"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat poorly drained",
                                          "poorly drained"], "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "10-01", "end": "11-30", "best": "Oct-Nov (U)", "verified": False,
                           "source": "assumed", "url": src("assumed")["url"]},
        "pest_notes": [], "cautions": [], "seed_cost_per_ha": seed(80, 50, 120), "needs_drill": True,
        "explainer_card": None, "sources": [src("fao56_table12")],
    },
    {
        "id": "sorghum_sudan", "name": "Sorghum-sudangrass (summer forage, multi-cut)", "family": "Poaceae",
        "role": ["forage"], "legume": False, "perennial": False, "root": "fibrous, deep-ish", "market_class": "feed",
        "kc": {"ini": lookup(0.50, "Kc", "fao56_table12", note="Spec B4.1 quote: Sudan grass hay averaged 0.50 / 0.90 / 0.85"),
               "mid": lookup(0.90, "Kc", "fao56_table12"),
               "end": lookup(0.85, "Kc", "fao56_table12")},
        "stage_lengths_days": {"ini": 25, "dev": 25, "mid": 15, "late": 10, "verified": True,
                               "source": "fao56_table11 Sudan first cutting cycle 25/25/15/10 (V); later cycles "
                                         "(mid stretched to the terminate date) are U",
                               "url": src("fao56_table11")["url"]},
        "cover_by_stage": cover_stage(0.1, 0.6, 0.9, 0.8),
        "ratings_0_4": ratings(3, 3, 2, 0, 2, 2, 3, 3, 1, 3),
        "root_depth_class": root_class(1),
        "yield_range": assumed(14000, "kg DM/ha", low=10000, high=18000, note="Placeholder (U)"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat poorly drained"],
                                "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "04-15", "end": "06-30", "best": "May (U)", "verified": False,
                           "source": "assumed", "url": src("assumed")["url"]},
        "pest_notes": [], "cautions": ["prussic acid/nitrate in young regrowth (U)"],
        "seed_cost_per_ha": seed(60, 40, 100), "needs_drill": True, "explainer_card": "drought_tolerant",
        "sources": [src("fao56_table12"), src("fao56_table11")],
    },
    {
        "id": "safflower", "name": "Safflower", "family": "Asteraceae",
        "role": ["cash"], "legume": False, "perennial": False, "root": "deep taproot", "market_class": "sell",
        "kc": {"ini": assumed(0.35, "Kc", low=0.25, high=0.45, note="U: spec B4.1 says safflower ini is U",
                              to_cite="FAO-56 Table 12 safflower entry"),
               "mid": lookup(1.075, "Kc", "fao56_table12", low=1.0, high=1.15,
                             note="Spec B4.1 quote: Safflower mid 1.0-1.15, end 0.25; value = midpoint"),
               "end": lookup(0.25, "Kc", "fao56_table12")},
        "stage_lengths_days": {"ini": 20, "dev": 35, "mid": 45, "late": 25, "verified": True,
                               "source": "fao56_table11 Safflower April California (V)",
                               "url": src("fao56_table11")["url"]},
        "cover_by_stage": cover_stage(0.1, 0.5, 0.9, 0.6),
        "ratings_0_4": ratings(1, 1, 1, 0, 2, 3, 0, 1, 0, 3),
        "root_depth_class": root_class(2),
        "yield_range": assumed(2800, "kg/ha", low=2000, high=3500, note="Seed yield placeholder (U)"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat poorly drained"],
                                "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "03-15", "end": "04-30", "best": "April (FAO-56 Table 11 Calif.)",
                           "verified": True, "source": "fao56_table11", "url": src("fao56_table11")["url"]},
        "pest_notes": [], "cautions": ["often grown on stored soil water with 0-1 irrigations (U)"],
        "seed_cost_per_ha": seed(40, 25, 70), "needs_drill": True, "explainer_card": "deep_rooting",
        "sources": [src("fao56_table12"), src("fao56_table11")],
    },
    {
        "id": "cereal_vetch_cover", "name": "Winter cover: cereal + vetch mix", "family": "Poaceae+Fabaceae",
        "families": ["Poaceae", "Fabaceae"],
        "role": ["cover"], "legume": True, "perennial": False, "root": "fibrous + taproot", "market_class": "none",
        "kc": {"ini": assumed(0.40, "Kc", low=0.30, high=0.70,
                              note="Spec B4.1: vetch cover -> clover hay values 0.40/0.90/0.85 (assumed). Range widened "
                                   "toward winter-wheat values for the cereal share (assumed)."),
               "mid": assumed(0.90, "Kc", low=0.80, high=1.15, note="As above (assumed)"),
               "end": assumed(0.85, "Kc", low=0.75, high=0.95, note="As above (assumed)")},
        "stage_lengths_days": {"ini": 30, "dev": 60, "mid": 50, "late": 10, "verified": False,
                               "source": STAGE_U + ": winter-sown cover, mid stretched to termination",
                               "url": src("assumed")["url"]},
        "cover_by_stage": cover_stage(0.1, 0.5, 0.9, 0.8),
        "ratings_0_4": ratings(4, 3, 2, 2, 3, 2, 1, 3, 1, 1),
        "root_depth_class": root_class(1),
        "yield_range": assumed(None, "kg DM/ha", low=None, high=None, note="Not harvested; no yield"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat poorly drained",
                                          "poorly drained"], "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "10-01", "end": "11-30", "best": "after rice straw chop (U)", "verified": False,
                           "source": "assumed", "url": src("assumed")["url"],
                           "note": "Species and seeding after rice are U (spec B1: UC trials exist, results not located)"},
        "pest_notes": [], "cautions": ["termination timing before rice field prep (U)"],
        "seed_cost_per_ha": seed(120, 70, 180), "needs_drill": True, "explainer_card": "cover_crop",
        "sources": [src("fao56_table12"), src("covercrop_selector")],
    },
    {
        "id": "fallow_bare", "name": "Fallow / bare soil", "family": "none",
        "role": ["fallow"], "legume": False, "perennial": False, "root": "none", "market_class": "none",
        "kc": {"ini": assumed(0.15, "Kc", low=0.10, high=0.30,
                              note="Spec B4.1: bare Kc 0.15 (U). Range is ours (U); wet winter bare soil likely "
                                   "evaporates more than 0.15 x ETo (doubt)."),
               "mid": assumed(0.15, "Kc", low=0.10, high=0.30, note="Constant"),
               "end": assumed(0.15, "Kc", low=0.10, high=0.30, note="Constant")},
        "stage_lengths_days": None,
        "cover_by_stage": cover_stage(0.0, 0.0, 0.0, 0.0, note="Bare"),
        "ratings_0_4": {k: assumed(0, "rating_0_4", low=0, high=0, note="Bare soil") for k in
                        ratings(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        "root_depth_class": assumed(0, "class_0_2", low=0, high=0, note="Bare"),
        "yield_range": assumed(None, "kg/ha", low=None, high=None, note="No yield"),
        "drainage_classes_ok": {"value": ["any"], "method": "assumed", "verified": False, "note": ""},
        "seeding_window": None, "pest_notes": [], "cautions": [], "seed_cost_per_ha": seed(0, 0, 0),
        "needs_drill": False, "explainer_card": None, "sources": [],
    },
    {
        "id": "open_water_flood", "name": "Flooded field (winter flood / pre-seeding flood)", "family": "none",
        "role": ["water"], "legume": False, "perennial": False, "root": "none", "market_class": "none",
        "kc": {"ini": assumed(1.05, "Kc", low=1.00, high=1.10,
                              note="U. FAO-56 Table 12 has an open-water entry, but the spec does not quote it, "
                                   "so it is unverified here."),
               "mid": assumed(1.05, "Kc", low=1.00, high=1.10, note="Constant"),
               "end": assumed(1.05, "Kc", low=1.00, high=1.10, note="Constant")},
        "stage_lengths_days": None,
        "cover_by_stage": cover_stage(0.0, 0.0, 0.0, 0.0, note="Water surface: not cover, not bare (spec B5.1/B5.4)"),
        "ratings_0_4": {k: assumed(0, "rating_0_4", low=0, high=0, note="Not a crop") for k in
                        ratings(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        "root_depth_class": assumed(0, "class_0_2", low=0, high=0, note="Not a crop"),
        "yield_range": assumed(None, "kg/ha", low=None, high=None, note="No yield"),
        "drainage_classes_ok": {"value": ["any"], "method": "assumed", "verified": False, "note": ""},
        "seeding_window": None, "pest_notes": [],
        "cautions": ["flood fill depth and seepage water are not modelled (U); habitat value not scored"],
        "seed_cost_per_ha": seed(0, 0, 0), "needs_drill": False, "explainer_card": None, "sources": [],
    },
]


# ---------------------------------------------------------------- BC crops (bc_salmon_river_forage)
# Designs: docs/handoff-bc.md "BC rotations to add (Appendix A, sources read)". lookup()/V only for numbers
# quoted from a source that was read (FAO-56 Tables 11/12, Kamloops Forage Manual, BC Drought Factsheet No. 6,
# BF04, ECCC -4 C dates); everything else is assumed()/U.
def seed_bc(v, lo, hi):
    return assumed(v, "USD/ha", low=lo, high=hi,
                   note="Placeholder order of magnitude only (USD for consistency with the CA records); no cited "
                        "source. Income is not computed for BC.",
                   to_cite="a BC forage enterprise budget (not located)")


ALF_BC_STAGES = {"ini": 176, "dev": 30, "mid": 129, "late": 30}   # sums to 365 (1-year steady state)
ALF_BC_STAGE_SRC = ("FAO-56 Table 11 alfalfa total season 'last -4 C in spring until first -4 C in fall', init 10, "
                    "dev 30 (V); -4 C dates from ECCC Silver Creek 1991-2021, last spring day 100 (10 Apr), first "
                    "fall day 299 (26 Oct) (V, computed); ini = 166 dormant days + FAO init 10; the mid 129 / late 30 "
                    "split is assumed (U)")

CROPS_BC = [
    {
        "id": "alfalfa_hay_bc", "name": "Alfalfa hay, 2 cuts, irrigated (Shuswap)", "family": "Fabaceae",
        "role": ["forage"], "legume": True, "perennial": True, "root": "deep taproot", "market_class": "either",
        "kc": {"ini": lookup(0.40, "Kc", "fao56_table12", note="FAO-56 Table 12 alfalfa hay, averaged cutting effects "
                             "0.40 / 0.95 / 0.90. The ini value also covers the dormant winter (U)."),
               "mid": lookup(0.95, "Kc", "fao56_table12"),
               "end": lookup(0.90, "Kc", "fao56_table12")},
        "stage_lengths_days": {**ALF_BC_STAGES, "verified": False, "source": ALF_BC_STAGE_SRC,
                               "url": src("fao56_table11")["url"]},
        "cover_by_stage": cover_stage(0.6, 0.8, 0.85, 0.8,
                                      note="U. Same as the CA alfalfa record: dormant crowns + stubble (often under "
                                           "snow) assumed >= 0.5 cover; mid is a 2-cut average."),
        "ratings_0_4": {**ratings(3, 3, 1, 4, 2, 3, 4, 2, 1, 3), "forage_harvest_value": r(4, 3, 4)},
        "root_depth_class": root_class(2),
        "yield_range": assumed(6900, "kg DM/ha/yr", low=5000, high=8500,
                               note="Kamloops District Forage Manual 2-cut budget 2.0 + 1.5 = 3.5 ton/acre hay (V) "
                                    "x 2242 kg/ha per ton/acre x 88% DM (assumed) = ~6,900 kg DM/ha; Kamloops "
                                    "district applied to the Shuswap (assumed); range ours (U)",
                               to_cite=src("kamloops_forage_manual")["url"]),
        "water_use_quoted": lookup(914, "mm/season", "bc_drought_factsheet6",
                                   note="'about 36 inches' for full-season alfalfa (36 in x 25.4); a 3-cut reference, "
                                        "so a 2-cut stand should need less. Sanity reference only, not a model input"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat excessively drained"],
                                "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "05-01", "end": "08-20", "best": "spring, or mid-Aug with irrigation (U)",
                           "verified": False, "source": "assumed", "url": src("assumed")["url"]},
        "pest_notes": [], "cautions": [],
        "seed_cost_per_ha": seed_bc(300, 200, 450), "needs_drill": True, "explainer_card": "nitrogen_fixing",
        "sources": [src("fao56_table12"), src("fao56_table11"), src("kamloops_forage_manual"),
                    src("eccc_frost_dates")],
    },
    {
        "id": "barley_silage_bc", "name": "Barley silage (spring-sown, ~100 days)", "family": "Poaceae",
        "role": ["forage"], "legume": False, "perennial": False, "root": "fibrous, medium", "market_class": "feed",
        "kc": {"ini": lookup(0.30, "Kc", "fao56_table12", note="FAO-56 Table 12 barley 0.3 / 1.15 / 0.25"),
               "mid": lookup(1.15, "Kc", "fao56_table12"),
               "end": lookup(0.25, "Kc", "fao56_table12",
                             note="Grain-barley end value. Silage is cut before full senescence, so the true Kc at "
                                  "harvest is likely higher (doubt).")},
        "stage_lengths_days": {"ini": 20, "dev": 25, "mid": 60, "late": 30, "verified": True,
                               "source": "fao56_table11 Barley 35-45 deg latitude, Mar/Apr planting 20/25/60/30 (V); "
                                         "scaled to the 96-d silage season (1 May - 5 Aug) and applied at 50.6 N (U)",
                               "url": src("fao56_table11")["url"]},
        "cover_by_stage": cover_stage(0.1, 0.6, 1.0, 0.9),
        "ratings_0_4": ratings(2, 2, 1, 0, 2, 2, 3, 2, 1, 2),
        "root_depth_class": root_class(1),
        "yield_range": assumed(7800, "kg DM/ha", low=5500, high=9000,
                               note="BC Drought Factsheet No. 6: '3 to 4 ton/acre' barley silage (V) = 6,700-9,000 "
                                    "kg/ha; read as dry matter (assumed); low end widened (U)",
                               to_cite=src("bc_drought_factsheet6")["url"]),
        "water_use_quoted": lookup(381, "mm/season", "bc_drought_factsheet6",
                                   note="'one crop of barley silage may only require about 15 inches of water for a 3 "
                                        "to 4 ton/acre yield' (15 in x 25.4). Sanity reference only, not a model input"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat poorly drained"],
                                "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "04-15", "end": "05-31", "best": "early May (U)", "verified": False,
                           "source": "assumed", "url": src("assumed")["url"]},
        "pest_notes": [], "cautions": [], "seed_cost_per_ha": seed_bc(80, 50, 120), "needs_drill": True,
        "explainer_card": None, "sources": [src("fao56_table12"), src("fao56_table11"), src("bc_drought_factsheet6")],
    },
    {
        "id": "fall_cereal_silage_bc", "name": "Fall rye / triticale silage (fall-sown, cut before heading)",
        "family": "Poaceae",
        "role": ["forage"], "legume": False, "perennial": False, "root": "fibrous, medium", "market_class": "feed",
        "kc": {"ini": lookup(0.40, "Kc", "fao56_table12",
                             note="FAO-56 Table 12 winter wheat with frozen soils 0.4 / 1.15 / 0.25-0.4, used for "
                                  "fall rye/triticale (the crop transfer is U)"),
               "mid": lookup(1.15, "Kc", "fao56_table12"),
               "end": lookup(0.325, "Kc", "fao56_table12", low=0.25, high=0.40,
                             note="Range quoted; value = midpoint. Unused: the calendar cuts before heading (late 0)")},
        "stage_lengths_days": {"ini": 160, "dev": 75, "mid": 75, "late": 25, "verified": True,
                               "source": "fao56_table11 Winter wheat Idaho October 160/75/75/25 (V); the BC calendar "
                                         "overrides to ini 205 / dev 55 / mid 24 / late 0 for a 25 Aug seeding cut "
                                         "5 June before heading (U)",
                               "url": src("fao56_table11")["url"]},
        "cover_by_stage": cover_stage(0.5, 0.7, 0.95, 0.9,
                                      note="U. Late-Aug seeding tillers before freeze-up; ini 0.5 sits on the exposure "
                                           "threshold, so the winter counts as covered (at 0.4 it would count as "
                                           "exposed)."),
        "ratings_0_4": ratings(4, 2, 1, 0, 3, 2, 3, 3, 1, 3),
        "root_depth_class": root_class(1),
        "yield_range": assumed(6000, "kg DM/ha", low=4000, high=8000,
                               note="Placeholder (U): no BC yield for a spring silage cut was read"),
        "drainage_classes_ok": {"value": ["well drained", "moderately well drained", "somewhat poorly drained",
                                          "poorly drained"], "method": "assumed", "verified": False, "note": "U"},
        "seeding_window": {"start": "08-15", "end": "09-30", "best": "late Aug (U)", "verified": False,
                           "source": "assumed", "url": src("assumed")["url"],
                           "note": "Needs fall moisture to establish (BC Drought Factsheet No. 6, V); dates U"},
        "pest_notes": [], "cautions": ["harvest before heading (BC Drought Factsheet No. 6)",
                                       "needs fall moisture to establish: late-Aug water may be unavailable in an "
                                       "order year (U)"],
        "seed_cost_per_ha": seed_bc(80, 50, 120), "needs_drill": True, "explainer_card": "drought_tolerant",
        "sources": [src("fao56_table12"), src("fao56_table11"), src("bc_drought_factsheet6")],
    },
    {
        "id": "sainfoin_grass_bc", "name": "Sainfoin + meadow brome hay, dryland, 1 cut", "family": "Fabaceae+Poaceae",
        "families": ["Fabaceae", "Poaceae"],
        "role": ["forage"], "legume": True, "perennial": True, "root": "deep taproot + fibrous",
        "market_class": "either",
        "kc": {"ini": assumed(0.40, "Kc", low=0.30, high=0.50,
                              note="Proxy (assumed): FAO-56 Table 12 clover hay, averaged cutting effects 0.40 / 0.90 "
                                   "/ 0.85; FAO-56 has no sainfoin entry. Range ours (U)",
                              to_cite=src("fao56_table12")["url"]),
               "mid": assumed(0.90, "Kc", low=0.80, high=1.00, note="As above (proxy, assumed)"),
               "end": assumed(0.85, "Kc", low=0.75, high=0.95, note="As above (proxy, assumed)")},
        "stage_lengths_days": {**ALF_BC_STAGES, "verified": False,
                               "source": "assumed (U): the alfalfa_hay_bc season (" + ALF_BC_STAGE_SRC + ")",
                               "url": src("assumed")["url"]},
        "cover_by_stage": cover_stage(0.6, 0.8, 0.85, 0.75,
                                      note="U. Established perennial stand; dryland regrowth after the July cut is "
                                           "limited."),
        "ratings_0_4": ratings(3, 3, 2, 3, 2, 3, 3, 2, 0, 4),
        "root_depth_class": root_class(2),
        "yield_range": assumed(2500, "kg DM/ha/yr", low=1500, high=4000,
                               note="Placeholder (U); BF04 gives 1 cut dryland (V) but no Shuswap yield"),
        "drainage_classes_ok": {"value": ["well drained", "somewhat excessively drained", "excessively drained"],
                                "method": "assumed", "verified": False,
                                "note": "BF04: lighter, well-drained soils, no wet feet (V); class list ours (U)"},
        "seeding_window": {"start": "05-01", "end": "06-30", "best": "spring (U)", "verified": False,
                           "source": "assumed", "url": src("assumed")["url"]},
        "pest_notes": [],
        "cautions": ["needs lighter, well-drained soil with no wet feet (BF04); check the SoilGrids texture",
                     "BF04 was written for northern BC (Bulkley-Nechako, Fraser-Fort George); its use in the "
                     "Shuswap is assumed"],
        "seed_cost_per_ha": seed_bc(250, 150, 400), "needs_drill": True, "explainer_card": "drought_tolerant",
        "sources": [src("bf04_nonbloat_legumes"), src("fao56_table12")],
    },
]
CROPS = CROPS + CROPS_BC

# ---------------------------------------------------------------- strategies
RICE_T = "uc_rice_blog (V avg: 50% planted by 12 May; 145-150 d); end = plant + FAO-56 Table 11 150 d"
U_T = "assumed (U)"


def e(year, crop_id, start, end, role, *, irrigated, timing_source, harvest_months=(), stage_mode="fixed",
      flooded_until=None, stage_override=None, cover_override=None, note="", season_boundary=False):
    d = {"year": year, "crop_id": crop_id, "plant": start, "harvest": end, "role": role, "irrigated": irrigated,
         "harvest_months": list(harvest_months), "stage_mode": stage_mode, "timing_source": timing_source}
    if season_boundary:   # an established stand's season start, not a seeding (skips the seeding-window check)
        d["season_boundary"] = True
    if flooded_until:
        d["flooded_until"] = flooded_until
    if stage_override:
        d["stage_override"] = stage_override
    if cover_override:
        d["cover_override"] = cover_override
    if note:
        d["note"] = note
    return d


RICE = lambda y=1: e(y, "rice_medium_grain", "05-10", "10-07", "cash", irrigated=True, timing_source=RICE_T,
                     harvest_months=[10], flooded_until="09-07",
                     note="Paddy flooded from seeding to drain ~30 d before harvest (drain date U)")
SPRING_FLOOD = lambda y=1: e(y, "open_water_flood", "04-25", "05-10", "water", irrigated=True,
                             timing_source="spec B1 calendar 'flood, water-seed late Apr-May' (V month); day U")
SMALL_GRAIN = lambda y=1: e(y, "small_grain_silage", "10-25", "04-20", "forage", irrigated=True, stage_mode="scale",
                            timing_source="spec B1 CAF calendar: drill Oct-Nov, silage harvest Apr-May (U)",
                            harvest_months=[4])

STRATEGIES = [
    {"id": "car0_rice_winterflood", "location_id": "car_colusa_rice", "is_baseline": True, "cycle_years": 1,
     "name": "Continuous rice with winter flood (current)",
     "calendar": [
         e(1, "open_water_flood", "11-01", "02-01", "water", irrigated=True, timing_source=U_T,
           note="Winter flood for straw decomposition / waterfowl; flood dates U. Only ET is counted as need."),
         SPRING_FLOOD(), RICE()],
     "allocation_rule": None},
    {"id": "car1_rice_wintercover", "location_id": "car_colusa_rice", "is_baseline": False, "cycle_years": 1,
     "name": "Rice + winter cover (cereal/vetch) instead of winter flood",
     "calendar": [
         SPRING_FLOOD(), RICE(),
         e(1, "cereal_vetch_cover", "10-25", "03-20", "cover", irrigated=False, stage_mode="stretch_mid",
           timing_source=U_T + ": drill after straw chop; terminate before field prep",
           note="Rainfed cover; ETc counted but not irrigation need")],
     "allocation_rule": None},
    {"id": "car2_dryyear_safflower", "location_id": "car_colusa_rice", "is_baseline": False, "cycle_years": 1,
     "name": "Dry-year plan: safflower instead of rice (allocation < 50%)",
     "calendar": [
         e(1, "cereal_vetch_cover", "01-01", "03-01", "cover", irrigated=False, stage_mode="truncate",
           timing_source=U_T + ": cover sown the previous fall (spec 'cover/bare' Jan-Feb)",
           stage_override={"ini": 0, "dev": 0, "mid": 59, "late": 1},
           note="Carried over from the previous (rice) year; modelled at full cover"),
         e(1, "safflower", "04-01", "08-04", "cash", irrigated=True, harvest_months=[8],
           timing_source="fao56_table11 Safflower April California 20/35/45/25 (V); spec calendar says harvest "
                         "July (U), FAO lengths give early Aug",
           note="Marked irrigated; the I formula has no stored-soil-water term, so I is likely an upper bound")],
     "allocation_rule": {"text": "Use this plan when surface-water allocation is below 50% of contract",
                         "threshold_pct_of_contract": {"value": 50, "unit": "%", "low": 50, "high": 50,
                                                       "method": "assumed", "source": src("assumed"),
                                                       "note": "Spec B1 CAR2 trigger (U)"}}},
    {"id": "car3_rice_wheat", "location_id": "car_colusa_rice", "is_baseline": False, "cycle_years": 2,
     "name": "Rice - winter wheat rotation (2-year)",
     "calendar": [
         SPRING_FLOOD(1), RICE(1),
         e(1, "winter_wheat", "12-01", "05-30", "cash", irrigated=True, harvest_months=[6],
           timing_source="fao56_table11 Winter wheat December California 20/60/70/30 (V); spec says harvest June (U)",
           note="Sacramento Valley wheat is often rain-fed or 1-2 irrigations (U); I is an upper bound")],
     "calendar_note": "Spec B1 shows only the wheat year (wheat Jan-May, bare Jul-Oct, drill wheat Nov-Dec). We model "
                      "a 2-year cycle: year 1 rice then wheat drilled 1 Dec; year 2 wheat to 30 May, bare until "
                      "the next rice flood. Confirm with the team.",
     "allocation_rule": None},
    {"id": "caf0_alfalfa", "location_id": "caf_tulare_forage", "is_baseline": True, "cycle_years": 1,
     "name": "Alfalfa hay, 7-8 cuts, 4-5 year stand (current)",
     "calendar": [
         e(1, "alfalfa_hay", "12-01", "12-01", "forage", irrigated=True, harvest_months=[3, 4, 5, 6, 7, 8, 9, 10],
           timing_source="uc_alfalfa (V: 28-day cutting schedule); stage dates read off spec B1 calendar (U)",
           note="Established stand in steady state; establishment year not modelled")],
     "allocation_rule": None},
    {"id": "caf1_smallgrain_corn", "location_id": "caf_tulare_forage", "is_baseline": False, "cycle_years": 1,
     "name": "Winter small-grain silage + silage corn double crop",
     "calendar": [
         SMALL_GRAIN(),
         e(1, "silage_corn", "05-05", "08-23", "forage", irrigated=True, harvest_months=[8], stage_mode="scale",
           timing_source=U_T + ": spec B1 'plant corn May, harvest Aug-Sept'; FAO-56 Table 11 maize stages scaled "
                               "to the 110-d season (FAO-56 advises scaling stage lengths to the local season)")],
     "allocation_rule": None},
    {"id": "caf2_smallgrain_sorghumsudan", "location_id": "caf_tulare_forage", "is_baseline": False,
     "cycle_years": 1, "name": "Winter small-grain silage + sorghum-sudan summer forage",
     "calendar": [
         SMALL_GRAIN(),
         e(1, "sorghum_sudan", "05-05", "09-15", "forage", irrigated=True, harvest_months=[6, 7, 8],
           stage_mode="stretch_mid", timing_source=U_T + ": spec B1 'plant May, cuts Jun-Aug, terminate Sept'")],
     "allocation_rule": None},
    {"id": "caf3_alfalfa_break", "location_id": "caf_tulare_forage", "is_baseline": False, "cycle_years": 4,
     "name": "Alfalfa 3-year stand, winter cereal break year, re-seed",
     "calendar": [
         e(4, "alfalfa_hay", "09-20", "12-01", "establishing", irrigated=True, stage_mode="truncate",
           stage_override={"ini": 30, "dev": 42, "mid": 0, "late": 0},
           cover_override={"ini": 0.1, "dev": 0.5, "mid": 0.5, "late": 0.5},
           timing_source="uc_alfalfa (V window mid-Sept-Oct); establishment stages U"),
         e(4, "alfalfa_hay", "12-01", "12-01", "forage", irrigated=True, harvest_months=[3, 4, 5, 6, 7, 8, 9, 10],
           timing_source="as CAF0 (U stage dates)", note="Stand year 1"),
         e(1, "alfalfa_hay", "12-01", "12-01", "forage", irrigated=True, harvest_months=[3, 4, 5, 6, 7, 8, 9, 10],
           timing_source="as CAF0 (U stage dates)", note="Stand year 2"),
         e(2, "alfalfa_hay", "12-01", "11-01", "forage", irrigated=True, harvest_months=[3, 4, 5, 6, 7, 8, 9, 10],
           stage_mode="truncate", timing_source="as CAF0; stand removed after the Oct cut (U)", note="Stand year 3"),
         e(3, "small_grain_silage", "11-01", "04-20", "forage", irrigated=True, stage_mode="scale",
           harvest_months=[4], timing_source="spec B1 CAF3: cereal Jan-Apr, harvest silage Apr (U)"),
     ],
     "calendar_note": "Cycle = 3 alfalfa production years + 1 break year (cereal to April, unirrigated summer fallow "
                      "May-Aug, re-seed 20 Sept). Year numbering wraps: the stand seeded in year 4 produces in "
                      "years 1-3 (labelled by the year its Dec-Nov season starts).",
     "allocation_rule": None},
]

# ---------------------------------------------------------------- BC strategies (bc_salmon_river_forage)
BC = "bc_salmon_river_forage"
KAM = "kamloops_forage_manual (V: 2 cuts typical in Zone 2, aftermath grazed late fall)"
ALF_BC = lambda y, start="10-26", end="10-26", note="", stage_mode="fixed": e(
    y, "alfalfa_hay_bc", start, end, "forage", irrigated=True, harvest_months=[6, 8], stage_mode=stage_mode,
    stage_override=dict(ALF_BC_STAGES), season_boundary=True,
    timing_source=KAM + "; cut months Jun/Aug and the stage split U; season = -4 C to -4 C (FAO-56 Table 11, ECCC)",
    note=note)

STRATEGIES_BC = [
    {"id": "bc0_alfalfa", "location_id": BC, "is_baseline": True, "cycle_years": 1,
     "name": "Irrigated alfalfa hay, 2 cuts, 5-year stand (current)", "short_name": "Alfalfa (current)",
     "calendar": [ALF_BC(1, note="Established stand in steady state; establishment year not modelled. Late-fall "
                                 "aftermath grazing not modelled")],
     "calendar_note": "Kamloops District Forage Manual system 1: continuous alfalfa, 5-year cycle, 20% reseeded each "
                      "year (V). Modelled as one established stand in steady state.",
     "allocation_rule": None},
    {"id": "bc1_barley_break", "location_id": BC, "is_baseline": False, "cycle_years": 5,
     "name": "Alfalfa with a barley-silage break year (5-year cycle)", "short_name": "Barley break",
     "calendar": [
         e(1, "barley_silage_bc", "05-01", "08-05", "forage", irrigated=True, harvest_months=[8], stage_mode="scale",
           timing_source="bc_drought_factsheet6 (V: barley silage ~100 days); FAO-56 Table 11 barley 20/25/60/30 "
                         "scaled to 96 d; dates U (harvested before a mid-August order)"),
         e(1, "alfalfa_hay_bc", "08-15", "10-26", "establishing", irrigated=True, stage_mode="truncate",
           stage_override={"ini": 30, "dev": 42, "mid": 0, "late": 0},
           cover_override={"ini": 0.1, "dev": 0.5, "mid": 0.5, "late": 0.5},
           timing_source="assumed (U): late-summer reseeding after the barley; establishment stages as CAF3 (U)"),
         ALF_BC(1, note="Stand year 1"), ALF_BC(2, note="Stand year 2"), ALF_BC(3, note="Stand year 3"),
         ALF_BC(4, note="Stand year 4"),
         e(5, "alfalfa_hay_bc", "10-26", "04-20", "forage", irrigated=False, stage_mode="truncate",
           stage_override=dict(ALF_BC_STAGES), season_boundary=True,
           timing_source="assumed (U): old stand dormant over winter, terminated in spring before the barley",
           note="Old stand, dormant; no cut"),
     ],
     "calendar_note": "Kamloops District Forage Manual system 2: a five-year cycle with part of the new seeding area "
                      "in annual crops such as barley (V). Year 1: barley silage 1 May - 5 Aug, alfalfa reseeded 15 Aug; "
                      "4 production years; the old stand is terminated the next spring. The late-summer seeding "
                      "needs August water, which an order year (16 Aug 2023) would not allow.",
     "allocation_rule": None},
    {"id": "bc2_fall_cereal_silage", "location_id": BC, "is_baseline": False, "cycle_years": 5,
     "name": "Alfalfa with a fall rye/triticale silage year (5-year cycle)", "short_name": "Fall rye silage",
     "calendar": [
         e(5, "fall_cereal_silage_bc", "08-25", "06-05", "forage", irrigated=True, harvest_months=[6],
           stage_override={"ini": 205, "dev": 55, "mid": 24, "late": 0},
           timing_source="bc_drought_factsheet6 (V: fall rye/triticale, harvest before heading); FAO-56 Table 11 "
                         "winter wheat Idaho Oct 160/75/75/25 adapted to ini 205 / dev 55 / mid 24 (U); dates U",
           note="Spring growth mostly on stored moisture and spring rain; establishment in late Aug needs water"),
         e(1, "alfalfa_hay_bc", "06-15", "10-26", "establishing", irrigated=True,
           stage_override={"ini": 30, "dev": 42, "mid": 61, "late": 0},
           cover_override={"ini": 0.1, "dev": 0.6, "mid": 0.8, "late": 0.8},
           timing_source="assumed (U): reseeded after the June silage cut; no seeding-year cut modelled"),
         ALF_BC(1, note="Stand year 1"), ALF_BC(2, note="Stand year 2"), ALF_BC(3, note="Stand year 3"),
         ALF_BC(4, "10-26", "08-20", note="Stand year 4: cut twice (Jun, Aug), terminated 20 Aug",
                stage_mode="truncate"),
     ],
     "calendar_note": "One year in five in fall-seeded cereal silage, the 'one fifth of the stand' idea applied to "
                      "one field over time. The last alfalfa year is cut twice and terminated 20 Aug; fall rye or "
                      "triticale 25 Aug - 5 Jun; alfalfa reseeded 15 Jun. Cereals are 'the most commonly grown "
                      "alternative forage crops' under limited irrigation (BC Drought Factsheet No. 6, V).",
     "allocation_rule": None},
    {"id": "bc3_sainfoin_grass", "location_id": BC, "is_baseline": False, "cycle_years": 1,
     "name": "Dryland sainfoin-meadow brome hay, 1 cut", "short_name": "Sainfoin-grass",
     "calendar": [
         e(1, "sainfoin_grass_bc", "10-26", "10-26", "forage", irrigated=False, harvest_months=[7],
           stage_override=dict(ALF_BC_STAGES), season_boundary=True,
           timing_source="bf04_nonbloat_legumes (V: 1 cut per season under dryland); July cut and stages U",
           note="Not irrigated: ETc is the crop's potential use; dryland stands use what rain and soil water allow")],
     "calendar_note": "Sainfoin with a bunchgrass (meadow brome), dryland (BF04, V). Needs lighter, well-drained soil "
                      "with no wet feet: check the SoilGrids texture before relying on this option.",
     "allocation_rule": None},
]
STRATEGIES = STRATEGIES + STRATEGIES_BC


def main():
    (ROOT / "crops.json").write_text(json.dumps({"crops": CROPS}, indent=1))
    (ROOT / "strategies.json").write_text(json.dumps({"strategies": STRATEGIES}, indent=1))
    print("wrote", ROOT / "crops.json", ROOT / "strategies.json")


if __name__ == "__main__":
    main()
