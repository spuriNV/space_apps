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
    rt = check("GET", L + "/transitions", ANY)
    if rt is not None and rt.status_code == 200:
        j = rt.json()
        ok = j["location_id"] == p and rt.headers["X-Data-Source"] == "real" and any(len(v) > 0 for v in j["methods"].values())
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /transitions: real, methods {sorted(j['methods'])}")
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
# ======================================================================== /salmon (BC only; backend/bc/salmon.py) ====
def _sns(x, path=""):
    if isinstance(x, dict):
        if "value" in x and "method" in x:
            yield path, x
        for k_, v_ in x.items():
            yield from _sns(v_, f"{path}/{k_}")
    elif isinstance(x, list):
        for i_, v_ in enumerate(x):
            yield from _sns(v_, f"{path}/{i_}")


for p in BC_FIELDS:
    rs = check("GET", f"/api/locations/{p}/salmon", validator("salmon.schema.json"))
    if rs is not None and rs.status_code == 200:
        j = rs.json()
        sns = list(_sns(j))
        bad = [pa for pa, v_ in sns if v_["value"] is not None and not ((v_.get("source") or {}).get("url") and v_.get("unit") is not None)]
        ok = bool(sns) and not bad
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /salmon: {len(sns)} SourcedNumbers, each with a unit and a source url" + (f"  <- {bad[:3]}" if bad else ""))
        th = {t_["id"]: t_ for t_ in j["flow"]["thresholds"]}
        ok = (th["order_2026_m311"]["value"]["value"] == 0.625 and th["order_2023_m238"]["value"]["value"] == 1.27
              and {t_["value"]["value"] for t_ in j["temperature"]["thresholds"]} == {18.0, 20.0}
              and j["series_meta"]["flow_daily"]["unit"] == "m3/s" and j["series_meta"]["flow_realtime_latest"]["datetime_utc"])
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /salmon: order thresholds 0.625 and 1.27 m3/s, 18/20 C, series_meta units and latest timestamp")
        ok = (j["early_warning"]["label"] == "Rule of thumb, not a forecast model" and "Illustration" in j["water_for_salmon"]["scale_up"]["label"]
              and not any("partner" in s_.lower() and "no partnership" not in s_.lower() for s_ in j["respect"]["statements"]))
        fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /salmon: rule-of-thumb and illustration labels; respect block claims no partnership")
for p in CA_FIELDS[:2]:
    r = check("GET", f"/api/locations/{p}/salmon", ANY, expect=404)
    ok = r is not None and "BC example field only" in r.json().get("detail", "")
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} /salmon 404 BC only")
# ======================================================================== end /salmon ===================================
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
if rg is not None and rg.status_code == 200:   # the real glossary, not the fixture (backend/api/glossary.json, copied by the Dockerfile)
    want = json.loads((ROOT / "backend/api/glossary.json").read_text())["items"]
    ok = (rg.headers["X-Data-Source"] == "real" and "_fixture" not in rg.json() and [i["id"] for i in rg.json()["items"]] == [i["id"] for i in want]
          and "COPY backend/api/ backend/api/" in (ROOT / "Dockerfile").read_text())
    fails += not ok; print(("PASS" if ok else "FAIL") + f" /api/glossary serves backend/api/glossary.json ({len(want)} entries, real) and the Dockerfile copies it")

# ---- task 3 (API gaps found by the apps): example water limit, short_name, sanitized text, public source links
import re  # noqa: E402
LIMIT = {"rice": 5.0, "forage": 3.0}
for p in BUILT:
    if p not in CA_FIELDS:
        continue
    w = client.get(f"/api/locations/{p}").json()["water"].get("example_limit_af_ac") or {}
    ok = w.get("value") == LIMIT[fieldreg.get(p)["family"]] and w.get("unit") == "acre-ft/acre" and w.get("method") == "assumed"
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} water.example_limit_af_ac = {w.get('value')} ({w.get('method')})")
SHORT = {"car0_rice_winterflood": "Rice + winter flood (current)", "car1_rice_wintercover": "Rice + winter cover", "car2_dryyear_safflower": "Dry-year safflower",
         "car3_rice_wheat": "Rice–wheat", "caf0_alfalfa": "Alfalfa (current)", "caf1_smallgrain_corn": "Grain silage + corn",
         "caf2_smallgrain_sorghumsudan": "Grain silage + sorghum-sudan", "caf3_alfalfa_break": "Alfalfa with break year"}
for p in BUILT:
    if p not in CA_FIELDS:
        continue
    its = client.get(f"/api/locations/{p}/strategies").json()["items"]
    sc = client.post(f"/api/locations/{p}/score", json={"weights": {"water_use": 3}}).json()["items"]
    ok = len(its) == 4 and all(s_.get("short_name") == SHORT[s_["id"]] for s_ in its) and all(s_.get("short_name") == SHORT[s_["id"]] for s_ in sc)
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} every strategy (GET and POST /score) has its short_name")
MARKER = re.compile(r"\((?:U|V)\)|\((?:U|V)[:;,]|[,;] (?:U|V)\)|\bspec B\d|planner-spec B\d")
TEXT_SKIP = {"url", "source_url", "id", "meta_path", "method"}


def _strings(x, key=None):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _strings(v, k)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v, key)
    elif isinstance(x, str) and key not in TEXT_SKIP:
        yield key, x


def _links(x):
    if isinstance(x, dict):
        for k in ("url", "source_url"):
            if isinstance(x.get(k), str):
                yield x[k], x.get("internal") is True
        for v in x.values():
            yield from _links(v)
    elif isinstance(x, list):
        for v in x:
            yield from _links(v)


SAN_ROUTES = ["", "/strategies", "/zones", "/validation", "/calendar", "/news", "/insurance", "/outlook", "/models", "/water_seen",
              "/trends?layer=heatwave_days", "/trends?layer=reservoir_storage", "/transitions", "/first_nations"]
for p in ["car_colusa_rice", "caf_tulare_forage", "car_glenn_rice", *BC_FIELDS]:
    bad, links, n_methods = [], [], 0
    for route in SAN_ROUTES:
        r = client.get(f"/api/locations/{p}{route}")
        if r.status_code != 200 or r.headers.get("X-Data-Source") == "fixture":
            continue
        j = r.json()
        bad += [(route, k, s_[:90]) for k, s_ in _strings(j) if MARKER.search(s_)]
        links += [(route, u, internal) for u, internal in _links(j)]
        n_methods += json.dumps(j).count('"method": "assumed"')
    for u in ("/api/crops/alfalfa_hay", "/api/crops/rice_medium_grain"):
        j = client.get(u).json()
        bad += [(u, k, s_[:90]) for k, s_ in _strings(j) if MARKER.search(s_)]
        links += [(u, l_, i_) for l_, i_ in _links(j)]
    ok = not bad and n_methods > 0
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} no internal markers ((U), (V), spec Bx) in user-facing text; method fields kept ({n_methods} 'assumed')"
                           + (f"  <- {bad[:3]}" if bad else ""))
    unmarked = [(rt, u) for rt, u, internal in links if u and not u.startswith(("http://", "https://")) and not internal]
    ok = not unmarked and not any(rt and "/blob/" in u and not i for rt, u, i in links)
    fails += not ok; print(("PASS" if ok else "FAIL") + f" {p} every source link is public (http[s]) or marked internal: true ({sum(i for _, _, i in links)} internal of {len(links)})"
                           + (f"  <- {unmarked[:3]}" if unmarked else ""))
ro = client.get("/api/locations/car_colusa_rice/outlook").json()
lk = {u for u, _ in _links(ro)}
ok = "https://cdec.water.ca.gov/" in lk and not any(u.startswith("data/cache/") for u in lk)
fails += not ok; print(("PASS" if ok else "FAIL") + " car_colusa_rice /outlook: data/cache/<id>/cdec.parquet link served as the public CDEC page")
lw = client.get("/api/locations/car_colusa_rice").json()["water"]["lookup"]
ok = all(g["url"].startswith("https://") for g in lw.get("gsa", []) if g.get("url"))
fails += not ok; print(("PASS" if ok else "FAIL") + " car_colusa_rice water.lookup.gsa urls carry https:// (bare domains in the registry)")
from app.sanitize import clean_text, public_url  # noqa: E402
ok = (clean_text("Every alternative rotation needs review (spec B11).") == "Every alternative rotation needs review."
      and clean_text("Estimate (U): 5 of 15 peril-years") == "Estimate: 5 of 15 peril-years"
      and clean_text("Sentinel-2 L2A NDVI (B08, B04)") == "Sentinel-2 L2A NDVI (B08, B04)" and clean_text("U.S. county") == "U.S. county"
      and public_url("planner-spec.md#b4-scoring-model") == ("planner-spec.md#b4-scoring-model", True)
      and public_url("data/cache/x/power.meta.json") == ("https://power.larc.nasa.gov/", False))
fails += not ok; print(("PASS" if ok else "FAIL") + " sanitizer unit cases (spec ref, (U), band names and U.S. untouched, link mapping)")

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
# ======================================================================================================
# ---- analyse any location (app/anyloc): GET /api/analyze + pt_* sub-routes. Live upstream calls (POWER, SDA, CDL,
# DWR, FCC); a fresh temp cache so the first call is cold. Self-contained block (own helper, own counters).
# ======================================================================================================
import tempfile as _tf  # noqa: E402
import time as _t  # noqa: E402
import app.anyloc as _al  # noqa: E402

_al.CACHE = Path(_tf.mkdtemp(prefix="anyloc_check_"))
_LOC_V, _STR_V = validator("location.schema.json"), validator("responses.schema.json", "Strategies")
_DAILY_V, _SCORE_V = validator("responses.schema.json", "Daily"), validator("responses.schema.json", "Score")
_PTS = [  # (label, lat, lon, ip, expectations)
    ("rice near Colusa (DWR 2023 rice field 0602326)", 39.1894, -122.0276, "198.51.100.1", {"family": "rice", "region": "ca", "boundary": "ready", "water": "ready"}),
    ("alfalfa near Tulare (DWR 2023 alfalfa field 5412895)", 36.3110, -119.4617, "198.51.100.2", {"family": "forage", "region": "ca", "boundary": "ready", "water": "ready"}),
    ("Nevada desert (Esmeralda County)", 38.0, -117.2, "198.51.100.3", {"family": "other", "region": "other", "boundary": "unavailable", "water": "unavailable"}),
]


def _ok(cond, label):
    global fails
    fails += not cond
    print(("PASS" if cond else "FAIL") + " anyloc " + label)
    return cond


def _errs(v, d):
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message[:90]}" for e in list(v.iter_errors(d))[:3]]


print("\nanalyse any location:")
for label, lat, lon, ip, exp in _PTS:
    H = {"X-Forwarded-For": ip}
    t0 = _t.time(); r = client.get(f"/api/analyze?lat={lat}&lon={lon}", headers=H); cold = _t.time() - t0
    if not _ok(r.status_code == 200, f"{label}: GET /api/analyze 200 ({cold:.1f} s cold) {'' if r.status_code == 200 else r.text[:200]}"):
        continue
    d = r.json(); pid = d["id"]
    e = _errs(_LOC_V, d)
    _ok(not e, f"{pid}: location payload schema-valid {e}")
    _ok(r.headers.get("X-Data-Source") == "live" and d.get("_source") == "live", f"{pid}: X-Data-Source/_source = live")
    st = d["sections"]
    _ok(all(v["status"] in d["analysis"]["section_statuses"] for v in st.values()), f"{pid}: every section status in {d['analysis']['section_statuses']}")
    _ok(all(st[k]["status"] == "ready" for k in ("weather", "soil", "crop_history", "county", "strategies")),
        f"{pid}: tier 1 ready (weather, soil, crop_history, county, strategies): {[(k, st[k]['status']) for k in ('weather', 'soil', 'crop_history', 'county', 'strategies')]}")
    _ok(d["family"] == exp["family"] and d["region"] == exp["region"], f"{pid}: family {d['family']} / region {d['region']} == {exp['family']} / {exp['region']}")
    _ok(st["boundary"]["status"] == exp["boundary"] and st["water"]["status"] == exp["water"],
        f"{pid}: boundary {st['boundary']['status']}, water {st['water']['status']} (expected {exp['boundary']}, {exp['water']})")
    _ok(st["openet"]["status"] == "unavailable" and st["imerg"]["status"] == "not_computed", f"{pid}: tier 2 marked (openet unavailable, imerg not_computed)")
    _ok(cold < 20, f"{pid}: cold analysis < 20 s ({cold:.1f} s; upstream {d['analysis']['timings_ms']})")
    t0 = _t.time(); r2 = client.get(f"/api/analyze?lat={lat}&lon={lon}", headers=H); warm = _t.time() - t0
    _ok(r2.status_code == 200 and r2.json()["analysis"]["cache"] == "hit" and warm < 0.5, f"{pid}: repeat tap is a cache hit in {warm * 1000:.0f} ms")
    r3 = client.get(f"/api/locations/{pid}", headers=H)
    _ok(r3.status_code == 200 and r3.json()["id"] == pid and not _errs(_LOC_V, r3.json()), f"{pid}: GET /api/locations/{{pid}} 200, same payload")
    rs = client.get(f"/api/locations/{pid}/strategies", headers=H)
    _ok(rs.status_code == 200 and not _errs(_STR_V, rs.json()) and len(rs.json()["items"]) == 4,
        f"{pid}: /strategies 200, 4 items, schema-valid {_errs(_STR_V, rs.json()) if rs.status_code == 200 else rs.text[:120]}")
    if rs.status_code == 200:
        want = "car" if exp["family"] == "rice" else "caf"
        _ok(all(i["id"].startswith(want) and i["location_id"] == pid for i in rs.json()["items"]), f"{pid}: strategies are the {want.upper()}0-3 rotation set for this point")
    rd = client.get(f"/api/locations/{pid}/daily?from=2024-01-01&to=2024-12-31", headers=H)
    _ok(rd.status_code == 200 and not _errs(_DAILY_V, rd.json()) and len(rd.json()["rows"]) == 366
        and all(x["tmax_c"] is not None and x["eto_mm"] is not None for x in rd.json()["rows"]), f"{pid}: /daily 2024 = 366 POWER rows with ETo, schema-valid")
    rsc = client.post(f"/api/locations/{pid}/score", json={"weights": {"water_use": 4}, "scenario": {"dT_c": 2, "dP_pct": -10}}, headers=H)
    _ok(rsc.status_code == 200 and not _errs(_SCORE_V, rsc.json()) and len(rsc.json()["ranking"]) == 4,
        f"{pid}: POST /score 200, schema-valid ranking {'' if rsc.status_code == 200 else rsc.text[:150]}")
    rst = client.get(f"/api/analyze/{pid}/status")
    _ok(rst.status_code == 200 and rst.json()["cached"] is True and rst.json()["sections"]["weather"]["status"] == "ready", f"{pid}: /api/analyze/{{pid}}/status cached")
    rc = client.get(f"/api/locations/{pid}/calendar", headers=H)
    _ok(rc.status_code == 404 and "not computed for tapped points" in rc.json()["detail"], f"{pid}: /calendar 404 'not computed for tapped points'")
# guards and edge cases
r = client.get("/api/analyze?lat=95&lon=0")
_ok(r.status_code == 422, "lat out of range -> 422")
r = client.get("/api/locations/pt_n999999_w1220000")
_ok(r.status_code == 404, "malformed point id -> 404")
r = client.get("/api/locations/car_colusa_rice")
_ok(r.status_code == 200 and r.json()["_source"] == "real", "preset ids still served by the preset routes (car_colusa_rice real)")
_saved = _al.GUARD.active
_al.GUARD.active = _al.MAX_CONCURRENT        # simulate two analyses in progress
r = client.get("/api/analyze?lat=37.0&lon=-120.0&refresh=1", headers={"X-Forwarded-For": "198.51.100.9"})
_ok(r.status_code == 429 and int(r.headers.get("Retry-After", 0)) > 0, f"busy -> 429 with Retry-After ({r.status_code}, {r.headers.get('Retry-After')})")
_al.GUARD.active = _saved
_old = _al.PER_IP_MIN
_al.PER_IP_MIN = 0                           # per-IP new-spot limit reached
r = client.get("/api/analyze?lat=37.0&lon=-120.0&refresh=1", headers={"X-Forwarded-For": "198.51.100.10"})
_ok(r.status_code == 429 and "address" in r.json()["detail"], "per-IP new-spot limit -> 429")
_al.PER_IP_MIN = _old
r = client.get(f"/api/analyze?lat={_PTS[0][1]}&lon={_PTS[0][2]}", headers={"X-Forwarded-For": "198.51.100.10"})
_ok(r.status_code == 200 and r.json()["analysis"]["cache"] == "hit", "cached spots are still served when the new-spot limit is reached")
# ---- end analyse any location ================================================================================

# ===============================================================================================# ---- my fields (app/myfields): user-drawn polygons. Self-contained ids (name + outline), optional disk cache.
# ======================================================================================================
import math as _m  # noqa: E402
import app.myfields as _mf  # noqa: E402

_mf.DIR = Path(_tf.mkdtemp(prefix="myfields_check_"))
_HM = {"X-Forwarded-For": "198.51.100.50"}


def _mok(cond, label):
    global fails
    fails += not cond
    print(("PASS" if cond else "FAIL") + " myfields " + label)
    return cond


def _rect(lon, lat, w_m, h_m):
    dx, dy = w_m / 2 / (111320 * _m.cos(_m.radians(lat))), h_m / 2 / 110574
    return {"type": "Polygon", "coordinates": [[[lon - dx, lat - dy], [lon + dx, lat - dy], [lon + dx, lat + dy], [lon - dx, lat + dy], [lon - dx, lat - dy]]]}


print("\nmy fields:")
_rice = _rect(-122.03, 39.19, 640, 640)            # about 41 ha, Colusa rice
t0 = _t.time(); r = client.post("/api/my-fields", json={"name": "North rice", "geometry": _rice}, headers=_HM); cold = _t.time() - t0
if _mok(r.status_code == 200, f"POST /api/my-fields 200 ({cold:.1f} s cold) {'' if r.status_code == 200 else r.text[:200]}"):
    d = r.json(); fid = d["id"]
    _mok(fid.startswith("my_") and len(fid) < 1800 and d["_source"] == "user" and r.headers.get("X-Data-Source") == "user", f"id {fid[:24]}... ({len(fid)} chars), _source user")
    e = _errs(_LOC_V, d)
    _mok(not e, f"location payload schema-valid {e}")
    _mok(35 < d["area_ha"]["value"] < 45 and abs(d["acres"] - d["area_ha"]["value"] * 2.47105) < 0.2, f"geodesic area {d['area_ha']['value']} ha = {d['acres']} acres")
    st = d["sections"]
    _mok(all(v["status"] in d["analysis"]["section_statuses"] for v in st.values()), "every section status valid")
    _mok(all(st[k]["status"] == "ready" for k in ("weather", "soil", "crop_history", "county", "strategies", "boundary", "dwr_fields")),
         f"tier 1 ready {[(k, st[k]['status']) for k in ('weather', 'soil', 'crop_history', 'county', 'strategies', 'dwr_fields')]}")
    _mok(d["family"] == "rice" and d["county_name"] == "Colusa" and st["crop_history"]["points_sampled"] >= 16, f"family {d['family']}, county {d['county_name']}, {st['crop_history']['points_sampled']} CDL sample points")
    _mok(set(d["crop_history_purity"]) == set(d["crop_history"]) and all(0 < v <= 1 for v in d["crop_history_purity"].values()), "crop history has a purity per year")
    _mok(d["user_field"]["dwr_fields"] and d["user_field"]["spans"]["counties"] == ["Colusa"] and d["user_field"]["spans"]["gsas"], f"DWR fields {len(d['user_field']['dwr_fields'])}, spans {d['user_field']['spans']}")
    _mok(sum(m["area_share"] for m in d["soil"]["map_units"]) > 0.99, f"soil area-weighted over {len(d['soil']['map_units'])} map units")
    _mok(cold < 25, f"cold create < 25 s ({cold:.1f} s; {d['analysis']['timings_ms']})")
    r2 = client.get(f"/api/my-fields/{fid}"); _mok(r2.status_code == 200 and r2.json()["analysis"]["cache"] == "hit" and r2.json()["name"] == "North rice", "GET /api/my-fields/{id} 200 (cache hit)")
    r3 = client.get(f"/api/locations/{fid}"); _mok(r3.status_code == 200 and r3.json()["id"] == fid and not _errs(_LOC_V, r3.json()), "GET /api/locations/{id} 200 schema-valid")
    # fresh process: no cache at all, the id alone is enough
    _old_dir = _mf.DIR; _mf.DIR = Path(_tf.mkdtemp(prefix="myfields_fresh_"))
    t0 = _t.time(); r4 = client.get(f"/api/my-fields/{fid}", headers={"X-Forwarded-For": "198.51.100.51"}); recompute = _t.time() - t0
    _mok(r4.status_code == 200 and r4.json()["id"] == fid and r4.json()["analysis"]["cache"] == "miss" and r4.json()["name"] == "North rice" and r4.json()["family"] == "rice",
         f"empty cache dir: id still resolves, recomputed ({recompute:.1f} s)")
    # rename = new id
    r5 = client.post("/api/my-fields", json={"name": "South rice", "geometry": r4.json()["geometry"]}, headers=_HM)
    _mok(r5.status_code == 200 and r5.json()["id"] != fid and r5.json()["name"] == "South rice", "rename gives a new id and the new name")
    rl = client.get(f"/api/my-fields?ids={fid},{r5.json()['id']},my_garbage")
    _mok(rl.status_code == 200 and [i["name"] for i in rl.json()["items"]] == ["North rice", "South rice"] and len(rl.json()["invalid"]) == 1 and rl.json()["items"][0]["computed"],
         "GET /api/my-fields?ids= summaries (2 valid, 1 invalid listed)")
    rs = client.get(f"/api/locations/{fid}/strategies", headers=_HM)
    _mok(rs.status_code == 200 and not _errs(_STR_V, rs.json()) and len(rs.json()["items"]) == 4 and all(i["id"].startswith("car") and i["location_id"] == fid for i in rs.json()["items"]),
         f"/strategies 200, CAR0-3, schema-valid {_errs(_STR_V, rs.json()) if rs.status_code == 200 else rs.text[:120]}")
    rd = client.get(f"/api/locations/{fid}/daily?from=2024-01-01&to=2024-12-31", headers=_HM)
    _mok(rd.status_code == 200 and not _errs(_DAILY_V, rd.json()) and len(rd.json()["rows"]) == 366, f"/daily 2024 = 366 rows, schema-valid {_errs(_DAILY_V, rd.json()) if rd.status_code == 200 else rd.text[:120]} {len(rd.json().get('rows', []))}")
    rsc = client.post(f"/api/locations/{fid}/score", json={"weights": {"water_use": 4}, "scenario": {"dT_c": 2, "dP_pct": -10}}, headers=_HM)
    _mok(rsc.status_code == 200 and not _errs(_SCORE_V, rsc.json()) and len(rsc.json()["ranking"]) == 4, f"POST /score 200, schema-valid {'' if rsc.status_code == 200 else rsc.text[:150]}")
    rc = client.get(f"/api/locations/{fid}/calendar")
    _mok(rc.status_code == 404 and "not computed for user-drawn fields" in rc.json()["detail"], "/calendar 404 with a reason")
    _mf.DIR = _old_dir
# bad ids -> 400
for label, bad in (("garbage", "my_notvalid!!"), ("not zlib", "my_AAAAAAAAAAAAAAAA"), ("truncated", fid[:40] if "fid" in dir() else "my_eJxLSyxK"), ("wrong prefix", "xx_abc")):
    rb = client.get(f"/api/my-fields/{bad}")
    _mok(rb.status_code == 400 and "bad field id" in rb.json()["detail"], f"bad id ({label}) -> 400 with a reason")
_mok(client.get("/api/locations/my_AAAAAAAAAAAAAAAA").status_code == 400, "bad id on /api/locations -> 400")
# invalid geometry and limits -> 422
_bow = {"type": "Polygon", "coordinates": [[[-122.03, 39.19], [-122.02, 39.20], [-122.02, 39.19], [-122.03, 39.20], [-122.03, 39.19]]]}
_circ = lambda n: {"type": "Polygon", "coordinates": [[[-122.03 + 0.004 * _m.cos(2 * _m.pi * i / n), 39.19 + 0.004 * _m.sin(2 * _m.pi * i / n)] for i in range(n)] + [[-122.03 + 0.004, 39.19]]]}
for label, geo, name, why in (
        ("self-intersecting bowtie", _bow, "x", "crosses"),
        ("401 vertices", _circ(401), "x", "400 vertices"),
        ("not a polygon", {"type": "Point", "coordinates": [-122.03, 39.19]}, "x", "Polygon or MultiPolygon"),
        ("too small (0.1 ha)", _rect(-122.03, 39.19, 30, 30), "x", "minimum"),
        ("too large (4,000 ha)", _rect(-122.03, 39.19, 6325, 6325), "x", "maximum"),
        ("out of range coordinates", {"type": "Polygon", "coordinates": [[[200, 39], [201, 39], [201, 40], [200, 39]]]}, "x", "outside"),
        ("no name", _rice, "  ", "name")):
    rv = client.post("/api/my-fields", json={"name": name, "geometry": geo}, headers=_HM)
    _mok(rv.status_code == 422 and why in rv.json()["detail"], f"{label} -> 422 ({str(rv.json().get('detail'))[:70]})")
import app.myfields.fid as _fid  # noqa: E402
# multi-part and holes (v:2 ids)
_ra, _rb = _rect(-122.03, 39.19, 640, 640), _rect(-122.00, 39.19, 640, 640)
_hole = lambda g, w, h: {"type": "Polygon", "coordinates": g["coordinates"] + [_rect(-122.03, 39.19, w, h)["coordinates"][0]]}
_rm = client.post("/api/my-fields", json={"name": "Two blocks", "geometry": {"type": "MultiPolygon", "coordinates": [_ra["coordinates"], _rb["coordinates"]]}}, headers={"X-Forwarded-For": "198.51.100.71"})
_mok(_rm.status_code == 200, f"MultiPolygon of two Colusa rectangles -> 200 {'' if _rm.status_code == 200 else _rm.text[:200]}")
if _rm.status_code == 200:
    _dm = _rm.json(); _uf = _dm["user_field"]
    _mok(_dm["geometry"]["type"] == "MultiPolygon" and _uf["parts"]["count"] == 2 and len(_uf["parts"]["items"]) == 2, "echoes MultiPolygon, user_field.parts.count == 2")
    _mok(abs(_dm["acres"] - 2 * 101.2) < 8 and abs(_dm["acres"] - sum(i["acres"] for i in _uf["parts"]["items"])) < 0.3, f"acres {_dm['acres']} = sum of parts {[i['acres'] for i in _uf['parts']['items']]}")
    _mok(not _errs(_LOC_V, _dm), f"MultiPolygon payload schema-valid {_errs(_LOC_V, _dm)}")
    _mok(_dm["sections"]["crop_history"]["points_sampled"] >= 2, "sample points taken in both parts")
_rh = client.post("/api/my-fields", json={"name": "Donut", "geometry": _hole(_ra, 300, 300)}, headers={"X-Forwarded-For": "198.51.100.72"})
_mok(_rh.status_code == 200 and _rh.json()["acres"] < client.post("/api/my-fields", json={"name": "Solid", "geometry": _ra}, headers={"X-Forwarded-For": "198.51.100.73"}).json()["acres"] - 15
     and _rh.json()["geometry"]["type"] == "Polygon" and len(_rh.json()["geometry"]["coordinates"]) == 2, f"rectangle with a hole -> fewer acres ({_rh.json().get('acres') if _rh.status_code == 200 else _rh.text[:120]})")
_ro = client.post("/api/my-fields", json={"name": "x", "geometry": {"type": "MultiPolygon", "coordinates": [_ra["coordinates"], _rect(-122.028, 39.19, 640, 640)["coordinates"]]}}, headers={"X-Forwarded-For": "198.51.100.74"})
_mok(_ro.status_code == 422 and "overlap" in _ro.json()["detail"], f"overlapping parts -> 422 ({_ro.json().get('detail')})")
_rx = client.post("/api/my-fields", json={"name": "x", "geometry": {"type": "Polygon", "coordinates": _ra["coordinates"] + [_rect(-122.0, 39.19, 100, 100)["coordinates"][0]]}}, headers={"X-Forwarded-For": "198.51.100.75"})
_mok(_rx.status_code == 422 and "inside its polygon" in _rx.json()["detail"], f"hole outside its shell -> 422 ({_rx.json().get('detail')})")
_vv1 = {"v": 1, "n": "Old id", "c": [x for i, p in enumerate(_ra["coordinates"][0][:-1]) for x in ((round(p[0] * 1e5), round(p[1] * 1e5)) if i == 0 else (round(p[0] * 1e5) - round(_ra["coordinates"][0][i - 1][0] * 1e5), round(p[1] * 1e5) - round(_ra["coordinates"][0][i - 1][1] * 1e5)))]}
import base64 as _b64, zlib as _zl, json as _js  # noqa: E402
_oldid = "my_" + _b64.urlsafe_b64encode(_zl.compress(_js.dumps(_vv1, separators=(",", ":")).encode(), 9)).rstrip(b"=").decode()
_ro1 = client.get(f"/api/my-fields/{_oldid}", headers={"X-Forwarded-For": "198.51.100.76"})
_mok(_ro1.status_code == 200 and _ro1.json()["name"] == "Old id" and 35 < _ro1.json()["area_ha"]["value"] < 45, f"old v:1 id still loads ({_ro1.status_code})")
_i2, _p2, _h2, _ = _fid.encode("rt", _hole(_ra, 300, 300))
_mok(_fid.decode(_i2)[1] == _p2 and _fid.decode(_i2)[1]["type"] == "Polygon", "v:2 id with a hole round-trips")
# 200 corners fit in an id (simplified if needed)
_noisy = {"type": "Polygon", "coordinates": [[[-122.03 + (0.004 + 0.0004 * ((i * 7919) % 13) / 13) * _m.cos(2 * _m.pi * i / 200), 39.19 + (0.004 + 0.0004 * ((i * 7919) % 13) / 13) * _m.sin(2 * _m.pi * i / 200)] for i in range(200)]]}
_noisy["coordinates"][0].append(_noisy["coordinates"][0][0])
_i, _p, _h, _n = _fid.encode("noisy", _noisy)
_mok(len(_i) <= 1800 and _fid.decode(_i)[1] == _p, f"200-corner outline: id {len(_i)} chars, round-trips ({'simplified ' + str(_n['corners_before']) + ' -> ' + str(_n['corners_after']) if _n else 'not simplified'})")
# limiter
_o = _mf.PER_IP_MIN; _mf.PER_IP_MIN = 0
rr = client.post("/api/my-fields", json={"name": "limit", "geometry": _rect(-122.05, 39.2, 600, 600)}, headers={"X-Forwarded-For": "198.51.100.60"})
_mok(rr.status_code == 429 and int(rr.headers.get("Retry-After", 0)) > 0, "per-IP limit -> 429 with Retry-After")
_mf.PER_IP_MIN = _o
_sv = _mf.GUARD.active; _mf.GUARD.active = _mf.MAX_CONCURRENT
rr = client.post("/api/my-fields", json={"name": "limit", "geometry": _rect(-122.05, 39.2, 600, 600)}, headers={"X-Forwarded-For": "198.51.100.61"})
_mok(rr.status_code == 429, "concurrency bound -> 429")
_mf.GUARD.active = _sv
# ---- BEGIN BC drawn field (myfields/build.py analyse_bc) ------------------------------------------------------
_rbc = client.post("/api/my-fields", json={"name": "Fraser Valley", "geometry": _rect(-122.52, 49.09, 450, 450)}, headers={"X-Forwarded-For": "198.51.100.80"})
if _mok(_rbc.status_code == 200, f"BC drawn field 200 {'' if _rbc.status_code == 200 else _rbc.text[:200]}"):
    _bc = _rbc.json()
    _mok(not _errs(_LOC_V, _bc), f"BC drawn field schema-valid {_errs(_LOC_V, _bc)}")
    _mok(_bc["region"] == "bc" and _bc.get("regional_district") and _bc["crop_history"] and _bc["sections"]["crop_history"].get("source") == "aafc_aci",
         f"BC region, regional district {_bc.get('regional_district')}, {len(_bc['crop_history'])} ACI years")
    _txt = json.dumps({k: v for k, v in _bc.items() if k not in ("soil", "nasa_datasets", "datasets", "sections", "_notes")})
    _mok("USDA" not in _txt and "US counties" not in _txt, "BC drawn field text has no USDA / US counties")
# ---- END BC drawn field ------------------------------------------------------------------------------------------
# ---- end my fields ===========================================================================================
# ======================================================================================================
# ---- Nation tools (app/nation): /api/locations/{pid}/nation[/drought_rotation|groundwater|land_season|funding|report.*]
# For First Nations and tribal farm, lands and water staff. Presets + a tapped point near Lemoore, CA. Live lookups: BC reserve WFS,
# Census AIANNH, FIRMS open CSV, NASA POWER (tapped point).
# ======================================================================================================
_NV = {k: validator("nation.schema.json", k) for k in ("Summary", "DroughtRotation", "Groundwater", "LandSeason", "Funding", "Report")}


def _nok(cond, label):
    global fails
    fails += not cond
    print(("PASS" if cond else "FAIL") + " nation " + label)
    return cond


print("\nnation tools:")
_NROUTES = [("", "Summary"), ("/drought_rotation", "DroughtRotation"), ("/groundwater", "Groundwater"), ("/land_season", "LandSeason"),
            ("/funding", "Funding"), ("/report.json", "Report")]
for _pid in ("car_colusa_rice", "caf_tulare_forage", "bc_salmon_river_forage"):
    for _suffix, _def in _NROUTES:
        if _suffix == "/groundwater" and _pid.startswith("bc_"):
            _r = client.get(f"/api/locations/{_pid}/nation/groundwater")
            _nok(_r.status_code == 404 and len(_r.json().get("detail", "")) > 20, f"{_pid}: /groundwater -> 404 with a reason (BC)")
            continue
        _r = client.get(f"/api/locations/{_pid}/nation{_suffix}", headers={"X-Forwarded-For": "198.51.100.40"})
        _bad = _errs(_NV[_def], _r.json()) if _r.status_code == 200 else _r.text[:120]
        _nok(_r.status_code == 200 and not _bad and _r.headers.get("X-Data-Source") in ("real", "live"), f"{_pid}: /nation{_suffix} 200, schema-valid {_bad or ''}")
    _r = client.get(f"/api/locations/{_pid}/nation/report.pdf")
    _nok(_r.status_code == 200 and _r.content[:5] == b"%PDF-" and len(_r.content) < 300_000 and _r.headers["content-type"] == "application/pdf",
         f"{_pid}: report.pdf is a PDF under 300 KB ({len(_r.content)} bytes)")
_r = client.get("/api/locations/car_colusa_rice/nation/funding")
_pg = _r.json()["programs"]
_nok(len(_pg) >= 10 and all(p["url"].startswith("http") for p in _pg), f"funding has >= 10 programs, all with URLs ({len(_pg)})")
_nok([p["status"] for p in _pg] == sorted((p["status"] for p in _pg), key=["open", "rolling", "unknown", "closed"].index), "funding: open programs first, closed last")
_nok(all(p["matched_reason"] for p in _pg) and any("Subbasin" in p["matched_reason"] for p in _pg), "funding: matched_reason set for every program, subbasin named where it applies")
_r = client.get("/api/locations/bc_salmon_river_forage/nation/funding")
_nok(all(set(p["jurisdictions"]) & {"BC", "CAN"} for p in _r.json()["programs"]) and any(p["id"] == "fn_adapt" for p in _r.json()["programs"]), "funding: BC location gets BC/Canada programs only, incl. First Nation Adapt")
_r = client.get("/api/locations/car_colusa_rice/nation/funding?jurisdiction=BC")
_nok(_r.status_code == 200 and _r.json()["jurisdiction"] == "BC", "funding: ?jurisdiction=BC overrides the location")
_nok(client.get("/api/locations/car_colusa_rice/nation/funding?jurisdiction=XX").status_code == 422, "funding: bad jurisdiction -> 422")
_r = client.get("/api/locations/car_colusa_rice/nation/report.pdf?program=cdfa_tfs")
_nok(_r.status_code == 200 and _r.content[:4] == b"%PDF", "report.pdf?program=cdfa_tfs")
_nok(client.get("/api/locations/car_colusa_rice/nation/report.pdf?program=nope").status_code == 422, "report.pdf: unknown program -> 422")
_r = client.get("/api/locations/car_colusa_rice/nation/drought_rotation?cutoff=07-01").json()
_a = client.get("/api/locations/car_colusa_rice/nation/drought_rotation?cutoff=09-15").json()
_nok(_r["cutoff_date"] == "07-01" and all(x["water_mm_after_cutoff"] > y["water_mm_after_cutoff"] for x, y in zip(_r["rotations"], _a["rotations"]) if x["water_mm_after_cutoff"]),
     "drought_rotation: an earlier cutoff leaves more water after it")
_nok(client.get("/api/locations/car_colusa_rice/nation/drought_rotation?cutoff=13-40").status_code == 422, "drought_rotation: bad cutoff -> 422")
_r = client.get("/api/locations/bc_salmon_river_forage/nation").json()
_nok(any(n["name"] == "Swawll Setatkwa" and n["source_url"].startswith("https://") for n in _r["place_names"]) and _r["nearest_nations"], "bc summary: place name with source, nearest Nations listed")
_r = client.get("/api/locations/car_colusa_rice/nation/land_season").json()
_nok(_r["phenology"]["peak_doy"] is not None and "proxy" in _r["phenology_note"] and "no harvest" in _r["harvest_rights_note"].lower().replace("stores no harvest", "no harvest"), "land_season: phenology with proxy caveat, harvest note")
_nok(client.get("/api/locations/nope/nation").status_code == 404, "unknown location -> 404")
# a tapped point near Lemoore, CA (cold analysis: live POWER, SSURGO, CDL, DWR)
_lem = "pt_n363000_w1197800"
_r = client.get(f"/api/locations/{_lem}/nation", headers={"X-Forwarded-For": "198.51.100.41"})
_bad = _errs(_NV["Summary"], _r.json()) if _r.status_code == 200 else _r.text[:150]
_nok(_r.status_code == 200 and not _bad and _r.json()["location"]["jurisdiction"] == "CA", f"pt near Lemoore: /nation 200, schema-valid, CA {_bad or ''}")
_r = client.get(f"/api/locations/{_lem}/nation/funding", headers={"X-Forwarded-For": "198.51.100.41"})
_bad = _errs(_NV["Funding"], _r.json()) if _r.status_code == 200 else _r.text[:150]
_nok(_r.status_code == 200 and not _bad and len(_r.json()["programs"]) >= 10, f"pt near Lemoore: /nation/funding 200, schema-valid {_bad or ''}")
_r = client.get(f"/api/locations/{_lem}/nation/drought_rotation", headers={"X-Forwarded-For": "198.51.100.41"})
_bad = _errs(_NV["DroughtRotation"], _r.json()) if _r.status_code == 200 else _r.text[:150]
_nok(_r.status_code == 200 and not _bad and _r.json()["series_status"]["grace"]["status"] == "not_computed" and _r.json()["drought_history"], f"pt near Lemoore: drought_rotation (POWER only, others not_computed) {_bad or ''}")
# user-drawn my_ field (Colusa rectangle): nation + this_week
_mid = _mf.FID.encode("Nation rice", _rect(-122.03, 39.19, 640, 640))[0]
for _suffix, _def in (("", "Summary"), ("/funding", "Funding")):
    _r = client.get(f"/api/locations/{_mid}/nation{_suffix}", headers={"X-Forwarded-For": "198.51.100.42"})
    _bad = _errs(_NV[_def], _r.json()) if _r.status_code == 200 else _r.text[:150]
    _nok(_r.status_code == 200 and not _bad, f"my_ field: /nation{_suffix} 200, schema-valid {_bad or ''}")
_r = client.get(f"/api/locations/{_mid}/this_week", headers={"X-Forwarded-For": "198.51.100.42"})
_bad = _errs(validator("this_week.schema.json"), _r.json()) if _r.status_code == 200 else _r.text[:150]
_nok(_r.status_code == 200 and not _bad, f"my_ field: /this_week 200, schema-valid {_bad or ''}")
# ---- end nation tools =========================================================================================
# ======================================================================================================
# ---- this week + reach (app/week): live Open-Meteo / NWS / NASA POWER reads, cached 3 h. Self-contained block.
# ======================================================================================================
_TW_V, _RC_V = validator("this_week.schema.json"), validator("reach.schema.json")


def _tw(cond, label):
    global fails
    fails += not cond
    print(("PASS" if cond else "FAIL") + " this_week " + label)
    return cond


print("\nthis week and reach:")
_tw_ids = ["car_colusa_rice", "caf_tulare_forage", "bc_salmon_river_forage", _al.B.point_id(_PTS[0][1], _PTS[0][2])]
for _id in _tw_ids:
    _r = client.get(f"/api/locations/{_id}/this_week")
    if not _tw(_r.status_code == 200, f"{_id}: 200 {'' if _r.status_code == 200 else _r.text[:150]}"):
        continue
    _d = _r.json()
    _e = _errs(_TW_V, _d)
    _tw(not _e, f"{_id}: schema-valid {_e}")
    _tw(len(_d["forecast"]) == 7 and bool(_d["irrigation"]["verdict"]) and len(_d["field_access"]["days"]) == 7
        and all(x["status"] in ("ok", "marginal", "too_wet") for x in _d["field_access"]["days"]) and bool(_d["field_access"]["line"]),
        f"{_id}: 7 forecast days, verdict '{_d['irrigation']['verdict']}', 7 field-access values, line '{_d['field_access']['line']}'")
    _tw(_d["label"] == "Forecast, not a guarantee" and _d["ttl_s"] == 10800, f"{_id}: label and ttl")
_r = client.get("/api/locations/car_colusa_rice/this_week")
_tw(_r.headers.get("X-Cache") == "hit", "second call is served from the 3 h cache")
_tw(client.get("/api/locations/nope_field/this_week").status_code == 404, "unknown id -> 404")
# ?lang=es (app/i18n_es.py): same shape, same ids and numbers; only prose differs. No DEEPSEEK_API_KEY -> English + X-Lang-Fallback.
_UNTOUCHED_KEYS = {"id", "url", "source_url", "unit", "units", "method", "type", "date", "crop_id", "location_id", "strategy_id", "status", "weekday"}


def _same_but_prose(a, b, key=None, path="$"):
    """Empty list when b (Spanish) equals a (English) in every key, list length, non-string leaf and every string under an id/url/unit-type key."""
    if isinstance(a, dict):
        if not isinstance(b, dict) or list(a) != list(b):
            return [path + " keys differ"]
        return [m for k in a for m in _same_but_prose(a[k], b[k], k, f"{path}.{k}")]
    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            return [path + " list length differs"]
        return [m for i, (x, y) in enumerate(zip(a, b)) for m in _same_but_prose(x, y, key, f"{path}[{i}]")]
    if isinstance(a, str):
        if not isinstance(b, str):
            return [path + " type differs"]
        return [path + f" {a!r} != {b!r}"] if (key in _UNTOUCHED_KEYS or (key or "").endswith(("_id", "_url")) or not b.strip()) and a != b else []
    return [] if a == b and type(a) is type(b) else [path + f" {a!r} != {b!r}"]


_en = client.get("/api/locations/car_colusa_rice/this_week")
_es = client.get("/api/locations/car_colusa_rice/this_week?lang=es")
if _tw(_es.status_code == 200, "lang=es: 200"):
    _fb = _es.headers.get("X-Lang-Fallback")
    _tw(_fb in (None, "en", "partial"), f"lang=es: X-Lang-Fallback {_fb!r} ({'Spanish' if not _fb else 'English fallback'})")
    _e = _errs(_TW_V, _es.json())
    _tw(not _e, f"lang=es: schema-valid like the plain call {_e}")
    _diff = _same_but_prose({k: v for k, v in _en.json().items()}, _es.json())
    _tw(not _diff, f"lang=es: keys, numbers, ids, urls and units identical to English {_diff[:3]}")
    _tw(_fb == "en" or _es.json()["irrigation"]["verdict"] != _en.json()["irrigation"]["verdict"], "lang=es: verdict is translated (or fell back to English)")
_tw(client.get("/api/locations/car_colusa_rice/this_week?lang=en").json() == client.get("/api/locations/car_colusa_rice/this_week").json(), "lang=en: unchanged")
_r = client.get("/api/reach")
_e = _errs(_RC_V, _r.json()) if _r.status_code == 200 else [_r.text[:100]]
_tw(_r.status_code == 200 and not _e, f"reach: 200, schema-valid {_e}")
_tw(_r.status_code == 200 and _r.json()["rice"]["california_planted_acres"]["value"] > 100000 and "rice" in _r.json()["pitch_line"],
    f"reach: rice acres > 100,000 ({_r.json()['rice']['california_planted_acres']['value']:,.0f}) and pitch line")
# ---- end this week + reach ====================================================================================
# ======================================================================================================
# ---- farm catalog (backend/catalog -> backend/api/out/catalog) + BC tier 1 + reserve / tribal land (app/anyloc).
# Catalog ids are served from the committed outputs (no upstream call); the BC, reserve and tribal taps are live.
# ======================================================================================================
import random as _rnd  # noqa: E402

print("\nfarm catalog:")
_rc = client.get("/api/catalog")
_cat = _rc.json() if _rc.status_code == 200 else {"items": [], "count": 0}
_idx = json.loads((ROOT / "backend/api/out/catalog/index.json").read_text()) if (ROOT / "backend/api/out/catalog/index.json").exists() else []
_ca = [x for x in _cat["items"] if x["region"] == "ca"]
_bc = [x for x in _cat["items"] if x["region"] == "bc"]
_us = [x for x in _cat["items"] if x["region"].startswith("us-")]
_can = [x for x in _cat["items"] if x["region"].startswith("can-")]
_ok(_rc.status_code == 200 and _cat["count"] == len(_idx) >= 430 and len(_ca) >= 140 and len(_bc) >= 35 and len(_us) >= 200 and len(_can) >= 38,
    f"/api/catalog lists {_cat['count']} fields (index.json {len(_idx)}): {len(_ca)} CA, {len(_bc)} BC, {len(_us)} US elsewhere, {len(_can)} Canada elsewhere")
_fs = client.get("/api/catalog?country=CA&state=AB").json()
_ok(_fs["count"] > 0 and all(x["state"] == "AB" and x["country"] == "CA" for x in _fs["items"]) and "IA" in client.get("/api/catalog").json()["states"],
    f"/api/catalog?country=CA&state=AB -> {_fs['count']}, states filter lists IA")
_ok(all(set(x) >= {"id", "name", "lat", "lon", "region", "crop_group", "county", "acres", "family"} for x in _cat["items"]),
    "every catalog item has id, name, lat, lon, region, crop_group, county, acres, family")
_rf = client.get("/api/catalog?region=bc&crop_group=forage").json()
_ok(_rf["count"] == sum(x["crop_group"] == "forage" for x in _bc) > 0 and all(x["region"] == "bc" and x["crop_group"] == "forage" for x in _rf["items"]),
    f"/api/catalog?region=bc&crop_group=forage -> {_rf['count']}")
_ok(len({x["id"] for x in _cat["items"]}) == _cat["count"] and all(_al.B.parse_id(x["id"]) for x in _cat["items"]), "catalog ids unique, valid pt_ ids")
_ok(client.get("/api/locations").json()["count"] <= 20, "/api/locations unchanged (hand-built fields only, catalog not listed)")
_rng = _rnd.Random()
for x in _rng.sample(_ca, min(5, len(_ca))) + _rng.sample(_bc, min(3, len(_bc))) + _rng.sample(_us, 5) + _rng.sample(_can, 3):
    t0 = _t.time(); r = client.get(f"/api/locations/{x['id']}", headers={"X-Forwarded-For": "198.51.100.20"}); dt_ = _t.time() - t0
    if not _ok(r.status_code == 200, f"catalog {x['id']} ({x['name']}): GET /api/locations 200"):
        continue
    d = r.json(); e = _errs(_LOC_V, d)
    _ok(not e and d["_source"] == "catalog" and r.headers.get("X-Data-Source") == "catalog" and d["analysis"]["cache"] == "catalog" and dt_ < 0.5,
        f"catalog {x['id']}: schema-valid, _source catalog, {dt_ * 1000:.0f} ms {e}")
    _ok(d["region"] == (x["region"] if x["region"] in ("ca", "bc") else "other") and d["name"] == x["name"] and all(d["sections"][k]["status"] == "ready" for k in ("weather", "crop_history", "boundary", "strategies")),
        f"catalog {x['id']}: region {d['region']}, tier 1 ready {[(k, d['sections'][k]['status']) for k in ('weather', 'soil', 'crop_history', 'boundary', 'strategies')]}")
    rs = client.get(f"/api/locations/{x['id']}/strategies", headers={"X-Forwarded-For": "198.51.100.20"})
    _ok(rs.status_code == 200 and not _errs(_STR_V, rs.json()) and len(rs.json()["items"]) == 4 and rs.json()["_source"] == "catalog"
        and all(i["id"].startswith("bc") for i in rs.json()["items"]) == (x["region"] == "bc" or x["region"].startswith("can-")),
        f"catalog {x['id']}: /strategies 200 from the catalog, schema-valid, {'BC0-3' if x['region'] == 'bc' or x['region'].startswith('can-') else 'CA'} rotation set")

print("\nBC tier 1 and reserve / tribal land (live):")
_LIVE = [  # (label, lat, lon, ip, kind)
    ("BC tap: Salmon River valley hay field", 50.6141, -119.3634, "198.51.100.30", None),
    ("BC reserve: Switsemalph IR 3 (Neskonlith)", 50.70, -119.33, "198.51.100.31", "first_nations_reserve"),
    ("CA tribal land: Torres-Martinez Reservation farm field", 33.51, -116.12, "198.51.100.32", "tribal_land"),
]
for label, lat, lon, ip, kind in _LIVE:
    r = client.get(f"/api/analyze?lat={lat}&lon={lon}", headers={"X-Forwarded-For": ip})
    if not _ok(r.status_code == 200, f"{label}: 200 {'' if r.status_code == 200 else r.text[:200]}"):
        continue
    d = r.json(); st = d["sections"]; e = _errs(_LOC_V, d)
    _ok(not e, f"{label}: schema-valid {e}")
    if kind is None or kind == "first_nations_reserve":
        _ok(d["region"] == "bc" and d["region_adapter"] == "bc" and st["county"].get("regional_district"),
            f"{label}: region bc, regional district {st['county'].get('regional_district')}")
        _ok(st["stations"]["status"] == "ready" and d["stations"] and d["stations"][0]["network"] == "ECCC"
            and (d.get("climate_eccc") or {}).get("monthly", {}).get("annual_precip_mm"),
            f"{label}: ECCC stations ready ({[s['id'] for s in d['stations']]}), monthly climate {((d.get('climate_eccc') or {}).get('monthly') or {}).get('annual_precip_mm')} mm/yr")
        _ok(st["soil"]["status"] == "ready" and d["soil"]["source"]["id"] == "aafc_slc_v3_2" and d["soil"]["awc_mm_per_m"]["value"],
            f"{label}: SLC soil ready ({d['soil']['mukey']}, {d['soil']['texture_class']}, {d['soil']['drainage_class']}, HSG {d['soil']['hydrologic_group']})")
        _ok(st["crop_history"]["status"] == "ready" and st["crop_history"]["source"] == "aafc_aci" and len(d["crop_history"]) >= 10,
            f"{label}: AAFC ACI crop history ready ({len(d['crop_history'])} years, {st['crop_history'].get('years')})")
        _ok(st["strategies"]["status"] == "ready" and d["template"] == "bc_salmon_river_forage", f"{label}: strategies = BC rotation set (BC0-BC3)")
        rs = client.get(f"/api/locations/{d['id']}/strategies", headers={"X-Forwarded-For": ip})
        _ok(rs.status_code == 200 and [i["id"][:3] for i in rs.json()["items"]] == ["bc0", "bc1", "bc2", "bc3"] and not _errs(_STR_V, rs.json()),
            f"{label}: /strategies bc0-bc3, schema-valid")
    if kind is None:
        _ok(st["boundary"]["status"] == "ready" and st["boundary"]["source"] == "parcelmap_bc_x_alr" and "PID" not in json.dumps(d.get("parcel")),
            f"{label}: boundary = ParcelMap BC parcel x ALR ({st['boundary'].get('clip')}), no PID stored")
        _ok(d.get("land_status") is None and d.get("nation_tools") is None, f"{label}: not reserve land (land_status null)")
    else:
        ls, nt = d.get("land_status") or {}, d.get("nation_tools") or {}
        _ok(ls.get("kind") == kind and ls.get("name") and ls.get("nation") and st["land_status"]["status"] == "ready",
            f"{label}: land_status {ls.get('kind')} '{ls.get('name')}' (Nation: {ls.get('nation')})")
        progs = nt.get("programs") or []
        _ok(nt.get("nation") == ls.get("nation") and progs and all(p.get("url", "").startswith("https://") for p in progs if p["verified"]),
            f"{label}: nation_tools with {len(progs)} programs ({sum(p['verified'] for p in progs)} with verified links)")
        _ok(st["weather"]["status"] == "ready" and st["strategies"]["status"] == "ready" and st["crop_history"]["status"] == "ready",
            f"{label}: full tier-1 analysis (weather, crop history, strategies ready)")
        if kind == "first_nations_reserve":
            _ok((nt.get("salmon") or {}).get("route") == "/salmon", f"{label}: in the Salmon River watershed, links /salmon")
        if kind == "tribal_land":
            g = nt.get("groundwater") or {}
            _ok(g.get("sgma_subbasin") and "10723.2" in g["tribal_engagement"]["citation"], f"{label}: SGMA subbasin {g.get('sgma_subbasin')}, GSA {g.get('gsa')}, Water Code 10723.2(h) note")
        r2 = client.get(f"/api/analyze?lat={lat}&lon={lon}", headers={"X-Forwarded-For": ip})
        _ok(r2.status_code == 200 and r2.json()["analysis"]["cache"] == "hit", f"{label}: cached like any other point (repeat tap is a hit)")
_ok(client.get("/api/analyze?lat=50.6141&lon=-119.3634").json()["nation_tools"] is None, "BC farm off reserve: no nation_tools")
# ---- end farm catalog ========================================================================================
# ---- First Nations lands (app/lands.py) =======================================================================
print("\nFirst Nations lands:")
_lr = client.get("/api/lands")
_lj = _lr.json() if _lr.status_code == 200 else {"features": [], "properties": {}}
_lbc = [f for f in _lj["features"] if f["properties"].get("province") == "BC"]
_lca = [f for f in _lj["features"] if f["properties"].get("state") == "CA"]
_lus = [f for f in _lj["features"] if f["properties"].get("country") == "US"]
_lcan = [f for f in _lj["features"] if f["properties"].get("country") == "CAN"]
_ok(_lr.status_code == 200 and "max-age=86400" in _lr.headers.get("cache-control", "") and len(_lbc) > 1500 and len(_lca) > 50 and len(_lus) > 600 and len(_lcan) > 3000, f"/api/lands: 200, cacheable 1 day, {len(_lus)} US lands ({len(_lca)} in CA), {len(_lcan)} Canada ({len(_lbc)} in BC)")
_ok(len(_lr.content) < 6_500_000 and _lj["properties"].get("fetched") and len(_lj["properties"].get("sources", [])) == 3, f"/api/lands: {len(_lr.content) / 1e6:.2f} MB, fetch date and 3 sources recorded")
_ok(all({"id", "name", "nation", "kind", "area_ha", "centroid", "country", "bbox"} <= set(f["properties"]) for f in _lj["features"]), "/api/lands: every land has id, name, nation, kind, area, centroid, country, bbox")
_ok(any("Tule River" in f["properties"]["name"] for f in _lca) and any(f["properties"]["nation"] == "Splatsin" for f in _lbc), "/api/lands: Tule River (CA) and Splatsin (BC) present")
_ov = client.get("/api/lands/overview")
_ovj = _ov.json() if _ov.status_code == 200 else {"rows": []}
_ok(_ov.status_code == 200 and len(_ovj["rows"]) == len(_lj["features"]) and len(_ov.content) < 1_500_000, f"/api/lands/overview: {len(_ovj['rows'])} lands, {len(_ov.content) / 1e3:.0f} KB raw")
_bx = client.get("/api/lands?bbox=-111,35,-108,37").json()
_ok(any(f["properties"]["nation"] == "Navajo Nation" for f in _bx["features"]) and 0 < _bx["properties"]["returned"] < len(_lj["features"]) and all(f["properties"]["country"] == "US" for f in _bx["features"]), f"/api/lands?bbox= (Four Corners): {_bx['properties']['returned']} lands incl. Navajo Nation")
_ok(all(f["properties"].get("province") == "SK" for f in client.get("/api/lands?country=CAN&province=SK").json()["features"]) and client.get("/api/lands?country=XX").status_code == 422 and client.get("/api/lands?bbox=1,2").status_code == 422, "/api/lands: province filter, bad country and bbox -> 422")
_pick = lambda fs, pred: next((f for f in fs if pred(f["properties"])), None)
_cases = [
    (_pick(_lj["features"], lambda p: p.get("province") == "BC" and p["name"].startswith("Salmon River 1 (Splatsin")), "BC"),
    (_pick(_lca, lambda p: p["name"].startswith("Tule River Reservation")), "CA"),
    (_pick(_lj["features"], lambda p: p.get("province") == "SK" and p["nation"].startswith("Carry the Kettle")), "CAN"),
    (_pick(_lj["features"], lambda p: p.get("province") == "ON" and p["nation"] == "Six Nations"), "CAN"),
    (_pick(_lj["features"], lambda p: p["name"] == "Navajo Nation Reservation"), "US"),
    (_pick(_lj["features"], lambda p: p.get("state") in ("OK", "MT") and p["kind"] == "reservation"), "US"),
]
for _lf, _jur in _cases:
    _lid = _lf["properties"]["id"] if _lf else "missing"
    _ld = client.get(f"/api/lands/{_lid}")
    _lj2 = _ld.json() if _ld.status_code == 200 else {}
    _ok(_ld.status_code == 200 and _lj2.get("jurisdiction") == _jur and _lj2["tools"]["funding"].startswith("/api/locations/pt_") and f"jurisdiction={_jur}" in _lj2["tools"]["funding"] and _lj2["area_acres"] > 0 and _lj2["centroid"]["lat"] and _lj2.get("source"), f"/api/lands/{_lid}: {_lj2.get('name')} ({_jur}, {_lj2.get('region')}), tools link to its centroid, {len(_lj2.get('nearby', []))} nearby within 15 km")
_fj = client.get(_cases[2][0] and client.get(f"/api/lands/{_cases[2][0]['properties']['id']}").json()["tools"]["funding"]).json() if _cases[2][0] else {}
_fids = {p["id"] for p in _fj.get("programs", [])}
_ok(bool(_fj.get("programs")) and all(set(p["jurisdictions"]) & {"CAN"} for p in _fj["programs"]) and _fj.get("location_jurisdiction") == "CAN", f"Saskatchewan reserve funding: {len(_fids)} Canada programs, location jurisdiction CAN")
_ok(client.get("/api/lands/nope").status_code == 404, "/api/lands/nope -> 404")
# ---- end lands ================================================================================================
# ---- Farming with a disability help ============================================================================
print("\nDisability help:")
_dh = client.get("/api/help/disability?region=bc").json()
_dc = client.get("/api/help/disability?region=ca").json()
_ok(any(p["id"] == "workbc_ats" for p in _dh["programs"]) and not any(p["id"] == "workbc_ats" for p in _dc["programs"]), "/api/help/disability: BC lists WorkBC ATS, CA does not")
_ok(any(p["id"] == "california_agrability" for p in _dc["programs"]) and all(p["url"].startswith("https://") and "verified" in p and p["checked"] and p["line"] for p in _dc["programs"] + _dh["programs"]), "/api/help/disability: California AgrAbility listed; every program has https url, verified flag, date and a plain line")
_ok(client.get("/api/help/disability?region=xx").status_code == 422, "/api/help/disability?region=xx -> 422")
# ---- end disability help ======================================================================================
# ---- voice input (app/chat/transcribe.py) =====================================================================
print("\nVoice input:")
import subprocess as _sp, tempfile as _tfm  # noqa: E402
from app.chat import transcribe as _stt  # noqa: E402
with _tfm.TemporaryDirectory() as _d:
    _w = f"{_d}/s.wav"
    _sp.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "1", _w], check=True)
    _tr = client.post("/api/ask/transcribe", files={"audio": ("s.wav", open(_w, "rb"), "audio/wav")})
if _stt.available():
    _ok(_tr.status_code == 200 and "text" in _tr.json() and "duration_s" in _tr.json(), f"/api/ask/transcribe: 200 with text ({_tr.status_code})")
else:
    _ok(_tr.status_code == 501, f"/api/ask/transcribe: 501 without the stt extra ({_tr.status_code})")
# ---- end voice input ==========================================================================================
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAIL'}")
sys.exit(1 if fails else 0)
