"""Field-data chunk checks (spec B10.1 checks 1 and 7, plus range/coverage checks).

Prints one PASS / FAIL / INFO line per check. Reads only local files (polygons, cache, out).
Run: uv run python checks/run_checks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fieldshift_field.common import CACHE_DIR, OUT_DIR, POLY_DIR, PRESETS, WORK_CRS, polygon_in  # noqa: E402

CA_LON, CA_LAT = (-124.5, -114.0), (32.5, 42.0)
results = []


def line(status, name, detail):
    results.append(status)
    print(f"{status:4s} | {name} | {detail}")


def load(p):
    return json.loads(Path(p).read_text())


def flat_coords(geom):
    if geom["type"] == "Polygon":
        return [xy for ring in geom["coordinates"] for xy in ring]
    return [xy for poly in geom["coordinates"] for ring in poly for xy in ring]


def check_polygons():
    for pid, cfg in PRESETS.items():
        f = POLY_DIR / f"{pid}.geojson"
        if not f.exists():
            line("FAIL", f"polygon {pid}", "missing file"); continue
        feat = load(f)["features"][0]
        xy = flat_coords(feat["geometry"])
        lon_ok = all(CA_LON[0] <= x <= CA_LON[1] for x, _ in xy)
        lat_ok = all(CA_LAT[0] <= y <= CA_LAT[1] for _, y in xy)
        x0, y0 = xy[0]
        line("PASS" if lon_ok and lat_ok else "FAIL", f"lon/lat order {pid}",
             f"first vertex (x={x0:.5f}, y={y0:.5f}) -> x is lon in CA range: {lon_ok}, y is lat in CA range: {lat_ok}")
        area = polygon_in(pid, WORK_CRS).area / 1e4
        tgt = cfg["target_ha"]
        ok = 0.5 * tgt <= area <= 1.5 * tgt
        cx, cy = feat["properties"]["centroid"]["lon"], feat["properties"]["centroid"]["lat"]
        line("PASS" if ok else "FAIL", f"polygon area {pid}",
             f"{area:.2f} ha in {WORK_CRS} (target ~{tgt:.0f} ha, accepted 50-150%); centroid {cy:.5f} N, {cx:.5f} E")
        tb = POLY_DIR / f"{pid}_training_box.json"
        if tb.exists():
            b = load(tb)["bbox_epsg32610"]
            line("PASS" if abs((b[2] - b[0]) - 10000) < 1 and abs((b[3] - b[1]) - 10000) < 1 else "FAIL",
                 f"training box {pid}", f"{(b[2]-b[0])/1000:.1f} x {(b[3]-b[1])/1000:.1f} km in EPSG:32610")
        else:
            line("FAIL", f"training box {pid}", "missing")


def crop_hist(pid):
    f = OUT_DIR / pid / "crop_history.json"
    return {r["year"]: r for r in load(f)["years"]} if f.exists() else None


def check_cdl():
    h = crop_hist("car_colusa_rice")
    if h is None:
        line("FAIL", "CAR CDL", "crop_history.json missing")
    else:
        for y, want in [(2021, "Rice"), (2022, "Fallow/Idle Cropland"), (2023, "Rice")]:
            r = h.get(y)
            ok = r is not None and r["majority_name"] == want
            line("PASS" if ok else "FAIL", f"CAR CDL {y} is {want}",
                 f"majority {r['majority_name']} ({r['purity_pct']}% of {r['n_pixels']} px)" if r else "no data")
    h = crop_hist("caf_tulare_forage")
    if h is None:
        line("FAIL", "CAF CDL", "crop_history.json missing")
    else:
        alf = [y for y, r in h.items() if r["majority_name"] == "Alfalfa"]
        corn = [y for y, r in h.items() if r["majority_name"] == "Corn"]
        ok = len(alf) + len(corn) >= len(h) / 2
        line("PASS" if ok else "FAIL", "CAF CDL alfalfa/corn history",
             f"{len(alf) + len(corn)}/{len(h)} years Alfalfa or Corn; Alfalfa {alf}; Corn {corn}")
        y23 = h.get(2023)
        line("INFO", "CAF CDL 2023", f"{y23['majority_name']} ({y23['purity_pct']}%)" if y23 else "no data")


def check_series():
    for pid in PRESETS:
        for src in ("s2", "landsat"):
            f = CACHE_DIR / pid / f"{src}.parquet"
            if not f.exists():
                line("FAIL", f"{src} series {pid}", "missing parquet"); continue
            d = pd.read_parquet(f)
            cols = [c for c in d.columns if c.startswith("ndvi_")]
            v = d[cols].stack().dropna()
            ok = bool(((v >= -1) & (v <= 1)).all())
            line("PASS" if ok else "FAIL", f"NDVI in [-1,1] {src} {pid}",
                 f"{len(v)} values, min {v.min():.3f}, max {v.max():.3f}; {len(d)} scenes {d.date.min()}..{d.date.max()}")
            cf = d.clear_frac
            line("PASS" if bool(((cf >= 0) & (cf <= 1)).all()) else "FAIL", f"clear_frac in [0,1] {src} {pid}",
                 f"median {cf.median():.2f}; scenes with clear_frac>=0.5: {(cf >= 0.5).sum()}")


def check_obs_counts():
    for pid in PRESETS:
        f = OUT_DIR / pid / "calendar.json"
        if not f.exists():
            line("FAIL", f"obs counts {pid}", "calendar.json missing"); continue
        cal = load(f)
        parts, low = [], []
        for y in cal["years"]:
            s = y["summary"]
            parts.append(f"{y['year']}:{s['n_obs']}({s['n_obs_s2']}/{s['n_obs_landsat']})")
            if s["n_obs"] < 12:
                low.append(y["year"])
        line("PASS" if not low else "FAIL", f"usable obs per year {pid} (total(S2/Landsat), need >=12)",
             " ".join(parts) + (f"; low: {low}" if low else ""))


def year_days(cal, y):
    for yy in cal["years"]:
        if yy["year"] == y:
            return yy["summary"]["days_by_class"]


def window_days(cal, start, end):
    """Days by class between two ISO dates (inclusive) from calendar segments."""
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    out = {k: 0 for k in cal["classes"]}
    for yy in cal["years"]:
        for sg in yy["segments"]:
            a, b = max(pd.Timestamp(sg["start"]), s), min(pd.Timestamp(sg["end"]), e)
            if a <= b:
                out[sg["class"]] += (b - a).days + 1
    return out


def check_calendar():
    f = OUT_DIR / "car_colusa_rice" / "calendar.json"
    if f.exists():
        cal = load(f)
        d = year_days(cal, 2022)
        known = sum(v for k, v in d.items() if k != "unknown")
        share = d["bare"] / known if known else 0
        line("PASS" if share > 0.5 else "FAIL", "CAR 2022 calendar mostly bare",
             f"bare {d['bare']} of {known} known days ({100*share:.0f}%); all: {d}")
        h = crop_hist("car_colusa_rice") or {}
        winters, wins = [], 0
        for y in range(2016, 2025):
            if h.get(y, {}).get("majority_name") != "Rice":
                continue
            w = window_days(cal, f"{y}-11-01", f"{y+1}-02-28")
            winters.append(f"{y}/{str(y+1)[2:]}: water {w['water']} bare {w['bare']} partial {w['partial']} "
                           f"covered {w['covered']} unknown {w['unknown']}")
            wins += w["water"] > w["bare"]
        ok = winters and wins > len(winters) / 2
        line("PASS" if ok else "FAIL", "CAR winter (Nov-Feb after a CDL rice year) reads water rather than bare",
             f"{wins}/{len(winters)} winters with water days > bare days | " + "; ".join(winters))
    else:
        line("FAIL", "CAR calendar", "calendar.json missing")
    f = OUT_DIR / "caf_tulare_forage" / "calendar.json"
    if f.exists():
        cal = load(f)
        w = window_days(cal, "2023-03-01", "2023-06-30")
        obs = [o for yy in cal["years"] if yy["year"] == 2023 for o in yy["observations"]
               if "2023-03-01" <= o["date"] <= "2023-06-30"]
        max_ndwi = max((o["ndwi"] for o in obs), default=float("nan"))
        line("INFO", "CAF spring 2023 (Mar-Jun) water on the field",
             f"{'water seen' if w['water'] else 'no water seen'}: days {w}; {len(obs)} obs, max field-median NDWI {max_ndwi:.3f}")
    else:
        line("FAIL", "CAF calendar", "calendar.json missing")


def check_grid():
    for pid in PRESETS:
        f = OUT_DIR / pid / "grid.geojson"
        if not f.exists():
            line("FAIL", f"grid {pid}", "grid.geojson missing"); continue
        g = load(f)
        vals = [v for ft in g["features"] for k, v in ft["properties"].items()
                if k.startswith("ndvi_") and v is not None]
        ok = vals and all(-1 <= v <= 1 for v in vals)
        area = sum(ft["properties"]["area_m2"] for ft in g["features"]) / 1e4
        line("PASS" if ok else "FAIL", f"grid {pid}",
             f"{g['n_cells']} cells, clipped area {area:.2f} ha, {len([l for l in g['layers'] if l.get('key')])} NDVI layers, "
             f"values in [-1,1]: {bool(ok)}")


if __name__ == "__main__":
    check_polygons()
    check_cdl()
    check_series()
    check_obs_counts()
    check_calendar()
    check_grid()
    print(f"---- {results.count('PASS')} PASS, {results.count('FAIL')} FAIL, {results.count('INFO')} INFO")
