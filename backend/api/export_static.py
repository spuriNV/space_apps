"""Export every GET route (plus precomputed POST /score variants) to static JSON for GitHub Pages.

Run: cd backend/api && uv run python export_static.py
Output: frontend/app/public/api/<url path>.json and manifest.json. Reads only committed files; no network, no .env.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, LAYERS, PRESETS, ROOT

OUT = ROOT / "frontend" / "app" / "public" / "api"
client = TestClient(app)
files: dict[str, int] = {}
skipped: list[str] = []


def write(rel: str, data) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, separators=(",", ":"))
    p.write_text(text)
    files[rel] = len(text.encode())


def get(url: str, rel: str) -> dict | None:
    r = client.get(url)
    if r.status_code != 200:
        skipped.append(f"GET {url} -> {r.status_code}")
        return None
    d = r.json()
    write(rel, d)
    return d


def post_score(pid: str, rel: str, body: dict) -> None:
    r = client.post(f"/api/locations/{pid}/score", json=body)
    if r.status_code != 200:
        skipped.append(f"POST score {rel} {body} -> {r.status_code}")
        return
    write(rel, r.json())


def main() -> int:
    import shutil
    if OUT.exists():
        shutil.rmtree(OUT)
    get("/api/locations", "locations.json")
    get("/api/glossary", "glossary.json")
    get("/api/bc/news", "bc/news.json")
    get("/api/bc/signal", "bc/signal.json")
    crops: set[str] = set()
    for pid in PRESETS:
        base = f"/api/locations/{pid}"
        loc = get(base, f"locations/{pid}.json")
        for route, rel in [("daily", "daily"), ("features/weekly", "features/weekly"), ("strategies", "strategies"),
                           ("models", "models"), ("zones", "zones"), ("validation", "validation"), ("news", "news"),
                           ("calendar", "calendar"), ("calendar_ml", "calendar_ml"), ("grid", "grid"),
                           ("outlook", "outlook")]:
            d = get(f"{base}/{route}", f"locations/{pid}/{rel}.json")
        for layer in LAYERS:
            d = get(f"{base}/trends?layer={layer}", f"locations/{pid}/trends/{layer}.json")
            if d is None:
                continue
            for y in d.get("years", []) if isinstance(d.get("years"), list) else []:
                get(f"{base}/trends?layer={layer}&year={y}", f"locations/{pid}/trends/{layer}/{y}.json")
        base_w = {}
        variants = {"default": {}, "replay-2022": {"replay_year": 2022}, "replay-2023": {"replay_year": 2023}}
        for dt in (0, 2, 4):
            for dp in (-20, 0, 20):
                variants[f"dT{dt}_dP{dp}"] = {"scenario": {"dT_c": dt, "dP_pct": dp}}
        for name, body in variants.items():
            post_score(pid, f"locations/{pid}/score/{name}.json", {"weights": base_w, **body})
    # crops: every id in engine crops.json
    cj = ROOT / "backend" / "engine" / "crops.json"
    if cj.is_file():
        for c in json.loads(cj.read_text()).get("crops", []):
            crops.add(c["id"])
    for cid in sorted(c for c in crops if c):
        get(f"/api/crops/{cid}", f"crops/{cid}.json")
    manifest = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "total_bytes": sum(files.values()), "skipped": skipped,
                "files": [{"path": f"api/{k}", "bytes": v} for k, v in sorted(files.items())]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(files)} files, {manifest['total_bytes']/1e6:.2f} MB -> {OUT}")
    for k, v in sorted(files.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {v/1e3:9.1f} kB  {k}")
    for s in skipped:
        print("SKIPPED", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
