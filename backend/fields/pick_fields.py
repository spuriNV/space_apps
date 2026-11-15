"""Find candidate fields for the registry (run once, by hand; not part of run_all).

Same method as backend/field/select_fields.py: DWR / Land IQ Statewide Crop
Mapping 2023 field outlines near a seed point, each scored against the USDA CDL
crop history 2008-2025 (majority class and purity inside the outline). Writes a
ranked candidate list per seed to the path given with --out; a person then picks
one per seed and adds it to registry.json.

Run from backend/field (it uses that chunk's packages):
  uv run python ../fields/pick_fields.py --out /tmp/candidates.json [seed ...]
CDL rasters for each seed go to --cdl-dir (not committed).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "field"))
from fieldshift_field import cdl as C  # noqa: E402
from fieldshift_field import common as K  # noqa: E402
from fieldshift_field.select_fields import dwr_fields, transform  # noqa: E402
from fieldshift_field.zonal import cdl_year_stats  # noqa: E402

RICE, FALLOW, ALFALFA, CORN, WATER = 3, 61, 36, 1, 111
FORAGE = {ALFALFA, CORN, 225, 226, 228, 237, 37, 205, 27, 28}  # alfalfa, corn, double-crop winter grain/corn, hay, small-grain forage
YEARS = list(range(2008, 2026))
RECENT = list(range(2016, 2026))

# seed id, family, county, lon, lat
SEEDS = [
    ("r_glenn", "rice", "Glenn", -122.06, 39.52),
    ("r_glenn_n", "rice", "Glenn", -122.03, 39.62),
    ("r_butte_richvale", "rice", "Butte", -121.77, 39.50),
    ("r_butte_gridley", "rice", "Butte", -121.73, 39.42),
    ("r_sutter", "rice", "Sutter", -121.72, 38.88),
    ("r_sutter_meridian", "rice", "Sutter", -121.87, 39.12),
    ("r_yolo", "rice", "Yolo", -121.76, 38.80),
    ("r_yolo_w", "rice", "Yolo", -121.85, 38.86),
    ("r_colusa_maxwell", "rice", "Colusa", -122.12, 39.30),
    ("r_colusa_grimes", "rice", "Colusa", -121.93, 39.07),
    ("f_kings_lake", "forage", "Kings", -119.78, 36.10),
    ("f_kings_lake_s", "forage", "Kings", -119.68, 36.02),
    ("f_tulare_tipton", "forage", "Tulare", -119.33, 36.07),
    ("f_tulare_goshen", "forage", "Tulare", -119.45, 36.36),
    ("f_fresno_riverdale", "forage", "Fresno", -119.86, 36.42),
    ("f_fresno_caruthers", "forage", "Fresno", -119.80, 36.52),
    ("f_merced_elnido", "forage", "Merced", -120.50, 37.15),
    ("f_merced_atwater", "forage", "Merced", -120.70, 37.30),
    ("f_stan_crows", "forage", "Stanislaus", -121.02, 37.40),
    ("f_stan_westley", "forage", "Stanislaus", -121.12, 37.55),
    # Tulare Lake bed, 2023 re-flooding (second pass, ranked by CDL 2023 open water)
    ("f_lake_corcoran_s", "forage", "Kings", -119.58, 36.05),
    ("f_lake_alpaugh", "forage", "Tulare", -119.52, 35.93),
    ("f_lake_central", "forage", "Kings", -119.64, 35.98),
]


def fetch_cdl(seed, lon, lat, cat, half):
    K.PRESETS[seed] = {"centre": (lon, lat), "target_ha": 50}
    box = C.box_5070(seed, half=half)
    d = K.cache(seed) / "rasters"
    for y in YEARS:
        dst = d / f"cdl_{y}.tif"
        if dst.exists():
            continue
        arr, info = C.export_year(box, cat[y])
        res = info["res_m"]
        tr = rasterio.Affine(res, 0, box[0], 0, -res, box[3])
        with rasterio.open(dst, "w", driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1,
                           dtype="uint8", crs=K.CDL_CRS, transform=tr, nodata=0, compress="deflate") as o:
            o.write(arr, 1)


def score(fam, st):
    maj = {y: st[y]["majority"] for y in st}
    pur = {y: st[y]["purity"] for y in st}
    if fam == "rice":
        rice = [y for y in RECENT if maj[y] == RICE]
        fallow = [y for y in RECENT if maj[y] == FALLOW]
        other = [y for y in RECENT if maj[y] not in (RICE, FALLOW)]
        ok = len(rice) >= 6 and len(other) <= 1 and maj[2025] == RICE
        p = float(np.mean([pur[y] for y in rice + fallow])) if rice else 0
        return ok, p, {"rice": len(rice), "fallow": fallow, "other": other}
    forage = [y for y in RECENT if maj[y] in FORAGE]
    alf = [y for y in RECENT if maj[y] == ALFALFA]
    corn = [y for y in RECENT if maj[y] in (CORN, 225, 226, 228, 237)]
    ok = len(alf) >= 3 and len(forage) >= 7 and (maj[2025] in FORAGE or maj[2024] in FORAGE)
    p = float(np.mean([pur[y] for y in forage])) if forage else 0
    return ok, p, {"alfalfa": len(alf), "corn": len(corn), "forage": len(forage)}


def run_seed(seed, fam, county, lon, lat, cat, leg):
    half = 4500
    fetch_cdl(seed, lon, lat, cat, half)
    to_utm = K.to_crs("EPSG:4326", K.WORK_CRS)
    to_alb = K.to_crs("EPSG:4326", K.CDL_CRS)
    feats = dwr_fields(lon, lat)
    out = []
    for f in feats:
        g = shape(f["geometry"])
        if g.is_empty:
            continue
        if g.geom_type == "MultiPolygon":
            continue
        area = transform(to_utm.transform, g).area / 1e4
        if not (15 <= area <= 120):
            continue
        ga = transform(to_alb.transform, g)
        st = {y: cdl_year_stats(seed, ga, y) for y in YEARS}
        if any(s is None for s in st.values()):
            continue
        ok, p, info = score(fam, st)
        name = lambda c: leg.get(str(c), {}).get("name", str(c))
        hist = {y: f"{name(st[y]['majority'])} {round(100 * st[y]['purity'])}" for y in YEARS}
        lake = st[2023]["fractions"].get(WATER, 0)
        out.append({"seed": seed, "ok": ok, "purity_mean": round(p, 3), "info": info, "area_ha": round(area, 1),
                    "dwr": f["properties"], "centroid": [round(g.centroid.x, 6), round(g.centroid.y, 6)],
                    "water_2023": round(lake, 3), "min_purity_recent": round(min(st[y]["purity"] for y in RECENT), 3),
                    "history": hist})
    out.sort(key=lambda c: (-c["ok"], -c["purity_mean"]))
    print(f"{seed}: {len(feats)} DWR fields, {sum(c['ok'] for c in out)} pass", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seeds", nargs="*")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cdl-dir", required=True)
    a = ap.parse_args()
    K.CACHE_DIR = Path(a.cdl_dir)
    cat = C.catalog()
    leg = {str(k): v for k, v in C.legend().items()}
    seeds = [s for s in SEEDS if not a.seeds or s[0] in a.seeds]
    res = {}
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(run_seed, *s, cat, leg): s[0] for s in seeds}
        for f in cf.as_completed(futs):
            try:
                res[futs[f]] = f.result()
            except Exception as e:  # noqa: BLE001
                print(futs[f], "FAILED", e, flush=True)
    prev = json.loads(Path(a.out).read_text()) if Path(a.out).exists() else {}
    prev.update(res)
    Path(a.out).write_text(json.dumps(prev, indent=1))


if __name__ == "__main__":
    main()
