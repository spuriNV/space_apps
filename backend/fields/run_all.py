"""Run every chunk's per-field steps for every registry field, skipping steps whose outputs already exist.

Stdlib only. From the repo root:
    python3 backend/fields/run_all.py                    # all steps, all fields that still need them
    python3 backend/fields/run_all.py --list             # what is done / to do, per step and field (no network)
    python3 backend/fields/run_all.py --fields car_glenn_rice,caf_goshen_forage
    python3 backend/fields/run_all.py --only field,regional
    python3 backend/fields/run_all.py --force engine.strategies --fields car_glenn_rice

Each step calls the chunk's own script (in that chunk's uv env) with FIELDSHIFT_FIELDS set to the fields that still need
it, so one process handles all of them: fields that share a coarse cell are read once (POWER 0.5 deg: copied between
fields in the same cell; IMERG 0.1 deg and GRACE 0.25 deg: one OPeNDAP hyperslab per granule for all fields; SMAP,
MODIS, ECOSTRESS: one AppEEARS point task for all fields; DSWx: each WTR tile downloaded once for every field on it).
Keyed steps need the repo-root .env (Earthdata, OpenET). OpenET is checked against the account's monthly quota first.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import fieldreg  # noqa: E402

B = REPO / "backend"
C = REPO / "data" / "cache"


def cache(name):
    return lambda f: C / f / name


def out(chunk, name):
    return lambda f: B / chunk / "out" / f / name


# (step id, chunk dir, command, output(s) that mark the step done, which fields)
STEPS = [
    ("field.cdl", "field", ["uv", "run", "python", "-m", "fieldshift_field.cdl"], [cache("cdl.meta.json")], None),
    ("field.polygon", "field", ["uv", "run", "python", "-m", "fieldshift_field.select_fields"],
     [lambda f: B / "field" / "polygons" / f"{f}.geojson"], None),
    ("field.crop_history", "field", ["uv", "run", "python", "-m", "fieldshift_field.crop_history"],
     [out("field", "crop_history.json")], None),
    ("field.series", "field", ["uv", "run", "python", "-m", "fieldshift_field.timeseries", "all"],
     [cache("s2.parquet"), cache("landsat.parquet")], None),
    ("field.calendar", "field", ["uv", "run", "python", "-m", "fieldshift_field.detector"], [out("field", "calendar.json")], None),
    ("field.grid", "field", ["uv", "run", "python", "-m", "fieldshift_field.grid"], [out("field", "grid.geojson")], None),
    ("regional.power", "regional", ["uv", "run", "python", "src/fetch_power.py"], [cache("power.parquet")], None),
    ("regional.derive", "regional", ["uv", "run", "python", "src/derive.py"], [out("regional", "daily_derived.parquet")], None),
    ("regional.ncei", "regional", ["uv", "run", "python", "src/fetch_ncei.py"], [cache("ncei.parquet")], None),
    ("regional.soil", "regional", ["uv", "run", "python", "src/fetch_ssurgo.py"], [cache("soil.json")], None),
    ("regional.usdm", "regional", ["uv", "run", "python", "src/fetch_usdm.py"], [cache("usdm.parquet")], None),
    ("regional.cdec", "regional", ["uv", "run", "python", "src/fetch_cdec.py"], [cache("cdec.parquet")], None),
    ("fields.water", ".", [sys.executable, "-I", str(HERE / "water_sources.py")], [lambda f: "water" if fieldreg.get(f).get("water") else None], "args"),
    ("nasa_open.terrain", "nasa_open", ["uv", "run", "python", "-m", "nasa_open.terrain"], [out("nasa_open", "terrain.json")], None),
    ("nasa.imerg", "nasa", ["uv", "run", "python", "fetch_imerg.py", "--from2000"], [cache("imerg.parquet")], None),
    ("nasa.grace", "nasa", ["uv", "run", "python", "fetch_grace.py"], [cache("grace.parquet")], None),
    ("nasa.smap_l3", "nasa", ["uv", "run", "python", "fetch_smap_l3.py"], [cache("smap_l3.parquet")], None),
    ("nasa.smap_l4", "nasa", ["uv", "run", "python", "fetch_smap_l4_opendap.py"], [cache("smap_l4.parquet")], None),
    ("nasa.modis", "nasa", ["uv", "run", "python", "fetch_modis.py"], [cache("modis.parquet")], None),
    ("nasa.ecostress", "nasa", ["uv", "run", "python", "fetch_ecostress.py"], [cache("ecostress.parquet")], None),
    ("nasa.dswx", "nasa", ["uv", "run", "python", "fetch_dswx.py"], [cache("dswx.parquet")], None),
    ("ground.openet", "ground", ["uv", "run", "python", "src/openet.py"], [cache("openet.parquet")], "openet"),
    ("ground.rma", "ground", ["uv", "run", "python", "src/rma.py"], [out("ground", "rma_profile.json")], None),
    ("ai.inputs", "ai", ["uv", "run", "python", "-m", "fieldshift_ai.inputs"], [lambda f: C / f / "ai" / "obs_field.parquet",
                                                                              lambda f: C / f / "ai" / "weekly.parquet"], None),
    ("ai.calendar_ml", "ai", ["uv", "run", "python", "-m", "fieldshift_ai.bare_cover"], [out("ai", "calendar_ml.json")], None),
    ("ai.stress", "ai", ["uv", "run", "python", "-m", "fieldshift_ai.stress"], [out("ai", "stress_weekly.json")], None),
    ("engine.strategies", "engine", ["uv", "run", "rotation-engine"], [out("engine", "strategies.json")], None),
    ("outlook.cpc", "outlook", ["uv", "run", "python", "src/fetch_cpc.py"], [lambda f: _in_combined("cpc.json", f)], None),
    ("outlook.water", "outlook", ["uv", "run", "python", "src/fetch_water.py"], [lambda f: _in_combined("water_now.json", f)], None),
    ("outlook.history", "outlook", ["uv", "run", "python", "src/history.py"], [lambda f: _in_combined("history.json", f)], None),
    ("outlook.irrigation", "engine", ["uv", "run", "python", "../outlook/src/irrigation.py"],
     [lambda f: _in_combined("irrigation.json", f)], None),
    ("outlook.build", "outlook", ["uv", "run", "python", "src/build_outlook.py"], [out("outlook", "outlook.json")], None),
    ("api.build", "api", ["uv", "run", "python", "build_real.py"], [out("api", "location.json")], "args"),
]


def _in_combined(name, f):
    p = B / "outlook" / "out" / name
    return name if p.exists() and f in json.loads(p.read_text()).get("presets", {}) else None


def done(step, f) -> bool:
    for fn in step[3]:
        r = fn(f)
        if r is None or (isinstance(r, Path) and not r.exists()):
            return False
    return True


def openet_quota():
    """(used, limit) from OpenET's account endpoint; None if no key or unreachable."""
    env = {}
    if (REPO / ".env").exists():
        for line in (REPO / ".env").read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    key = os.environ.get("OPENET_API_KEY") or env.get("OPENET_API_KEY")
    if not key:
        return None
    req = urllib.request.Request("https://openet-api.org/account/status", headers={"Authorization": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            s = json.loads(r.read())["Monthly Requests"]   # e.g. "5 used of 100"
        used, limit = s.split(" used of ")
        return int(used), int(limit)
    except Exception as e:  # noqa: BLE001
        print("  OpenET quota check failed:", e)
        return None


def sync_registry():
    """Write NOAA stations chosen by backend/regional (fetch_ncei.py) back into registry.json where they are null."""
    doc = json.loads(fieldreg.REGISTRY.read_text())
    changed = False
    for f in doc["fields"]:
        m = C / f["id"] / "ncei.meta.json"
        if not f.get("ncei_stations") and m.exists():
            f["ncei_stations"] = [s["station"] for s in json.loads(m.read_text())["selected_stations"]]
            changed = True
    if changed:
        fieldreg.REGISTRY.write_text(json.dumps(doc, indent=1) + "\n")
        fieldreg._load.cache_clear()
        print("registry: NOAA stations written back")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fields", help="comma-separated ids (default: whole registry)")
    ap.add_argument("--only", help="comma-separated chunk names or step ids (e.g. field,nasa.dswx)")
    ap.add_argument("--force", help="comma-separated step ids to rerun even if outputs exist")
    ap.add_argument("--list", action="store_true", help="print status only")
    ap.add_argument("--keep-going", action="store_true", help="continue after a failed step")
    a = ap.parse_args()
    ids = a.fields.split(",") if a.fields else fieldreg.ids()
    for f in ids:
        fieldreg.get(f)
    only = set(a.only.split(",")) if a.only else None
    force = set(a.force.split(",")) if a.force else set()
    failed = []
    for step in STEPS:
        sid, chunk, cmd, _, mode = step
        if only and sid not in only and sid.split(".")[0] not in only:
            continue
        todo = [f for f in ids if sid in force or not done(step, f)]
        if a.list:
            print(f"{sid:20s} {'done' if not todo else 'TODO ' + ','.join(todo)}")
            continue
        if not todo:
            print(f"[skip] {sid}: done for all {len(ids)} fields")
            continue
        if mode == "openet":
            q = openet_quota()
            if q is None:
                print(f"[blocked] {sid}: no OpenET key or quota unknown; not run"); continue
            used, limit = q
            print(f"  OpenET quota: {used} of {limit} used this month; {len(todo)} queries needed")
            if used + len(todo) > limit - 5:   # keep a margin of 5
                print(f"[blocked] {sid}: would exceed the monthly quota; not run"); continue
        full = cmd + (todo if mode == "args" else [])
        env = {**os.environ, "FIELDSHIFT_FIELDS": ",".join(todo)}
        print(f"[run] {sid} for {len(todo)} field(s): {' '.join(full[:6])} ...", flush=True)
        t0 = time.time()
        r = subprocess.run(full, cwd=B / chunk if chunk != "." else REPO, env=env)
        print(f"[{'ok' if r.returncode == 0 else 'FAIL'}] {sid} in {time.time() - t0:.0f}s", flush=True)
        if sid == "regional.ncei":
            sync_registry()
        if r.returncode != 0:
            failed.append(sid)
            if not a.keep_going:
                break
    if failed:
        print("failed steps:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
