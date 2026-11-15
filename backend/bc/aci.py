"""AAFC Annual Crop Inventory (ACI) for the lower Salmon River valley: clip each year's BC GeoTIFF to a box.

Source: Agriculture and Agri-Food Canada, Annual Crop Inventory, 30 m (56 m in 2009-2010), one GeoTIFF per province
and year, https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/data_donnees/tif/<year>/aci_<year>_bc_v*.zip
(Open Government Licence - Canada). Class codes and names: ACI Data Product Specification (ISO 19131), section 4,
https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/supportdocument_documentdesupport/en/ISO%2019131_AAFC_Annual_Crop_Inventory_Data_Product_Specifications.pdf
CRS: EPSG:10820 (WGS 84 / Agriculture Canada Albers). Class 122 "Pasture / Forages" = "tame grasses and other perennial
crops such as alfalfa and clover grown alone or as mixtures for hay, pasture or seed": the ACI has no separate alfalfa
class, which is one of the BC gaps (California's CDL separates alfalfa, other hay and grass pasture).

The zips (about 1.6 GB for 2009-2025) are downloaded outside the repo (pass --zips DIR); only the clipped box is kept:
data/cache/bc_salmon_river_forage/rasters/aci_<year>.tif (git-ignored) and aci_legend.json.

Run: uv run python aci.py --zips /path/to/zips
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from common import CACHE, now, write_json

BASE = "https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/data_donnees/tif"
SPEC = ("https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/supportdocument_documentdesupport/en/"
        "ISO%2019131_AAFC_Annual_Crop_Inventory_Data_Product_Specifications.pdf")
# Lower Salmon River valley, Falkland to Salmon Arm (lon/lat)
BOX = (-119.52, 50.42, -119.12, 50.75)
LEGEND = {
    0: "Not mapped (no data)", 10: "Cloud", 20: "Water", 30: "Exposed Land / Barren", 34: "Urban / Developed", 35: "Greenhouses", 50: "Shrubland",
    60: "Forest Fire / Burnt Area", 80: "Wetland", 85: "Peatland", 110: "Grassland", 120: "Agriculture (undifferentiated)",
    121: "Cropland", 122: "Pasture / Forages", 130: "Too Wet to be Seeded", 131: "Fallow", 132: "Cereals", 133: "Barley",
    134: "Other Grains", 135: "Millet", 136: "Oats", 137: "Rye", 138: "Spelt", 139: "Triticale", 140: "Wheat",
    141: "Switchgrass", 142: "Sorghum", 143: "Quinoa", 145: "Winter Wheat", 146: "Spring Wheat", 147: "Corn",
    148: "Tobacco", 149: "Ginseng", 150: "Oilseeds", 151: "Borage", 152: "Camelina", 153: "Canola / Rapeseed",
    154: "Flaxseed", 155: "Mustard", 156: "Safflower", 157: "Sunflower", 158: "Soybeans", 159: "Other Oilseeds",
    160: "Pulses", 161: "Other Pulses", 162: "Peas", 163: "Chickpeas", 167: "Beans", 168: "Fababeans", 174: "Lentils",
    175: "Vegetables", 176: "Tomatoes", 177: "Potatoes", 178: "Sugarbeets", 179: "Other Vegetables", 180: "Fruits",
    181: "Berries", 182: "Blueberry", 183: "Cranberry", 185: "Other Berries", 188: "Orchards", 189: "Other Fruits",
    190: "Vineyards", 191: "Hops", 192: "Sod", 193: "Herbs", 194: "Nursery", 195: "Buckwheat", 196: "Canaryseed",
    197: "Hemp", 198: "Vetch", 199: "Other Crops", 200: "Forest (undifferentiated)", 210: "Coniferous",
    220: "Broadleaf", 230: "Mixedwood",
}
FORAGE = 122
FARM = set(range(120, 200))   # agricultural classes 120-199


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True, help="directory with aci_<year>_bc_v*.zip")
    a = ap.parse_args()
    out = CACHE / "rasters"
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for z in sorted(Path(a.zips).glob("aci_*_bc_v*.zip")):
        year = int(re.search(r"aci_(\d{4})_bc", z.name).group(1))
        tif = z.name.replace(".zip", ".tif")
        with rasterio.open(f"/vsizip/{z}/{tif}") as src:
            b = transform_bounds("EPSG:4326", src.crs, *BOX, densify_pts=21)
            win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
            arr = src.read(1, window=win, boundless=True, fill_value=0)
            prof = src.profile | {"driver": "GTiff", "height": arr.shape[0], "width": arr.shape[1],
                                  "transform": src.window_transform(win), "compress": "deflate", "tiled": False}
            prof.pop("blockxsize", None); prof.pop("blockysize", None)
            dst = out / f"aci_{year}.tif"
            with rasterio.open(dst, "w", **prof) as d:
                d.write(arr, 1)
        files[year] = {"zip": f"{BASE}/{year}/{z.name}", "res_m": abs(prof["transform"].a), "shape": list(arr.shape),
                       "forage_px": int((arr == FORAGE).sum())}
        print(year, z.name, arr.shape, "forage px", files[year]["forage_px"])
    write_json(CACHE / "aci_legend.json", {"source": SPEC, "classes": {str(k): v for k, v in LEGEND.items()}})
    write_json(CACHE / "aci.meta.json", {
        "title": "AAFC Annual Crop Inventory (ACI), British Columbia GeoTIFFs, clipped to the lower Salmon River valley",
        "url": BASE, "spec": SPEC, "box_lonlat": BOX, "crs": "EPSG:10820", "fetched_at": now(), "auth": "none",
        "licence": "Open Government Licence - Canada", "years": files,
        "note": "30 m from 2011; 2009-2010 are 56 m and cover little of BC. Class 122 Pasture / Forages lumps alfalfa, "
                "tame grass hay and pasture (no alfalfa class)."})


if __name__ == "__main__":
    main()
