"""OpenET as an independent check of the baseline's modelled ET (spec B4.1 validation line; never a score input).

OpenET Ensemble monthly ET over the field polygon (backend/ground -> data/cache/<id>/openet.parquet) is compared
with the engine's ETc only in the calendar years whose CDL majority crop is the baseline crop
(backend/field/out/<id>/crop_history.json), and the engine is run on the SAME weather years. Fallow/other-crop
years (e.g. CAR 2016, 2020, 2022) would otherwise compare a rice model with a fallow field.
Nothing here is fitted: no engine coefficient is derived from OpenET.
"""
from __future__ import annotations

import json

import pandas as pd

from .observed import BASELINE_CDL, _base_crop
from .weather import REPO


def openet_matched(preset_id: str, strategy: dict) -> dict | None:
    p = REPO / "data" / "cache" / preset_id / "openet.parquet"
    h = REPO / "backend" / "field" / "out" / preset_id / "crop_history.json"
    base = _base_crop(strategy)
    if not p.exists() or not h.exists() or base is None:
        return None
    hist = json.loads(h.read_text())["by_year"]
    oe = pd.read_parquet(p)
    if "model" in oe:
        oe = oe[oe["model"] == "Ensemble"]
    oe = oe.assign(date=pd.to_datetime(oe["date"]))
    tot = oe.groupby(oe.date.dt.year)["et_mm"].agg(["sum", "count"])
    years = [int(y) for y, r in tot.iterrows() if r["count"] == 12 and hist.get(str(y)) in BASELINE_CDL[base]]
    if not years:
        return None
    vals = tot.loc[years, "sum"]
    meta_p = p.with_name("openet.meta.json")
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    return {"years": years, "mean": float(vals.mean()), "low": float(vals.min()), "high": float(vals.max()),
            "url": meta.get("url", "https://openet-api.org/raster/timeseries/polygon"),
            "cache_path": str(p.relative_to(REPO)), "crop": sorted(BASELINE_CDL[base])[0]}
