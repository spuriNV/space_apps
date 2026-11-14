"""PASS/FAIL checks for backend/nasa_open (local files; ISS URL check does HEAD requests)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, requests
HERE = Path(__file__).resolve().parents[1]; REPO = HERE.parents[1]
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]
fails = 0
def out(ok, name, msg):
    global fails
    fails += (not ok) if ok is not None else 0
    print(f"{'PASS' if ok else 'FAIL' if ok is not None else 'INFO'} | {name} | {msg}")

for p in PRESETS:
    t = json.load(open(HERE / "out" / p / "terrain.json"))
    fs = t["field_stats"]
    lo, hi = (0, 40) if p.startswith("car") else (40, 100)
    out(-5 < fs["elevation_m_mean"] < 120, f"elevation plausible {p}", f"mean {fs['elevation_m_mean']:.1f} m (range {fs['elevation_m_min']:.0f}-{fs['elevation_m_max']:.0f}); expected roughly {lo}-{hi} m for this part of the Central Valley")
    out(lo <= fs["elevation_m_mean"] <= hi, f"elevation in local band {p}", f"{fs['elevation_m_mean']:.1f} m in [{lo},{hi}]")
    sm = t["field_summary"]["slope_mean_pct"]["value"]
    out(sm < 2.5, f"slope near 0 (levelled/flat field) {p}", f"smoothed mean {sm:.2f} %, p90 {t['field_summary']['slope_p90_pct']['value']:.2f} %; raw-pixel mean {fs['slope_pct_mean']:.2f} % (radar noise)")
    n = len(t["cells"]); ok = sum(c["elevation_m"] is not None for c in t["cells"])
    g = json.load(open(REPO / "backend/field/out" / p / "grid.geojson"))
    ids = {f["properties"]["cell_id"] for f in g["features"]}
    same_ids = {c["cell_id"] for c in t["cells"]} == ids
    out(ok / len(ids) >= 0.99 and same_ids, f"cell join coverage {p}", f"{ok}/{len(ids)} grid cells have terrain values; ids match grid.geojson: {same_ids}")
    # HLS
    h = pd.read_parquet(REPO / "data/cache" / p / "hls.parquet"); u = h[h.clear_frac >= 0.5].copy()
    out(u.ndvi_med.between(-1, 1).all() and u.ndwi_med.between(-1, 1).all(), f"HLS NDVI/NDWI in [-1,1] {p}", f"{len(h)} scenes, {len(u)} usable (clear>=0.5), {u.date.min()}..{u.date.max()}, NDVI {u.ndvi_med.min():.2f}..{u.ndvi_med.max():.2f}")
    out(len(u) >= 100, f"HLS usable scenes {p}", f"{len(u)} usable; per year {u.groupby(u.date.str[:4]).size().to_dict()}")
    ref = pd.concat([pd.read_parquet(REPO / "data/cache" / p / f"{s}.parquet").assign(src=s) for s in ("s2", "landsat")])
    ref = ref[ref.clear_frac >= 0.5]
    for s in ("s2", "landsat"):
        r = ref[ref.src == s].groupby("date").ndvi_med.mean()
        hh = u.groupby("date").ndvi_med.mean()
        # same-date pairs, and +-3 day pairs interpolated from the reference
        same = pd.concat([hh, r], axis=1, keys=["hls", "ref"]).dropna()
        rd = pd.to_datetime(r.index); hd = pd.to_datetime(hh.index)
        rs = pd.Series(r.values, index=rd).sort_index()
        near = []
        for d, v in zip(hd, hh.values):
            m = rs[(rs.index >= d - pd.Timedelta(days=3)) & (rs.index <= d + pd.Timedelta(days=3))]
            if len(m): near.append((v, m.iloc[(abs(m.index - d)).argmin()]))
        a = np.array(near) if near else np.zeros((0, 2))
        if len(same) >= 5:
            c = same.hls.corr(same.ref); b = (same.hls - same.ref).mean()
            out(c > 0.9, f"HLS vs {s} same-date NDVI {p}", f"n={len(same)} r={c:.3f} bias(HLS-{s})={b:+.3f}")
        if len(a) >= 10:
            c = np.corrcoef(a[:, 0], a[:, 1])[0, 1]
            out(c > 0.85, f"HLS vs {s} within +-3 d NDVI {p}", f"n={len(a)} r={c:.3f} bias={np.mean(a[:,0]-a[:,1]):+.3f}")

# ISS
for p in PRESETS:
    f = REPO / "data/cache" / p / "iss" / "iss.json"
    if not f.exists():
        out(None, f"ISS {p}", "no iss.json (nothing found for this area, see README Blocked)"); continue
    d = json.load(open(f)); ph = d["photos"]
    bad = [x["photo_id"] for x in ph if not (x.get("photo_id") and x.get("date") and x.get("image_url"))]
    out(not bad and len(ph) > 0, f"ISS ids/dates/urls {p}", f"{len(ph)} photos; missing fields: {bad}")
    bad = []
    for x in ph:
        try:
            r = requests.head(x["image_url"], timeout=30, allow_redirects=True)
            if r.status_code != 200: bad.append((x["photo_id"], r.status_code))
        except Exception as e: bad.append((x["photo_id"], str(e)[:40]))
    out(not bad, f"ISS URLs resolve {p}", f"{len(ph)-len(bad)}/{len(ph)} HTTP 200; {bad}")
    dl = [x for x in ph if x.get("local_file")]
    out(all((REPO / x["local_file"]).exists() for x in dl) and len(dl) <= 6, f"ISS downloads {p}", f"{len(dl)} files present")
print("----", "all checks passed" if not fails else f"{fails} FAIL")
sys.exit(1 if fails else 0)
