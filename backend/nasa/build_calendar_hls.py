"""NASA-native field calendar: backend/field's rule detector (imported, unchanged thresholds) run on HLS v2.0 scenes only.
Inputs: data/cache/<id>/hls.parquet (Planetary Computer copy, backend/nasa_open, 2017-08..2025) and
data/cache/<id>/hls_lpdaac.parquet (NASA LP DAAC with the Earthdata login: 2016-2017 and 2026..today).
Output: backend/nasa/out/<id>/calendar_hls.json, same shape as backend/field/out/<id>/calendar.json.
Same-day rule: HLSS30 (Sentinel-2 based) over HLSL30, as the detector prefers Sentinel-2. No BSI in HLS rows (null)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "field"))
from fieldshift_field import detector as D  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]


def load_hls(p: str) -> tuple[pd.DataFrame, list[str]]:
    frames, used = [], []
    for name in ("hls", "hls_lpdaac"):
        f = REPO / "data" / "cache" / p / f"{name}.parquet"
        if f.exists():
            d = pd.read_parquet(f)
            d["store"] = name
            frames.append(d)
            used.append(name)
    d = pd.concat(frames, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])
    # same granule in both stores: keep one (LP DAAC is NASA's own archive)
    d["_sid"] = d.scene_id.str.replace(r"\.v2\.0$", "", regex=True)
    d = d.sort_values("store").drop_duplicates("_sid", keep="last")
    d = d[(d.clear_frac >= D.MIN_CLEAR) & (d.n_valid >= D.MIN_PIXELS) & d.ndvi_med.notna()].copy()
    d["sensor"] = np.where(d.platform == "HLSS30", "hls_s30", "hls_l30")
    d["prio"] = (d.platform != "HLSS30").astype(int)
    d = d.sort_values(["date", "prio", "n_valid"], ascending=[True, True, False]).drop_duplicates("date")
    d["is_water"] = (d.ndwi_med > D.NDWI_WATER) | (d.water_frac.fillna(0) > D.WATER_FRAC)
    d["cls"] = np.where(d.is_water, "water", np.where(d.ndvi_med < D.BARE, "bare",
                                                      np.where(d.ndvi_med <= D.COVER, "partial", "covered")))
    return d.reset_index(drop=True), used


def build(p: str) -> dict:
    d, used = load_hls(p)
    last = d.date.max()
    full = D.daily(d, "2015-07-01", last.strftime("%Y-%m-%d"))
    marks = D.markers(d)
    years = []
    for y in range(2016, last.year + 1):
        s = full[str(y)]
        dy = d[d.date.dt.year == y]
        segs = D.segments(s, list(dy.date))
        counts = s.value_counts().to_dict()
        years.append({
            "year": y, "segments": segs, "transitions": D.transitions(segs),
            "markers": [m for m in marks if m["date"].startswith(str(y))],
            "summary": {"days_by_class": {k: int(counts.get(k, 0)) for k in D.CLASSES}, "n_obs": int(len(dy)),
                        "n_obs_hls_s30": int((dy.sensor == "hls_s30").sum()), "n_obs_hls_l30": int((dy.sensor == "hls_l30").sum()),
                        "through": s.index.max().strftime("%Y-%m-%d")},
            "observations": [{"date": r.date.strftime("%Y-%m-%d"), "sensor": r.sensor, "ndvi": round(float(r.ndvi_med), 3),
                              "ndwi": round(float(r.ndwi_med), 3), "bsi": None, "clear_frac": round(float(r.clear_frac), 2),
                              "class": r.cls} for r in dy.itertuples()],
        })
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = {
        "preset_id": p, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "detector": "rule_ndvi",
        "source": "hls", "last_observation": last.strftime("%Y-%m-%d"),
        "classes": D.CLASSES,
        "method": {"bare_lt": D.BARE, "covered_gt": D.COVER, "water": f"NDWI > {D.NDWI_WATER} or HLS Fmask water > {D.WATER_FRAC}",
                   "max_interp_gap_days": D.MAX_GAP, "min_clear_frac": D.MIN_CLEAR, "min_clear_pixels": D.MIN_PIXELS,
                   "green_up": f"{D.GREENUP_N} consecutive obs NDVI > {D.COVER}",
                   "senescence_harvest": f"{D.DROP_N} consecutive obs > {D.DROP} below {D.DROP_WIN}-day max",
                   "same_day_priority": "HLSS30 over HLSL30", "thresholds_status": "U rule of thumb (spec B5.1), not tuned; "
                   "identical to backend/field (imported from fieldshift_field.detector)",
                   "inputs": used},
        "sources": [
            {"id": "hls_lpdaac", "title": "HLS v2.0 HLSL30/HLSS30, NASA/USGS (NASA LP DAAC, Earthdata login)",
             "url": "https://doi.org/10.5067/HLS/HLSS30.002", "accessed": today, "verified": True},
            {"id": "hls_mpc", "title": "HLS v2.0 (Microsoft Planetary Computer copy, 2017-08..2025)",
             "url": "https://planetarycomputer.microsoft.com/dataset/hls2-s30", "accessed": today, "verified": True}],
        "notes": ["HLS is NASA's harmonized Landsat 8/9 + Sentinel-2 surface reflectance at 30 m; same thresholds as the "
                  "Sentinel-2/Landsat calendar, so the two calendars differ only by input data.",
                  "Days after the last clear HLS scene are 'unknown' (not extrapolated)."],
        "years": years,
    }
    (OUT / p).mkdir(parents=True, exist_ok=True)
    (OUT / p / "calendar_hls.json").write_text(json.dumps(doc, separators=(",", ":")))
    print(p, "last obs", doc["last_observation"])
    for y in years:
        print(f"  {y['year']}: obs {y['summary']['n_obs']:3d} days {y['summary']['days_by_class']}")
    return doc


if __name__ == "__main__":
    for p in sys.argv[1:] or PRESETS:
        build(p)
