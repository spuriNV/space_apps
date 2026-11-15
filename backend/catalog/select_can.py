"""Canada outside BC for the farm catalog: ~44 real fields in the Prairies (AB, SK, MB) and Ontario / Quebec.

AAFC Annual Crop Inventory 2025 (ImageServer exportImage, 30 m, EPSG:3978) over random 24 km tiles inside each province's
farm belt. A field is a connected patch of one crop group (2025) of 8-121 ha (20-300 acres) that is compact (area / convex
hull >= 0.8) and does not touch the tile edge; the patch outline (simplified to ~15 m) is the field outline the build uses.
Farthest-point spread, every pair >= 5 km apart. Names from the Canadian Geographical Names Database.

Merges into out/selection.json (keeps everything that is not region can-*). Run: cd backend/catalog && uv run python select_can.py
"""
from __future__ import annotations

import importlib.util
import json
import random
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.ops import transform

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sel0", HERE / "select.py")
S = importlib.util.module_from_spec(spec)
sys.modules["sel0"] = S
spec.loader.exec_module(S)

CRS = "EPSG:3978"
MIN_SEP = 5.0
BELTS = {   # province: (name, region, area, belt lon0, lat0, lon1, lat1, plan {group: n})
    "AB": ("Alberta", "can-prairies", (-114.4, 51.3, -110.3, 55.4), {"canola": 4, "grain": 5, "pulses": 1}),
    "SK": ("Saskatchewan", "can-prairies", (-108.6, 50.0, -102.3, 53.8), {"canola": 5, "grain": 4, "pulses": 4}),
    "MB": ("Manitoba", "can-prairies", (-100.8, 49.2, -97.2, 51.2), {"canola": 3, "grain": 2, "soy": 3}),
    "ON": ("Ontario", "can-east", (-82.6, 42.6, -79.8, 44.4), {"grain": 4, "soy": 3}),
    "QC": ("Quebec", "can-east", (-73.9, 45.0, -71.8, 46.4), {"grain": 3, "soy": 2, "forage": 1}),
}
GROUPS = {"canola": {153}, "grain": {133, 136, 140, 145, 146, 147}, "pulses": {160, 161, 162, 163, 167, 168, 174}, "soy": {158}, "forage": {122}}
WORD = {**S.ACI_WORD, **{158: "Soybean field", 162: "Pea field", 174: "Lentil field", 163: "Chickpea field", 168: "Faba bean field",
                           167: "Bean field", 160: "Pulse field", 161: "Pulse field", 147: "Corn field"}}
LABEL = {"canola": "Canola", "grain": "Wheat, barley, oats and corn", "pulses": "Peas, lentils and other pulses", "soy": "Soybeans",
         "forage": "Alfalfa, hay and pasture"}


def tile(h, year, cx, cy, half=12000):
    import rasterio  # noqa: PLC0415
    from rasterio.io import MemoryFile  # noqa: PLC0415
    n = 2 * half // 30
    r = h.get(S.ACI.format(year=year) + "/exportImage", {"bbox": f"{cx - half},{cy - half},{cx + half},{cy + half}", "bboxSR": 3978,
              "imageSR": 3978, "size": f"{n},{n}", "format": "tiff", "pixelType": "U8", "interpolation": "RSP_NearestNeighbor", "f": "image"})
    with MemoryFile(r.content) as mf, mf.open() as ds:
        return ds.read(1), ds.transform


def main():
    from rasterio.features import shapes  # noqa: PLC0415
    from scipy import ndimage  # noqa: PLC0415
    rng = random.Random(11)
    h = S.Http()
    to_p = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    to_ll = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True).transform
    picked = []
    for prov, (pname, region, box, plan) in BELTS.items():
        cands = {g: [] for g in plan}
        ntiles = 14 if sum(plan.values()) > 7 else 10
        for _ in range(ntiles):
            lon, lat = rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3])
            cx, cy = to_p.transform(lon, lat)
            try:
                a, tr = tile(h, 2025, cx, cy)
            except Exception as e:  # noqa: BLE001
                print("  tile failed", prov, str(e)[:80])
                continue
            for g in plan:
                m = np.isin(a, list(GROUPS[g]))
                lab, k = ndimage.label(m)
                if not k:
                    continue
                sizes = ndimage.sum(m, lab, index=np.arange(1, k + 1))
                for i, sz in enumerate(sizes, 1):
                    if not 89 <= sz <= 1344:
                        continue
                    pm = (lab == i)
                    rr, cc = np.nonzero(pm)
                    if rr.min() == 0 or cc.min() == 0 or rr.max() == a.shape[0] - 1 or cc.max() == a.shape[1] - 1:
                        continue
                    geom = next(shape for shape, v in shapes(pm.astype("uint8"), mask=pm, transform=tr))
                    pg = Polygon(geom["coordinates"][0])
                    if pg.area / pg.convex_hull.area < 0.8:
                        continue
                    ll = transform(to_ll, pg).simplify(0.00015)
                    ip = S.interior(ll)
                    if ip is None or ll.is_empty:
                        continue
                    codes, cnt = np.unique(a[pm], return_counts=True)
                    top = int(codes[np.argmax(cnt)])
                    cands[g].append({"pt": (round(ip.x, 4), round(ip.y, 4)), "acres": round(pg.area / 4046.86, 1), "aci": top,
                                     "outline": [[round(x, 5), round(y, 5)] for x, y in ll.exterior.coords]})
        for g, n in plan.items():
            sel = S.spread_pick(cands[g], n, [p["pt"] for p in picked] + [(0, 0)], rng=rng)
            sel = [c for c in sel if all(S.km(c["pt"], p["pt"]) >= MIN_SEP for p in picked)][:n]
            for c in sel:
                picked.append({"region": region, "area": pname, "country": "CA", "state": prov, "crop_group": g, "pt": c["pt"],
                               "county": pname, "acres": c["acres"], "crop_word": WORD.get(c["aci"], "Field"),
                               "outline": c["outline"], "source": {"aci_2025_majority": c["aci"], "outline": "AAFC ACI 2025 patch"}})
            print(f"{prov} {g:8s} want {n} cands {len(cands[g])} picked {len(sel)}")
    for p in picked:
        for r in (15, 30, 60):
            pl = None
            d = h.json(S.GEONAMES, {"lat": round(p["pt"][1], 5), "lon": round(p["pt"][0], 5), "radius": r, "concise": "CITY,TOWN,VILG,UNP,MUN1,MUN2"})
            if d.get("items"):
                it = min(d["items"], key=lambda i: S.km(p["pt"], (i["longitude"], i["latitude"])))
                pl = it["name"]
                break
        p["place"] = pl
        p["crop_group_label"] = LABEL[p["crop_group"]]
        p["id"] = S.point_id(p["pt"][1], p["pt"][0])
        p["name"] = f"{p['crop_word']} near {pl}, {p['state']}" if pl else f"{p['crop_word']} in {p['county']}"
    sel_path = S.OUT
    doc = json.loads(sel_path.read_text())
    doc["fields"] = [f for f in doc["fields"] if not f["region"].startswith("can-")] + picked
    sel_path.write_text(json.dumps(doc, indent=1) + "\n")
    print(len(picked), "Canadian fields")


if __name__ == "__main__":
    main()
