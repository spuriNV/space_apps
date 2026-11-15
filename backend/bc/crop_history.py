"""AAFC ACI crop history inside the BC field outline, in the same shape as backend/field's CDL crop_history.json.

Writes backend/field/out/bc_salmon_river_forage/crop_history.json and data/cache/bc_salmon_river_forage/aci.parquet
(year, code, name, fraction, n_pixels). Needs aci.py and select_field.py first.

Run: uv run python crop_history.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask
from shapely.geometry import mapping
from shapely.ops import transform

from aci import BASE, LEGEND, SPEC
from common import CACHE, FIELD_OUT, FID, now, polygon, read_json, write_json


def main():
    g, _ = polygon()
    rows, years = [], []
    for f in sorted((CACHE / "rasters").glob("aci_*.tif")):
        y = int(f.stem.split("_")[1])
        with rasterio.open(f) as r:
            gg = transform(Transformer.from_crs("EPSG:4326", r.crs, always_xy=True).transform, g)
            m = ~geometry_mask([mapping(gg)], out_shape=(r.height, r.width), transform=r.transform)
            if m.sum() < 3:   # 56 m years: fall back to touching pixels
                m = ~geometry_mask([mapping(gg)], out_shape=(r.height, r.width), transform=r.transform, all_touched=True)
            v = r.read(1)[m]
            res = abs(r.transform.a)
        codes, counts = np.unique(v, return_counts=True)
        order = np.argsort(-counts)
        top = [{"code": int(codes[i]), "name": LEGEND.get(int(codes[i]), f"class {codes[i]}"),
                "pct": round(100 * counts[i] / len(v), 1)} for i in order]
        for t in top:
            rows.append({"year": y, "code": t["code"], "name": t["name"], "fraction": t["pct"] / 100,
                         "n_pixels": int(round(t["pct"] / 100 * len(v)))})
        years.append({"year": y, "majority_code": top[0]["code"], "majority_name": top[0]["name"],
                      "purity_pct": top[0]["pct"], "n_pixels": int(len(v)), "pixel_res_m": res, "top_classes": top[:4]})
    pd.DataFrame(rows).to_parquet(CACHE / "aci.parquet", index=False)
    meta = read_json(CACHE / "aci.meta.json")
    write_json(CACHE / "aci_field.meta.json", {**{k: meta[k] for k in ("title", "url", "spec", "licence")},
                                               "fetched_at": now(), "footprint_geojson": mapping(g)})
    by_year = {str(y["year"]): y["majority_name"] for y in years}
    undiff = [y["year"] for y in years if y["majority_code"] == 120]
    unmapped = [y["year"] for y in years if y["majority_code"] == 0]
    out = {
        "preset_id": FID,
        "source": {"id": "aafc_aci", "title": "AAFC Annual Crop Inventory (ACI), 30 m (56 m 2009-2010)", "url": BASE,
                   "spec": SPEC, "accessed": now()[:10], "verified": True,
                   "licence": "Open Government Licence - Canada"},
        "method": "Majority ACI class of the pixels whose centre lies inside the field outline (all touched pixels in "
                  "the 56 m years); purity = share of the majority class.",
        "by_year": by_year, "years": years,
        "caveats": [
            "ACI class 122 'Pasture / Forages' lumps alfalfa, clover, tame grass hay and pasture: it cannot say whether "
            "the field was alfalfa or grass hay in a given year (California's CDL separates them).",
            f"{unmapped}: the ACI does not cover this part of BC in these years (value 0, not mapped).",
            f"{undiff}: AAFC mapped this area only as 120 'Agriculture (undifferentiated)' in these years (no crop type).",
            "ACI overall accuracy for crop classes in British Columbia, from the ACI specification: 88.34% (2024 map) and "
            "89.02% (2025 map); 73-93% in earlier years. That is for all crop classes province-wide, not for forage at "
            "this field: treat single-year changes as possible errors.",
            "The outline was chosen from ACI forage pixels, so forage purity here is not an independent check.",
        ],
    }
    write_json(FIELD_OUT / "crop_history.json", out)
    for y in years:
        print(y["year"], y["majority_name"], y["purity_pct"], y["n_pixels"], [(t["name"], t["pct"]) for t in y["top_classes"][1:3]])


if __name__ == "__main__":
    main()
