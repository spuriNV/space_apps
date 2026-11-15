"""PASS/FAIL checks for the British Columbia chunk (backend/bc): registry entry, caches, API payloads, the API's BC routes.
Local files only, no network.

Run (needs the API venv for jsonschema/fastapi):
    cd backend/api && uv run python ../bc/checks/run_checks.py
Exit code 1 on any FAIL. INFO lines name inputs that are still downloading (rerun ../bc/build_api.py once they land).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
API = REPO / "backend" / "api"
sys.path.insert(0, str(API))
sys.path.insert(0, str(REPO / "backend" / "fields"))
import fieldreg  # noqa: E402

FID = "bc_salmon_river_forage"
OUT = API / "out" / FID
CACHE = REPO / "data" / "cache" / FID
counts = {"PASS": 0, "FAIL": 0, "INFO": 0}


def line(status: str, name: str, msg: str):
    counts[status] += 1
    print(f"{status} | {name} | {msg}")


def ok(cond: bool, name: str, msg: str):
    line("PASS" if cond else "FAIL", name, msg)


def load(p: Path):
    return json.loads(Path(p).read_text())


# ---- registry
reg = fieldreg.get(FID)
ok(fieldreg.region(FID) == "bc" and FID in fieldreg.ids(region=None) and FID not in fieldreg.ids(), "registry",
   "region bc; listed with region=None, hidden from the default (California) list")
ok(set(reg.get("not_available", {})) >= {"openet", "insurance", "outlook", "ml_calendar", "sgma"}, "registry", "not_available reasons present")
ok(bool((reg.get("water_context") or {}).get("orders")), "registry", "water_context has the 2023 orders")

# ---- inputs (required ones FAIL, downloads still running are INFO)
for f in ("power.parquet", "eccc.parquet"):
    ok((CACHE / f).exists(), "inputs", f"data/cache/{FID}/{f}")
ok((REPO / "backend/field/polygons" / f"{FID}.geojson").exists(), "inputs", "field polygon")
for rel in (f"data/cache/{FID}/soilgrids.json", f"data/cache/{FID}/imerg.parquet", f"data/cache/{FID}/smap_l4.parquet",
            f"data/cache/{FID}/power_nrt.parquet", f"backend/field/out/{FID}/calendar.json", f"backend/field/out/{FID}/grid.geojson",
            f"backend/engine/out/{FID}/strategies.json", f"data/cache/{FID}/reserves_nearby.geojson", f"backend/nasa_open/out/{FID}/terrain.json"):
    if not (REPO / rel).exists():
        line("INFO", "inputs", f"missing {rel} (rerun build_api.py when it lands)")

# ---- payloads
for name in ("location.json", "daily.json", "features_weekly.json", "nasa_series.json", "validation.json"):
    ok((OUT / name).exists(), "payloads", f"backend/api/out/{FID}/{name}")
if (OUT / "location.json").exists():
    loc = load(OUT / "location.json")
    ok(loc["region_adapter"] == "bc" and loc.get("region") == "bc", "location", "region_adapter and region are bc")
    ok(loc["county_name"] == reg["county"]["name"] and loc["state_fips"] + loc["county_fips"] == reg["county"]["fips"], "location",
       f"county {loc['county_name']} ({reg['county']['fips']}) from the registry")
    ok(bool(loc["stations"]) and all(s["network"] == "ECCC" for s in loc["stations"]), "location", f"{len(loc['stations'])} ECCC stations")
    ok({g["id"] for g in loc.get("data_gaps", [])} == set(reg["not_available"]) and all(g["reason"] for g in loc["data_gaps"]), "location",
       "data_gaps = registry not_available, each with its reason")
    ok(all(g.get("filled_with") for g in loc["data_gaps"]), "location", "every data_gaps entry says what fills it (filled_with)")
    ok(loc.get("water_context") == reg["water_context"], "location", "water_context copied from the registry")
    lim = loc["water"].get("example_limit_af_ac") or {}
    ok(lim.get("value") == 3.0 and lim.get("method") == "assumed" and bool(lim.get("note")), "location", "water.example_limit_af_ac 3.0 (assumed, noted)")
    soil = loc["soil"]
    ok(soil["drainage_class"] == "unknown" and soil["hydrologic_group"] == "unknown", "location", "soil drainage / hydrologic group unknown")
    if (CACHE / "soilgrids.json").exists():
        ok(soil["mukey"] == "soilgrids_v2" and soil["om_pct"]["value"] is not None, "location", f"soil from SoilGrids: {soil['texture_class']}")
    else:
        line("INFO", "location", "soil block is a placeholder until SoilGrids is fetched")
if (OUT / "daily.json").exists():
    d = load(OUT / "daily.json")
    rows = d["rows"]
    ok(rows[0]["date"] == "2015-01-01" and rows[-1]["date"] >= "2026-11-01", "daily", f"{rows[0]['date']}..{rows[-1]['date']}")
    ok(any(r["eccc_precip_mm"] is not None for r in rows) and all(r["ncei_precip_mm"] is None for r in rows), "daily",
       "ECCC station columns filled, NOAA columns null")
news = REPO / "backend/news/out" / f"{FID}.json"
ok(news.exists() and all(i["query_id"].startswith("bc_") for i in load(news)), "news", "field news exists and is BC-only")

# ---- schema + API
try:
    from fastapi.testclient import TestClient
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    from app.main import app
except ImportError as e:
    line("FAIL", "api", f"run from the backend/api venv ({e})")
else:
    sreg = Registry()
    for f in (REPO / "schemas").glob("*.schema.json"):
        s = load(f)
        sreg = sreg.with_resource(s["$id"], Resource.from_contents(s))
    v = Draft202012Validator({"$ref": "https://fieldshift.local/schemas/location.schema.json"}, registry=sreg)
    c = TestClient(app)
    r = c.get(f"/api/locations/{FID}")
    errs = list(v.iter_errors(r.json())) if r.status_code == 200 else ["status"]
    ok(r.status_code == 200 and not errs, "api", f"GET /api/locations/{FID} schema-valid" + (f": {errs[0]}" if errs else ""))
    for route in ("/daily", "/features/weekly", "/nasa_series", "/validation", "/news"):
        ok(c.get(f"/api/locations/{FID}{route}").status_code == 200, "api", f"{route} 200")
    r = c.get(f"/api/locations/{FID}/first_nations")
    vf = Draft202012Validator({"$ref": "https://fieldshift.local/schemas/first_nations.schema.json"}, registry=sreg)
    ok(r.status_code == 200 and not list(vf.iter_errors(r.json())), "api", "/first_nations 200 and schema-valid")
    r = c.get("/api/locations/car_colusa_rice/first_nations")
    ok(r.status_code == 404 and "BC example field only" in r.json().get("detail", ""), "api", "CA /first_nations 404")
    # California-only routes: an estimate in the California shape, _source "estimate", schema-valid where a schema exists
    vm = Draft202012Validator({"$ref": "https://fieldshift.local/schemas/responses.schema.json#/$defs/Models"}, registry=sreg)
    vt = Draft202012Validator({"$ref": "https://fieldshift.local/schemas/responses.schema.json#/$defs/Trends"}, registry=sreg)
    any_ = Draft202012Validator({})
    for route, val in (("/openet", any_), ("/insurance", any_), ("/outlook", any_), ("/calendar_ml", any_), ("/stress", any_),
                       ("/water_seen", any_), ("/transitions", any_), ("/models", vm),
                       ("/trends?layer=usdm_d2_weeks&year=2023", vt), ("/trends?layer=reservoir_storage&year=2023", vt)):
        r = c.get(f"/api/locations/{FID}{route}")
        j = r.json() if r.status_code == 200 else {}
        errs = list(val.iter_errors(j)) if j else ["status"]
        ok(r.status_code == 200 and not errs and j.get("_source") == "estimate" and r.headers.get("X-Data-Source") == "estimate",
           "api", f"{route} 200, schema-valid, _source estimate" + (f": {str(errs[0])[:100]}" if errs else ""))

    def assumed_sns(x, path=""):   # every SourcedNumber in an estimate payload is method assumed with a note
        if isinstance(x, dict):
            if "value" in x and "method" in x and "unit" in x:
                yield path, x
            for k, v in x.items():
                yield from assumed_sns(v, f"{path}/{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x[:50]):
                yield from assumed_sns(v, f"{path}/{i}")
    for route in ("/insurance", "/outlook"):
        sns = list(assumed_sns(c.get(f"/api/locations/{FID}{route}").json()))
        bad = [p_ for p_, v in sns if v["method"] != "assumed" or not v.get("note")]
        ok(bool(sns) and not bad, "api", f"{route}: {len(sns)} SourcedNumbers, all method assumed with a note" + (f" (bad: {bad[:2]})" if bad else ""))
    j = c.get(f"/api/locations/{FID}/openet").json()
    ok("OpenET does not cover BC" in j.get("note", "") and len(j.get("rows", [])) >= 120, "api", f"/openet estimate: {len(j.get('rows', []))} monthly rows, note names the engine")
    j = c.get(f"/api/locations/{FID}/outlook").json()
    mk = {m["date"][:4] for m in j["drought"]["us_drought_monitor"].get("drought_markers", [])}
    ok({"2023", "2026"} <= mk and all(s_["temperature"]["category"] == "equal chances" for s_ in j["cpc_seasonal_outlook"]["seasons"]),
       "api", "/outlook: climatology (equal chances) with drought markers in 2023 and 2026")
    for route in ("/openet", "/insurance", "/water_seen"):   # California unchanged
        r = c.get(f"/api/locations/car_colusa_rice{route}")
        ok(r.status_code == 200 and r.json().get("_source") == "real", "api", f"CA {route} still real")

# ---- engine (backend/engine/out): BC erosion uses the station rain threshold, so the rotations differ
sf = REPO / "backend/engine/out" / FID / "strategies.json"
if sf.exists():
    st = load(sf)
    st = st.get("items", st) if isinstance(st, dict) else st
    ero = [s_["scores"]["erosion"]["value"] for s_ in st]
    ok(len(set(ero)) > 1, "engine", f"erosion differs across the BC rotations: {ero}")
    note = st[0]["exposure"]["exposed_rain_days"]["note"]
    ok("99th percentile" in note and "25 mm/day or" not in note, "engine", "exposed_rain_days note states the BC station threshold")
    pr = st[0]["scores"]["income"]["components"]["price_range"]
    ok(pr.get("value") is not None and pr["unit"] == "CAD/t" and pr["method"] == "assumed" and "CAD per USD" in pr.get("note", ""), "engine",
       f"income price_range: California hay stand-in {pr.get('value')} CAD/t, assumed, rate stated")

print(f"\n{counts['PASS']} PASS, {counts['FAIL']} FAIL, {counts['INFO']} INFO")
sys.exit(1 if counts["FAIL"] else 0)
