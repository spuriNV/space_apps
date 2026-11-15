"""Pre-build the farm catalog: run the any-location tier-1 pipeline (backend/api/app/anyloc) for every field in
out/selection.json and write the committed outputs the API serves instantly:

  backend/api/out/catalog/<pt_id>/location.json    location payload (schemas/location.schema.json) + `sections` + `_catalog`
  backend/api/out/catalog/<pt_id>/strategies.json.gz  Strategies envelope (engine, family rotation set), gzip
  backend/api/out/catalog/index.json               [{id, name, lat, lon, region, area, crop_group, county, acres, family, ...}]

Daily rows are not written: GET /api/locations/<pt_id>/daily stays lazy (NASA POWER, cached per cell).
Polite to upstreams: CONCURRENCY points at a time (POWER is cached per 0.5 x 0.625 deg cell, so neighbours share one
download; ACI is fetched two years at a time; SDA, CroplandCROS, DWR and ECCC see a handful of calls per point).

Run (uses the API venv): cd backend/api && uv run python ../catalog/build.py [--only pt_...,pt_...] [--missing]
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import gzip
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "backend" / "api"))
from app.anyloc import STORE, TIER1  # noqa: E402
from app.anyloc import build as B  # noqa: E402

SEL = HERE / "out" / "selection.json"
OUT = REPO / "backend" / "api" / "out" / "catalog"
CONCURRENCY = 3


def rnd(x):
    if isinstance(x, float):
        return x if x != x or x in (float("inf"), float("-inf")) else float(f"{x:.5g}")
    if isinstance(x, dict):
        return {k: rnd(v) for k, v in x.items()}
    if isinstance(x, list):
        return [rnd(v) for v in x]
    return x


def validator():
    from jsonschema import Draft202012Validator  # noqa: PLC0415
    from referencing import Registry, Resource  # noqa: PLC0415
    reg = Registry()
    for f in (REPO / "schemas").glob("*.schema.json"):
        s = json.loads(f.read_text())
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    return Draft202012Validator({"$ref": "https://fieldshift.local/schemas/location.schema.json"}, registry=reg)


def _outline(f):
    o = f.get("outline")
    return {"type": "Polygon", "coordinates": [o]} if o and f["region"] not in ("ca", "bc") else None


async def build_one(f, sem, V):
    lon, lat = f["pt"]
    async with sem:
        for attempt in range(3):
            t = time.time()
            try:
                loc, _daily, items, info = await asyncio.wait_for(B.analyse(lat, lon, STORE, outline=_outline(f)), 150)
            except Exception as e:  # noqa: BLE001
                print(f"  {f['id']} attempt {attempt + 1} failed: {type(e).__name__} {str(e)[:120]}")
                await asyncio.sleep(5 * (attempt + 1))
                continue
            errored = [k for k in TIER1 if info["sections"].get(k, {}).get("status") == "error"]
            if errored and attempt < 2:
                print(f"  {f['id']} attempt {attempt + 1}: errored sections {errored}; retrying")
                await asyncio.sleep(5 * (attempt + 1))
                continue
            break
        else:
            return None
    region_name = f["area"]
    loc["name"] = f["name"]
    loc["farmer_name"] = f["name"]
    loc["why_chosen"] = (f"Part of the CropLytics farm catalog ({region_name}, {f['crop_group_label'].lower()}): picked from "
                         + ("the DWR / Land IQ 2023 crop map, checked against the 2023 Cropland Data Layer. " if f["region"] == "ca" else
                               "the USDA Crop Sequence Boundaries (field outline and crop history). " if f["region"].startswith("us-") else
                               "the AAFC Annual Crop Inventory 2025 (field outline from a single-crop patch). " if f["region"].startswith("can-") else
                               "the AAFC Annual Crop Inventory 2025 inside a ParcelMap BC parcel in the Agricultural Land Reserve. ")
                         + loc["why_chosen"].removeprefix("You tapped this spot on the map. "))
    errs = [e.message[:160] for e in V.iter_errors(loc)]
    built = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    cat = {"id": f["id"], "name": f["name"], "region": f["region"], "region_name": region_name, "crop_group": f["crop_group"],
           "crop_group_label": f["crop_group_label"], "built_at": built, "timings_ms": info["timings_ms"], "selection": f["source"],
           "selection_rule": "backend/catalog/select.py", "schema_errors": errs}
    d = OUT / f["id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "location.json").write_text(json.dumps(rnd({**loc, "sections": info["sections"], "_catalog": cat}), separators=(",", ":")))
    if items:   # gzip: ~200 kB of engine output per field raw, ~30 kB compressed (keeps the catalog under ~10 MB)
        with gzip.open(d / "strategies.json.gz", "wt", compresslevel=9) as fh:
            json.dump(rnd({"location_id": f["id"], "items": items, "template": loc.get("template"),
                           "note": info["sections"]["strategies"].get("reason")}), fh, separators=(",", ":"))
    st = {k: info["sections"][k]["status"] for k in ("boundary", "weather", "soil", "crop_history", "strategies") if k in info["sections"]}
    print(f"{f['id']} {f['name'][:60]:60s} {time.time() - t:5.1f}s {st} schema_errs={len(errs)}")
    return f["id"]


def write_index(fields):
    idx = []
    for f in fields:
        p = OUT / f["id"] / "location.json"
        if not p.exists():
            continue
        loc = json.loads(p.read_text())
        idx.append({"id": f["id"], "name": f["name"], "lat": f["pt"][1], "lon": f["pt"][0], "region": f["region"], "area": f["area"],
                    "crop_group": f["crop_group"], "crop_group_label": f["crop_group_label"],
                    "country": f.get("country") or "CA" if f["region"] == "bc" else f.get("country") or "US", "state": f.get("state") or ("BC" if f["region"] == "bc" else "CA"),
                    "county": f["county"] if f.get("country") else loc.get("county_name") or f["county"], "acres": loc.get("acres"), "family": loc.get("family"),
                    "template": loc.get("template"), "land_status": (loc.get("land_status") or {}).get("kind"),
                    "strategies": (OUT / f["id"] / "strategies.json.gz").exists()})
    (OUT / "index.json").write_text(json.dumps(idx, indent=0, separators=(",", ":")) + "\n")
    return idx


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated catalog ids")
    ap.add_argument("--missing", action="store_true", help="only ids without a location.json yet")
    ap.add_argument("--index-only", action="store_true")
    a = ap.parse_args()
    fields = json.loads(SEL.read_text())["fields"]
    todo = fields
    if a.only:
        want = set(a.only.split(","))
        todo = [f for f in fields if f["id"] in want]
    if a.missing:
        todo = [f for f in todo if not (OUT / f["id"] / "location.json").exists()]
    if not a.index_only:
        V = validator()
        sem = asyncio.Semaphore(CONCURRENCY)
        res = await asyncio.gather(*(build_one(f, sem, V) for f in todo))
        bad = [f["id"] for f, r in zip(todo, res) if r is None]
        if bad:
            print("FAILED:", bad)
    # drop outputs no longer in the selection
    keep = {f["id"] for f in fields}
    for d in OUT.glob("pt_*"):
        if d.name not in keep:
            for x in d.iterdir():
                x.unlink()
            d.rmdir()
    idx = write_index(fields)
    print(f"index: {len(idx)} of {len(fields)} fields")


if __name__ == "__main__":
    asyncio.run(main())
