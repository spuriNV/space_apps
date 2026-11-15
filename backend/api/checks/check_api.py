"""Hit every route for both presets with a TestClient, validate against schemas/, print PASS/FAIL per route.
Run: cd backend/api && uv run python checks/check_api.py   (exit code 1 on any FAIL)"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from fastapi.testclient import TestClient  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402
from referencing import Registry, Resource  # noqa: E402

from app.main import ROOT, PRESETS, LAYERS, app, fieldreg  # noqa: E402

ALL_FIELDS = list(PRESETS)                      # every registry field of every region gets the core routes (below)
CA_FIELDS = fieldreg.ids(region="ca")           # California counts stay on region="ca"
BC_FIELDS = fieldreg.ids(region="bc")
PRESETS = [p for p in PRESETS if fieldreg.is_original(p)]   # the original two get every route and content check

SCHEMAS = ROOT / "schemas"
reg = Registry()
for f in SCHEMAS.glob("*.schema.json"):
    s = json.loads(f.read_text())
    reg = reg.with_resource(s["$id"], Resource.from_contents(s))
BASE = "https://fieldshift.local/schemas/"


def validator(file, defname=None):
    ref = BASE + file + (f"#/$defs/{defname}" if defname else "")
    return Draft202012Validator({"$ref": ref}, registry=reg)


client = TestClient(app)
fails = 0
SOURCES = {}  # route label (preset id replaced by {id}) -> set of X-Data-Source values seen
ESTIMATES = {}  # same, for responses served as estimates (BC stand-ins for California-only sources); kept out of SOURCES
# Routes that must be served from real output (a regression to fixture is a FAIL). Everything else may be fixture.
EXPECT_REAL = ["/api/locations", "/api/locations/{id}", "/daily", "/features/weekly", "/strategies", "/score", "/zones",
               "/trends?layer=heatwave_days", "/trends?layer=precip_anomaly", "/trends?layer=usdm_d2_weeks", "/trends?layer=reservoir_storage", "/trends?layer=grace_gw_pct", "/news", "/validation", "/calendar", "/grid", "/api/bc/news", "/api/crops/{cid}"]
EXPECT_FIXTURE_OK = {"/models": "no producer (AI workstream)", "/api/bc/signal": "SMAP/GRACE need Earthdata (blocked)",
                     }
EXPECT_REAL += ["/openet", "/nasa_now", "/nasa_series", "/insurance", "/stress", "/water_seen", "/api/glossary", "/transitions",
                "/calendar_ml", "/outlook"]
# NASA AppEEARS layers: must be real once their cache exists for both presets (backend/nasa); fixture is allowed only before that
for _layer, _ds in (("smap_anomaly", "smap_l4"), ("modis_ndvi_anomaly", "modis")):
    if all((ROOT / "data" / "cache" / _p / f"{_ds}.parquet").exists() and (ROOT / "backend/api/out" / _p / f"trends_{_layer}.json").exists()
           for _p in PRESETS):
        EXPECT_REAL.append(f"/trends?layer={_layer}")
    else:
        EXPECT_FIXTURE_OK[f"/trends?layer={_layer}"] = f"{_ds} not cached yet (AppEEARS task pending in backend/nasa)"


def check(method, url, validator_, body=None, expect=200):
    global fails
    label = f"{method} {url}"
    try:
        r = client.request(method, url, json=body)
        errs = []
        if r.status_code != expect:
            errs.append(f"status {r.status_code} != {expect}: {r.text[:120]}")
        elif expect == 200:
            data = r.json()
            src = r.headers.get("X-Data-Source")
            if src not in ("fixture", "real", "estimate") or data.get("_source") != src:
                errs.append(f"missing/inconsistent source marker header={src} field={data.get('_source')}")
            key = url.split("?")[0]
            if key.endswith("/trends"):
                key += "?layer=" + url.split("layer=")[1].split("&")[0]
            for pid in ALL_FIELDS:
                key = key.replace(pid, "{id}")
            if "/api/crops/" in key:
                key = "/api/crops/{cid}"
            if "/api/locations/{id}/" in key:
                key = "/" + key.split("/api/locations/{id}/")[1] if key.split("/api/locations/{id}/")[1] != "" else key
            (ESTIMATES if src == "estimate" else SOURCES).setdefault(key, set()).add(src)
            if src == "fixture" and data.get("_fixture") is not True:
                errs.append("fixture response lacks _fixture:true")
            errs += [f"{'/'.join(map(str, e.absolute_path))}: {e.message[:100]}" for e in list(validator_.iter_errors(data))[:3]]
        if errs:
            fails += 1; print(f"FAIL {label}  <- {'; '.join(errs)}")
        else:
            print(f"PASS {label}  [{r.headers.get('X-Data-Source', '-')}]")
        return r
    except Exception as e:  # noqa: BLE001
        fails += 1; print(f"FAIL {label}  <- exception {e!r}")


ANY = Draft202012Validator({})
check("GET", "/api/locations", validator("responses.schema.json", "Locations"))
for p in PRESETS:
    L = f"/api/locations/{p}"
    check("GET", L, validator("location.schema.json"))
    check("GET", L + "/daily?from=2023-03-01&to=2023-03-31", validator("responses.schema.json", "Daily"))
    check("GET", L + "/features/weekly", validator("responses.schema.json", "FeaturesWeekly"))
    r = check("GET", L + "/strategies", validator("responses.schema.json", "Strategies"))
    check("POST", L + "/score", validator("responses.schema.json", "Score"),
          {"weights": {"water_use": 4, "forage_value": 0}, "constraints": {}, "market_preference": "sell", "allocation": None,
           "replay_year": 2022, "scenario": {"dT_c": 2, "dP_pct": -10}})
    rs = client.post(L + "/score", json={"weights": {"water_use": 2}})
    ok = rs.status_code == 200 and all("etc_vs_openet_pct" in st["water"] and "openet_et_mm_season" in st["water"] for st in rs.json()["items"])
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} POST /score items carry water.etc_vs_openet_pct and openet_et_mm_season")
    check("POST", L + "/score", ANY, {"weights": {"bogus": 1}}, expect=422)
    check("GET", L + "/models", validator("responses.schema.json", "Models"))
    check("GET", L + "/zones", validator("responses.schema.json", "Zones"))
    for layer in LAYERS:
        check("GET", L + f"/trends?layer={layer}&year=2023", validator("responses.schema.json", "Trends"))
    check("GET", L + "/news", validator("responses.schema.json", "News"))
    check("GET", L + "/validation", validator("responses.schema.json", "Validation"))
    check("GET", L + "/calendar", ANY)
    check("GET", L + "/calendar?year=2022", ANY)
    rh = check("GET", L + "/calendar?source=hls&year=2026", ANY)
    check("GET", L + "/calendar?source=bogus", ANY, expect=422)
    ro = check("GET", L + "/openet?from=2023-01-01&to=2023-12-31", ANY)
    if ro is not None and ro.status_code == 200:
        ok = len(ro.json()["rows"]) == 12
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /openet 2023 has 12 monthly rows")
    check("GET", L + "/insurance", ANY)
    rst = check("GET", L + "/stress", ANY)
    rw = check("GET", L + "/water_seen", ANY)
    if rw is not None and rw.status_code == 200:
        j = rw.json()
        ok = len(j["scenes"]) > 0 and bool(j["summary"]) and all(0 <= s_["water_frac"] <= 1 for s_ in j["scenes"] if s_["water_frac"] is not None)
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /water_seen has {len(j['scenes'])} scenes and a summary")
    ri = client.get(L + "/insurance").json()
    ok = "share_peril_unattributed" in json.dumps(ri) or p == "car_colusa_rice"
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /insurance keeps share_peril_unattributed")
    ok = loc_ok = client.get(L).json()
    ok = bool(ok.get("dwr_unique_id")) and "ec_ds_per_m" in ok["soil"] and "texture_detail" in ok["soil"] and (ok["terrain"]["slope_mean_pct"]["value"] is not None)
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} location has dwr_unique_id, soil EC/texture, NASADEM slope")
    rn = check("GET", L + "/nasa_now", ANY)
    check("GET", L + "/nasa_now?date=2022-08-01", ANY)
    check("GET", L + "/nasa_series?from=2023-01-01&to=2023-03-31", ANY)
    if rn is not None and rn.status_code == 200:
        rd = rn.json()["readings"]
        ok = all(k in rd and rd[k]["value"] is not None for k in ("grace_gw_pct", "imerg_wy_to_date_mm"))
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /nasa_now has GRACE groundwater and IMERG season rain")
    loc = client.get(L).json()
    ok = isinstance(loc.get("nasa_datasets"), list) and any(d["status"] == "live" for d in loc["nasa_datasets"])
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} location.nasa_datasets present ({sum(d['status'] == 'live' for d in loc.get('nasa_datasets', []))} live)")
    dl = client.get(L + "/daily?from=2026-01-01").json()["rows"]
    ok = len(dl) > 250 and any(r_.get("imerg_precip_mm") is not None for r_ in dl)
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /daily reaches {dl[-1]['date'] if dl else None} with IMERG rain in 2026")
    check("GET", L + "/grid?layer=ndvi_2023_q3", ANY)
    check("GET", L + "/grid?layer=bogus", ANY, expect=422)
    crop_ids = sorted({c["crop_id"] for s in (r.json()["items"] if r else []) for c in s["calendar"]})
    for cid in crop_ids:
        check("GET", f"/api/crops/{cid}", validator("crop.schema.json"))
check("GET", "/api/locations/nope", ANY, expect=404)
check("GET", "/api/locations/nope/transitions", ANY, expect=404)

# ---- registry: list, filters, and the core routes for every field
rl = client.get("/api/locations").json()
BUILT = [p for p in ALL_FIELDS if (ROOT / "backend/api/out" / p / "location.json").exists()]   # payloads built so far
ok = rl["count"] == len(BUILT) and len(CA_FIELDS) == 14 and [i["id"] for i in rl["items"]][:2] == ["car_colusa_rice", "caf_tulare_forage"]
fails += not ok; print(("PASS" if ok else "FAIL") + f" /api/locations lists {rl['count']} built of {len(ALL_FIELDS)} registry fields ({len(CA_FIELDS)} CA), originals first")
if len(BUILT) < len(ALL_FIELDS):
    print(f"INFO registry fields not built yet (skipped by /api/locations): {[p for p in ALL_FIELDS if p not in BUILT]}")
for q, fam, cty in (("family=rice", "rice", None), ("family=forage", "forage", None), ("county=Tulare", None, "Tulare"),
                    ("county=06031", None, "06031"), ("family=forage&county=kings", "forage", "kings"),
                    ("county=Colusa", None, "Colusa"), ("family=rice&county=Kings", "rice", "Kings")):
    for rq, rg in (("", None), ("&region=ca", "ca")):   # no region filter = every region; region=ca = California only
        want = len([f for f in fieldreg.fields(fam, cty, region=rg) if f["id"] in BUILT])
        n = client.get(f"/api/locations?{q}{rq}").json()["count"]
        ok = n == want
        fails += not ok; print(("PASS" if ok else "FAIL") + f" /api/locations?{q}{rq} -> {n} (want {want})")
check("GET", "/api/locations?family=wheat", ANY, expect=422)
ok = all(i.get("family") and i.get("farmer_name") and i.get("acres") and i.get("region") in ("ca", "bc") for i in rl["items"]) and \
    all((i.get("water") or {}).get("sgma_subbasin") for i in rl["items"] if i["region"] == "ca")
fails += not ok; print(("PASS" if ok else "FAIL") + " every location item has region, family, farmer_name, acres; every CA item water.sgma_subbasin")
for p in BUILT:
    if p in PRESETS or p not in CA_FIELDS:
        continue
    L = f"/api/locations/{p}"
    check("GET", L, validator("location.schema.json"))
    check("GET", L + "/daily?from=2023-03-01&to=2023-03-31", validator("responses.schema.json", "Daily"))
    check("GET", L + "/features/weekly", validator("responses.schema.json", "FeaturesWeekly"))
    r = check("GET", L + "/strategies", validator("responses.schema.json", "Strategies"))
    ok = r is not None and r.status_code == 200 and all(s_["location_id"] == p for s_ in r.json()["items"])
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} strategies carry location_id {p}")
    check("POST", L + "/score", validator("responses.schema.json", "Score"), {"weights": {"water_use": 4}})
    for route in ("/zones", "/news", "/validation", "/calendar", "/grid?layer=ndvi_2023_q3", "/openet", "/insurance",
                  "/water_seen", "/trends?layer=heatwave_days&year=2023"):
        check("GET", L + route, ANY)
    # outputs of later steps (backend/ai, backend/outlook): checked when built, else must be a clean 404
    for route, rel in (("/models", "backend/ai/out/{p}/models.json"), ("/stress", "backend/ai/out/{p}/stress_weekly.json"),
                       ("/calendar_ml", "backend/ai/out/{p}/calendar_ml.json"), ("/transitions", "backend/ai/out/{p}/transitions.json"),
                       ("/outlook", "backend/outlook/out/{p}/outlook.json")):
        check("GET", L + route, ANY, expect=200 if (ROOT / rel.format(p=p)).exists() else 404)

# ---- British Columbia: core routes 200 + schema; California-only routes 200 with an estimate in the California shape
# (_source "estimate", schema-valid where a schema exists)
CA_ONLY = ["/openet", "/insurance", "/outlook", "/calendar_ml", "/stress", "/water_seen", "/transitions", "/models",
           "/trends?layer=usdm_d2_weeks&year=2023", "/trends?layer=reservoir_storage&year=2023"]
EST_SCHEMA = {"/models": ("responses.schema.json", "Models"), "/trends?layer=usdm_d2_weeks&year=2023": ("responses.schema.json", "Trends"),
              "/trends?layer=reservoir_storage&year=2023": ("responses.schema.json", "Trends")}
for p in BC_FIELDS:
    if p not in BUILT:
        fails += 1; print(f"FAIL {p} payloads not built (cd backend/api && uv run python ../bc/build_api.py)"); continue
    L = f"/api/locations/{p}"
    reasons = fieldreg.get(p).get("not_available", {})
    loc = check("GET", L, validator("location.schema.json"))
    if loc is not None and loc.status_code == 200:
        j = loc.json()
        ok = (j["region_adapter"] == "bc" and j.get("region") == "bc" and {g["id"] for g in j.get("data_gaps", [])} == set(reasons)
              and all(g.get("filled_with") for g in j["data_gaps"])
              and bool((j.get("water_context") or {}).get("orders")) and j["water"].get("example_limit_af_ac", {}).get("value") == 3.0
              and all(s_["network"] == "ECCC" for s_ in j["stations"]))
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} location: region bc, data_gaps = registry not_available (each with filled_with), water_context, example limit 3.0, ECCC stations")
    n = client.get(f"/api/locations?region=bc").json()
    ok = n["count"] == 1 and n["items"][0]["id"] == p and n["facets"]["region"].get("bc") == len(BC_FIELDS)
    fails += not ok; print(("PASS" if ok else "FAIL") + f" /api/locations?region=bc -> {n['count']} ({p}), region facet {n['facets'].get('region')}")
    check("GET", L + "/daily?from=2023-03-01&to=2023-03-31", validator("responses.schema.json", "Daily"))
    check("GET", L + "/features/weekly", validator("responses.schema.json", "FeaturesWeekly"))
    check("GET", L + "/validation", validator("responses.schema.json", "Validation"))
    for layer in ("heatwave_days", "precip_anomaly"):
        check("GET", L + f"/trends?layer={layer}&year=2023", validator("responses.schema.json", "Trends"))
    for layer in ("grace_gw_pct", "smap_anomaly", "modis_ndvi_anomaly"):
        built = (ROOT / "backend/api/out" / p / f"trends_{layer}.json").exists()
        check("GET", L + f"/trends?layer={layer}&year=2023", validator("responses.schema.json", "Trends") if built else ANY, expect=200 if built else 404)
    rn = check("GET", L + "/news", validator("responses.schema.json", "News"))
    if rn is not None and rn.status_code == 200:
        its = rn.json()["items"]
        ok = len(its) > 0 and all(i["query_id"].startswith("bc_") for i in its)
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /news has {len(its)} BC items and no California news")
    check("GET", L + "/nasa_series?from=2023-01-01&to=2023-12-31", ANY)
    check("GET", L + "/nasa_now?date=2023-08-16", ANY)
    has_strat = (ROOT / "backend/engine/out" / p / "strategies.json").exists()
    if has_strat:
        r = check("GET", L + "/strategies", validator("responses.schema.json", "Strategies"))
        check("POST", L + "/score", validator("responses.schema.json", "Score"), {"weights": {"water_use": 4}})
        for cid in sorted({c["crop_id"] for s_ in (r.json()["items"] if r is not None and r.status_code == 200 else []) for c in s_["calendar"]}):
            check("GET", f"/api/crops/{cid}", validator("crop.schema.json"))
    else:
        print(f"INFO {p} engine strategies not built yet (backend/engine/out/{p}/strategies.json); /strategies must 404")
        check("GET", L + "/strategies", ANY, expect=404)
    for route, rel in (("/calendar", "backend/field/out/{p}/calendar.json"), ("/grid", "backend/field/out/{p}/grid.geojson"),
                       ("/zones", "backend/api/out/{p}/zones.json"), ("/calendar?source=hls", "backend/nasa/out/{p}/calendar_hls.json")):
        check("GET", L + route, ANY, expect=200 if (ROOT / rel.format(p=p)).exists() else 404)
    for route in CA_ONLY:
        r = check("GET", L + route, validator(*EST_SCHEMA[route]) if route in EST_SCHEMA else ANY)
        j = r.json() if r is not None and r.status_code == 200 else {}
        ok = j.get("_source") == "estimate" and r.headers.get("X-Data-Source") == "estimate" and bool(j.get("estimate_note") or j.get("note"))
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} {route} is an estimate (_source {j.get('_source')})")
    ro = client.get(L + "/openet?from=2023-01-01&to=2023-12-31").json()
    ok = len(ro.get("rows", [])) == 12 and "OpenET does not cover BC" in ro.get("note", "")
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /openet estimate: 2023 has {len(ro.get('rows', []))} monthly rows, note says OpenET does not cover BC")
    ri = client.get(L + "/insurance").json()
    shares = next(iter(ri.get("profiles", {}).values()), {}).get("shares", {})
    ok = set(shares) == {"share_drought", "share_excess_moisture", "share_heat", "share_other"} and all(v["method"] == "assumed" and v.get("note") for v in shares.values()) \
        and abs(sum(v["value"] for v in shares.values()) - 1) < 0.01
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /insurance estimate: four RMA-style shares, method assumed with notes, summing to 1")
    rw = client.get(L + "/water_seen").json()
    ok = len(rw.get("scenes", [])) > 0 and bool(rw.get("summary")) and all(0 <= s_["water_frac"] <= 1 for s_ in rw["scenes"])
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /water_seen estimate has {len(rw.get('scenes', []))} scenes and a summary")
    rf = check("GET", L + "/first_nations", validator("first_nations.schema.json"))
    if rf is not None and rf.status_code == 200:
        j = rf.json(); lf = client.get(L).json().get("first_nations") or {}
        ok = (j["engagement_steps"][0].startswith("Contact Splatsin first") and j["lower_river_nation"]["nation"] == "Splatsin"
              and j["nearby"] == sorted(j["nearby"], key=lambda r_: r_["distance_to_field_km"]) and j["nearest_km"] == j["nearby"][0]["distance_to_field_km"]
              and lf.get("statement") == j["statement"] and lf.get("nearest_km") == j["nearest_km"])
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /first_nations: Splatsin first, nearby sorted, nearest {j['nearest_km']} km, summary in location.json")
    if (ROOT / "data/cache" / p / "reserves_nearby.geojson").exists():
        rg_ = check("GET", L + "/first_nations/reserves.geojson", ANY)
        ok = rg_ is not None and rg_.status_code == 200 and rg_.json()["type"] == "FeatureCollection" and len(rg_.json()["features"]) > 0
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} reserves.geojson is a FeatureCollection")
for p in CA_FIELDS[:2]:   # First Nations context is BC only
    for route in ("/first_nations", "/first_nations/reserves.geojson"):
        r = check("GET", f"/api/locations/{p}{route}", ANY, expect=404)
        ok = r is not None and "built for the BC example field only" in r.json().get("detail", "")
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} {route} 404 BC only")
for p in CA_FIELDS[:2]:   # California is untouched by the BC gate
    for route in ("/openet", "/insurance", "/water_seen"):
        check("GET", f"/api/locations/{p}{route}", ANY)
check("GET", "/api/bc/news", validator("responses.schema.json", "News"))
check("GET", "/api/bc/signal", validator("responses.schema.json", "BcSignal"))
rg = check("GET", "/api/glossary", validator("responses.schema.json", "Glossary"))
if rg is not None and rg.status_code == 200:
    its = rg.json()["items"]
    ok = len(its) >= 15 and all(len(i["short"].split()) <= 60 and i.get("source_url") for i in its)
    fails += not ok; print(("PASS" if ok else "FAIL") + f" glossary: {len(its)} entries, each <= 60 words with a source URL")
# real vs fixture report
print("\nroute data source (X-Data-Source over both presets):")
for k in sorted(SOURCES):
    v = "/".join(sorted(SOURCES[k]))
    flag = ""
    if k in EXPECT_REAL and v != "real":
        fails += 1; flag = "  <- FAIL expected real"
    elif k in EXPECT_FIXTURE_OK and v != "real":
        flag = f"  (fixture: {EXPECT_FIXTURE_OK[k]})"
    print(f"  {v:8s} {k}{flag}")
if ESTIMATES:
    print("\nroutes served as estimates (BC stand-ins for California-only sources):")
    for k in sorted(ESTIMATES):
        print(f"  {'/'.join(sorted(ESTIMATES[k])):8s} {k}")
# CORS
r = client.options("/api/locations", headers={"Origin": "http://localhost:5171", "Access-Control-Request-Method": "GET"})
ok = r.headers.get("access-control-allow-origin") == "http://localhost:5171"
fails += not ok; print(("PASS" if ok else "FAIL") + " CORS preflight localhost:5171")
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAIL'}")
sys.exit(1 if fails else 0)
