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
    check("POST", L + "/score", ANY, {"weights": {"bogus": 1}}, expect=422)
    check("GET", L + "/models", validator("responses.schema.json", "Models"))
    check("GET", L + "/zones", validator("responses.schema.json", "Zones"))
    for layer in LAYERS:
        check("GET", L + f"/trends?layer={layer}&year=2023", validator("responses.schema.json", "Trends"))
    check("GET", L + "/news", validator("responses.schema.json", "News"))
    check("GET", L + "/validation", validator("responses.schema.json", "Validation"))
    crop_ids = sorted({c["crop_id"] for s in (r.json()["items"] if r else []) for c in s["calendar"]})
    for cid in crop_ids:
        check("GET", f"/api/crops/{cid}", validator("crop.schema.json"))
check("GET", "/api/locations/nope", ANY, expect=404)
check("GET", "/api/bc/news", validator("responses.schema.json", "News"))
check("GET", "/api/bc/signal", validator("responses.schema.json", "BcSignal"))
check("GET", "/api/glossary", validator("responses.schema.json", "Glossary"))
# CORS
r = client.options("/api/locations", headers={"Origin": "http://localhost:5171", "Access-Control-Request-Method": "GET"})
ok = r.headers.get("access-control-allow-origin") == "http://localhost:5171"
fails += not ok; print(("PASS" if ok else "FAIL") + " CORS preflight localhost:5171")
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAIL'}")
sys.exit(1 if fails else 0)
