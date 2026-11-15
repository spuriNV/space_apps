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

from app.main import ROOT, PRESETS, LAYERS, app  # noqa: E402

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
# Routes that must be served from real output (a regression to fixture is a FAIL). Everything else may be fixture.
EXPECT_REAL = ["/api/locations", "/api/locations/{id}", "/daily", "/features/weekly", "/strategies", "/score", "/zones",
               "/trends?layer=heatwave_days", "/trends?layer=precip_anomaly", "/trends?layer=usdm_d2_weeks", "/trends?layer=reservoir_storage", "/trends?layer=grace_gw_pct", "/news", "/validation", "/calendar", "/grid", "/api/bc/news", "/api/crops/{cid}"]
EXPECT_FIXTURE_OK = {"/models": "no producer (AI workstream)", "/api/bc/signal": "SMAP/GRACE need Earthdata (blocked)",
                     }
EXPECT_REAL += ["/openet", "/nasa_now", "/nasa_series", "/insurance", "/stress", "/water_seen", "/api/glossary"]
# NASA AppEEARS layers: must be real once their cache exists for both presets (backend/nasa); fixture is allowed only before that
for _layer, _ds in (("smap_anomaly", "smap_l4"), ("modis_ndvi_anomaly", "modis")):
    if all((ROOT / "data" / "cache" / _p / f"{_ds}.parquet").exists() for _p in PRESETS):
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
            if src not in ("fixture", "real") or data.get("_source") != src:
                errs.append(f"missing/inconsistent source marker header={src} field={data.get('_source')}")
            key = url.split("?")[0]
            if key.endswith("/trends"):
                key += "?layer=" + url.split("layer=")[1].split("&")[0]
            for pid in PRESETS:
                key = key.replace(pid, "{id}")
            if "/api/crops/" in key:
                key = "/api/crops/{cid}"
            if "/api/locations/{id}/" in key:
                key = "/" + key.split("/api/locations/{id}/")[1] if key.split("/api/locations/{id}/")[1] != "" else key
            SOURCES.setdefault(key, set()).add(src)
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
# CORS
r = client.options("/api/locations", headers={"Origin": "http://localhost:5171", "Access-Control-Request-Method": "GET"})
ok = r.headers.get("access-control-allow-origin") == "http://localhost:5171"
fails += not ok; print(("PASS" if ok else "FAIL") + " CORS preflight localhost:5171")
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAIL'}")
sys.exit(1 if fails else 0)
