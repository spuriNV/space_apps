"""CDL crop history per preset polygon -> out/<preset>/crop_history.json + data/cache/<preset>/cdl.parquet.

Usage: uv run python -m fieldshift_field.crop_history [preset ...]
"""
from __future__ import annotations

import sys

import pandas as pd

from .cdl import SERVICE
from .common import CDL_CRS, PRESETS, cache, now, out, polygon_in, read_json, today, write_json
from .zonal import cdl_year_stats


def build(preset: str):
    g = polygon_in(preset, CDL_CRS)
    meta = read_json(cache(preset) / "cdl.meta.json")
    leg = read_json(cache(preset) / "cdl_legend.json")["classes"]
    name = lambda c: leg.get(str(c), {}).get("name", f"class {c}")
    years = sorted(int(y) for y in meta["files"])
    rows, recs = [], []
    for y in years:
        s = cdl_year_stats(preset, g, y)
        if s is None:
            recs.append({"year": y, "majority_code": None, "majority_name": None, "purity_pct": None,
                         "note": "no CDL pixels inside polygon"})
            continue
        top = sorted(s["fractions"].items(), key=lambda kv: -kv[1])[:3]
        recs.append({
            "year": y, "majority_code": s["majority"], "majority_name": name(s["majority"]),
            "purity_pct": round(100 * s["purity"], 1), "n_pixels": s["n_pixels"], "pixel_res_m": s["res_m"],
            "top_classes": [{"code": c, "name": name(c), "pct": round(100 * f, 1)} for c, f in top],
        })
        for c, f in s["fractions"].items():
            rows.append({"year": y, "code": c, "name": name(c), "fraction": f,
                         "n_pixels": round(f * s["n_pixels"]), "res_m": s["res_m"]})
    c = cache(preset)
    pd.DataFrame(rows).to_parquet(c / "cdl.parquet", index=False)
    doc = {
        "preset_id": preset, "generated_at": now(),
        "source": {"id": "usda_nass_cdl", "title": "USDA NASS Cropland Data Layer (via CroplandCROS image service)",
                   "url": SERVICE, "accessed": today(), "verified": True},
        "method": ("Pixels whose centre lies inside the polygon (CDL native EPSG:5070 grid; 30 m to 2023, 10 m in 2024-2025). "
                   "Majority class and its share (purity). Class names from the service raster attribute table."),
        "first_year": years[0], "last_year": years[-1],
        "by_year": {str(r["year"]): r["majority_name"] for r in recs},
        "years": recs,
        "caveats": ["CDL is a classification with per-class accuracy that varies by year and crop; purity is agreement among pixels, not accuracy.",
                    "2024-2025 CDL is 10 m, so pixel counts are ~9x those of earlier years."],
    }
    write_json(out(preset) / "crop_history.json", doc)
    print(preset)
    for r in recs:
        print(f"  {r['year']}: {r['majority_name']} ({r['purity_pct']}%)")
    return doc


if __name__ == "__main__":
    for p in (sys.argv[1:] or list(PRESETS)):
        build(p)
