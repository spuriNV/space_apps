"""Paths, fields, crop calendars, the ModelReport builder and JSON helpers for the AI chunk.

Merged from backend/ai (paths, presets, CDL crop windows) and the `ds` branch library
`field_shift_ai/field_shift_models/fieldshift_models/common.py` by spuriNV (ModelReport builder,
NaN-safe JSON writer). Credit: the ModelReport builder and `_jsonable` follow spuriNV's code.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AI_DIR = Path(__file__).resolve().parents[1]
REPO = AI_DIR.parents[1]
FIELD_DIR = REPO / "backend" / "field"
FIELDS_DIR = REPO / "backend" / "fields"
REGIONAL_DIR = REPO / "backend" / "regional"
ENGINE_DIR = REPO / "backend" / "engine"
CACHE_DIR = REPO / "data" / "cache"
OUT_DIR = AI_DIR / "out"
SCHEMAS = REPO / "schemas"

# Reuse backend/field code (read-only import; nothing in backend/field is modified).
if str(FIELD_DIR) not in sys.path:
    sys.path.insert(0, str(FIELD_DIR))

sys.path.insert(0, str(REPO / "backend" / "fields"))
import fieldreg  # noqa: E402

PRESETS = fieldreg.selected()          # registry fields (FIELDSHIFT_FIELDS limits the list)
TRAINED = ["car_colusa_rice", "caf_tulare_forage"]   # fields with their own training box; the others reuse their family's model
TEMPLATES = {"rice": "car_colusa_rice", "forage": "caf_tulare_forage"}
YEARS = list(range(2016, 2026))          # CDL label years of the training sample
TRAIN_YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2023]  # legacy year split (pre-merge code); see bare_cover.TESTS
TEST_YEARS = [2022, 2024, 2025]
CAL_LAST_YEAR = 2026                     # calendar_ml covers 2016..CAL_LAST_YEAR

# Crop calendar windows for CDL-year-class labels (spec B6.1). Day-of-year boundaries, all U
# (typical Sacramento / San Joaquin Valley timing from the spec's preset calendars, not field records).
#   bare:    windows labelled bare
#   covered: windows labelled covered
# Anything outside these windows ("uncertain": planting/harvest +/- ~15 days) gets no CDL label.
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
PERENNIAL_FORAGE = {36, 37}              # CDL alfalfa, other hay: cuttings are not harvests
CROP_NAME_TO_CODE = {"Rice": 3, "Corn": 1, "Winter Wheat": 24, "Alfalfa": 36, "Cotton": 2, "Sunflower": 6,
                     "Safflower": 33, "Dbl Crop WinWht/Corn": 225, "Fallow/Idle Cropland": 61, "Other Hay/Non Alfalfa": 37}

CLASSES3 = ["bare", "covered", "water"]   # the ML classes (decision: no "partial" label exists)


# ------------------------------------------------------------------ fields
def _fieldreg():
    return fieldreg if (FIELDS_DIR / "registry.json").exists() else None


def field_ids() -> list[str]:
    """Every registry field (limited by FIELDSHIFT_FIELDS, see fieldreg.selected) if backend/fields/registry.json
    exists, else the two presets."""
    fr = _fieldreg()
    return fr.selected() if fr else list(TRAINED)


def family(fid: str) -> str:
    fr = _fieldreg()
    if fr and fr.has(fid):
        return fr.get(fid)["family"]
    return "rice" if fid.startswith("car_") else "forage"


def template(fid: str) -> str:
    """The original preset whose 10 km training sample (and so trained models) this field reuses."""
    return TEMPLATES[family(fid)]


def field_polygon(fid: str):
    from shapely.geometry import shape  # noqa: PLC0415
    fc = read_json(FIELD_DIR / "polygons" / f"{fid}.geojson")
    return shape(fc["features"][0]["geometry"] if "features" in fc else fc.get("geometry", fc))


def crop_history(fid: str) -> dict[int, str]:
    p = FIELD_DIR / "out" / fid / "crop_history.json"
    return {int(y): c for y, c in read_json(p)["by_year"].items()} if p.exists() else {}


# ------------------------------------------------------------------ misc
def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    return dt.date.today().isoformat()


def cache(fid: str) -> Path:
    return CACHE_DIR / fid


def ai_cache(fid: str) -> Path:
    p = CACHE_DIR / fid / "ai"
    p.mkdir(parents=True, exist_ok=True)
    return p


def out(fid: str) -> Path:
    p = OUT_DIR / fid
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(p):
    return json.loads(Path(p).read_text())


def _jsonable(o):
    """NaN/inf -> null, numpy -> python, timestamps -> ISO dates (spuriNV, ds branch)."""
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return [_jsonable(v) for v in o.tolist()]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(o, pd.Timestamp):
        return o.strftime("%Y-%m-%d")
    if o is pd.NA or o is pd.NaT:
        return None
    return o


def write_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_jsonable(obj), indent=2, default=str))


def window_label(code: int, doy: int):
    w = CROP_WINDOWS.get(int(code))
    if w is None:
        return None
    if any(a <= doy <= b for a, b in w["bare"]):
        return "bare"
    if any(a <= doy <= b for a, b in w["covered"]):
        return "covered"
    return None


def r4(x, nd=4):
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else round(float(x), nd)


def model_report(*, id, task, method, features, labels, split, metrics, confusion=None, feature_importance=None,
                 disagreement_with=None, notes="", **extra) -> dict:
    """ModelReport in the shape of planner-spec.md B3 / schemas/model_report.schema.json (spuriNV's builder).
    Extra keys (location_id, badge, checks, test, headline, ...) are listed in the schema."""
    rep = {
        "id": id, "task": task, "method": method, "features": list(features), "labels": labels, "split": split,
        "metrics": {k: (r4(v) if isinstance(v, (float, np.floating)) else v) for k, v in metrics.items()},
        "confusion": confusion, "feature_importance": feature_importance or [],
        "disagreement_with": {k: r4(v) for k, v in (disagreement_with or {}).items() if v is not None},
        "notes": notes,
    }
    if rep["confusion"] is None:
        rep.pop("confusion")
    rep.update({k: v for k, v in extra.items() if v is not None})
    return rep
