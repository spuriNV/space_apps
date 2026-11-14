"""Shared helpers: class names, ModelReport builder (planner-spec.md B3), JSON output."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

CLASSES = ["bare", "partial", "covered"]
CLASS_TO_ORD = {c: i for i, c in enumerate(CLASSES)}


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return [_jsonable(v) for v in o.tolist()]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) or math.isinf(f) else round(f, 4)
    if isinstance(o, (pd.Timestamp,)):
        return o.strftime("%Y-%m-%d")
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_json(path: str | Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(obj), indent=2))


def model_report(*, id, task, method, features, labels, split, metrics,
                 confusion=None, feature_importance=None, disagreement_with=None,
                 notes="", **extra) -> dict:
    """ModelReport in the shape given in planner-spec.md B3. Extra keys (e.g. location_id) are appended."""
    rep = {
        "id": id,
        "task": task,  # bare_cover | transition | stress_anomaly
        "method": method,  # rule_ndvi | random_forest | hist_gbt | zscore | isolation_forest
        "features": list(features),
        "labels": labels,
        "split": split,
        "metrics": metrics,
        "confusion": confusion,
        "feature_importance": feature_importance or [],
        "disagreement_with": disagreement_with or {},
        "notes": notes,
    }
    rep.update(extra)
    return rep
