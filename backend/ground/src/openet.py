"""OpenET monthly ET 2016-2025 per field polygon, Ensemble + per-model. Docs: https://openet.gitbook.io/docs/reference/api-reference/raster.md
POST https://openet-api.org/raster/timeseries/polygon, header Authorization: <key> (no Bearer). Quota: free 100 queries/month,
20 req/min; so default = Ensemble (2 queries total) and --models adds 6 more queries per field."""
import sys, json, time, requests, pandas as pd
from common import *
URL = "https://openet-api.org/raster/timeseries/polygon"
MODELS = ["ensemble", "ssebop", "eemetric", "disalexi", "geesebal", "ptjpl", "sims"]

def parse(js, model):
    rows = js if isinstance(js, list) else js.get("data", js.get("results", []))
    out = []
    for r in rows:
        d = r.get("time") or r.get("date") or r.get("Date")
        v = next((r[k] for k in ("et", "ET", "value", "mean") if k in r), None)
        out.append({"date": pd.to_datetime(d), "et_mm": v, "model": model})
    return pd.DataFrame(out)

def main(models):
    key = need_key("OPENET_API_KEY")
    for preset in PRESETS:
        geom = polygon(preset); frames = []
        for m in models:
            body = {"date_range": ["2016-01-01", "2025-12-31"], "interval": "monthly", "geojson": geom, "reducer": "mean",
                    "model": m, "variable": "et", "reference_et": "gridmet", "units": "mm", "file_format": "json"}
            r = requests.post(URL, json=body, headers={"Authorization": key, "accept": "application/json", "Content-Type": "application/json"}, timeout=300)
            if r.status_code != 200:
                print(f"{preset} {m}: HTTP {r.status_code} {r.text[:300]}"); continue
            try: js = r.json()
            except Exception: print(f"{preset} {m}: non-JSON response (zip?) {r.headers.get('content-type')}"); continue
            (GROUND / "out" / preset).mkdir(parents=True, exist_ok=True)
            json.dump(js, open(GROUND / "out" / preset / f"openet_raw_{m}.json", "w"))
            frames.append(parse(js, "Ensemble" if m == "ensemble" else m)); time.sleep(4)
        if not frames: continue
        df = pd.concat(frames, ignore_index=True); df["et_mm"] = pd.to_numeric(df["et_mm"], errors="coerce")
        meta, path = write_cache(preset, "openet", df, URL, {**{k: v for k, v in body.items() if k != "geojson"}, "models": models, "geometry": "backend/field/polygons/%s.geojson" % preset})
        save_meta(meta, path, source_note="OpenET v2.1 monthly mean ET over the field polygon; validation only", verified=True)
        print(f"{preset}: {len(df)} rows -> data/cache/{preset}/openet.parquet")
if __name__ == "__main__":
    main(MODELS if "--models" in sys.argv else ["ensemble"])
