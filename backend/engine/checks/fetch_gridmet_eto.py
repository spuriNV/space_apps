"""One-off: OpenET's gridMET reference ET (monthly, field polygon) for the ETo comparison in validate_et.py.

Run from backend/engine: uv run python checks/fetch_gridmet_eto.py   (uses 1 OpenET query per preset)
Key: OPENET_API_KEY in the repo-root .env (never printed or stored). Endpoint quirks follow
backend/ground/src/openet.py (flat `geometry` array, Authorization header without Bearer).
Output: backend/engine/.cache/<preset>/gridmet_eto.parquet (+ .meta.json). Validation input only; never an engine input.
"""
import json
import sys
from pathlib import Path

import urllib.error
import urllib.request

import pandas as pd

CHUNK = Path(__file__).resolve().parents[1]
REPO = CHUNK.parents[1]
URL = "https://openet-api.org/raster/timeseries/polygon"


def key():
    for line in (REPO / ".env").read_text().splitlines():
        if line.strip().startswith("OPENET_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("BLOCKED: no OPENET_API_KEY in .env")


def main(presets):
    k = key()
    for p in presets:
        out = CHUNK / ".cache" / p / "gridmet_eto.parquet"
        if out.exists():
            print(p, "cached", out); continue
        g = json.loads((REPO / "backend/field/polygons" / f"{p}.geojson").read_text())["features"][0]["geometry"]
        body = {"date_range": ["2016-01-01", "2025-12-31"], "interval": "monthly",
                "geometry": [round(x, 6) for pt in g["coordinates"][0][:-1] for x in pt], "reducer": "mean",
                "model": "Ensemble", "variable": "ETo", "reference_et": "gridMET", "units": "mm", "file_format": "JSON"}
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
            "Authorization": k, "accept": "application/json", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                js = json.load(resp)
        except urllib.error.HTTPError as e:
            print(p, "HTTP", e.code, e.read()[:300]); continue
        rows = js if isinstance(js, list) else js.get("data", [])
        df = pd.DataFrame([{"date": pd.to_datetime(x.get("time") or x.get("date")),
                            "eto_mm": next(x[c] for c in x if c not in ("time", "date"))} for x in rows])
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)
        out.with_suffix(".meta.json").write_text(json.dumps(
            {"url": URL, "params": {kk: v for kk, v in body.items() if kk != "geometry"},
             "geometry_source": f"backend/field/polygons/{p}.geojson outer ring", "rows": len(df),
             "fetched_at": pd.Timestamp.now("UTC").isoformat(), "raw_keys": list(rows[0].keys()) if rows else [],
             "note": "gridMET grass reference ETo as served by OpenET; validation only"}, indent=1))
        print(p, len(df), "rows ->", out)


if __name__ == "__main__":
    main(sys.argv[1:] or ["car_colusa_rice", "caf_tulare_forage"])
