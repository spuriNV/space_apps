"""Paths, presets, crop calendars and small helpers for the AI chunk."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

AI_DIR = Path(__file__).resolve().parents[1]
REPO = AI_DIR.parents[1]
FIELD_DIR = REPO / "backend" / "field"
REGIONAL_DIR = REPO / "backend" / "regional"
CACHE_DIR = REPO / "data" / "cache"
OUT_DIR = AI_DIR / "out"
SCHEMAS = REPO / "schemas"

# Reuse backend/field code (read-only import; nothing in backend/field is modified).
if str(FIELD_DIR) not in sys.path:
    sys.path.insert(0, str(FIELD_DIR))

PRESETS = ["car_colusa_rice", "caf_tulare_forage"]
YEARS = list(range(2016, 2026))
TRAIN_YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2023]  # spec B6.1 split (a)
TEST_YEARS = [2022, 2024, 2025]

# Crop calendar windows for CDL-year-class labels (spec B6.1). Day-of-year boundaries, all U
# (typical Sacramento / San Joaquin Valley timing from the spec's preset calendars, not field records).
#   bare:    list of (start_doy, end_doy) windows labelled bare (water if the scene's water flag is set)
#   covered: list of windows labelled covered
# Anything outside these windows is "uncertain" (the +/-15 day planting/harvest windows) and is not used.
CROP_WINDOWS = {
    61: {"name": "Fallow/Idle Cropland", "bare": [(1, 366)], "covered": []},
    3: {"name": "Rice",  # water-seeded late Apr-May (50% by 12 May); harvest late Sep-Oct
        "bare": [(1, 114), (290, 366)], "covered": [(171, 258)]},
    1: {"name": "Corn",  # SJV silage corn: plant Apr-May, harvest Aug-Sep
        "bare": [(46, 91), (274, 334)], "covered": [(166, 227)]},
    24: {"name": "Winter Wheat",  # drilled Nov-Dec, harvest June
         "bare": [(182, 304)], "covered": [(46, 135)]},
    36: {"name": "Alfalfa", "bare": [], "covered": [(91, 273)]},
    2: {"name": "Cotton", "bare": [(15, 90), (335, 366)], "covered": [(182, 258)]},
    6: {"name": "Sunflower", "bare": [(15, 90), (288, 366)], "covered": [(166, 212)]},
    33: {"name": "Safflower", "bare": [(244, 366)], "covered": [(135, 181)]},
    225: {"name": "Dbl Crop WinWht/Corn", "bare": [], "covered": [(60, 110), (182, 227)]},
}

CLASSES3 = ["bare", "covered", "water"]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    return dt.date.today().isoformat()


def cache(preset: str) -> Path:
    return CACHE_DIR / preset


def ai_cache(preset: str) -> Path:
    p = CACHE_DIR / preset / "ai"
    p.mkdir(parents=True, exist_ok=True)
    return p


def out(preset: str) -> Path:
    p = OUT_DIR / preset
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(p):
    return json.loads(Path(p).read_text())


def write_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, default=str))


def window_label(code: int, doy: int):
    w = CROP_WINDOWS.get(int(code))
    if w is None:
        return None
    if any(a <= doy <= b for a, b in w["bare"]):
        return "bare"
    if any(a <= doy <= b for a, b in w["covered"]):
        return "covered"
    return None
