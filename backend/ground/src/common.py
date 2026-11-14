import json, os, sys, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
GROUND = Path(__file__).resolve().parents[1]
PRESETS = ["car_colusa_rice", "caf_tulare_forage"]

def load_env():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v: os.environ.setdefault(k.strip(), v)

def need_key(name):
    load_env()
    v = os.environ.get(name, "")
    if not v:
        print(f"BLOCKED: no {name} in .env"); raise SystemExit(0)
    return v

def polygon(preset):
    g = json.load(open(ROOT / "backend" / "field" / "polygons" / f"{preset}.geojson"))
    return g["features"][0]["geometry"]

def cache_dir(preset):
    d = ROOT / "data" / "cache" / preset; d.mkdir(parents=True, exist_ok=True); return d

def write_cache(preset, name, df, url, params):
    """params must not contain secrets."""
    d = cache_dir(preset)
    df.to_parquet(d / f"{name}.parquet", index=False)
    meta = {"url": url, "params": params, "fetched_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rows": int(len(df)), "columns": list(df.columns)}
    return meta, d / f"{name}.meta.json"

def save_meta(meta, path, **extra):
    meta.update(extra); json.dump(meta, open(path, "w"), indent=1)
